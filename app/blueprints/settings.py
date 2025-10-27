"""Settings management blueprint"""
from flask import Blueprint, render_template, request, jsonify
from auth import require_auth
from app.extensions import csrf
from database import (
    get_setting, update_setting, get_notification_managers,
    add_notification_manager, remove_notification_manager,
    get_all_employees, get_full_time_employees, get_all_workplaces,
    add_workplace, update_workplace, delete_workplace,
    hash_password, check_password
)
from auth import change_password
from validators import (
    validate_reply_deadline_time, validate_message_template,
    validate_workplace_name
)
import scheduler
import logging

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@require_auth
def settings():
    """設定画面"""
    deadline_time = get_setting('reply_deadline_time', '13:00')

    # デフォルトのメッセージテンプレート
    default_template = """【勤務連絡】

{date}の勤務についてお知らせします。

勤務場所: {workplace}
出勤時間: {time}

上記の内容で出勤をお願いします。
この連絡に返信をお願いします。"""

    message_template = get_setting('message_template', default_template)
    managers = get_notification_managers()
    all_employees = get_all_employees()
    full_time = get_full_time_employees()
    workplaces = get_all_workplaces()

    return render_template(
        'settings.html',
        deadline_time=deadline_time,
        message_template=message_template,
        managers=managers,
        all_employees=all_employees,
        full_time=full_time,
        workplaces=workplaces
    )

@settings_bp.route('/deadline', methods=['POST'])
@csrf.exempt
@require_auth
def update_deadline():
    """返信期限時刻を更新"""
    data = request.json
    new_time = data.get('deadline_time')

    if not new_time:
        return jsonify({'error': '時刻が指定されていません'}), 400

    # 入力検証
    valid, error_msg = validate_reply_deadline_time(new_time)
    if not valid:
        logging.warning(f"Invalid deadline_time from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    update_setting('reply_deadline_time', new_time)

    # スケジューラーを再セットアップ
    scheduler.stop_scheduler()
    scheduler.setup_scheduler()

    logging.info(f"Deadline updated to {new_time} from {request.remote_addr}")
    return jsonify({'success': True, 'message': f'返信期限を{new_time}に変更しました'})

@settings_bp.route('/password', methods=['POST'])
@csrf.exempt
@require_auth
def update_password():
    """パスワードを変更"""
    data = request.json
    current = data.get('current_password')
    new = data.get('new_password')

    if not current or not new:
        return jsonify({'error': 'パスワードを入力してください'}), 400

    success, message = change_password(current, new)

    if success:
        logging.info(f"Admin password changed from {request.remote_addr}")
        return jsonify({'success': True, 'message': message})
    else:
        logging.warning(f"Failed admin password change from {request.remote_addr}")
        return jsonify({'error': message}), 400

@settings_bp.route('/employee_password', methods=['POST'])
@csrf.exempt
@require_auth
def update_employee_password():
    """従業員管理パスワードを変更"""
    data = request.json
    current = data.get('current_password')
    new = data.get('new_password')

    if not current or not new:
        return jsonify({'error': 'パスワードを入力してください'}), 400

    # 現在のパスワードを確認
    stored_hash = get_setting('employee_mgmt_password_hash')
    if not stored_hash or not check_password(current, stored_hash):
        logging.warning(f"Failed employee password change (wrong current password) from {request.remote_addr}")
        return jsonify({'error': '現在のパスワードが正しくありません'}), 400

    # 新しいパスワードをハッシュ化して保存
    new_hash = hash_password(new)
    update_setting('employee_mgmt_password_hash', new_hash)

    logging.info(f"Employee management password changed from {request.remote_addr}")
    return jsonify({'success': True, 'message': '従業員管理パスワードを変更しました'})

@settings_bp.route('/managers', methods=['POST'])
@csrf.exempt
@require_auth
def update_managers():
    """通知先社員を更新（勤務地指定可能）"""
    data = request.json
    employee_id = data.get('employee_id')
    action = data.get('action')  # 'add' or 'remove'
    workplace_id = data.get('workplace_id')  # None の場合は全勤務地向け

    if not employee_id or not action:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    if action == 'add':
        add_notification_manager(employee_id, workplace_id)
        logging.info(f"Notification manager added: employee_id={employee_id} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '通知先に追加しました'})
    elif action == 'remove':
        remove_notification_manager(employee_id)
        logging.info(f"Notification manager removed: employee_id={employee_id} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '通知先から削除しました'})
    else:
        return jsonify({'error': '不正なアクションです'}), 400

@settings_bp.route('/message_template', methods=['POST'])
@csrf.exempt
@require_auth
def update_message_template():
    """送信テンプレートを更新"""
    data = request.json
    template = data.get('template')

    if not template:
        return jsonify({'error': 'テンプレートが指定されていません'}), 400

    # 入力検証
    valid, error_msg = validate_message_template(template)
    if not valid:
        logging.warning(f"Invalid message template from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    update_setting('message_template', template)
    logging.info(f"Message template updated from {request.remote_addr}")
    return jsonify({'success': True, 'message': 'テンプレートを保存しました'})

@settings_bp.route('/message_template/reset', methods=['POST'])
@csrf.exempt
@require_auth
def reset_message_template():
    """送信テンプレートをデフォルトに戻す"""
    default_template = """【勤務連絡】

{date}の勤務についてお知らせします。

勤務場所: {workplace}
出勤時間: {time}

上記の内容で出勤をお願いします。
この連絡に返信をお願いします。"""

    update_setting('message_template', default_template)
    logging.info(f"Message template reset to default from {request.remote_addr}")
    return jsonify({'success': True, 'message': 'テンプレートをデフォルトに戻しました'})

@settings_bp.route('/workplaces/add', methods=['POST'])
@csrf.exempt
@require_auth
def add_workplace_route():
    """勤務場所を追加"""
    data = request.json
    name = data.get('name')
    sort_order = data.get('sort_order', 999)

    if not name:
        return jsonify({'error': '勤務場所名は必須です'}), 400

    # 入力検証
    valid, error_msg = validate_workplace_name(name)
    if not valid:
        logging.warning(f"Invalid workplace name from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    workplace_id = add_workplace(name, sort_order)

    if workplace_id:
        logging.info(f"Workplace added: name={name} from {request.remote_addr}")
        return jsonify({'success': True, 'workplace_id': workplace_id, 'message': '勤務場所を追加しました'})
    else:
        logging.warning(f"Failed to add workplace: name={name} from {request.remote_addr}")
        return jsonify({'error': '勤務場所の追加に失敗しました（重複の可能性）'}), 400

@settings_bp.route('/workplaces/update', methods=['POST'])
@csrf.exempt
@require_auth
def update_workplace_route():
    """勤務場所を更新"""
    data = request.json
    workplace_id = data.get('workplace_id')
    name = data.get('name')
    sort_order = data.get('sort_order')

    if not workplace_id or not name or sort_order is None:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    # 入力検証
    valid, error_msg = validate_workplace_name(name)
    if not valid:
        logging.warning(f"Invalid workplace name for update from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    success = update_workplace(workplace_id, name, sort_order)

    if success:
        logging.info(f"Workplace updated: id={workplace_id}, name={name} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '勤務場所を更新しました'})
    else:
        return jsonify({'error': '勤務場所の更新に失敗しました'}), 400

@settings_bp.route('/workplaces/delete', methods=['POST'])
@csrf.exempt
@require_auth
def delete_workplace_route():
    """勤務場所を削除（物理削除）"""
    data = request.json
    workplace_id = data.get('workplace_id')

    if not workplace_id:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    success = delete_workplace(workplace_id)

    if success:
        logging.info(f"Workplace deleted: id={workplace_id} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '勤務場所を完全に削除しました'})
    else:
        return jsonify({'error': '勤務場所の削除に失敗しました'}), 400
