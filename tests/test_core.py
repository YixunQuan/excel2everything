# -*- coding: utf-8 -*-
"""
DataForge Core - 基础测试

测试核心模块的导入和基本功能。
"""

import pytest


class TestImport:
    """测试模块导入"""
    
    def test_import_main_package(self):
        """测试主包导入"""
        import excel2everything
        assert hasattr(excel2everything, "__version__")
        assert excel2everything.__version__ == "0.1.0"
    
    def test_import_models(self):
        """测试数据模型导入"""
        from excel2everything.models import (
            TableModel,
            FieldMapping,
            MappingGroup,
            ColumnDefinition,
            TableDDL,
        )
        assert TableModel is not None
        assert FieldMapping is not None
    
    def test_import_parser(self):
        """测试解析器导入"""
        from excel2everything.parser import ExcelParser, RuleEngine
        assert ExcelParser is not None
        assert RuleEngine is not None
    
    def test_import_generator(self):
        """测试生成器导入"""
        from excel2everything.generator import SQLGenerator, DDLGenerator, SUPPORTED_DIALECTS
        assert SQLGenerator is not None
        assert DDLGenerator is not None
        assert len(SUPPORTED_DIALECTS) >= 5
    
    def test_import_analyzer(self):
        """测试分析器导入"""
        from excel2everything.analyzer import DependencyAnalyzer
        assert DependencyAnalyzer is not None
    
    def test_import_validator(self):
        """测试验证器导入"""
        from excel2everything.validator import SQLValidator
        assert SQLValidator is not None
    
    def test_import_aliases(self):
        """测试便捷别名"""
        from excel2everything import Parser, Generator, Validator, Analyzer
        assert Parser is not None
        assert Generator is not None
        assert Validator is not None
        assert Analyzer is not None


class TestModels:
    """测试数据模型"""
    
    def test_field_mapping(self):
        """测试字段映射模型"""
        from excel2everything.models import FieldMapping
        
        field = FieldMapping(
            target="CUST_ID",
            target_label="客户ID",
            expr="T01.CUST_ID",
            source_table="F_CUST_INFO",
            source_field="CUST_ID",
        )
        
        assert field.target == "CUST_ID"
        assert field.target_label == "客户ID"
        assert field.expr == "T01.CUST_ID"
    
    def test_table_model(self):
        """测试表模型"""
        from excel2everything.models import TableModel, MappingGroup, FieldMapping
        
        field = FieldMapping(
            target="CUST_ID",
            expr="T01.CUST_ID",
        )
        
        group = MappingGroup(
            name="来源表1",
            from_clause="F_CUST_INFO T01",
            fields=[field],
        )
        
        table = TableModel(
            table_name="M_CUST_INFO",
            table_label="客户信息表",
            groups=[group],
        )
        
        assert table.table_name == "M_CUST_INFO"
        assert table.total_fields == 1
        assert len(table.groups) == 1


class TestValidator:
    """测试 SQL 验证器"""
    
    def test_validate_simple_sql(self):
        """测试简单 SQL 验证"""
        from excel2everything.validator import SQLValidator
        
        validator = SQLValidator()
        sql = "SELECT * FROM DUAL"
        
        issues = validator.validate(sql)
        assert isinstance(issues, list)
    
    def test_validate_string_literal_error(self):
        """测试字符串字面量错误检测"""
        from excel2everything.validator import SQLValidator, IssueSeverity
        
        validator = SQLValidator()
        # 单引号不配对
        sql = "SELECT 'test FROM DUAL"
        
        issues = validator.validate(sql)
        # 应该检测到引号不配对
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        assert len(critical_issues) > 0


class TestDDLGenerator:
    """测试 DDL 生成器"""
    
    def test_supported_dialects(self):
        """测试支持的数据库方言"""
        from excel2everything.generator import SUPPORTED_DIALECTS
        
        expected = ["oracle", "mysql", "postgresql", "hive", "inceptor"]
        for dialect in expected:
            assert dialect in SUPPORTED_DIALECTS
    
    def test_infer_data_type(self):
        """测试数据类型推断"""
        from excel2everything.generator.ddl import infer_data_type
        
        # 日期类型
        assert "DATE" in infer_data_type("日期类")
        
        # 金额类型
        assert "NUMBER" in infer_data_type("金额类")
        
        # 字符串类型
        assert "VARCHAR" in infer_data_type("字符类")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
