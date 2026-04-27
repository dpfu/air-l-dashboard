from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from scripts.utils import now_iso, read_ndjson, write_json

PUBLIC_NDJSON = Path("data/public/posts.ndjson")
PUBLIC_DIR = Path("data/public")
SITE_DATA_DIR = Path("site/data")


def run() -> None:
    posts = read_ndjson(PUBLIC_NDJSON)
    posts = sorted(posts, key=lambda x: x["date"], reverse=True)
    latest = posts[:500]

    facets = {
        "categories": Counter(p.get("category", "other") for p in posts),
        "tags": Counter(tag for p in posts for tag in p.get("tags", [])),
        "years": Counter(datetime.fromisoformat(p["date"].replace("Z", "+00:00")).year for p in posts if p.get("date")),
    }

    search_index = [
        {
            "id": p["id"],
            "subject": p["subject"],
            "snippet": p.get("snippet", ""),
            "category": p.get("category", "other"),
            "tags": p.get("tags", []),
            "date": p.get("date"),
            "deadline": p.get("deadline"),
            "archive_url": p.get("archive_url"),
        }
        for p in posts
    ]

    stats = {
        "indexed_at": now_iso(),
        "total_posts": len(posts),
        "with_deadline": sum(1 for p in posts if p.get("deadline")),
        "categories": facets["categories"],
    }

    write_json(PUBLIC_DIR / "posts-latest.json", latest)
    write_json(PUBLIC_DIR / "search-index.json", search_index)
    write_json(PUBLIC_DIR / "facets.json", {k: dict(v) for k, v in facets.items()})
    write_json(PUBLIC_DIR / "stats.json", stats)

    write_json(SITE_DATA_DIR / "posts-latest.json", latest)
    write_json(SITE_DATA_DIR / "search-index.json", search_index)
    write_json(SITE_DATA_DIR / "facets.json", {k: dict(v) for k, v in facets.items()})
    write_json(SITE_DATA_DIR / "stats.json", stats)


if __name__ == "__main__":
    run()
