"""認証システム - パスワード認証とセッション管理"""
from functools import wraps
from flask import session, redirect, url_for, flash
from database import get_setting, update_setting, check_password, hash_password

def require_auth(f):
    """設定画面アクセスに認証を要求するデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            flash('設定画面にアクセスするにはパスワードが必要です', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def verify_password(password):
    """パスワードを検証"""
    stored_hash = get_setting('admin_password_hash')
    if not stored_hash:
        print("❌ パスワードハッシュが設定されていません")
        return False
    return check_password(password, stored_hash)

def login_user(password):
    """ユーザーをログイン"""
    if verify_password(password):
        session['authenticated'] = True
        session.permanent = True  # セッションを永続化
        return True, "ログインしました"
    return False, "パスワードが正しくありません"

def logout_user():
    """ユーザーをログアウト"""
    session.pop('authenticated', None)

def change_password(current_password, new_password):
    """パスワードを変更"""
    if not verify_password(current_password):
        return False, "現在のパスワードが正しくありません"

    if len(new_password) < 4:
        return False, "新しいパスワードは4文字以上にしてください"

    new_hash = hash_password(new_password)
    update_setting('admin_password_hash', new_hash)
    return True, "パスワードを変更しました"

def is_authenticated():
    """現在認証されているかチェック"""
    return session.get('authenticated', False)
