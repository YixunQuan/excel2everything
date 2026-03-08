# -*- coding: utf-8 -*-
"""
Excel 解析器 — 从数据模型 Excel 文件中提取映射信息，转为 IR 模型。

这是一个「输入适配器」，未来可以添加 csv.py / yaml_loader.py 等其他适配器，
只要输出统一的 List[TableModel] 即可。
"""

import re
from typing import List, Dict, Tuple, Optional
from collections import OrderedDict

import pandas as pd

from excel2everything.models import TableModel, MappingGroup, FieldMapping, CodeMappingJoin


# ============================================================
# 映射规则解析
# ============================================================

def _parse_source_table(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """解析 '源系统表英文名称' → (table_name, alias)"""
    if not raw or raw.strip() in ("", "nan", "固定"):
        return None, None
    parts = raw.strip().split(None, 1)
    return parts[0], (parts[1] if len(parts) > 1 else parts[0])


def _normalize_mapping(
    rule: str,
    src_table_info: str,
    src_field: str,
    alias: str,
    target_field: str = "",
) -> Tuple[str, str, str]:
    """
    解析映射规则文本 → (sql_expr, comment, warning)

    返回:
      sql_expr: 可直接放入 SELECT 的 SQL 表达式
      comment:  行尾注释
      warning:  解析告警(空 = 正常)
    """
    if not rule or rule.strip() in ("", "nan"):
        return "NULL", "", ""

    r = rule.strip()

    # 0. DATA_DT 公共字段特殊处理 - 统一使用 V_DATEID
    if target_field.upper() == "DATA_DT":
        return "V_DATEID", "-- 数据日期", ""

    # 1. 直取
    if r == "直取":
        if src_field and src_field.strip() not in ("", "nan", "固定"):
            field = src_field.strip().split("\n")[0].strip()
            expr = f"{alias}.{field}" if alias else field
            return expr, "", ""
        return "NULL", "", f"映射规则={r},但无源字段"
    
    # 1.1 码值 / 码值映射 / 公共码值 / 中文转码值 - 返回占位符，后续会替换为 Vi.detail_code_value
    # 支持包含这些关键词的规则（如"码值映射-证件类型"）
    code_mapping_keywords = ("码值", "码值映射", "公共码值", "中文转码值")
    if any(keyword in r for keyword in code_mapping_keywords):
        if src_field and src_field.strip() not in ("", "nan", "固定"):
            field = src_field.strip().split("\n")[0].strip()
            # 返回占位符，后续会被替换
            return f"__CODE_MAPPING_{field}__", "", ""
        return "NULL", "", f"映射规则={r},但无源字段"

    # 1.5 空值语义规则
    if r in ("不涉及", "为空", "空"):
        return "NULL", f"-- {r}", ""

    # 2. 变量 / 参数引用 (增强:支持更多变量前缀)
    if re.match(r"^[VPvp]_[A-Z0-9_]+$", r, re.IGNORECASE):
        return r.upper(), "", ""

    # 3. 完整引号固定值 'xxx' 或 'xxx' -- comment
    m = re.match(r"^'([^']*)'\s*(--.*)?$", r)
    if m:
        value = m.group(1)
        comment = (m.group(2) or "").strip()
        # 不需要转义，因为这里匹配的是 [^'] ，即不包含单引号的内容
        return f"'{value}'", comment, ""
    
    # 处理内部包含单引号的情况，如 '-- 原S70报送字段，年终升级后删除'
    if r.startswith("'"):
        last_quote_idx = r.rfind("'")
        
        # 情况1: 只有一个单引号（开头），后面是注释或空白
        if last_quote_idx == 0:
            rest = r[1:].strip()
            # 如果后面是注释或空白，返回空字符串
            if rest == "" or rest.startswith("--"):
                return "''", rest if rest.startswith("--") else "", ""
        
        # 情况2: 有配对的单引号
        elif last_quote_idx > 0:
            value = r[1:last_quote_idx]
            rest = r[last_quote_idx + 1:].strip()
            if rest == "" or rest.startswith("--"):
                comment = rest if rest.startswith("--") else ""
                # 检查是否已经转义过，避免重复转义
                if "'" in value and "''" not in value:
                    value = value.replace("'", "''")
                return f"'{value}'", comment.strip(), ""

    # 4. SQL 表达式 (CASE / 函数) - 增强识别
    kw = ("CASE ", "SELECT ", "CONCAT(", "SUBSTR(", "REPLACE(",
          "TO_CHAR(", "TO_DATE(", "NVL(", "COALESCE(", "DECODE(",
          "IF(", "TRIM(", "UPPER(", "LOWER(", "CAST(",
          "TDH_TODATE(", "LAST_DAY(", "ADD_MONTHS(", "TRUNC(", "ROW_NUMBER(",
          "LENGTH(", "INSTR(", "ROUND(", "FLOOR(", "CEIL(", "ABS(",
          "SIGN(", "MOD(", "POWER(", "SQRT(", "EXP(", "LN(", "LOG(",
          "REGEXP_REPLACE(", "REGEXP_SUBSTR(", "LPAD(", "RPAD(",
          "GREATEST(", "LEAST(", "NULLIF(", "SUM(", "COUNT(", "AVG(",
          "MAX(", "MIN(", "FIRST_VALUE(", "LAST_VALUE(", "LAG(", "LEAD(")
    if any(r.upper().startswith(k) for k in kw):
        return _sanitize_trailing_comment(r), "", ""
    if "CASE" in r.upper() and "WHEN" in r.upper():
        return _sanitize_trailing_comment(r), "", ""

    # 5. 缺失左引号: value' -- comment
    # 这种情况下，value' 后面跟空格和注释，说明是字符串字面量缺少了左引号
    m2 = re.match(r"^([^']+)'\s*(--.*)?$", r)
    if m2:
        val = m2.group(1).strip()
        cmt = (m2.group(2) or "").strip()
        # 排除 SQL 关键字，避免误判
        if not any(k in val.upper() for k in ("SELECT", "FROM", "WHERE", "CASE", "WHEN", "END")):
            # 检查 val 中是否有单引号需要转义
            if "'" in val:
                val = val.replace("'", "''")
            return f"'{val}'", cmt, ""

    # 6. 纯数字或带小数点的数字
    if re.match(r"^\d+(\.\d+)?$", r):
        return r, "", ""  # 数字直接保留,不加引号

    # 7. 拼接操作
    if "||" in r:
        return _sanitize_trailing_comment(r), "", ""

    # 8. 源表为"固定"
    if src_table_info and src_table_info.strip() == "固定":
        if r == "'":
            return "''", "", ""
        # 如果不是以引号开头的，自动加引号并转义内部的单引号
        if not r.startswith("'"):
            # SQL 中单引号需要用两个单引号转义
            escaped_r = r.replace("'", "''")
            return f"'{escaped_r}'", "", ""
        # 如果已经有引号，检查内部是否需要转义
        # 移除首尾引号，转义内部单引号，再加回引号
        if r.startswith("'") and r.endswith("'") and len(r) > 2:
            inner = r[1:-1]
            # 只有当内部单引号不是成对出现时才转义
            # 统计内部单引号数量
            inner_quote_count = inner.count("'")
            if inner_quote_count > 0:
                # 如果是奇数个，说明有未转义的单引号
                if inner_quote_count % 2 != 0:
                    inner = inner.replace("'", "''")
            return f"'{inner}'", "", ""
        return r, "", ""

    # 9. 简单的表.字段引用 (A.FIELD)
    if re.match(r"^[A-Z_][A-Z0-9_]*\.[A-Z_][A-Z0-9_]*$", r, re.IGNORECASE):
        return r, "", ""

    # 10. fallback - 但减少告警
    # 如果包含常见SQL模式,直接保留不告警
    if any(pat in r.upper() for pat in ["(", ")", "+", "-", "*", "/", "."]):
        return _sanitize_trailing_comment(r), "", ""
    
    return r, "", f"未识别的映射规则，已原样保留: {r[:60]}"


def _sanitize_trailing_comment(expr: str) -> str:
    """去除表达式尾部的 SQL 单行注释，避免吞掉 AS alias"""
    if "--" not in expr:
        return expr.strip()
    lines = expr.split("\n")
    if len(lines) == 1:
        return re.sub(r"\s*--[^\n]*$", "", expr).rstrip()
    cleaned = lines[:-1]
    cleaned.append(re.sub(r"\s*--[^\n]*$", "", lines[-1]).rstrip())
    return "\n".join(cleaned)


def _clean_from_clause(from_clause: str) -> str:
    """
    清理 FROM 子句中的序号前缀和多余空白
    
    处理的情况:
    - '1.表\nF_TABLE T01' -> 'F_TABLE T01'
    - '1. 表名' -> '表名'
    - '2.表名 T01' -> '表名 T01'
    - 多行时清理每一行的序号前缀
    - '1.表' 单独一行会被移除
    - '过滤条件' 等说明性文本会被转换为 SQL 注释
    
    示例:
    >>> _clean_from_clause("1.表\nF_HXYW_GLSINACCTLIST_I T01")
    'F_HXYW_GLSINACCTLIST_I T01'
    >>> _clean_from_clause("1. 表名 T01 -- 内部帐明细")
    '表名 T01 -- 内部帐明细'
    """
    if not from_clause:
        return ""
    
    # 需要转换为注释的关键词（这些是说明性文本，不是 SQL 代码）
    comment_keywords = ('过滤条件', '筛选条件', '查询条件', '条件')
    
    lines = from_clause.split("\n")
    cleaned_lines = []
    
    for line in lines:
        # 保留注释部分
        comment = ""
        if "--" in line:
            parts = line.split("--", 1)
            line = parts[0]
            comment = "--" + parts[1]
        
        # 去除行首的序号前缀 (如 "1.表" 或 "1. " 或 "2.FROM")
        line = re.sub(r'^\s*\d+\.\s*', '', line.strip())
        
        # 如果清理后只剩下单个汉字"表"或为空，跳过这一行
        if line.strip() in ('', '表', 'FROM'):
            continue
        
        # 如果是说明性关键词（如"过滤条件"），转换为 SQL 注释
        # 检查是否匹配关键词（支持多种格式："过滤条件"、"过滤条件："、"2. 过滤条件"、"2.过滤条件：" 等）
        line_stripped = line.strip()
        matched_keyword = None
        for kw in comment_keywords:
            # 精确匹配
            if line_stripped == kw:
                matched_keyword = kw
                break
            # 带冒号（中英文）
            if line_stripped.startswith(kw + '：') or line_stripped.startswith(kw + ':'):
                matched_keyword = kw
                break
            # 带序号前缀（如 "1. 过滤条件"、"2.过滤条件："）
            seq_match = re.match(r'^\d+\.\s*', line_stripped)
            if seq_match:
                rest = line_stripped[seq_match.end():]
                if rest == kw or rest.startswith(kw + '：') or rest.startswith(kw + ':'):
                    matched_keyword = kw
                    break
        if matched_keyword:
            # 如果已经有注释，合并；否则添加注释前缀
            if comment:
                line = "-- " + line_stripped + " " + comment.lstrip("--").lstrip()
            else:
                line = "-- " + line_stripped
            comment = ""  # 已经处理过了
        
        # 重新组合（如果有注释的话）
        if comment and line.strip() and not line.strip().startswith("--"):
            line = line.rstrip() + " " + comment
        
        if line.strip():
            cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)


# ============================================================
# 列分组检测
# ============================================================

def _detect_col_groups(columns: List[str]) -> Dict[str, List[str]]:
    """将 pandas 的 .1 .2 后缀列按基础名分组"""
    groups: Dict[str, List[str]] = OrderedDict()
    for col in columns:
        base = re.sub(r"\.\d+$", "", col)
        groups.setdefault(base, []).append(col)
    for base in groups:
        groups[base].sort(
            key=lambda c: int(c.rsplit(".", 1)[1])
            if "." in c and c.rsplit(".", 1)[1].isdigit() else 0
        )
    return groups


def _count_groups(col_groups: Dict[str, List[str]]) -> int:
    keys = ["关联条件", "源系统表英文名称", "映射规则"]
    return max((len(col_groups.get(k, [])) for k in keys), default=1)


# ============================================================
# 主解析入口
# ============================================================

def extract_from_excel(
    file_path: str,
    only_tables: List[str] = None,
    filter_enabled: bool = True,
    filter_column: str = "启用标记",
) -> List[TableModel]:
    """
    从 Excel 文件中提取所有表的映射模型。

    Args:
        file_path:     Excel 文件路径
        only_tables:   只处理的表英文名列表（None = 全部）
        filter_enabled: 是否启用过滤（只处理启用标记列为 1 的行）

    Returns:
        List[TableModel] — 结构化的映射模型列表
    """
    engine = "xlrd" if file_path.lower().endswith(".xls") else "openpyxl"
    xls = pd.ExcelFile(file_path, engine=engine)

    # 1. 读取目录
    catalog = pd.read_excel(xls, sheet_name="目录", dtype=str)
    tables_meta = []
    for _, row in catalog.iterrows():
        cn = str(row.get("表中文名", "")).strip()
        en = str(row.get("表英文名", "")).strip()
        if cn and cn != "nan" and en and en != "nan":
            tables_meta.append((cn, en))

    if only_tables:
        tables_meta = [(cn, en) for cn, en in tables_meta if en in only_tables]

    # 2. 读取组标签 (Excel 第 4 行)
    def _read_group_labels(sheet_name: str) -> Dict[int, str]:
        try:
            raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=4, dtype=str)
            labels = {}
            if len(raw) >= 4:
                for ci, val in enumerate(raw.iloc[3]):
                    vs = str(val).strip()
                    if vs != "nan" and "来源表" in vs:
                        labels[ci] = vs
            return labels
        except Exception:
            return {}

    # 3. 逐表解析
    result: List[TableModel] = []

    for cn_name, en_name in tables_meta:
        try:
            df = pd.read_excel(xls, sheet_name=cn_name, header=4, dtype=str)
        except Exception:
            continue

        df = df.dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        # 根据启用标记列过滤：只处理标记为 1 的行
        if filter_enabled and filter_column in df.columns:
            df = df[df[filter_column].astype(str).str.strip() == "1"]

        if df.empty:
            continue

        col_groups = _detect_col_groups(list(df.columns))
        n_groups = _count_groups(col_groups)
        group_labels = _read_group_labels(cn_name)

        def _get_col(base: str, gidx: int) -> str:
            cols = col_groups.get(base, [base])
            return cols[min(gidx, len(cols) - 1)]

        # 目标字段列始终取第一组
        tgt_field_col = col_groups.get("字段英文名", ["字段英文名"])[0]
        tgt_label_col = col_groups.get("字段中文名", ["字段中文名"])[0]

        mapping_groups: List[MappingGroup] = []

        for g in range(n_groups):
            src_table_col = _get_col("源系统表英文名称", g)
            mapping_col = _get_col("映射规则", g)

            # 源字段英文名
            src_field_cols = col_groups.get("字段英文名", ["字段英文名"])
            src_field_col = src_field_cols[min(g + 1, len(src_field_cols) - 1)] if len(src_field_cols) > 1 else src_field_cols[0]

            # 源字段中文名
            src_cn_cols = col_groups.get("字段中文名", ["字段中文名"])
            src_cn_col = src_cn_cols[min(g + 1, len(src_cn_cols) - 1)] if len(src_cn_cols) > 1 else src_cn_cols[0]

            # FROM 子句
            cond_col = _get_col("关联条件", g)
            from_clause = ""
            if cond_col in df.columns:
                cvals = df[cond_col].dropna().astype(str).str.strip()
                cvals = cvals[cvals != ""]
                if not cvals.empty:
                    # 清理序号前缀（如 "1.表" -> "表"）
                    from_clause = _clean_from_clause(cvals.iloc[0])

            # 默认别名
            default_alias = en_name
            if from_clause:
                fl = re.sub(r"\s*--.*$", "", from_clause.split("\n")[0].strip()).strip()
                parts = fl.split(None, 2)
                if parts:
                    default_alias = parts[1] if len(parts) > 1 else parts[0]
            else:
                if src_table_col in df.columns:
                    for val in df[src_table_col].dropna().astype(str):
                        tn, al = _parse_source_table(val)
                        if tn:
                            default_alias = al or tn
                            from_clause = tn
                            break

            # 组标签
            cond_cols_list = col_groups.get("关联条件", [])
            label = ""
            if g < len(cond_cols_list) and cond_cols_list[g] in df.columns:
                pos = list(df.columns).index(cond_cols_list[g])
                label = group_labels.get(pos, "")

            # 逐行解析字段
            fields: List[FieldMapping] = []
            code_mapping_fields = []  # 收集码值映射字段信息
            
            for i in range(len(df)):
                tgt = str(df[tgt_field_col].iloc[i]).strip()
                if not tgt or tgt == "nan":
                    continue

                tgt_label = str(df[tgt_label_col].iloc[i]).strip() if tgt_label_col in df.columns else ""
                if tgt_label == "nan":
                    tgt_label = ""

                row_src_table = str(df[src_table_col].iloc[i]).strip() if src_table_col in df.columns else ""
                if row_src_table == "nan":
                    row_src_table = ""

                raw_rule = str(df[mapping_col].iloc[i]).strip() if mapping_col in df.columns else ""
                if raw_rule == "nan":
                    raw_rule = ""

                raw_src_field = str(df[src_field_col].iloc[i]).strip() if src_field_col in df.columns else ""
                if raw_src_field == "nan":
                    raw_src_field = ""

                src_label = str(df[src_cn_col].iloc[i]).strip() if src_cn_col in df.columns else ""
                if src_label in ("nan", "固定"):
                    src_label = ""
                else:
                    src_label = src_label.split("\n")[0].strip()

                _, row_alias = _parse_source_table(row_src_table)
                alias = row_alias or default_alias

                expr, comment, warning = _normalize_mapping(raw_rule, row_src_table, raw_src_field, alias, tgt)

                # 检查是否为码值映射（支持包含关键词的规则）
                rule_normalized = raw_rule.strip() if raw_rule else ""
                code_mapping_keywords = ("码值", "码值映射", "公共码值", "中文转码值")
                is_code_mapping = any(keyword in rule_normalized for keyword in code_mapping_keywords)
                
                if is_code_mapping and raw_src_field and raw_src_field.strip() not in ("", "nan", "固定"):
                    # 收集码值映射字段信息，用于后续生成 LEFT JOIN
                    field_name = raw_src_field.strip().split("\n")[0].strip()
                    source_table_name, source_table_alias = _parse_source_table(row_src_table)
                    code_mapping_fields.append({
                        'field_name': field_name,
                        'source_table': source_table_name or "",
                        'source_table_alias': source_table_alias or alias,
                        'target_field': tgt,  # 目标字段名，用于 JOIN 条件
                    })

                if src_label and not comment:
                    comment = f"-- {src_label}"
                elif src_label and comment:
                    comment = f"-- {src_label} | {comment.lstrip('- ')}"

                fields.append(FieldMapping(
                    target=tgt,
                    target_label=tgt_label,
                    expr=expr,
                    source_table=row_src_table,
                    source_field=raw_src_field,
                    source_label=src_label,
                    mapping_rule_raw=raw_rule,
                    comment=comment,
                    warning=warning,
                    is_code_mapping=is_code_mapping,
                ))

            if not fields:
                continue

            # 生成码值映射的 LEFT JOIN 列表
            code_mapping_joins: List[CodeMappingJoin] = []
            for idx, cm_info in enumerate(code_mapping_fields, start=1):
                alias = f"V{idx}"
                # 为对应的 FieldMapping 设置别名
                # 需要同时匹配 source_field 和 target_field，避免同一源字段的不同目标字段被错误覆盖
                for f in fields:
                    if (f.is_code_mapping and 
                        f.source_field.strip().split("\n")[0].strip() == cm_info['field_name'] and
                        f.target == cm_info['target_field']):
                        f.code_mapping_alias = alias
                
                code_mapping_joins.append(CodeMappingJoin(
                    alias=alias,
                    source_field=cm_info['field_name'],
                    source_table=cm_info['source_table'],
                    target_table=en_name,
                    target_field=cm_info['target_field'],  # 目标字段名
                    source_table_alias=cm_info['source_table_alias'],
                ))

            mapping_groups.append(MappingGroup(
                name=label,
                group_index=g,
                from_clause=from_clause,
                fields=fields,
                code_mapping_joins=code_mapping_joins,
            ))

        if mapping_groups:
            result.append(TableModel(
                table_name=en_name,
                table_label=cn_name,
                groups=mapping_groups,
            ))

    return result


def detect_excel_format(file_path: str) -> dict:
    """
    检测 Excel 文件格式
    
    Args:
        file_path: Excel 文件路径
        
    Returns:
        {
            "format": "default" | "unknown",
            "has_catalog": bool,
            "sheet_count": int,
        }
    """
    engine = "xlrd" if file_path.lower().endswith(".xls") else "openpyxl"
    try:
        xls = pd.ExcelFile(file_path, engine=engine)
        sheets = xls.sheet_names
        
        # 检测是否有目录表
        has_catalog = "目录" in sheets
        
        # 检测格式
        if has_catalog:
            return {
                "format": "default",
                "has_catalog": True,
                "sheet_count": len(sheets),
            }
        else:
            return {
                "format": "unknown",
                "has_catalog": False,
                "sheet_count": len(sheets),
            }
    except Exception as e:
        return {
            "format": "error",
            "has_catalog": False,
            "sheet_count": 0,
            "error": str(e),
        }


class ExcelParser:
    """Excel 解析器
    
    用于解析数据模型 Excel 文件，提取表结构、字段映射规则等信息。
    
    Example:
        >>> from excel2everything import Parser
        >>> parser = Parser(format="default")
        >>> model = parser.parse("model.xlsx")
        >>> print(f"表名: {model.table_name}")
    """
    
    def __init__(self, format: str = "default"):
        """
        初始化解析器
        
        Args:
            format: Excel 格式类型，目前支持 "default"
        """
        self.format = format
    
    def parse(self, file_path: str, only_tables: List[str] = None) -> List[TableModel]:
        """
        解析 Excel 文件
        
        Args:
            file_path: Excel 文件路径
            only_tables: 只处理的表名列表（可选）
            
        Returns:
            List[TableModel] 解析后的表模型列表
        """
        if self.format not in ("default", "standard"):
            raise ValueError(f"不支持的格式: {self.format}")
        
        return extract_from_excel(file_path, only_tables=only_tables)
    
    def parse_single(self, file_path: str, table_name: str) -> Optional[TableModel]:
        """
        解析单个表
        
        Args:
            file_path: Excel 文件路径
            table_name: 表英文名
            
        Returns:
            TableModel 或 None
        """
        results = self.parse(file_path, only_tables=[table_name])
        return results[0] if results else None
    
    def detect_format(self, file_path: str) -> dict:
        """
        检测 Excel 文件格式
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            格式信息字典
        """
        return detect_excel_format(file_path)
