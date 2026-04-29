# Design: 自動化高鐵訂票系統（thsr-auto-book）

## 1. 技術選型理由

### 為什麼用 Puppeteer（pyppeteer）而非 Playwright 或 requests？

| 方案 | 優點 | 缺點 |
|------|------|------|
| **pyppeteer** | 生態成熟、文件充足、Linux + Xvfb 支援穩定 | 非同步 API有一點學習曲線 |
| Playwright | 官方 Python 支援、API 更乾淨 | Linux GUI 支援相對新 |
| requests | 輕量快速 | THSR 反爬強，header/cookie/session 處理複雜 |

**結論：pyppeteer 是平衡穩定性與可行性的選擇。**

---

## 2. 瀏覽器配置

### 2.1 Chrome 啟動參數

```python
chrome_options = [
    '--no-sandbox',              # Docker/Linux 必要
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',   # 記憶體問題緩解
    '--disable-gpu',
    '--headless',                # Xvfb 環境下不需要，但保留
    '--window-size=1280,900',
    '--disable-blink-features=AutomationControlled',  # 降低被偵測
]
```

### 2.2 Xvfb 整合

```bash
Xvfb :99 -screen 0 1280x900x24 &
export DISPLAY=:99
```

使用 `/home/w/.openclaw/workspace/scripts/run-puppeteer-headful-xvfb.sh` 包裝。

---

## 3. THSR 網站操作流程（DOM 操作）

### 3.1 查詢頁面（第一步）

| 動作 | DOM 策略 |
|------|---------|
| 選擇出發站 | `select#DepartCity > option[value="Taipei"]` |
| 選擇到達站 | `select#ArriveCity > option[value="Zuoying"]` |
| 行程類型 | `select#ServiceType > option[value="O"]`（單程） |
| 去程日期 | `input#DepartDate"` |
| 去程時刻 | `select#DepartTime"` |
| 車廂種類 | `select#CarType > option[value="0"]`（標準）|
| 全票張數 | `input#TicketNormal"` |
| 孩童票 | `input#TicketChild"` |
| 敬老票 | `input#TicketElderly"` |
| 愛心票 | `input#TicketLove"` |
| 大學生票 | `input#TicketCollege"` |
| 查詢按鈕 | `input[value="確認"]` |

### 3.2 班次結果頁

- 等待表格載入：`.result-table` 或 `#tbody > tr`
- 解析每一列：`td:nth-child(N)` 取得車次/時間/剩餘位
- 點選車次：`tr[data-train="302"] > td > input[type="radio"]`

### 3.3 乘客資料頁

- 身份證字號：`input#PersonId`
- 確認按鈕：`input[value="確認"]`

### 3.4 驗證碼頁面

- 驗證碼圖片：`img[alt="驗證碼"]` 或 `#SecurityCode`
- 驗證碼輸入框：`input#SecurityCode`
- 確認按鈕：`input[value="我確認"]`

### 3.5 訂票結果頁

- 取票代碼：`.ticket-no` 或 `td.ticket-number`

---

## 4. Discord 整合設計

### 4.1 發送訊息（Webhook）

使用 `requests` 發送 `POST` 到 Discord Webhook URL：

```python
def send_discord(msg: str, webhook_url: str):
    payload = {"content": msg}
    requests.post(webhook_url, json=payload)
```

### 4.2 接收驗證碼回覆

由於 Webhook 是單向的，驗證碼回覆採用 **訊息擷取** 機制：

- 系統在 Discord 發送「🔐 請輸入驗證碼」
- 使用者回覆在同一頻道（可thread 或直接回）
- 系統使用 Discord Bot Token + Channel History API 取得最新回覆
-  polling頻率：每秒檢查一次，最多等待 300 秒（5 分鐘）

```python
async def wait_for_captcha_response(channel_id: str, bot_token: str, timeout: int = 300):
    start = time.time()
    while time.time() - start < timeout:
        messages = await fetch_last_messages(channel_id, bot_token, limit=5)
        for msg in messages:
            if is_valid_captcha(msg.content):
                return msg.content
        await asyncio.sleep(1)
    raise TimeoutError("驗證碼輸入逾時")
```

### 4.3 Discord 訊息格式

```
=== 班次清單 ===
🚄 可用班次

`1.` [07:30] 302 | 台北 → 左營 | 標準車廂 | 剩餘 25 位 | NT$1490
`2.` [07:45] 1212 | 台北 → 左營 | 標準車廂 | 剩餘 12 位 | NT$1490

請回覆數字選擇車次，或輸入「監控」自動監控
---

=== 驗證碼 ===
🔐 請輸入驗證碼（請回覆在同一頻道）

---

=== 成功 ===
✅ 訂票成功！
車次：302 | 07:30 → 09:00
取票代碼：`ABC123`
```

---

## 5. 監控邏輯

```python
async def monitor_and_book(config: QueryConfig, selected_train: Train):
    while True:
        trains = await search_trains(config)
        target = find_train(trains, selected_train.number)
        
        if target and target.available > 0:
            await book_train(target, config)
            return True
        
        # 發送監控更新
        send_discord(f"🔄 {target.number} 無位，30秒後重試...")
        await asyncio.sleep(30)
```

---

## 6. 目錄結構

```
thsr-auto-book/
├── main.py
├── config.py
├── browser.py
├── search.py
├── book.py
├── monitor.py
├── discord_client.py
├── exceptions.py
├── .env.example
├── requirements.txt
├── README.md
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_search.py
    └── test_book.py
```

---

## 7. 環境變數

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
DISCORD_BOT_TOKEN=xxxxxxxxxxxxxxxxxxxxx
DISCORD_CHANNEL_ID=1498705594196951060
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 8. 錯誤應對策略

| 情境 | 策略 |
|------|------|
| 瀏�器崩潰 | 重啟瀏覽器，重試當前步驟（最多3次）|
| 網站 DOM 變動 | 截圖保存現場，拋例外並通知用戶 |
| 驗證碼逾時 | 停止監控，通知用戶手動處理 |
| Anti-bot 驗證 | 通知用戶，可能需換 IP 或等待後再試 |
| 網站無回應 | 等待 10 秒無回應則重試 |
