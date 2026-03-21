# JDParser

岗位描述信息提取 — 面向职业规划知识图谱的 JD 知识抽取工具

## 项目结构

```
data/
  raw/              # 原始JD（每人收集的txt）
  parsed/           # 解析后的结构化JSON

src/
  config.py         # 路径与API配置
  models.py         # 数据模型（JobDescription, Skill）
  normalizer.py     # 技能名称归一化
  pipeline.py       # 处理流水线
  main.py           # CLI 入口
  parsers/
    base.py         # 解析器抽象基类
    regex_parser.py # 正则/规则解析器
    llm_parser.py   # DeepSeek LLM 解析器

requirements.txt
README.md
```

## 快速开始

建议Python版本：3.12.x，建议使用venv管理环境

```bash
# 安装依赖
pip install -r requirements.txt

# 仅使用正则解析（无需API，提取结构化元数据）
python -m src.main --mode regex

# 使用 DeepSeek LLM 解析（提取细粒度技能）
export DEEPSEEK_API_KEY="your-key-here"   # Linux/Mac
$env:DEEPSEEK_API_KEY="your-key-here"     # PowerShell
python -m src.main --mode llm

# 详细日志
python -m src.main --mode llm -v
```

## 抽取字段

| 字段 | 说明 | 正则模式 | LLM模式 |
|------|------|:--------:|:-------:|
| job_title | 职位名称 | ✓ | ✓ |
| location | 工作地点 | ✓ | ✓ |
| education | 学历要求 | ✓ | ✓ |
| experience | 工作年限 | ✓ | ✓ |
| department | 所属部门 | ✓ | - |
| employment_type | 全职/兼职 | ✓ | - |
| headcount | 招聘人数 | ✓ | - |
| publish_date | 发布日期 | ✓ | - |
| job_category | 职位类别 | ✓ | ✓ |
| target_group | 面向对象 | ✓ | - |
| responsibilities | 工作职责 | ✓ | ✓ |
| raw_requirements | 原始任职要求 | ✓ | - |
| required_skills | 必需技能（细粒度） | - | ✓ |
| preferred_skills | 加分技能（细粒度） | - | ✓ |

## 技能归一化

所有技能名称经过归一化处理，确保同一技能在知识图谱中只有一个节点。
例如：`JS` → `JavaScript`，`K8S` → `Kubernetes`，`Vue3` → `Vue.js`

## 输出

- `data/parsed/<filename>.json` — 每个JD的独立解析结果
- `data/parsed/_all.json` — 所有JD的汇总文件