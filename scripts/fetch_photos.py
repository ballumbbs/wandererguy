"""Finds a free-licensed photo for every guide that doesn't have one yet.

Source: Wikimedia Commons (via the English Wikipedia page named in each
destination's "wiki" field). Only Commons files are used — they carry free
licences — and the photographer + licence are saved so the site can credit them.
Results are cached in content/photos.json; edit that file to swap any photo.
Never fails the daily run: anything that goes wrong is skipped and retried tomorrow.
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request

from common import POSTS, load_json, save_json

PHOTOS = POSTS.parent / "photos.json"  # content/photos.json, committed with the posts
UA = {"User-Agent": "WandererGuyBot/1.0 (https://wandererguy.in; site photo credits)"}
WIDTH, SMALL = 1280, 500  # standard Wikimedia thumbnail steps


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()[:120]


def find_photo(title):
    summary = get_json("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_")))
    src = (summary.get("originalimage") or summary.get("thumbnail") or {}).get("source", "")
    if "/wikipedia/commons/" not in src or src.lower().endswith((".svg", ".png", ".gif")):
        return None  # skip non-free (local) files, maps, flags and logos
    fname = urllib.parse.unquote(src.split("/")[-1])
    if "/thumb/" in src:  # thumbnail URL: the real file name is the second-to-last segment
        fname = urllib.parse.unquote(src.split("/")[-2])
    q = urllib.parse.urlencode({"action": "query", "titles": "File:" + fname, "prop": "imageinfo",
                                "iiprop": "url|extmetadata", "iiurlwidth": WIDTH,
                                "format": "json", "formatversion": 2})
    data = get_json("https://commons.wikimedia.org/w/api.php?" + q)
    info = data["query"]["pages"][0]["imageinfo"][0]
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
            added += 1
            print(f"  photo for {slug}: {photo['credit']} ({photo['license']})")
        else:
            print(f"  photo for {slug}: no free photo on '{title}' — add one to content/photos.json", file=sys.stderr)
    save_json(PHOTOS, photos)
    print(f"Photos: {added} added, {len(photos)} total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
