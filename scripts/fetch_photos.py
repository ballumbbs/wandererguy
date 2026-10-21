"""Finds a free-licensed photo for every guide that doesn't have one yet.

Source: Wikimedia Commons (via the English Wikipedia page named in each
destination's "wiki" field). Only freely licensed lead images are used (pilicense=free) — and the photographer + licence are saved so the site can credit them.
Results are cached in content/photos.json; edit that file to swap any photo.
Never fails the daily run: anything that goes wrong is skipped and retried tomorrow.
"""
import html
import time
import json
import re
import sys
import urllib.parse
import urllib.request

from common import POSTS, load_json, save_json

PHOTOS = POSTS.parent / "photos.json"  # content/photos.json, committed with the posts
UA = {"User-Agent": "WandererGuyBot/1.0 (https://wandererguy.in; site photo credits)"}
WIDTH, SMALL = 1280, 500  # standard Wikimedia thumbnail steps


def get_json(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # retry slowly on rate limits / network blips
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()[:120]


def page_image(title):
    """The lead image of a Wikipedia article, only if it is freely licensed."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "redirects": 1,
                                "prop": "pageimages", "piprop": "name", "pilicense": "free", "titles": title})
    pages = get_json("https://en.wikipedia.org/w/api.php?" + q).get("query", {}).get("pages", [])
    return pages[0].get("pageimage") if pages else None


def file_info(fname):
    q = urllib.parse.urlencode({"action": "query", "titles": "File:" + fname, "prop": "imageinfo",
                                "iiprop": "url|extmetadata", "iiurlwidth": WIDTH, "format": "json", "formatversion": 2})
    for host in ("commons.wikimedia.org", "en.wikipedia.org"):
        pages = get_json(f"https://{host}/w/api.php?" + q).get("query", {}).get("pages", [])
        if pages and pages[0].get("imageinfo"):
            return pages[0]["imageinfo"][0]
    return None


def find_photo(title):
    fname = page_image(title)
    if not fname or fname.lower().endswith((".svg", ".png", ".gif", ".tif", ".tiff")):
        return None  # no free lead photo (or only a map / flag / logo)
    info = file_info(fname)
    if not info:
        return None
    meta = info.get("extmetadata", {})
    big = info.get("thumburl") or info["url"]
    small = big.replace(f"/{WIDTH}px-", f"/{SMALL}px-") if f"/{WIDTH}px-" in big else big
    return {
        "url": big,
        "small": small,
        "credit": clean(meta.get("Artist", {}).get("value")) or "Wikimedia Commons contributor",
        "license": clean(meta.get("LicenseShortName", {}).get("value")) or "See source",
        "license_url": meta.get("LicenseUrl", {}).get("value", ""),
        "source": info.get("descriptionurl", ""),
        "wiki": title,
    }


def main():
    photos = load_json(PHOTOS, {})
    added = 0
    for f in sorted(POSTS.glob("*.json")):
        post = load_json(f)
        slug = post["slug"]
        if slug in photos:
            continue
        title = post.get("wiki") or post["name"]
        try:
            photo = find_photo(title)
        except Exception as e:
            print(f"  photo for {slug}: skipped ({e})", file=sys.stderr)
            continue
        if photo:
            photos[slug] = photo
            time.sleep(0.5)  # be polite to Wikimedia
            added += 1
            print(f"  photo for {slug}: {photo['credit']} ({photo['license']})")
        else:
            print(f"  photo for {slug}: no free photo on '{title}' — add one to content/photos.json", file=sys.stderr)
    save_json(PHOTOS, photos)
    print(f"Photos: {added} added, {len(photos)} total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
