# DataForge Core

<p align="center">
  <strong>Data Model to SQL - Excel 驱动的 SQL 代码生成器</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/dataforge-core/">
    <img src="https://img.shields.io/pypi/v/dataforge-core.svg" alt="PyPI version">
  </a>
  <a href="https://github.com/dataforge/dataforge-core/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python version">
  </a>
</p>

---

## 概述 / Overview

DataForge Core 是一个数据模型转换工具，帮助业务人员在 Excel 中定义字段映射规则，自动生成可执行的 SQL 代码。

DataForge Core is a data model transformation tool that helps business users define field mapping rules in Excel and automatically generate executable SQL code.

### 核心功能 / Core Features

- **Excel 解析 / Excel Parsing** - 智能解析数据模型 Excel 文件 / Intelligently parse data model Excel files
- **SQL 生成 / SQL Generation** - 自动生成 INSERT SQL 和存储过程 / Automatically generate INSERT SQL and stored procedures
- **DDL 生成 / DDL Generation** - 支持多种数据库方言的建表语句 / Support DDL statements for multiple database dialects
- **依赖分析 / Dependency Analysis** - 分析表级和字段级依赖关系 / Analyze table-level and field-level dependencies
- **SQL 验证 / SQL Validation** - 内置语法检查和质量验证 / Built-in syntax checking and quality validation
- **多数据库支持 / Multi-Database Support** - Oracle, MySQL, PostgreSQL, Hive, Inceptor, OceanBase

---

## 安装 / Installation

```bash
pip install dataforge-core
```

---

## 快速开始 / Quick Start

### 解析 Excel 模型 / Parse Excel Model

```python
from dataforge import Parser

# 创建解析器 / Create parser
parser = Parser()

# 解析 Excel 文件 / Parse Excel file
model = parser.parse("path/to/model.xlsx")

# 查看解析结果 / View parsing results
print(f"表名 / Table name: {model.table_name}")
print(f"表中文名 / Table label: {model.table_label}")
print(f"字段数 / Field count: {model.total_fields}")
```

### 生成 SQL / Generate SQL

```python
from dataforge import Generator

# 创建生成器 / Create generator
generator = Generator(dialect="oracle")

# 生成存储过程 / Generate stored procedure
sql = generator.generate_procedure(model)

# 输出结果 / Output result
print(sql)
```

### 生成 DDL / Generate DDL

```python
from dataforge import DDLGenerator

# 创建 DDL 生成器 / Create DDL generator
ddl_gen = DDLGenerator(dialect="mysql")

# 生成建表语句 / Generate DDL statement
ddl = ddl_gen.generate(table_ddl_model)

print(ddl)
```

### 依赖分析 / Dependency Analysis

```python
from dataforge import Analyzer

# 创建分析器 / Create analyzer
analyzer = Analyzer()

# 分析依赖关系 / Analyze dependencies
deps = analyzer.analyze(model)

# 查看源表列表 / View source table list
print(f"依赖源表 / Source tables: {deps.all_source_tables}")
```

### SQL 验证 / SQL Validation

```python
from dataforge import Validator

# 创建验证器 / Create validator
validator = Validator()

# 验证 SQL / Validate SQL
report = validator.validate(sql)

if report["has_errors"]:
    print("发现错误 / Errors found:")
    for issue in report["issues"]:
        print(f"  - {issue['problem']}: {issue['suggestion']}")
```

---

## 数据库支持 / Database Support

### DDL 生成支持 / DDL Generation Support

DataForge 支持为以下数据库生成建表语句（DDL）：

DataForge supports generating DDL statements for the following databases:

| 数据库 / Database | 状态 / Status | 说明 / Description |
|--------|----------|----------|
| Oracle | ✅ 已支持 | 企业级数据库 / Enterprise database |
| MySQL | ✅ 已支持 | 最流行的开源数据库 / Most popular open-source database |
| PostgreSQL | ✅ 已支持 | 功能强大的开源数据库 / Powerful open-source database |
| Hive | ✅ 已支持 | Hadoop 数据仓库 / Hadoop data warehouse |
| Inceptor (星环) | ✅ 已支持 | 星环科技数据库 / Transwarp database |
| OceanBase | ✅ 已支持 | 蚂蚁集团分布式数据库 / Ant Group distributed database |
| **更多...** | 🚧 开发中 | 持续添加中 / Continuously adding |

### SQL 生成支持 / SQL Generation Support

INSERT SQL 和存储过程生成目前主要支持 Inceptor 和 OceanBase 方言，后续会扩展更多数据库。

INSERT SQL and stored procedure generation currently mainly supports Inceptor and OceanBase dialects, with more databases to be added.

### 添加新数据库 / Adding New Databases

如果你想支持其他数据库，可以通过自定义模板实现：

If you want to support other databases, you can do so via custom templates:

```python
from dataforge import DDLGenerator

# 自定义数据库方言 / Custom database dialect
# 只需在 templates/ 目录下创建对应的模板文件
# Just create corresponding template files in templates/ directory
```

---

## 自定义模板 / Custom Templates

DataForge 使用 Jinja2 模板引擎，你可以自定义 SQL 生成模板：

DataForge uses Jinja2 template engine, you can customize SQL generation templates:

```python
from dataforge import Generator

# 使用自定义模板目录 / Use custom template directory
generator = Generator(
    dialect="oracle",
    template_dir="/path/to/custom/templates"
)
```

---

## 项目结构 / Project Structure

```
dataforge-core/
├── src/dataforge/
│   ├── parser/        # Excel 解析器 / Excel parser
│   ├── generator/     # SQL/DDL 生成器 / SQL/DDL generator
│   ├── analyzer/      # 依赖分析器 / Dependency analyzer
│   ├── validator/     # SQL 验证器 / SQL validator
│   ├── models/        # 数据模型 / Data models
│   └── config/        # 配置管理 / Config management
├── tests/             # 测试用例 / Test cases
├── examples/          # 使用示例 / Usage examples
└── docs/              # 文档 / Documentation
```

---

## 文档 / Documentation

文档正在完善中，目前请参考源码和示例代码。

Documentation is being improved, please refer to the source code and examples for now.

- [使用示例 / Usage Example](examples/basic_usage.py)

---

## 开发 / Development

### 环境设置 / Environment Setup

```bash
# 克隆仓库 / Clone repository
git clone https://github.com/dataforge/dataforge-core.git
cd dataforge-core

# 创建虚拟环境 / Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖 / Install development dependencies
pip install -e ".[dev]"
```

### 运行测试 / Run Tests

```bash
pytest
```

### 代码格式化 / Code Formatting

```bash
black src tests
ruff check src tests
```

---

## 贡献 / Contributing

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)。

Contributions are welcome! Please check the [Contributing Guide](CONTRIBUTING.md).

---

## 许可证 / License

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 未来规划 / Future Plans

DataForge 目前为开源项目，未来计划提供：

DataForge is currently an open-source project with plans to provide:

- 可视化桌面应用 / Visual desktop application
- 数据库直连执行 / Direct database execution
- 高级规则引擎 / Advanced rule engine
- 团队协作功能 / Team collaboration features

如果你对这些功能有需求或合作意向，欢迎联系我！

If you have needs for these features or collaboration interests, feel free to contact me!

---

## 联系方式 / Contact

- **Issues**: [GitHub Issues](https://github.com/dataforge/dataforge-core/issues)
- **Email / 邮件**: 欢迎通过 Issues 或邮件联系我讨论问题或合作
  
  Feel free to contact me via Issues or email for questions or collaboration.

---

<p align="center">
  Made with ❤️ by 个人开发者 / Individual Developer
</p>
