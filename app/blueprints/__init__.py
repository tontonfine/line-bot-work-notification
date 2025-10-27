"""Blueprint registration"""

def register_blueprints(app):
    """全Blueprintをアプリケーションに登録"""
    from .main import main_bp
    from .send import send_bp
    from .auth import auth_bp
    from .employees import employees_bp
    from .settings import settings_bp
    from .api import api_bp
    from .webhook import webhook_bp
    from .test import test_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(send_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(test_bp)
