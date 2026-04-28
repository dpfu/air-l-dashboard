import json
import re
from pathlib import Path

from scripts.classify import classify_post


ALLOWED_PUBLIC_FIELDS = {
    "id",
    "source",
    "subject",
    "date",
    "archive_url",
    "category",
    "tags",
    "snippet",
    "deadline",
    "event_date",
    "indexed_at",
}
FORBIDDEN_PUBLIC_FIELDS = {"author", "author_name", "email", "body", "body_html", "content", "message"}
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def _public_rows():
    path = Path("data/public/posts.ndjson")
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_classification_snippet_does_not_copy_transient_body():
    body = "Deadline: May 25, 2026. Contact secret@example.org for the full announcement."
    post = classify_post("CFP: Digital Culture Workshop", body)
    assert "secret@example.org" not in post.snippet
    assert "full announcement" not in post.snippet
    assert "Metadata-only summary" in post.snippet


def test_public_rows_keep_minimal_schema_and_redact_emails():
    for row in _public_rows():
        assert set(row) == ALLOWED_PUBLIC_FIELDS
        assert not (set(row) & FORBIDDEN_PUBLIC_FIELDS)
        assert len(row.get("snippet") or "") <= 220
        assert not EMAIL_RE.search(json.dumps(row))


def test_thread_index_contains_only_ids_and_structure():
    path = Path("data/public/thread-index.json")
    if not path.exists():
        return

    index = json.loads(path.read_text(encoding="utf-8"))
    assert set(index) <= {"source", "indexed_at", "by_id", "threads"}
    assert not EMAIL_RE.search(json.dumps(index))

    for post_id, meta in index.get("by_id", {}).items():
        assert post_id.isdigit()
        assert set(meta) == {"thread_id", "parent_id", "depth", "position"}
        assert str(meta["thread_id"]).isdigit()
        assert meta["parent_id"] is None or str(meta["parent_id"]).isdigit()
        assert isinstance(meta["depth"], int)
        assert isinstance(meta["position"], int)

    for thread_id, post_ids in index.get("threads", {}).items():
        assert thread_id.isdigit()
        assert all(str(post_id).isdigit() for post_id in post_ids)
