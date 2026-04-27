"""美团招聘爬虫测试。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.crawlers.meituan import MeituanCrawler
from src.crawlers.models import RawJobPosting
from src.crawlers.text_adapter import format_meituan_raw_text


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
        decoded = json.loads(data.decode("utf-8"))
        self.calls.append((url, decoded))
        return self._responses.pop(0)


def _workspace_temp_dir(name: str) -> Path:
    base_dir = Path.cwd() / ".tmp" / name
    shutil.rmtree(base_dir, ignore_errors=True)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def test_format_meituan_raw_text_contains_expected_sections():
    job = RawJobPosting(
        source="meituan",
        post_id="2384830163",
        detail_url="https://zhaopin.meituan.com/web/position/detail?jobUnionId=2384830163&jobShareType=1",
        title="美团团购品牌营销岗",
        location="北京市",
        category="市场营销类",
        business_group="核心本地商业-美团平台",
        company_name="美团",
        product_name="营销",
        experience="5年",
        introduction="良好业务前景和公司实力。",
        responsibilities="1.负责品牌定位\n2.推动营销项目落地",
        requirements="1.本科及以上学历\n2.有互联网经验者优先",
        last_update_time="2026-04-25",
    )

    content = format_meituan_raw_text(job)

    assert "美团团购品牌营销岗" in content
    assert "部门：核心本地商业-美团平台" in content
    assert "职位族：营销" in content
    assert "业务介绍" in content
    assert "1、负责品牌定位" in content
    assert "2、有互联网经验者优先" in content


def test_meituan_crawler_writes_raw_files_and_manifest():
    fake_session = _FakeSession(
        [
            {
                "status": 1,
                "message": "成功",
                "data": {
                    "list": [{"jobUnionId": "2384830163", "name": "美团团购品牌营销岗"}],
                    "page": {"pageNo": 1, "pageSize": 10, "totalPage": 1, "totalCount": 1},
                },
            },
            {
                "status": 1,
                "message": "成功",
                "data": {
                    "jobUnionId": "2384830163",
                    "name": "美团团购品牌营销岗",
                    "jobFamily": "市场营销类",
                    "jobFamilyGroup": "营销",
                    "cityList": [{"name": "北京市"}],
                    "workYear": "5年",
                    "department": [{"name": "核心本地商业-美团平台"}],
                    "departmentIntro": "美团平台介绍",
                    "jobDuty": "1.负责品牌定位\n2.推动营销项目落地",
                    "jobRequirement": "1.本科及以上学历",
                    "precedence": "有互联网经验者优先。",
                    "refreshTime": 1777098600000,
                },
            },
        ]
    )
    crawler = MeituanCrawler(session=fake_session)
    tmp_path = _workspace_temp_dir("test_meituan_crawler")
    stats = crawler.crawl(output_dir=tmp_path, max_pages=1, delay=0.0)

    assert stats.pages_fetched == 1
    assert stats.jobs_seen == 1
    assert stats.jobs_written == 1
    assert stats.jobs_failed == 0
    assert (tmp_path / "2384830163.txt").exists()
    assert "工作职责" in (tmp_path / "2384830163.txt").read_text(encoding="utf-8")
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    assert json.loads(manifest_lines[0])["source"] == "meituan"
    assert fake_session.calls[0][1]["jfJgList"] == [{"code": "11001", "subCode": []}]
    assert fake_session.calls[0][1]["jobType"] == [{"code": "3", "subCode": []}]
    assert fake_session.calls[1][1]["jobUnionId"] == "2384830163"
