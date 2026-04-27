"""将站点职位详情整理为 raw 文本。"""

from __future__ import annotations

import re

from src.crawlers.models import RawJobPosting


_NUMBERED_ITEM_RE = re.compile(r"(?:^|\n)\s*\d+[\.\、\)）]\s*")
_BULLET_ITEM_RE = re.compile(r"^\s*[-*•]\s*")


def split_numbered_items(text: str | None) -> list[str]:
    """将带编号的职责/要求文本拆成条目。"""

    if not text:
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    matches = list(_NUMBERED_ITEM_RE.finditer(normalized))
    if not matches:
        lines = [
            _BULLET_ITEM_RE.sub("", line).strip(" \t;；")
            for line in normalized.split("\n")
            if line.strip()
        ]
        return [line for line in lines if line]

    items: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        item = normalized[start:end].strip(" \n\t;；")
        item = re.sub(r"\s*\n\s*", "", item)
        item = _BULLET_ITEM_RE.sub("", item).strip(" \t;；")
        if item:
            items.append(item)
    return items


def _append_section(lines: list[str], title: str, content: str | None) -> None:
    if not content:
        return

    items = split_numbered_items(content)
    if not items:
        return

    if lines and lines[-1] != "":
        lines.append("")
    lines.append(title)
    for index, item in enumerate(items, 1):
        lines.append(f"{index}、{item}")


def format_tencent_raw_text(job: RawJobPosting) -> str:
    """将腾讯职位详情格式化为 data/raw 下的 txt 风格文本。"""

    lines: list[str] = [job.title]

    for value in (job.location, job.category, job.experience):
        if value:
            lines.append(value)

    meta_lines = []
    if job.business_group:
        meta_lines.append(f"业务线：{job.business_group}")
    if job.company_name:
        meta_lines.append(f"公司：{job.company_name}")
    if job.product_name:
        meta_lines.append(f"所属产品：{job.product_name}")
    if job.last_update_time:
        meta_lines.append(f"更新时间：{job.last_update_time}")

    if meta_lines:
        lines.append("")
        lines.extend(meta_lines)

    if job.introduction:
        lines.append("")
        lines.append("业务介绍")
        lines.extend(split_numbered_items(job.introduction))

    _append_section(lines, "工作职责", job.responsibilities)
    _append_section(lines, "任职要求", job.requirements)

    return "\n".join(lines).strip() + "\n"


def format_baidu_raw_text(job: RawJobPosting) -> str:
    """将百度职位列表数据格式化为 data/raw 下的 txt 风格文本。"""

    lines: list[str] = [job.title]

    for value in (job.location, job.category, job.experience):
        if value:
            lines.append(value)

    meta_lines = []
    if job.business_group:
        meta_lines.append(f"业务线：{job.business_group}")
    if job.product_name:
        meta_lines.append(f"部门：{job.product_name}")
    if job.company_name:
        meta_lines.append(f"公司：{job.company_name}")
    if job.last_update_time:
        meta_lines.append(f"更新时间：{job.last_update_time}")

    if meta_lines:
        lines.append("")
        lines.extend(meta_lines)

    _append_section(lines, "工作职责", job.responsibilities)
    _append_section(lines, "任职要求", job.requirements)

    return "\n".join(lines).strip() + "\n"


def format_meituan_raw_text(job: RawJobPosting) -> str:
    """将美团职位详情格式化为 data/raw 下的 txt 风格文本。"""

    lines: list[str] = [job.title]

    for value in (job.location, job.category, job.experience):
        if value:
            lines.append(value)

    meta_lines = []
    if job.business_group:
        meta_lines.append(f"部门：{job.business_group}")
    if job.product_name:
        meta_lines.append(f"职位族：{job.product_name}")
    if job.company_name:
        meta_lines.append(f"公司：{job.company_name}")
    if job.last_update_time:
        meta_lines.append(f"更新时间：{job.last_update_time}")

    if meta_lines:
        lines.append("")
        lines.extend(meta_lines)

    if job.introduction:
        lines.append("")
        lines.append("业务介绍")
        lines.extend(split_numbered_items(job.introduction))

    _append_section(lines, "工作职责", job.responsibilities)
    _append_section(lines, "任职要求", job.requirements)

    return "\n".join(lines).strip() + "\n"


def format_jd_raw_text(job: RawJobPosting) -> str:
    """将京东招聘列表数据格式化为 data/raw 下的 txt 风格文本。"""

    lines: list[str] = [job.title]

    for value in (job.location, job.category, job.experience):
        if value:
            lines.append(value)

    meta_lines = []
    if job.business_group:
        meta_lines.append(f"业务线：{job.business_group}")
    if job.product_name:
        meta_lines.append(f"所属部门：{job.product_name}")
    if job.company_name:
        meta_lines.append(f"公司：{job.company_name}")
    if job.last_update_time:
        meta_lines.append(f"发布时间：{job.last_update_time}")

    if meta_lines:
        lines.append("")
        lines.extend(meta_lines)

    if job.introduction:
        lines.append("")
        lines.append("职位介绍")
        lines.extend(split_numbered_items(job.introduction))

    _append_section(lines, "岗位描述", job.responsibilities)
    _append_section(lines, "任职要求", job.requirements)

    return "\n".join(lines).strip() + "\n"
