"""解析结果查看 — 命令行入口

用法:
    # 加载全量结果（_all.json）并打印摘要
    python -m src.cli.load --all

    # 加载指定文件并打印摘要
    python -m src.cli.load --file xzl_16.json

    # 打印详细信息（含技能列表）
    python -m src.cli.load --all --verbose

    # 列出 data/parsed/ 下所有可用 JSON 文件
    python -m src.cli.load --list
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.core import config
from src.core.models import JobDescription
from src.loader import load_all, load_file


def _print_summary(jds: list[JobDescription], verbose: bool = False) -> None:
    """打印 JD 摘要表格"""
    print(f"\n{'─' * 70}")
    print(f"  共 {len(jds)} 条 JD")
    print(f"{'─' * 70}")

    for i, jd in enumerate(jds, 1):
        req_count = len(jd.required_skills)
        pref_count = len(jd.preferred_skills)
        print(
            f"  [{i:>3}] {jd.job_title or '(无标题)':<30} "
            f"来源: {jd.source_file:<15} "
            f"必需技能: {req_count:>2}  加分技能: {pref_count:>2}"
        )

        if verbose:
            if jd.location or jd.education or jd.experience:
                meta = "  ".join(filter(None, [jd.location, jd.education, jd.experience]))
                print(f"       📍 {meta}")
            if jd.required_skills:
                skill_names = ", ".join(s.name for s in jd.required_skills[:8])
                suffix = f" ...等{req_count}项" if req_count > 8 else ""
                print(f"       🔧 必需: {skill_names}{suffix}")
            if jd.preferred_skills:
                pref_names = ", ".join(s.name for s in jd.preferred_skills[:5])
                suffix = f" ...等{pref_count}项" if pref_count > 5 else ""
                print(f"       ⭐ 加分: {pref_names}{suffix}")
            print()

    print(f"{'─' * 70}")
    total_req = sum(len(jd.required_skills) for jd in jds)
    total_pref = sum(len(jd.preferred_skills) for jd in jds)
    print(f"  合计  必需技能: {total_req}  加分技能: {total_pref}  总计: {total_req + total_pref}")
    print(f"{'─' * 70}\n")


def _list_files(parsed_dir: Path) -> None:
    """列出 parsed 目录下所有 JSON 文件"""
    files = sorted(parsed_dir.glob("*.json"))
    if not files:
        print(f"目录 {parsed_dir} 下没有 JSON 文件")
        return
    print(f"\n{parsed_dir} 下共 {len(files)} 个 JSON 文件:")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:<30} {size_kb:>6.1f} KB")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="查看 JD 解析结果（data/parsed/ 目录）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="加载全量结果文件 (_all.json)",
    )
    group.add_argument(
        "--file",
        metavar="FILENAME",
        help="加载指定 JSON 文件，如: xzl_16.json",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="列出 data/parsed/ 下所有可用 JSON 文件",
    )

    parser.add_argument(
        "--dir",
        type=Path,
        default=config.PARSED_DATA_DIR,
        help=f"解析结果目录 (默认: {config.PARSED_DATA_DIR})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细信息（含技能列表）",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parsed_dir: Path = args.dir

    try:
        if args.list:
            _list_files(parsed_dir)

        elif args.all:
            jds = load_all(parsed_dir)
            _print_summary(jds, verbose=args.verbose)

        elif args.file:
            jds = load_file(args.file, parsed_dir)
            _print_summary(jds, verbose=args.verbose)

    except FileNotFoundError as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n未预期的错误: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
