"""基于 Langbase 平台的 JD 知识抽取解析器

通过 Langbase API 调用预配置的 Workflow 应用来提取 JD 结构化信息。
Workflow 为异步执行：先 trigger 获取 runID，再轮询 workflow-runs 获取结果。
支持分批并发触发以提升吞吐量。
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from src.core import config
from src.core.models import JobDescription
from src.parsers.base import BaseParser
from src.parsers.regex_parser import RegexParser

logger = logging.getLogger(__name__)


@dataclass
class _TaskInfo:
    """记录一个已触发的 workflow 任务"""
    index: int          # 在批次中的序号
    filename: str       # 源文件名
    app_id: str         # Langbase appID
    run_id: str         # Langbase runID
    jd: JobDescription  # 正则预解析结果
    text: str = ""      # 原始 JD 文本，用于限流失败后重新触发
    retry_count: int = 0  # 已重试次数


class LangbaseParser(BaseParser):
    """使用 Langbase Workflow API 进行深度知识抽取（支持分批并发）"""

    def __init__(self, api_key: str | None = None):
        if not api_key:
            raise ValueError("Langbase 模式需要提供 api_key (Token)")
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })
        self._regex_parser = RegexParser()
        self._last_request_time = 0.0

    # ── 单文件解析（BaseParser 接口） ──

    def parse(self, text: str, filename: str) -> JobDescription:
        jd = self._regex_parser.parse(text, filename)

        result = self._call_single(text)
        if result:
            self.merge_extracted_result(jd, result)

        return jd

    # ── 批量解析 ──

    def parse_batch(self, items: list[tuple[str, str]]) -> list[JobDescription]:
        """分批处理多个 JD

        Args:
            items: [(text, filename), ...] 列表

        Returns:
            与输入顺序对应的 JobDescription 列表
        """
        total = len(items)
        batch_size = config.LANGBASE_BATCH_SIZE
        results: list[JobDescription] = [None] * total  # type: ignore[list-item]

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_items = items[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info("━━ 批次 %d/%d: 触发 %d 个任务 (第 %d-%d 个) ━━",
                        batch_num, total_batches, len(batch_items),
                        batch_start + 1, batch_end)

            # Step 1: 批量触发
            tasks: list[_TaskInfo] = []
            for i, (text, filename) in enumerate(batch_items):
                global_idx = batch_start + i
                jd = self._regex_parser.parse(text, filename)

                run_info = self._trigger(text)
                if run_info and run_info.get("runID"):
                    tasks.append(_TaskInfo(
                        index=global_idx,
                        filename=filename,
                        app_id=run_info.get("appID", config.LANGBASE_APP_ID),
                        run_id=run_info["runID"],
                        jd=jd,
                        text=text,
                    ))
                    logger.info("  [%d/%d] %s → runID=%s",
                                i + 1, len(batch_items), filename, run_info["runID"])
                else:
                    logger.warning("  [%d/%d] %s → 触发失败，使用正则结果",
                                   i + 1, len(batch_items), filename)
                    results[global_idx] = jd

                self._rate_limit()

            if not tasks:
                continue

            # Step 2: 批量轮询
            logger.info("━━ 批次 %d/%d: 等待 %d 个任务完成 ━━",
                        batch_num, total_batches, len(tasks))
            self._poll_batch(tasks)

            # Step 3: 收集结果
            for task in tasks:
                results[task.index] = task.jd

        return results

    # ── 内部方法 ──

    @staticmethod
    def _is_rate_limit_failure(message: str) -> bool:
        """判断 workflow failed 消息是否由上游限流（429）引起"""
        return "429" in message or "Too Many Requests" in message or "too_many_requests" in message

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < config.LANGBASE_REQUEST_INTERVAL:
            time.sleep(config.LANGBASE_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _call_single(self, text: str, retry_count: int = 0) -> dict[str, Any] | None:
        """单任务：触发 → 轮询 → 返回结果，支持限流失败后重试"""
        self._rate_limit()

        run_info = self._trigger(text)
        if not run_info or not run_info.get("runID"):
            logger.error("Langbase trigger 返回中无 runID: %s", run_info)
            return None

        app_id = run_info.get("appID", config.LANGBASE_APP_ID)
        run_id = run_info["runID"]
        logger.info("Langbase workflow 已触发, runID=%s, 等待执行完成...", run_id)
        return self._poll_single(app_id, run_id, text=text, retry_count=retry_count)

    def _trigger(self, text: str) -> dict[str, Any] | None:
        """调用 trigger 接口启动 Workflow"""
        payload = {
            "appID": config.LANGBASE_APP_ID,
            "inputs": {
                "text": text,
                "system_prompt": config.SYSTEM_PROMPT,
            },
            "bizContext": "jd_parsing",
            "bizInfo": {
                "business": "langbase",
                "scene": "langbase-test",
            },
        }

        for attempt in range(config.LANGBASE_MAX_RETRIES):
            try:
                self._last_request_time = time.time()
                resp = self._session.post(
                    config.LANGBASE_TRIGGER_URL, json=payload,
                    timeout=config.LANGBASE_TIMEOUT,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.debug("Langbase trigger 响应: %s", result)
                return result.get("data", result)

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 0
                if status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", config.LANGBASE_RETRY_DELAY * (attempt + 2)))
                    logger.warning("Langbase trigger 触发限流 429 (%d/%d), 等待 %ds",
                                   attempt + 1, config.LANGBASE_MAX_RETRIES, retry_after)
                    time.sleep(retry_after)
                else:
                    logger.warning("Langbase trigger HTTP 错误 (%d/%d): %s | %s",
                                   attempt + 1, config.LANGBASE_MAX_RETRIES, e, resp.text)
                    if attempt < config.LANGBASE_MAX_RETRIES - 1:
                        time.sleep(config.LANGBASE_RETRY_DELAY * (attempt + 1))
            except requests.exceptions.RequestException as e:
                logger.warning("Langbase trigger 请求失败 (%d/%d): %s",
                               attempt + 1, config.LANGBASE_MAX_RETRIES, e)
                if attempt < config.LANGBASE_MAX_RETRIES - 1:
                    time.sleep(config.LANGBASE_RETRY_DELAY * (attempt + 1))

        logger.error("Langbase trigger 最终失败")
        return None

    def _poll_single(self, app_id: str, run_id: str, *,
                     text: str = "", retry_count: int = 0) -> dict[str, Any] | None:
        """轮询单个 workflow 任务直到完成，失败时若为限流错误则重新触发"""
        url = f"{config.LANGBASE_BASE_URL}/app/workflow-runs"
        params = {"appID": app_id, "runID": run_id}

        for i in range(config.LANGBASE_POLL_MAX_ATTEMPTS):
            time.sleep(config.LANGBASE_POLL_INTERVAL)
            try:
                self._rate_limit()
                resp = self._session.get(url, params=params, timeout=config.LANGBASE_TIMEOUT)
                resp.raise_for_status()
                data = resp.json().get("data", resp.json())
                status = data.get("status", "unknown")

                logger.debug("workflow 状态 [%d/%d]: %s",
                             i + 1, config.LANGBASE_POLL_MAX_ATTEMPTS, status)

                if status == "success":
                    return self._parse_outputs(data.get("outputs", {}))
                elif status == "failed":
                    message = data.get("message", "未知错误")
                    if text and retry_count < config.LANGBASE_MAX_RETRIES and self._is_rate_limit_failure(message):
                        wait = config.LANGBASE_RETRY_DELAY * (retry_count + 2)
                        logger.warning("workflow 限流失败，%ds 后重新触发 (第 %d 次重试): %s",
                                       wait, retry_count + 1, message[:200])
                        time.sleep(wait)
                        return self._call_single(text, retry_count=retry_count + 1)
                    logger.error("workflow 执行失败: %s", message)
                    return None

            except requests.exceptions.RequestException as e:
                logger.warning("轮询请求失败 [%d/%d]: %s",
                               i + 1, config.LANGBASE_POLL_MAX_ATTEMPTS, e)

        logger.error("workflow 轮询超时 (%.0fs)",
                     config.LANGBASE_POLL_MAX_ATTEMPTS * config.LANGBASE_POLL_INTERVAL)
        return None

    def _poll_batch(self, tasks: list[_TaskInfo]) -> None:
        """批量轮询多个 workflow 任务，直到全部完成或超时"""
        url = f"{config.LANGBASE_BASE_URL}/app/workflow-runs"
        pending = list(tasks)

        for poll_round in range(config.LANGBASE_POLL_MAX_ATTEMPTS):
            if not pending:
                break
            time.sleep(config.LANGBASE_POLL_INTERVAL)

            still_pending: list[_TaskInfo] = []
            for task in pending:
                self._rate_limit()
                try:
                    resp = self._session.get(
                        url, params={"appID": task.app_id, "runID": task.run_id},
                        timeout=config.LANGBASE_TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json().get("data", resp.json())
                    status = data.get("status", "unknown")

                    if status == "success":
                        result = self._parse_outputs(data.get("outputs", {}))
                        if result:
                            self.merge_extracted_result(task.jd, result)
                        logger.info("  ✓ %s (runID=%s) 完成", task.filename, task.run_id)

                    elif status == "failed":
                        message = data.get("message", "未知错误")
                        if task.text and task.retry_count < config.LANGBASE_MAX_RETRIES \
                                and self._is_rate_limit_failure(message):
                            wait = config.LANGBASE_RETRY_DELAY * (task.retry_count + 2)
                            logger.warning("  ↻ %s 限流失败，%ds 后重新触发 (第 %d 次重试)",
                                           task.filename, wait, task.retry_count + 1)
                            time.sleep(wait)
                            self._rate_limit()
                            run_info = self._trigger(task.text)
                            if run_info and run_info.get("runID"):
                                task.run_id = run_info["runID"]
                                task.retry_count += 1
                                still_pending.append(task)
                                logger.info("  ↻ %s 重新触发成功 → runID=%s",
                                            task.filename, task.run_id)
                            else:
                                logger.error("  ✗ %s 重新触发失败，放弃", task.filename)
                        else:
                            logger.error("  ✗ %s (runID=%s) 失败: %s",
                                         task.filename, task.run_id, message)

                    elif status in ("running", "queued"):
                        still_pending.append(task)
                    else:
                        logger.warning("  ? %s 未知状态: %s", task.filename, status)
                        still_pending.append(task)

                except requests.exceptions.RequestException as e:
                    logger.warning("  轮询 %s 失败: %s", task.filename, e)
                    still_pending.append(task)

            pending = still_pending
            if pending:
                logger.debug("轮询第 %d 轮, 剩余 %d 个未完成", poll_round + 1, len(pending))

        if pending:
            logger.error("%d 个任务超时: %s", len(pending), [t.filename for t in pending])

    # ── 结果解析 ──

    @staticmethod
    def _parse_outputs(outputs: dict[str, Any]) -> dict[str, Any] | None:
        """解析 workflow outputs，尝试从 param1 或其他字段中提取 JSON"""
        raw = outputs.get("param1") or outputs.get("output") or ""

        if not raw and len(outputs) == 1:
            raw = next(iter(outputs.values()))

        if not raw:
            logger.warning("workflow outputs 为空: %s", outputs)
            return None

        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("输出无法解析为 JSON: %s", raw[:300])
                return None
        return None