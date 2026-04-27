from __future__ import annotations

import argparse
import re
import time
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from scripts.classify import classify_post
from scripts.utils import load_json, now_iso, read_ndjson, sanitize_text, write_json, write_ndjson

ARCHIVE_BASE = "http://listserv.aoir.org/pipermail/air-l-aoir.org/"
PUBLIC_PATH = "data/public/posts.ndjson"
SEEN_IDS_PATH = "data/internal/seen-ids.json"
SCRAPE_LOG_PATH = "data/internal/scrape-log.json"
ID_RE = re.compile(r"/(\d{5,})\.html$")


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = None
        self._txt = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._txt = []

    def handle_data(self, data):
        if self._href is not None:
            self._txt.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._txt).strip()))
            self._href = None


def month_slug(dt: datetime) -> str:
    return dt.strftime("%Y-%B")


def _fetch_text(url: str, timeout: int = 30) -> tuple[int, str]:
    try:
        import requests  # type: ignore

        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "aoir-airl-index-bot/0.1 (+github.com)"})
        return resp.status_code, resp.text
    except Exception:
        req = Request(url, headers={"User-Agent": "aoir-airl-index-bot/0.1 (+github.com)"})
        try:
            with urlopen(req, timeout=timeout) as res:
                return getattr(res, "status", 200), res.read().decode("utf-8", errors="ignore")
        except HTTPError as e:
            return e.code, ""
        except URLError:
            return 599, ""


def parse_month_page(html: str, month_url: str) -> list[dict[str, str]]:
    parser = _LinkParser()
    parser.feed(html)
    rows = []
    for href, text in parser.links:
        if not href or not href.endswith(".html") or href.startswith(("thread", "subject", "author", "date")):
            continue
        full_url = urljoin(month_url, href)
        m = ID_RE.search(full_url)
        if not m:
            continue
        rows.append({"id": m.group(1), "archive_url": full_url, "subject": sanitize_text(text, 180)})
    return list({r["id"]: r for r in rows}.values())


def extract_transient_detail(html: str) -> tuple[str, str | None]:
    pre_match = re.search(r"<pre[^>]*>([\s\S]*?)</pre>", html, flags=re.IGNORECASE)
    body_text = re.sub(r"<[^>]+>", " ", pre_match.group(1)).strip() if pre_match else ""

    i_match = re.search(r"<i[^>]*>([\s\S]*?)</i>", html, flags=re.IGNORECASE)
    parsed_date = None
    if i_match:
        raw = re.sub(r"<[^>]+>", " ", i_match.group(1)).strip()
        for fmt in ("%a %b %d %H:%M:%S %Z %Y", "%a %b %d %H:%M:%S %Y", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed_date = datetime.strptime(raw, fmt).replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
                break
            except ValueError:
                continue
    return body_text, parsed_date


def run(only_current_month: bool = True, delay_seconds: float = 1.0) -> None:
    now = datetime.now(UTC)
    months = [month_slug(now)]
    if not only_current_month:
        months.append(month_slug(now.replace(day=1) - timedelta(days=1)))

    seen_set = set(load_json(SEEN_IDS_PATH, default=[]))
    posts_by_id = {p["id"]: p for p in read_ndjson(PUBLIC_PATH)}
    scrape_log = {"indexed_at": now_iso(), "months": [], "new_posts": 0}

    for slug in months:
        month_url = urljoin(ARCHIVE_BASE, f"{slug}/date.html")
        status, html = _fetch_text(month_url)
        if status != 200:
            scrape_log["months"].append({"month": slug, "status": status, "new": 0})
            continue

        month_entries = parse_month_page(html, month_url)
        new_count = 0
        for entry in month_entries:
            if entry["id"] in seen_set:
                continue
            d_status, d_html = _fetch_text(entry["archive_url"])
            if d_status != 200:
                continue

            transient_body, parsed_date = extract_transient_detail(d_html)
            classified = classify_post(entry["subject"], transient_body)
            posts_by_id[entry["id"]] = {
                "id": entry["id"],
                "source": "air-l",
                "subject": entry["subject"],
                "date": parsed_date or now_iso(),
                "archive_url": entry["archive_url"],
                "category": classified.category,
                "tags": classified.tags,
                "snippet": sanitize_text(classified.snippet, 220),
                "deadline": classified.deadline,
                "event_date": classified.event_date,
                "indexed_at": now_iso(),
            }
            seen_set.add(entry["id"])
            new_count += 1
            time.sleep(delay_seconds)

        scrape_log["months"].append({"month": slug, "status": 200, "new": new_count, "total_found": len(month_entries)})
        scrape_log["new_posts"] += new_count

    write_ndjson(PUBLIC_PATH, sorted(posts_by_id.values(), key=lambda x: x["date"], reverse=True))
    write_json(SEEN_IDS_PATH, sorted(seen_set))
    write_json(SCRAPE_LOG_PATH, scrape_log)


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-previous-month", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    run(only_current_month=not args.include_previous_month, delay_seconds=args.delay)


if __name__ == "__main__":
    cli()
