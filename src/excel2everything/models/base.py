# -*- coding: utf-8 -*-
"""
DataForge Core - 数据模型定义

结构化中间表示 (IR) 数据模型。

所有从 Excel / CSV / YAML 解析出来的映射信息，
都先转为这里定义的 Pydantic 模型，再交给渲染器生成 SQL。

Example:
    >>> from excel2everything.models import TableModel, FieldMapping
    >>> field = FieldMapping(target="CUST_ID", expr="T01.CUST_ID")
    >>> print(field.target)
    CUST_ID
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, field_validator


class FieldMapping(BaseModel):
    """单个字段的映射定义"""
    target: str                          # 目标表字段英文名
    target_label: str = ""               # 目标表字段中文名
    expr: str = "NULL"                   # SQL 表达式
    source_table: str = ""               # 源表名（仅用于展示）
    source_field: str = ""               # 源字段名（仅用于展示）
    source_label: str = ""               # 源字段中文名
    mapping_rule_raw: str = ""           # Excel 中原始映射规则文本
    comment: str = ""                    # 行尾注释
    warning: str = ""                    # 解析告警（如 fallback）
    is_code_mapping: bool = False        # 是否为码值映射
    code_mapping_alias: str = ""         # 码值映射表的别名（如 V1, V2）

    @field_validator("target", mode="before")
    @classmethod
    def strip_target(cls, v):
        return str(v).strip() if v else ""


class ColumnDefinition(BaseModel):
    """DDL 字段定义 - 用于生成建表语句"""
    name: str                            # 字段英文名
    label: str = ""                      # 字段中文名
    data_type: str = "VARCHAR2(100)"     # 数据类型
    is_primary_key: bool = False         # 是否主键
    is_nullable: bool = True             # 是否允许空值
    default_value: Optional[str] = None  # 默认值
    comment: str = ""                    # 字段注释
    value_domain: str = ""               # 值域类型（从 Excel 解析）
    value_constraint: str = ""           # 值域约束
    
    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v):
        return str(v).strip().upper() if v else ""


class TableDDL(BaseModel):
    """DDL 表定义 - 用于生成建表语句"""
    table_name: str                      # 表英文名
    table_label: str = ""                # 表中文名
    columns: List[ColumnDefinition] = [] # 字段列表
    primary_key: List[str] = []          # 主键字段列表
    table_comment: str = ""              # 表注释
    tablespace: str = ""                 # 表空间（Oracle 使用）
    partition_by: str = ""               # 分区字段
    
    @property
    def column_count(self) -> int:
        return len(self.columns)
    
    def get_primary_key_columns(self) -> List[ColumnDefinition]:
        """获取主键字段列表"""
        return [c for c in self.columns if c.is_primary_key]


class CodeMappingJoin(BaseModel):
    """码值映射的 LEFT JOIN 定义"""
    alias: str                           # 别名（如 V1, V2）
    source_field: str                    # 源字段名
    source_table: str                    # 源表名
    target_table: str                    # 目标表名
    target_field: str                    # 目标字段名（用于 JOIN 条件）
    source_table_alias: str              # 源表别名


class MappingGroup(BaseModel):
    """一个源系统组的映射（对应一条 INSERT INTO ... SELECT ... FROM）"""
    name: str = ""                       # 组名（如 "来源表1-核心系统个人客户"）
    group_index: int = 0                 # 组序号 (0-based)
    from_clause: str = ""                # FROM + JOIN 子句
    fields: List[FieldMapping] = []      # 字段映射列表
    code_mapping_joins: List[CodeMappingJoin] = []  # 码值映射的 LEFT JOIN 列表


class TableModel(BaseModel):
    """一个目标表的完整映射模型"""
    table_name: str                      # 目标表英文名 (如 M_CUST_IND_INFO)
    table_label: str = ""                # 目标表中文名 (如 个人客户信息)
    load_strategy: str = "full_snapshot" # 加载策略
    groups: List[MappingGroup] = []      # 多个源系统组

    @property
    def target_fields(self) -> List[str]:
        """目标表的字段列表（取第一组的 target 字段）"""
        if self.groups and self.groups[0].fields:
            return [f.target for f in self.groups[0].fields if f.target]
        return []

    @property
    def total_fields(self) -> int:
        if self.groups:
            return len(self.groups[0].fields)
        return 0

    @property
    def warnings(self) -> List[dict]:
        """汇总所有告警"""
        result = []
        for g in self.groups:
            for f in g.fields:
                if f.warning:
                    result.append({
                        "group": g.name or f"组{g.group_index + 1}",
                        "field": f.target,
                        "warning": f.warning,
                    })
        return result


class ProjectConfig(BaseModel):
    """项目级配置"""
    name: str = "excel2sql Project"
    template: str = "inceptor"           # 使用的模板名称
    global_vars: dict = {}               # 全局变量（如 lgl_rep_id）
    tables: List[TableModel] = []
