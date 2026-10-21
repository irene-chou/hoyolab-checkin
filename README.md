# hoyolab-checkin

每天 00:10（台灣時間）透過 GitHub Actions 自動在 HoYoLAB 簽到原神、星穹鐵道，並把結果推到 Discord。

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

需要另一個 Secret `HOYOLAB_REDEEM_COOKIE`，內容至少要有 `cookie_token_v2`（`account_mid_v2`、`account_id_v2` 可一併附上，缺少時會從 `HOYOLAB_COOKIE` 補）：

```
cookie_token_v2=...
```

取法：開 https://genshin.hoyoverse.com/gift 登入 → DevTools → Application → Cookies → `https://genshin.hoyoverse.com` → 複製 `cookie_token_v2`。
注意：在 hoyolab.com 重新登入只會換 `ltoken_v2`，不會換發 `cookie_token_v2`；舊值失效時務必從兌換頁重新登入取得。
在同一瀏覽器切換登入另一個帳號會讓前一個帳號的 token 失效，操作第二個帳號請用無痕視窗。

手動執行：`gh workflow run redeem.yml`

## 多帳號

帳號清單放 repo variable `ACCOUNTS`，格式 `名稱@SECRET後綴:遊戲;...`（遊戲代碼：`gi` 原神、`hsr` 星穹鐵道、`zzz` 絕區零），例如：

```
gh variable set ACCOUNTS -b 'player1@MAIN:gi,hsr;player2@ALT:gi,zzz'
```

名稱只用於通知顯示與 `redeemed.json`。`@` 後面是 secret 後綴，省略時等於名稱大寫；後綴 `MAIN` 代表無後綴的 secret（`HOYOLAB_COOKIE`、`HOYOLAB_REDEEM_COOKIE`），其他後綴直接接在 secret 名稱後：

```
gh secret set HOYOLAB_COOKIE_ALT -b 'ltoken_v2=...; ltuid_v2=...'
gh secret set HOYOLAB_REDEEM_COOKIE_ALT -b 'cookie_token_v2=...; account_mid_v2=...; account_id_v2=...'
```

新帳號的 secret 名稱也要加進 `.github/workflows/checkin.yml` 與 `redeem.yml` 的 `env` 區塊（GitHub 不允許一次傳入全部 secrets）。通知合併在同一則 Discord 訊息，以帳號名稱分段。
