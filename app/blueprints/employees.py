"""Employee management blueprint"""
from flask import Blueprint, render_template, request, jsonify, session
from auth import require_admin_auth
from app.extensions import csrf
from app.line_bot import LIFF_ID
from database import (
    get_db_connection, add_employee, update_employee_type,
    update_employee_active_status, delete_employee_permanent
)
from sheets_sync import sync_employees_from_sheet
from validators import validate_employee_name, validate_employee_number, validate_employee_type
import logging

employees_bp = Blueprint('employees', __name__, url_prefix='/employees')

@employees_bp.route('/')
@require_admin_auth
def employees_list():
    """従業員一覧（管理者認証必要）"""
    # is_active >= 0 のみ表示（-1は非表示）
    conn = get_db_connection()
    # 従業員番号の数値部分でソート（k00001, k00002, ... の順）
    employees = conn.execute('''
        SELECT * FROM employees
        WHERE is_active >= 0
        ORDER BY CAST(SUBSTR(employee_number, 2) AS INTEGER)
    ''').fetchall()
    conn.close()

    return render_template('employees.html', employees=employees, liff_id=LIFF_ID)

@employees_bp.route('/add', methods=['POST'])
@csrf.exempt
def add_employee_route():
    """従業員を手動追加（管理用）"""
    # 認証チェック
    if not session.get('admin_authenticated'):
        logging.warning(f"Unauthorized employee add attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    data = request.json
    name = data.get('name')
    employee_number = data.get('employee_number')

    if not name or not employee_number:
        return jsonify({'error': '名前と従業員番号は必須です'}), 400

    # 入力検証
    valid, error_msg = validate_employee_name(name)
    if not valid:
        logging.warning(f"Invalid employee name from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    valid, error_msg = validate_employee_number(employee_number)
    if not valid:
        logging.warning(f"Invalid employee_number from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    employee_id = add_employee(name, employee_number)

    if employee_id:
        logging.info(f"Employee added: {employee_number} from {request.remote_addr}")
        return jsonify({'success': True, 'employee_id': employee_id})
    else:
        logging.warning(f"Failed to add employee: {employee_number} from {request.remote_addr}")
        return jsonify({'error': '従業員の追加に失敗しました（重複の可能性）'}), 400

@employees_bp.route('/type', methods=['POST'])
@csrf.exempt
def update_employee_type_route():
    """従業員種別を変更（アルバイト⇔社員）"""
    # 認証チェック
    if not session.get('admin_authenticated'):
        logging.warning(f"Unauthorized employee type update attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    data = request.json
    employee_id = data.get('employee_id')
    employee_type = data.get('employee_type')  # 'part_time' or 'full_time'

    if not employee_id or not employee_type:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    # 入力検証
    valid, error_msg = validate_employee_type(employee_type)
    if not valid:
        logging.warning(f"Invalid employee_type from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    success = update_employee_type(employee_id, employee_type)

    if success:
        type_name = 'アルバイト' if employee_type == 'part_time' else '社員'
        logging.info(f"Employee type updated: id={employee_id} to {employee_type} from {request.remote_addr}")
        return jsonify({'success': True, 'message': f'{type_name}に変更しました'})
    else:
        return jsonify({'error': '従業員種別の変更に失敗しました'}), 400

@employees_bp.route('/status', methods=['POST'])
@csrf.exempt
def update_employee_status():
    """従業員の在籍状況を更新"""
    # 認証チェック
    if not session.get('admin_authenticated'):
        logging.warning(f"Unauthorized employee status update attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    data = request.json
    employee_id = data.get('employee_id')
    is_active = data.get('is_active')  # 1 or 0

    if employee_id is None or is_active is None:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    if is_active not in [0, 1]:
        return jsonify({'error': '不正なステータスです'}), 400

    success = update_employee_active_status(employee_id, is_active)

    if success:
        status_name = '在籍' if is_active == 1 else '退職'
        logging.info(f"Employee status updated: id={employee_id} to {status_name} from {request.remote_addr}")
        return jsonify({'success': True, 'message': f'ステータスを{status_name}に変更しました'})
    else:
        return jsonify({'error': 'ステータス変更に失敗しました'}), 400

@employees_bp.route('/delete', methods=['POST'])
@csrf.exempt
def delete_employee():
    """従業員を物理削除（退職者のみ、関連データも削除）"""
    # 認証チェック
    if not session.get('admin_authenticated'):
        logging.warning(f"Unauthorized employee delete attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    data = request.json
    employee_id = data.get('employee_id')

    if employee_id is None:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    # 退職者のみ削除可能
    conn = get_db_connection()
    employee = conn.execute('SELECT is_active, employee_number, name FROM employees WHERE id = ?', (employee_id,)).fetchone()
    conn.close()

    if not employee:
        return jsonify({'error': '従業員が見つかりません'}), 404

    if employee['is_active'] == 1:
        return jsonify({'error': '在籍中の従業員は削除できません'}), 400

    # 物理削除（データベースから完全に削除、関連データも削除）
    success = delete_employee_permanent(employee_id)

    if success:
        logging.info(f"Employee permanently deleted: id={employee_id}, number={employee['employee_number']}, name={employee['name']} from {request.remote_addr}")
        return jsonify({'success': True, 'message': f'従業員を完全に削除しました（従業員番号 {employee["employee_number"]} は再利用可能です）'})
    else:
        logging.error(f"Failed to delete employee: id={employee_id} from {request.remote_addr}")
        return jsonify({'error': '削除に失敗しました'}), 400

@employees_bp.route('/sync', methods=['POST'])
@csrf.exempt
def sync_employees():
    """Googleスプレッドシートから従業員データを同期"""
    # 認証チェック
    if not session.get('admin_authenticated'):
        logging.warning(f"Unauthorized employee sync attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    try:
        logging.info(f"Employee sync started from {request.remote_addr}")
        result = sync_employees_from_sheet()

        if result['success']:
            message = f"✅ 同期完了: 新規{result['added']}件、更新{result['updated']}件"
            if result.get('errors'):
                message += f"（エラー{len(result['errors'])}件）"

            logging.info(f"Employee sync completed: added={result['added']}, updated={result['updated']} from {request.remote_addr}")
            return jsonify({
                'success': True,
                'message': message,
                'added': result['added'],
                'updated': result['updated'],
                'total': result['total'],
                'errors': result.get('errors', [])
            })
        else:
            logging.error(f"Employee sync failed from {request.remote_addr}: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '同期に失敗しました')
            }), 400

    except Exception as e:
        logging.error(f"Employee sync error from {request.remote_addr}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'同期エラー: {str(e)}'
        }), 500

@employees_bp.route('/login', methods=['GET', 'POST'])
def employee_login():
    """従業員管理ログイン（後方互換性）"""
    from flask import redirect, url_for
    return redirect(url_for('auth.admin_login'))

@employees_bp.route('/logout')
def employee_logout():
    """従業員管理ログアウト（後方互換性のため残す）"""
    from flask import redirect, url_for
    return redirect(url_for('auth.logout'))
