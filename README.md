# Folk Directory

Hugo site for [folkdirectory.co.uk](https://folkdirectory.co.uk) — UK and Ireland folk clubs, sessions, dances, and festivals.

**Events** (`/listings/`) supports Type, County, and Status filters, optional text search, Show 10/25/50/100/All, and shareable URL query params. Data comes from `/listings/index.json`; the filter UI is driven by `static/js/listings-browse.js`.

## Local preview

```bash
git submodule update --init --recursive
hugo server
```

Contract tests for the listings browse index/filters:

```bash
hugo --minify
python3 -m pytest
```

Built and deployed with GitHub Pages (`.github/workflows/pages.yml`).

## Local ingest / scrape (maintainer only)

Scrapers, corpus/ledger, assessors, and prompts live under `ingest/`, `scripts/`,
`data/`, and `prompts/` — **gitignored** so GitHub Pages never ships caches,
JSONL, SQLite, or API keys. On a maintainer checkout that has those dirs:

- Ops runbook: [`ingest/README.md`](ingest/README.md)
- Env template: [`.env.example`](.env.example) (`SEARXNG_BASE_URL`, Venice, Maps)
- Never commit `.env`, `ingest/cache/`, `ingest/out/`, or `data/*.jsonl`

Public site content is only updated via `scripts/publish_corpus.py` writing
`content/listings/` (and map JSON under `static/data/`).

## Machine-readable listings API

`GET /listings/index.json` (built from `layouts/listings/list.json.json`):

| Field | Type | Notes |
|-------|------|--------|
| `version` | number | Currently `1` |
| `generated` | string | ISO-8601 UTC timestamp |
| `items` | array | One object per listing |

Each item:

| Field | Type | Notes |
|-------|------|--------|
| `id` | string/number | Listing id or filename |
| `title` | string | Display title |
| `permalink` | string | Site-relative path |
| `summary` | string | Truncated plain text |
| `event_types` | string[] | e.g. `folk-club`, `session`, `festival`, `dance` |
| `county` | string | |
| `status` | string | `listed` or `defunct` |
| `when` | string | Schedule / dates |
| `venue` | string | |
| `place` | string | Town / locality |
| `post_code` | string | |
| `www` | string | Website host or URL (may be empty) |
| `locations` | string[] | Taxonomy slugs |
| `logo` | string | Logo path, or empty for placeholder |

Map pins use `/data/listings-map.json` (coordinates + `event_type` + `status` + `www`). Popups and browse cards share `static/js/folk-utils.js` to turn a bare host into an `https://` link.

Propose new/updated listings via `/submit/`.
