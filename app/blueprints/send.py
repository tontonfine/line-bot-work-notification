"""Send notifications blueprint"""
from flask import Blueprint, request, jsonify
from app.extensions import csrf, limiter
from line_sender import send_bulk_notifications, send_work_notification
from database import add_work_schedule
from validators import validate_work_date, validate_workplace_name, validate_work_time
import logging

send_bp = Blueprint('send', __name__)

@send_bp.route('/send', methods=['POST'])
@csrf.exempt
@limiter.limit("20 per minute")
def send_notifications():
    """勤務連絡を一斉送信（履歴保存あり）"""
    data = request.json

    # 送信データの検証
    if not data or 'notifications' not in data:
        logging.warning(f"Invalid send request from {request.remote_addr}")
        return jsonify({'error': '送信データが不正です'}), 400

    notifications = data['notifications']
    if not notifications:
        logging.warning(f"Empty notifications from {request.remote_addr}")
        return jsonify({'error': '送信対象が選択されていません'}), 400

    # 入力検証（各通知の内容をチェック）
    for i, notification in enumerate(notifications):
        work_date = notification.get('work_date')
        workplace = notification.get('workplace')
        work_time = notification.get('work_time')

        if work_date:
            valid, error_msg = validate_work_date(work_date)
            if not valid:
                logging.warning(f"Invalid work_date in notification {i} from {request.remote_addr}: {error_msg}")
                return jsonify({'error': f'通知{i+1}の勤務日が不正です: {error_msg}'}), 400

        if workplace:
            valid, error_msg = validate_workplace_name(workplace)
            if not valid:
                logging.warning(f"Invalid workplace in notification {i} from {request.remote_addr}: {error_msg}")
                return jsonify({'error': f'通知{i+1}の勤務場所が不正です: {error_msg}'}), 400

        if work_time:
            valid, error_msg = validate_work_time(work_time)
            if not valid:
                logging.warning(f"Invalid work_time in notification {i} from {request.remote_addr}: {error_msg}")
                return jsonify({'error': f'通知{i+1}の出勤時間が不正です: {error_msg}'}), 400

    # 送信実行
    results = send_bulk_notifications(notifications)

    # データベースに記録（送信成功したもののみ）
    recorded_count = 0
    for i, notification in enumerate(notifications):
        if notification.get('employee_id'):
            # 対応する送信結果を確認
            if i < len(results['results']) and results['results'][i]['success']:
                add_work_schedule(
                    employee_id=notification['employee_id'],
                    work_date=notification['work_date'],
                    workplace=notification['workplace'],
                    work_time=notification['work_time'],
                    message_content=results['results'][i].get('message')
                )
                recorded_count += 1

    logging.info(f"Bulk send: {results['success']} sent, {results['failed']} failed from {request.remote_addr}")

    return jsonify({
        'success': True,
        'sent_count': results['success'],
        'failed_count': results['failed'],
        'recorded_count': recorded_count,
        'message': f'{results["success"]}件送信しました（DB記録: {recorded_count}件）'
    })

@send_bp.route('/wizard/send', methods=['POST'])
@csrf.exempt
@limiter.limit("20 per minute")
def wizard_send_notifications():
    """ウィザード送信（履歴保存あり、個別カスタムテンプレート対応）"""
    data = request.json

    # 送信データの検証
    if not data or 'notifications' not in data:
        logging.warning(f"Invalid wizard send request from {request.remote_addr}")
        return jsonify({'error': '送信データが不正です'}), 400

    notifications = data['notifications']
    if not notifications:
        logging.warning(f"Empty wizard notifications from {request.remote_addr}")
        return jsonify({'error': '送信対象が選択されていません'}), 400

    # 入力検証（各通知の内容をチェック）
    for i, notification in enumerate(notifications):
        work_date = notification.get('work_date')
        workplace = notification.get('workplace')
        work_time = notification.get('work_time')

        if work_date:
            valid, error_msg = validate_work_date(work_date)
            if not valid:
                logging.warning(f"Invalid work_date in wizard notification {i} from {request.remote_addr}: {error_msg}")
                return jsonify({'error': f'通知{i+1}の勤務日が不正です: {error_msg}'}), 400

        if workplace:
            valid, error_msg = validate_workplace_name(workplace)
            if not valid:
                logging.warning(f"Invalid workplace in wizard notification {i} from {request.remote_addr}: {error_msg}")
                return jsonify({'error': f'通知{i+1}の勤務場所が不正です: {error_msg}'}), 400

        if work_time:
            valid, error_msg = validate_work_time(work_time)
            if not valid:
                logging.warning(f"Invalid work_time in wizard notification {i} from {request.remote_addr}: {error_msg}")
                return jsonify({'error': f'通知{i+1}の出勤時間が不正です: {error_msg}'}), 400

    # 各通知を個別に送信（個別テンプレート対応）
    success_count = 0
    failed_count = 0
    recorded_count = 0

    for notification in notifications:
        # 個別のカスタムテンプレートを取得
        custom_template = notification.get('custom_template')

        # 送信実行
        success, message_content = send_work_notification(
            notification['line_user_id'],
            notification['work_date'],
            notification['workplace'],
            notification['work_time'],
            custom_template
        )

        if success:
            success_count += 1
            # データベースに記録（メッセージ内容も保存）
            if notification.get('employee_id'):
                add_work_schedule(
                    employee_id=notification['employee_id'],
                    work_date=notification['work_date'],
                    workplace=notification['workplace'],
                    work_time=notification['work_time'],
                    message_content=message_content
                )
                recorded_count += 1
        else:
            failed_count += 1

    logging.info(f"Wizard send: {success_count} sent, {failed_count} failed from {request.remote_addr}")

    return jsonify({
        'success': True,
        'sent_count': success_count,
        'failed_count': failed_count,
        'recorded_count': recorded_count,
        'message': f'{success_count}件送信しました（履歴記録: {recorded_count}件）'
    })
