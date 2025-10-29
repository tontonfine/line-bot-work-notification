import pytest
import tempfile
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app
from database import init_db

@pytest.fixture
def app():
    """テスト用のFlaskアプリ"""
    db_fd, db_path = tempfile.mkstemp()

    flask_app.config['TESTING'] = True
    flask_app.config['DATABASE'] = db_path

    with flask_app.app_context():
        init_db()

    yield flask_app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLIランナー"""
    return app.test_cli_runner()
