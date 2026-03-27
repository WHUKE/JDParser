"""JD 知识抽取 — 命令行入口

用法:
    # 仅使用正则解析（无需API）
    python -m src.main --mode regex

    # 使用 DeepSeek LLM 解析（需要设置环境变量 DEEPSEEK_API_KEY）
    python -m src.main --mode llm

    # 使用 Langbase 解析
    python -m src.main --mode langbase

    # 指定输入/输出目录
    python -m src.main --mode llm --input data/raw --output data/parsed
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from src import config
from src.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="JD 知识抽取工具")
    parser.add_argument(
        "--mode",
        choices=["regex", "llm", "langbase"],
        default="llm",
        help="解析模式: regex=仅正则, llm=DeepSeek+正则, langbase=Langbase+正则 (默认: llm)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=config.RAW_DATA_DIR,
        help=f"输入目录路径 (默认: {config.RAW_DATA_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=config.PARSED_DATA_DIR,
        help=f"输出目录路径 (默认: {config.PARSED_DATA_DIR})",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API Key (DeepSeek 通过 DEEPSEEK_API_KEY 环境变量, Langbase 通过 LANGBASE_API_KEY 环境变量)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志",
    )

    args = parser.parse_args()

    # 日志配置
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # API Key
    if args.mode == "llm":
        api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            print("错误: LLM 模式需要设置 DEEPSEEK_API_KEY 环境变量或使用 --api-key 参数")
            sys.exit(1)
    elif args.mode == "langbase":
        api_key = args.api_key or os.environ.get("LANGBASE_API_KEY")
        if not api_key:
            print("错误: Langbase 模式需要设置 LANGBASE_API_KEY 环境变量或使用 --api-key 参数")
            sys.exit(1)
    else:
        api_key = None

    # 执行
    pipeline = Pipeline.create(mode=args.mode, api_key=api_key)
    results = pipeline.process_directory(input_dir=args.input, output_dir=args.output)

    # 统计
    total_skills = sum(len(jd.required_skills) + len(jd.preferred_skills) for jd in results)
    print(f"\n完成! 处理了 {len(results)} 个JD, 共提取 {total_skills} 个技能项")


if __name__ == "__main__":
    main()