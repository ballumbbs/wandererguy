"""Renders the whole static site into ./public."""
import datetime as dt
import hashlib
import json
import random
import shutil
import sys
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape

from affiliates import Links
from common import DATA, POSTS, ROOT, STATE_FILE, load_config, load_json, today

OUT = ROOT / "public"
PHOTOS = POSTS.parent / "photos.json"

# fallback art when a guide has no photo yet
PALETTES = [("#13294b", "#2f6f8f"), ("#3b2a5a", "#c76b8f"), ("#0e4d64", "#4fb3a9"), ("#2c4a2e", "#9bbf6a"),
            ("#5a2a1f", "#e0a458"), ("#1d3557", "#7fb7d8"), ("#3d405b", "#e9c46a"), ("#284b63", "#d9a5b3")]

MOODS = [("beach", "Beaches", ["beach", "island"]), ("mountain", "Mountains", ["mountain", "hills", "snow", "trek"]),
         ("heritage", "Heritage & history", ["heritage", "art"]), ("spiritual", "Spiritual journeys", ["spiritual"]),
         ("nature", "Nature & wildlife", ["nature", "wildlife", "waterfalls"]), ("city", "City breaks", ["city"]),
         ("food", "Food trips", ["food"]), ("romantic", "Romantic getaways", ["romantic"]),
         ("adventure", "Adventure", ["adventure", "roadtrip", "diving"]), ("desert", "Deserts", ["desert"])]


def palette(slug):
    return PALETTES[int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(PALETTES)]


def gear_for(post, gear, n=4):
    tags = set(post.get("tags", []))
    specific = [g for g in gear if tags & set(g["tags"])]
    general = [g for g in gear if "all" in g["tags"]]
    random.Random(post["slug"]).shuffle(general)
    return (specific + general)[:n]


def main():
    cfg = load_config()
    d = today()
    links = Links(cfg, d)
    if links.missing():
        print("⚠ Missing affiliate IDs (links still work, but won't earn):", ", ".join(links.missing()))

    state = load_json(STATE_FILE, {"published": []})
    meta = {p["slug"]: p for p in state["published"]}
    photos = load_json(PHOTOS, {})
    gear = load_json(DATA / "gear.json", [])
    origin = cfg.get("home_airport", "DEL")

    posts = []
    for f in POSTS.glob("*.json"):
        p = load_json(f)
        m = meta.get(p["slug"], {})
        p["featured_on"] = m.get("last_featured", p.get("updated"))
        p["seq"] = m.get("seq", 0)
        p["url"] = f"/posts/{p['slug']}/"
        p["c1"], p["c2"] = palette(p["slug"])
        p["photo"] = photos.get(p["slug"])
        p["abroad"] = p.get("country") != "India"
        p["route"] = f"{origin} → {p['iata']}" if p.get("iata") and p.get("iata") != origin else None
        posts.append(p)
    if not posts:
        print("No posts yet — run scripts/generate_daily.py first.")
        return 1
    posts.sort(key=lambda p: (p["featured_on"], p["seq"]), reverse=True)

    weekend, wk_nights = links.next_weekend()
    later, later_nights = links.in_weeks(3, 3)
    for p in posts:
        p["deals"] = {
            "weekend": {"label": f"{weekend:%a %d %b} to {(weekend + dt.timedelta(days=wk_nights)):%a %d %b}",
                        "booking": links.booking(p["name"], p["country"], weekend, wk_nights),
                        "agoda": links.agoda(p["name"], weekend, wk_nights)},
            "later": {"label": f"{later:%d %b} to {(later + dt.timedelta(days=later_nights)):%d %b}",
                      "booking": links.booking(p["name"], p["country"], later, later_nights),
                      "agoda": links.agoda(p["name"], later, later_nights)},
            "flights": links.flights(p.get("iata"), later),
            "fly_date": f"{later:%d %b}",
        }
        p["gear"] = [{**g, "url": links.amazon(g["keyword"])} for g in gear_for(p, gear)]

    rnd = random.Random(d.isoformat())  # same picks all day, new picks tomorrow
    today_post = posts[0]
    rest = posts[1:]
    india = [p for p in rest if not p["abroad"]]
    abroad = [p for p in rest if p["abroad"]]
    rnd.shuffle(india)
    rnd.shuffle(abroad)
    deals = rnd.sample(posts, min(12, len(posts)))

    moods = []
    for key, label, tags in MOODS:
        items = [p for p in posts if set(p.get("tags", [])) & set(tags)]
        if items:
            cover = next((p for p in items if p["photo"]), items[0])
            moods.append({"key": key, "label": label, "tags": tags, "count": len(items), "cover": cover})

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    env.globals.update(site=cfg, today=d, year=d.year, origin=origin, moods=moods, total=len(posts))

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")

    def render(tpl, path, **ctx):
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(tpl).render(**ctx), encoding="utf-8")

    render("index.html", "index.html", today_post=today_post, india=india[:10], abroad=abroad[:10],
           deals=deals[:4], latest=posts[1:9], page_url="/")
    for p in posts:
        related = [q for q in posts if q is not p and set(q.get("tags", [])) & set(p.get("tags", []))]
        random.Random(p["slug"] + d.isoformat()).shuffle(related)
        render("post.html", f"posts/{p['slug']}/index.html", post=p, related=related[:4], page_url=p["url"])
    by_name = sorted(posts, key=lambda p: p["name"])
    render("destinations.html", "destinations/index.html", posts=by_name, page_url="/destinations/")
    render("search.html", "search/index.html", page_url="/search/")
    render("deals.html", "deals/index.html", deals=deals, weekend=weekend, page_url="/deals/")
    render("page_about.html", "about/index.html", page_url="/about/")
    render("page_disclosure.html", "disclosure/index.html", page_url="/disclosure/")
    render("page_privacy.html", "privacy/index.html", page_url="/privacy/")
    render("404.html", "404.html", page_url="/404.html")

    # search index used by the search box on every page
    index = [{"n": p["name"], "c": p["country"], "r": p.get("region", ""), "t": p.get("tags", []),
              "g": p.get("tagline", ""), "u": p["url"], "i": (p["photo"] or {}).get("small", ""),
              "a": p["abroad"], "c1": p["c1"], "c2": p["c2"]} for p in by_name]
    (OUT / "search-index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    # SEO + feeds
    base = cfg["base_url"].rstrip("/")
    urls = [(u, d.isoformat()) for u in ("/", "/destinations/", "/deals/", "/about/", "/disclosure/")]
    urls += [(p["url"], p["updated"]) for p in posts]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{base}{u}</loc><lastmod>{m}</lastmod></url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    items = "".join(
        f"<item><title>{escape(p['title'])}</title><link>{base}{p['url']}</link><guid>{base}{p['url']}</guid>"
        f"<pubDate>{dt.datetime.fromisoformat(p['featured_on']):%a, %d %b %Y} 06:00:00 +0530</pubDate>"
        f"<description>{escape(p['description'])}</description></item>"
        for p in posts[:20])
    (OUT / "feed.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{escape(cfg["site_name"])}</title>'
        f"<link>{base}/</link><description>{escape(cfg['tagline'])}</description>{items}</channel></rss>",
        encoding="utf-8")
    (OUT / "CNAME").write_text(cfg["domain"] + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Built {len(posts)} guides ({sum(1 for p in posts if p['photo'])} with photos) for {d}. Today: {today_post['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
