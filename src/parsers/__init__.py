"""解析器模块

提供三种 JD 解析策略:
- RegexParser:  纯正则/规则解析，无需外部 API
- LLMParser:    DeepSeek LLM + 正则预解析
- LangbaseParser:  Langbase Workflow + 正则预解析（支持分批并发）
"""

from src.parsers.base import BaseParser
from src.parsers.regex_parser import RegexParser
from src.parsers.llm_parser import LLMParser
from src.parsers.langbase_parser import LangbaseParser

__all__ = ["BaseParser", "RegexParser", "LLMParser", "LangbaseParser"]
