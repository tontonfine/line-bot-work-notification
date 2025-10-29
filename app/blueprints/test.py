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

@test_bp.route('/debug_info', methods=['GET'])
@csrf.exempt
@require_auth
def debug_info():
    """デバッグ情報表示"""
    from database import (
        get_notification_managers, get_today_schedules_by_reply_status,
        check_all_replied_today, get_today_all_replies_with_time,
        check_all_replied_notification_sent_today
    )
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        # 通知先社員
        managers = get_notification_managers()

        # 本日の送信履歴
        schedules = get_today_schedules_by_reply_status()

        # 全員返信チェック
        all_replied, total_count, replied_count = check_all_replied_today()

        # 返信情報
        replies_info = get_today_all_replies_with_time() if all_replied else []

        # 通知済みフラグ
        notification_sent = check_all_replied_notification_sent_today()

        # 現在時刻
        now = datetime.now(ZoneInfo('Asia/Tokyo'))
        today = str(now.date())

        return jsonify({
            'success': True,
            'debug_info': {
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'today': today,
                'managers': [
                    {
                        'name': m['name'],
                        'line_user_id': m['line_user_id'][:20] + '...' if m['line_user_id'] else None
                    } for m in managers
                ],
                'today_schedules': [
                    {
                        'employee_name': s['employee_name'],
                        'reply_status': s['reply_status'],
                        'sent_at': s['sent_at']
                    } for s in schedules
                ],
                'reply_check': {
                    'all_replied': all_replied,
                    'total_count': total_count,
                    'replied_count': replied_count
                },
                'replies_info': [
                    {
                        'employee_name': r['employee_name'],
                        'replied_at': r['replied_at']
                    } for r in replies_info
                ],
                'notification_sent_today': notification_sent
            }
        })
    except Exception as e:
        logging.error(f"Debug info failed: {str(e)}")
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
