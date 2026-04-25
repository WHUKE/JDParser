"""招聘站 raw 文本抓取 CLI。"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.core import config
from src.crawlers import BaiduCrawler, TencentCrawler


CRAWLER_BY_SITE = {
    "tencent": TencentCrawler,
    "baidu": BaiduCrawler,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="从招聘站批量抓取职位并落盘为 raw txt")
    parser.add_argument(
        "--site",
        choices=sorted(CRAWLER_BY_SITE),
        default="tencent",
        help="站点适配器，目前支持 tencent / baidu",
    )
    parser.add_argument(
        "--root-url",
        default=None,
        help="招聘根 URL，默认使用对应站点适配器内置根 URL",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出目录，默认 data/raw/<site>",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="最多抓取多少页列表 (默认: 5)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=10,
        help="每页职位数量 (默认: 10)",
    )
    parser.add_argument(
        "--keyword",
        default="",
        help="职位关键词过滤，例如 后端 / 算法 / 产品",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="详情请求间隔秒数 (默认: 0.2)",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=None,
        help="最多抓取多少个职位，便于调试",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的 txt 文件",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="打印详细日志",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.max_pages <= 0:
        print("错误: --max-pages 必须大于 0", file=sys.stderr)
        sys.exit(2)
    if args.page_size <= 0:
        print("错误: --page-size 必须大于 0", file=sys.stderr)
        sys.exit(2)

    crawler_cls = CRAWLER_BY_SITE[args.site]
    root_url = args.root_url or crawler_cls.ROOT_URL
    output_dir = args.output or (config.RAW_DATA_DIR / args.site)
    crawler = crawler_cls(root_url=root_url)

    stats = crawler.crawl(
        output_dir=output_dir,
        max_pages=args.max_pages,
        page_size=args.page_size,
        keyword=args.keyword,
        delay=args.delay,
        overwrite=args.overwrite,
        max_jobs=args.max_jobs,
    )

    print(
        "\n完成! "
        f"列表页: {stats.pages_fetched}, "
        f"看到职位: {stats.jobs_seen}, "
        f"新写入: {stats.jobs_written}, "
        f"跳过: {stats.jobs_skipped}, "
        f"失败: {stats.jobs_failed}"
    )
    print(f"输出目录: {output_dir}")
    print(f"manifest: {output_dir / 'manifest.jsonl'}")


if __name__ == "__main__":
    main()
