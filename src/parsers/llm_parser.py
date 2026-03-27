"""基于 DeepSeek LLM 的 JD 知识抽取解析器

使用 LLM 从 JD 文本中提取细粒度技能、职责等结构化信息，
并由 RegexParser 预解析的元数据进行补充。
"""

import json
import logging
import time
from typing import Any

from openai import OpenAI

from src import config
from src.models import JobDescription
from src.parsers.base import BaseParser
from src.parsers.regex_parser import RegexParser

logger = logging.getLogger(__name__)


class LLMParser(BaseParser):
    """使用 DeepSeek API 进行深度知识抽取"""

    def __init__(self, api_key: str):
        self._client = OpenAI(
            api_key=api_key,
            base_url=config.DEEPSEEK_BASE_URL,
        )
        self._regex_parser = RegexParser()
        self._last_request_time = 0.0

    def parse(self, text: str, filename: str) -> JobDescription:
        # 先用正则解析器提取基础字段
        jd = self._regex_parser.parse(text, filename)

        # 调用 LLM 提取深层知识
        llm_result = self._call_llm(text)
        if llm_result:
            self.merge_extracted_result(jd, llm_result)

        return jd

    def _call_llm(self, text: str) -> dict[str, Any] | None:
        """调用 DeepSeek API 并解析返回的 JSON"""
        # 速率限制
        elapsed = time.time() - self._last_request_time
        if elapsed < config.LLM_REQUEST_INTERVAL:
            time.sleep(config.LLM_REQUEST_INTERVAL - elapsed)

        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                self._last_request_time = time.time()
                response = self._client.chat.completions.create(
                    model=config.DEEPSEEK_MODEL,
                    temperature=config.LLM_TEMPERATURE,
                    messages=[
                        {"role": "system", "content": config.SYSTEM_PROMPT},
                        {"role": "user", "content": f"请从以下JD中提取结构化信息：\n\n{text}"},
                    ],
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if content:
                    return json.loads(content)
            except json.JSONDecodeError:
                logger.warning("LLM 返回的JSON解析失败 (尝试 %d/%d)", attempt + 1, config.LLM_MAX_RETRIES)
            except Exception as e:
                logger.warning("LLM 请求失败 (尝试 %d/%d): %s", attempt + 1, config.LLM_MAX_RETRIES, e)
                if attempt < config.LLM_MAX_RETRIES - 1:
                    time.sleep(config.LLM_RETRY_DELAY * (attempt + 1))

        logger.error("LLM 调用最终失败，将仅使用正则解析结果")
        return None
