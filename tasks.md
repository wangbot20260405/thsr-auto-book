# Tasks: 自動化高鐵訂票系統（thsr-auto-book）

> 交付給 Codex CLI 實作。實作前請先閱讀 `proposal.md`、`specs/spec.md`、`design.md`。

---

## Task 1：專案初始化

- [ ] 建立 `thsr-auto-book/` 目錄結構
- [ ] 建立 `requirements.txt`
- [ ] 建立 `.env.example`
- [ ] 建立 `README.md`（含使用說明）
- [ ] 建立 `tests/` 目錄與基本 `__init__.py`
- [ ] 初始化 git（`main` branch）
- [ ] 建立 `.gitignore`

**檔案：**
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
├── .gitignore
├── requirements.txt
├── README.md
└── tests/
    ├── __init__.py
    ├── test_config.py
    └── test_search.py
```

---

## Task 2：config.py — 資料結構

- [ ] 建立 `QueryConfig` dataclass（含所有查詢欄位）
- [ ] 建立 `Train` dataclass（含車次資訊）
- [ ] 建立 `BookingResult` dataclass（含訂票結果）
- [ ] 實作基本驗證（如：日期格式、張數總和大於 0）
- [ ] 實作 `.env` 讀取（`python-dotenv`）
- [ ] 寫 `tests/test_config.py`

---

## Task 3：browser.py — 瀏覽器管理

- [ ] 實作 `BrowserManager` class
  - [ ] `launch()`：啟動 Chrome（含 Linux 必要參數）
  - [ ] `new_page()`：開新分頁
  - [ ] `close()`：關閉瀏覽器
- [ ] 實作 `catch_exception` decorator（用於包裝任何頁面操作，失敗時截圖）
- [ ] 整合 Xvfb 環境變數設定
- [ ] 測試：可在 Linux 環境成功啟動 Chrome 並開啟空白頁

---

## Task 4：search.py — 班次查詢

- [ ] 實作 `THSRSearcher` class
  - [ ] `navigate_to_search()`：開啟 THSR 查詢頁
  - [ ] `fill_form(config: QueryConfig)`：填入查詢表單
  - [ ] `submit()`：點擊查詢
  - [ ] `parse_results()`：解析班次結果，回傳 `List[Train]`
- [ ] 實作 `select_train(train: Train)`：點選指定車次
- [ ] 錯誤處理：DOM 找不到時截圖並拋例外
- [ ] 寫 `tests/test_search.py`（mock 資料）

---

## Task 5：book.py — 訂票流程

- [ ] 實作 `THSRBooker` class
  - [ ] `fill_passenger(pid: str)`：填入乘客資料
  - [ ] `check_captcha()`：判斷是否出現驗證碼
  - [ ] `wait_for_captcha_response()`：等待 Discord 回覆（polling channel history）
  - [ ] `submit_booking()`：送出訂票
  - [ ] `parse_result()`：解析結果頁，取「取票代碼」
- [ ] 整合 `discord_client.py` 的驗證碼等待機制
- [ ] 錯誤處理：訂票失敗時截圖

---

## Task 6：discord_client.py — Discord 整合

- [ ] 實作 `send_message(content: str, webhook_url: str)`
- [ ] 實作 `wait_for_captcha_response(channel_id: str, bot_token: str, timeout: int = 300) -> str`
  - 使用 Discord REST API（`channels/{id}/messages`）polling
  - 每秒一次，最多 timeout 秒
  - 只取驗證碼格式（4-6 碼數字）的最新訊息
- [ ] 實作 `send_train_list(trains: List[Train], webhook_url: str)`
- [ ] 實作 `send_booking_result(result: BookingResult, webhook_url: str)`

---

## Task 7：monitor.py — 自動監控

- [ ] 實作 `monitor_loop(config: QueryConfig, selected_train: Train, interval: int = 30)`
  - 每隔 `interval` 秒查詢一次
  - 比對目標車次是否有位
  - 有位時呼叫 `book.py` 完成訂票
  - 每次查詢發送 Discord 狀態更新
- [ ] 實作 `cancel_monitor()`（支援 Ctrl+C 中斷）
- [ ] 整合 AsyncIO

---

## Task 8：main.py — 整合與 CLI 入口

- [ ] CLI 互動：使用 `input()` 或 `questionary` 收集使用者輸入
- [ ] 整合所有模組：`BrowserManager` → `THSRSearcher` → `monitor.py` → `THSRBooker`
- [ ] 整合 Discord 通知（班次清單、驗證碼請求、訂票結果）
- [ ] 實作 `graceful_shutdown()`（Ctrl+C 時關閉瀏覽器）
- [ ] 主流程：
  ```
  收集輸入 → 查詢班次 → 發送 Discord 清單 → 等待選擇
  → 有位：訂票 → 通知結果
  → 無位：監控 30 秒 → 有位時自動訂 → 通知結果
  ```

---

## Task 9：GitHub 整合

- [ ] 使用 `GITHUB_TOKEN`（Personal Access Token）建立 GitHub repo
  - API：`POST /user/repos`，body `{"name": "thsr-auto-book", "private": false}`
- [ ] 設定 remote：`git remote add origin https://<token>@github.com/<user>/thsr-auto-book.git`
- [ ] 第一次 commit 與 push

---

## Task 10：文件與測試

- [ ] 補完 `README.md`（含安裝流程、.env 設定範例、使用截圖說明）
- [ ] 確認所有模組有基本單元測試
- [ ] 確認程式可在 Linux 環境從頭跑到底（end-to-end smoke test）

---

## Task 依賴關係

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5
                 ↓
              Task 6 → Task 7 → Task 8
                                   ↓
                                Task 9 → Task 10
```

---

## 驗收標準（每個 Task 需滿足）

1. 程式碼可運行，無 syntax / import error
2. 每個模組有基本單元測試
3. 失敗時有明確錯誤訊息（非靜默）
4. 重要流程有 log 輸出到終端機
5. 交接文件足夠（註解 / docstring）
