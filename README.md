# AoIR Air-L Public Metadata Index (Static MVP)

Dieses Repo implementiert eine **datensparsame, vollständig statische** Index-Suche für das öffentliche AoIR/Air-L-Pipermail-Archiv.

## Datenschutz-/Scope-Prinzipien

- Kein Volltext-Mirror.
- Keine Persistierung von Autor:innen-Namen.
- Keine Persistierung von E-Mail-Adressen.
- Detailseiten werden nur temporär gelesen, um Kategorie/Tags/Deadline zu erkennen.
- Persistiert werden nur: `id`, `source`, `subject`, `date`, `archive_url`, `category`, `tags`, `snippet`, `deadline`, `event_date`, `indexed_at`.

## Implementierungsplan (MVP)

1. Monatliche Indexseite scrapen (aktueller Monat, optional Vormonat).
2. Detailseiten temporär laden und nur minimale Metadaten extrahieren.
3. Regelbasierte Klassifikation + Tagging + Datumserkennung.
4. Öffentliche JSON-Artefakte für Frontend bauen.
5. Statische Site (Suche, Filter, Sortierung) erstellen.
6. RSS-Feeds aus Minimalmetadaten generieren.
7. GitHub Actions für tägliches Update und Pages-Deployment.

## Repo-Struktur

```text
.github/
  workflows/
    update.yml
    deploy-pages.yml
scripts/
  scrape.py
  classify.py
  build_public_data.py
  build_feeds.py
  utils.py
data/
  public/
    posts.ndjson
    posts-latest.json
    search-index.json
    facets.json
    stats.json
  internal/
    seen-ids.json
    scrape-log.json
    classification-review.json
site/
  index.html
  app.js
  styles.css
  data/
  feeds/
  legal/
    impressum.html
    privacy.html
    opt-out.html
tests/
  test_classify.py
  test_parse.py
requirements.txt
README.md
LICENSE
```

## Lokales Ausführen

```bash
pip install -r requirements.txt
python -m scripts.scrape
python -m scripts.build_public_data
python -m scripts.build_feeds
pytest
```

## GitHub Actions

- `update.yml`: täglicher Lauf + `workflow_dispatch`, Scrape + Build + Commit.
- `deploy-pages.yml`: deployed den `site/`-Ordner auf GitHub Pages.

## Hinweise

- Vor Produktivbetrieb `BASE_URL` in `scripts/build_feeds.py` auf die echte GitHub-Pages-URL setzen.
- `site/legal/*` mit echter Betreiber-/Datenschutzinfo ergänzen.
