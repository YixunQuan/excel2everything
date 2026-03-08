# -*- coding: utf-8 -*-
"""
DataForge Generator - SQL/DDL 生成器模块

从数据模型生成 INSERT SQL、存储过程、DDL 建表语句。

支持的数据库方言:
    - Oracle
    - MySQL
    - PostgreSQL
    - Hive
    - Inceptor (星环)
    - OceanBase

Example:
    >>> from excel2everything.generator import SQLGenerator, DDLGenerator
    >>> generator = SQLGenerator(dialect="oracle")
    >>> sql = generator.generate_procedure(model)
"""

from excel2everything.generator.sql import (
    SQLGenerator,
    render_insert_sql,
    render_procedure,
)
from excel2everything.generator.ddl import (
    DDLGenerator,
    infer_data_type,
    SUPPORTED_DIALECTS,
)

__all__ = [
    "SQLGenerator",
    "DDLGenerator",
    "render_insert_sql",
    "render_procedure",
    "infer_data_type",
    "SUPPORTED_DIALECTS",
]
