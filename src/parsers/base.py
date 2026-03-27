"""解析器抽象基类及公共工具"""

from abc import ABC, abstractmethod
from typing import Any

from src.models import JobDescription, Skill


class BaseParser(ABC):
    """JD 解析器基类"""

    @abstractmethod
    def parse(self, text: str, filename: str) -> JobDescription:
        """将原始 JD 文本解析为结构化对象

        Args:
            text: 原始 JD 文本内容
            filename: 源文件名（用于溯源）

        Returns:
            结构化的 JobDescription 对象
        """
        ...

    # ── 公共工具方法 ──

    @staticmethod
    def merge_extracted_result(jd: JobDescription, data: dict[str, Any]) -> None:
        """将外部抽取结果（LLM / Langbase 等）合并到 JD 对象

        合并策略：
        - 简单字段：仅在正则未提取到时补充
        - 职责列表：外部结果通常更干净，直接替换
        - 技能列表：外部结果擅长细粒度拆分，直接替换

        Args:
            jd: 已经过正则预解析的 JobDescription 对象
            data: 外部抽取的结构化字典
        """
        # 简单字段：仅在正则未提取到时使用外部结果
        for field_name in ("job_title", "location", "education", "experience", "job_category"):
            val = data.get(field_name)
            if val and not getattr(jd, field_name, None):
                setattr(jd, field_name, val)

        # 职责
        if data.get("responsibilities"):
            jd.responsibilities = data["responsibilities"]

        # 必需技能
        if data.get("required_skills"):
            jd.required_skills = [
                Skill(
                    name=s.get("name", ""),
                    proficiency=s.get("proficiency"),
                    category=s.get("category"),
                )
                for s in data["required_skills"]
                if s.get("name")
            ]

        # 加分技能
        if data.get("preferred_skills"):
            jd.preferred_skills = [
                Skill(
                    name=s.get("name", ""),
                    proficiency=s.get("proficiency"),
                    category=s.get("category"),
                )
                for s in data["preferred_skills"]
                if s.get("name")
            ]