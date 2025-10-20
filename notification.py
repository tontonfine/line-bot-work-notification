"""通知システム - 社員への通知管理"""
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from database import get_notification_managers, get_db_connection
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))

def send_to_managers(message_text):
    """通知先社員全員にメッセージを送信"""
    managers = get_notification_managers()

    if not managers:
        print("⚠️ 通知先社員が設定されていません")
        return

    success_count = 0
    for manager in managers:
        if not manager['line_user_id']:
            print(f"⚠️ {manager['name']}のLINE IDが未設定")
            continue

        try:
            line_bot_api.push_message(
                manager['line_user_id'],
                TextSendMessage(text=message_text)
            )
            record_notification('manager_notification', manager['id'], None, message_text)
            print(f"✅ {manager['name']}に通知送信")
            success_count += 1
        except LineBotApiError as e:
            print(f"❌ {manager['name']}への通知失敗: {e}")

    return success_count

def send_reply_summary(replied_list, not_replied_list):
    """13:00の返信状況まとめ通知"""
    message = "📊 本日の返信状況\n\n"

    if replied_list:
        message += "✅ 返信済み:\n"
        for emp in replied_list:
            message += f"  • {emp['employee_name']}\n"
        message += "\n"

    if not_replied_list:
        message += "⚠️ 未返信 (再送信しました):\n"
        for emp in not_replied_list:
            message += f"  • {emp['employee_name']}\n"

    send_to_managers(message)
    print("📊 返信状況まとめ通知を送信しました")

def send_late_reply_notification(employee_name, reply_time, pending_employees):
    """遅延返信の即時通知（未返信者リスト付き）

    Args:
        employee_name: 返信した従業員名
        reply_time: 返信時刻 (HH:MM形式)
        pending_employees: 未返信者リスト [{'employee_name': str}, ...]
    """
    message = f"📨 遅延返信がありました\n\n{employee_name}さんから返信 ({reply_time})\n"

    # 未返信者リストを追加
    if pending_employees:
        message += f"\n⚠️ 残り未返信者 ({len(pending_employees)}人):\n"
        for emp in pending_employees:
            message += f"  • {emp['employee_name']}\n"
    else:
        message += "\n✅ 全員返信完了"

    send_to_managers(message)
    print(f"📨 {employee_name}の遅延返信を通知しました（残り未返信: {len(pending_employees)}人）")

def send_all_replied_notification(all_replies_info):
    """全員返信完了の即時通知（重複防止付き、全員分の時刻表示）"""
    from database import check_all_replied_notification_sent_today, mark_all_replied_notification_sent

    # 本日既に通知済みかチェック
    if check_all_replied_notification_sent_today():
        print(f"⏭️ 全員返信完了通知は既に送信済み（スキップ）")
        return

    # 全員分の返信情報を整形
    message = "✅ 全員分の返信が集まりました\n\n返信状況:\n"

    for i, reply in enumerate(all_replies_info):
        # replied_atをパース（YYYY-MM-DD HH:MM:SS.ffffff形式）
        replied_at_str = reply['replied_at']
        try:
            # タイムスタンプから時刻部分を取得
            time_part = replied_at_str.split()[1].split('.')[0]  # "HH:MM:SS"
            time_display = time_part[:5]  # "HH:MM"
        except (IndexError, AttributeError):
            time_display = "??:??"

        # 最後の返信にマーク
        if i == len(all_replies_info) - 1:
            message += f"  • {reply['employee_name']}さん {time_display} ← 最後\n"
        else:
            message += f"  • {reply['employee_name']}さん {time_display}\n"

    send_to_managers(message)

    # 通知済みフラグを記録
    mark_all_replied_notification_sent()

    last_name = all_replies_info[-1]['employee_name'] if all_replies_info else '不明'
    print(f"✅ 全員返信完了を通知しました（最後: {last_name}）")

def send_second_reminder_alert(not_replied_list):
    """14:00時点の未返信通知"""
    if not not_replied_list:
        return

    message = "🚨 14:00時点でまだ未返信\n\n"
    for emp in not_replied_list:
        message += f"  • {emp['employee_name']}\n"

    message += "\n※3回連続で送信しました"
    send_to_managers(message)
    print("🚨 14:00未返信アラートを送信しました")

def record_notification(notification_type, recipient_id, schedule_id, message):
    """通知履歴をDBに記録"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO notifications (notification_type, recipient_id, schedule_id, message)
               VALUES (?, ?, ?, ?)''',
            (notification_type, recipient_id, schedule_id, message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ 通知履歴記録エラー: {e}")
