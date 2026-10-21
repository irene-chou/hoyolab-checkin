#!/usr/bin/env python3
"""Auto-redeem gift codes for Genshin Impact and Honkai: Star Rail via HoYoLAB.

Env vars:
  HOYOLAB_REDEEM_COOKIE  "cookie_token_v2=...; account_mid_v2=...; account_id_v2=..."
                         (falls back to HOYOLAB_COOKIE if it already contains cookie_token_v2)
  DISCORD_WEBHOOK        optional
  GAMES                  optional, default gi,hsr
  HOYOLAB_LANG           optional, default zh-tw

State: redeemed.json in the repo keeps codes that reached a final state
(redeemed / expired / invalid / already used) so they are never retried.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from accounts import parse_accounts, secret, shared

STATE = Path(__file__).with_name("redeemed.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

GAMES = {
    "gi": {
        "name": "原神",
        "biz": "hk4e_global",
        "redeem": "https://sg-hk4e-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkey",
        "method": "GET",
        "sources": [
            ("https://hoyo-codes.seria.moe/codes?game=genshin", "codes"),
            ("https://api.ennead.cc/mihoyo/genshin/codes", "active"),
        ],
    },
    "hsr": {
        "name": "星穹鐵道",
        "biz": "hkrpg_global",
        "redeem": "https://sg-hkrpg-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkeyRisk",
        "method": "POST",
        "sources": [
            ("https://hoyo-codes.seria.moe/codes?game=hkrpg", "codes"),
            ("https://api.ennead.cc/mihoyo/starrail/codes", "active"),
        ],
    },
    "zzz": {
        "name": "絕區零",
        "biz": "nap_global",
        "redeem": "https://public-operation-nap.hoyoverse.com/common/apicdkey/api/webExchangeCdkey",
        "method": "GET",
        "sources": [
            ("https://hoyo-codes.seria.moe/codes?game=nap", "codes"),
            ("https://api.ennead.cc/mihoyo/zenless/codes", "active"),
        ],
    },
}

# retcode -> (final?, message)
RESULTS = {
    0: (True, "兌換成功"),
    -2001: (True, "已過期"),
    -2003: (True, "無效的兌換碼"),
    -2006: (True, "兌換次數已達上限"),
    -2017: (True, "已經兌換過"),
    -2018: (True, "已經兌換過"),
    -2016: (False, "冷卻中"),
    -1048: (False, "系統忙碌"),
}
COOKIE_ERRORS = {-100, -10001, -1071}
COOLDOWN = 5.5


def request(url: str, cookie: str, method: str = "GET", params: dict | None = None) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": UA,
        "Origin": "https://genshin.hoyoverse.com",
        "Referer": "https://genshin.hoyoverse.com/",
        "Cookie": cookie,
    }
    req = urllib.request.Request(url, headers=headers, method=method,
                                 data=b"" if method == "POST" else None)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_codes(game: dict) -> dict[str, str]:
    """code -> reward description, union of all sources."""
    codes: dict[str, str] = {}
    for url, key in game["sources"]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            for item in data.get(key, []):
                code = str(item.get("code", "")).strip().upper()
                if not code:
                    continue
                rewards = item.get("rewards", "")
                if isinstance(rewards, list):
                    rewards = ", ".join(rewards)
                codes.setdefault(code, rewards or "")
        except Exception as e:  # noqa: BLE001
            print(f"[{game['name']}] 兌換碼來源失敗 {url}: {e}", file=sys.stderr)
    return codes


def get_role(game: dict, cookie: str, lang: str) -> dict | None:
    data = request("https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByCookie",
                   cookie, params={"game_biz": game["biz"], "lang": lang})
    if data.get("retcode") in COOKIE_ERRORS:
        print(f"[debug] getUserGameRolesByCookie retcode={data.get('retcode')} message={data.get('message')}")
        raise PermissionError("cookie")
    roles = (data.get("data") or {}).get("list") or []
    return roles[0] if roles else None


def key_of(game: dict) -> str:
    return next(k for k, v in GAMES.items() if v is game)


def redeem(game: dict, role: dict, code: str, cookie: str, lang: str) -> tuple[bool, str]:
    params = {
        "uid": role["game_uid"], "region": role["region"], "lang": lang,
        "cdkey": code, "game_biz": game["biz"], "sLangKey": lang,
    }
    if game["method"] == "POST" or key_of(game) == "zzz":
        params["t"] = int(time.time() * 1000)
    for attempt in range(2):
        data = request(game["redeem"], cookie, game["method"], params)
        rc = data.get("retcode")
        if rc in COOKIE_ERRORS:
            print(f"[debug] redeem retcode={rc} message={data.get('message')}")
            raise PermissionError("cookie")
        final, msg = RESULTS.get(rc, (False, f"未知結果 retcode={rc} {data.get('message')}"))
        if final or attempt:
            return final, msg
        time.sleep(COOLDOWN * 2)
    return False, msg


def notify(webhook: str, content: str) -> None:
    payload = json.dumps({"username": "HoYoLAB 兌換碼", "content": content}).encode()
    req = urllib.request.Request(webhook, data=payload, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:  # noqa: BLE001
        print(f"Discord 通知失敗: {e}", file=sys.stderr)


def load_state() -> dict:
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    # migrate old single-account layout {"gi": {...}, "hsr": {...}} -> {"main": {...}}
    if state and all(k in GAMES for k in state):
        state = {"main": state}
    return state


def redeem_cookie(suffix: str) -> str:
    """Combine the redeem cookie (cookie_token_v2 ...) with the login cookie (ltoken_v2 ...)."""
    parts = [secret("HOYOLAB_REDEEM_COOKIE", suffix), secret("HOYOLAB_COOKIE", suffix)]
    cookie = "; ".join(p.strip().rstrip(";") for p in parts if p.strip())
    return cookie if "cookie_token_v2" in cookie or "ltoken_v2" in cookie else ""


def run_account(name: str, suffix: str, games: list[str], lang: str, state: dict,
                codes_by_game: dict[str, dict[str, str]]) -> tuple[list[str], list[str], bool]:
    tag = f"[{name}] "
    notes, errors, changed = [], [], False
    cookie = redeem_cookie(suffix)
    if not cookie:
        sfx = "" if suffix == "MAIN" else "_" + suffix
        return notes, [f"❌ {tag}缺少 HOYOLAB_REDEEM_COOKIE{sfx}（需含 cookie_token_v2、account_mid_v2、account_id_v2）"], False
    acct = state.setdefault(name, {})
    for key in games:
        game = GAMES.get(key)
        if not game:
            continue
        done = acct.setdefault(key, {})
        codes = codes_by_game.setdefault(key, fetch_codes(game))
        todo = {c: r for c, r in codes.items() if c not in done}
        print(f"{tag}[{game['name']}] 來源 {len(codes)} 組，待處理 {len(todo)} 組")
        if not todo:
            continue
        try:
            role = get_role(game, cookie, lang)
            if not role:
                errors.append(f"❌ {tag}{game['name']}：此帳號沒有角色")
                continue
            for i, (code, reward) in enumerate(todo.items()):
                if i:
                    time.sleep(COOLDOWN)
                final, msg = redeem(game, role, code, cookie, lang)
                line = f"{tag}{game['name']} {code}：{msg}" + (f"（{reward}）" if reward else "")
                print(line)
                if final:
                    done[code] = msg
                    changed = True
                    if msg == "兌換成功":
                        notes.append("🎁 " + line)
                elif "未知" in msg:
                    errors.append("❓ " + line)
        except PermissionError:
            errors.append(f"❌ {tag}兌換用 cookie 失效，請更新 HOYOLAB_REDEEM_COOKIE")
            break  # same cookie for every game of this account; no point continuing
        except Exception as e:  # noqa: BLE001
            errors.append(f"❌ {tag}{game['name']}：{e}")
    return notes, errors, changed


def main() -> int:
    lang = os.environ.get("HOYOLAB_LANG", "zh-tw")
    webhook = shared("DISCORD_WEBHOOK")
    state = load_state()
    codes_by_game: dict[str, dict[str, str]] = {}
    notes, errors, changed = [], [], False

    for name, suffix, games in parse_accounts():
        n, e, c = run_account(name, suffix, games, lang, state, codes_by_game)
        notes += n
        errors += e
        changed |= c

    if changed:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    report = "\n".join(notes + errors)
    if report:
        print(report)
    if report and webhook:
        notify(webhook, report)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
