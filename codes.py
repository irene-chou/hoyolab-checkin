#!/usr/bin/env python3
"""Watch community gift-code lists and post new codes with redemption links to Discord.

No HoYoLAB cookies needed. Env vars:
  ACCOUNTS         repo variable; only the game list is used (see accounts.py)
  DISCORD_WEBHOOK  optional

State: codes.json keeps every code already announced per game.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from accounts import parse_accounts, shared

STATE = Path(__file__).with_name("codes.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

GAMES = {
    "gi": {
        "name": "原神",
        "link": "https://genshin.hoyoverse.com/gift?code={code}",
        "sources": [
            ("https://api.ennead.cc/mihoyo/genshin/codes", "active"),
            ("https://hoyo-codes.seria.moe/codes?game=genshin", "codes"),
        ],
    },
    "hsr": {
        "name": "星穹鐵道",
        "link": "https://hsr.hoyoverse.com/gift?code={code}",
        "sources": [
            ("https://api.ennead.cc/mihoyo/starrail/codes", "active"),
            ("https://hoyo-codes.seria.moe/codes?game=hkrpg", "codes"),
        ],
    },
    "zzz": {
        "name": "絕區零",
        "link": "https://zenless.hoyoverse.com/redemption?code={code}",
        "sources": [
            ("https://api.ennead.cc/mihoyo/zenless/codes", "active"),
            ("https://hoyo-codes.seria.moe/codes?game=nap", "codes"),
        ],
    },
}


def fetch_codes(game: dict) -> tuple[dict[str, str], int]:
    """Returns ({code: rewards}, number of sources that answered)."""
    codes: dict[str, str] = {}
    ok = 0
    for url, key in game["sources"]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            ok += 1
            for item in data.get(key, []):
                code = str(item.get("code", "")).strip().upper()
                if not code:
                    continue
                rewards = item.get("rewards", "")
                if isinstance(rewards, list):
                    rewards = "、".join(rewards)
                rewards = re.sub(r"\s*\*\s*(?=\d)", " ×", str(rewards).replace(";", "、")).strip()
                if rewards or code not in codes:
                    codes[code] = rewards or codes.get(code, "")
        except Exception as e:  # noqa: BLE001
            print(f"[{game['name']}] 兌換碼來源失敗 {url}: {e}", file=sys.stderr)
    return codes, ok


def notify(webhook: str, content: str) -> None:
    payload = json.dumps({"username": "HoYoLAB 兌換碼", "content": content}).encode()
    req = urllib.request.Request(webhook, data=payload, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:  # noqa: BLE001
        print(f"Discord 通知失敗: {e}", file=sys.stderr)


def main() -> int:
    webhook = shared("DISCORD_WEBHOOK")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    today = dt.date.today().isoformat()
    games = [g for g in GAMES if any(g in acct_games for _, _, acct_games in parse_accounts())]

    sections, errors, changed = [], [], False
    for key in games:
        game = GAMES[key]
        seen = state.setdefault(key, {})
        codes, ok = fetch_codes(game)
        if not ok:
            errors.append(f"❌ {game['name']}：所有兌換碼來源都無法連線")
            continue
        new = {c: r for c, r in codes.items() if c not in seen}
        print(f"[{game['name']}] 來源 {len(codes)} 組，新 {len(new)} 組")
        if not new:
            continue
        lines = [f"🎁 **{game['name']}** 新兌換碼"]
        for code, reward in new.items():
            seen[code] = {"rewards": reward, "seen": today}
            changed = True
            link = game["link"].format(code=code)
            lines.append(f"`{code}`" + (f"（{reward}）" if reward else "") + f"\n<{link}>")
        sections.append("\n".join(lines))

    if changed:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    report = "\n\n".join(sections + errors)
    if report:
        print(report)
    if report and webhook:
        notify(webhook, report)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
