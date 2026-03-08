# Excel2Everything

<p align="center">
  <strong>Parse Excel → Transform with Templates → Generate Anything</strong>
</p>

<p align="center">
  <strong>解析 Excel → 模板转换 → 生成任意格式</strong>
</p>

<p align="center">
  <a href="https://github.com/excel2everything/excel2everything/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python version">
  </a>
</p>

---

## 概述 / Overview

**Excel2Everything** 是一个模板驱动的 Excel 转换工具。核心思路很简单：**一次解析，无限输出**。

**Excel2Everything** is a template-driven Excel transformation tool. The core idea is simple: **Parse Once, Output Anything**.

### 工作原理 / How It Works

```
Excel 文件
    ↓
[解析器 Parser] → 中间表示 (IR) 模型
    ↓
[模板 Template] → Jinja2 渲染
    ↓
输出文件 (SQL / Python / JSON / ...)
```

### 核心特性 / Core Features

- **Excel 解析 / Excel Parsing** - 解析数据模型 Excel，提取表结构、字段映射规则
- **模板驱动 / Template-Driven** - 基于 Jinja2，自定义输出格式
- **一次解析，多种输出 / Parse Once, Output Anything** - 同一 Excel 可生成 SQL、DDL、代码、文档等
- **多数据库支持 / Multi-Database Support** - 内置 Oracle、MySQL、PostgreSQL、Hive、OceanBase 等模板
- **可扩展 / Extensible** - 添加新输出格式只需编写模板，无需修改代码

---

## 安装 / Installation

### 从源码安装 / Install from Source

```bash
# 克隆仓库 / Clone repository
git clone https://github.com/excel2everything/excel2everything.git
cd excel2everything

# 安装 / Install
pip install -e .
```

### 验证安装 / Verify Installation

```bash
excel2everything info
```

---

## 快速开始 / Quick Start

### 命令行使用 / CLI Usage

```bash
# 解析 Excel / Parse Excel
excel2everything parse model.xlsx --output ./output

# 生成 SQL（使用内置模板）/ Generate SQL with built-in templates
excel2everything generate model.xlsx --dialect oracle --output ./sql

# 生成 DDL / Generate DDL
excel2everything ddl model.xlsx --dialect mysql --output ./ddl

# 分析依赖 / Analyze dependencies
excel2everything analyze model.xlsx
```

### Python API

```python
from excel2everything import Parser, Generator

# 1. 解析 Excel → IR 模型 / Parse Excel to IR model
parser = Parser()
model = parser.parse("model.xlsx")

# 2. 使用模板生成 SQL / Generate SQL with template
generator = Generator(dialect="oracle")
sql = generator.generate_procedure(model)
print(sql)
```

### 自定义模板 / Custom Templates

只需创建 Jinja2 模板文件即可扩展输出格式：

Just create a Jinja2 template file to extend output formats:

```python
from excel2everything import Parser
from jinja2 import Environment, FileSystemLoader

# 解析 Excel / Parse Excel
parser = Parser()
model = parser.parse("model.xlsx")

# 自定义模板渲染 / Custom template rendering
env = Environment(loader=FileSystemLoader("./templates"))
template = env.get_template("my_output.py.j2")
result = template.render(model=model)
```

模板示例 / Template example `my_output.py.j2`：

```jinja2
# 自动生成: {{ model.table_name }}
# {{ model.table_label }}

class {{ model.table_name }}:
    fields = [
{%- for field in model.target_fields %}
        "{{ field }}",
{%- endfor %}
    ]
```

---

## 内置模板 / Built-in Templates

### SQL 生成 / SQL Generation

| 输出类型 / Output Type | Oracle | MySQL | PostgreSQL | Hive | OceanBase |
|------------------------|--------|-------|------------|------|----------|
| DDL 建表语句 / DDL | ✅ | ✅ | ✅ | ✅ | ✅ |
| INSERT SQL | ✅ | ✅ | ✅ | ✅ | ✅ |
| 存储过程 / Procedure | ✅ | - | - | ✅ | ✅ |

### 可扩展输出 / Extensible Outputs

通过自定义模板，你可以生成 / With custom templates, you can generate:

| 输出类型 / Output Type | 用途 / Usage | 示例模板 / Example Template |
|------------------------|--------------|----------------------------|
| Python 代码 / Python Code | Pandas ETL | `etl.py.j2` |
| JSON Schema | 数据验证 / Validation | `schema.json.j2` |
| Markdown 文档 / Markdown Doc | 表结构文档 / Table Doc | `doc.md.j2` |
| YAML 配置 / YAML Config | 配置文件 / Config File | `config.yaml.j2` |
| API 代码 / API Code | FastAPI 接口 | `api.py.j2` |

---

## 项目结构 / Project Structure

```
excel2everything/
├── src/dataforge/
│   ├── parser/        # Excel 解析器 → IR 模型 / Excel parser to IR model
│   ├── generator/     # 模板渲染器 / Template renderer
│   ├── templates/     # Jinja2 模板文件 / Jinja2 template files
│   ├── models/        # IR 数据模型 / IR data models
│   └── cli.py         # 命令行接口 / CLI interface
├── templates/         # Excel 模板文件 / Excel template files
├── tests/             # 测试用例 / Test cases
└── examples/          # 使用示例 / Usage examples
```

---

## 文档 / Documentation

文档正在完善中，目前请参考源码和示例代码。

Documentation is being improved, please refer to the source code and examples for now.

- [使用示例 / Usage Example](examples/basic_usage.py)

---

## 开发 / Development

```bash
# 克隆仓库 / Clone repository
git clone https://github.com/excel2everything/excel2everything.git
cd excel2everything

# 安装开发依赖 / Install dev dependencies
pip install -e ".[dev]"

# 运行测试 / Run tests
pytest
```

---

## 许可证 / License

MIT License - 详见 [LICENSE](LICENSE) 文件

MIT License - See [LICENSE](LICENSE) file for details

---

## 联系方式 / Contact

- **Issues**: [GitHub Issues](https://github.com/excel2everything/excel2everything/issues)
- **Email**: 欢迎通过 Issues 联系 / Feel free to contact via Issues

---

<p align="center">
  Made with ❤️ by 个人开发者 / Individual Developer
</p>
