"""爬虫基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.crawlers.models import CrawlStats


class BaseCrawler(ABC):
    """站点爬虫基类。"""

    @abstractmethod
    def crawl(self, *args, **kwargs) -> CrawlStats:
        """执行批量抓取。"""
        raise NotImplementedError
