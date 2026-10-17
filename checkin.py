#!/usr/bin/env python3
"""HoYoLAB daily check-in for Genshin Impact and Honkai: Star Rail.

Env vars:
  HOYOLAB_COOKIE   required, e.g. "ltoken_v2=...; ltuid_v2=..."
  DISCORD_WEBHOOK  optional, Discord webhook URL for result notification
  GAMES            optional, comma list of gi,hsr (default: gi,hsr)
  HOYOLAB_LANG     optional, default zh-tw
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

GAMES = {
    "gi": {
        "name": "原神",
        "url": "https://sg-hk4e-api.hoyolab.com/event/sol/sign",
        "act_id": "e202102251931481",
        "signgame": "hk4e",
    },
    "hsr": {
        "name": "星穹鐵道",
        "url": "https://sg-public-api.hoyolab.com/event/luna/os/sign",
        "act_id": "e202303301540311",
        "signgame": "hkrpg",
    },
}

MESSAGES = {
    0: ("✅", "簽到成功"),
    -5003: ("✅", "今天已經簽過了"),
    -100: ("❌", "Cookie 失效，請重新登入 HoYoLAB 並更新 HOYOLAB_COOKIE"),
    -10002: ("❌", "找不到角色，這個帳號沒玩過此遊戲"),
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def sign(game: dict, cookie: str, lang: str) -> tuple[bool, str]:
    url = f"{game['url']}?lang={lang}&act_id={game['act_id']}"
    body = json.dumps({"lang": lang, "act_id": game["act_id"]}).encode()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://act.hoyolab.com",
        "Referer": "https://act.hoyolab.com/",
        "User-Agent": UA,
        "x-rpc-app_version": "2.34.1",
        "x-rpc-client_type": "4",
        "x-rpc-signgame": game["signgame"],
        "Cookie": cookie,
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, f"請求失敗: {e}"

    retcode = data.get("retcode")
    if data.get("data", {}) and data["data"].get("gt_result", {}).get("is_risk"):
        return False, "被圖形驗證（Geetest）擋下，需手動簽到一次"
    icon, text = MESSAGES.get(retcode, ("❌", f"未知錯誤 retcode={retcode} {data.get('message')}"))
    return icon == "✅", text


def _get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def today_reward(game: dict, cookie: str, lang: str) -> str:
    """Return e.g. '冒險家的經驗 ×3' for the reward claimed today, or '' on failure."""
    base = game["url"].rsplit("/", 1)[0]
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://act.hoyolab.com",
        "Referer": "https://act.hoyolab.com/",
        "User-Agent": UA,
        "x-rpc-signgame": game["signgame"],
        "Cookie": cookie,
    }
    try:
        info = _get(f"{base}/info?lang={lang}&act_id={game['act_id']}", headers)["data"]
        home = _get(f"{base}/home?lang={lang}&act_id={game['act_id']}", headers)["data"]
        day = int(info.get("total_sign_day", 0))
        award = home["awards"][day - 1] if day > 0 else None
        return f"{award['name']} ×{award['cnt']}" if award else ""
    except Exception:  # noqa: BLE001
        return ""


def notify(webhook: str, content: str) -> None:
    payload = json.dumps({"username": "HoYoLAB 自動簽到", "content": content}).encode()
    req = urllib.request.Request(
        webhook, data=payload, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:  # noqa: BLE001
        print(f"Discord 通知失敗: {e}", file=sys.stderr)


def main() -> int:
    cookie = os.environ.get("HOYOLAB_COOKIE", "").strip()
    if not cookie:
        print("缺少 HOYOLAB_COOKIE", file=sys.stderr)
        return 1
    lang = os.environ.get("HOYOLAB_LANG", "zh-tw")
    games = [g.strip() for g in os.environ.get("GAMES", "gi,hsr").split(",") if g.strip()]
    webhook = os.environ.get("DISCORD_WEBHOOK", "").strip()

    lines, ok_all = [], True
    for i, key in enumerate(games):
        game = GAMES.get(key)
        if not game:
            lines.append(f"❌ 未知遊戲代碼 {key}")
            ok_all = False
            continue
        if i:
            time.sleep(1)
        ok, text = sign(game, cookie, lang)
        ok_all &= ok
        if ok:
            reward = today_reward(game, cookie, lang)
            if reward:
                text += f"，領取 {reward}"
        lines.append(f"{'✅' if ok else '❌'} {game['name']}：{text}")

    report = "\n".join(lines)
    print(report)
    if webhook:
        notify(webhook, ("⚠️ 簽到有問題\n" if not ok_all else "") + report)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
