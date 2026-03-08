# -*- coding: utf-8 -*-
"""
DataForge Validator - SQL 验证器模块

对生成的 SQL 进行语法检查和质量验证。

Example:
    >>> from excel2everything.validator import SQLValidator, validate_sql
    >>> report = validate_sql(sql_string)
    >>> print(report["has_errors"])
"""

from excel2everything.validator.sql import (
    SQLValidator,
    SQLIssue,
    IssueSeverity,
    validate_insert_sql,
    validate_procedure_sql,
    validate_sql_expression,
    validate_from_clause,
    validate_sql,
)

__all__ = [
    "SQLValidator",
    "SQLIssue",
    "IssueSeverity",
    "validate_insert_sql",
    "validate_procedure_sql",
    "validate_sql_expression",
    "validate_from_clause",
    "validate_sql",
]
