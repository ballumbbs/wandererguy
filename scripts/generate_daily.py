"""Creates today's destination post.

Run once per day (GitHub Actions does this automatically).
- Picks the next destination that has not been published yet.
- If ANTHROPIC_API_KEY is set, Claude writes a richer, unique guide
  (and can cover destinations beyond the built-in list).
- Otherwise a guide is assembled from the curated destination data.
- When everything has been covered, the oldest guide is refreshed and
  re-featured as today's post.
"""
import hashlib
import json
import os
import re
import sys

from common import DATA, POSTS, STATE_FILE, load_config, load_json, save_json, today


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def pick(seq, seed):
    return seq[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(seq)]


# ---------------------------------------------------------------- template mode
INTROS = [
    "{name} is one of those places that stays with you long after the trip ends. {tagline} — and it is easier to plan than you might think.",
    "Looking for your next escape? {name} delivers: {tagline_l}. Here is everything you need to plan a trip.",
    "{tagline}. That is {name} in one line — but there is a lot more to it. This guide covers when to go, where to stay and what not to miss.",
    "If {name} has been on your list, consider this your sign. {tagline}, all within reach of a short holiday.",
]

COST_TEXT = {
    "₹": "budget-friendly — hostels, homestays and local food keep costs low",
    "₹₹": "mid-range — comfortable stays and good food without overspending",
    "₹₹₹": "on the premium side — worth saving up for, though budget options exist",
}


def template_post(dest, date):
    seed = f"{dest['slug']}{date}"
    intro = pick(INTROS, seed).format(name=dest["name"], tagline=dest["tagline"],
                                       tagline_l=dest["tagline"][0].lower() + dest["tagline"][1:])
    sections = [
        {"heading": f"Why visit {dest['name']}",
         "paragraphs": [f"{dest['name']} ({dest.get('region', dest['country'])}) is known for its "
                        f"{', '.join(dest['tags'][:-1])} and {dest['tags'][-1]} experiences. "
                        f"Overall it is {COST_TEXT.get(dest.get('cost', '₹₹'))}."]},
        {"heading": "Best time to go", "paragraphs": [f"The best time to visit is {dest['best_time']}."]},
        {"heading": "Top things to do", "list": dest["highlights"]},
        {"heading": "What to eat", "list": dest["food"]},
        {"heading": "How to get there", "paragraphs": [dest["getting_there"]]},
        {"heading": "Where to stay", "list": dest["stay_areas"]},
        {"heading": "Insider tip", "paragraphs": [dest["tip"]]},
    ]
    faq = [
        {"q": f"When is the best time to visit {dest['name']}?", "a": dest["best_time"][0].upper() + dest["best_time"][1:] + "."},
        {"q": f"How do I reach {dest['name']}?", "a": dest["getting_there"]},
        {"q": f"Where should I stay in {dest['name']}?", "a": "Popular choices: " + "; ".join(dest["stay_areas"]) + "."},
    ]
    return {"intro": intro, "sections": sections, "faq": faq, "source": "template"}


# ---------------------------------------------------------------- Claude mode
PROMPT = """You are the writer for {site}, an Indian travel blog. Write a practical, honest,
up-to-date-feeling travel guide for: {name}, {country}.
Audience: Indian travellers (mention costs only as relative levels, never exact prices;
do NOT state visa rules, entry fees or anything that changes often — tell readers to check official sources instead).

{known}

Return ONLY valid JSON with exactly these keys:
{{
 "tagline": "one short line",
 "region": "state/region",
 "tags": ["3-4 lowercase words from: beach, mountain, city, heritage, food, nature, adventure, spiritual, island, romantic, family, hills, desert, trek, culture, shopping, luxury, backpacking"],
 "cost": "₹ or ₹₹ or ₹₹₹",
 "best_time": "short phrase",
 "highlights": ["4-6 items"],
 "food": ["3-4 items"],
 "stay_areas": ["2-4 'Area for reason' items"],
 "getting_there": "1-2 sentences",
 "tip": "one insider tip",
 "intro": "2-3 engaging sentences",
 "sections": [{{"heading": "...", "paragraphs": ["..."]}}],   // 5-7 sections, 120-200 words each, include a suggested 3-day itinerary section
 "faq": [{{"q": "...", "a": "..."}}]   // 3-4 items
}}"""


def claude_post(dest, cfg):
    import anthropic  # imported lazily so template mode needs no extra package

    known = ""
    if dest.get("highlights"):
        known = "Facts you can rely on:\n" + json.dumps(
            {k: dest[k] for k in ("best_time", "highlights", "food", "stay_areas", "getting_there", "tip") if k in dest},
            ensure_ascii=False)
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=cfg.get("claude_model", "claude-sonnet-5-5"),
        max_tokens=6000,
        messages=[{"role": "user", "content": PROMPT.format(
            site=cfg["site_name"], name=dest["name"], country=dest["country"], known=known)}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    data["source"] = "claude"
    return data


# ---------------------------------------------------------------- main
def main():
    cfg = load_config()
    date = today().isoformat()
    state = load_json(STATE_FILE, {"published": []})
    published = {p["slug"]: p for p in state["published"]}

    if any(p.get("last_featured") == date for p in state["published"]):
        print(f"Already published for {date}; nothing to do.")
        return 0

    curated = load_json(DATA / "destinations.json", [])
    extra = load_json(DATA / "extra_destinations.json", [])
    use_ai = bool(os.environ.get("ANTHROPIC_API_KEY"))

    dest, refresh = None, False
    for d in curated:
        if d["slug"] not in published:
            dest = d
            break
    if dest is None and use_ai:
        for d in extra:
            if slugify(d["name"]) not in published:
                dest = {**d, "slug": slugify(d["name"])}
                break
    if dest is None:  # everything covered → refresh the oldest guide
        oldest = min(state["published"], key=lambda p: p["last_featured"])
        old = load_json(POSTS / f"{oldest['slug']}.json")
        dest, refresh = old, True

    print(f"{date}: {'refreshing' if refresh else 'writing'} {dest['name']} ({'Claude' if use_ai else 'template'})")

    body = None
    if use_ai:
        try:
            body = claude_post(dest, cfg)
        except Exception as e:  # never let the daily run fail because of the API
            print(f"Claude generation failed ({e}); falling back to template.", file=sys.stderr)
    if body is None:
        if not dest.get("highlights"):
            print("No data available for this destination without the API; skipping.", file=sys.stderr)
            return 0
        body = template_post(dest, date)

    base = {k: v for k, v in dest.items() if k not in ("intro", "sections", "faq", "source")}
    post = {**base, **{k: v for k, v in body.items() if v}}  # AI fields fill gaps / enrich
    for k in ("highlights", "food", "stay_areas", "best_time", "getting_there", "tip", "tagline"):
        if dest.get(k):
            post[k] = dest[k]  # curated facts always win
    post.setdefault("region", post.get("country", ""))
    post.setdefault("tags", ["travel"])
    post.setdefault("cost", "₹₹")
    post["slug"] = dest["slug"]
    post["title"] = f"{post['name']} Travel Guide: Best Time, Things to Do & Where to Stay"
    post["description"] = f"{post['tagline']}. Plan your {post['name']} trip: best time to visit, top sights, food, and hotel and flight deals."
    post["published"] = published.get(dest["slug"], {}).get("published", date)
    post["updated"] = date

    save_json(POSTS / f"{dest['slug']}.json", post)
    published[dest["slug"]] = {"slug": dest["slug"], "published": post["published"], "last_featured": date}
    state["published"] = sorted(published.values(), key=lambda p: p["last_featured"])
    save_json(STATE_FILE, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
