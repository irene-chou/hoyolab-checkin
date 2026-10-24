"""Shared multi-account config for checkin.py and codes.py.

ACCOUNTS  repo variable, e.g. "player1@MAIN:gi,hsr;player2@ALT:zzz" (default "main:gi,hsr")
          name       display label used in notifications and redeemed.json
          @SUFFIX    optional secret suffix; defaults to NAME upper-cased
Secrets are read from env vars; the workflow must list each account's secrets.

Secret naming: suffix MAIN uses the plain name (HOYOLAB_COOKIE or HOYOLAB_COOKIE_MAIN),
any other suffix is appended (HOYOLAB_COOKIE_ALT).
"""
from __future__ import annotations

import os


def _secrets() -> dict[str, str]:
    return dict(os.environ)


def parse_accounts(default_games: str = "gi,hsr") -> list[tuple[str, str, list[str]]]:
    """Returns [(name, secret_suffix, games), ...]."""
    spec = os.environ.get("ACCOUNTS", "").strip() or f"main:{default_games}"
    accounts = []
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        label, _, games = part.partition(":")
        name, _, suffix = label.partition("@")
        name = name.strip()
        suffix = (suffix or name).strip().upper()
        games = [g.strip() for g in (games or default_games).split(",") if g.strip()]
        accounts.append((name, suffix, games))
    return accounts


def secret(key: str, suffix: str) -> str:
    s = _secrets()
    suffix = suffix.strip().upper()
    for k in ([key] if suffix == "MAIN" else []) + [f"{key}_{suffix}"]:
        v = s.get(k, "").strip()
        if v:
            return v
    return ""


def shared(key: str) -> str:
    return _secrets().get(key, "").strip()
