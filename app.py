"""Flask application entry point"""
from dotenv import load_dotenv
import os

# 環境変数読み込み
load_dotenv()

# アプリケーション作成
from app import create_app
app = create_app()

if __name__ == '__main__':
    print("🚀 アプリケーションを起動します...")
    print(f"📍 http://127.0.0.1:5001 でアクセスできます")

    # デバッグモードは開発環境のみ
    DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    if DEBUG_MODE:
        print("⚠️  WARNING: デバッグモードで起動中（本番環境では無効化してください）")

    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=5001)
