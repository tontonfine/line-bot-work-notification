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

    # セキュアなパスワードポリシー
    if len(new_password) < 12:
        return False, "新しいパスワードは12文字以上にしてください"

    # 推奨: 英数字と記号を含む複雑さチェック
    has_upper = any(c.isupper() for c in new_password)
    has_lower = any(c.islower() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)

    if not (has_upper and has_lower and has_digit):
        return False, "パスワードは大文字、小文字、数字を含む必要があります"

    new_hash = hash_password(new_password)
    update_setting('admin_password_hash', new_hash)
    return True, "パスワードを変更しました"

def is_authenticated():
    """現在認証されているかチェック"""
    return session.get('authenticated', False)
