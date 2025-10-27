"""Flask application factory"""
from flask import Flask
from datetime import timedelta
import os
import logging

def create_app():
    """アプリケーションファクトリー"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('security.log'),
            logging.StreamHandler()
        ]
    )

    # SECRET_KEY必須化
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError(
            "❌ CRITICAL: SECRET_KEY environment variable must be set!\n"
            "   Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'\n"
            "   Then add to .env: SECRET_KEY=<generated_key>"
        )

    # Flask設定
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

    # セキュアなセッション設定
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS必須
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # JavaScriptからアクセス不可
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF対策

    # 拡張機能初期化（CSRF, Limiter, Talisman）
    from app.extensions import init_extensions
    init_extensions(app)

    # LINE Bot初期化
    from app.line_bot import init_line_bot
    init_line_bot()

    # データベース初期化
    from database import init_db, migrate_database
    init_db()
    migrate_database()

    # スケジューラー初期化
    import scheduler
    scheduler.setup_scheduler()
    print("✅ スケジューラーセットアップ完了")

    # Blueprint登録
    from app.blueprints import register_blueprints
    register_blueprints(app)

    return app
