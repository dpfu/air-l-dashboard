from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from scripts.utils import sanitize_text, unique_tags

try:
    import dateparser as _dateparser  # type: ignore
    from dateparser.search import search_dates as _search_dates  # type: ignore
except Exception:  # pragma: no cover
    _dateparser = None
    _search_dates = None


@dataclass
class ClassifiedPost:
    category: str
    tags: list[str]
    snippet: str
    deadline: str | None
    event_date: str | None


CATEGORY_ORDER = ("job", "call_for_papers", "publication", "event", "other")

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "job": [
        r"\bjob(s)?\b",
        r"\bhiring\b",
        r"\bvacanc(y|ies)\b",
        r"\bopen positions?\b",
        r"\bresearch positions?\b",
        r"\bpostdoctoral positions?\b",
        r"\bdoctoral positions?\b",
        r"\bfaculty positions?\b",
        r"\bacademic positions?\b",
        r"\bpositions?\s+(open|available|in|on|at|for)\b",
        r"\bposition\s+call\b",
        r"\bacademic positions?\b",
        r"\b(phd|doctoral)\s+(position|positions|studentship|studentships|fellowship|fellowships)\b",
        r"\bfunded phd\b",
        r"\bfully funded\b.*\bphd\b",
        r"\bphd\b.*\b(fully funded|apply|application|studentship|university|uni\b|deadline)\b",
        r"\bpost[-\s]?doc(toral)?\b",
        r"\bassistant professor\b",
        r"\bassociate professor\b",
        r"\btenure[-\s]?track professor\b",
        r"\bprofessorship\b",
        r"\bfaculty\s+(position|positions|job|jobs|search)\b",
        r"\bfellowship(s)?\b",
        r"\bvisiting fellow\b",
        r"\bresidenc(y|ies)\b",
        r"\blecturer\b",
        r"\bassistant managing editor\b",
    ],
    "call_for_papers": [
        r"\bcf[apsc]\b",
        r"\bcall[-\s]+for[-\s]+(papers?|abstracts?|chapters?|book chapters?|contributions?|proposals?|submissions?)\b",
        r"\bcall[-\s]+for[-\s]+(poster presentations?|posters?|research (track )?papers?|industry track papers?|journal first papers?|workshop papers?|workshop proposals?|fast abstracts?|project highlights?|project showcases?|replications?|negative results?)\b",
        r"\b(first|second|third|last|final|combo)\s+call\s+for\s+(research|industry|journal|workshop|fast|project|replications?|negative|papers?|abstracts?|proposals?|submissions?|posters?)\b",
        r"\b(first|second|third|last|final|combo)\s+call\s+for\b.{0,80}\b(papers?|abstracts?|proposals?|submissions?)\b",
        r"\b(final )?call for (posters|demos|work[-\s]?in[-\s]?progress|wip)\b",
        r"\bcall for extended abstracts\b",
        r"\binviting submissions\b",
        r"\bsubmissions? now open\b",
        r"\bsubmissions? (open|due|invited|welcome)\b",
        r"\bsubmission site\b",
        r"\bsubmit your abstracts?\b",
        r"\babstract submissions?\b",
        r"\babstracts? due\b",
        r"\bproposals? due\b",
        r"\bproposal deadline\b",
        r"\bsubmission deadline\b",
        r"\bextended deadline\b",
        r"\bdeadline extension\b",
        r"\bdeadline reminder:\s*abstract",
        r"\bdeadline for abstracts\b",
        r"\bcall for book proposal\b",
        r"\bcall for chapter proposals?\b",
        r"\bopen panel\b",
        r"\b4s call\b",
        r"\bpanel proposal\b",
        r"\bproposal for panel\b",
        r"\bspecial issue\b.*\b(call|cfp|submissions?|deadline|abstracts?|proposals?)\b",
        r"\b(call|cfp|submissions?|deadline|abstracts?|proposals?)\b.*\bspecial issue\b",
    ],
    "publication": [
        r"\bnew book\b",
        r"\bbook announcement\b",
        r"\bbook review\b",
        r"\bnew article\b",
        r"\bnew paper\b",
        r"\bnew journal\b",
        r"\bnew reports?\b",
        r"\bpolicy report\b",
        r"\bresearch report\b",
        r"\bannual report\b",
        r"\breport:\b",
        r"\bpaper summary\b",
        r"\bjournal article\b",
        r"\bopen access (book|article|paper|publication)\b",
        r"\bspecial issue\b",
        r"\bspecial issue (published|out|released)\b",
        r"\bnew special issue\b",
        r"\bpublished\b",
        r"\bpublication\b",
    ],
    "event": [
        r"\bconference\b",
        r"\bsymposium\b",
        r"\bworkshop\b",
        r"\bwebinar\b",
        r"\bsummer school\b",
        r"\bseminar\b",
        r"\bseminars?\b",
        r"\blecture\b",
        r"\bpublic lecture\b",
        r"\bpanel\b",
        r"\broundtable\b",
        r"\bforum\b",
        r"\bpre[-\s]?conference\b",
        r"\bevent invitation\b",
        r"\binvite:\b",
        r"\bschool on\b",
        r"\btalk series\b",
        r"\bspeaker series\b",
        r"\bbook launch\b",
        r"\breport launch\b",
        r"\blaunch event\b",
        r"^\s*(\[air-l\]\s*)?\d{1,2}\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
        r"\b\d{1,2}\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b.*\b(at|online|lecture|seminar|panel|forum|conference|workshop|webinar|school|symposium)\b",
        r"\b(at|online|lecture|seminar|panel|forum|conference|workshop|webinar|school|symposium)\b.*\b\d{1,2}\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
        r"\blive\b.*\bwhat('s|’s| is) on\b",
        r"\bprogramme announced\b",
        r"\bprogram(me)?\b.*\bannounced\b",
        r"\bearly registration\b",
        r"\binvitation\b.*\b(lecture|talk|webinar|workshop|conference)\b",
        r"\b\d{1,2}[-–]\d{1,2}\s+[A-Za-z]{3,10}\s+\d{4}\b",
    ],
}

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
DEADLINE_CONTEXT_RE = re.compile(
    r"\b("
    r"deadline|due|due date|submit by|submission deadline|proposal deadline|abstract deadline|paper deadline|"
    r"submissions? deadline|submissions? close|submissions? closes|submissions? due|"
    r"abstracts? due|abstracts? by|proposals? due|proposals? by|papers? due|papers? by|"
    r"full papers? due|extended deadline|deadline extended|deadline extension|closing date"
    r")\b",
    re.IGNORECASE,
)
STRONG_DEADLINE_CONTEXT_RE = re.compile(
    r"\b(submission deadline|proposal deadline|abstract deadline|paper deadline|deadline for abstracts?|"
    r"abstracts? due|papers? due|full papers? due|deadline extended|extended deadline|deadline extension|submissions? close|submit by)\b",
    re.IGNORECASE,
)
NON_DEADLINE_DATE_CONTEXT_RE = re.compile(
    r"\b(conference dates?|conference|event date|event dates?|workshop date|workshop dates?|"
    r"notification|acceptance|camera[-\s]?ready|publication date|published|program(me)?|"
    r"takes place|held|starts?|begins?|from|to)\b",
    re.IGNORECASE,
)
DATE_WITH_DAY_RE = re.compile(
    r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,10}|\b[A-Za-z]{3,10}\.?\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}[./-]\d{1,2})",
    re.IGNORECASE,
)
EVENT_RESOURCE_RE = re.compile(r"^\s*(\[air-l\]\s*)?(\[ext\]\s*)?(recording|recordings|video)\b", re.IGNORECASE)
REGISTRATION_CALL_RE = re.compile(r"\b(last|final)?\s*call for registration\b|\bregistration deadline\b|\bearly registration\b", re.IGNORECASE)
QUOTE_OR_FOOTER_RE = re.compile(
    r"(?im)^(>+|on .+ wrote:|-----original message-----|more information about the air-l|to see the collection of prior postings)",
)

CATEGORY_LABELS = {
    "call_for_papers": "CfP",
    "job": "JOBS",
    "event": "Events",
    "publication": "Publication",
    "other": "OTHER",
}


def _reference_datetime(reference_date: str | datetime | None) -> datetime:
    if isinstance(reference_date, datetime):
        return reference_date if reference_date.tzinfo else reference_date.replace(tzinfo=UTC)
    if isinstance(reference_date, str) and reference_date:
        try:
            return datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(UTC)


def _plausible_for_reference(value: str, reference_date: datetime) -> bool:
    year = datetime.fromisoformat(value).year
    return reference_date.year - 1 <= year <= reference_date.year + 3


def _analysis_body(transient_body: str) -> str:
    kept: list[str] = []
    for line in transient_body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if QUOTE_OR_FOOTER_RE.search(stripped):
            break
        kept.append(stripped)
        if len(" ".join(kept)) > 2500:
            break
    return "\n".join(kept)


def _parse_date(candidate: str, reference_date: datetime):
    if _dateparser:
        dt = _dateparser.parse(candidate, settings={"PREFER_DATES_FROM": "current_period", "RELATIVE_BASE": reference_date})
        if dt:
            parsed = dt.date().isoformat()
            return parsed if _plausible_for_reference(parsed, reference_date) else None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(candidate.replace(".", ""), fmt).date().isoformat()
            return parsed if _plausible_for_reference(parsed, reference_date) else None
        except ValueError:
            continue
    return None


def _searched_dates(text: str, reference_date: datetime) -> list[tuple[str, str, int]]:
    if not _search_dates:
        return []
    found = _search_dates(
        text,
        settings={
            "PREFER_DATES_FROM": "current_period",
            "RELATIVE_BASE": reference_date,
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    ) or []
    lowered = text.lower()
    cursor = 0
    dates: list[tuple[str, str, int]] = []
    for raw, dt in found:
        if not DATE_WITH_DAY_RE.search(raw):
            continue
        parsed = dt.date().isoformat()
        if not _plausible_for_reference(parsed, reference_date):
            continue
        pos = lowered.find(raw.lower(), cursor)
        if pos < 0:
            pos = lowered.find(raw.lower())
        if pos < 0:
            pos = 0
        cursor = pos + len(raw)
        dates.append((raw, parsed, pos))
    return dates


def _date_fallbacks(text: str, reference_date: datetime) -> list[tuple[str, str, int]]:
    dates = []
    for match in DATE_HINT_RE.finditer(text):
        raw = match.group(1).strip()
        parsed = _parse_date(raw, reference_date)
        if parsed:
            dates.append((raw, parsed, match.start(1)))
    return dates


def _line_deadline_score(line: str, date_pos: int, date_value: str, reference_date: datetime) -> float | None:
    context_matches = list(DEADLINE_CONTEXT_RE.finditer(line))
    if not context_matches:
        return None

    distance = min(abs(date_pos - match.start()) for match in context_matches)
    score = 80 - min(distance, 100) / 5
    if STRONG_DEADLINE_CONTEXT_RE.search(line):
        score += 40
    if re.search(r"\b(extended|extension|final|last|reminder)\b", line, flags=re.IGNORECASE):
        score += 12
    if NON_DEADLINE_DATE_CONTEXT_RE.search(line):
        score -= 35

    reference_day = reference_date.date()
    parsed_day = datetime.fromisoformat(date_value).date()
    if parsed_day < reference_day:
        score -= min((reference_day - parsed_day).days, 60) / 2
    if parsed_day > reference_day.replace(year=reference_day.year + 2):
        score -= 30
    return score


def detect_deadline(text: str, reference_date: str | datetime | None = None) -> str | None:
    reference = _reference_datetime(reference_date)
    candidates: list[tuple[float, str]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not DEADLINE_CONTEXT_RE.search(line):
            continue
        dates = _searched_dates(line, reference) or _date_fallbacks(line, reference)
        for _, parsed, pos in dates:
            score = _line_deadline_score(line, pos, parsed, reference)
            if score is not None:
                candidates.append((score, parsed))

    if not candidates:
        return None

    best_score = max(score for score, _ in candidates)
    best_dates = sorted(date for score, date in candidates if score >= best_score - 8)
    return best_dates[0] if best_dates else None


def detect_dates(text: str, reference_date: str | datetime | None = None) -> tuple[str | None, str | None]:
    return detect_deadline(text, reference_date=reference_date), None


def build_metadata_snippet(category: str, tags: list[str], deadline: str | None, event_date: str | None) -> str:
    """Generate a short snippet without copying transient message body text."""
    label = CATEGORY_LABELS.get(category, category.replace("_", " "))
    parts = [f"Metadata-only summary: {label}."]
    if tags:
        parts.append(f"Tags: {', '.join(tags[:6])}.")
    if deadline:
        parts.append(f"Deadline: {deadline}.")
    if event_date:
        parts.append(f"Event date: {event_date}.")
    return sanitize_text(" ".join(parts), max_len=220)


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def classify_category(subject_source: str, body_source: str) -> str:
    """Assign one of the coarse public labels from conservative text signals."""
    subject_hits = {
        category: _matches_any(CATEGORY_PATTERNS[category], subject_source)
        for category in CATEGORY_ORDER
        if category != "other"
    }

    if subject_hits["job"]:
        return "job"
    if subject_hits["call_for_papers"] and not REGISTRATION_CALL_RE.search(subject_source):
        return "call_for_papers"
    if subject_hits["publication"]:
        return "publication"
    if subject_hits["event"] and not EVENT_RESOURCE_RE.search(subject_source):
        return "event"

    weak_subject = not subject_source.strip() or "(no subject)" in subject_source
    if not weak_subject:
        return "other"

    body_hits = {
        category: _matches_any(CATEGORY_PATTERNS[category], body_source)
        for category in CATEGORY_ORDER
        if category != "other"
    }
    if body_hits["call_for_papers"] and not REGISTRATION_CALL_RE.search(body_source):
        return "call_for_papers"
    if body_hits["job"]:
        return "job"
    if body_hits["publication"]:
        return "publication"
    if body_hits["event"] and not EVENT_RESOURCE_RE.search(body_source):
        return "event"
    return "other"


def classify_post(subject: str, transient_body: str = "", reference_date: str | datetime | None = None) -> ClassifiedPost:
    subject_source = subject.lower()
    body_source = _analysis_body(transient_body).lower()
    source = f"{subject_source}\n{body_source}"
    category = classify_category(subject_source, body_source)
    tags: list[str] = []
    if category == "call_for_papers":
        tags.append("cfp")
    elif category != "other":
        tags.append(category)

    for tag, pattern in TAG_PATTERNS:
        if re.search(pattern, source, flags=re.IGNORECASE):
            tags.append(tag)

    deadline, event_date = detect_dates(source, reference_date=reference_date)
    if deadline:
        tags.append("deadline")

    tags = unique_tags(tags)
    snippet = build_metadata_snippet(category, tags, deadline, event_date)
    return ClassifiedPost(category=category, tags=tags, snippet=snippet, deadline=deadline, event_date=event_date)
