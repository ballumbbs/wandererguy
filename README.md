# wandererguy.in — fully automated travel site

Every morning at **6:00 AM IST**, without you touching anything, GitHub:

1. **Publishes a new destination guide** (55 are live from launch; 29 more are queued, then new ones are written by Claude if you add an API key) (best time, things to do, food, where to stay, how to get there, FAQs, packing list).
2. **Refreshes the daily deals** — hotel searches for *this weekend* and *3 weeks out*, plus flight searches from your home airport, all with dates pre-filled and your affiliate IDs attached.
3. **Rotates the featured destinations** on the homepage.
4. **Adds free-licensed photos** from Wikimedia Commons to any guide that doesn't have one, with photographer credits (saved in `content/photos.json` — edit that file to swap a photo).
5. Rebuilds the search index, sitemap and RSS feed and **deploys to wandererguy.in**.

Affiliate links: **Booking.com** (`aid`), **Agoda** (`cid`), **Amazon.in** (`tag`), **Travelpayouts / Aviasales** flights (`marker`).

Cost to run: **₹0** (GitHub Pages + Actions free tier). Optional Claude API key for better articles (a few rupees per post).

---

## One-time setup (about 20 minutes)

### 1. Put the code on GitHub
1. Create a free account at github.com (if you don't have one).
2. Click **New repository** → name it `wandererguy` → **Public** → Create.
3. On the new repo page click **uploading an existing file**, drag in *everything inside this folder* (including the `.github` folder), and **Commit**.
   - Tip: on Mac, press `Cmd+Shift+.` in Finder to see the hidden `.github` folder. Or install GitHub Desktop and publish the folder from there.

### 2. Turn on GitHub Pages
Repo → **Settings → Pages** → under *Build and deployment*, set **Source = GitHub Actions**.

### 3. Add your affiliate IDs
Repo → **Settings → Secrets and variables → Actions → Variables tab → New repository variable**. Add each one you have:

| Name | Where to find it | Example |
|---|---|---|
| `BOOKING_TP_LINK` | Booking.com **through Travelpayouts** — see below | `https://tp.media/r?marker=…&u=…` |
| `BOOKING_AID` | Only if you have a *direct* Booking.com partner account (overrides the line above) | `1234567` |
| `AGODA_CID` | Agoda Partners → your site ID (CID) | `1891234` |
| `AMAZON_TAG` | Amazon Associates India → your tracking ID | `wandererguy-21` |
| `TP_MARKER` | Travelpayouts → profile → your marker | `512345` |
| `HOME_AIRPORT` *(optional)* | Departure airport for flight links (default `DEL`) | `BOM` |

Links work even before you add IDs — they just won't earn until you do.

**Booking.com via Travelpayouts (`BOOKING_TP_LINK`):**
1. Travelpayouts → **Programs** → find **Booking.com** → **Join** (approval takes up to 3 business days).
2. Once approved: **Tools → Links**, choose Booking.com, paste `https://www.booking.com/` as the page, and **turn OFF "Short link"**.
3. Copy the long link (starts with `https://tp.media/r?marker=793264…`) and save it as the `BOOKING_TP_LINK` variable.

The site swaps in each destination's own hotel search (with dates) while keeping your tracking. A short `….tp.st/…` link won't work here — it must be the long one.

### 4. (Optional, recommended) Better articles with Claude
Repo → **Settings → Secrets and variables → Actions → Secrets tab → New repository secret**
- Name: `ANTHROPIC_API_KEY`, value: your key from console.anthropic.com

With the key, every post is a unique, longer article (with a 3-day itinerary), and the site keeps covering new places after the built-in list of 35 runs out (30 more are queued in `data/extra_destinations.json`). Without it, posts are assembled from the curated data, and after ~35 days the oldest guides are refreshed in rotation.

### 5. Connect wandererguy.in
At your domain registrar (GoDaddy, Hostinger, BigRock, etc.) → DNS settings:

| Type | Host | Value |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | `YOUR-GITHUB-USERNAME.github.io` |

Delete any other A record for `@`. Then in **Settings → Pages**, enter `wandererguy.in` as the custom domain and tick **Enforce HTTPS** once it becomes available (DNS can take a few hours).

### 5b. Point wandererguy.com at the site
GitHub Pages serves one domain per site, so `wandererguy.in` stays the main address and `wandererguy.com` forwards to it.
GoDaddy → **My Products → wandererguy.com → DNS → Forwarding → Add forwarding**:
- Forward to: `https://wandererguy.in`
- Redirect type: **Permanent (301)** — this passes Google ranking to the .in site
- Settings: **Forward only** (not masking)

Add the same forwarding for the `www` subdomain. Wait up to an hour, then open `wandererguy.com` — it should land on `https://wandererguy.in`.

### 6. Launch
Repo → **Actions → Daily update & deploy → Run workflow**. In ~1 minute your first guide is live. From then on it runs itself every morning.

---

## Day-to-day

- **Nothing to do.** Check the **Actions** tab occasionally — a green tick means today's post went out.
- **Add your own destinations:** add an entry to `data/destinations.json` (copy an existing one). New entries are published in order.
- **Change the posting time:** edit the `cron` line in `.github/workflows/daily.yml` (it's in UTC; IST = UTC + 5:30).
- **Change the look:** `static/style.css` and `templates/`.
- **Edit a published post:** edit its file in `content/posts/` — the site redeploys automatically.
- **My Experience pages:** each file in `content/experiences/` becomes a page under `/experiences/` (the Everest Base Camp trek is the first). Copy it to add another trip. Put a YouTube video ID in `"youtube_video"` to embed that video on the page.
- **YouTube channel link:** set `youtube_url` and `youtube_name` in `config.json`.
- **Search:** typing a place, landmark (e.g. "Taj Mahal", "Thamel") or close spelling ("manli") and pressing Enter opens that page directly. Landmarks come from each guide's highlights and stay areas; add extra words with `"search_keywords"`. Places without a guide fall back to a Booking.com hotel search with your tracking.

## Test it on your computer (optional)
```bash
pip install -r requirements.txt
python scripts/generate_daily.py     # writes today's post
python scripts/build.py              # builds the site into ./public
python -m http.server -d public 8000 # open http://localhost:8000
```

## Good to know
- **Check one link of each type once** after adding IDs (click it and confirm the partner dashboard registers the click). Partners occasionally change their URL formats; all link formats live in `scripts/affiliates.py`.
- **Amazon Associates India** closes accounts that don't make 3 qualifying sales within the first 180 days — share the site to get early traffic.
- **Google rewards original content.** Auto-generated pages rank better when you add your own photos and experiences — editing a post now and then helps a lot.
- The site never shows invented prices; deal cards open live searches so visitors see real, current prices.
- The required affiliate disclosure (including Amazon's exact wording) is on every page footer and at `/disclosure/`.

## Project layout
```
.github/workflows/daily.yml   ← the daily automation
config.json                   ← site name, domain, defaults
data/destinations.json        ← 84 curated destinations (India and abroad)
data/extra_destinations.json  ← 30 more (written by Claude when the API key is set)
data/gear.json                ← packing items for Amazon links
data/state.json               ← what has been published and when (auto)
content/posts/*.json          ← published guides (auto)
scripts/generate_daily.py     ← writes the day's post
scripts/build.py              ← renders the site + deals + search index + sitemap + RSS
scripts/fetch_photos.py       ← finds a credited Wikimedia Commons photo for each guide
static/site.js                ← search box suggestions, search page, destination filters
scripts/affiliates.py         ← all affiliate link formats
templates/, static/           ← design
```
