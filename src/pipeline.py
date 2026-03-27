"""处理流水线 — 编排 读取→解析→归一化→输出 的完整流程"""

import json
import logging
from pathlib import Path

from src import config
from src.models import JobDescription
from src.normalizer import normalize_skills
from src.parsers import BaseParser, RegexParser, LLMParser, LangbaseParser

logger = logging.getLogger(__name__)


class Pipeline:
    """JD 知识抽取流水线"""

    def __init__(self, parser: BaseParser):
        self._parser = parser

    @classmethod
    def create(cls, mode: str = "regex", api_key: str | None = None) -> "Pipeline":
        """工厂方法

        Args:
            mode: "regex" 仅使用正则解析，"llm" 使用 DeepSeek+正则，"langbase" 使用 Langbase+正则
            api_key: DeepSeek API key（mode="llm" 时必需）或 Langbase API key（mode="langbase" 时必需）
        """
        if mode == "llm":
            if not api_key:
                raise ValueError("LLM 模式需要提供 api_key")
            parser = LLMParser(api_key=api_key)
        elif mode == "langbase":
            if not api_key:
                raise ValueError("Langbase 模式需要提供 api_key (Token)")
            parser = LangbaseParser(api_key=api_key)
        else:
            parser = RegexParser()
        return cls(parser)

    def process_file(self, filepath: Path) -> JobDescription:
        """处理单个 JD 文件"""
        text = filepath.read_text(encoding="utf-8")
        jd = self._parser.parse(text, filepath.name)
        # 归一化技能
        jd.required_skills = normalize_skills(jd.required_skills)
        jd.preferred_skills = normalize_skills(jd.preferred_skills)
        return jd

    def process_directory(self, input_dir: Path | None = None, output_dir: Path | None = None) -> list[JobDescription]:
        """批量处理目录下所有 txt 文件

        Args:
            input_dir: 输入目录，默认为 config.RAW_DATA_DIR
            output_dir: 输出目录，默认为 config.PARSED_DATA_DIR

        Returns:
            所有解析后的 JobDescription 列表
        """
        input_dir = input_dir or config.RAW_DATA_DIR
        output_dir = output_dir or config.PARSED_DATA_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        txt_files = sorted(input_dir.glob("*.txt"))
        if not txt_files:
            logger.warning("目录 %s 下未找到 txt 文件", input_dir)
            return []

        # Langbase 模式使用分批并发处理
        if isinstance(self._parser, LangbaseParser):
            results = self._process_directory_batch(txt_files, output_dir)
        else:
            results = self._process_directory_sequential(txt_files, output_dir)

        # 写入汇总文件
        summary_path = output_dir / "_all.json"
        summary = [jd.to_dict() for jd in results]
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("处理完成，共 %d 个文件，结果已输出到 %s", len(results), output_dir)

        return results

    def _process_directory_sequential(self, txt_files: list[Path], output_dir: Path) -> list[JobDescription]:
        """逐个处理（regex / llm 模式）"""
        results: list[JobDescription] = []
        total = len(txt_files)

        for i, filepath in enumerate(txt_files, 1):
            logger.info("[%d/%d] 正在处理: %s", i, total, filepath.name)
            try:
                jd = self.process_file(filepath)
                results.append(jd)

                out_path = output_dir / filepath.with_suffix(".json").name
                out_path.write_text(jd.to_json(), encoding="utf-8")
            except Exception as e:
                logger.error("处理 %s 失败: %s", filepath.name, e)

        return results

    def _process_directory_batch(self, txt_files: list[Path], output_dir: Path) -> list[JobDescription]:
        """分批并发处理（langbase 模式）

        一次触发 LANGBASE_BATCH_SIZE 个任务，批量轮询结果，再写入文件。
        """
        assert isinstance(self._parser, LangbaseParser)

        # 读取所有文件内容
        items: list[tuple[str, str]] = []  # (text, filename)
        filepaths: list[Path] = []
        for filepath in txt_files:
            try:
                text = filepath.read_text(encoding="utf-8")
                items.append((text, filepath.name))
                filepaths.append(filepath)
            except Exception as e:
                logger.error("读取 %s 失败: %s", filepath.name, e)

        if not items:
            return []

        logger.info("共 %d 个文件，每批 %d 个，分 %d 批处理",
                    len(items), config.LANGBASE_BATCH_SIZE,
                    (len(items) + config.LANGBASE_BATCH_SIZE - 1) // config.LANGBASE_BATCH_SIZE)

        # 分批触发 + 轮询
        jd_list = self._parser.parse_batch(items)

        # 归一化 + 写入文件
        results: list[JobDescription] = []
        for jd, filepath in zip(jd_list, filepaths):
            if jd is None:
                logger.error("处理 %s 无结果，跳过", filepath.name)
                continue

            jd.required_skills = normalize_skills(jd.required_skills)
            jd.preferred_skills = normalize_skills(jd.preferred_skills)
            results.append(jd)

            out_path = output_dir / filepath.with_suffix(".json").name
            out_path.write_text(jd.to_json(), encoding="utf-8")

        return results