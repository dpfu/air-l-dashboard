from __future__ import annotations

import argparse
import html as html_lib
import re
import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from scripts.classify import classify_post
from scripts.utils import load_json, now_iso, read_ndjson, sanitize_text, write_json, write_ndjson

ARCHIVE_BASE = "http://listserv.aoir.org/pipermail/air-l-aoir.org/"
USER_AGENT = "aoir-airl-index-bot/0.1 (+https://github.com/dpfu/air-l-dashboard)"
PUBLIC_PATH = "data/public/posts.ndjson"
THREAD_INDEX_PATH = "data/public/thread-index.json"
SEEN_IDS_PATH = "data/internal/seen-ids.json"
SCRAPE_LOG_PATH = "data/internal/scrape-log.json"
ID_RE = re.compile(r"/(\d{5,})\.html$")
THREAD_COMMENT_RE = re.compile(r"^\s*(\d+)\s+")
THREAD_ID_RE = re.compile(r"\.(\d{5,})-")
MONTH_ARG_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_ROBOTS_CACHE: dict[str, RobotFileParser] = {}


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


class _ThreadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.threads_by_id: dict[str, dict[str, str | int | None]] = {}
        self._position = 0

    def handle_comment(self, data):
        depth_match = THREAD_COMMENT_RE.search(data)
        ids = THREAD_ID_RE.findall(data)
        if not depth_match or not ids:
            return

        current_id = ids[-1]
        self.threads_by_id[current_id] = {
            "thread_id": ids[0],
            "parent_id": ids[-2] if len(ids) > 1 else None,
            "depth": int(depth_match.group(1)),
            "position": self._position,
        }
        self._position += 1


def month_slug(dt: datetime) -> str:
    return dt.strftime("%Y-%B")


def month_slug_from_arg(value: str) -> str:
    if not MONTH_ARG_RE.match(value):
        raise argparse.ArgumentTypeError("month must use YYYY-MM, for example 2026-01")
    return month_slug(datetime.strptime(value, "%Y-%m").replace(tzinfo=UTC))


def _robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    parser = _ROBOTS_CACHE.get(origin)
    if parser is None:
        parser = RobotFileParser()
        parser.set_url(urljoin(origin, "/robots.txt"))
        try:
            parser.read()
        except Exception:
            return False
        _ROBOTS_CACHE[origin] = parser
    return parser.can_fetch(USER_AGENT, url)


def _fetch_text(url: str, timeout: int = 30) -> tuple[int, str]:
    if not _robots_allowed(url):
        return 999, ""
    try:
        import requests  # type: ignore

        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        return resp.status_code, resp.text
    except Exception:
        req = Request(url, headers={"User-Agent": USER_AGENT})
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


def parse_thread_page(html: str) -> dict[str, dict[str, str | int | None]]:
    parser = _ThreadParser()
    parser.feed(html)
    return parser.threads_by_id


def build_thread_index(by_id: dict[str, dict[str, str | int | None]], known_ids: set[str]) -> dict:
    filtered = {post_id: meta for post_id, meta in by_id.items() if post_id in known_ids}
    threads: dict[str, list[str]] = {}
    for post_id, meta in sorted(filtered.items(), key=lambda item: int(item[1].get("position") or 0)):
        thread_id = str(meta.get("thread_id") or post_id)
        threads.setdefault(thread_id, []).append(post_id)
    return {
        "source": "air-l",
        "indexed_at": now_iso(),
        "by_id": filtered,
        "threads": threads,
    }


def extract_transient_detail(html: str) -> tuple[str, str | None]:
    pre_match = re.search(r"<pre[^>]*>([\s\S]*?)</pre>", html, flags=re.IGNORECASE)
    body_text = html_lib.unescape(re.sub(r"<[^>]+>", " ", pre_match.group(1))).strip() if pre_match else ""

    i_match = re.search(r"<i[^>]*>([\s\S]*?)</i>", html, flags=re.IGNORECASE)
    parsed_date = None
    if i_match:
        raw = html_lib.unescape(re.sub(r"<[^>]+>", " ", i_match.group(1))).strip()
        try:
            parsed = parsedate_to_datetime(raw)
            parsed_date = parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError):
            for fmt in ("%a %b %d %H:%M:%S %Y", "%Y-%m-%d %H:%M:%S"):
                try:
                    parsed_date = datetime.strptime(raw, fmt).replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
                    break
                except ValueError:
                    continue
    return body_text, parsed_date


def run(
    only_current_month: bool = True,
    delay_seconds: float = 1.0,
    refresh_seen: bool = False,
    explicit_months: list[str] | None = None,
) -> None:
    now = datetime.now(UTC)
    months = explicit_months or [month_slug(now)]
    if not explicit_months and not only_current_month:
        months.append(month_slug(now.replace(day=1) - timedelta(days=1)))
    months = list(dict.fromkeys(months))

    seen_set = set(load_json(SEEN_IDS_PATH, default=[]))
    posts_by_id = {p["id"]: p for p in read_ndjson(PUBLIC_PATH)}
    thread_by_id = load_json(THREAD_INDEX_PATH, default={}).get("by_id", {})
    scrape_log = {"indexed_at": now_iso(), "months": [], "new_posts": 0}

    for slug in months:
        month_url = urljoin(ARCHIVE_BASE, f"{slug}/date.html")
        status, html = _fetch_text(month_url)
        if status != 200:
            scrape_log["months"].append({"month": slug, "status": status, "new": 0})
            continue

        month_entries = parse_month_page(html, month_url)
        thread_status, thread_html = _fetch_text(urljoin(ARCHIVE_BASE, f"{slug}/thread.html"))
        parsed_threads = parse_thread_page(thread_html) if thread_status == 200 else {}
        thread_by_id.update(parsed_threads)
        new_count = 0
        processed_count = 0
        for entry in month_entries:
            was_seen = entry["id"] in seen_set
            if was_seen and not refresh_seen:
                continue
            d_status, d_html = _fetch_text(entry["archive_url"])
            if d_status != 200:
                continue

            transient_body, parsed_date = extract_transient_detail(d_html)
            classified = classify_post(entry["subject"], transient_body, reference_date=parsed_date)
            indexed_at = now_iso()
            posts_by_id[entry["id"]] = {
                "id": entry["id"],
                "source": "air-l",
                "subject": entry["subject"],
                "date": parsed_date or indexed_at,
                "archive_url": entry["archive_url"],
                "category": classified.category,
                "tags": classified.tags,
                "snippet": sanitize_text(classified.snippet, 220),
                "deadline": classified.deadline,
                "event_date": classified.event_date,
                "indexed_at": indexed_at,
            }
            seen_set.add(entry["id"])
            if not was_seen:
                new_count += 1
            processed_count += 1
            time.sleep(delay_seconds)

        scrape_log["months"].append({
            "month": slug,
            "status": 200,
            "new": new_count,
            "processed": processed_count,
            "total_found": len(month_entries),
            "thread_status": thread_status,
            "thread_entries": len(parsed_threads),
        })
        scrape_log["new_posts"] += new_count

    write_ndjson(PUBLIC_PATH, sorted(posts_by_id.values(), key=lambda x: x["date"], reverse=True))
    write_json(THREAD_INDEX_PATH, build_thread_index(thread_by_id, set(posts_by_id)))
    write_json(SEEN_IDS_PATH, sorted(seen_set))
    write_json(SCRAPE_LOG_PATH, scrape_log)


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--month",
        action="append",
        type=month_slug_from_arg,
        help="Archive month to scrape as YYYY-MM. Can be repeated for cautious backfills.",
    )
    parser.add_argument("--include-previous-month", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--refresh-seen", action="store_true")
    args = parser.parse_args()
    run(
        only_current_month=not args.include_previous_month,
        delay_seconds=args.delay,
        refresh_seen=args.refresh_seen,
        explicit_months=args.month,
    )


if __name__ == "__main__":
    cli()
