"""解析结果 JSON 加载器

提供两种加载方式：
- load_all()        — 读取 data/parsed/_all.json，返回全量 JobDescription 列表
- load_file(name)   — 读取指定 JSON 文件（单条或数组），返回 JobDescription 列表

示例（Python API）::

    from src.loader import load_all, load_file

    jds = load_all()
    print(jds[0].job_title)

    jds = load_file("xzl_16.json")
    print(jds[0].required_skills)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.core import config
from src.core.models import JobDescription, Skill

logger = logging.getLogger(__name__)

# _all.json 的文件名约定（与 pipeline.py 保持一致）
_ALL_FILENAME = "_all.json"


# ── 公共 API ──────────────────────────────────────────────────────────────────

def load_all(parsed_dir: Path | None = None) -> list[JobDescription]:
    """加载全量解析结果（读取 _all.json）

    Args:
        parsed_dir: 解析结果目录，默认为 config.PARSED_DATA_DIR

    Returns:
        JobDescription 列表（按文件中顺序）

    Raises:
        FileNotFoundError: 若 _all.json 不存在
    """
    parsed_dir = parsed_dir or config.PARSED_DATA_DIR
    all_path = parsed_dir / _ALL_FILENAME

    if not all_path.exists():
        raise FileNotFoundError(
            f"全量文件不存在: {all_path}\n"
            f"请先运行 `python -m src.cli.extract` 生成解析结果。"
        )

    logger.info("加载全量文件: %s", all_path)
    raw: list[dict[str, Any]] = json.loads(all_path.read_text(encoding="utf-8"))
    jds = [_dict_to_jd(d) for d in raw]
    logger.info("共加载 %d 条 JD", len(jds))
    return jds


def load_file(filename: str, parsed_dir: Path | None = None) -> list[JobDescription]:
    """加载指定 JSON 文件

    支持两种格式：
    - 单个对象 ``{...}``           → 返回长度为 1 的列表
    - 对象数组 ``[{...}, {...}]``  → 返回完整列表

    Args:
        filename: JSON 文件名，如 ``"xzl_16.json"``（不含路径）
        parsed_dir: 解析结果目录，默认为 config.PARSED_DATA_DIR

    Returns:
        JobDescription 列表

    Raises:
        FileNotFoundError: 若指定文件不存在
    """
    parsed_dir = parsed_dir or config.PARSED_DATA_DIR
    filepath = parsed_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(
            f"文件不存在: {filepath}\n"
            f"可用文件: {[p.name for p in sorted(parsed_dir.glob('*.json'))]}"
        )

    logger.info("加载文件: %s", filepath)
    content = json.loads(filepath.read_text(encoding="utf-8"))

    if isinstance(content, dict):
        jds = [_dict_to_jd(content)]
    elif isinstance(content, list):
        jds = [_dict_to_jd(d) for d in content]
    else:
        raise ValueError(f"无法识别的 JSON 格式: {type(content)}")

    logger.info("共加载 %d 条 JD（来自 %s）", len(jds), filename)
    return jds


# ── 内部工具 ──────────────────────────────────────────────────────────────────

def _dict_to_skill(d: dict[str, Any]) -> Skill:
    """将字典还原为 Skill 对象"""
    return Skill(
        name=d.get("name", ""),
        proficiency=d.get("proficiency"),
        category=d.get("category"),
        parent=d.get("parent"),
    )


def _dict_to_jd(d: dict[str, Any]) -> JobDescription:
    """将字典还原为 JobDescription 对象"""
    return JobDescription(
        source_file=d.get("source_file", ""),
        job_title=d.get("job_title"),
        location=d.get("location"),
        education=d.get("education"),
        experience=d.get("experience"),
        department=d.get("department"),
        employment_type=d.get("employment_type"),
        headcount=d.get("headcount"),
        publish_date=d.get("publish_date"),
        job_category=d.get("job_category"),
        target_group=d.get("target_group"),
        responsibilities=d.get("responsibilities", []),
        required_skills=[_dict_to_skill(s) for s in d.get("required_skills", [])],
        preferred_skills=[_dict_to_skill(s) for s in d.get("preferred_skills", [])],
        raw_requirements=d.get("raw_requirements", []),
    )
