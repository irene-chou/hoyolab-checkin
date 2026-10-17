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
