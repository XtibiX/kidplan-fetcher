"""
Integration tests — require KIDPLAN_USERNAME and KIDPLAN_PASSWORD environment variables.

These tests hit the real Kidplan API to verify that:
  - Authentication still works
  - The album listing endpoint still returns data
  - Album pages still contain parseable image links
  - Image URLs are reachable and serve valid image content

Run locally:
    KIDPLAN_USERNAME=your@email.com KIDPLAN_PASSWORD=secret pytest tests/test_integration.py -v
"""

import os
import tempfile

import puremagic

import pytest
import requests

from kidplan_fetcher.cli import get_all_albums, get_fullsize_urls, login

USERNAME = os.getenv("KIDPLAN_USERNAME")
PASSWORD = os.getenv("KIDPLAN_PASSWORD")

pytestmark = pytest.mark.skipif(
    not USERNAME or not PASSWORD,
    reason="KIDPLAN_USERNAME and KIDPLAN_PASSWORD environment variables not set",
)


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (kidplan-fetcher-test)"
    assert login(s, USERNAME, PASSWORD), "Login failed — check credentials"
    return s


@pytest.fixture(scope="module")
def albums(session):
    return get_all_albums(session)


def test_album_list_not_empty(albums):
    assert len(albums) > 0, "Expected at least one album"


def test_album_list_has_required_fields(albums):
    required = {"AlbumId", "Title", "PictureCount", "Modified"}
    for album in albums[:5]:
        assert required.issubset(album.keys()), f"Missing fields in album: {album}"


def test_album_list_modified_timestamp(albums):
    import re
    for album in albums[:5]:
        assert re.search(r"\d+", album.get("Modified", "")), (
            f"Unexpected Modified format: {album.get('Modified')}"
        )


def test_first_album_with_pictures_has_image_urls(session, albums):
    target = next((a for a in albums if a.get("PictureCount", 0) > 0), None)
    assert target is not None, "No album with pictures found"

    pictures = get_fullsize_urls(session, target["AlbumId"])
    assert len(pictures) > 0, f"No images found for album: {target['Title']}"


def test_image_urls_have_no_size_param(session, albums):
    target = next((a for a in albums if a.get("PictureCount", 0) > 0), None)
    pictures = get_fullsize_urls(session, target["AlbumId"])
    for _guid, url in pictures:
        assert "size=" not in url, f"size param still present in URL: {url}"


def test_first_image_is_downloadable_jpeg(session, albums):
    target = next((a for a in albums if a.get("PictureCount", 0) > 0), None)
    pictures = get_fullsize_urls(session, target["AlbumId"])
    assert pictures

    _guid, url = pictures[0]
    resp = session.get(url, stream=True, timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
        tmp_path = f.name

    matches = puremagic.magic_file(tmp_path)
    mime_types = [m.mime_type for m in matches]
    assert any(m.startswith("image/") for m in mime_types), (
        f"Downloaded file is not a recognised image. Detected: {mime_types}"
    )
