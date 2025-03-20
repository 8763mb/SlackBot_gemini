# SlackBot_gemini

Slack串接gemini
# Slack Gemini Bot

一個整合 Google Gemini API 的 Slack 聊天機器人，可在頻道中回應提及，並支援私訊互動。

## 功能特色

- 在 Slack 頻道中回應提及 (@機器人名稱)
- 使用免費gemini模型產生回應



## 安裝步驟

### 1. 複製專案

```bash
git clone https://github.com/your-username/slack-gemini-bot.git
cd slack-gemini-bot
```

### 2. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

建立 `.env` 檔案，並填入以下必要資訊：

```
GOOGLE_API_KEY=your-gemini-api-key
SLACK_BOT_TOKEN=your-slack-bot-token
PORT=3000
```

### 4. 設定 Slack Bot

1. 前往 [Slack API 網站](https://api.slack.com/apps) 建立新的應用程式
2. 啟用 Bot 功能，並授予以下權限（OAuth Scopes）：
   - `app_mentions:read`
   - `chat:write`
   - `im:history`
   - `im:read`
   - `im:write`
3. 啟用 Event Subscriptions 並訂閱以下事件：
   - `app_mention`
   - `message.im`

## 執行程式

```bash
python app.py
ngrok http 3000
```

應用程式將在 `http://0.0.0.0:3000` 上運行（除非在 .env 中指定其他端口）。

## API 端點

- `GET /`: 健康檢查
- `POST /`: 處理 Slack 事件
- `GET /check-config`: 檢查環境配置狀態
- `GET /test-bot`: 測試 Bot 連接狀態
- `GET /list-channels`: 列出所有 Slack 頻道

## 使用方式

### 頻道中提及

在任何已加入 Bot 的頻道中，輸入 `@你的機器人名稱 你的問題` 來取得回應。

## 故障排除

如果遇到問題，請檢查：

1. 環境變數是否正確設定
2. 使用 `/check-config` 端點檢查配置
3. 確認 Slack Bot 權限是否足夠
4. 檢查 SSL 證書是否正確
5. 使用 `/test-bot` 端點測試連接

## 限制

- 每分鐘最多處理 10 個請求（可在程式碼中調整 MAX_REQUESTS_PER_MINUTE 值）
- 受 Google Gemini API 配額限制
- 部分敏感或不支援的內容可能無法處理
