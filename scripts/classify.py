from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from scripts.utils import sanitize_text, unique_tags

try:
    import dateparser as _dateparser  # type: ignore
except Exception:  # pragma: no cover
    _dateparser = None


@dataclass
class ClassifiedPost:
    category: str
    tags: list[str]
    snippet: str
    deadline: str | None
    event_date: str | None


RULES: list[tuple[str, list[str], str]] = [
    ("call_for_papers", ["cfp", "call for papers", "special issue", "panel proposal"], "cfp"),
    ("job", ["job", "position", "hiring", "postdoc", "phd", "assistant professor", "fellowship"], "job"),
    ("event", ["conference", "symposium", "workshop", "webinar", "summer school"], "event"),
    ("publication", ["new book", "journal", "article", "open access", "special issue out"], "publication"),
    ("book_review", ["book review"], "book_review"),
    ("resource", ["dataset", "repository", "toolkit", "syllabus"], "resource"),
    ("announcement", ["announcement", "launch", "released"], "announcement"),
    ("question", ["?", "any recommendations", "does anyone"], "question"),
]

TAG_PATTERNS: list[tuple[str, str]] = [
    ("cfp", r"\bcfp\b|call for papers"), ("deadline", r"\bdeadline\b|due\s+date"), ("conference", r"\bconference\b"),
    ("workshop", r"\bworkshop\b"), ("special_issue", r"special issue"), ("journal", r"\bjournal\b"),
    ("phd", r"\bphd\b|doctoral"), ("postdoc", r"\bpostdoc\b|post-doctoral"), ("faculty", r"assistant professor|associate professor|faculty"),
    ("fellowship", r"\bfellowship\b"), ("book", r"\bbook\b"), ("open_access", r"open access"), ("book_review", r"book review"),
    ("dataset", r"\bdataset\b|data set"), ("teaching", r"\bteaching\b|syllabus"), ("method", r"method|methodology"),
    ("ai", r"\bai\b|artificial intelligence"), ("platforms", r"platform"), ("social_media", r"social media"),
    ("internet_governance", r"internet governance"), ("digital_culture", r"digital culture"),
]

DATE_HINT_RE = re.compile(
    r"(?:deadline|due|event date|on|by)\s*[:\-]?\s*([A-Za-z]{3,10}\.?\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    re.IGNORECASE,
)


def _parse_date(candidate: str):
    if _dateparser:
        dt = _dateparser.parse(candidate, settings={"PREFER_DATES_FROM": "future"})
        if dt:
            return dt.date().isoformat()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(candidate.replace(".", ""), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def detect_dates(text: str) -> tuple[str | None, str | None]:
    parsed = []
    for c in DATE_HINT_RE.findall(text):
        d = _parse_date(c.strip())
        if d:
            parsed.append(d)
    if not parsed:
        return None, None
    parsed = sorted(set(parsed))
    return parsed[0], parsed[1] if len(parsed) > 1 else None


def classify_post(subject: str, transient_body: str = "") -> ClassifiedPost:
    source = f"{subject}\n{transient_body}".lower()
    category = "other"
    tags: list[str] = []

    for candidate_category, keywords, marker_tag in RULES:
        if any(keyword in source for keyword in keywords):
            category = candidate_category
            tags.append(marker_tag)
            break

    for tag, pattern in TAG_PATTERNS:
        if re.search(pattern, source, flags=re.IGNORECASE):
            tags.append(tag)

    deadline, event_date = detect_dates(source)
    if deadline:
        tags.append("deadline")

    snippet = sanitize_text(subject if not transient_body else f"{subject} — {transient_body[:180]}", max_len=220)
    return ClassifiedPost(category=category, tags=unique_tags(tags), snippet=snippet, deadline=deadline, event_date=event_date)
