"""models 模块测试"""

import json
import pytest
from src.core.models import Skill, JobDescription


class TestSkill:
    """测试 Skill 数据模型"""

    def test_basic_creation(self):
        s = Skill(name="Python")
        assert s.name == "Python"
        assert s.proficiency is None
        assert s.category is None
        assert s.parent is None

    def test_full_creation(self):
        s = Skill(name="Helm", proficiency="熟悉", category="DevOps工具", parent="Kubernetes")
        assert s.name == "Helm"
        assert s.proficiency == "熟悉"
        assert s.category == "DevOps工具"
        assert s.parent == "Kubernetes"

    def test_to_dict_excludes_none(self):
        s = Skill(name="Python")
        d = s.to_dict()
        assert d == {"name": "Python"}
        assert "proficiency" not in d
        assert "category" not in d
        assert "parent" not in d

    def test_to_dict_includes_all_set_fields(self):
        s = Skill(name="Helm", proficiency="熟悉", category="DevOps工具", parent="Kubernetes")
        d = s.to_dict()
        assert d == {
            "name": "Helm",
            "proficiency": "熟悉",
            "category": "DevOps工具",
            "parent": "Kubernetes",
        }


class TestJobDescription:
    """测试 JobDescription 数据模型"""

    def test_minimal_creation(self):
        jd = JobDescription(source_file="test.txt")
        assert jd.source_file == "test.txt"
        assert jd.job_title is None
        assert jd.responsibilities == []
        assert jd.required_skills == []
        assert jd.preferred_skills == []

    def test_full_creation(self):
        jd = JobDescription(
            source_file="test.txt",
            job_title="后端工程师",
            location="北京",
            education="本科",
            experience="3-5年",
            responsibilities=["开发后端服务"],
            required_skills=[Skill(name="Java")],
            preferred_skills=[Skill(name="Go")],
        )
        assert jd.job_title == "后端工程师"
        assert len(jd.required_skills) == 1
        assert jd.required_skills[0].name == "Java"

    def test_to_dict_excludes_none_fields(self):
        jd = JobDescription(source_file="test.txt", job_title="测试")
        d = jd.to_dict()
        assert "source_file" in d
        assert "job_title" in d
        assert "location" not in d  # None 字段被排除
        assert "department" not in d

    def test_to_dict_skills_serialization(self):
        jd = JobDescription(
            source_file="test.txt",
            required_skills=[
                Skill(name="Python", proficiency="熟练", category="编程语言"),
            ],
        )
        d = jd.to_dict()
        assert d["required_skills"] == [
            {"name": "Python", "proficiency": "熟练", "category": "编程语言"}
        ]

    def test_to_json_valid(self):
        jd = JobDescription(
            source_file="test.txt",
            job_title="前端工程师",
            required_skills=[Skill(name="React")],
        )
        json_str = jd.to_json()
        parsed = json.loads(json_str)
        assert parsed["job_title"] == "前端工程师"
        assert parsed["required_skills"][0]["name"] == "React"

    def test_to_json_ensure_ascii_false(self):
        jd = JobDescription(source_file="test.txt", job_title="前端工程师")
        json_str = jd.to_json()
        assert "前端工程师" in json_str  # 中文不被转义

    def test_empty_lists_in_dict(self):
        jd = JobDescription(source_file="test.txt")
        d = jd.to_dict()
        # 空列表不是 None，应保留
        assert "responsibilities" in d
        assert d["responsibilities"] == []
