from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

from scripts.classify import build_metadata_snippet, classify_post
from scripts.scrape import _fetch_text, extract_transient_detail
from scripts.utils import now_iso, read_ndjson, unique_tags, write_json, write_ndjson

PUBLIC_PATH = Path("data/public/posts.ndjson")
REFRESH_LOG_PATH = Path("data/internal/deadline-refresh.json")


def refresh_cfp_deadlines(delay_seconds: float = 0.5, limit: int | None = None) -> None:
    posts = read_ndjson(PUBLIC_PATH)
    candidates = [post for post in posts if post.get("category") == "call_for_papers" and post.get("archive_url")]
    if limit:
        candidates = candidates[:limit]

    by_id = {post["id"]: post for post in posts}
    changes = []
    failures = []

    for post in candidates:
        status, html = _fetch_text(post["archive_url"])
        if status != 200:
            failures.append({"id": post["id"], "status": status})
            continue

        transient_body, parsed_date = extract_transient_detail(html)
        reference_date = post.get("date") or parsed_date
        classified = classify_post(post.get("subject", ""), transient_body, reference_date=reference_date)

        updated = by_id[post["id"]]
        old_deadline = updated.get("deadline")
        deadline = classified.deadline
        event_date = classified.event_date
        tags = list(classified.tags)
        if deadline:
            tags.append("deadline")
        tags = unique_tags(tags)

        updated["category"] = classified.category
        updated["tags"] = tags
        updated["deadline"] = deadline
        updated["event_date"] = event_date
        updated["snippet"] = build_metadata_snippet(classified.category, tags, deadline, event_date)

        if old_deadline != deadline:
            changes.append({
                "id": post["id"],
                "from": old_deadline,
                "to": deadline,
                "subject": post.get("subject", ""),
            })

        time.sleep(delay_seconds)

    refreshed_posts = sorted(by_id.values(), key=lambda post: post.get("date") or "", reverse=True)
    write_ndjson(PUBLIC_PATH, refreshed_posts)

    write_json(REFRESH_LOG_PATH, {
        "refreshed_at": now_iso(),
        "scope": "call_for_papers",
        "processed": len(candidates),
        "changed_deadlines": len(changes),
        "failures": failures,
        "deadline_counts": dict(Counter(post.get("deadline") or "none" for post in refreshed_posts if post.get("category") == "call_for_papers")),
        "changes": changes,
    })


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    refresh_cfp_deadlines(delay_seconds=args.delay, limit=args.limit)


if __name__ == "__main__":
    cli()
