# -*- coding: utf-8 -*-
"""
配置数据模型 - Pydantic 模型定义
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DetectionConfig(BaseModel):
    """格式识别特征配置"""
    catalog_sheet: Optional[str] = None
    required_columns: List[str] = Field(default_factory=list)
    optional_columns: List[str] = Field(default_factory=list)


class CatalogConfig(BaseModel):
    """目录表配置"""
    sheet_name: str = "目录"
    columns: Dict[str, str] = Field(default_factory=dict)
    skip_rows: int = 0


class DataColumnMapping(BaseModel):
    """数据表列名映射"""
    target_field: str = "字段英文名"
    target_label: str = "字段中文名"
    source_table: str = "源系统表英文名称"
    source_field: str = "字段英文名"
    source_label: str = "字段中文名"
    mapping_rule: str = "映射规则"
    condition: str = "关联条件"
    filter: Optional[str] = None
    remark: Optional[str] = None


class DataSheetConfig(BaseModel):
    """数据表配置"""
    header_row: int = 4
    data_start_row: int = 5
    filter_column: Optional[str] = None
    filter_value: Optional[str] = None
    columns: DataColumnMapping = Field(default_factory=DataColumnMapping)


class GroupLabelsConfig(BaseModel):
    """组标签检测配置"""
    source_row: int = 3
    keyword: str = "来源表"


class GroupDetectionConfig(BaseModel):
    """映射组检测配置"""
    method: str = "column_suffix"  # column_suffix | explicit_column | single
    base_columns: List[str] = Field(default_factory=lambda: ["关联条件", "源系统表英文名称", "映射规则"])


class ExcelFormatConfig(BaseModel):
    """Excel 格式完整配置"""
    name: str
    description: str = ""
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    data_sheet: DataSheetConfig = Field(default_factory=DataSheetConfig)
    group_labels: GroupLabelsConfig = Field(default_factory=GroupLabelsConfig)
    group_detection: GroupDetectionConfig = Field(default_factory=GroupDetectionConfig)


class MappingRule(BaseModel):
    """单条映射规则"""
    name: str
    pattern: str
    action: str
    description: str = ""
    condition: Optional[Dict[str, Any]] = None


class MappingRuleConfig(BaseModel):
    """映射规则配置"""
    name: str
    description: str = ""
    rules: List[MappingRule] = Field(default_factory=list)


class DefaultsConfig(BaseModel):
    """默认配置"""
    excel_format: str = "regulatory"
    mapping_rules: str = "default"
    database_dialect: str = "inceptor"


class AutoDetectionConfig(BaseModel):
    """智能识别配置"""
    enabled: bool = True
    fallback_format: str = "generic"


class OutputConfig(BaseModel):
    """输出配置"""
    encoding: str = "utf-8"
    include_comments: bool = True
    procedure_template: str = "inceptor"


class UIConfig(BaseModel):
    """界面配置"""
    theme: str = "dark"
    language: str = "zh-CN"


class SettingsConfig(BaseModel):
    """全局设置"""
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    auto_detection: AutoDetectionConfig = Field(default_factory=AutoDetectionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
