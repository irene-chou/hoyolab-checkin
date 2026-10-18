"""Shared multi-account config for checkin.py and redeem.py.

ACCOUNTS      repo variable, e.g. "main:gi,hsr;alt:hsr" (default "main:gi,hsr")
SECRETS_JSON  all GitHub secrets as JSON (toJSON(secrets)); falls back to os.environ

Secret naming: account "main" uses the plain name (HOYOLAB_COOKIE), any other
account uses a suffix (HOYOLAB_COOKIE_ALT). HOYOLAB_COOKIE_MAIN also works.
"""
from __future__ import annotations

import json
import os


def _secrets() -> dict[str, str]:
    raw = os.environ.get("SECRETS_JSON", "").strip()
    data = {}
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {**os.environ, **{k: str(v) for k, v in data.items()}}


def parse_accounts(default_games: str = "gi,hsr") -> list[tuple[str, list[str]]]:
    spec = os.environ.get("ACCOUNTS", "").strip() or f"main:{default_games}"
    accounts = []
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, games = part.partition(":")
        games = [g.strip() for g in (games or default_games).split(",") if g.strip()]
        accounts.append((name.strip(), games))
    return accounts


def secret(key: str, account: str) -> str:
    s = _secrets()
    suffix = account.strip().upper()
    for k in ([key] if suffix == "MAIN" else []) + [f"{key}_{suffix}"]:
        v = s.get(k, "").strip()
        if v:
            return v
    return ""


def shared(key: str) -> str:
    return _secrets().get(key, "").strip()
