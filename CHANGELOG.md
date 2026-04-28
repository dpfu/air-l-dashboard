# Changelog

## 0.1.0 - 2026-04-28

First static MVP release of the AoIR Air-L metadata index.

### Added

- Static, data-minimizing Air-L metadata index for GitHub Pages.
- Pipermail scraper for month pages, detail pages, and thread pages.
- Public metadata schema with no stored message bodies, author names, or email addresses.
- Rule-based labels for CfP, Publication, Events, JOBS, and OTHER.
- CfP deadline extraction from subject plus transient detail text.
- Thread grouping with messages hidden by default and expandable in the frontend.
- Dense Hacker News-style frontend with search-as-you-type, month filtering, thread toggle, category dashboard, and deadline sorting.
- Toggleable CfP deadline calendar; selecting a day filters only CfPs due on that date.
- Static JSON data artifacts and RSS feeds.
- GitHub Actions workflows for updates, Pages deployment, and CI checks.
- `uv`-based local and CI workflow.

### Data Snapshot

- 588 indexed public metadata records.
- 178 CfPs.
- 82 CfPs with detected deadlines.
- 131 records with any detected deadline.
- 0 email addresses detected in public data/feed artifacts by the release privacy scan.

### Known Limits

- Deadline extraction is heuristic and intentionally conservative.
- Legal pages are placeholders and must be completed before a public production launch.
- The project is an index linking back to the original archive, not a full-text mirror.
