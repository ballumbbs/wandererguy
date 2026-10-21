"""Shared helpers: paths, config, dates."""
import datetime as dt
import json
import os
import pathlib
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
POSTS = ROOT / "content" / "posts"
STATE_FILE = DATA / "state.json"
IST = ZoneInfo("Asia/Kolkata")


def load_json(path, default=None):
    path = pathlib.Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config():
    cfg = load_json(ROOT / "config.json")
    aff = cfg.setdefault("affiliates", {})
    for key in list(aff):
        if os.environ.get(key):  # GitHub Actions variables / secrets win
            aff[key] = os.environ[key].strip()
    for key in ("BASE_URL", "HOME_AIRPORT", "CLAUDE_MODEL"):
        if os.environ.get(key):
            cfg[key.lower()] = os.environ[key].strip()
    return cfg


def today():
    """Site date in IST. SITE_DATE=YYYY-MM-DD overrides it (useful for testing)."""
    if os.environ.get("SITE_DATE"):
        return dt.date.fromisoformat(os.environ["SITE_DATE"])
    return dt.datetime.now(IST).date()
