"""スケジューラー - 定期的な返信チェックとリマインダー送信"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date
from database import (
    get_setting, get_schedules_by_date, get_today_schedules_by_reply_status,
    update_work_schedule_reply_status,
    update_first_reminder_sent, update_second_reminder_sent
)
from line_sender import send_work_notification, send_work_notification_triple
from notification import send_reply_summary, send_second_reminder_alert
import pytz

scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Tokyo'))
JST = pytz.timezone('Asia/Tokyo')

def check_1pm_replies():
    """13:00の返信チェックジョブ"""
    print("🕐 13:00返信チェック開始")
    try:
        # 本日送信分の勤務予定を取得
        schedules = get_today_schedules_by_reply_status()

        if not schedules:
            print("📭 本日の送信履歴がありません")
            return

        # 返信済み/未返信を分類
        replied = [s for s in schedules if s['reply_status'] in ('replied', 'late_replied')]
        not_replied = [s for s in schedules if s['reply_status'] == 'pending']

        print(f"📊 返信済み: {len(replied)}件、未返信: {len(not_replied)}件")

        # 未返信者に再送（元のメッセージ内容を使用）
        for schedule in not_replied:
            if schedule['line_user_id']:
                print(f"📤 再送信: {schedule['employee_name']}")
                success, _ = send_work_notification(
                    schedule['line_user_id'],
                    schedule['work_date'],
                    schedule['workplace'],
                    schedule['work_time'],
                    schedule['message_content']  # 元のメッセージ内容を使用
                )
                if success:
                    update_first_reminder_sent(schedule['id'])
                else:
                    print(f"⚠️ {schedule['employee_name']}への再送信失敗")

        # 社員に通知
        if replied or not_replied:
            send_reply_summary(replied, not_replied)

        print("✅ 13:00チェック完了")

    except Exception as e:
        print(f"❌ 13:00チェックエラー: {e}")
        import traceback
        traceback.print_exc()

def check_2pm_replies():
    """14:00の未返信チェックジョブ"""
    print("🕑 14:00未返信チェック開始")
    try:
        # 本日送信分の勤務予定を取得
        schedules = get_today_schedules_by_reply_status()

        if not schedules:
            print("📭 本日の送信履歴がありません")
            return

        # 13:00に再送したがまだ未返信の人
        still_not_replied = [
            s for s in schedules
            if s['first_reminder_sent_at'] and s['reply_status'] == 'pending'
        ]

        if not still_not_replied:
            print("✅ 全員返信済み")
            return

        print(f"🚨 まだ未返信: {len(still_not_replied)}件")

        # 3回連続送信（元のメッセージ内容を使用）
        for schedule in still_not_replied:
            if schedule['line_user_id']:
                print(f"📤📤📤 3回連続送信: {schedule['employee_name']}")
                success = send_work_notification_triple(
                    schedule['line_user_id'],
                    schedule['work_date'],
                    schedule['workplace'],
                    schedule['work_time'],
                    schedule['message_content']  # 元のメッセージ内容を使用
                )
                if success:
                    update_second_reminder_sent(schedule['id'])
                else:
                    print(f"⚠️ {schedule['employee_name']}への3連続送信失敗")

        # 社員に通知
        send_second_reminder_alert(still_not_replied)

        print("✅ 14:00チェック完了")

    except Exception as e:
        print(f"❌ 14:00チェックエラー: {e}")
        import traceback
        traceback.print_exc()

def setup_scheduler():
    """スケジューラーをセットアップして開始"""
    try:
        # 設定から返信期限時刻を取得（デフォルト13:00）
        deadline_time = get_setting('reply_deadline_time', '13:00')
        hour, minute = map(int, deadline_time.split(':'))

        print(f"⏰ スケジューラーセットアップ: 期限時刻 {deadline_time}")

        # 既存のジョブを削除（再起動時の重複防止）
        if scheduler.get_job('check_1pm'):
            scheduler.remove_job('check_1pm')
        if scheduler.get_job('check_2pm'):
            scheduler.remove_job('check_2pm')

        # 13:00のチェックジョブ
        scheduler.add_job(
            check_1pm_replies,
            'cron',
            hour=hour,
            minute=minute,
            timezone=JST,
            id='check_1pm',
            replace_existing=True
        )
        print(f"✅ 13:00チェックジョブ登録: 毎日{hour:02d}:{minute:02d}")

        # 14:00のチェックジョブ（期限時刻+1時間）
        scheduler.add_job(
            check_2pm_replies,
            'cron',
            hour=hour + 1,
            minute=minute,
            timezone=JST,
            id='check_2pm',
            replace_existing=True
        )
        print(f"✅ 14:00チェックジョブ登録: 毎日{hour+1:02d}:{minute:02d}")

        # スケジューラー開始
        if not scheduler.running:
            scheduler.start()
            print("🚀 スケジューラー起動完了")
        else:
            print("✅ スケジューラーは既に起動中")

    except Exception as e:
        print(f"❌ スケジューラーセットアップエラー: {e}")

def stop_scheduler():
    """スケジューラーを停止"""
    if scheduler.running:
        scheduler.shutdown()
        print("🛑 スケジューラー停止")

def get_scheduled_jobs():
    """登録されているジョブの一覧を取得"""
    jobs = scheduler.get_jobs()
    return [
        {
            'id': job.id,
            'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
        }
        for job in jobs
    ]
