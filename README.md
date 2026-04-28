# Air-L Index

Static, data-minimizing metadata index for the public AoIR/Air-L Pipermail archive.

It links to original archive messages. It does not republish full message bodies.

## Scope

- No stored full-text bodies.
- No stored author names.
- No stored email addresses.
- Detail pages are read only transiently during scraping.
- Public data contains only minimal metadata: ID, subject, date, original link, category, tags, snippet, deadline/event date, and index timestamp.

## Run

```bash
uv sync
uv run python -m scripts.scrape
uv run python -m scripts.build_public_data
uv run python -m scripts.build_feeds
uv run pytest
```

## Release

Current version: `0.1.0`

See `CHANGELOG.md` and `RELEASE.md`.
