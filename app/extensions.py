"""Flask extensions initialization"""
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# グローバルインスタンス（初期化前）
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def init_extensions(app):
    """Flask拡張機能を初期化"""
    import os

    # CSRF保護
    csrf.init_app(app)

    # レート制限
    limiter.init_app(app)

    # セキュリティヘッダー（本番環境のみ）
    IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
    if IS_PRODUCTION:
        Talisman(app, content_security_policy={
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://static.line-scdn.net"],
            'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
            'img-src': ["'self'", "data:", "https:"],
            'connect-src': ["'self'", "https://api.line.me", "https://access.line.me", "https://liffsdk.line-scdn.net"],
        })
