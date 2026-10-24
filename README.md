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

## 兌換碼通知

`codes.py` 每 6 小時從社群維護的兌換碼清單（ennead.cc、seria.moe）抓 `ACCOUNTS` 裡有的遊戲的有效碼，發現新碼就推 Discord，附獎勵內容與官方兌換頁連結（點開連結後登入即可兌換）。已通知過的碼記在 `codes.json`，由 workflow 自動 commit。

不需要任何 HoYoLAB cookie。原本的自動兌換因為兌換用的 `cookie_token_v2` 幾天就失效、且國際服沒有不需帳密登入的續期方式而移除。

手動執行：`gh workflow run codes.yml`

## 多帳號

帳號清單放 repo variable `ACCOUNTS`，格式 `名稱@SECRET後綴:遊戲;...`（遊戲代碼：`gi` 原神、`hsr` 星穹鐵道、`zzz` 絕區零），例如：

```
gh variable set ACCOUNTS -b 'player1@MAIN:gi,hsr;player2@ALT:gi,zzz'
```

名稱只用於簽到通知顯示。`@` 後面是 secret 後綴，省略時等於名稱大寫；後綴 `MAIN` 代表無後綴的 secret（`HOYOLAB_COOKIE`），其他後綴直接接在 secret 名稱後：

```
gh secret set HOYOLAB_COOKIE_ALT -b 'ltoken_v2=...; ltuid_v2=...'
```

新帳號的 secret 名稱也要加進 `.github/workflows/checkin.yml` 的 `env` 區塊（GitHub 不允許一次傳入全部 secrets）。簽到通知合併在同一則 Discord 訊息，以帳號名稱分段；兌換碼通知以遊戲分段，不分帳號。
