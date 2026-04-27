"""京东招聘爬虫测试。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.crawlers.jd import JdCrawler
from src.crawlers.models import RawJobPosting
from src.crawlers.text_adapter import format_jd_raw_text


class _FakeResponse:
    def __init__(self, payload):
        self.content = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, responses: list):
        self._responses = [_FakeResponse(item) for item in responses]
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, dict]] = []

    def post(self, url, data=None, headers=None, timeout=None):  # noqa: ANN001
        self.calls.append((url, data or {}))
        return self._responses.pop(0)


def _workspace_temp_dir(name: str) -> Path:
    base_dir = Path.cwd() / ".tmp" / name
    shutil.rmtree(base_dir, ignore_errors=True)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def test_format_jd_raw_text_contains_expected_sections():
    job = RawJobPosting(
        source="jd",
        post_id="216285",
        detail_url="https://zhaopin.jd.com/web/job-info-detail?requementId=216285",
        title="紧固件大客户销售经理",
        location="广东省",
        category="运营类",
        business_group="京东工业",
        company_name="京东",
        responsibilities="1、负责华南区紧固件全品类大客户开发\n2、完成年度销售指标",
        requirements="1、本科及以上学历\n2、5 年及以上行业经验",
        last_update_time="2026-04-27",
    )

    content = format_jd_raw_text(job)

    assert "紧固件大客户销售经理" in content
    assert "业务线：京东工业" in content
    assert "公司：京东" in content
    assert "岗位描述" in content
    assert "负责华南区紧固件全品类大客户开发" in content
    assert "任职要求" in content
    assert "5 年及以上行业经验" in content


def test_jd_crawler_writes_raw_files_and_manifest():
    fake_session = _FakeSession(
        [
            1,
            [
                {
                    "requirementId": 216285,
                    "positionId": 216211,
                    "positionName": "客户经理岗",
                    "positionNameOpen": "紧固件大客户销售经理",
                    "jobType": "运营类",
                    "workCity": "广东省",
                    "positionDeptName": "京东工业",
                    "publishTime": 1777219200000,
                    "formatPublishTime": "2026-04-27",
                    "workContent": "1、负责华南区紧固件全品类大客户开发",
                    "qualification": "1、本科及以上学历",
                }
            ],
        ]
    )
    crawler = JdCrawler(session=fake_session)
    tmp_path = _workspace_temp_dir("test_jd_crawler")
    stats = crawler.crawl(output_dir=tmp_path, max_pages=1, page_size=10, delay=0.0)

    assert stats.pages_fetched == 1
    assert stats.jobs_seen == 1
    assert stats.jobs_written == 1
    assert stats.jobs_failed == 0
    assert (tmp_path / "216285.txt").exists()
    assert "岗位描述" in (tmp_path / "216285.txt").read_text(encoding="utf-8")
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    assert json.loads(manifest_lines[0])["source"] == "jd"
    assert fake_session.calls[0][1]["jobSearch"] == ""
    assert fake_session.calls[0][1]["jobTypeJson"] == '["YANFA"]'
    assert fake_session.calls[0][1]["workCityJson"] == "[]"
    assert fake_session.calls[0][1]["depTypeJson"] == "[]"
    assert fake_session.calls[1][1]["pageIndex"] == "1"
    assert fake_session.calls[1][1]["pageSize"] == "10"
    assert fake_session.calls[1][1]["jobTypeJson"] == '["YANFA"]'
