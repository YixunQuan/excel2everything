# -*- coding: utf-8 -*-
"""
DataForge Parser - Excel 解析器模块

解析 Excel 数据模型文件，提取表结构、字段映射规则等信息。

Example:
    >>> from dataforge.parser import ExcelParser
    >>> parser = ExcelParser(format="default")
    >>> model = parser.parse("model.xlsx")
"""

from dataforge.parser.excel import (
    extract_from_excel,
    detect_excel_format,
    ExcelParser,
)
from dataforge.parser.rule_engine import (
    normalize_mapping_rule,
    RuleEngine,
    MappingRuleEngine,
    RuleContext,
    RuleResult,
    apply_rule,
    get_rule_engine,
)

__all__ = [
    "extract_from_excel",
    "detect_excel_format",
    "ExcelParser",
    "normalize_mapping_rule",
    "RuleEngine",
    "MappingRuleEngine",
    "RuleContext",
    "RuleResult",
    "apply_rule",
    "get_rule_engine",
]
