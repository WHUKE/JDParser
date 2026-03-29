"""base parser 模块测试"""

import pytest
from src.core.models import JobDescription, Skill
from src.parsers.base import BaseParser


class TestMergeExtractedResult:
    """测试 merge_extracted_result 合并策略"""

    def _make_jd(self, **kwargs) -> JobDescription:
        defaults = {"source_file": "test.txt"}
        defaults.update(kwargs)
        return JobDescription(**defaults)

    def test_simple_fields_supplement_only(self):
        """正则已提取到的简单字段不被覆盖"""
        jd = self._make_jd(job_title="前端工程师", education="本科")
        data = {"job_title": "高级前端工程师", "education": "硕士", "location": "北京"}
        BaseParser.merge_extracted_result(jd, data)
        assert jd.job_title == "前端工程师"  # 不被覆盖
        assert jd.education == "本科"  # 不被覆盖
        assert jd.location == "北京"  # 空字段被补充

    def test_responsibilities_replaced(self):
        """职责列表被外部结果替换"""
        jd = self._make_jd(responsibilities=["旧职责1", "旧职责2"])
        data = {"responsibilities": ["新职责1", "新职责2", "新职责3"]}
        BaseParser.merge_extracted_result(jd, data)
        assert len(jd.responsibilities) == 3
        assert jd.responsibilities[0] == "新职责1"

    def test_required_skills_replaced(self):
        """必需技能列表被外部结果替换"""
        jd = self._make_jd(required_skills=[Skill(name="OldSkill")])
        data = {
            "required_skills": [
                {"name": "Python", "proficiency": "熟练", "category": "编程语言"},
                {"name": "Go", "proficiency": "了解"},
            ]
        }
        BaseParser.merge_extracted_result(jd, data)
        assert len(jd.required_skills) == 2
        assert jd.required_skills[0].name == "Python"
        assert jd.required_skills[0].proficiency == "熟练"
        assert jd.required_skills[1].name == "Go"

    def test_preferred_skills_replaced(self):
        jd = self._make_jd()
        data = {
            "preferred_skills": [
                {"name": "Kubernetes", "category": "DevOps工具", "parent": None},
            ]
        }
        BaseParser.merge_extracted_result(jd, data)
        assert len(jd.preferred_skills) == 1
        assert jd.preferred_skills[0].name == "Kubernetes"

    def test_skills_filter_empty_name(self):
        """name 为空的技能应被过滤"""
        jd = self._make_jd()
        data = {
            "required_skills": [
                {"name": "Python"},
                {"name": ""},
                {"proficiency": "熟练"},  # 没有 name 字段
            ]
        }
        BaseParser.merge_extracted_result(jd, data)
        assert len(jd.required_skills) == 1

    def test_empty_data(self):
        """空数据不应修改 jd"""
        jd = self._make_jd(job_title="测试", responsibilities=["职责1"])
        BaseParser.merge_extracted_result(jd, {})
        assert jd.job_title == "测试"
        assert jd.responsibilities == ["职责1"]

    def test_skill_with_parent(self):
        jd = self._make_jd()
        data = {
            "required_skills": [
                {"name": "Helm", "parent": "Kubernetes", "category": "DevOps工具"},
            ]
        }
        BaseParser.merge_extracted_result(jd, data)
        assert jd.required_skills[0].parent == "Kubernetes"

    def test_no_responsibilities_key(self):
        """data 中没有 responsibilities 键时不替换"""
        jd = self._make_jd(responsibilities=["原始职责"])
        data = {"job_title": "新标题"}
        BaseParser.merge_extracted_result(jd, data)
        assert jd.responsibilities == ["原始职责"]
