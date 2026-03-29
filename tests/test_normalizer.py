"""normalizer 模块测试"""

import pytest
from src.core.models import Skill
from src.core.normalizer import normalize_skill_name, normalize_skills


# ── normalize_skill_name 测试 ──


class TestNormalizeSkillName:
    """测试技能名称归一化"""

    def test_lowercase_alias(self):
        assert normalize_skill_name("js") == "JavaScript"

    def test_uppercase_alias(self):
        assert normalize_skill_name("JS") == "JavaScript"

    def test_mixed_case_alias(self):
        assert normalize_skill_name("TypeScript") == "TypeScript"

    def test_k8s_to_kubernetes(self):
        assert normalize_skill_name("k8s") == "Kubernetes"

    def test_vue_to_vuejs(self):
        assert normalize_skill_name("vue") == "Vue.js"

    def test_vue3_to_vuejs(self):
        assert normalize_skill_name("vue3") == "Vue.js"

    def test_springboot(self):
        assert normalize_skill_name("springboot") == "Spring Boot"

    def test_unknown_skill_passthrough(self):
        assert normalize_skill_name("SomeUnknownSkill") == "SomeUnknownSkill"

    def test_whitespace_stripping(self):
        assert normalize_skill_name("  js  ") == "JavaScript"

    def test_python_alias(self):
        assert normalize_skill_name("py") == "Python"

    def test_golang(self):
        assert normalize_skill_name("golang") == "Go"

    def test_docker(self):
        assert normalize_skill_name("docker") == "Docker"

    def test_react(self):
        assert normalize_skill_name("react.js") == "React"

    def test_nodejs(self):
        assert normalize_skill_name("nodejs") == "Node.js"

    def test_express(self):
        assert normalize_skill_name("express") == "Express.js"

    def test_redis(self):
        assert normalize_skill_name("redis") == "Redis"

    def test_mysql(self):
        assert normalize_skill_name("mysql") == "MySQL"

    def test_postgres(self):
        assert normalize_skill_name("postgres") == "PostgreSQL"

    def test_mongodb(self):
        assert normalize_skill_name("mongo") == "MongoDB"

    def test_html5_to_html(self):
        assert normalize_skill_name("html5") == "HTML"

    def test_css3_to_css(self):
        assert normalize_skill_name("css3") == "CSS"


# ── normalize_skills 测试 ──


class TestNormalizeSkills:
    """测试批量归一化 + 去重"""

    def test_basic_normalization(self):
        skills = [Skill(name="js"), Skill(name="ts")]
        result = normalize_skills(skills)
        assert len(result) == 2
        assert result[0].name == "JavaScript"
        assert result[1].name == "TypeScript"

    def test_deduplication(self):
        skills = [
            Skill(name="js", proficiency="熟练"),
            Skill(name="JavaScript", proficiency="精通"),
        ]
        result = normalize_skills(skills)
        assert len(result) == 1
        assert result[0].name == "JavaScript"
        assert result[0].proficiency == "熟练"  # 保留第一个

    def test_deduplication_case_insensitive(self):
        skills = [
            Skill(name="Python"),
            Skill(name="python"),
        ]
        result = normalize_skills(skills)
        assert len(result) == 1

    def test_parent_normalization(self):
        """parent 字段也应被归一化"""
        skills = [
            Skill(name="Helm", parent="k8s"),
            Skill(name="kubectl", parent="K8S"),
        ]
        result = normalize_skills(skills)
        assert result[0].parent == "Kubernetes"
        assert result[1].parent == "Kubernetes"

    def test_parent_none_unchanged(self):
        skills = [Skill(name="Python", parent=None)]
        result = normalize_skills(skills)
        assert result[0].parent is None

    def test_parent_empty_string(self):
        """空字符串 parent 不应触发归一化"""
        skills = [Skill(name="Python", parent="")]
        result = normalize_skills(skills)
        assert result[0].parent == ""

    def test_parent_with_alias(self):
        """确保各类 parent 别名都能归一化"""
        skills = [
            Skill(name="Docker Compose", parent="docker"),
            Skill(name="Redux", parent="react"),
            Skill(name="Vue Router", parent="vue"),
            Skill(name="Spring Boot", parent="spring"),
        ]
        result = normalize_skills(skills)
        assert result[0].parent == "Docker"
        assert result[1].parent == "React"
        assert result[2].parent == "Vue.js"
        assert result[3].parent == "Spring"

    def test_empty_list(self):
        result = normalize_skills([])
        assert result == []

    def test_preserves_other_fields(self):
        skills = [Skill(name="js", proficiency="熟练", category="编程语言")]
        result = normalize_skills(skills)
        assert result[0].proficiency == "熟练"
        assert result[0].category == "编程语言"

    def test_multiple_duplicates(self):
        skills = [
            Skill(name="vue"),
            Skill(name="Vue.js"),
            Skill(name="vue3"),
        ]
        result = normalize_skills(skills)
        assert len(result) == 1
        assert result[0].name == "Vue.js"
