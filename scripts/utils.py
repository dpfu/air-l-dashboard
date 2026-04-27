from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
NAMEY_SIGNATURE_RE = re.compile(r"(?im)^(best|regards|kind regards|cheers|sincerely)[\s\S]{0,180}$")
WHITESPACE_RE = re.compile(r"\s+")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def load_json(path: str | Path, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_ndjson(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_ndjson(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sanitize_text(value: str, max_len: int = 220) -> str:
    """Data-minimizing sanitizer for short snippets only.

    Removes emails, collapses whitespace, strips signature-like tails, and truncates.
    """
    cleaned = EMAIL_RE.sub("[redacted-email]", value or "")
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    cleaned = NAMEY_SIGNATURE_RE.sub("", cleaned).strip()
    if len(cleaned) > max_len:
        return cleaned[: max_len - 1].rstrip() + "…"
    return cleaned


def unique_tags(tags: list[str]) -> list[str]:
    return sorted(set(tags))
