# -*- coding: utf-8 -*-
"""
DataForge Core - 命令行接口

Usage:
    dataforge --help
    dataforge parse <excel_file> [--table <table_name>] [--output <output_dir>]
    dataforge generate <excel_file> [--dialect <dialect>] [--output <output_dir>]
    dataforge ddl <excel_file> [--dialect <dialect>] [--output <output_dir>]
    dataforge analyze <excel_file> [--output <output_file>]
    dataforge validate <sql_file>
    dataforge info
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dataforge import (
    __version__,
    Parser,
    Generator,
    Analyzer,
    Validator,
    DDLGenerator,
    SUPPORTED_DIALECTS,
)
from dataforge.parser import detect_excel_format


def cmd_parse(args):
    """解析 Excel 文件"""
    excel_path = args.excel_file
    
    if not os.path.exists(excel_path):
        print(f"❌ 错误: 文件不存在: {excel_path}")
        return 1
    
    # 检测格式
    format_info = detect_excel_format(excel_path)
    print(f"📋 文件格式: {format_info['format']}")
    print(f"📊 工作表数量: {format_info['sheet_count']}")
    
    if format_info['format'] not in ('default', 'standard'):
        print(f"❌ 错误: 不支持的 Excel 格式")
        return 1
    
    # 解析
    parser = Parser(format='default')
    
    if args.table:
        models = parser.parse(excel_path, only_tables=[args.table])
        if not models:
            print(f"❌ 错误: 未找到表: {args.table}")
            return 1
    else:
        models = parser.parse(excel_path)
    
    print(f"\n✅ 解析完成，共 {len(models)} 个表模型:")
    
    for model in models:
        print(f"\n  📄 {model.table_name} ({model.table_label})")
        print(f"     字段数: {model.total_fields}")
        print(f"     映射组数: {len(model.groups)}")
    
    # 输出到文件
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for model in models:
            output_file = output_dir / f"{model.table_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(model.model_dump_json(indent=2))
            print(f"\n💾 已保存: {output_file}")
    
    return 0


def cmd_generate(args):
    """生成 SQL"""
    excel_path = args.excel_file
    dialect = args.dialect or 'oceanbase'
    
    if not os.path.exists(excel_path):
        print(f"❌ 错误: 文件不存在: {excel_path}")
        return 1
    
    if dialect.lower() not in SUPPORTED_DIALECTS:
        print(f"❌ 错误: 不支持的数据库方言: {dialect}")
        print(f"   支持的方言: {', '.join(SUPPORTED_DIALECTS)}")
        return 1
    
    # 解析
    parser = Parser(format='default')
    models = parser.parse(excel_path)
    
    if not models:
        print("❌ 错误: 未解析到任何表模型")
        return 1
    
    print(f"📋 解析完成，共 {len(models)} 个表模型")
    print(f"🔧 目标方言: {dialect.upper()}")
    
    # 生成 SQL
    generator = Generator(dialect=dialect)
    
    output_dir = Path(args.output) if args.output else Path('.')
    if args.output:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    for model in models:
        try:
            procedure = generator.generate_procedure(model)
            
            output_file = output_dir / f"{model.table_name}_procedure.sql"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(procedure)
            
            print(f"  ✅ {model.table_name}: {output_file}")
        except Exception as e:
            print(f"  ❌ {model.table_name}: {e}")
    
    print(f"\n💾 输出目录: {output_dir.absolute()}")
    return 0


def cmd_ddl(args):
    """生成 DDL"""
    excel_path = args.excel_file
    dialect = args.dialect or 'oracle'
    
    if not os.path.exists(excel_path):
        print(f"❌ 错误: 文件不存在: {excel_path}")
        return 1
    
    if dialect.lower() not in SUPPORTED_DIALECTS:
        print(f"❌ 错误: 不支持的数据库方言: {dialect}")
        print(f"   支持的方言: {', '.join(SUPPORTED_DIALECTS)}")
        return 1
    
    # 解析 DDL
    from dataforge.generator.ddl import extract_ddl_from_excel
    
    tables = extract_ddl_from_excel(excel_path)
    
    if not tables:
        print("❌ 错误: 未从 Excel 中提取到表定义")
        return 1
    
    print(f"📋 提取完成，共 {len(tables)} 个表定义")
    print(f"🔧 目标方言: {dialect.upper()}")
    
    # 生成 DDL
    ddl_gen = DDLGenerator(dialect=dialect)
    
    output_dir = Path(args.output) if args.output else Path('.')
    if args.output:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    ddl_file = output_dir / f"ddl_{dialect}.sql"
    with open(ddl_file, 'w', encoding='utf-8') as f:
        for table in tables:
            ddl = ddl_gen.generate(table)
            f.write(ddl)
            f.write("\n\n")
            print(f"  ✅ {table.table_name}")
    
    print(f"\n💾 DDL 文件: {ddl_file.absolute()}")
    return 0


def cmd_analyze(args):
    """分析依赖关系"""
    excel_path = args.excel_file
    
    if not os.path.exists(excel_path):
        print(f"❌ 错误: 文件不存在: {excel_path}")
        return 1
    
    # 解析
    parser = Parser(format='default')
    models = parser.parse(excel_path)
    
    if not models:
        print("❌ 错误: 未解析到任何表模型")
        return 1
    
    print(f"📋 解析完成，共 {len(models)} 个表模型")
    
    # 分析依赖
    analyzer = Analyzer()
    deps = analyzer.analyze_all(models)
    
    # 输出结果
    print("\n📊 依赖分析结果:")
    
    for table_name, dep in deps.items():
        source_tables = dep.all_source_tables
        print(f"\n  📄 {table_name} ({dep.table_label})")
        print(f"     源表数: {len(source_tables)}")
        if source_tables:
            print(f"     源表: {', '.join(source_tables[:5])}", end='')
            if len(source_tables) > 5:
                print(f" ... (+{len(source_tables) - 5})")
            else:
                print()
    
    # 统计摘要
    summary = analyzer.build_summary(deps)
    print(f"\n📈 统计摘要:")
    print(f"   M 表总数: {summary['total_m_tables']}")
    print(f"   源表总数: {summary['total_source_tables']}")
    print(f"   引用总数: {summary['total_references']}")
    print(f"   平均每表引用源表数: {summary['avg_sources_per_table']}")
    
    # 输出到文件
    if args.output:
        output = {
            'dependencies': {k: v.to_dict() for k, v in deps.items()},
            'summary': summary,
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n💾 已保存: {args.output}")
    
    return 0


def cmd_validate(args):
    """验证 SQL 文件"""
    sql_path = args.sql_file
    
    if not os.path.exists(sql_path):
        print(f"❌ 错误: 文件不存在: {sql_path}")
        return 1
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print(f"📄 文件: {sql_path}")
    print(f"📝 SQL 长度: {len(sql)} 字符")
    
    # 验证
    validator = Validator()
    report = validator.validate(sql)
    
    print(f"\n🔍 验证结果:")
    print(f"   错误数: {report['error_count']}")
    print(f"   警告数: {report['warning_count']}")
    print(f"   提示数: {report['info_count']}")
    
    if report['has_errors']:
        print(f"\n❌ 发现错误:")
        for issue in report['issues']:
            if issue['severity'] == 'critical':
                print(f"   行 {issue['line_number']}: {issue['problem']}")
                print(f"      💡 {issue['suggestion']}")
    elif report['has_warnings']:
        print(f"\n⚠️  发现警告:")
        for issue in report['issues'][:5]:
            if issue['severity'] == 'warning':
                print(f"   行 {issue['line_number']}: {issue['problem']}")
    else:
        print(f"\n✅ SQL 验证通过，未发现问题")
    
    return 0 if not report['has_errors'] else 1


def cmd_info(args):
    """显示版本和配置信息"""
    print("╔════════════════════════════════════════════════════════╗")
    print("║           DataForge Core - 企业级数据开发工具          ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"\n📦 版本: {__version__}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"\n🔧 支持的数据库方言:")
    for dialect in SUPPORTED_DIALECTS:
        print(f"   • {dialect.upper()}")
    print(f"\n📖 核心功能:")
    print("   • Excel 解析 - 解析数据模型 Excel 文件")
    print("   • SQL 生成 - 生成 INSERT SQL 和存储过程")
    print("   • DDL 生成 - 生成建表语句")
    print("   • 依赖分析 - 分析表级和字段级依赖关系")
    print("   • SQL 验证 - 语法检查和质量验证")
    print(f"\n💡 使用示例:")
    print("   dataforge parse model.xlsx --output ./output")
    print("   dataforge generate model.xlsx --dialect oracle")
    print("   dataforge ddl model.xlsx --dialect mysql")
    print("   dataforge analyze model.xlsx")
    print("   dataforge validate procedure.sql")
    return 0


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog='dataforge',
        description='DataForge Core - 企业级数据开发工具链核心引擎',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dataforge info                           显示版本和帮助信息
  dataforge parse model.xlsx               解析 Excel 文件
  dataforge generate model.xlsx -d oracle  生成 Oracle 存储过程
  dataforge ddl model.xlsx -d mysql        生成 MySQL DDL
  dataforge analyze model.xlsx             分析依赖关系
  dataforge validate procedure.sql         验证 SQL 文件
        """
    )
    
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # parse 命令
    parse_parser = subparsers.add_parser('parse', help='解析 Excel 文件')
    parse_parser.add_argument('excel_file', help='Excel 文件路径')
    parse_parser.add_argument('--table', '-t', help='只解析指定的表')
    parse_parser.add_argument('--output', '-o', help='输出目录')
    parse_parser.set_defaults(func=cmd_parse)
    
    # generate 命令
    gen_parser = subparsers.add_parser('generate', help='生成 SQL')
    gen_parser.add_argument('excel_file', help='Excel 文件路径')
    gen_parser.add_argument('--dialect', '-d', help='数据库方言 (默认: oceanbase)')
    gen_parser.add_argument('--output', '-o', help='输出目录')
    gen_parser.set_defaults(func=cmd_generate)
    
    # ddl 命令
    ddl_parser = subparsers.add_parser('ddl', help='生成 DDL')
    ddl_parser.add_argument('excel_file', help='Excel 文件路径')
    ddl_parser.add_argument('--dialect', '-d', help='数据库方言 (默认: oracle)')
    ddl_parser.add_argument('--output', '-o', help='输出目录')
    ddl_parser.set_defaults(func=cmd_ddl)
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='分析依赖关系')
    analyze_parser.add_argument('excel_file', help='Excel 文件路径')
    analyze_parser.add_argument('--output', '-o', help='输出 JSON 文件路径')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # validate 命令
    validate_parser = subparsers.add_parser('validate', help='验证 SQL 文件')
    validate_parser.add_argument('sql_file', help='SQL 文件路径')
    validate_parser.set_defaults(func=cmd_validate)
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='显示版本和配置信息')
    info_parser.set_defaults(func=cmd_info)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
