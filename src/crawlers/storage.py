"""raw 文本和 manifest 落盘。"""

from __future__ import annotations

import json
from pathlib import Path

from src.crawlers.models import ManifestRecord


class RawStorage:
    """管理 raw 文本和 manifest 文件。"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.output_dir / "manifest.jsonl"

    def get_text_path(self, post_id: str) -> Path:
        return self.output_dir / f"{post_id}.txt"

    def write_text(self, post_id: str, content: str, *, overwrite: bool = False) -> tuple[Path, bool]:
        path = self.get_text_path(post_id)
        if path.exists() and not overwrite:
            return path, False
        path.write_text(content, encoding="utf-8")
        return path, True

    def append_manifest(self, record: ManifestRecord) -> None:
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False))
            handle.write("\n")
