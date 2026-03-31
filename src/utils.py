"""Utility functions for Paper Agent."""

import json
import hashlib
import os
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def load_config(path="config.json"):
    """Load configuration from config.json."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config, path="config.json"):
    """Save configuration to config.json."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_history(path="history.json"):
    """Load push history from history.json."""
    if not os.path.exists(path):
        return {"pushed_papers": [], "last_push": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history, path="history.json"):
    """Save push history to history.json."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def normalize_title(title: str) -> str:
    """Normalize a paper title for dedup comparison."""
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title


def title_hash(title: str) -> str:
    """Generate a hash from a normalized title."""
    return hashlib.md5(normalize_title(title).encode()).hexdigest()


def get_local_now(timezone_name: str = "America/Edmonton"):
    """Get current time in the configured IANA timezone."""
    try:
        return datetime.now(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        fallback = timezone(timedelta(hours=-6))
        return datetime.now(fallback)


def get_mdt_now():
    """Backward-compatible helper for legacy callers."""
    return get_local_now("America/Edmonton")


def get_env_or_default(env_key: str, default=None):
    """Get environment variable or return default."""
    val = os.environ.get(env_key, "")
    return val if val.strip() else default
