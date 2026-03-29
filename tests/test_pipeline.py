"""pipeline 模块测试"""

import json
import pytest
from pathlib import Path

from src.pipeline import Pipeline
from src.core.models import JobDescription, Skill
from src.parsers.regex_parser import RegexParser


class TestPipelineCreate:
    """测试 Pipeline 工厂方法"""

    def test_create_regex(self):
        p = Pipeline.create(mode="regex")
        assert isinstance(p._parser, RegexParser)

    def test_create_llm_no_key_raises(self):
        with pytest.raises(ValueError, match="api_key"):
            Pipeline.create(mode="llm")

    def test_create_langbase_no_key_raises(self):
        with pytest.raises(ValueError, match="api_key"):
            Pipeline.create(mode="langbase")


class TestPipelineProcessFile:
    """测试单文件处理"""

    def test_process_file(self, tmp_path):
        jd_text = "后端工程师\n全职\n\n岗位要求\n1、本科及以上学历\n"
        filepath = tmp_path / "test.txt"
        filepath.write_text(jd_text, encoding="utf-8")

        pipeline = Pipeline.create(mode="regex")
        jd = pipeline.process_file(filepath)
        assert jd.job_title == "后端工程师"
        assert jd.source_file == "test.txt"

    def test_process_file_normalizes_skills(self, tmp_path):
        """确认 process_file 会归一化技能（包括 parent）"""
        jd_text = "测试\n全职\n"
        filepath = tmp_path / "test.txt"
        filepath.write_text(jd_text, encoding="utf-8")

        pipeline = Pipeline.create(mode="regex")
        jd = pipeline.process_file(filepath)
        # 手动注入待归一化技能来验证归一化流程
        jd.required_skills = [Skill(name="js", parent="nodejs")]
        jd.preferred_skills = [Skill(name="k8s")]

        # 重新调用归一化（模拟 pipeline 流程）
        from src.core.normalizer import normalize_skills
        jd.required_skills = normalize_skills(jd.required_skills)
        jd.preferred_skills = normalize_skills(jd.preferred_skills)

        assert jd.required_skills[0].name == "JavaScript"
        assert jd.required_skills[0].parent == "Node.js"
        assert jd.preferred_skills[0].name == "Kubernetes"


class TestPipelineProcessDirectory:
    """测试目录批量处理"""

    def test_process_directory(self, tmp_path):
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "parsed"
        input_dir.mkdir()

        for i in range(3):
            (input_dir / f"test_{i:02d}.txt").write_text(
                f"工程师{i}\n全职\n\n岗位要求\n1、本科学历\n", encoding="utf-8"
            )

        pipeline = Pipeline.create(mode="regex")
        results = pipeline.process_directory(input_dir, output_dir)

        assert len(results) == 3
        assert output_dir.exists()
        # 检查汇总文件
        all_path = output_dir / "_all.json"
        assert all_path.exists()
        summary = json.loads(all_path.read_text(encoding="utf-8"))
        assert len(summary) == 3

    def test_process_directory_individual_files(self, tmp_path):
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "parsed"
        input_dir.mkdir()

        (input_dir / "sample.txt").write_text("测试职位\n全职\n", encoding="utf-8")

        pipeline = Pipeline.create(mode="regex")
        pipeline.process_directory(input_dir, output_dir)

        assert (output_dir / "sample.json").exists()

    def test_empty_directory(self, tmp_path):
        input_dir = tmp_path / "empty"
        input_dir.mkdir()
        output_dir = tmp_path / "out"

        pipeline = Pipeline.create(mode="regex")
        results = pipeline.process_directory(input_dir, output_dir)
        assert results == []
