"""腾讯招聘爬虫测试。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.crawlers.models import ManifestRecord, RawJobPosting
from src.crawlers.storage import RawStorage
from src.crawlers.tencent import TencentCrawler
from src.crawlers.text_adapter import format_tencent_raw_text, split_numbered_items


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

    def get(self, url, params=None, headers=None, timeout=None):  # noqa: ANN001
        self.calls.append((url, params or {}))
        return self._responses.pop(0)


def _workspace_temp_dir(name: str) -> Path:
    base_dir = Path.cwd() / ".tmp" / name
    shutil.rmtree(base_dir, ignore_errors=True)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def test_split_numbered_items():
    text = "1. 第一条职责\r\n2. 第二条职责\r\n3. 第三条职责"
    assert split_numbered_items(text) == ["第一条职责", "第二条职责", "第三条职责"]


def test_format_tencent_raw_text_contains_expected_sections():
    job = RawJobPosting(
        source="tencent",
        post_id="123",
        detail_url="https://careers.tencent.com/jobdesc.html?postId=123",
        title="后端开发工程师",
        location="深圳",
        category="技术",
        business_group="CSIG",
        product_name="腾讯云",
        experience="3年以上工作经验",
        introduction="负责核心云产品研发。",
        responsibilities="1. 负责服务端开发\r\n2. 参与架构设计",
        requirements="1. 熟悉 Python\r\n2. 熟悉 MySQL",
        last_update_time="2026年4月22日",
    )

    content = format_tencent_raw_text(job)

    assert "后端开发工程师" in content
    assert "业务线：CSIG" in content
    assert "所属产品：腾讯云" in content
    assert "工作职责" in content
    assert "1、负责服务端开发" in content
    assert "任职要求" in content
    assert "2、熟悉 MySQL" in content


def test_raw_storage_write_and_manifest():
    tmp_path = _workspace_temp_dir("test_storage")
    storage = RawStorage(tmp_path)
    path, written = storage.write_text("123", "sample", overwrite=False)
    assert written is True
    assert path.read_text(encoding="utf-8") == "sample"

    storage.append_manifest(
        ManifestRecord(
            source="tencent",
            post_id="123",
            url="https://careers.tencent.com/jobdesc.html?postId=123",
            title="测试职位",
            status="success",
            file="123.txt",
            fetched_at="2026-04-22T12:00:00+08:00",
        )
    )
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    data = json.loads(manifest_lines[0])
    assert data["post_id"] == "123"
    assert data["file"] == "123.txt"


def test_tencent_crawler_writes_raw_files_and_manifest():
    fake_session = _FakeSession(
        [
            {
                "Code": 200,
                "Data": {
                    "Count": 1,
                    "Posts": [
                        {
                            "PostId": "123",
                            "PostURL": "https://careers.tencent.com/jobdesc.html?postId=123",
                            "RecruitPostName": "测试职位",
                        }
                    ],
                },
            },
            {
                "Code": 200,
                "Data": {
                    "PostId": "123",
                    "PostURL": "https://careers.tencent.com/jobdesc.html?postId=123",
                    "RecruitPostName": "测试职位",
                    "LocationName": "深圳",
                    "CategoryName": "技术",
                    "BGName": "CSIG",
                    "ProductName": "腾讯云",
                    "RequireWorkYearsName": "3年以上工作经验",
                    "Responsibility": "1. 负责开发\r\n2. 负责维护",
                    "Requirement": "1. 熟悉 Python\r\n2. 熟悉 MySQL",
                    "LastUpdateTime": "2026年4月22日",
                    "SourceID": 1,
                },
            },
        ]
    )
    crawler = TencentCrawler(session=fake_session)
    tmp_path = _workspace_temp_dir("test_crawler")
    stats = crawler.crawl(output_dir=tmp_path, max_pages=1, delay=0.0)

    assert stats.pages_fetched == 1
    assert stats.jobs_seen == 1
    assert stats.jobs_written == 1
    assert stats.jobs_failed == 0
    assert (tmp_path / "123.txt").exists()
    assert "工作职责" in (tmp_path / "123.txt").read_text(encoding="utf-8")
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    assert json.loads(manifest_lines[0])["status"] == "success"
    assert fake_session.calls[0][1]["parentCategoryId"] == "40001"
