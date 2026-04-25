"""百度招聘爬虫测试。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.crawlers.baidu import BaiduCrawler
from src.crawlers.models import RawJobPosting
from src.crawlers.text_adapter import format_baidu_raw_text, split_numbered_items


class _FakeResponse:
    def __init__(self, payload: dict):
        self.content = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, responses: list[dict]):
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


def test_split_numbered_items_strips_baidu_bullets():
    text = "-负责产品规划\n-推动项目落地"
    assert split_numbered_items(text) == ["负责产品规划", "推动项目落地"]


def test_format_baidu_raw_text_contains_expected_sections():
    job = RawJobPosting(
        source="baidu",
        post_id="abc",
        detail_url="https://talent.baidu.com/jobs/detail/SOCIAL/abc",
        title="平台产品经理",
        location="北京市",
        category="产品",
        business_group="ACG",
        company_name="百度",
        product_name="伐谋产品组",
        responsibilities="-负责平台能力设计\n-推动产品落地",
        requirements="-本科及以上学历\n-具备产品经验",
        last_update_time="2026-04-24",
    )

    content = format_baidu_raw_text(job)

    assert "平台产品经理" in content
    assert "业务线：ACG" in content
    assert "部门：伐谋产品组" in content
    assert "工作职责" in content
    assert "1、负责平台能力设计" in content
    assert "任职要求" in content
    assert "2、具备产品经验" in content


def test_baidu_crawler_writes_raw_files_and_manifest():
    fake_session = _FakeSession(
        [
            {
                "status": "ok",
                "data": {
                    "total": "1",
                    "list": [
                        {
                            "name": "平台产品经理",
                            "postId": "abc",
                            "postType": "产品",
                            "workPlace": "北京市",
                            "workYears": "",
                            "orgName": "伐谋产品组",
                            "bgShortName": "ACG",
                            "updateDate": "2026-04-24",
                            "workContent": "-负责平台能力设计\n-推动产品落地",
                            "serviceCondition": "-本科及以上学历\n-具备产品经验",
                        }
                    ],
                    "pageNum": 1,
                    "pageSize": 10,
                },
            }
        ]
    )
    crawler = BaiduCrawler(session=fake_session)
    tmp_path = _workspace_temp_dir("test_baidu_crawler")
    stats = crawler.crawl(output_dir=tmp_path, max_pages=1, delay=0.0)

    assert stats.pages_fetched == 1
    assert stats.jobs_seen == 1
    assert stats.jobs_written == 1
    assert stats.jobs_failed == 0
    assert (tmp_path / "abc.txt").exists()
    assert "工作职责" in (tmp_path / "abc.txt").read_text(encoding="utf-8")
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    assert json.loads(manifest_lines[0])["source"] == "baidu"
    assert fake_session.calls[0][1]["recruitType"] == "SOCIAL"
