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

# English item names from the code lists -> zh-TW in-game names. Unknown names stay in English.
ZH = {
    # 原神
    "Primogem": "原石", "Mora": "摩拉", "Hero's Wit": "大英雄的經驗",
    "Adventurer's Experience": "冒險家的經驗", "Wanderer's Advice": "流浪者的經驗",
    "Mystic Enhancement Ore": "精鍛用魔礦", "Fine Enhancement Ore": "精鍛用良礦",
    "Enhancement Ore": "精鍛用雜礦", "Jueyun Chili Chicken": "絕雲鍋巴",
    "Fragile Resin": "脆弱樹脂",
    # 星穹鐵道
    "Stellar Jade": "星瓊", "Credit": "信用點", "Traveler's Guide": "漫遊指南",
    "Adventure Log": "冒險記錄", "Travel Encounters": "旅情見聞",
    "Refined Aether": "提純以太", "Condensed Aether": "凝縮以太",
    "Lost Gold Fragment": "失落金塊", "Lost Crystal": "失落晶塊", "Lost Lightdust": "失落塵金",
    "Fuel": "燃料", "Bottled Soda": "瓶裝汽水", "Cold Joke": "冷笑話",
    # 絕區零
    "Polychrome": "菲林", "Denny": "丁尼", "Dennies": "丁尼",
    "Official Investigator Log": "調查員紀錄", "Senior Investigator Log": "資深調查員紀錄",
    "Investigator Log": "初級調查員紀錄",
    "W-Engine Power Supply": "音擎電源", "W-Engine Power Supplies": "音擎電源", "W-Engine Energy Module": "音擎能源模組",
    "Bangboo Algorithm Module": "邦布演算法模組", "Bangboo System Widget": "邦布系統插件",
    "Free items": "未公開獎勵",
}
_ZH_RE = re.compile("|".join(re.escape(k) + "s?" for k in sorted(ZH, key=len, reverse=True)
                             if k != "Dennies"), re.IGNORECASE)
_ZH_LOWER = {k.lower(): v for k, v in ZH.items()}


_NUM_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
              "seven": "7", "eight": "8", "nine": "9", "ten": "10"}


def translate(text: str) -> str:
    """Translate item names; also tidy free-text lists like '30 stellar jade, two fuel, and 20k credits'."""
    text = text.replace("\u2019", "'").replace("\u00a0", " ")
    text = re.sub(r"\b(\d+)k\b", lambda m: m.group(1) + "000", text)
    text = re.sub(r"\b(" + "|".join(_NUM_WORDS) + r")\b", lambda m: _NUM_WORDS[m.group(1).lower()], text, flags=re.IGNORECASE)
    text = re.sub(r",?\s+and\s+|,\s+", "、", text)

    def repl(m: re.Match) -> str:
        w = m.group(0).lower()
        return _ZH_LOWER.get(w) or _ZH_LOWER.get(w[:-1], m.group(0))
    text = _ZH_RE.sub(repl, text)
    # "60 星瓊" -> "星瓊 ×60" so free-text and structured sources look the same
    return "、".join(re.sub(r"^(\d[\d,]*) (.+)$", r"\2 ×\1", seg.strip()) if "×" not in seg else seg.strip()
                    for seg in text.split("、"))


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
                rewards = translate(re.sub(r"\s*[x\*]\s*(?=\d)", " ×", str(rewards).replace(";", "、")).strip())
                if code not in codes or (rewards and not codes[code]):
                    codes[code] = rewards
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
