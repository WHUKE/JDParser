"""爬虫层数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class RawJobPosting:
    """站点详情页抽象后的原始职位对象。"""

    source: str
    post_id: str
    detail_url: str
    title: str
    location: str | None = None
    category: str | None = None
    business_group: str | None = None
    company_name: str | None = None
    product_name: str | None = None
    experience: str | None = None
    introduction: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    last_update_time: str | None = None
    source_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass
class ManifestRecord:
    """单条抓取记录。"""

    source: str
    post_id: str
    url: str
    title: str
    status: str
    file: str | None = None
    fetched_at: str | None = None
    message: str | None = None
    page_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass
class CrawlStats:
    """批量抓取统计。"""

    pages_fetched: int = 0
    jobs_seen: int = 0
    jobs_written: int = 0
    jobs_skipped: int = 0
    jobs_failed: int = 0
