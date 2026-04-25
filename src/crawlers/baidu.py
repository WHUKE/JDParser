"""百度招聘站点抓取。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.crawlers.base import BaseCrawler
from src.crawlers.models import CrawlStats, ManifestRecord, RawJobPosting
from src.crawlers.storage import RawStorage
from src.crawlers.text_adapter import format_baidu_raw_text

logger = logging.getLogger(__name__)


class BaiduCrawlerError(RuntimeError):
    """百度招聘接口异常。"""


class BaiduCrawler(BaseCrawler):
    """基于百度招聘官网职位列表接口的抓取器。"""

    SOURCE = "baidu"
    ROOT_URL = "https://talent.baidu.com/jobs/social"
    SEARCH_URL = "https://talent.baidu.com/jobs/social-list"
    LIST_API_URL = "https://talent.baidu.com/httservice/getPostListNew"

    def __init__(
        self,
        *,
        root_url: str = ROOT_URL,
        session: requests.Session | None = None,
        timeout: int = 20,
    ):
        self.root_url = root_url
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
            }
        )

    def crawl(
        self,
        *,
        output_dir: Path,
        max_pages: int,
        page_size: int = 10,
        keyword: str = "",
        delay: float = 0.0,
        overwrite: bool = False,
        max_jobs: int | None = None,
    ) -> CrawlStats:
        storage = RawStorage(output_dir)
        stats = CrawlStats()
        total_count: int | None = None

        for page_index in range(1, max_pages + 1):
            page_total, posts = self.fetch_page(
                page_index=page_index,
                page_size=page_size,
                keyword=keyword,
            )
            stats.pages_fetched += 1
            total_count = page_total if total_count is None else total_count

            if not posts:
                logger.info("第 %d 页没有返回职位，停止抓取。", page_index)
                break

            logger.info("第 %d 页返回 %d 个职位（站点总量 %s）", page_index, len(posts), total_count)

            for post in posts:
                if max_jobs is not None and stats.jobs_seen >= max_jobs:
                    return stats

                stats.jobs_seen += 1
                fetched_at = self._now_iso()
                try:
                    detail = self._to_raw_job(post)
                    content = format_baidu_raw_text(detail)
                    text_path, written = storage.write_text(detail.post_id, content, overwrite=overwrite)
                    status = "success" if written else "skipped"
                    if written:
                        stats.jobs_written += 1
                    else:
                        stats.jobs_skipped += 1

                    storage.append_manifest(
                        ManifestRecord(
                            source=self.SOURCE,
                            post_id=detail.post_id,
                            url=detail.detail_url,
                            title=detail.title,
                            status=status,
                            file=text_path.name,
                            fetched_at=fetched_at,
                            page_index=page_index,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    post_id = str(post.get("postId", ""))
                    logger.exception("抓取职位 %s 失败", post_id)
                    stats.jobs_failed += 1
                    storage.append_manifest(
                        ManifestRecord(
                            source=self.SOURCE,
                            post_id=post_id,
                            url=self._detail_url(post_id) if post_id else self.SEARCH_URL,
                            title=str(post.get("name", "")),
                            status="failed",
                            fetched_at=fetched_at,
                            message=str(exc),
                            page_index=page_index,
                        )
                    )

                if delay > 0:
                    time.sleep(delay)

            if total_count is not None and page_index * page_size >= total_count:
                break

        return stats

    def fetch_page(self, *, page_index: int, page_size: int, keyword: str = "") -> tuple[int, list[dict[str, Any]]]:
        payload = self._post_form(
            self.LIST_API_URL,
            data={
                "recruitType": "SOCIAL",
                "workPlace": "",
                "pageSize": str(page_size),
                "keyWord": keyword,
                "postType": "",
                "curPage": str(page_index),
                "projectType": "",
            },
            referer=self.SEARCH_URL,
        )
        data = self._unwrap_api_data(payload)
        return int(data.get("total") or 0), list(data.get("list") or [])

    def _post_form(self, url: str, *, data: dict[str, str], referer: str) -> dict[str, Any]:
        response = self.session.post(
            url,
            data=data,
            headers={
                "Referer": referer,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            return json.loads(response.content.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise BaiduCrawlerError(f"接口返回的 JSON 无法解析: {url}") from exc

    @staticmethod
    def _unwrap_api_data(payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("status") != "ok":
            raise BaiduCrawlerError(f"百度招聘接口返回异常: {payload.get('message')}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BaiduCrawlerError("百度招聘接口返回缺少 data 字段")
        return data

    def _to_raw_job(self, post: dict[str, Any]) -> RawJobPosting:
        post_id = str(post["postId"])
        update_date = self._clean_text(post.get("updateDate"))
        publish_date = self._clean_text(post.get("publishDate"))
        return RawJobPosting(
            source=self.SOURCE,
            post_id=post_id,
            detail_url=self._detail_url(post_id),
            title=str(post.get("name") or ""),
            location=self._clean_text(post.get("workPlace")),
            category=self._clean_text(post.get("postType")),
            business_group=self._clean_text(post.get("bgShortName")),
            company_name="百度",
            product_name=self._clean_text(post.get("orgName")),
            experience=self._clean_text(post.get("workYears")),
            responsibilities=self._clean_text(post.get("workContent")),
            requirements=self._clean_text(post.get("serviceCondition")),
            last_update_time=update_date or publish_date,
        )

    @staticmethod
    def _detail_url(post_id: str) -> str:
        return f"https://talent.baidu.com/jobs/detail/SOCIAL/{post_id}"

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
