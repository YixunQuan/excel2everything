# -*- coding: utf-8 -*-
"""
DDL 生成器 - 从数据字典生成建表语句

支持多种数据库:
- Oracle
- MySQL
- PostgreSQL
- Hive
- Inceptor (星环)
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from jinja2 import Environment, FileSystemLoader, select_autoescape

from excel2everything.models import TableDDL, ColumnDefinition

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


# 值域类型到 Oracle 数据类型的映射
VALUE_DOMAIN_TYPE_MAP = {
    # 日期类
    "日期类": "DATE",
    "日期": "DATE",
    "datetime": "DATE",
    "date": "DATE",
    
    # 数值类
    "数值类": "NUMBER(18,6)",
    "金额类": "NUMBER(18,2)",
    "金额": "NUMBER(18,2)",
    "数量": "NUMBER(18,0)",
    "比率": "NUMBER(10,6)",
    "百分比": "NUMBER(10,6)",
    "整数": "NUMBER(18,0)",
    "小数": "NUMBER(18,6)",
    "number": "NUMBER(18,6)",
    
    # 字符串类
    "字符类": "VARCHAR2(200)",
    "字符串": "VARCHAR2(200)",
    "代码类": "VARCHAR2(50)",
    "编码": "VARCHAR2(50)",
    "代码": "VARCHAR2(50)",
    "标识": "VARCHAR2(50)",
    "名称": "VARCHAR2(200)",
    "描述": "VARCHAR2(500)",
    "备注": "VARCHAR2(500)",
    "varchar": "VARCHAR2(200)",
    "varchar2": "VARCHAR2(200)",
    "string": "VARCHAR2(200)",
    
    # 大文本
    "文本类": "CLOB",
    "大文本": "CLOB",
    "clob": "CLOB",
    
    # 标志类
    "标志类": "VARCHAR2(10)",
    "标志": "VARCHAR2(10)",
    "是否": "VARCHAR2(10)",
    "flag": "VARCHAR2(10)",
}


def infer_data_type(
    value_domain: str,
    field_name: str = "",
    field_label: str = ""
) -> str:
    """
    根据值域类型推断数据类型
    
    Args:
        value_domain: 值域类型（如 "日期类"、"金额类"）
        field_name: 字段名（用于额外推断）
        field_label: 字段标签（用于额外推断）
        
    Returns:
        Oracle 数据类型
    """
    # 直接匹配值域类型
    if value_domain:
        vdt = value_domain.strip()
        if vdt in VALUE_DOMAIN_TYPE_MAP:
            return VALUE_DOMAIN_TYPE_MAP[vdt]
        
        # 部分匹配
        vdt_lower = vdt.lower()
        for key, dtype in VALUE_DOMAIN_TYPE_MAP.items():
            if key in vdt_lower or vdt_lower in key.lower():
                return dtype
    
    # 根据字段名推断
    if field_name:
        name_upper = field_name.upper()
        if "DT" in name_upper or "DATE" in name_upper:
            return "DATE"
        if "AMT" in name_upper or "AMOUNT" in name_upper:
            return "NUMBER(18,2)"
        if "FLAG" in name_upper or "IND" in name_upper:
            return "VARCHAR2(10)"
        if "NO" in name_upper or "NUM" in name_upper:
            return "VARCHAR2(50)"
        if "NAME" in name_upper or "DESC" in name_upper:
            return "VARCHAR2(200)"
        if "ID" in name_upper:
            return "VARCHAR2(50)"
    
    # 根据字段标签推断
    if field_label:
        label = field_label
        if "日期" in label:
            return "DATE"
        if "金额" in label or "余额" in label:
            return "NUMBER(18,2)"
        if "数量" in label or "笔数" in label:
            return "NUMBER(18,0)"
        if "比率" in label or "比例" in label:
            return "NUMBER(10,6)"
        if "名称" in label:
            return "VARCHAR2(200)"
        if "标志" in label or "是否" in label:
            return "VARCHAR2(10)"
        if "代码" in label or "编码" in label:
            return "VARCHAR2(50)"
        if "描述" in label or "备注" in label:
            return "VARCHAR2(500)"
    
    # 默认
    return "VARCHAR2(200)"


class DDLGenerator:
    """DDL 生成器"""
    
    def __init__(self, dialect: str = "oracle"):
        """
        初始化 DDL 生成器
        
        Args:
            dialect: 数据库方言 (oracle/mysql/postgresql/hive/inceptor)
        """
        self.dialect = dialect.lower()
        self.template_dir = os.path.join(TEMPLATES_DIR, self.dialect)
        
        if not os.path.exists(self.template_dir):
            raise ValueError(f"不支持的数据库方言: {dialect}")
        
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape([]),
            keep_trailing_newline=True,
            trim_blocks=False,
            lstrip_blocks=False,
        )
    
    def generate(self, model: TableDDL, drop_if_exists: bool = False) -> str:
        """
        生成 DDL 语句
        
        Args:
            model: 表定义模型
            drop_if_exists: 是否生成 DROP TABLE 语句
            
        Returns:
            DDL SQL 语句
        """
        # 设置 drop 标志
        model_dict = model.model_dump()
        model_dict["drop_if_exists"] = drop_if_exists
        
        # 渲染模板
        template = self.env.get_template("ddl.sql.j2")
        return template.render(model=model_dict)
    
    def generate_all(self, models: List[TableDDL], drop_if_exists: bool = False) -> Dict[str, str]:
        """
        批量生成 DDL
        
        Args:
            models: 表定义列表
            drop_if_exists: 是否生成 DROP TABLE 语句
            
        Returns:
            {table_name: ddl_sql} 字典
        """
        return {
            model.table_name: self.generate(model, drop_if_exists)
            for model in models
        }


def extract_ddl_from_excel(
    file_path: str,
    only_tables: List[str] = None,
    filter_column: str = "启用标记",
    filter_value: str = "1",
) -> List[TableDDL]:
    """
    从 Excel 文件中提取表定义用于生成 DDL
    
    Args:
        file_path: Excel 文件路径
        only_tables: 只处理的表名列表
        filter_column: 过滤列名
        filter_value: 过滤值
        
    Returns:
        List[TableDDL] 表定义列表
    """
    import pandas as pd
    
    engine = "xlrd" if file_path.lower().endswith(".xls") else "openpyxl"
    xls = pd.ExcelFile(file_path, engine=engine)
    
    # 读取目录
    catalog = pd.read_excel(xls, sheet_name="目录", dtype=str)
    tables_meta = []
    for _, row in catalog.iterrows():
        cn = str(row.get("表中文名", "")).strip()
        en = str(row.get("表英文名", "")).strip()
        if cn and cn != "nan" and en and en != "nan":
            tables_meta.append((cn, en))
    
    if only_tables:
        tables_meta = [(cn, en) for cn, en in tables_meta if en in only_tables]
    
    result = []
    
    for cn_name, en_name in tables_meta:
        try:
            df = pd.read_excel(xls, sheet_name=cn_name, header=4, dtype=str)
        except Exception:
            continue
        
        df = df.dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]
        
        # 应用过滤
        if filter_column and filter_column in df.columns:
            df = df[df[filter_column].astype(str).str.strip() == filter_value]
        if df.empty:
            continue
        
        # 解析字段
        columns = []
        primary_keys = []
        
        for _, row in df.iterrows():
            field_name = str(row.get("字段英文名", "")).strip()
            if not field_name or field_name == "nan":
                continue
            
            field_label = str(row.get("字段中文名", "")).strip()
            if field_label == "nan":
                field_label = ""
            
            value_domain = str(row.get("值域类型", "")).strip()
            if value_domain == "nan":
                value_domain = ""
            
            value_constraint = str(row.get("值域约束", "")).strip()
            if value_constraint == "nan":
                value_constraint = ""
            
            is_pk = str(row.get("是否主键", "")).strip().upper() in ("Y", "YES", "1", "是")
            
            # 推断数据类型
            data_type = infer_data_type(value_domain, field_name, field_label)
            
            col = ColumnDefinition(
                name=field_name.upper(),
                label=field_label,
                data_type=data_type,
                is_primary_key=is_pk,
                is_nullable=not is_pk,
                value_domain=value_domain,
                value_constraint=value_constraint,
                comment=field_label,
            )
            columns.append(col)
            
            if is_pk:
                primary_keys.append(field_name.upper())
        
        if not columns:
            continue
        
        table_ddl = TableDDL(
            table_name=en_name.upper(),
            table_label=cn_name,
            columns=columns,
            primary_key=primary_keys,
            table_comment=cn_name,
        )
        result.append(table_ddl)
    
    return result


# 支持的数据库列表
SUPPORTED_DIALECTS = ["oracle", "mysql", "postgresql", "hive", "inceptor", "oceanbase"]


def extract_ddl_from_table_list(
    file_path: str,
) -> List[TableDDL]:
    """
    从"表结构清单"格式的 Excel 文件中提取表定义（信贷系统格式）。
    
    该格式的特征:
    - 有"表结构清单"工作表作为目录（第 1 列为表英文名，第 2 列为表中文名）
    - 每个表有独立的 sheet，行 0 是标题行，行 1 是列头
      (表名, 列名, 字段类型, 是否为空, 字段注释, ...)
    """
    import pandas as pd

    engine = "xlrd" if file_path.lower().endswith(".xls") else "openpyxl"
    xls = pd.ExcelFile(file_path, engine=engine)

    # 检查是否存在"表结构清单"工作表
    if "表结构清单" not in xls.sheet_names:
        raise ValueError("未找到 表结构清单 工作表")

    # 读取目录 —— 从第 2 行开始（跳过标题行）
    catalog_df = pd.read_excel(xls, sheet_name="表结构清单", dtype=str, header=None)

    # 找到列头行（包含"数据表"关键字的行）
    header_row = None
    for idx in range(min(5, len(catalog_df))):
        row_vals = catalog_df.iloc[idx].astype(str).tolist()
        if any("数据表" in str(v) for v in row_vals):
            header_row = idx
            break

    if header_row is None:
        raise ValueError("表结构清单中未找到列头行")

    # 跳过标题和空行，从 header_row+1 开始取数据
    # 列 1 = 表英文名, 列 2 = 中文名/描述
    tables_meta = []
    for idx in range(header_row + 1, len(catalog_df)):
        en_name = str(catalog_df.iloc[idx, 1]).strip()
        cn_name = str(catalog_df.iloc[idx, 2]).strip()
        if en_name and en_name != "nan":
            if cn_name == "nan":
                cn_name = en_name
            # 取分号前的部分作为中文名
            cn_name = cn_name.split(";")[0].strip()
            tables_meta.append((en_name, cn_name))

    result = []
    skip_sheets = {"修订记录", "表结构清单", "码值映射清单"}

    for en_name, cn_name in tables_meta:
        # 查找对应的 sheet（大小写不敏感匹配）
        sheet_name = None
        for sn in xls.sheet_names:
            if sn.lower() == en_name.lower():
                sheet_name = sn
                break
        if not sheet_name or sheet_name in skip_sheets:
            continue

        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str, header=None)
        except Exception:
            continue

        # 找列头行（包含"列名"关键字的行）
        col_header_row = None
        for idx in range(min(5, len(df))):
            row_vals = [str(v).strip() for v in df.iloc[idx].tolist()]
            if "列名" in row_vals:
                col_header_row = idx
                break

        if col_header_row is None:
            continue

        # 解析列头位置
        headers = [str(v).strip() for v in df.iloc[col_header_row].tolist()]
        col_idx = {}
        for i, h in enumerate(headers):
            if h == "列名":
                col_idx["name"] = i
            elif h == "字段类型":
                col_idx["type"] = i
            elif h == "是否为空":
                col_idx["nullable"] = i
            elif h == "字段注释":
                col_idx["comment"] = i

        if "name" not in col_idx:
            continue

        columns = []
        primary_keys = []
        for idx in range(col_header_row + 1, len(df)):
            name = str(df.iloc[idx, col_idx["name"]]).strip()
            if not name or name == "nan":
                continue

            data_type = str(df.iloc[idx, col_idx.get("type", 0)]).strip() if "type" in col_idx else "VARCHAR2(200)"
            if data_type == "nan":
                data_type = "VARCHAR2(200)"

            nullable_val = str(df.iloc[idx, col_idx.get("nullable", 0)]).strip() if "nullable" in col_idx else "YES"
            is_nullable = nullable_val.upper() != "NO"
            is_pk = nullable_val.upper() == "NO"  # 简单推断：NOT NULL 可能是主键

            comment = str(df.iloc[idx, col_idx.get("comment", 0)]).strip() if "comment" in col_idx else ""
            if comment == "nan":
                comment = ""

            col = ColumnDefinition(
                name=name.upper(),
                label=comment,
                data_type=data_type,
                is_primary_key=False,
                is_nullable=is_nullable,
                comment=comment,
            )
            columns.append(col)

            if is_pk:
                primary_keys.append(name.upper())

        if not columns:
            continue

        table_ddl = TableDDL(
            table_name=en_name.upper(),
            table_label=cn_name,
            columns=columns,
            primary_key=primary_keys,
            table_comment=cn_name,
        )
        result.append(table_ddl)

    return result


def get_dialect_display_name(dialect: str) -> str:
    """获取数据库方言的显示名称"""
    names = {
        "oracle": "Oracle",
        "mysql": "MySQL",
        "postgresql": "PostgreSQL",
        "hive": "Apache Hive",
        "inceptor": "星环 Inceptor",
        "oceanbase": "OceanBase",
    }
    return names.get(dialect.lower(), dialect)
