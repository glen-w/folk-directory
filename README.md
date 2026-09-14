# Folk Directory

Hugo site for [folkdirectory.co.uk](https://folkdirectory.co.uk) — UK folk clubs, sessions, dances, and festivals.

**Events** (`/listings/`) supports Type and County filters, Show 10/25/50/100/All, and shareable URL query params. Data comes from `/listings/index.json`; the filter UI is driven by `static/js/listings-browse.js`.

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
