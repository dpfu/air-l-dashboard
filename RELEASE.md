# Release Process

This project uses simple Git tags for releases. Version `0.1.0` is defined in `pyproject.toml`.

## Local Preflight

```bash
uv sync --frozen
uv run pytest -q
node --check site/app.js
if rg -n "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" data/public site/data site/feeds; then exit 1; fi
```

## Build Data Artifacts

For a normal update:

```bash
uv run python -m scripts.scrape
uv run python -m scripts.build_public_data
uv run python -m scripts.build_feeds
```

For a cautious CfP deadline refresh after heuristic changes:

```bash
uv run python -m scripts.refresh_deadlines --delay 0.5
uv run python -m scripts.build_public_data
uv run python -m scripts.build_feeds
```

## Tag 0.1.0

```bash
git status --short
git add .
git commit -m "release: 0.1.0"
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin HEAD
git push origin v0.1.0
```

## GitHub Release Notes

Use `CHANGELOG.md` section `0.1.0 - 2026-04-28` as the release body.

## Before Public Announcement

- Complete `site/legal/impressum.html`.
- Complete `site/legal/opt-out.html` with a working contact path.
- Confirm the GitHub Pages URL and `SITE_BASE_URL`.
- Run the manual `Update Air-L Index` workflow once.
- Verify the deployed site opens, searches, filters months, opens the CfP calendar, and links to original archive messages.
