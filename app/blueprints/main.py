"""Main routes blueprint"""
from flask import Blueprint, render_template
from auth import require_basic_auth
from app.line_bot import LIFF_ID
from database import (
    get_all_employees, get_all_workplaces,
    get_schedules_with_reply_status, get_active_workplaces
)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@require_basic_auth
def index():
    """メイン画面（送信管理画面）"""
    employees = get_all_employees()
    workplaces = get_all_workplaces()
    recent_schedules = get_schedules_with_reply_status(20)
    return render_template(
        'index.html',
        employees=employees,
        workplaces=workplaces,
        recent_schedules=recent_schedules,
        liff_id=LIFF_ID
    )

@main_bp.route('/register')
def register_page():
    """LIFF登録画面"""
    return render_template('register.html', liff_id=LIFF_ID)

@main_bp.route('/wizard')
@require_basic_auth
def wizard():
    """ウィザード形式の送信画面"""
    workplaces = get_active_workplaces()
    return render_template('wizard.html', workplaces=workplaces)
