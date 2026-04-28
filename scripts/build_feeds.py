from __future__ import annotations

import os
from datetime import datetime
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from scripts.utils import read_ndjson

SITE_FEEDS_DIR = "site/feeds"
BASE_URL = os.environ.get("SITE_BASE_URL", "https://dpfu.github.io/air-l-dashboard").rstrip("/")


def rss_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return format_datetime(dt, usegmt=True)


def rss_for(posts: list[dict], title: str, link_path: str = "/") -> bytes:
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = title
    SubElement(channel, "link").text = BASE_URL + link_path
    SubElement(channel, "description").text = "AoIR Air-L public metadata index (no full-text mirror)."

    for p in posts[:100]:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = p.get("subject", "Untitled")
        SubElement(item, "link").text = p.get("archive_url")
        SubElement(item, "guid").text = p.get("archive_url")
        SubElement(item, "pubDate").text = rss_date(p.get("date"))
        SubElement(item, "description").text = p.get("snippet", "")

    return tostring(rss, encoding="utf-8", xml_declaration=True)


def run() -> None:
    posts = read_ndjson("data/public/posts.ndjson")

    by_name = {
        "all.xml": posts,
        "call-for-papers.xml": [p for p in posts if p.get("category") == "call_for_papers"],
        "jobs.xml": [p for p in posts if p.get("category") == "job"],
        "publications.xml": [p for p in posts if p.get("category") == "publication"],
        "events.xml": [p for p in posts if p.get("category") == "event"],
    }

    os.makedirs(SITE_FEEDS_DIR, exist_ok=True)
    for name, subset in by_name.items():
        title = f"AoIR Air-L {name.replace('.xml', '').replace('-', ' ').title()}"
        with open(f"{SITE_FEEDS_DIR}/{name}", "wb") as f:
            f.write(rss_for(subset, title))


if __name__ == "__main__":
    run()
