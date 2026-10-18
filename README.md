# hoyolab-checkin

每天 07:10（台灣時間）透過 GitHub Actions 自動在 HoYoLAB 簽到原神、星穹鐵道，並把結果推到 Discord。

## 設定

GitHub Secrets：

| 名稱 | 內容 |
|---|---|
| `HOYOLAB_COOKIE` | `ltoken_v2=...; ltuid_v2=...` |
| `DISCORD_WEBHOOK` | Discord 頻道的 webhook URL（可省略） |

取 cookie：登入 https://www.hoyolab.com → DevTools → Application → Cookies → `https://www.hoyolab.com` → 複製 `ltoken_v2` 與 `ltuid_v2` 的值。

## 手動執行

```sh
gh workflow run checkin.yml && sleep 20 && gh run list --limit 1
```

或本機：

```sh
HOYOLAB_COOKIE='ltoken_v2=...; ltuid_v2=...' python3 checkin.py
```

## 常見狀況

- `Cookie 失效`：重新登入 HoYoLAB 取新 cookie，`gh secret set HOYOLAB_COOKIE`。
- `被圖形驗證擋下`：到 HoYoLAB 網頁手動簽到一次，通常之後就恢復。

## 自動兌換碼

`redeem.py` 每 6 小時從社群維護的兌換碼清單（seria.moe、ennead.cc）抓原神與星穹鐵道的有效碼並自動兌換，已處理過的碼記在 `redeemed.json`，只有「兌換成功」或錯誤才會推 Discord。

需要另一個 Secret `HOYOLAB_REDEEM_COOKIE`，內容是同一個 HoYoLAB 登入的三個 cookie：

```
cookie_token_v2=...; account_mid_v2=...; account_id_v2=...
```

手動執行：`gh workflow run redeem.yml`

## 多帳號

帳號清單放 repo variable `ACCOUNTS`，格式 `名稱:遊戲;名稱:遊戲`，例如：

```
gh variable set ACCOUNTS -b 'main:gi,hsr;alt:hsr'
```

`main` 用無後綴的 secret（`HOYOLAB_COOKIE`、`HOYOLAB_REDEEM_COOKIE`），其他帳號用大寫名稱當後綴：

```
gh secret set HOYOLAB_COOKIE_ALT -b 'ltoken_v2=...; ltuid_v2=...'
gh secret set HOYOLAB_REDEEM_COOKIE_ALT -b 'cookie_token_v2=...; account_mid_v2=...; account_id_v2=...'
```

新帳號的 secret 名稱也要加進 `.github/workflows/checkin.yml` 與 `redeem.yml` 的 `env` 區塊（GitHub 不允許一次傳入全部 secrets）。通知合併在同一則 Discord 訊息，以帳號名稱分段。
