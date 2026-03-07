# -*- coding: utf-8 -*-
"""
DataForge Core - 基础使用示例

展示如何使用 DataForge Core 进行数据模型解析和 SQL 生成。
"""

from dataforge import (
    Parser,
    Generator,
    Validator,
    Analyzer,
    TableModel,
    FieldMapping,
    MappingGroup,
    DDLGenerator,
)


def example_create_model_manually():
    """
    示例：手动创建数据模型
    
    在没有 Excel 文件的情况下，可以手动构建数据模型。
    """
    print("=" * 50)
    print("示例 1：手动创建数据模型")
    print("=" * 50)
    
    # 创建字段映射
    fields = [
        FieldMapping(
            target="CUST_ID",
            target_label="客户ID",
            expr="T01.CUST_ID",
            source_table="F_CUST_INFO",
            source_field="CUST_ID",
        ),
        FieldMapping(
            target="CUST_NAME",
            target_label="客户姓名",
            expr="T01.CUST_NAME",
            source_table="F_CUST_INFO",
            source_field="CUST_NAME",
        ),
        FieldMapping(
            target="CREATE_DT",
            target_label="创建日期",
            expr="SYSDATE",
            is_constant=True,
        ),
    ]
    
    # 创建映射组
    group = MappingGroup(
        name="来源表1-客户信息表",
        group_index=0,
        from_clause="F_CUST_INFO T01",
        fields=fields,
    )
    
    # 创建表模型
    table = TableModel(
        table_name="M_CUST_INFO",
        table_label="客户信息表",
        load_strategy="full_snapshot",
        groups=[group],
    )
    
    print(f"表名: {table.table_name}")
    print(f"表中文名: {table.table_label}")
    print(f"字段数: {table.total_fields}")
    print(f"目标字段: {table.target_fields}")
    
    return table


def example_generate_sql(model: TableModel):
    """
    示例：生成 SQL
    
    从数据模型生成 INSERT SQL 和存储过程。
    """
    print("\n" + "=" * 50)
    print("示例 2：生成 SQL")
    print("=" * 50)
    
    # 创建 SQL 生成器
    generator = Generator(dialect="oracle")
    
    # 生成 SQL（需要实际的模板）
    try:
        # sql = generator.generate_procedure(model)
        # print(sql)
        print("SQL 生成器已创建")
        print(f"支持的方言: {generator.dialect}")
    except Exception as e:
        print(f"注意: {e}")
    
    return generator


def example_validate_sql():
    """
    示例：验证 SQL
    
    使用验证器检查 SQL 语法。
    """
    print("\n" + "=" * 50)
    print("示例 3：验证 SQL")
    print("=" * 50)
    
    # 创建验证器
    validator = Validator()
    
    # 测试正确的 SQL
    correct_sql = """
    SELECT T01.CUST_ID, T01.CUST_NAME
    FROM F_CUST_INFO T01
    WHERE T01.STATUS = 'A'
    """
    
    issues = validator.validate(correct_sql)
    print(f"正确 SQL 验证结果: {len(issues)} 个问题")
    
    # 测试有错误的 SQL（单引号不配对）
    wrong_sql = "SELECT 'test FROM DUAL"
    
    issues = validator.validate(wrong_sql)
    print(f"错误 SQL 验证结果: {len(issues)} 个问题")
    
    for issue in issues:
        print(f"  - [{issue.severity.value}] {issue.problem}")
        print(f"    建议: {issue.suggestion}")
    
    return validator


def example_analyze_dependencies(model: TableModel):
    """
    示例：分析依赖关系
    
    分析表和字段的依赖关系。
    """
    print("\n" + "=" * 50)
    print("示例 4：分析依赖关系")
    print("=" * 50)
    
    # 创建分析器
    analyzer = Analyzer()
    
    # 分析依赖
    deps = analyzer.analyze(model)
    
    print(f"表名: {deps.table_name}")
    print(f"表标签: {deps.table_label}")
    print(f"源表数量: {len(deps.all_source_tables)}")
    print(f"源表列表: {deps.all_source_tables}")
    
    # 查看每个组的依赖
    for group in deps.groups:
        print(f"\n组: {group.group_name}")
        for st in group.source_tables:
            print(f"  源表: {st.table_name} ({st.alias})")
            print(f"    使用字段: {st.used_fields}")
    
    return deps


def example_generate_ddl():
    """
    示例：生成 DDL
    
    生成建表语句。
    """
    print("\n" + "=" * 50)
    print("示例 5：生成 DDL")
    print("=" * 50)
    
    from dataforge.generator import SUPPORTED_DIALECTS
    
    print(f"支持的数据库方言: {SUPPORTED_DIALECTS}")
    
    # 创建 DDL 生成器
    try:
        ddl_gen = DDLGenerator(dialect="mysql")
        print(f"DDL 生成器已创建，方言: {ddl_gen.dialect}")
    except Exception as e:
        print(f"注意: {e}")
    
    return SUPPORTED_DIALECTS


def main():
    """运行所有示例"""
    print("DataForge Core - 使用示例")
    print("=" * 50)
    
    # 示例 1：创建模型
    model = example_create_model_manually()
    
    # 示例 2：生成 SQL
    generator = example_generate_sql(model)
    
    # 示例 3：验证 SQL
    validator = example_validate_sql()
    
    # 示例 4：分析依赖
    deps = example_analyze_dependencies(model)
    
    # 示例 5：生成 DDL
    dialects = example_generate_ddl()
    
    print("\n" + "=" * 50)
    print("所有示例运行完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
