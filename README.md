# kidplan-fetcher

[![CI](https://github.com/XtibiX/kidplan-fetcher/actions/workflows/ci.yml/badge.svg)](https://github.com/XtibiX/kidplan-fetcher/actions/workflows/ci.yml)

Downloads all photos from [Kidplan](https://app.kidplan.com) kindergarten albums and organises them locally by year and month.

```
kidplan_images/
└── 2026/
    ├── March/
    │   ├── Vårtur i skogen/
    │   │   ├── Vårtur i skogen_001.jpeg
    │   │   ├── Vårtur i skogen_002.jpeg
    │   │   └── ...
    │   └── Karneval 2026/
    │       ├── Karneval 2026_001.jpeg
    │       └── ...
    └── February/
        └── Snølek uke 8/
            └── ...
```

## Installation

```bash
pip install .
```

Or run directly without installing:

```bash
pip install requests beautifulsoup4
python kidplan_fetcher/cli.py
```

## Usage

**With username/password:**
```bash
kidplan-fetcher -u your@email.com -o ./photos
```

**With a session cookie** (faster — grab `.ASPXAUTH` from browser DevTools → Application → Cookies):
```bash
kidplan-fetcher --cookie "<value>" -o ./photos
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-u`, `--username` | Kidplan email | — |
| `-c`, `--cookie` | `.ASPXAUTH` session cookie value | — |
| `-o`, `--output` | Output directory | `./kidplan_images` |
| `--delay` | Seconds between requests | `0.2` |
| `--since` | Only download albums modified on or after `YYYY-MM-DD` | — |
| `--album` | Only download albums whose title contains this string (case-insensitive) | — |

## How it works

1. Authenticates via username/password or a browser session cookie
2. Fetches the full album list from `/bilder/GetAlbumsAsJson`
3. For each album, scrapes the album page for original-resolution image URLs
4. Downloads images into `<output>/<year>/<month>/<album title>/` — skipping files already on disk
5. Names files `<album title>_001.jpg`, `<album title>_002.jpg`, …

## CI

GitHub Actions runs two test suites on every push:

| Suite | When | Requires |
|-------|------|----------|
| Unit tests (Python 3.10 / 3.11 / 3.12) | Every push & PR | Nothing |
| Integration tests (real Kidplan API) | Push to `main` only | Repo secrets |

To enable integration tests, add these two secrets to your fork:
`Settings → Secrets and variables → Actions`

| Secret | Value |
|--------|-------|
| `KIDPLAN_USERNAME` | Your Kidplan email |
| `KIDPLAN_PASSWORD` | Your Kidplan password |

## Notes

- Session cookies expire when you log out. Re-fetch from DevTools if downloads fail with 401/403.
- Already-downloaded files are skipped on re-runs, so interrupted downloads are resumable.
