"""API routes blueprint"""
from flask import Blueprint, request, jsonify, session
from app.extensions import csrf, limiter
from app.line_bot import LIFF_ID
from database import (
    get_all_employees, get_all_workplaces, get_setting,
    get_filtered_schedules, get_part_time_employees,
    get_full_time_employees, get_available_employee_numbers,
    update_employee_line_id, check_password
)
from validators import (
    validate_employee_number, validate_employee_name, validate_line_user_id
)
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/register', methods=['POST'])
@csrf.exempt
@limiter.limit("10 per minute")
def register_employee():
    """従業員登録API（LIFFから呼ばれる）"""
    data = request.json

    employee_number = data.get('employee_number')
    employee_name = data.get('employee_name')
    line_user_id = data.get('line_user_id')

    if not employee_number or not line_user_id:
        logging.warning(f"Invalid registration attempt from {request.remote_addr}")
        return jsonify({'error': '従業員番号とLINEユーザーIDは必須です'}), 400

    if not employee_name:
        logging.warning(f"Missing employee name from {request.remote_addr}")
        return jsonify({'error': '氏名は必須です'}), 400

    # 入力検証
    valid, error_msg = validate_employee_number(employee_number)
    if not valid:
        logging.warning(f"Invalid employee_number format from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    valid, error_msg = validate_employee_name(employee_name)
    if not valid:
        logging.warning(f"Invalid employee_name format from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    valid, error_msg = validate_line_user_id(line_user_id)
    if not valid:
        logging.warning(f"Invalid line_user_id format from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    # LINEユーザーIDを更新（名前確認あり、UNIQUE制約対応）
    try:
        success, error_message = update_employee_line_id(employee_number, line_user_id, employee_name)

        if success:
            logging.info(f"Employee registered: {employee_number} ({employee_name}) from {request.remote_addr}")
            return jsonify({'success': True, 'message': '登録が完了しました'})
        else:
            logging.warning(f"Failed registration for employee: {employee_number} ({employee_name}) - {error_message}")
            return jsonify({'error': error_message or '従業員番号または氏名が一致しません'}), 404

    except Exception as e:
        logging.error(f"Unexpected error during registration: {employee_number} ({employee_name}) - {str(e)}")
        return jsonify({'error': '登録処理中にエラーが発生しました。管理者に連絡してください。'}), 500

@api_bp.route('/employees')
def api_employees():
    """従業員一覧API"""
    employees = get_all_employees()
    return jsonify([dict(emp) for emp in employees])

@api_bp.route('/workplaces')
def api_workplaces():
    """勤務場所一覧API"""
    workplaces = get_all_workplaces()
    return jsonify([dict(wp) for wp in workplaces])

@api_bp.route('/message_template')
def api_message_template():
    """メッセージテンプレート取得API"""
    default_template = """【勤務連絡】

{date}の勤務についてお知らせします。

勤務場所: {workplace}
出勤時間: {time}

上記の内容で出勤をお願いします。
この連絡に返信をお願いします。"""

    template = get_setting('message_template', default_template)
    return jsonify({'template': template})

@api_bp.route('/work_schedules')
def api_work_schedules():
    """送信履歴取得API（フィルター対応）"""
    work_date = request.args.get('date')
    workplace = request.args.get('workplace')

    schedules = get_filtered_schedules(work_date, workplace)
    return jsonify([dict(schedule) for schedule in schedules])

@api_bp.route('/part_time_employees')
def api_part_time_employees():
    """アルバイト従業員一覧API"""
    employees = get_part_time_employees()
    return jsonify([dict(emp) for emp in employees])

@api_bp.route('/full_time_employees')
def api_full_time_employees():
    """社員一覧API"""
    employees = get_full_time_employees()
    return jsonify([dict(emp) for emp in employees])

@api_bp.route('/available_employee_numbers')
def api_available_employee_numbers():
    """使用可能な従業員番号を取得"""
    limit = request.args.get('limit', 10, type=int)
    available_numbers = get_available_employee_numbers(limit)
    return jsonify(available_numbers)

@api_bp.route('/verify_password', methods=['POST'])
@csrf.exempt
def verify_password():
    """削除用パスワード検証API"""
    if not session.get('admin_authenticated'):
        logging.warning(f"Unauthorized password verification attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    data = request.json
    password = data.get('password')

    if not password:
        return jsonify({'error': 'パスワードが入力されていません'}), 400

    # 従業員管理パスワードと照合
    stored_hash = get_setting('employee_mgmt_password_hash')

    if stored_hash and check_password(password, stored_hash):
        logging.info(f"Password verification successful from {request.remote_addr}")
        return jsonify({'success': True, 'message': 'パスワードが正しいです'})
    else:
        logging.warning(f"Password verification failed from {request.remote_addr}")
        return jsonify({'success': False, 'error': 'パスワードが正しくありません'}), 401
