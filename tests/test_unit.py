"""Unit tests — no network, no credentials required."""

import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from kidplan_fetcher.cli import get_fullsize_urls, slugify


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert slugify("Vårtur i skogen") == "Vårtur i skogen"

def test_slugify_strips_special_chars():
    assert "/" not in slugify("Album: test/2026")
    assert "!" not in slugify("Hello!")

def test_slugify_truncates_to_80():
    long = "A" * 100
    assert len(slugify(long)) <= 80

def test_slugify_empty():
    assert slugify("") == ""


# ---------------------------------------------------------------------------
# /Date(ms)/ timestamp parsing  (inline, same logic as cli.py)
# ---------------------------------------------------------------------------

def parse_modified(value: str):
    ms_match = re.search(r"\d+", value)
    if not ms_match:
        return None
    return datetime.fromtimestamp(int(ms_match.group()) / 1000, tz=timezone.utc)


def test_date_parsing_year():
    # 1774540708303 ms → 2026
    dt = parse_modified("/Date(1774540708303)/")
    assert dt.year == 2026

def test_date_parsing_month():
    dt = parse_modified("/Date(1774540708303)/")
    assert dt.strftime("%B") == "March"

def test_date_parsing_invalid():
    assert parse_modified("") is None
    assert parse_modified("/Date()/") is None


# ---------------------------------------------------------------------------
# size parameter stripping
# ---------------------------------------------------------------------------

def test_size_param_stripped():
    url = "https://img.kidplan.com/albumpicture/?id=abc.jpeg&token=XYZ&size=f1440x1440"
    stripped = re.sub(r"&size=[^&]*", "", url)
    assert "size" not in stripped
    assert "token=XYZ" in stripped

def test_no_size_param_unchanged():
    url = "https://img.kidplan.com/albumpicture/?id=abc.jpeg&token=XYZ"
    stripped = re.sub(r"&size=[^&]*", "", url)
    assert stripped == url


# ---------------------------------------------------------------------------
# get_fullsize_urls — mocked HTTP response
# ---------------------------------------------------------------------------

ALBUM_HTML = """
<html><body>
  <a class="album-thumbnail"
     href="https://img.kidplan.com/albumpicture/?id=pic1.jpeg&token=TOK&size=f1440x1440"
     data-pic-guid="pic1">
    <img data-src="...x350x350" />
  </a>
  <a class="album-thumbnail"
     href="https://img.kidplan.com/albumpicture/?id=pic2.jpg&token=TOK&size=f1440x1440"
     data-pic-guid="pic2">
    <img data-src="...x350x350" />
  </a>
  <a href="/some/other/link">not an image</a>
</body></html>
"""


def _mock_session(html: str) -> requests.Session:
    session = MagicMock(spec=requests.Session)
    resp = MagicMock()
    resp.text = html
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp
    return session


def test_get_fullsize_urls_count():
    session = _mock_session(ALBUM_HTML)
    results = get_fullsize_urls(session, "fake-album-id")
    assert len(results) == 2

def test_get_fullsize_urls_no_size_param():
    session = _mock_session(ALBUM_HTML)
    results = get_fullsize_urls(session, "fake-album-id")
    for _guid, url in results:
        assert "size" not in url

def test_get_fullsize_urls_guids():
    session = _mock_session(ALBUM_HTML)
    results = get_fullsize_urls(session, "fake-album-id")
    guids = [g for g, _ in results]
    assert "pic1" in guids
    assert "pic2" in guids

def test_get_fullsize_urls_ignores_non_kidplan_links():
    session = _mock_session(ALBUM_HTML)
    results = get_fullsize_urls(session, "fake-album-id")
    for _guid, url in results:
        assert "img.kidplan.com" in url

def test_get_fullsize_urls_empty_album():
    session = _mock_session("<html><body></body></html>")
    results = get_fullsize_urls(session, "fake-album-id")
    assert results == []
