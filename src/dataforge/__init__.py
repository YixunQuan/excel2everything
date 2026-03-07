# -*- coding: utf-8 -*-
"""
DataForge Core - 企业级数据开发工具链核心引擎

DataForge 是一个数据开发工具链，用于将数据模型转换为可执行的 SQL 代码。

核心功能:
    - Excel 数据模型解析
    - SQL 存储过程生成
    - DDL 建表语句生成
    - 表依赖关系分析
    - SQL 语法验证
    - 多数据库方言支持

支持的数据库:
    - Oracle
    - MySQL
    - PostgreSQL
    - Hive
    - Inceptor (星环)
    - OceanBase

Example:
    >>> from dataforge import Parser, Generator, Validator
    >>> 
    >>> # 解析 Excel
    >>> parser = Parser(format="default")
    >>> model = parser.parse("model.xlsx")
    >>> 
    >>> # 生成 SQL
    >>> generator = Generator(dialect="oracle")
    >>> sql = generator.generate_procedure(model)
    >>> 
    >>> # 验证 SQL
    >>> validator = Validator()
    >>> report = validator.validate(sql)

版本历史:
    0.1.0 - 初始版本，核心引擎重构
"""

__version__ = "0.1.0"
__author__ = "DataForge Team"
__license__ = "MIT"

# 导入主要组件
from dataforge.models import (
    TableModel,
    FieldMapping,
    MappingGroup,
    ColumnDefinition,
    TableDDL,
    ProjectConfig,
)

from dataforge.parser import (
    ExcelParser,
    extract_from_excel,
    RuleEngine,
)

from dataforge.generator import (
    SQLGenerator,
    DDLGenerator,
    SUPPORTED_DIALECTS,
)

from dataforge.analyzer import (
    DependencyAnalyzer,
    analyze_all,
)

from dataforge.validator import (
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
