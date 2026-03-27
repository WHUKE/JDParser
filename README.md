# JDParser

岗位描述信息提取 — 面向职业规划知识图谱的 JD 知识抽取工具

## 项目结构

```
JDParser/
├── data/
│   ├── raw/                    # 原始 JD 文本（.txt）
│   └── parsed/                 # 解析输出（.json）
│       ├── _all.json           # 全量汇总文件
│       └── <name>.json         # 每个 JD 的独立结果
│
├── src/
│   ├── core/                   # 核心数据层
│   │   ├── config.py           # 路径与 API 配置
│   │   ├── models.py           # 数据模型（JobDescription, Skill）
│   │   └── normalizer.py       # 技能名称归一化
│   │
│   ├── parsers/                # 解析器
│   │   ├── base.py             # 抽象基类 & 公共工具
│   │   ├── regex_parser.py     # 正则/规则解析器
│   │   ├── llm_parser.py       # DeepSeek LLM 解析器
│   │   └── langbase_parser.py  # Langbase Workflow 解析器
│   │
│   ├── loader/                 # 解析结果加载器
│   │   └── loader.py           # load_all() / load_file()
│   │
│   ├── cli/                    # 命令行入口
│   │   ├── extract.py          # JD 知识抽取命令
│   │   └── load.py             # 解析结果查看命令
│   │
│   └── pipeline.py             # 处理流水线（读取→解析→归一化→输出）
│
├── requirements.txt
└── README.md
```

## 快速开始

建议 Python 版本：**3.12.x**，建议使用 venv 管理环境。

```bash
# 安装依赖
pip install -r requirements.txt
```

---

## 知识抽取

将 JD 文本文件（`.txt`）放入 `data/raw/`，然后运行：

```bash
# 仅使用正则解析（无需 API，提取结构化元数据）
python -m src.cli.extract --mode regex

# 使用 DeepSeek LLM 解析（细粒度技能抽取，需要 API Key）
export DEEPSEEK_API_KEY="your-key-here"   # Linux/macOS
$env:DEEPSEEK_API_KEY="your-key-here"     # PowerShell
python -m src.cli.extract --mode llm

# 使用 Langbase Workflow 解析
export LANGBASE_API_KEY="your-key-here"
python -m src.cli.extract --mode langbase

# 指定输入/输出目录
python -m src.cli.extract --mode llm --input data/raw --output data/parsed

# 显示详细日志
python -m src.cli.extract --mode llm -v
```

解析完成后会在 `data/parsed/` 下生成每个 JD 的独立 JSON 文件，以及汇总文件 `_all.json`。

---

## 加载解析结果

### CLI 方式

```bash
# 列出 data/parsed/ 下所有可用 JSON 文件
python -m src.cli.load --list

# 加载全量结果（_all.json）并打印摘要
python -m src.cli.load --all

# 加载指定文件并打印摘要
python -m src.cli.load --file xzl_16.json

# 打印详细信息（含技能预览）
python -m src.cli.load --all --verbose
python -m src.cli.load --file xzl_16.json -v
```

### Python API 方式

供后续数据清洗、Neo4j 导入等模块直接调用：

```python
from src.loader import load_all, load_file

# 加载全量结果
jds = load_all()

# 加载指定文件
jds = load_file("xzl_16.json")

# JobDescription 对象包含完整字段
for jd in jds:
    print(jd.job_title, jd.location)
    for skill in jd.required_skills:
        print(skill.name, skill.category, skill.proficiency)
```

---

## 抽取字段说明

| 字段 | 说明 | 正则模式 | LLM 模式 |
|---|---|:---:|:---:|
| `job_title` | 职位名称 | ✓ | ✓ |
| `location` | 工作地点 | ✓ | ✓ |
| `education` | 学历要求 | ✓ | ✓ |
| `experience` | 工作年限 | ✓ | ✓ |
| `job_category` | 职位类别 | ✓ | ✓ |
| `responsibilities` | 工作职责列表 | ✓ | ✓ |
| `required_skills` | 必需技能（细粒度） | — | ✓ |
| `preferred_skills` | 加分技能（细粒度） | — | ✓ |
| `department` | 所属部门 | ✓ | — |
| `employment_type` | 全职 / 兼职 | ✓ | — |
| `headcount` | 招聘人数 | ✓ | — |
| `publish_date` | 发布日期 | ✓ | — |
| `target_group` | 面向对象（社招/校招） | ✓ | — |
| `raw_requirements` | 原始任职要求文本 | ✓ | — |

### Skill 对象字段

| 字段 | 说明 | 示例 |
|---|---|---|
| `name` | 归一化技能名称 | `Kubernetes` |
| `proficiency` | 熟练度 | `熟悉` / `熟练` / `精通` / `不限` |
| `category` | 技能分类 | `DevOps工具` / `编程语言` / `软技能` |
| `parent` | 父技能名称（层级关系） | `Kubernetes`（对应 `Helm`） |

---

## 技能归一化

所有技能名称经过归一化处理，确保同一技能在知识图谱中只有一个节点。

示例：`JS` → `JavaScript`，`K8S` → `Kubernetes`，`Vue3` → `Vue.js`