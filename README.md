# DataForge Core

<p align="center">
  <strong>Enterprise Data Development Toolkit - Core Engine</strong>
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

## 概述

DataForge Core 是一个企业级数据开发工具链的核心引擎，用于将数据模型自动转换为可执行的 SQL 代码。

### 核心功能

- **Excel 解析** - 智能解析监管数据模型 Excel 文件
- **SQL 生成** - 自动生成 INSERT SQL 和存储过程
- **DDL 生成** - 支持多种数据库方言的建表语句
- **依赖分析** - 分析表级和字段级依赖关系
- **SQL 验证** - 内置语法检查和质量验证
- **多数据库支持** - Oracle, MySQL, PostgreSQL, Hive, Inceptor, OceanBase

---

## 安装

```bash
pip install dataforge-core
```

---

## 快速开始

### 解析 Excel 模型

```python
from dataforge import Parser

# 创建解析器
parser = Parser(format="regulatory")

# 解析 Excel 文件
model = parser.parse("path/to/model.xlsx")

# 查看解析结果
print(f"表名: {model.table_name}")
print(f"表中文名: {model.table_label}")
print(f"字段数: {model.total_fields}")
```

### 生成 SQL

```python
from dataforge import Generator

# 创建生成器
generator = Generator(dialect="oracle")

# 生成存储过程
sql = generator.generate_procedure(model)

# 输出结果
print(sql)
```

### 生成 DDL

```python
from dataforge import DDLGenerator

# 创建 DDL 生成器
ddl_gen = DDLGenerator(dialect="mysql")

# 生成建表语句
ddl = ddl_gen.generate(table_ddl_model)

print(ddl)
```

### 依赖分析

```python
from dataforge import Analyzer

# 创建分析器
analyzer = Analyzer()

# 分析依赖关系
deps = analyzer.analyze(model)

# 查看源表列表
print(f"依赖源表: {deps.all_source_tables}")
```

### SQL 验证

```python
from dataforge import Validator

# 创建验证器
validator = Validator()

# 验证 SQL
report = validator.validate(sql)

if report["has_errors"]:
    print("发现错误:")
    for issue in report["issues"]:
        print(f"  - {issue['problem']}: {issue['suggestion']}")
```

---

## 支持的数据库

| 数据库 | SQL 生成 | DDL 生成 | 模板路径 |
|--------|----------|----------|----------|
| Oracle | ✅ | ✅ | `templates/oracle/` |
| MySQL | ✅ | ✅ | `templates/mysql/` |
| PostgreSQL | ✅ | ✅ | `templates/postgresql/` |
| Hive | ✅ | ✅ | `templates/hive/` |
| Inceptor (星环) | ✅ | ✅ | `templates/inceptor/` |
| OceanBase | ✅ | ✅ | `templates/oceanbase/` |

---

## 自定义模板

DataForge 使用 Jinja2 模板引擎，你可以自定义 SQL 生成模板：

```python
from dataforge import Generator

# 使用自定义模板目录
generator = Generator(
    dialect="oracle",
    template_dir="/path/to/custom/templates"
)
```

---

## 项目结构

```
dataforge-core/
├── src/dataforge/
│   ├── parser/        # Excel 解析器
│   ├── generator/     # SQL/DDL 生成器
│   ├── analyzer/      # 依赖分析器
│   ├── validator/     # SQL 验证器
│   ├── models/        # 数据模型
│   └── config/        # 配置管理
├── tests/             # 测试用例
├── examples/          # 使用示例
└── docs/              # 文档
```

---

## 文档

完整文档请访问：[https://docs.dataforge.dev](https://docs.dataforge.dev)

- [快速开始](docs/getting-started.md)
- [API 参考](docs/api-reference.md)
- [配置说明](docs/configuration.md)
- [自定义规则](docs/custom-rules.md)
- [模板开发](docs/templates.md)

---

## 开发

### 环境设置

```bash
# 克隆仓库
git clone https://github.com/dataforge/dataforge-core.git
cd dataforge-core

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black src tests
ruff check src tests
```

---

## 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)。

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 商业版本

DataForge 还提供商业版本，包含：

- 可视化桌面应用
- 数据库直连执行
- 高级规则引擎
- 团队协作功能
- 企业级支持

更多信息请访问：[https://dataforge.dev](https://dataforge.dev)

---

<p align="center">
  Made with ❤️ by DataForge Team
</p>
