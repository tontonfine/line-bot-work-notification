"""認証システム - 2段階パスワード認証とセッション管理"""
from functools import wraps
from flask import session, redirect, url_for, flash
from database import get_setting, update_setting, check_password, hash_password

def require_basic_auth(f):
    """基本アクセス（トップページ）に認証を要求するデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 管理者権限がある場合は基本権限も自動的に付与
        if not (session.get('basic_authenticated') or session.get('admin_authenticated')):
            flash('このページにアクセスするにはログインが必要です', 'warning')
            return redirect(url_for('auth.basic_login'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin_auth(f):
    """管理者アクセス（従業員管理・設定）に認証を要求するデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            flash('このページにアクセスするには管理者権限が必要です', 'warning')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# 後方互換性のため残す
def require_auth(f):
    """設定画面アクセスに認証を要求するデコレーター（後方互換性）"""
    return require_admin_auth(f)

def verify_basic_password(password):
    """基本パスワード（トップページアクセス用）を検証"""
    stored_hash = get_setting('admin_password_hash')
    if not stored_hash:
        print("❌ 基本パスワードハッシュが設定されていません")
        return False
    return check_password(password, stored_hash)

def verify_admin_password(password):
    """管理者パスワード（従業員管理・設定アクセス用）を検証"""
    stored_hash = get_setting('employee_mgmt_password_hash')
    if not stored_hash:
        print("❌ 管理者パスワードハッシュが設定されていません")
        return False
    return check_password(password, stored_hash)

def login_basic_user(password):
    """基本ユーザーとしてログイン（トップページアクセス権）"""
    if verify_basic_password(password):
        session['basic_authenticated'] = True
        session.permanent = True  # セッションを永続化
        return True, "ログインしました"
    return False, "パスワードが正しくありません"

def login_admin_user(password):
    """管理者としてログイン（従業員管理・設定アクセス権）"""
    if verify_admin_password(password):
        session['admin_authenticated'] = True
        session['basic_authenticated'] = True  # 管理者は基本権限も持つ
        session.permanent = True  # セッションを永続化
        return True, "管理者としてログインしました"
    return False, "パスワードが正しくありません"

# 後方互換性のため残す
def verify_password(password):
    """パスワードを検証（後方互換性）"""
    return verify_basic_password(password)

def login_user(password):
    """ユーザーをログイン（後方互換性）"""
    return login_basic_user(password)

def logout_user():
    """ユーザーをログアウト（全セッションをクリア）"""
    session.pop('basic_authenticated', None)
    session.pop('admin_authenticated', None)
    session.pop('authenticated', None)  # 旧セッションもクリア

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
