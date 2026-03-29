"""技能名称归一化模块

将 JD 中出现的各种技能别名统一为规范名称，
确保知识图谱中同一技能只有一个节点。
"""

import re
from src.core.models import Skill


# ── 归一化映射表 ──
# key: 小写别名/缩写  →  value: 规范名称
_ALIAS_MAP: dict[str, str] = {
    # 编程语言
    "js": "JavaScript",
    "javascript": "JavaScript",
    "es6": "JavaScript",
    "es6+": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "python": "Python",
    "py": "Python",
    "java": "Java",
    "golang": "Go",
    "go": "Go",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "scala": "Scala",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "objective-c": "Objective-C",
    "objc": "Objective-C",
    "shell": "Shell",
    "bash": "Shell",
    "lua": "Lua",
    "r": "R",
    "sql": "SQL",
    "html": "HTML",
    "html5": "HTML",
    "css": "CSS",
    "css3": "CSS",

    # 前端框架
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "vue3": "Vue.js",
    "vue 3": "Vue.js",
    "vue2": "Vue.js",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "angular": "Angular",
    "angularjs": "Angular",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "nuxt": "Nuxt.js",
    "nuxt.js": "Nuxt.js",
    "svelte": "Svelte",
    "jquery": "jQuery",

    # 构建工具
    "webpack": "Webpack",
    "vite": "Vite",
    "rollup": "Rollup",
    "gulp": "Gulp",
    "babel": "Babel",
    "esbuild": "esbuild",

    # 后端框架
    "express": "Express.js",
    "express.js": "Express.js",
    "koa": "Koa.js",
    "koa.js": "Koa.js",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "gin": "Gin",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",

    # 数据库
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "es": "Elasticsearch",
    "hbase": "HBase",
    "cassandra": "Cassandra",
    "sqlite": "SQLite",
    "oracle": "Oracle",
    "clickhouse": "ClickHouse",
    "tidb": "TiDB",

    # 消息队列
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "rocketmq": "RocketMQ",
    "activemq": "ActiveMQ",
    "pulsar": "Pulsar",

    # 容器 & 编排
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "swarm": "Docker Swarm",
    "docker swarm": "Docker Swarm",

    # 云平台
    "aws": "AWS",
    "阿里云": "阿里云",
    "aliyun": "阿里云",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "azure": "Azure",
    "腾讯云": "腾讯云",
    "华为云": "华为云",

    # CI/CD & DevOps
    "jenkins": "Jenkins",
    "gitlab ci": "GitLab CI",
    "github actions": "GitHub Actions",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "nginx": "Nginx",
    "git": "Git",
    "gitops": "GitOps",
    "ci/cd": "CI/CD",

    # AI/ML
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "pandas": "pandas",
    "numpy": "NumPy",
    "spark": "Apache Spark",
    "apache spark": "Apache Spark",
    "hadoop": "Hadoop",
    "hive": "Hive",
    "flink": "Apache Flink",
    "onnx runtime": "ONNX Runtime",
    "tensorrt": "TensorRT",
    "coreml": "Core ML",

    # AI 工具
    "copilot": "GitHub Copilot",
    "github copilot": "GitHub Copilot",
    "cursor": "Cursor",
    "claude code": "Claude Code",

    # 爬虫
    "scrapy": "Scrapy",
    "selenium": "Selenium",
    "playwright": "Playwright",
    "puppeteer": "Puppeteer",

    # 游戏引擎
    "unreal engine": "Unreal Engine",
    "ue": "Unreal Engine",
    "ue4": "Unreal Engine",
    "ue5": "Unreal Engine",
    "unity": "Unity",

    # 其他工具
    "minio": "MinIO",
    "etcd": "etcd",
    "zookeeper": "ZooKeeper",
    "linux": "Linux",
    "windows": "Windows",
    "macos": "macOS",
    "ios": "iOS",
    "android": "Android",

    # 测试
    "jest": "Jest",
    "mocha": "Mocha",
    "cypress": "Cypress",
    "junit": "JUnit",
    "pytest": "pytest",

    # 协议 & 概念
    "http": "HTTP",
    "https": "HTTPS",
    "grpc": "gRPC",
    "graphql": "GraphQL",
    "restful": "RESTful",
    "rest": "RESTful",
    "websocket": "WebSocket",
    "微服务": "微服务架构",
    "分布式": "分布式系统",
    "高并发": "高并发",
    "高可用": "高可用",

    # 软技能
    "沟通能力": "沟通能力",
    "团队协作": "团队协作",
    "学习能力": "学习能力",
    "项目管理": "项目管理",
    "产品思维": "产品思维",
}


def normalize_skill_name(name: str) -> str:
    """将技能名称归一化为规范形式"""
    key = name.strip().lower()
    return _ALIAS_MAP.get(key, name.strip())


def normalize_skills(skills: list[Skill]) -> list[Skill]:
    """批量归一化技能列表，并去重"""
    seen: set[str] = set()
    result: list[Skill] = []

    for skill in skills:
        normalized = normalize_skill_name(skill.name)
        skill.name = normalized

        # 归一化 parent 字段，确保父技能名称与技能名称使用同一规范
        if skill.parent:
            skill.parent = normalize_skill_name(skill.parent)

        # 去重：相同名称只保留第一个
        if normalized.lower() not in seen:
            seen.add(normalized.lower())
            result.append(skill)

    return result
