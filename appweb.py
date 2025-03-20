import os
import logging
import time
import google.generativeai as genai
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import ssl
import certifi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# SSL 設定
ssl_context = ssl.create_default_context(cafile=certifi.where())

# gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('models/gemini-2.0-flash-lite-preview-02-05')

# 初始化 Slack WebClient
slack_client = WebClient(
    token=os.environ["SLACK_BOT_TOKEN"],
    ssl=ssl_context
)

# 節流控制
MAX_REQUESTS_PER_MINUTE = 10
request_timestamps = []

def throttle_requests():
    current_time = time.time()
    global request_timestamps
    request_timestamps = [ts for ts in request_timestamps if current_time - ts < 60]
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        return True
    request_timestamps.append(current_time)
    return False

# 設定 Flask 應用程式
app = Flask(__name__)

@app.route('/list-channels', methods=['GET'])
def list_channels():
    try:
        result = slack_client.conversations_list()
        channels = result["channels"]
        channel_list = [{"id": channel["id"], "name": channel["name"]} for channel in channels]
        return jsonify(channel_list)
    except Exception as e:
        return jsonify({"error": str(e)})

# 處理所有 Slack 事件
@app.route('/', methods=['POST'])
def handle_slack_events():
    data = request.json

    # [重要]處理Slack URL驗證請求
    if data and "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # 避免處理重複事件
    if "X-Slack-Retry-Num" in request.headers and int(request.headers["X-Slack-Retry-Num"]) > 0:
        return jsonify({"status": "ok"})

    # 處理 app_mention 事件 (在頻道中被提及)
    if data and data.get("event", {}).get("type") == "app_mention":
        event = data.get("event", {})
        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "")
        
        # 解析問題文字 (移除 mention 部分)
        parts = text.split(">", 1)
        question = parts[1].strip() if len(parts) > 1 else text.strip()
        
        # 檢查是否需要節流
        if throttle_requests():
            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=f"<@{user_id}> 很抱歉，由於請求量過大，我暫時無法處理新的請求。請稍後再試。"
                )
            except SlackApiError:
                pass
            return jsonify({"status": "throttled"})
            
        try:
            # 使用 Gemini API 生成回覆
            response = model.generate_content(question)
            reply_text = response.text
            
            # 發送回覆到 Slack
            slack_client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> {reply_text}"
            )
            
        except Exception as e:
            error_message = str(e)
            custom_reply = f"<@{user_id}> 很抱歉，我目前暫時無法處理您的請求。"
            
            # 根據錯誤類型提供訊息
            if "429" in error_message or "RATE_LIMIT_EXCEEDED" in error_message:
                custom_reply += " Google API 配額已達上限，請稍後再試。"
            elif "InvalidArgument" in error_message:
                custom_reply += " 您的問題可能包含不支援的內容。請嘗試更改您的問題。"
            else:
                custom_reply += " 發生未預期的錯誤，請稍後再試。"
                
            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=custom_reply
                )
            except SlackApiError:
                pass

    # 處理私訊事件
    if data and data.get("event", {}).get("type") == "message" and data.get("event", {}).get("channel_type") == "im":
        event = data.get("event", {})
        if event.get("subtype") is None:  # 不是系統訊息
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")
            
            # 檢查是否需要節流
            if throttle_requests():
                try:
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        text="很抱歉，由於請求量過大，我暫時無法處理新的請求。請稍後再試。"
                    )
                except SlackApiError:
                    pass
                return jsonify({"status": "throttled"})
                
            try:
                response = model.generate_content(text)
                reply_text = response.text
                
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=reply_text
                )
                
            except Exception as e:
                error_message = str(e)
                custom_reply = "很抱歉，我目前暫時無法處理您的請求。"
                
                # 根據錯誤類型提供訊息
                if "429" in error_message or "RATE_LIMIT_EXCEEDED" in error_message:
                    custom_reply += " Google API 配額已達上限，請稍後再試。"
                elif "InvalidArgument" in error_message:
                    custom_reply += " 您的問題可能包含不支援的內容。請嘗試更改您的問題。"
                else:
                    custom_reply += " 發生未預期的錯誤，請稍後再試。"
                    
                try:
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        text=custom_reply
                    )
                except SlackApiError:
                    pass

    return jsonify({"status": "ok"})

# 健康檢查路由
@app.route('/', methods=['GET'])
def health_check():
    return "Your Slack Bot is running!"

@app.route('/check-config', methods=['GET'])
def check_config():
    config_status = {
        "GOOGLE_API_KEY": "已設定" if os.environ.get("GOOGLE_API_KEY") else "未設定",
        "SLACK_BOT_TOKEN": "已設定" if os.environ.get("SLACK_BOT_TOKEN") else "未設定"
    }

# 啟動應用程式
if __name__ == "__main__":
    # 檢查環境變數
    required_env_vars = ["GOOGLE_API_KEY", "SLACK_BOT_TOKEN"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"錯誤: 缺少必要的環境變數: {', '.join(missing_vars)}")
        print("請確保 .env 文件包含所有必要的環境變數")
        exit(1)
    
    port = int(os.environ.get("PORT", 3000))
    print(f"啟動應用程式於端口: {port}")
    app.run(port=port, host='0.0.0.0')