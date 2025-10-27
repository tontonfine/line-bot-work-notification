"""Authentication routes blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import login_user, login_basic_user, login_admin_user, logout_user
from app.extensions import limiter
import logging

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """ログイン画面"""
    if request.method == 'POST':
        password = request.form.get('password')
        success, message = login_user(password)

        if success:
            flash(message, 'success')
            logging.info(f"Successful login from {request.remote_addr}")
            return redirect(url_for('settings.settings'))
        else:
            flash(message, 'error')
            logging.warning(f"Failed login attempt from {request.remote_addr}")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """ログアウト（全セッションクリア）"""
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('auth.basic_login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def basic_login():
    """基本ログイン（トップページアクセス用）"""
    if request.method == 'POST':
        password = request.form.get('password')
        success, message = login_basic_user(password)

        if success:
            logging.info(f"Successful basic login from {request.remote_addr}")
            return redirect(url_for('main.index'))
        else:
            flash(message, 'error')
            logging.warning(f"Failed basic login from {request.remote_addr}")

    return render_template('basic_login.html')

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def admin_login():
    """管理者ログイン（従業員管理・設定アクセス用）"""
    if request.method == 'POST':
        password = request.form.get('password')
        success, message = login_admin_user(password)

        if success:
            logging.info(f"Successful admin login from {request.remote_addr}")
            return redirect(url_for('employees.employees_list'))
        else:
            flash(message, 'error')
            logging.warning(f"Failed admin login from {request.remote_addr}")

    return render_template('admin_login.html')

@auth_bp.route('/employees/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def employee_login():
    """従業員管理ログイン（後方互換性）"""
    return redirect(url_for('auth.admin_login'))

@auth_bp.route('/employees/logout')
def employee_logout():
    """従業員管理ログアウト（後方互換性のため残す）"""
    return redirect(url_for('auth.logout'))
