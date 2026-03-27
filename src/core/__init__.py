"""核心数据层 — 配置、数据模型、归一化"""

from src.core.models import Skill, JobDescription
from src.core.config import RAW_DATA_DIR, PARSED_DATA_DIR

__all__ = ["Skill", "JobDescription", "RAW_DATA_DIR", "PARSED_DATA_DIR"]
