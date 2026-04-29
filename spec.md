# Spec: 自動化高鐵訂票系統（thsr-auto-book）

## 1. 專案概覽

| 項目 | 內容 |
|------|------|
| 專案名稱 | thsr-auto-book |
| 語言 | Python 3 |
| 功能 | 高鐵班次查詢、座位監控、自動化訂票 |
| 觸發方式 | CLI 手動執行 |
| 通知方式 | Discord Webhook |

---

## 2. 功能需求

### 2.1 CLI 輸入介面

腳本 `main.py` 執行時，依序詢問以下資訊：

```
出發站: 
到達站: 
出發日期 (YYYY/MM/DD): 
出發時間 (HH:MM): 
車廂種類 (standard/business): 
票種與張數:
  - 全票: N
  - 孩童票: N
  - 敬老票: N
  - 愛心票: N
  - 大學生票: N
乘客身分證字號: 
Discord Webhook URL (可直接 Enter 使用預設):
```

### 2.2 班次查詢

- 使用 pyppeteer 控制瀏覽器（Headful Chrome + Xvfb）
- 開啟 THSR 官方訂票網站
- 自動填入第一頁「查詢行程」表單
- 點擊查詢，等待班次結果頁載入

### 2.3 班次選擇清單（Discord 通知）

系統解析班次結果後，發送一條 Discord 訊息：

```
🚄 可用班次（篩選後）

1. [07:30] 302 | 標準車廂 剩餘：25
2. [07:45] 1212 | 標準車廂 剩餘：12
3. [08:00] 308 | 標準車廂 剩餘：0 ❌

請回覆數字選擇車次，或輸入「監控」啟動自動監控
```

### 2.4 自動監控模式

當選擇的車次無位時：
- 每 **30 秒**自動重新查詢
- 有位時自動進入訂票流程
- 每次重查在 Discord 發送監控狀態（如：「🔄 [08:00] 308 無位，30秒後重試...」）
- 有位時自動鎖定班次，發送「✅ 有位！正在訂票...」

### 2.5 訂票流程

選定車次後：
1. 點選該車次
2. 填入乘客資料（身份證字號）
3. 若出現驗證碼頁面：
   - 發送 Discord 訊息：「🔐 請輸入驗證碼（Discord 回覆）」
   - **等待** 使用者在 Discord 輸入驗證碼
   - 收到後自動填入並繼續
4. 送出訂票
5. 取得訂位代碼

### 2.6 結果通知（Discord）

**成功時：**
```
✅ 訂票成功！
車次：308 | 07:30 → 09:00
座位：標準車廂對號座
取票代碼：ABC123
金額：NT$1490
請於取票期限前完成付款取票
```

**失敗時：**
```
❌ 訂票失敗
原因：[錯誤說明]
請自行至高鐵網站處理
```

---

## 3. 資料結構

### 3.1 查詢條件（QueryConfig）

```python
@dataclass
class QueryConfig:
    depart: str          # 出發站
    arrive: str          # 到達站
    date: str            # 日期 YYYY/MM/DD
    time: str            # 時間 HH:MM
    cabin: str           # standard / business
    adult: int = 0       # 全票張數
    child: int = 0       # 孩童票張數
    senior: int = 0      # 敬老票張數
    love: int = 0        # 愛心票張數
    college: int = 0    # 大學生票張數
    pid: str             # 乘客身份證字號
    webhook_url: str     # Discord Webhook URL
```

### 3.2 班次（Train）

```python
@dataclass
class Train:
    number: str          # 車次代碼，如 "302"
    depart_time: str     # 出發時間 "07:30"
    arrive_time: str     # 到達時間 "09:00"
    duration: str        # 行車時間 "1h30m"
    cabin: str           # 車廂種類
    available: int       # 剩餘座位數
    price: int           # 價格
```

---

## 4. 模組架構

```
thsr-auto-book/
├── main.py              # 程式入口，CLI 互動
├── config.py            # QueryConfig 資料結構與驗證
├── browser.py           # pyppeteer 瀏覽器管理（啟動/關閉/截圖）
├── search.py            # 查詢流程（填表/送出/解析結果）
├── book.py              # 訂票流程（選車次/填乘客/驗證碼/送出）
├── monitor.py           # 監控邏輯（30秒輪詢）
├── discord_bot.py       # Discord Webhook 發送/接收（驗證碼回覆）
├── exceptions.py        # 自訂例外
├── requirements.txt      # 依賴
├── .env.example         # 環境變數範例（PAT、webhook）
├── README.md            # 使用說明
└── tests/               # 測試目錄
```

---

## 5. 外部依賴

```
pyppeteer       # 瀏覽器自動化
python-dotenv   # 環境變數
requests        # Discord Webhook
```

---

## 6. 驗證碼處理流程

```
1. 系統偵測到驗證碼頁面
2. 截圖驗證碼區域
3. 發送到 Discord：「🔐 請輸入驗證碼」
4. 等待使用者回覆（poll Discord webhook 或使用現成訊息回覆機制）
5. 收到驗證碼後填入表單
6. 繼續訂票流程
```

---

## 7. 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| 網站載入失敗 | 重試 3 次，間隔 5 秒，仍失敗則放棄 |
| 驗證碼解析失敗 | 通知用戶人工輸入 |
| 訂票失敗（無座位）| 回傳「無座位」，進入監控模式 |
| 網站 Anti-bot 偵測 | 通知用戶，可能需要更換 IP 或 Proxy |
| 系統例外 | 發送錯誤至 Discord，終止程式 |

---

## 8. GitHub 整合

- 建立新 repo：`https://github.com/<username>/thsr-auto-book`
- 使用 Personal Access Token（`GITHUB_TOKEN` 環境變數）推送
- 初始化 git，預設 branch：`main`
- 第一次 commit 包含完整專案結構

---

## 9. 使用流程

```
1. 安裝依賴：pip install -r requirements.txt
2. 設定 .env（GitHub PAT、Discord Webhook）
3. 執行：python main.py
4. 依序輸入查詢條件
5. 在 Discord 選擇車次
6. 若需驗證碼，在 Discord 輸入
7. 收到結果通知
```
