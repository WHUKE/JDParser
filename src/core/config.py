"""项目配置"""

from pathlib import Path

# ── 路径配置 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PARSED_DATA_DIR = PROJECT_ROOT / "data" / "parsed"

# ── 系统提示词 ──
SYSTEM_PROMPT = """\
你是一个专业的职位描述（JD）知识抽取助手。
你的任务是从给定的 JD 文本中提取结构化信息，用于构建就业/职业规划知识图谱。

请严格按照以下 JSON Schema 输出，不要输出任何额外文字：

{
  "job_title": "职位名称（去掉公司/平台前缀标记）",
  "location": "工作城市",
  "education": "学历要求（博士/硕士/本科/大专/不限）",
  "experience": "工作年限要求（如 3-5年、不限）",
  "job_category": "职位所属大类（如 后端开发、前端开发、数据分析、AI/机器学习、运维、测试、产品、设计 等）",
  "responsibilities": ["职责1", "职责2", ...],
  "required_skills": [
    {"name": "技能名称", "proficiency": "熟练度", "category": "技能分类", "parent": "父技能名称或null"},
    ...
  ],
  "preferred_skills": [
    {"name": "技能名称", "proficiency": "熟练度", "category": "技能分类", "parent": "父技能名称或null"},
    ...
  ]
}

技能抽取规则：
1. 将每个技能拆成最小粒度，例如"熟悉 MySQL/Redis/MongoDB" → 三个独立技能
2. 技能名称归一化：使用业界通用名称，如 "JavaScript" 而非 "JS"，"Kubernetes" 而非 "K8S"
3. proficiency 取值：了解 / 熟悉 / 熟练 / 精通 / 不限（如果文中未明确说明则为"不限"）
4. category 取值范围：编程语言 / 前端框架 / 后端框架 / 数据库 / 缓存 / 消息队列 / 云平台 / DevOps工具 / AI工具 / 机器学习 / 深度学习 / 数据处理 / 操作系统 / 网络 / 测试工具 / 项目管理 / 通用技能 / 软技能 / 其他
5. 软技能也要提取，如"沟通能力""团队协作""学习能力"等，category 为"软技能"
6. 加分项里的技能放到 preferred_skills
7. 层级技能识别（parent 字段）：
   - 当一个技能明显是某个更大技术/平台/生态的子组件、子工具、子模块或特定功能时，必须通过 parent 字段标注其父技能
   - 父技能也必须作为独立条目出现在技能列表中（即使原文没有单独提及父技能）
   - 如果一个技能没有父级关系，parent 设为 null
   - 常见的层级关系示例：
     * Docker → Docker Compose, Docker Swarm, Docker Registry, Dockerfile
     * Kubernetes → Helm, kubectl, KubeFlow
     * Spring → Spring Boot, Spring Cloud, Spring MVC, Spring Security
     * React → React Router, React Native, Redux, Next.js
     * Vue.js → Vue Router, Vuex, Pinia, Nuxt.js
     * AWS → EC2, S3, Lambda, DynamoDB, SageMaker
     * Node.js → Express.js, Koa.js, NestJS
     * Python → Django, Flask, FastAPI
     * Apache Spark → Spark SQL, Spark Streaming, PySpark
     * Elasticsearch → Kibana, Logstash (ELK Stack)
   - 判断原则：子技能离开父技能后无法独立定义其上下文（如 "Helm" 离开 "Kubernetes" 就失去语境）
   - 编程语言与其框架之间不视为 parent 关系（如 Java 和 Spring Boot 不构成 parent 关系），因为框架是独立的生态
   - 但框架内部的子模块/组件需标注 parent（如 Spring Boot 是 Spring 的子模块）
"""

# ── DeepSeek API 配置 ──
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ── LLM 请求配置 ──
LLM_MAX_RETRIES = 3
LLM_RETRY_DELAY = 2  # 秒
LLM_TEMPERATURE = 0.1
LLM_REQUEST_INTERVAL = 0.5  # 请求间隔（秒），避免触发速率限制

# ── Langbase API 配置 ──
LANGBASE_BASE_URL = "https://langbase.netease.com/api/v1"
LANGBASE_TRIGGER_URL = f"{LANGBASE_BASE_URL}/app/trigger"
LANGBASE_APP_ID = "626ea359-380d-4e9e-b263-d05c1922dee8"

# ── Langbase 请求配置 ──
LANGBASE_MAX_RETRIES = 3
LANGBASE_RETRY_DELAY = 5  # 秒
LANGBASE_TIMEOUT = 60  # 请求超时时间（秒）
LANGBASE_REQUEST_INTERVAL = 1  # 请求间隔（秒），避免触发速率限制
LANGBASE_POLL_INTERVAL = 1  # 轮询间隔（秒）
LANGBASE_POLL_MAX_ATTEMPTS = 60  # 最大轮询次数（1秒×60次=最多等1分钟）
LANGBASE_BATCH_SIZE = 5  # 每批并发触发的任务数
