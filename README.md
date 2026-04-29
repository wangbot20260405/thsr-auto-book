# THSR Auto-Book 自動化高鐵訂票系統

使用 Playwright + HTTP hybrid 架構，結合 CNN 驗證碼辨識與 Discord 通知，自動化高鐵訂票流程。

## 功能

- ✅ 班次查詢（起訖站/日期/時段）
- ✅ 自動監控指定車次（30 秒輪詢）
- ✅ CNN 驗證碼自動辨識（~76% 準確率）
- ✅ Discord Webhook 整合（班次清單/驗證碼請求/訂票結果）
- ✅ 驗證碼失敗時自動切換 Discord 人工輸入
- ✅ 支援全票/孩童票/敬老票/愛心票/大學生票
- ✅ 滑鼠點擊操作，模擬人類行為（降低被偵測風險）

## 架構

```
Browser (Playwright)     HTTP (requests)
┌─────────────────┐      ┌──────────────────┐
│ 處理 Cloudflare │ ──→  │ 填表/送表單       │
│ 填表/點擊       │      │ 解析回應         │
│ 截圖存證        │      │ 高效能            │
└────────┬────────┘      └────────┬─────────┘
         │                        │
         └─────── cookies ────────┘
                   │
           ┌───────▼───────┐
           │  CNN Captcha  │
           │  (76% 成功率) │
           └───────────────┘
                   │
           ┌───────▼───────┐
           │   Discord     │
           │ Webhook 通知  │
           └───────────────┘
```

## 安裝

```bash
git clone https://github.com/wangbot20260405/thsr-auto-book.git
cd thsr-auto-book
pip install -r requirements.txt
```

## 設定

複製 `.env.example` 為 `.env`，填入：

```bash
# Discord Bot（可选，用于驗證碼 polling）
DISCORD_BOT_TOKEN=

# Discord Webhook（必填，用於發送通知）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# 頻道 ID
DISCORD_CHANNEL_ID=1498705594196951060

# GitHub（可選）
GITHUB_TOKEN=
```

## 使用

```bash
python main.py
```

依序輸入：
1. 出發站 / 到達站
2. 出發日期（YYYY/MM/DD）
3. 出發時段
4. 車廂種類
5. 全票張數
6. 乘客身分證字號
7. 手機號碼

系統會：
1. 查詢可用班次 → 發送至 Discord
2. 選擇車次後，嘗試 CNN 自動解驗證碼
3. CNN 失敗時，發送驗證碼圖至 Discord 等候人工輸入
4. 訂票成功後發送結果

### 自動監控模式

輸入班次編號後，輸入「監控」即可啟動自動監控：
- 每 30 秒重新查詢
- 有位時自動完成訂票
- 全程 Discord 通知進度

## 目錄結構

```
thsr-auto-book/
├── main.py              # CLI 入口
├── config.py            # 資料結構與驗證
├── browser.py           # Playwright 瀏覽器管理
├── search.py            # 班次查詢
├── book.py              # 訂票流程
├── monitor.py           # 座位監控
├── discord_client.py     # Discord Webhook
├── exceptions.py         # 例外階層
├── requirements.txt
├── .env.example
├── .gitignore
└── tests/
    └── test_config.py
```

## 驗證碼系統

驗證碼模組來自 `thsr_tools/captcha.py`，使用 EfficientNet-B0 Transfer Learning 模型：

| 模型 | 訓練資料 | 準確率 |
|------|---------|--------|
| `thsr_captcha_transfer.pth` | 21 張已標記 | 76.2% |

CNN 失敗時自動降級到 Discord 人工輸入。

## 環境需求

- Python 3.10+
- Playwright（`playwright install chromium`）— 必要
- Xvfb（Linux headless 環境）
- 網路連線（須能連線到 `irs.thsrc.com.tw`）

### 依賴衝突警告

`playwright` 與 `pyppeteer` 有相依衝突（`pyee` 版本衝突）。兩者共存時可能需要在不同 virtualenv 分離。

### 網站存取限制

某些網路環境（例如高鐵站或企業內網）可能無法直接連線到 `irs.thsrc.com.tw`。若有 Cloudflare 挑戰，系統會等待最多 60 秒再視為逾時。

## 已知限制

- 驗證碼 CNN 模型目前 76% 準確率，建議同步設定 Discord Bot 以備人工輸入
- 網站 anti-bot 偵測可能造成 30-60 秒的額外等待
- 本工具僅供研究與個人自動化需求，請勿干擾高鐵官方服務

## 維護紀錄

- 2026-04-29：初始實作，完成 Tasks 2-10，pip 安裝完成，Playwright Chromium 已下載，單元測試全部通過（8/8）
- 安裝後依賴衝突：`playwright` 升級到 1.58.0 取代 `pyppeteer` 的舊版 `pyee`
- 驗證碼模型：`thsr_captcha_transfer.pth`（17MB，EfficientNet-B0 Transfer Learning，76.2% 準確率）
- THC 網站直接瀏覽器存取的網路穩定性待驗證（集團網路可能有限制）

## 注意事項

- 本工具僅供研究與個人自動化需求
- 請勿用於商業用途或干擾高鐵官方服務
- 取票後需自行完成付款