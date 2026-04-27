"""美团招聘站点抓取。"""

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
from src.crawlers.text_adapter import format_meituan_raw_text

logger = logging.getLogger(__name__)


class MeituanCrawlerError(RuntimeError):
    """美团招聘接口异常。"""


class MeituanCrawler(BaseCrawler):
    """基于美团招聘官网职位列表和详情接口的抓取器。"""

    SOURCE = "meituan"
    ROOT_URL = "https://zhaopin.meituan.com/web/position"
    LIST_API_URL = "https://zhaopin.meituan.com/api/official/job/getJobList"
    DETAIL_API_URL = "https://zhaopin.meituan.com/api/official/job/getJobDetail"
    TECH_JF_JG_LIST = [{"code": "11001", "subCode": []}]

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
                "Origin": "https://zhaopin.meituan.com",
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
                post_id = str(post.get("jobUnionId") or "")
                try:
                    detail = self.fetch_detail(post_id)
                    content = format_meituan_raw_text(detail)
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
                    logger.exception("抓取职位 %s 失败", post_id)
                    stats.jobs_failed += 1
                    storage.append_manifest(
                        ManifestRecord(
                            source=self.SOURCE,
                            post_id=post_id,
                            url=self._detail_url(post_id) if post_id else self.root_url,
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
        payload = self._post_json(
            self.LIST_API_URL,
            data={
                "page": {"pageNo": page_index, "pageSize": page_size},
                "jobShareType": "1",
                "keywords": keyword,
                "cityList": [],
                "department": [],
                "jfJgList": self.TECH_JF_JG_LIST,
                "jobType": [{"code": "3", "subCode": []}],
                "typeCode": [],
                "specialCode": [],
            },
            referer=self.root_url,
        )
        data = self._unwrap_api_data(payload)
        page = data.get("page") or {}
        return int(page.get("totalCount") or 0), list(data.get("list") or [])

    def fetch_detail(self, post_id: str) -> RawJobPosting:
        if not post_id:
            raise MeituanCrawlerError("缺少 jobUnionId")

        detail_url = self._detail_url(post_id)
        payload = self._post_json(
            self.DETAIL_API_URL,
            data={"jobUnionId": post_id, "jobShareType": "1"},
            referer=detail_url,
        )
        data = self._unwrap_api_data(payload)
        return self._to_raw_job(data)

    def _post_json(self, url: str, *, data: dict[str, Any], referer: str) -> dict[str, Any]:
        response = self.session.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={
                "Referer": referer,
                "Content-Type": "application/json;charset=UTF-8",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            return json.loads(response.content.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise MeituanCrawlerError(f"接口返回的 JSON 无法解析: {url}") from exc

    @staticmethod
    def _unwrap_api_data(payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("status") != 1:
            raise MeituanCrawlerError(f"美团招聘接口返回异常: {payload.get('message')}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise MeituanCrawlerError("美团招聘接口返回缺少 data 字段")
        return data

    def _to_raw_job(self, data: dict[str, Any]) -> RawJobPosting:
        post_id = str(data["jobUnionId"])
        return RawJobPosting(
            source=self.SOURCE,
            post_id=post_id,
            detail_url=self._detail_url(post_id),
            title=str(data.get("name") or ""),
            location=self._join_names(data.get("cityList")),
            category=self._clean_text(data.get("jobFamily")),
            business_group=self._join_names(data.get("department")),
            company_name="美团",
            product_name=self._clean_text(data.get("jobFamilyGroup")),
            experience=self._clean_text(data.get("workYear")),
            introduction=self._join_text(data.get("departmentIntro"), data.get("highLight")),
            responsibilities=self._clean_text(data.get("jobDuty")),
            requirements=self._join_text(data.get("jobRequirement"), data.get("precedence")),
            last_update_time=self._format_timestamp(data.get("refreshTime")),
        )

    @staticmethod
    def _detail_url(post_id: str) -> str:
        return f"https://zhaopin.meituan.com/web/position/detail?jobUnionId={post_id}&jobShareType=1"

    @staticmethod
    def _join_names(value: Any) -> str | None:
        if not isinstance(value, list):
            return None
        names = [str(item.get("name")).strip() for item in value if isinstance(item, dict) and item.get("name")]
        return "、".join(names) or None

    @classmethod
    def _join_text(cls, *values: Any) -> str | None:
        parts = [text for value in values if (text := cls._clean_text(value))]
        return "\n".join(parts) or None

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _format_timestamp(value: Any) -> str | None:
        if value is None:
            return None
        try:
            seconds = int(value) / 1000
        except (TypeError, ValueError):
            return str(value).strip() or None
        return datetime.fromtimestamp(seconds).date().isoformat()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
