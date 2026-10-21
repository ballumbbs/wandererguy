"""Illustrated travel posters (SVG), one per destination.

Used whenever a guide has no real photo yet. Each poster is drawn from the
destination's character (its tags), with hand-picked landmarks for some places.
Everything is deterministic: the same destination always gets the same poster.
"""
import hashlib
import math
import random
from xml.sax.saxutils import quoteattr

W, H = 800, 600

SKIES = {  # top, middle, bottom of the sky; sun colour
    "dawn":   ("#f6c6a8", "#f3a7a0", "#fde3c2", "#fff4d6"),
    "day":    ("#5fa8d3", "#9fd3ea", "#e6f4f1", "#fff8dc"),
    "sunset": ("#3d2c5c", "#d8576b", "#f6ae5b", "#ffe08a"),
    "dusk":   ("#1f2b4d", "#5a4a7a", "#d98c6a", "#ffd18a"),
    "night":  ("#0b1a33", "#1d3461", "#3f5b8c", "#f5f0d8"),
}
INK = "#13294b"

# scene per destination when tags alone aren't specific enough
SCENE_OVERRIDE = {
    "agra": "taj", "paris": "eiffel", "tokyo": "fuji", "london": "clock", "dubai": "spire", "abu-dhabi": "mosque",
    "muscat": "mosque", "istanbul": "mosque", "hyderabad": "heritage", "amritsar": "golden", "leh-ladakh": "stupa",
    "bhutan": "stupa", "kathmandu": "stupa", "pokhara": "lake_mountain", "tawang": "stupa", "spiti-valley": "stupa",
    "mcleodganj": "stupa", "gangtok": "stupa", "varanasi": "ghats", "rishikesh": "ghats", "pushkar": "ghats",
    "madurai": "gopuram", "kanyakumari": "gopuram", "mahabalipuram": "gopuram", "hampi": "gopuram",
    "alleppey": "backwaters", "kochi": "backwaters", "udaipur": "lake_palace", "srinagar": "lake_mountain",
    "nainital": "lake_mountain", "jaisalmer": "desert", "kutch": "salt", "jodhpur": "fort", "jaipur": "fort",
    "munnar": "tea", "darjeeling": "tea", "coorg": "tea", "chikmagalur": "tea", "wayanad": "forest",
    "kaziranga": "grassland", "ranthambore": "grassland", "siem-reap": "angkor", "bangkok": "pagoda_city",
    "chiang-mai": "pagoda", "hanoi": "karst", "krabi": "karst", "phuket": "karst", "langkawi": "karst",
    "da-nang-hoi-an": "lanterns", "interlaken": "alps", "auli": "alps", "almaty": "alps", "shimla": "hill_town",
    "mussoorie": "hill_town", "ooty": "hill_town", "mount-abu": "hill_town", "singapore": "city", "hong-kong": "city",
    "kuala-lumpur": "twin", "seoul": "city", "mumbai": "city", "kolkata": "heritage", "baku": "city",
    "amsterdam": "canal", "khajuraho": "temples", "aurangabad": "temples", "mysuru": "heritage",
}


def _rng(slug):
    return random.Random(int(hashlib.md5(slug.encode()).hexdigest(), 16))


def mix(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def scene_for(post):
    slug, tags = post["slug"], set(post.get("tags", []))
    if slug in SCENE_OVERRIDE:
        return SCENE_OVERRIDE[slug]
    for keys, scene in ((("beach", "island", "diving"), "beach"), (("desert",), "desert"), (("snow",), "alps"),
                        (("mountain", "trek"), "mountains"), (("tea", "coffee"), "tea"), (("backwaters",), "backwaters"),
                        (("lakes", "river"), "lake_mountain"), (("wildlife",), "grassland"), (("waterfalls", "nature"), "forest"),
                        (("hills",), "hill_town"), (("spiritual",), "gopuram"), (("heritage", "art"), "heritage"),
                        (("city", "shopping", "nightlife", "food"), "city")):
        if tags & set(keys):
            return scene
    return "mountains"


# ---------------------------------------------------------------- shapes
def ridge(rng, y, amp, n, color, jag=True):
    pts = [(0, H)]
    step = W / n
    for i in range(n + 1):
        x = i * step
        yy = y - rng.uniform(0.3, 1) * amp if (i % 2 or not jag) else y - rng.uniform(0, .35) * amp
        pts.append((x, yy))
    pts.append((W, H))
    return f'<polygon points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" fill="{color}"/>', pts[1:-1]


def peaks(rng, base, height, count, color, snow=True):
    out, xs = [], sorted(rng.uniform(-50, W + 50) for _ in range(count))
    for x in xs:
        h = height * rng.uniform(.65, 1)
        w = h * rng.uniform(1.1, 1.6)
        top = (x, base - h)
        out.append(f'<polygon points="{x - w:.0f},{base} {top[0]:.0f},{top[1]:.0f} {x + w:.0f},{base}" fill="{color}"/>')
        if snow:
            s = h * .28
            out.append(f'<polygon points="{x - s * w / h:.0f},{top[1] + s:.0f} {top[0]:.0f},{top[1]:.0f} {x + s * w / h:.0f},{top[1] + s:.0f} '
                       f'{x + s * w / h * .4:.0f},{top[1] + s * .75:.0f} {x:.0f},{top[1] + s * 1.05:.0f} {x - s * w / h * .4:.0f},{top[1] + s * .75:.0f}" fill="#ffffff" opacity=".92"/>')
    return "".join(out)


def hills(rng, y, amp, color, waves=3):
    d = f"M0,{H} L0,{y}"
    seg = W / waves
    for i in range(waves):
        x0 = i * seg
        d += f" Q{x0 + seg / 2:.0f},{y - amp * rng.uniform(.6, 1.2):.0f} {x0 + seg:.0f},{y + rng.uniform(-amp * .3, amp * .3):.0f}"
    return f'<path d="{d} L{W},{H} Z" fill="{color}"/>'


def palm(x, base, h, color, lean=1):
    tx, ty = x + 40 * lean, base - h
    trunk = f'<path d="M{x},{base} Q{x + 10 * lean},{base - h * .5} {tx},{ty}" stroke="{color}" stroke-width="9" fill="none" stroke-linecap="round"/>'
    fronds = "".join(
        f'<path d="M{tx},{ty} Q{tx + math.cos(a) * 45},{ty + math.sin(a) * 45 - 25} {tx + math.cos(a) * 85:.0f},{ty + math.sin(a) * 85 + 15:.0f}" '
        f'stroke="{color}" stroke-width="7" fill="none" stroke-linecap="round"/>'
        for a in (math.pi, math.pi * 1.15, math.pi * 1.5, math.pi * 1.85, 0, math.pi * .2))
    return trunk + fronds


def pine(x, base, h, color):
    w = h * .38
    return (f'<polygon points="{x - w:.0f},{base} {x:.0f},{base - h:.0f} {x + w:.0f},{base}" fill="{color}"/>'
            f'<polygon points="{x - w * .8:.0f},{base - h * .35:.0f} {x:.0f},{base - h * 1.12:.0f} {x + w * .8:.0f},{base - h * .35:.0f}" fill="{color}"/>')


def dome(cx, base, r, color):
    return (f'<path d="M{cx - r},{base} L{cx - r},{base - r * .2} Q{cx - r},{base - r * 1.5} {cx},{base - r * 1.75} '
            f'Q{cx + r},{base - r * 1.5} {cx + r},{base - r * .2} L{cx + r},{base} Z" fill="{color}"/>'
            f'<rect x="{cx - 2}" y="{base - r * 2.1}" width="4" height="{r * .4}" fill="{color}"/>')


def minaret(x, base, h, w, color):
    return (f'<rect x="{x - w / 2}" y="{base - h}" width="{w}" height="{h}" fill="{color}"/>'
            f'<rect x="{x - w * .8}" y="{base - h * .7}" width="{w * 1.6}" height="5" fill="{color}"/>'
            + dome(x, base - h, w * .75, color))


def water(y, top, bottom, sun=None):
    out = f'<rect x="0" y="{y}" width="{W}" height="{H - y}" fill="url(#wg)"/>'
    out += f'<linearGradient id="wg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>'
    if sun:
        sx, col = sun
        for i in range(6):
            yy = y + 10 + i * 14
            ww = 120 - i * 14
            out += f'<rect x="{sx - ww / 2:.0f}" y="{yy}" width="{ww}" height="3" rx="1.5" fill="{col}" opacity="{.7 - i * .1:.2f}"/>'
    return out


def buildings(rng, base, color, count, hmin, hmax, windows=None):
    out, x = [], -10
    while x < W:
        w = rng.uniform(40, 90)
        h = rng.uniform(hmin, hmax)
        out.append(f'<rect x="{x:.0f}" y="{base - h:.0f}" width="{w:.0f}" height="{h + 2:.0f}" fill="{color}"/>')
        if windows:
            for wy in range(int(base - h + 12), int(base - 8), 16):
                for wx in range(int(x + 8), int(x + w - 8), 14):
                    if rng.random() < .35:
                        out.append(f'<rect x="{wx}" y="{wy}" width="5" height="7" fill="{windows}" opacity=".85"/>')
        x += w + rng.uniform(-6, 6)
    return "".join(out)


def stupa(cx, base, s, color, white):
    return (f'<rect x="{cx - s * 1.3}" y="{base - s * .35}" width="{s * 2.6}" height="{s * .35}" fill="{white}"/>'
            f'<path d="M{cx - s},{base - s * .35} Q{cx},{base - s * 1.6} {cx + s},{base - s * .35} Z" fill="{white}"/>'
            f'<rect x="{cx - s * .25}" y="{base - s * 1.35}" width="{s * .5}" height="{s * .3}" fill="{color}"/>'
            f'<polygon points="{cx - s * .2},{base - s * 1.35} {cx},{base - s * 2.4} {cx + s * .2},{base - s * 1.35}" fill="#d9a441"/>')


def flags(x1, y1, x2, y2):
    cols = ["#2f6fb3", "#ffffff", "#c8372d", "#2e8b57", "#f2c230"]
    out = f'<path d="M{x1},{y1} Q{(x1 + x2) / 2},{max(y1, y2) + 40} {x2},{y2}" stroke="#2a2a2a" stroke-width="1.5" fill="none"/>'
    n = 14
    for i in range(1, n):
        t = i / n
        x = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * (x1 + x2) / 2 + t ** 2 * x2
        y = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * (max(y1, y2) + 40) + t ** 2 * y2
        out += f'<rect x="{x - 7:.0f}" y="{y:.0f}" width="14" height="18" fill="{cols[i % 5]}"/>'
    return out


def shikhara(cx, base, h, w, color):
    pts = f"{cx - w},{base} {cx - w * .9},{base - h * .5} {cx - w * .45},{base - h * .92} {cx},{base - h} {cx + w * .45},{base - h * .92} {cx + w * .9},{base - h * .5} {cx + w},{base}"
    out = f'<polygon points="{pts}" fill="{color}"/>'
    for i in range(1, 6):
        yy = base - h * i / 6
        ww = w * (1 - (i / 6) ** 2 * .55)
        out += f'<rect x="{cx - ww:.0f}" y="{yy:.0f}" width="{ww * 2:.0f}" height="3" fill="#000" opacity=".12"/>'
    out += f'<path d="M{cx},{base - h} L{cx},{base - h - 26} L{cx + 18},{base - h - 20} L{cx},{base - h - 14}" fill="#e85d2a" stroke="{color}" stroke-width="2"/>'
    return out


def gopuram(cx, base, h, w, color):
    out = ""
    tiers = 7
    for i in range(tiers):
        ww = w * (1 - i / tiers * .6)
        th = h / tiers
        out += f'<rect x="{cx - ww:.0f}" y="{base - th * (i + 1):.0f}" width="{ww * 2:.0f}" height="{th + 1:.0f}" fill="{color}"/>'
        out += f'<rect x="{cx - ww:.0f}" y="{base - th * (i + 1):.0f}" width="{ww * 2:.0f}" height="3" fill="#000" opacity=".15"/>'
    top = base - h
    out += f'<path d="M{cx - w * .45},{top} Q{cx},{top - 40} {cx + w * .45},{top} Z" fill="{color}"/>'
    return out


# ---------------------------------------------------------------- scenes
def draw(scene, rng, sky, near, sky_sun_x=400):
    """Returns (svg body, chosen sky key override or None)."""
    far, mid = mix(sky[2], near, .35), mix(sky[2], near, .6)
    g = []
    if scene in ("beach",):
        g.append(water(380, mix(sky[1], "#1b6f8a", .55), mix(sky[1], "#0e3d57", .75), (rng.uniform(300, 600), sky[3])))
        g.append(f'<path d="M0,{H} L0,500 Q250,455 520,505 T{W},480 L{W},{H} Z" fill="#f3d9a4"/>')
        g.append(f'<path d="M0,512 Q250,467 520,517 T{W},492" stroke="#ffffff" stroke-width="4" fill="none" opacity=".7"/>')
        g.append(palm(rng.uniform(40, 120), 560, 250, near, 1))
        g.append(palm(rng.uniform(150, 220), 570, 190, near, 1.3))
        if rng.random() < .6:
            g.append(f'<path d="M560,400 l50,0 l-8,10 l-34,0 z M585,400 l0,-40 l20,36 z" fill="{near}"/>')
    elif scene == "karst":
        g.append(water(420, mix(sky[1], "#1f7a7a", .5), mix(sky[1], "#0e3d4a", .75), (rng.uniform(350, 550), sky[3])))
        for x, h, c in ((120, 260, far), (330, 200, far), (560, 300, mid), (720, 220, mid), (250, 160, near)):
            g.append(f'<path d="M{x - 55},420 C{x - 70},{420 - h * .6} {x - 40},{420 - h} {x},{420 - h} C{x + 40},{420 - h} {x + 70},{420 - h * .6} {x + 55},420 Z" fill="{c}"/>')
        g.append(f'<path d="M300,470 q60,-10 120,0 l-15,14 l-90,0 z" fill="{near}"/>')
    elif scene in ("mountains", "alps", "lake_mountain"):
        g.append(peaks(rng, 430, 280, 3, far))
        g.append(peaks(rng, 470, 200, 4, mid))
        if scene == "lake_mountain":
            g.append(water(470, mix(sky[1], mid, .5), mix(sky[2], near, .5)))
            g.append(f'<path d="M360,500 q40,-12 80,0 l-10,10 l-60,0 z M398,500 l0,-30 l16,26 z" fill="{near}"/>')
            g.append(hills(rng, 560, 30, near, 2))
        else:
            g.append(hills(rng, 520, 50, near, 3))
            for x in range(20, W, 70):
                g.append(pine(x + rng.uniform(-15, 15), 600, rng.uniform(70, 120), mix(near, "#000000", .15)))
        if scene == "alps":
            g.append(f'<rect x="560" y="450" width="70" height="40" fill="#8a3b2e"/><polygon points="550,452 595,420 640,452" fill="#5a2a1f"/>')
    elif scene == "hill_town":
        g.append(peaks(rng, 420, 230, 3, far))
        g.append(hills(rng, 470, 60, mid, 2))
        for i in range(9):
            x, y = rng.uniform(80, 720), rng.uniform(430, 520)
            col = rng.choice(["#c8553d", "#e8b04a", "#f2efe6", "#5b8fb9"])
            g.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="34" height="26" fill="{col}"/><polygon points="{x - 4:.0f},{y:.0f} {x + 17:.0f},{y - 16:.0f} {x + 38:.0f},{y:.0f}" fill="{near}"/>')
        g.append(hills(rng, 560, 30, near, 2))
        for x in (30, 90, 700, 760):
            g.append(pine(x, 600, 140, near))
    elif scene == "tea":
        g.append(hills(rng, 330, 70, far, 2))
        g.append(hills(rng, 400, 80, mix(far, "#3f7d3a", .5), 3))
        g.append(hills(rng, 470, 70, "#4f8f3f", 2))
        for i in range(10):
            y = 480 + i * 13
            g.append(f'<path d="M0,{y} Q400,{y - 30} {W},{y + 5}" stroke="#2f6a2b" stroke-width="5" fill="none" opacity=".6"/>')
        g.append(pine(720, 520, 160, near))
    elif scene in ("desert", "salt", "fort"):
        if scene == "salt":
            g.append(hills(rng, 420, 20, far, 3))
            g.append(f'<rect x="0" y="420" width="{W}" height="180" fill="#f4f1ea"/>')
            g.append(f'<ellipse cx="{sky_sun_x}" cy="470" rx="120" ry="10" fill="{sky[3]}" opacity=".5"/>')
            for i in range(14):
                g.append(f'<polygon points="{rng.uniform(0, W):.0f},{rng.uniform(440, 600):.0f} {rng.uniform(0, W):.0f},{rng.uniform(440, 600):.0f} {rng.uniform(0, W):.0f},{rng.uniform(440, 600):.0f}" fill="none" stroke="#d9d3c4" stroke-width="2"/>')
        else:
            g.append(hills(rng, 470, 60, "#e3a55a", 2))
            g.append(hills(rng, 530, 50, "#c9853f", 3))
        if scene in ("desert", "fort"):
            fx, fy = (480, 470) if scene == "desert" else (400, 420)
            col = mix("#b5743a", near, .35)
            g.append(f'<rect x="{fx - 170}" y="{fy - 90}" width="340" height="90" fill="{col}"/>')
            for i in range(9):
                g.append(f'<rect x="{fx - 170 + i * 40}" y="{fy - 102}" width="22" height="14" fill="{col}"/>')
            for tx in (fx - 150, fx - 40, fx + 80):
                g.append(f'<rect x="{tx}" y="{fy - 150}" width="50" height="60" fill="{col}"/>' + dome(tx + 25, fy - 150, 20, col))
            for i in range(6):
                g.append(f'<path d="M{fx - 140 + i * 50},{fy} l0,-22 q12,-14 24,0 l0,22 z" fill="{near}" opacity=".5"/>')
        if scene == "desert":
            g.append(f'<path d="M140,540 q10,-30 30,-30 q10,-20 25,-2 q20,-5 30,15 l0,30 l-6,0 l0,-20 l-60,0 l0,20 l-6,0 z" fill="{near}"/>')
        if scene == "fort":
            g.append(hills(rng, 560, 30, near, 2))
    elif scene in ("backwaters", "lake_palace"):
        g.append(hills(rng, 400, 40, far, 2))
        g.append(water(420, mix(sky[1], "#2a6f6a", .45), mix(sky[2], "#0f3b3a", .7), (rng.uniform(450, 650), sky[3])))
        if scene == "lake_palace":
            col = "#f4ecdb"
            g.append(f'<rect x="250" y="370" width="300" height="70" fill="{col}"/>')
            for i in range(7):
                g.append(f'<path d="M{262 + i * 40},440 l0,-30 q14,-18 28,0 l0,30 z" fill="{mix(col, near, .35)}"/>')
            for tx in (270, 400, 530):
                g.append(dome(tx, 370, 22, col))
            g.append(f'<rect x="250" y="440" width="300" height="40" fill="{col}" opacity=".25"/>')
        else:
            g.append(f'<path d="M260,470 Q400,500 540,470 L520,490 Q400,510 280,490 Z" fill="#5a3418"/>'
                     f'<path d="M290,470 Q400,420 510,470 Z" fill="#c9a26b"/>'
                     f'<path d="M300,470 Q400,430 500,470" stroke="#8a6a3c" stroke-width="3" fill="none"/>')
        g.append(palm(60, 470, 230, near, 1))
        g.append(palm(720, 470, 210, near, -1))
        g.append(f'<rect x="0" y="465" width="140" height="10" fill="{near}"/><rect x="660" y="465" width="140" height="10" fill="{near}"/>')
    elif scene in ("forest", "grassland"):
        g.append(hills(rng, 380, 80, far, 2))
        if scene == "forest":
            g.append(f'<path d="M420,300 L470,300 L480,600 L410,600 Z" fill="{mid}"/>'
                     f'<path d="M432,300 L458,300 L462,600 L428,600 Z" fill="#e8f4f8"/>')
            g.append(hills(rng, 470, 40, mid, 3))
            for x in range(0, W, 46):
                g.append(pine(x + rng.uniform(-10, 10), 600, rng.uniform(110, 190), near))
        else:
            g.append(f'<rect x="0" y="440" width="{W}" height="160" fill="{mix("#c9b458", near, .25)}"/>')
            for i in range(60):
                x = rng.uniform(0, W)
                g.append(f'<path d="M{x:.0f},600 q4,-40 {rng.uniform(-10, 10):.0f},-{rng.uniform(40, 90):.0f}" stroke="{mix("#8a7a2e", near, .3)}" stroke-width="3" fill="none"/>')
            g.append(f'<path d="M150,440 q30,-60 70,-60 q40,0 70,60 Z" fill="{near}"/><rect x="214" y="440" width="12" height="60" fill="{near}"/>')
            g.append(f'<path d="M480,500 q10,-40 50,-40 l60,0 q20,0 25,25 l0,30 l-8,0 l0,-15 l-100,0 l0,15 l-8,0 z M520,460 l-10,-15 l8,0 z" fill="{near}"/>')
    elif scene in ("city", "pagoda_city", "twin", "spire", "clock", "eiffel", "canal"):
        g.append(buildings(rng, 470, far, 10, 80, 200))
        g.append(buildings(rng, 520, mid, 10, 60, 160, windows=sky[3] if sky[0] in (SKIES["night"][0], SKIES["dusk"][0]) else None))
        if scene == "twin":
            for x in (340, 430):
                g.append(f'<path d="M{x},520 L{x},250 L{x + 10},220 L{x + 20},160 L{x + 30},220 L{x + 40},250 L{x + 40},520 Z" fill="{near}"/>')
            g.append(f'<rect x="380" y="330" width="50" height="8" fill="{near}"/>')
        if scene == "spire":
            g.append(f'<path d="M380,520 L384,300 L392,200 L398,90 L400,40 L402,90 L408,200 L416,300 L420,520 Z" fill="{near}"/>')
        if scene == "clock":
            g.append(f'<rect x="370" y="220" width="60" height="300" fill="{near}"/><polygon points="365,222 400,140 435,222" fill="{near}"/>'
                     f'<circle cx="400" cy="260" r="20" fill="{sky[3]}"/><path d="M400,260 l0,-12 M400,260 l9,4" stroke="{near}" stroke-width="3"/>')
        if scene == "eiffel":
            g.append(f'<path d="M330,560 Q370,420 388,260 L394,120 L400,60 L406,120 L412,260 Q430,420 470,560 L445,560 Q420,470 400,470 Q380,470 355,560 Z" fill="{near}"/>'
                     f'<rect x="370" y="380" width="60" height="8" fill="{near}"/><rect x="384" y="260" width="32" height="6" fill="{near}"/>')
        if scene == "pagoda_city":
            g.append(f'<polygon points="360,520 400,250 440,520" fill="{near}"/><rect x="396" y="215" width="8" height="40" fill="{near}"/>')
        if scene == "canal":
            g.append(water(520, mix(sky[1], "#2a5d7a", .5), mix(sky[2], "#173a52", .7)))
            for i in range(6):
                x = 60 + i * 120
                col = rng.choice(["#8a3b2e", "#2f4858", "#6b4f3a", "#33658a"])
                g.append(f'<rect x="{x}" y="360" width="90" height="162" fill="{col}"/><polygon points="{x},360 {x + 45},320 {x + 90},360" fill="{col}"/>')
                for wy in (380, 420, 460):
                    g.append(f'<rect x="{x + 15}" y="{wy}" width="16" height="22" fill="#f3e3b3"/><rect x="{x + 58}" y="{wy}" width="16" height="22" fill="#f3e3b3"/>')
        g.append(f'<rect x="0" y="518" width="{W}" height="82" fill="{near}"/>')
    elif scene in ("heritage", "taj", "mosque", "golden", "angkor", "temples", "lanterns"):
        col = {"taj": "#f6f1e7", "golden": "#e3b448", "angkor": mix("#8a7f6a", near, .3)}.get(scene, mix("#e9d8b8", near, .25))
        if scene == "taj":
            g.append(f'<rect x="0" y="470" width="{W}" height="130" fill="{mix("#3f6b3a", near, .4)}"/>')
            g.append(f'<rect x="370" y="470" width="60" height="130" fill="{mix(sky[1], "#6aa0c0", .5)}"/>')
            g.append(f'<rect x="250" y="360" width="300" height="110" fill="{col}"/>')
            g.append(dome(400, 360, 70, col))
            for x in (290, 510):
                g.append(dome(x, 360, 24, col))
            for x in (190, 610):
                g.append(minaret(x, 470, 210, 16, col))
            g.append(f'<path d="M370,470 l0,-70 q30,-36 60,0 l0,70 z" fill="{mix(col, near, .35)}"/>')
            for x in range(10, W, 60):
                if not 160 < x < 640:
                    g.append(pine(x, 520, 90, near))
        elif scene == "angkor":
            g.append(water(470, mix(sky[1], "#4b7a6a", .4), mix(sky[2], "#1e3d36", .7)))
            g.append(f'<rect x="200" y="380" width="400" height="90" fill="{col}"/>')
            for x, h in ((260, 110), (330, 140), (400, 190), (470, 140), (540, 110)):
                g.append(f'<path d="M{x - 30},380 Q{x - 26},{380 - h * .6} {x},{380 - h} Q{x + 26},{380 - h * .6} {x + 30},380 Z" fill="{col}"/>')
            g.append(palm(80, 480, 200, near, 1))
        elif scene == "lanterns":
            g.append(buildings(rng, 520, mix("#c98b3a", near, .45), 8, 90, 140))
            g.append(water(520, "#20363f", "#10232b"))
            for i in range(16):
                x, y = rng.uniform(30, 770), rng.uniform(90, 300)
                c = rng.choice(["#e94f37", "#f6ae2d", "#f26419", "#c1292e"])
                g.append(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{y - 20:.0f}" stroke="#1d1d1d" stroke-width="1"/><ellipse cx="{x:.0f}" cy="{y:.0f}" rx="18" ry="22" fill="{c}"/>')
        else:
            g.append(hills(rng, 470, 40, mid, 2))
            if scene == "temples":
                for x, h in ((260, 180), (400, 240), (540, 170)):
                    g.append(shikhara(x, 480, h, h * .32, col))
            else:
                g.append(f'<rect x="230" y="380" width="340" height="100" fill="{col}"/>')
                g.append(dome(400, 380, 60, col))
                g.append(dome(300, 380, 26, col) + dome(500, 380, 26, col))
                for x in (220, 580):
                    g.append(minaret(x, 480, 190 if scene == "mosque" else 140, 14, col))
                for i in range(7):
                    g.append(f'<path d="M{250 + i * 45},480 l0,-48 q16,-22 32,0 l0,48 z" fill="{mix(col, near, .4)}"/>')
            if scene == "golden":
                g.append(water(480, mix(sky[1], "#3b6b8a", .5), mix(sky[2], "#183a52", .7), (400, "#e3b448")))
            else:
                g.append(f'<rect x="0" y="478" width="{W}" height="122" fill="{near}"/>')
    elif scene in ("stupa",):
        g.append(peaks(rng, 430, 260, 3, far))
        g.append(peaks(rng, 480, 160, 3, mid, snow=False))
        g.append(hills(rng, 520, 30, near, 2))
        g.append(stupa(400, 520, 70, near, "#f6f2ea"))
        g.append(flags(60, 300, 380, 360) + flags(420, 360, 760, 290))
    elif scene in ("ghats", "gopuram"):
        g.append(hills(rng, 420, 40, far, 2))
        col = mix("#d9a46a", near, .3)
        if scene == "gopuram":
            g.append(gopuram(400, 470, 260, 90, col))
            g.append(gopuram(220, 470, 150, 55, mix(col, near, .25)))
            g.append(palm(640, 480, 220, near, -1))
            g.append(f'<rect x="0" y="468" width="{W}" height="132" fill="{near}"/>')
        else:
            g.append(shikhara(260, 400, 190, 60, col) + shikhara(520, 400, 150, 48, mix(col, near, .2)))
            g.append(f'<rect x="120" y="398" width="560" height="10" fill="{col}"/>')
            for i in range(6):
                g.append(f'<rect x="0" y="{400 + i * 12}" width="{W}" height="12" fill="{mix(col, near, .15 + i * .08)}"/>')
            g.append(water(472, mix(sky[2], "#5a7a8a", .4), mix(sky[2], near, .7), (rng.uniform(300, 500), sky[3])))
            g.append(f'<path d="M320,520 q60,-14 120,0 l-12,14 l-96,0 z" fill="{near}"/>')
            for i in range(9):
                g.append(f'<circle cx="{rng.uniform(100, 700):.0f}" cy="{rng.uniform(500, 580):.0f}" r="4" fill="#ffb84d"/>')
    elif scene == "pagoda":
        g.append(hills(rng, 400, 70, far, 2))
        g.append(hills(rng, 470, 60, mid, 3))
        col = "#e0b04a"
        g.append(f'<rect x="330" y="400" width="140" height="40" fill="{col}"/><rect x="345" y="370" width="110" height="30" fill="{col}"/>')
        g.append(f'<path d="M360,370 Q370,300 400,250 Q430,300 440,370 Z" fill="{col}"/><path d="M400,250 L403,170 L397,170 Z" fill="{col}"/>')
        for x in range(0, W, 52):
            if not 300 < x < 500:
                g.append(pine(x + rng.uniform(-8, 8), 560, rng.uniform(90, 150), near))
        g.append(hills(rng, 560, 20, near, 2))
    elif scene == "fuji":
        g.append(f'<path d="M80,500 L330,190 Q400,165 470,190 L720,500 Z" fill="{mix(far, "#5d7fa8", .4)}"/>')
        g.append(f'<path d="M330,190 Q400,165 470,190 L520,252 L490,240 L460,262 L430,238 L400,264 L370,238 L340,262 L310,240 L280,252 Z" fill="#ffffff"/>')
        g.append(water(500, mix(sky[1], "#3d6f9a", .5), mix(sky[2], "#173a52", .7)))
        g.append(f'<polygon points="590,500 650,330 710,500" fill="{near}"/><rect x="630" y="390" width="40" height="6" fill="#c8372d"/>')
        for x in (40, 110):
            g.append(pine(x, 520, 150, near))
    else:
        g.append(peaks(rng, 470, 240, 4, mid))
    return "".join(g)


def make_poster(post):
    rng = _rng(post["slug"])
    scene = scene_for(post)
    pref = {"beach": ["sunset", "day", "dawn"], "desert": ["sunset", "dusk"], "salt": ["dusk", "dawn"],
            "city": ["dusk", "night"], "pagoda_city": ["dusk", "sunset"], "twin": ["night", "dusk"], "spire": ["dusk", "night"],
            "lanterns": ["night"], "ghats": ["dawn", "sunset"], "taj": ["dawn", "sunset"], "golden": ["dusk", "night"],
            "alps": ["day", "dawn"], "tea": ["day", "dawn"], "forest": ["day", "dawn"], "stupa": ["day", "dawn"]}
    key = rng.choice(pref.get(scene, ["day", "dawn", "sunset", "dusk"]))
    sky = SKIES[key]
    near = mix(INK, sky[0], .15)
    sun_x, sun_y = rng.uniform(150, 650), rng.uniform(110, 230)
    stars = ""
    if key in ("night", "dusk"):
        stars = "".join(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, 260):.0f}" r="{rng.uniform(.6, 1.8):.1f}" fill="#fff" opacity="{rng.uniform(.4, .95):.2f}"/>'
                        for _ in range(60 if key == "night" else 25))
    body = draw(scene, rng, sky, near, round(sun_x))
    uid = post["slug"].replace("-", "")
    body = body.replace('id="wg"', f'id="wg{uid}"').replace("url(#wg)", f"url(#wg{uid})")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" role="img" aria-label={quoteattr("Illustration of " + post["name"])}>
<defs><linearGradient id="sky{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[0]}"/><stop offset=".55" stop-color="{sky[1]}"/><stop offset="1" stop-color="{sky[2]}"/></linearGradient></defs>
<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>{stars}
<circle cx="{sun_x:.0f}" cy="{sun_y:.0f}" r="{70 if key != "night" else 38}" fill="{sky[3]}" opacity="{.9 if key != "day" else .75}"/>
{body}
</svg>'''
