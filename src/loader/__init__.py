"""数据加载模块 — 读取 data/parsed/ 下的 JSON 文件，还原为 JobDescription 对象"""

from src.loader.loader import load_all, load_file

__all__ = ["load_all", "load_file"]
