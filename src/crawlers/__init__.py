"""职位抓取模块。"""

from src.crawlers.baidu import BaiduCrawler
from src.crawlers.tencent import TencentCrawler

__all__ = ["BaiduCrawler", "TencentCrawler"]
