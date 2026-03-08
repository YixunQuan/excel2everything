# -*- coding: utf-8 -*-
"""
依赖分析器 — 从 IR 模型中提取源表依赖关系。

分析维度:
  1. 表级依赖:   M 表依赖了哪些源表
  2. 字段级依赖: M 表的每个目标字段引用了哪些源表的哪些字段
  3. 全局视图:   所有源表被哪些 M 表引用（反向索引）
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from excel2everything.models import TableModel, MappingGroup, FieldMapping


# ── 数据结构 ──

@dataclass
class SourceTableRef:
    """一个源表的引用信息"""
    table_name: str              # 源表英文名
    alias: str = ""              # 在 SQL 中使用的别名
    comment: str = ""            # FROM 子句中的注释（通常是中文表名）
    join_type: str = "MAIN"      # MAIN / LEFT JOIN / INNER JOIN / ...
    used_fields: List[str] = field(default_factory=list)  # 被引用的字段列表
    used_by_targets: List[str] = field(default_factory=list)  # 哪些目标字段引用了它

    def to_dict(self):
        return asdict(self)


@dataclass
class FieldDependency:
    """单个目标字段的依赖信息"""
    target: str                  # 目标字段名
    target_label: str = ""
    refs: List[dict] = field(default_factory=list)  # [{alias, field, table_name}]
    is_constant: bool = False    # 是否为常量/变量（无源表依赖）
    expr: str = ""


@dataclass
class GroupDependency:
    """单个映射组的依赖汇总"""
    group_index: int
    group_name: str
    source_tables: List[SourceTableRef] = field(default_factory=list)
    field_deps: List[FieldDependency] = field(default_factory=list)

    def to_dict(self):
        return {
            "group_index": self.group_index,
            "group_name": self.group_name,
            "source_tables": [t.to_dict() for t in self.source_tables],
            "field_deps": [asdict(f) for f in self.field_deps],
        }


@dataclass
class TableDependency:
    """一个 M 表的完整依赖分析"""
    table_name: str
    table_label: str
    groups: List[GroupDependency] = field(default_factory=list)

    @property
    def all_source_tables(self) -> List[str]:
        """去重后的所有源表名列表"""
        seen = set()
        result = []
        for g in self.groups:
            for st in g.source_tables:
                if st.table_name not in seen:
                    seen.add(st.table_name)
                    result.append(st.table_name)
        return result

    def to_dict(self):
        return {
            "table_name": self.table_name,
            "table_label": self.table_label,
            "all_source_tables": self.all_source_tables,
            "source_count": len(self.all_source_tables),
            "groups": [g.to_dict() for g in self.groups],
        }


# ── 解析逻辑 ──

# SQL 关键字排除列表 (增强版)
_SQL_KEYWORDS = frozenset({
    "SELECT", "FROM", "WHERE", "ON", "AND", "OR", "IN", "AS", "OVER", "BY",
    "ORDER", "PARTITION", "CASE", "WHEN", "THEN", "ELSE", "END", "GROUP",
    "HAVING", "BETWEEN", "NOT", "NULL", "IS", "LIKE", "EXISTS", "UNION",
    "ALL", "DISTINCT", "TOP", "INTO", "SET", "VALUES", "INSERT", "UPDATE",
    "DELETE", "CREATE", "DROP", "ALTER", "INDEX", "TABLE", "VIEW", "TRUE",
    "FALSE", "ASC", "DESC", "LIMIT", "OFFSET", "FETCH", "NEXT", "ROWS",
    "ONLY", "WITH", "RECURSIVE", "INTERVAL", "DAY", "MONTH", "YEAR",
    "DATE", "TIMESTAMP", "VARCHAR2", "NUMBER", "CHAR", "INTEGER",
    "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL",
    "USING", "NATURAL", "LATERAL", "APPLY", "PIVOT", "UNPIVOT",
    "CAST", "CONVERT", "EXTRACT", "SUBSTRING", "POSITION",
})


def _extract_tables_from_clause(from_clause: str) -> List[SourceTableRef]:
    """
    从 FROM 子句中提取所有源表及其别名。

    处理的情况:
      - 主表: TABLE_NAME ALIAS --注释
      - JOIN: LEFT JOIN TABLE_NAME ALIAS ON ...
      - 子查询中的表: (SELECT ... FROM TABLE_NAME ALIAS ...)
    """
    if not from_clause or not from_clause.strip():
        return []

    results = []
    seen = set()
    lines = from_clause.strip().split("\n")

    # 1. 第一行通常是主表（不带 FROM/JOIN 关键字）
    first_line = lines[0].strip()
    first_clean = re.sub(r"\s*--.*$", "", first_line).strip()
    first_comment = ""
    cm = re.search(r"--\s*(.+)$", first_line)
    if cm:
        first_comment = cm.group(1).strip()

    m = re.match(r"^([A-Z_][A-Z0-9_.]+)\s+([A-Z][A-Z0-9_]*)", first_clean, re.IGNORECASE)
    if m and m.group(1).upper() not in _SQL_KEYWORDS:
        tbl = m.group(1).upper()
        alias = m.group(2)
        if tbl not in seen:
            seen.add(tbl)
            results.append(SourceTableRef(
                table_name=tbl, alias=alias,
                comment=first_comment, join_type="MAIN"
            ))

    # 2. 扫描所有 FROM / JOIN 关键字后的表名
    full_text = from_clause
    # 匹配 JOIN 类型
    join_pattern = re.compile(
        r'((?:LEFT|RIGHT|INNER|OUTER|CROSS|FULL)\s+)?JOIN\s+([A-Z_][A-Z0-9_.]+)\s+([A-Z][A-Z0-9_]*)?',
        re.IGNORECASE
    )
    for jm in join_pattern.finditer(full_text):
        join_type = (jm.group(1) or "").strip().upper() + " JOIN"
        join_type = join_type.strip()
        tbl = jm.group(2).upper()
        alias = jm.group(3) or ""

        if tbl in _SQL_KEYWORDS:
            continue

        # 提取该行的注释
        line_start = full_text.rfind("\n", 0, jm.start()) + 1
        line_end = full_text.find("\n", jm.end())
        if line_end == -1:
            line_end = len(full_text)
        line_text = full_text[line_start:line_end]
        comment = ""
        cm2 = re.search(r"--\s*(.+?)(?:\n|$)", line_text)
        if cm2:
            comment = cm2.group(1).strip()

        if tbl not in seen:
            seen.add(tbl)
            results.append(SourceTableRef(
                table_name=tbl, alias=alias,
                comment=comment, join_type=join_type
            ))

    # 3. 子查询中的 FROM TABLE
    from_pattern = re.compile(
        r'FROM\s+([A-Z_][A-Z0-9_.]+)\s+([A-Z][A-Z0-9_]*)?',
        re.IGNORECASE
    )
    for fm in from_pattern.finditer(full_text):
        tbl = fm.group(1).upper()
        alias = fm.group(2) or ""

        if tbl in _SQL_KEYWORDS:
            continue

        # 提取注释
        line_start = full_text.rfind("\n", 0, fm.start()) + 1
        line_end = full_text.find("\n", fm.end())
        if line_end == -1:
            line_end = len(full_text)
        line_text = full_text[line_start:line_end]
        comment = ""
        cm3 = re.search(r"--\s*(.+?)(?:\n|$)", line_text)
        if cm3:
            comment = cm3.group(1).strip()

        if tbl not in seen:
            seen.add(tbl)
            results.append(SourceTableRef(
                table_name=tbl, alias=alias,
                comment=comment, join_type="SUBQUERY"
            ))

    return results


def _extract_field_refs(expr: str) -> List[Tuple[str, str]]:
    """
    从 SQL 表达式中提取所有 alias.field 引用。
    返回 [(alias, field), ...]
    """
    if not expr:
        return []
    # 匹配 ALIAS.FIELD_NAME 模式，排除字符串常量内的内容
    refs = re.findall(r'\b([A-Z][A-Z0-9_]*)\.\b([A-Z][A-Z0-9_]+)\b', expr, re.IGNORECASE)
    # 过滤掉 SQL 关键字作为前缀的情况
    return [(a, f) for a, f in refs if a.upper() not in _SQL_KEYWORDS]


def _is_constant_expr(expr: str) -> bool:
    """判断表达式是否为常量/变量（无源表字段引用）"""
    if not expr or expr.strip() == "NULL":
        return True
    e = expr.strip()
    # 纯引号值
    if re.match(r"^'[^']*'$", e):
        return True
    # 变量引用
    if re.match(r"^[VP]_[A-Z0-9_]+$", e):
        return True
    # 空字符串
    if e == "''":
        return True
    return False


# ── 主入口 ──

def analyze_table(model: TableModel) -> TableDependency:
    """分析单个 M 表的依赖关系"""
    td = TableDependency(
        table_name=model.table_name,
        table_label=model.table_label,
    )

    for group in model.groups:
        # 1. 从 FROM 子句提取源表
        source_tables = _extract_tables_from_clause(group.from_clause)

        # 建立 alias → table_name 映射
        alias_map: Dict[str, str] = {}
        for st in source_tables:
            if st.alias:
                alias_map[st.alias.upper()] = st.table_name

        # 2. 分析每个字段的依赖
        field_deps: List[FieldDependency] = []
        # 记录每个源表被引用的字段和目标字段
        table_fields: Dict[str, Set[str]] = defaultdict(set)
        table_targets: Dict[str, Set[str]] = defaultdict(set)

        for f in group.fields:
            fd = FieldDependency(
                target=f.target,
                target_label=f.target_label,
                expr=f.expr,
                is_constant=_is_constant_expr(f.expr),
            )

            if not fd.is_constant:
                refs = _extract_field_refs(f.expr)
                for alias, field_name in refs:
                    tbl = alias_map.get(alias.upper(), f"?{alias}")
                    fd.refs.append({
                        "alias": alias,
                        "field": field_name,
                        "table_name": tbl,
                    })
                    table_fields[tbl].add(field_name)
                    table_targets[tbl].add(f.target)

            field_deps.append(fd)

        # 3. 回填源表的引用字段信息
        for st in source_tables:
            st.used_fields = sorted(table_fields.get(st.table_name, set()))
            st.used_by_targets = sorted(table_targets.get(st.table_name, set()))

        gd = GroupDependency(
            group_index=group.group_index,
            group_name=group.name or f"组{group.group_index + 1}",
            source_tables=source_tables,
            field_deps=field_deps,
        )
        td.groups.append(gd)

    return td


def analyze_all(models: List[TableModel]) -> Dict[str, TableDependency]:
    """分析所有 M 表的依赖关系"""
    return {m.table_name: analyze_table(m) for m in models}


def build_reverse_index(deps: Dict[str, TableDependency]) -> Dict[str, List[dict]]:
    """
    构建反向索引: 源表 → 被哪些 M 表的哪些字段引用。

    返回:
    {
        "F_ECIF_T01_xxx": [
            {"m_table": "M_CUST_IND_INFO", "group": "...", "fields_used": [...], "targets": [...]},
            ...
        ]
    }
    """
    reverse: Dict[str, List[dict]] = defaultdict(list)

    for m_name, td in deps.items():
        for gd in td.groups:
            for st in gd.source_tables:
                reverse[st.table_name].append({
                    "m_table": m_name,
                    "m_label": td.table_label,
                    "group": gd.group_name,
                    "join_type": st.join_type,
                    "alias": st.alias,
                    "comment": st.comment,
                    "fields_used": st.used_fields,
                    "fields_count": len(st.used_fields),
                    "targets": st.used_by_targets,
                })

    # 按引用次数降序排列
    return dict(sorted(reverse.items(), key=lambda x: -len(x[1])))


def build_summary_stats(deps: Dict[str, TableDependency]) -> dict:
    """构建全局统计摘要"""
    all_source = set()
    total_refs = 0
    max_deps_table = ("", 0)
    most_shared_source = ("", 0)

    source_counter: Dict[str, int] = defaultdict(int)

    for m_name, td in deps.items():
        src_count = len(td.all_source_tables)
        if src_count > max_deps_table[1]:
            max_deps_table = (m_name, src_count)
        for st_name in td.all_source_tables:
            all_source.add(st_name)
            source_counter[st_name] += 1
            total_refs += 1

    if source_counter:
        top_source = max(source_counter.items(), key=lambda x: x[1])
        most_shared_source = top_source

    return {
        "total_m_tables": len(deps),
        "total_source_tables": len(all_source),
        "total_references": total_refs,
        "most_deps_table": {"name": max_deps_table[0], "count": max_deps_table[1]},
        "most_shared_source": {"name": most_shared_source[0], "count": most_shared_source[1]},
        "avg_sources_per_table": round(total_refs / max(len(deps), 1), 1),
    }


class DependencyAnalyzer:
    """依赖分析器
    
    分析数据模型中的表依赖关系、字段依赖关系。
    
    Example:
        >>> from excel2everything import Analyzer
        >>> analyzer = Analyzer()
        >>> deps = analyzer.analyze(model)
        >>> print(f"源表列表: {deps.all_source_tables}")
    """
    
    def __init__(self):
        """初始化依赖分析器"""
        pass
    
    def analyze(self, model: TableModel) -> TableDependency:
        """
        分析单个表模型的依赖关系
        
        Args:
            model: 表模型数据
            
        Returns:
            TableDependency 依赖分析结果
        """
        return analyze_table(model)
    
    def analyze_all(self, models: List[TableModel]) -> Dict[str, TableDependency]:
        """
        批量分析所有表模型的依赖关系
        
        Args:
            models: 表模型列表
            
        Returns:
            {table_name: TableDependency} 字典
        """
        return analyze_all(models)
    
    def build_reverse_index(self, deps: Dict[str, TableDependency]) -> Dict[str, List[dict]]:
        """
        构建反向索引: 源表 → 被哪些 M 表引用
        
        Args:
            deps: 依赖分析结果
            
        Returns:
            {source_table: [引用信息列表]} 字典
        """
        return build_reverse_index(deps)
    
    def build_summary(self, deps: Dict[str, TableDependency]) -> dict:
        """
        构建全局统计摘要
        
        Args:
            deps: 依赖分析结果
            
        Returns:
            统计摘要字典
        """
        return build_summary_stats(deps)
