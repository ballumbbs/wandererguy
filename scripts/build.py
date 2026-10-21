"""Renders the whole static site into ./public."""
import datetime as dt
import hashlib
import random
import shutil
import sys
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape

from affiliates import Links
from common import DATA, POSTS, ROOT, STATE_FILE, load_config, load_json, today

OUT = ROOT / "public"

PALETTES = [("#0f5257", "#e9a03b"), ("#7a2e2e", "#f2c57c"), ("#1f3b73", "#7fc8f8"),
            ("#2f5d3a", "#d8e2a4"), ("#5b2a86", "#f0a6ca"), ("#8a4b08", "#ffd29d"),
            ("#114b5f", "#88d498"), ("#3d405b", "#f2cc8f")]
TAG_ICON = {"beach": "🏖️", "island": "🏝️", "mountain": "🏔️", "snow": "❄️", "city": "🏙️", "heritage": "🏰",
            "food": "🍜", "nature": "🌿", "adventure": "🧗", "spiritual": "🛕", "romantic": "💞", "desert": "🐪",
            "lakes": "🛶", "backwaters": "🛶", "tea": "🍵", "coffee": "☕", "hills": "⛰️", "trek": "🥾",
            "diving": "🤿", "luxury": "✨", "culture": "🎎", "shopping": "🛍️", "family": "👨‍👩‍👧", "river": "🌊",
            "waterfalls": "💧", "roadtrip": "🛣️", "nightlife": "🌙", "backpacking": "🎒", "boulders": "🪨"}


def palette(slug):
    return PALETTES[int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(PALETTES)]


def icon(post):
    for t in post.get("tags", []):
        if t in TAG_ICON:
            return TAG_ICON[t]
    return "🧭"


def gear_for(post, gear, n=4):
    tags = set(post.get("tags", []))
    specific = [g for g in gear if tags & set(g["tags"])]
    general = [g for g in gear if "all" in g["tags"]]
    rnd = random.Random(post["slug"])
    rnd.shuffle(general)
    return (specific + general)[:n]


def main():
    cfg = load_config()
    d = today()
    links = Links(cfg, d)
    if links.missing():
        print("⚠ Missing affiliate IDs (links still work, but won't earn):", ", ".join(links.missing()))

    state = load_json(STATE_FILE, {"published": []})
    featured_on = {p["slug"]: p["last_featured"] for p in state["published"]}
    posts = []
    for f in POSTS.glob("*.json"):
        p = load_json(f)
        p["featured_on"] = featured_on.get(p["slug"], p.get("updated"))
        p["url"] = f"/posts/{p['slug']}/"
        p["c1"], p["c2"] = palette(p["slug"])
        p["icon"] = icon(p)
        posts.append(p)
    posts.sort(key=lambda p: p["featured_on"], reverse=True)
    if not posts:
        print("No posts yet — run scripts/generate_daily.py first.")
        return 1

    gear = load_json(DATA / "gear.json", [])
    weekend, wk_nights = links.next_weekend()
    later, later_nights = links.in_weeks(3, 3)

    def deals_for(p):
        return {
            "weekend": {"label": f"{weekend:%a %d %b} – {(weekend + dt.timedelta(days=wk_nights)):%a %d %b}",
                        "booking": links.booking(p["name"], p["country"], weekend, wk_nights),
                        "agoda": links.agoda(p["name"], weekend, wk_nights)},
            "later": {"label": f"{later:%d %b} – {(later + dt.timedelta(days=later_nights)):%d %b}",
                      "booking": links.booking(p["name"], p["country"], later, later_nights),
                      "agoda": links.agoda(p["name"], later, later_nights)},
            "flights": links.flights(p.get("iata"), later),
            "flight_label": f"{cfg['home_airport']} → {p.get('iata')} on {later:%d %b}",
        }

    for p in posts:
        p["deals"] = deals_for(p)
        p["gear"] = [{**g, "url": links.amazon(g["keyword"])} for g in gear_for(p, gear)]

    # Daily rotation: same picks all day, new picks tomorrow
    rnd = random.Random(d.isoformat())
    pool = posts[1:] or posts
    featured = rnd.sample(pool, min(6, len(pool)))
    deals = rnd.sample(posts, min(12, len(posts)))

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    env.globals.update(site=cfg, today=d, year=d.year, amazon=links.amazon)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")

    def render(tpl, path, **ctx):
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(tpl).render(**ctx), encoding="utf-8")

    render("index.html", "index.html", today_post=posts[0], featured=featured, deals=deals[:3],
           recent=posts[1:9], page_url="/")
    for i, p in enumerate(posts):
        related = [q for q in posts if q is not p and set(q.get("tags", [])) & set(p.get("tags", []))][:3]
        render("post.html", f"posts/{p['slug']}/index.html", post=p, related=related, page_url=p["url"])
    all_tags = sorted({t for p in posts for t in p.get("tags", [])})
    render("destinations.html", "destinations/index.html", posts=sorted(posts, key=lambda p: p["name"]),
           tags=all_tags, page_url="/destinations/")
    render("deals.html", "deals/index.html", deals=deals, weekend=weekend, page_url="/deals/")
    render("page_about.html", "about/index.html", count=len(posts), page_url="/about/")
    render("page_disclosure.html", "disclosure/index.html", page_url="/disclosure/")
    render("page_privacy.html", "privacy/index.html", page_url="/privacy/")
    render("404.html", "404.html", page_url="/404.html")

    # SEO + feeds
    base = cfg["base_url"].rstrip("/")
    urls = [("/", d.isoformat()), ("/destinations/", d.isoformat()), ("/deals/", d.isoformat()),
            ("/about/", d.isoformat()), ("/disclosure/", d.isoformat())]
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

    print(f"Built {len(posts)} guides into {OUT} for {d}. Today's post: {posts[0]['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
