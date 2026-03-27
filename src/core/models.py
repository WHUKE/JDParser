"""数据模型定义 — 面向知识图谱的结构化JD表示"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class Skill:
    """技能实体"""
    name: str                              # 归一化后的技能名称
    proficiency: Optional[str] = None      # 熟练度: 了解/熟悉/熟练/精通 等
    category: Optional[str] = None         # 技能分类: 编程语言/框架/数据库/工具 等
    parent: Optional[str] = None           # 父技能名称（如 Docker Swarm → Docker）

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class JobDescription:
    """结构化的岗位描述"""
    source_file: str                                    # 原始文件名
    job_title: Optional[str] = None                     # 职位名称
    location: Optional[str] = None                      # 工作地点
    education: Optional[str] = None                     # 学历要求
    experience: Optional[str] = None                    # 工作年限
    department: Optional[str] = None                    # 所属部门
    employment_type: Optional[str] = None               # 招聘类型: 全职/兼职
    headcount: Optional[int] = None                     # 招聘人数
    publish_date: Optional[str] = None                  # 发布日期
    job_category: Optional[str] = None                  # 职位类别
    target_group: Optional[str] = None                  # 面向对象: 社招/校招
    responsibilities: list[str] = field(default_factory=list)  # 工作职责
    required_skills: list[Skill] = field(default_factory=list)  # 必需技能
    preferred_skills: list[Skill] = field(default_factory=list) # 加分技能
    raw_requirements: list[str] = field(default_factory=list)   # 原始任职要求文本

    def to_dict(self) -> dict:
        d = asdict(self)
        # 清除 None 值以保持输出整洁
        d["required_skills"] = [s.to_dict() for s in self.required_skills]
        d["preferred_skills"] = [s.to_dict() for s in self.preferred_skills]
        return {k: v for k, v in d.items() if v is not None}

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
