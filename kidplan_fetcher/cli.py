#!/usr/bin/env python3
"""
Kidplan image downloader.
Uses GetAlbumsAsJson to list all albums, then scrapes each album page
for full-size image URLs (size=f1440x1440) and downloads them immediately.
"""

import re
import sys
import time
import getpass
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

BASE_URL = "https://app.kidplan.com"


def login(session: requests.Session, username: str, password: str) -> bool:
    resp = session.get(
        f"{BASE_URL}/Account/GetKinderGartenIds",
        params={"username": username, "password": password},
    )
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        print("ERROR: Unexpected response from server.")
        return False
    if not data:
        print("ERROR: No kindergartens found.")
        return False
    if isinstance(data, list) and len(data) > 1:
        print("Multiple kindergartens found:")
        for i, kg in enumerate(data):
            print(f"  [{i}] {kg.get('Name', kg)}")
        idx = int(input("Select kindergarten index: "))
        kid_id = data[idx]["Id"]
    elif isinstance(data, list):
        kid_id = data[0]["Id"] if isinstance(data[0], dict) else data[0]
    else:
        kid_id = data
    resp = session.post(
        f"{BASE_URL}/LogOn",
        params={"kid": kid_id},
        data={"UserName": username, "Password": password, "RememberMe": "false"},
        allow_redirects=True,
    )
    resp.raise_for_status()
    if "/LogOn" in resp.url or "/Account/Login" in resp.url:
        print("ERROR: Login failed.")
        return False
    print("Login successful.")
    return True


def get_all_albums(session: requests.Session) -> list[dict]:
    """Paginate through GetAlbumsAsJson until all albums are fetched."""
    albums = []
    skip = 0
    take = 1000
    while True:
        print(f"  Fetching albums {skip}–{skip+take}...", flush=True)
        resp = session.get(
            f"{BASE_URL}/bilder/GetAlbumsAsJson",
            params={"take": take, "skip": skip, "noCache": int(time.time() * 1000)},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        albums.extend(batch)
        print(f"  Got {len(batch)}, total so far: {len(albums)}", flush=True)
        if len(batch) < take:
            break
        skip += take
    return albums


def get_fullsize_urls(session: requests.Session, album_id: str) -> list[tuple[str, str]]:
    """
    Scrape the album page and return list of (pic_guid, full_size_url).
    Full-size URLs use size=f1440x1440 and are in the <a href> of each thumbnail.
    """
    resp = session.get(f"{BASE_URL}/bilder/albumet/{album_id}")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for a in soup.find_all("a", class_="album-thumbnail"):
        href = a.get("href", "")
        guid = a.get("data-pic-guid", "")
        if href and "img.kidplan.com" in href:
            href = re.sub(r"&size=[^&]*", "", href)
            results.append((guid, href))

    return results


def download_image(session: requests.Session, url: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  SKIP: {dest.name}")
        return True
    try:
        resp = session.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        print(f"  OK: {dest.name}")
        return True
    except Exception as e:
        print(f"  FAIL {url}: {e}")
        return False


def slugify(text: str) -> str:
    return re.sub(r"[^\w\- ]", "", text).strip()[:80]


def main():
    parser = argparse.ArgumentParser(description="Download all Kidplan album images")
    parser.add_argument("-u", "--username", help="Kidplan username/email")
    parser.add_argument("-c", "--cookie", help="Value of the .ASPXAUTH cookie")
    parser.add_argument("-o", "--output", default="./kidplan_images", help="Output directory (default: ./kidplan_images)")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between requests in seconds (default: 0.2)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"

    if args.cookie:
        session.cookies.set(".ASPXAUTH", args.cookie, domain="app.kidplan.com")
        print("Using provided session cookie.")
    else:
        username = args.username or input("Username/email: ")
        password = getpass.getpass("Password: ")
        if not login(session, username, password):
            sys.exit(1)

    print("\nFetching album list...")
    albums = get_all_albums(session)
    print(f"Found {len(albums)} album(s).\n")

    total_downloaded = 0
    total_failed = 0

    for album in albums:
        album_id = album["AlbumId"]
        title = slugify(album.get("Title") or album_id)
        pic_count = album.get("PictureCount", "?")

        # Parse /Date(ms)/ timestamp to get year/month folder
        ms_match = re.search(r"\d+", album.get("Modified", ""))
        if ms_match:
            dt = datetime.fromtimestamp(int(ms_match.group()) / 1000, tz=timezone.utc)
            year = str(dt.year)
            month = dt.strftime("%B")  # e.g. "March"
        else:
            year, month = "Unknown", "Unknown"

        album_dir = output_dir / year / month / title

        print(f"[{title}] ({pic_count} pictures)", flush=True)

        pictures = get_fullsize_urls(session, album_id)
        time.sleep(args.delay)

        if not pictures:
            print(f"  No pictures found on page, skipping.")
            continue

        for i, (guid, url) in enumerate(pictures, start=1):
            match = re.search(r"id=[^.]+\.(\w+)", url)
            ext = "." + match.group(1) if match else ".jpg"
            filename = f"{title}_{i:03d}{ext}"
            dest = album_dir / filename
            if download_image(session, url, dest):
                total_downloaded += 1
            else:
                total_failed += 1
            time.sleep(args.delay)

    print(f"\nDone. {total_downloaded} downloaded, {total_failed} failed → {output_dir}/")


if __name__ == "__main__":
    main()
