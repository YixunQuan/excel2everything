# -*- coding: utf-8 -*-
"""
DataForge Analyzer - 依赖分析器模块

分析数据模型中的表依赖关系、字段依赖关系。

Example:
    >>> from excel2everything.analyzer import DependencyAnalyzer
    >>> analyzer = DependencyAnalyzer()
    >>> deps = analyzer.analyze(model)
"""

from excel2everything.analyzer.dependency import (
    analyze_table,
    analyze_all,
    build_reverse_index,
    build_summary_stats,
    DependencyAnalyzer,
    TableDependency,
    GroupDependency,
    FieldDependency,
    SourceTableRef,
)

__all__ = [
    "analyze_table",
    "analyze_all",
    "build_reverse_index",
    "build_summary_stats",
    "DependencyAnalyzer",
    "TableDependency",
    "GroupDependency",
    "FieldDependency",
    "SourceTableRef",
]
