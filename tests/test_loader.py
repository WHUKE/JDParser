"""loader 模块测试"""

import json
import pytest
from pathlib import Path

from src.core.models import JobDescription, Skill
from src.loader.loader import load_all, load_file, _dict_to_jd, _dict_to_skill


class TestDictToSkill:
    """测试字典到 Skill 的反序列化"""

    def test_full_dict(self):
        d = {"name": "Python", "proficiency": "熟练", "category": "编程语言", "parent": None}
        s = _dict_to_skill(d)
        assert s.name == "Python"
        assert s.proficiency == "熟练"
        assert s.category == "编程语言"
        assert s.parent is None

    def test_minimal_dict(self):
        d = {"name": "Go"}
        s = _dict_to_skill(d)
        assert s.name == "Go"
        assert s.proficiency is None

    def test_empty_dict(self):
        s = _dict_to_skill({})
        assert s.name == ""


class TestDictToJd:
    """测试字典到 JobDescription 的反序列化"""

    def test_full_dict(self):
        d = {
            "source_file": "test.txt",
            "job_title": "后端工程师",
            "location": "北京",
            "education": "本科",
            "experience": "3-5年",
            "responsibilities": ["开发", "维护"],
            "required_skills": [{"name": "Java", "proficiency": "熟练"}],
            "preferred_skills": [{"name": "Go"}],
            "raw_requirements": ["要求1"],
        }
        jd = _dict_to_jd(d)
        assert jd.source_file == "test.txt"
        assert jd.job_title == "后端工程师"
        assert len(jd.responsibilities) == 2
        assert len(jd.required_skills) == 1
        assert jd.required_skills[0].name == "Java"
        assert len(jd.preferred_skills) == 1

    def test_minimal_dict(self):
        d = {"source_file": "min.txt"}
        jd = _dict_to_jd(d)
        assert jd.source_file == "min.txt"
        assert jd.responsibilities == []
        assert jd.required_skills == []

    def test_missing_source_file(self):
        jd = _dict_to_jd({})
        assert jd.source_file == ""


class TestLoadAll:
    """测试 load_all"""

    def test_load_existing_all_json(self, tmp_path):
        data = [
            {
                "source_file": "a.txt",
                "job_title": "工程师A",
                "responsibilities": [],
                "required_skills": [],
                "preferred_skills": [],
                "raw_requirements": [],
            },
            {
                "source_file": "b.txt",
                "job_title": "工程师B",
                "responsibilities": [],
                "required_skills": [{"name": "Python"}],
                "preferred_skills": [],
                "raw_requirements": [],
            },
        ]
        all_path = tmp_path / "_all.json"
        all_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        jds = load_all(tmp_path)
        assert len(jds) == 2
        assert jds[0].job_title == "工程师A"
        assert jds[1].required_skills[0].name == "Python"

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_all(tmp_path)


class TestLoadFile:
    """测试 load_file"""

    def test_load_single_object(self, tmp_path):
        data = {
            "source_file": "single.txt",
            "job_title": "测试职位",
            "responsibilities": [],
            "required_skills": [],
            "preferred_skills": [],
            "raw_requirements": [],
        }
        (tmp_path / "single.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        jds = load_file("single.json", tmp_path)
        assert len(jds) == 1
        assert jds[0].job_title == "测试职位"

    def test_load_array(self, tmp_path):
        data = [
            {"source_file": "a.txt", "responsibilities": [], "required_skills": [], "preferred_skills": [], "raw_requirements": []},
            {"source_file": "b.txt", "responsibilities": [], "required_skills": [], "preferred_skills": [], "raw_requirements": []},
        ]
        (tmp_path / "multi.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        jds = load_file("multi.json", tmp_path)
        assert len(jds) == 2

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_file("nonexistent.json", tmp_path)
