# Changelog

## [1.0.0] - 2026-03-27

### Added
- Download all Kidplan album photos via the `GetAlbumsAsJson` API
- Organise downloads by `year/month/album title/` folder structure
- Sequential filenames: `Album Title_001.jpeg`, `Album Title_002.jpeg`, …
- Username/password and session cookie authentication
- Resume support — already-downloaded files are skipped
- Unit tests with mocked HTTP responses
- Integration tests against the real Kidplan API
- GitHub Actions CI (unit tests on 3.10/3.11/3.12, integration tests on push to main)
