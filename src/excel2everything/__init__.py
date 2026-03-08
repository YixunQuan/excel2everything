# -*- coding: utf-8 -*-
"""
Excel2Everything - 模板驱动的 Excel 转换工具

核心思路：一次解析，无限输出
    Excel → [Parser] → IR Model → [Template] → Anything

核心功能:
    - Excel 解析：提取表结构、字段映射规则
    - 模板驱动：基于 Jinja2 自定义输出格式
    - 内置模板：SQL、DDL、存储过程等
    - 可扩展：添加新输出格式只需编写模板

内置支持:
    - Oracle, MySQL, PostgreSQL, Hive, OceanBase

Example:
    >>> from excel2everything import Parser, Generator
    >>> 
    >>> # 解析 Excel
    >>> parser = Parser()
    >>> model = parser.parse("model.xlsx")
    >>> 
    >>> # 使用模板生成 SQL
    >>> generator = Generator(dialect="oracle")
    >>> sql = generator.generate_procedure(model)

版本历史:
    0.1.0 - 初始版本
"""

__version__ = "0.1.0"
__author__ = "DataForge Team"
__license__ = "MIT"

# 导入主要组件
from excel2everything.models import (
    TableModel,
    FieldMapping,
    MappingGroup,
    ColumnDefinition,
    TableDDL,
    ProjectConfig,
)

from excel2everything.parser import (
    ExcelParser,
    extract_from_excel,
    RuleEngine,
)

from excel2everything.generator import (
    SQLGenerator,
    DDLGenerator,
    SUPPORTED_DIALECTS,
)

from excel2everything.analyzer import (
    DependencyAnalyzer,
    analyze_all,
)

from excel2everything.validator import (
    SQLValidator,
    validate_insert_sql,
    validate_sql,
)

# 便捷别名
Parser = ExcelParser
Generator = SQLGenerator
Validator = SQLValidator
Analyzer = DependencyAnalyzer

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__license__",
    
    # 数据模型
    "TableModel",
    "FieldMapping",
    "MappingGroup",
    "ColumnDefinition",
    "TableDDL",
    "ProjectConfig",
    
    # 解析器
    "Parser",
    "ExcelParser",
    "extract_from_excel",
    "RuleEngine",
    
    # 生成器
    "Generator",
    "SQLGenerator",
    "DDLGenerator",
    "SUPPORTED_DIALECTS",
    
    # 分析器
    "Analyzer",
    "DependencyAnalyzer",
    "analyze_all",
    
    # 验证器
    "Validator",
    "SQLValidator",
    "validate_insert_sql",
    "validate_sql",
]
