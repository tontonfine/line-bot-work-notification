"""LINE webhook blueprint"""
from flask import Blueprint, request
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from app.extensions import csrf, limiter
from app.line_bot import line_bot_api, handler
from database import (
    get_employee_by_line_id, get_latest_pending_schedule,
    get_setting, add_reply, update_work_schedule_reply_status,
    get_today_pending_employees, check_all_replied_today,
    get_today_all_replies_with_time
)
from notification import send_late_reply_notification, send_all_replied_notification
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['POST'])
@csrf.exempt
@limiter.limit("100 per minute")
def webhook():
    """LINE Webhook（LIFF登録用）"""
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logging.warning(f"Invalid webhook signature from {request.remote_addr}")
        return 'Invalid signature', 400

    return 'OK'

# メッセージハンドラーはモジュールレベルで定義
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """メッセージイベントの処理 - 返信を記録"""
    line_user_id = event.source.user_id
    message_text = event.message.text

    # LINE User IDから従業員を取得
    employee = get_employee_by_line_id(line_user_id)

    if employee:
        # 最新の未返信勤務予定を取得
        schedule = get_latest_pending_schedule(employee['id'])

        if not schedule:
            print(f"⚠️ {employee['name']}の未返信勤務予定が見つかりません")
            # 確認メッセージを返信
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="一緒に頑張りましょう!")
                )
            except LineBotApiError as e:
                print(f"❌ 返信エラー: {e}")
            return

        # 返信期限時刻を取得
        deadline_time = get_setting('reply_deadline_time', '13:00')
        deadline_hour, deadline_minute = map(int, deadline_time.split(':'))

        # 現在時刻と比較（日本時間）
        now = datetime.now(ZoneInfo('Asia/Tokyo'))
        deadline = now.replace(hour=deadline_hour, minute=deadline_minute, second=0, microsecond=0)
        is_late = now > deadline

        # 返信を記録（scheduleと紐付け）
        add_reply(employee['id'], message_text, schedule['id'])

        if is_late:
            # 遅延返信 - 即座に社員に通知
            print(f"⏰ 遅延返信: {employee['name']} - {message_text}")
            # reply_statusを'late_replied'に更新
            update_work_schedule_reply_status(schedule['id'], 'late_replied')
            # 未返信者リストを取得（この人の返信を反映した後のリスト）
            pending_employees = get_today_pending_employees()
            # 返信時刻を取得
            reply_time = now.strftime('%H:%M')
            # 遅延返信通知を送信
            send_late_reply_notification(employee['name'], reply_time, pending_employees)
        else:
            # 通常返信
            print(f"✅ 返信を記録: {employee['name']} - {message_text}")
            # reply_statusを'replied'に更新
            update_work_schedule_reply_status(schedule['id'], 'replied')

        # 全員返信チェック
        all_replied, total_count, replied_count = check_all_replied_today()
        logging.info(f"📊 全員返信チェック: all_replied={all_replied}, total={total_count}, replied={replied_count}")

        if all_replied and total_count > 0:
            # 全員が返信した場合、全員分の返信情報を取得して通知
            logging.info(f"✅ 全員返信を検知！通知を送信します")
            all_replies_info = get_today_all_replies_with_time()
            logging.info(f"📝 返信情報を取得: {len(all_replies_info)}件")
            send_all_replied_notification(all_replies_info)
            print(f"🎉 全員返信完了: {replied_count}/{total_count}人")
            logging.info(f"🎉 全員返信完了通知を送信しました: {replied_count}/{total_count}人")
        else:
            logging.info(f"⏳ まだ全員返信していません: {replied_count}/{total_count}人")

        # 確認メッセージを返信
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="一緒に頑張りましょう!")
            )
        except LineBotApiError as e:
            print(f"❌ 返信エラー: {e}")
    else:
        print(f"⚠️ 未登録のユーザーからのメッセージ: {line_user_id}")
