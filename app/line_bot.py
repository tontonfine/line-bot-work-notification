"""LINE Bot API initialization"""
from linebot import LineBotApi, WebhookHandler
import os
import logging

# グローバル変数（初期化後に設定）
line_bot_api = None
handler = None
LIFF_ID = None

logger = logging.getLogger(__name__)

def check_environment_variables():
    """必須環境変数の存在をチェック"""
    required_vars = {
        'LINE_CHANNEL_ACCESS_TOKEN': 'LINE Channel Access Token',
        'LINE_CHANNEL_SECRET': 'LINE Channel Secret',
        'LIFF_ID': 'LIFF ID'
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var} ({description})")

    if missing_vars:
        print("❌ 必須環境変数が設定されていません:")
        print("\n".join(missing_vars))
        print("\n.envファイルを確認してください。")
        return False

    print("✅ 環境変数チェック完了")
    return True

def init_line_bot():
    """LINE Bot APIを初期化"""
    global line_bot_api, handler, LIFF_ID

    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    LIFF_ID = os.getenv('LIFF_ID')

    # 環境変数チェック
    if not check_environment_variables():
        logger.warning("⚠️ 警告: 環境変数が不足していますが、アプリケーションを起動します")
        logger.warning("LINE機能は正常に動作しない可能性があります\n")

    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)

    logger.info("✅ LINE Bot API初期化完了")
