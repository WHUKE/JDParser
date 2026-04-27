"""职位抓取模块。"""

from src.crawlers.baidu import BaiduCrawler
from src.crawlers.jd import JdCrawler
from src.crawlers.meituan import MeituanCrawler
from src.crawlers.tencent import TencentCrawler

__all__ = ["BaiduCrawler", "JdCrawler", "MeituanCrawler", "TencentCrawler"]
