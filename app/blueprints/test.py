"""Test routes blueprint"""
from flask import Blueprint, request, jsonify
from auth import require_auth
from app.extensions import csrf
import logging

test_bp = Blueprint('test', __name__, url_prefix='/test')

@test_bp.route('/check_deadline', methods=['POST'])
@csrf.exempt
@require_auth
def test_check_deadline():
    """テスト用: 13:00の期限チェックを手動実行"""
    from scheduler import check_1pm_replies

    try:
        logging.info(f"Manual 1pm check triggered from {request.remote_addr}")
        check_1pm_replies()
        return jsonify({
            'success': True,
            'message': '✅ 期限チェック（13:00相当）を実行しました'
        })
    except Exception as e:
        logging.error(f"Manual 1pm check failed from {request.remote_addr}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'❌ エラー: {str(e)}'
        }), 500

@test_bp.route('/check_deadline_plus_1', methods=['POST'])
@csrf.exempt
@require_auth
def test_check_deadline_plus_1():
    """テスト用: 14:00の期限+1時間チェックを手動実行"""
    from scheduler import check_2pm_replies

    try:
        logging.info(f"Manual 2pm check triggered from {request.remote_addr}")
        check_2pm_replies()
        return jsonify({
            'success': True,
            'message': '✅ 期限+1時間チェック（14:00相当）を実行しました'
        })
    except Exception as e:
        logging.error(f"Manual 2pm check failed from {request.remote_addr}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'❌ エラー: {str(e)}'
        }), 500

@test_bp.route('/reset_notification_flag', methods=['POST'])
@csrf.exempt
@require_auth
def reset_notification_flag():
    """テスト用: 全員返信完了通知フラグをリセット"""
    from database import clear_all_replied_notification_flag

    try:
        logging.info(f"Notification flag reset triggered from {request.remote_addr}")
        clear_all_replied_notification_flag()
        return jsonify({
            'success': True,
            'message': '✅ 通知フラグをリセットしました。再度テストできます。'
        })
    except Exception as e:
        logging.error(f"Notification flag reset failed from {request.remote_addr}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'❌ エラー: {str(e)}'
        }), 500
