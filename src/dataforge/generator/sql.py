# -*- coding: utf-8 -*-
"""
Jinja2 模板渲染器 — 将 IR 模型渲染为 SQL / 存储过程文本。
"""

import os
import re
from typing import Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape

from dataforge.models import TableModel, MappingGroup

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _get_env(template_name: str) -> Environment:
    """创建 Jinja2 环境，指向 templates/{template_name}/ 目录"""
    tpl_dir = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.isdir(tpl_dir):
        raise FileNotFoundError(f"模板目录不存在: {tpl_dir}")
    return Environment(
        loader=FileSystemLoader(tpl_dir),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def _process_code_mapping_expressions(group: MappingGroup) -> MappingGroup:
    """
    处理码值映射表达式的占位符替换
    将 __CODE_MAPPING_{field}__ 替换为对应的 Vi.detail_code_value
    """
    import copy
    # 创建组的深拷贝，避免修改原始数据
    processed_group = copy.deepcopy(group)
    
    for field in processed_group.fields:
        if field.is_code_mapping and field.code_mapping_alias:
            # 替换占位符为实际的码值映射字段引用
            placeholder = f"__CODE_MAPPING_{field.source_field.strip().split(chr(10))[0].strip()}__"
            field.expr = field.expr.replace(placeholder, f"{field.code_mapping_alias}.detail_code_value")
    
    return processed_group


def _generate_code_mapping_joins(group: MappingGroup) -> str:
    """
    生成码值映射的 LEFT JOIN 语句
    
    根据 CODE_VALUE_MAPPING 表的主键定义，JOIN 条件必须包含：
    - DETAIL_TABLE_NAME_EN: 目标表英文名
    - DETAIL_FIELD_NAME_EN: 目标字段英文名（关键！避免笛卡尔积）
    - SOURCE_TABLE_NAME_EN: 源表英文名
    - SOURCE_FIELD_NAME_EN: 源字段英文名
    - SOURCE_CODE_VALUE: 源码值（来自源表字段）
    
    生成的格式:
    LEFT JOIN CODE_VALUE_MAPPING V1
    ON V1.DETAIL_TABLE_NAME_EN = '{target_table}'
    AND V1.DETAIL_FIELD_NAME_EN = '{target_field}'
    AND V1.SOURCE_TABLE_NAME_EN = '{source_table}'
    AND V1.SOURCE_FIELD_NAME_EN = '{source_field}'
    AND V1.SOURCE_CODE_VALUE = {source_alias}.{source_field}
    """
    if not group.code_mapping_joins:
        return ""
    
    join_parts = []
    for join in group.code_mapping_joins:
        join_sql = (
            f"LEFT JOIN CODE_VALUE_MAPPING {join.alias}\n"
            f"ON {join.alias}.DETAIL_TABLE_NAME_EN = '{join.target_table}'\n"
            f"AND {join.alias}.DETAIL_FIELD_NAME_EN = '{join.target_field}'\n"
            f"AND {join.alias}.SOURCE_TABLE_NAME_EN = '{join.source_table}'\n"
            f"AND {join.alias}.SOURCE_FIELD_NAME_EN = '{join.source_field}'\n"
            f"AND {join.alias}.SOURCE_CODE_VALUE = {join.source_table_alias}.{join.source_field}"
        )
        join_parts.append(join_sql)
    
    return "\n".join(join_parts)


def _clean_common_sql_errors(text: str) -> str:
    """
    清洗 Excel 模型数据中的常见 SQL 语法错误
    
    修复的错误类型:
    1. BEWTEEN -> BETWEEN (拼写错误)
    2. T02.T02. -> T02. (重复表别名)
    3. NVL(0,field,0) -> NVL(field,0) (错误的三参数NVL)
    4. NVL(0,field) -> NVL(field,0) (NVL参数顺序错误)
    5. max(0,expr) -> GREATEST(0,expr) (Oracle聚合函数误用)
    6. 缺少WHERE关键字的过滤条件
    """
    if not text:
        return text
    
    # 修复 BEWTEEN 拼写错误
    text = re.sub(r'\bBEWTEEN\b', 'BETWEEN', text, flags=re.IGNORECASE)
    
    # 修复重复表别名 TXX.TXX. 模式 (如 T02.T02. -> T02.)
    text = re.sub(r'\b(T\d{2})\.\1\.', r'\1.', text)
    
    # 修复错误的 NVL 三参数调用: NVL(0, field, 0) -> NVL(field, 0)
    # 模式: NVL(0, 任意内容, 0) 其中第一个0可能是误写的
    text = re.sub(r'\bNVL\s*\(\s*0\s*,\s*([A-Za-z_][A-Za-z0-9_.]*)\s*,\s*0\s*\)', r'NVL(\1, 0)', text, flags=re.IGNORECASE)
    
    # 修复 NVL(0, field) 参数顺序错误 -> NVL(field, 0)
    text = re.sub(r'\bNVL\s*\(\s*0\s*,\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\)', r'NVL(\1, 0)', text, flags=re.IGNORECASE)
    
    # 修复 max(0, expr) 聚合函数误用 -> GREATEST(0, expr)
    # 注意：只匹配小写的 max，避免修改正确的 MAX(字段) 聚合函数
    text = re.sub(r'\bmax\s*\(\s*0\s*,', 'GREATEST(0,', text)
    text = re.sub(r'\bMAX\s*\(\s*0\s*,', 'GREATEST(0,', text)
    
    return text


def _ensure_semicolon_on_new_line(from_clause: str) -> str:
    """
    确保分号添加在 SQL 语句的真正结尾，而不是注释后面。
    
    问题场景：
    - 输入: "WHERE (SUBSTR(T01.PRODUCTID,1,3)='121' --个人房屋贷款\nOR T01.PRODUCTID='1230010') -- 个人商业用房按揭;"
    - 错误输出: 分号在注释后面，导致语法错误
    - 正确输出: 分号在 SQL 代码结束后单独一行
    
    处理逻辑：
    1. 如果 from_clause 以分号结尾，先移除它
    2. 找到最后一行非注释的代码行
    3. 在 SQL 代码结束后添加换行和分号
    """
    if not from_clause:
        return ";"
    
    # 移除末尾已有的分号（如果有）
    from_clause = from_clause.rstrip().rstrip(';').rstrip()
    
    # 按行分割
    lines = from_clause.split('\n')
    
    # 找到最后一行包含实际 SQL 代码（非纯注释）的行
    last_code_line_idx = -1
    for i, line in enumerate(lines):
        # 提取代码部分（去掉注释）
        code_part = line.split('--')[0].strip()
        if code_part:  # 如果代码部分不为空
            last_code_line_idx = i
    
    if last_code_line_idx >= 0:
        # 在最后一行代码后添加换行和分号
        # 检查最后一行是否已经有分号
        last_line = lines[last_code_line_idx]
        code_part = last_line.split('--')[0].rstrip()
        
        if not code_part.endswith(';'):
            # 在 from_clause 末尾添加换行和分号
            from_clause = from_clause + '\n;'
    else:
        # 所有行都是注释，直接添加分号
        from_clause = from_clause + '\n;'
    
    return from_clause


def _insert_joins_into_from_clause(from_clause: str, join_sql: str) -> str:
    """
    将 LEFT JOIN 语句插入到 FROM 子句中
    
    插入位置规则：
    1. 如果有 "-- 过滤条件" 等注释行，插入到该注释之前
    2. 如果有 WHERE 子句，插入到 WHERE 之前
    3. 否则追加到末尾
    """
    if not join_sql:
        return from_clause
    
    if not from_clause:
        return join_sql
    
    # 按行分割
    lines = from_clause.split('\n')
    
    # 过滤条件相关的注释关键词
    filter_comment_keywords = ('过滤条件', '筛选条件', '查询条件')
    
    # 查找过滤条件注释的位置
    filter_comment_index = -1
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # 检查是否是过滤条件注释行
        if line_stripped.startswith('--'):
            comment_content = line_stripped.lstrip('-').strip()
            if any(kw in comment_content for kw in filter_comment_keywords):
                filter_comment_index = i
                break
    
    # 查找最外层 WHERE 的位置
    where_index = -1
    bracket_count = 0
    
    for i, line in enumerate(lines):
        # 统计括号
        for char in line:
            if char == '(':
                bracket_count += 1
            elif char == ')':
                bracket_count -= 1
        
        # 只有在括号层级为0时才检测 WHERE
        if bracket_count == 0:
            line_content = line.split('--')[0].strip()
            if line_content.upper().startswith('WHERE'):
                where_index = i
                break
    
    # 确定插入位置：优先使用过滤条件注释位置，其次使用 WHERE 位置
    insert_index = -1
    if filter_comment_index >= 0:
        insert_index = filter_comment_index
    elif where_index >= 0:
        insert_index = where_index
    
    if insert_index >= 0:
        # 在指定位置前插入 JOIN
        new_lines = lines[:insert_index]
        # 检查前一行是否为空行，如果不是则添加空行
        if new_lines and new_lines[-1].strip():
            new_lines.append('')
        new_lines.append(join_sql)
        if join_sql.strip():
            new_lines.append('')
        new_lines.extend(lines[insert_index:])
    else:
        # 没有找到合适位置，追加到末尾
        new_lines = lines
        if lines and lines[-1].strip():
            new_lines.append('')
        new_lines.append(join_sql)
    
    return '\n'.join(new_lines)


# [DATA_DT 功能已禁用] 如需恢复，取消以下函数的注释
# def _add_data_dt_to_joins(from_clause: str, skip_main_table: bool = True) -> str:
#     """
#     为所有 LEFT JOIN 的表添加 DATA_DT = V_DATEID 条件。
#     
#     示例转换:
#         FROM T_MAIN T01
#         LEFT JOIN T_DETAIL T02 ON T01.ID = T02.ID
#         
#         转换为:
#         FROM T_MAIN T01
#         LEFT JOIN T_DETAIL T02 ON T01.ID = T02.ID AND T02.DATA_DT = V_DATEID
#     
#     Args:
#         from_clause: 原始 FROM 子句
#         skip_main_table: 是否跳过主表（通常主表在 WHERE 中处理）
#     
#     Returns:
#         增强后的 FROM 子句
#     """
#     if not from_clause or not from_clause.strip():
#         return from_clause
#     
#     # 处理子查询：递归处理括号内的内容
#     def process_subqueries(text: str) -> str:
#         result = []
#         i = 0
#         while i < len(text):
#             if text[i] == '(':
#                 # 找到匹配的右括号
#                 depth = 1
#                 j = i + 1
#                 while j < len(text) and depth > 0:
#                     if text[j] == '(':
#                         depth += 1
#                     elif text[j] == ')':
#                         depth -= 1
#                     j += 1
#                 # 递归处理子查询内容
#                 subquery = text[i+1:j-1]
#                 processed_subquery = _add_data_dt_to_joins(subquery, skip_main_table=False)
#                 result.append('(' + processed_subquery + ')')
#                 i = j
#             else:
#                 result.append(text[i])
#                 i += 1
#         return ''.join(result)
#     
#     # 先处理子查询
#     processed = process_subqueries(from_clause)
#     
#     # 匹配 LEFT JOIN ... alias ON ... 模式
#     # 需要处理多行的情况
#     lines = processed.split('\n')
#     result_lines = []
#     
#     # 正则匹配 LEFT JOIN 表名 别名 ON ...
#     join_pattern = re.compile(
#         r'^(\s*(?:LEFT|RIGHT|INNER|OUTER|CROSS|FULL)\s+)?'
#         r'JOIN\s+'
#         r'([A-Z_][A-Z0-9_.]*)\s+'  # 表名
#         r'([A-Z][A-Z0-9_]*)\s*'     # 别名
#         r'(ON\s+.+)?$',             # ON 条件
#         re.IGNORECASE
#     )
#     
#     # 用于跟踪当前 JOIN 的 ON 条件是否跨行
#     i = 0
#     while i < len(lines):
#         line = lines[i]
#         
#         # 检查是否已经有 DATA_DT 条件（避免重复添加）
#         if re.search(r'\bDATA_DT\s*=\s*[V\']', line, re.IGNORECASE):
#             result_lines.append(line)
#             i += 1
#             continue
#         
#         # 尝试匹配 JOIN 行
#         match = join_pattern.match(line)
#         if match:
#             join_keyword = match.group(1) or ''
#             table_name = match.group(2)
#             alias = match.group(3)
#             on_clause = match.group(4) or ''
#             
#             if on_clause:
#                 # ON 条件在同一行，需要找到 ON 条件的结束位置
#                 # 检查是否需要添加 DATA_DT 条件
#                 if not re.search(rf'\b{alias}\.DATA_DT\b', on_clause, re.IGNORECASE):
#                     # 找到 ON 条件的有效部分（排除注释）
#                     on_content = on_clause.split('--')[0].strip()
#                     if on_content.upper().startswith('ON'):
#                         # 添加 DATA_DT 条件
#                         new_on = on_content + f' AND {alias}.DATA_DT = V_DATEID'
#                         # 保留原注释（如果有）
#                         comment_part = '--' + on_clause.split('--')[1] if '--' in on_clause else ''
#                         new_line = line[:line.find('ON')] + new_on + comment_part
#                         result_lines.append(new_line)
#                     else:
#                         result_lines.append(line)
#                 else:
#                     result_lines.append(line)
#             else:
#                 # ON 条件可能在下一行，需要合并处理
#                 result_lines.append(line)
#                 # 检查下一行是否是 ON 条件
#                 if i + 1 < len(lines):
#                     next_line = lines[i + 1]
#                     if re.match(r'^\s*ON\s+', next_line, re.IGNORECASE):
#                         # 下一行是 ON 条件
#                         if not re.search(rf'\b{alias}\.DATA_DT\b', next_line, re.IGNORECASE):
#                             # 在 ON 条件末尾添加 DATA_DT
#                             on_content = next_line.split('--')[0].rstrip()
#                             comment_part = '--' + next_line.split('--')[1] if '--' in next_line else ''
#                             new_on_line = on_content + f' AND {alias}.DATA_DT = V_DATEID'
#                             if comment_part:
#                                 new_on_line += '  ' + comment_part
#                             result_lines.append(new_on_line)
#                             i += 1  # 跳过下一行
#             i += 1
#             continue
#         
#         # 检查是否是独立的 ON 行（处理 ON 条件跨多行的情况）
#         on_match = re.match(r'^(\s*ON\s+)(.+)$', line, re.IGNORECASE)
#         if on_match:
#             # 这可能是上一行 JOIN 的 ON 条件
#             # 需要检查前一行是否是 LEFT JOIN
#             if result_lines and re.search(r'JOIN\s+[A-Z_][A-Z0-9_.]*\s+[A-Z][A-Z0-9_]*\s*$', result_lines[-1], re.IGNORECASE):
#                 # 提取前一行 JOIN 的别名
#                 prev_match = re.search(r'JOIN\s+[A-Z_][A-Z0-9_.]*\s+([A-Z][A-Z0-9_]*)\s*$', result_lines[-1], re.IGNORECASE)
#                 if prev_match:
#                     alias = prev_match.group(1)
#                     if not re.search(rf'\b{alias}\.DATA_DT\b', line, re.IGNORECASE):
#                         on_content = line.split('--')[0].rstrip()
#                         comment_part = '--' + line.split('--')[1] if '--' in line else ''
#                         new_on_line = on_content + f' AND {alias}.DATA_DT = V_DATEID'
#                         if comment_part:
#                             new_on_line += '  ' + comment_part
#                         result_lines.append(new_on_line)
#                         i += 1
#                         continue
#         
#         result_lines.append(line)
#         i += 1
#     
#     return '\n'.join(result_lines)


def is_valid_mapping_group(group: MappingGroup) -> dict:
    """
    检查映射组是否有效（可以生成有效的 SQL）
    
    有效性条件:
    1. 有字段定义
    2. FROM 子句不为空
    3. 至少有一个非 NULL 的字段表达式
    
    Returns:
        {
            "is_valid": bool,
            "has_fields": bool,
            "has_from": bool,
            "has_valid_data": bool,
            "reasons": list[str],  # 无效原因列表
        }
    """
    result = {
        "is_valid": False,
        "has_fields": False,
        "has_from": False,
        "has_valid_data": False,
        "reasons": [],
    }
    
    # 检查1: 是否有字段
    has_fields = group.fields and len(group.fields) > 0
    result["has_fields"] = has_fields
    if not has_fields:
        result["reasons"].append("没有定义任何字段映射")
    
    # 检查2: FROM 子句是否有效
    has_from = bool(group.from_clause and group.from_clause.strip())
    result["has_from"] = has_from
    if not has_from:
        result["reasons"].append("FROM 子句为空，缺少数据源表")
    
    # 检查3: 是否有非 NULL 的字段表达式
    has_valid_data = False
    if has_fields:
        for f in group.fields:
            expr = f.expr.strip().upper() if f.expr else ""
            # 检查是否是非 NULL 的有效表达式
            if expr and expr != "NULL" and expr != "":
                has_valid_data = True
                break
    
    result["has_valid_data"] = has_valid_data
    if has_fields and not has_valid_data:
        result["reasons"].append("所有字段映射均为 NULL，无实际数据来源")
    
    # 综合判断
    result["is_valid"] = has_fields and has_from and has_valid_data
    
    return result


def render_insert_sql(group: MappingGroup, model: TableModel, add_data_dt: bool = False) -> str:
    """渲染单组映射的 INSERT INTO ... SELECT ... SQL
    
    Args:
        group: 映射组数据
        model: 表模型数据
        add_data_dt: 是否为 LEFT JOIN 添加 DATA_DT = V_DATEID 条件（功能已禁用）
    """
    # 处理码值映射表达式
    processed_group = _process_code_mapping_expressions(group)
    
    # 清洗 FROM 子句中的常见 SQL 语法错误
    if processed_group.from_clause:
        processed_group.from_clause = _clean_common_sql_errors(processed_group.from_clause)
    
    # 清洗字段表达式中的常见 SQL 语法错误
    for field in processed_group.fields:
        if field.expr:
            field.expr = _clean_common_sql_errors(field.expr)
    
    # 生成码值映射的 LEFT JOIN
    code_mapping_joins = _generate_code_mapping_joins(processed_group)
    
    # 将 JOIN 插入到 FROM 子句
    if code_mapping_joins:
        processed_group.from_clause = _insert_joins_into_from_clause(
            processed_group.from_clause, code_mapping_joins
        )
    
    # [DATA_DT 功能已禁用] 为 LEFT JOIN 添加 DATA_DT 条件
    # if add_data_dt:
    #     processed_group.from_clause = _add_data_dt_to_joins(processed_group.from_clause)
    
    # 确保分号添加在正确的位置（避免分号在注释后面导致语法错误）
    processed_group.from_clause = _ensure_semicolon_on_new_line(processed_group.from_clause)
    
    # 计算有效性信息（供模板使用）
    validity = is_valid_mapping_group(processed_group)
    
    env = _get_env("oceanbase")
    tpl = env.get_template("insert.sql.j2")
    return tpl.render(model=model, group=processed_group, validity=validity)


def render_procedure(model: TableModel, add_data_dt: bool = False) -> str:
    """渲染完整的存储过程
    
    Args:
        model: 表模型数据
        add_data_dt: 是否为 LEFT JOIN 添加 DATA_DT = V_DATEID 条件
    """
    env = _get_env("oceanbase")
    tpl = env.get_template("procedure.sql.j2")

    # 先渲染每个组的 INSERT SQL，并计算有效性
    insert_sqls = []
    for g in model.groups:
        validity = is_valid_mapping_group(g)
        sql = render_insert_sql(g, model, add_data_dt=add_data_dt)
        insert_sqls.append({
            "group": g, 
            "sql": sql,
            "is_valid": validity["is_valid"],
            "validity": validity,
        })

    return tpl.render(model=model, insert_sqls=insert_sqls)


def render_all(models: list, template_name: str = "inceptor", add_data_dt: bool = False) -> Dict[str, Dict]:
    """
    批量渲染所有表模型。
    
    Args:
        models: 表模型列表
        template_name: 模板名称
        add_data_dt: 是否为 LEFT JOIN 添加 DATA_DT = V_DATEID 条件

    Returns:
        {
            "M_CUST_IND_INFO": {
                "procedure": "CREATE OR REPLACE ...",
                "inserts": [
                    {"group_name": "...", "sql": "INSERT INTO ...", "is_valid": bool},
                    ...
                ],
                "warnings": [...],
                "invalid_groups": [...],  # 无效映射组列表
                "has_invalid_groups": bool,  # 是否存在无效映射组
            },
            ...
        }
    """
    results = {}
    for model in models:
        inserts = []
        invalid_groups = []
        valid_count = 0
        
        for g in model.groups:
            # 检查映射组有效性
            validity = is_valid_mapping_group(g)
            
            sql = render_insert_sql(g, model, add_data_dt=add_data_dt)
            
            insert_item = {
                "group_name": g.name or f"组{g.group_index + 1}",
                "group_index": g.group_index,
                "sql": sql,
                "is_valid": validity["is_valid"],
                "validity": validity,
                "fields_count": len(g.fields) if g.fields else 0,
            }
            inserts.append(insert_item)
            
            # 记录无效映射组
            if not validity["is_valid"]:
                invalid_groups.append({
                    "group_index": g.group_index,
                    "group_name": g.name or f"组{g.group_index + 1}",
                    "from_clause": g.from_clause,
                    "reasons": validity["reasons"],
                })
            else:
                valid_count += 1

        procedure = render_procedure(model, add_data_dt=add_data_dt)

        results[model.table_name] = {
            "table_label": model.table_label,
            "procedure": procedure,
            "inserts": inserts,
            "total_fields": model.total_fields,
            "total_groups": len(model.groups),
            "valid_groups": valid_count,
            "invalid_groups": invalid_groups,
            "has_invalid_groups": len(invalid_groups) > 0,
            "warnings": model.warnings,
        }

    return results
