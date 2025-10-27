#!/usr/bin/env python3
"""
全員返信完了通知のデバッグスクリプト
なぜ通知が送られないのかを調査する
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from database import (
    get_db_connection,
    check_all_replied_today,
    get_today_all_replies_with_time,
    check_all_replied_notification_sent_today,
    get_notification_managers,
    get_setting
)

def debug_notification_issue():
    """全員返信完了通知が送られない原因を調査"""

    print("=" * 60)
    print("🔍 全員返信完了通知デバッグ")
    print("=" * 60)

    # 1. 現在の日付
    today = str(datetime.now(ZoneInfo('Asia/Tokyo')).date())
    print(f"\n📅 現在の日付: {today}")

    # 2. 本日の勤務予定を確認
    conn = get_db_connection()
    schedules = conn.execute(
        '''SELECT ws.id, e.name as employee_name, ws.reply_status, ws.sent_at
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           WHERE DATE(ws.sent_at) = ?
           ORDER BY ws.id''',
        (today,)
    ).fetchall()

    print(f"\n📋 本日送信した勤務予定: {len(schedules)}件")
    for schedule in schedules:
        print(f"  - ID:{schedule['id']} {schedule['employee_name']} "
              f"[{schedule['reply_status']}] (送信:{schedule['sent_at']})")

    # 3. 全員返信チェック
    all_replied, total_count, replied_count = check_all_replied_today()
    print(f"\n✅ 全員返信チェック:")
    print(f"  - 対象者数: {total_count}人")
    print(f"  - 返信済み: {replied_count}人")
    print(f"  - 全員返信: {'はい' if all_replied else 'いいえ'}")

    # 4. 返信情報の詳細
    if all_replied:
        replies = get_today_all_replies_with_time()
        print(f"\n📝 返信情報:")
        for reply in replies:
            print(f"  - {reply['employee_name']}: {reply['replied_at']}")

    # 5. 重複防止フラグの確認
    notification_sent_today = check_all_replied_notification_sent_today()
    notification_date = get_setting('all_replied_notification_sent_date')
    print(f"\n🚩 重複防止フラグ:")
    print(f"  - 本日通知済み: {'はい' if notification_sent_today else 'いいえ'}")
    print(f"  - 記録された通知日: {notification_date or '未設定'}")

    # 6. 通知先社員の確認
    managers = get_notification_managers()
    print(f"\n👥 通知先社員: {len(managers)}人")
    for manager in managers:
        try:
            line_id_status = "✅ 設定済み" if manager['line_user_id'] else "❌ 未設定"
            emp_num = manager['employee_number'] if 'employee_number' in manager.keys() else '不明'
            print(f"  - {manager['name']} ({emp_num}) {line_id_status}")
        except (KeyError, TypeError):
            print(f"  - {manager['name']} (情報取得エラー)")

    # 7. 最近の勤務予定を確認（過去7日間）
    recent_schedules = conn.execute(
        '''SELECT DATE(ws.sent_at) as sent_date, COUNT(*) as count
           FROM work_schedules ws
           WHERE DATE(ws.sent_at) >= DATE('now', '-7 days')
           GROUP BY DATE(ws.sent_at)
           ORDER BY DATE(ws.sent_at) DESC
           LIMIT 10'''
    ).fetchall()

    if recent_schedules:
        print(f"\n📆 過去7日間の送信履歴:")
        for row in recent_schedules:
            print(f"  - {row['sent_date']}: {row['count']}件")
    else:
        print(f"\n📆 過去7日間の送信履歴: なし")

    # 8. 問題の診断
    print(f"\n" + "=" * 60)
    print("🔎 診断結果")
    print("=" * 60)

    if total_count == 0:
        print("❌ 問題: 本日の勤務予定が送信されていません")
        print("   解決策: 先に勤務連絡を送信してください")
    elif not all_replied:
        print(f"❌ 問題: まだ全員が返信していません ({replied_count}/{total_count}人)")
        print("   解決策: 未返信者に返信を促してください")
    elif notification_sent_today:
        print("⚠️ 問題: 本日既に通知を送信済みです")
        print("   解決策: 重複防止フラグをリセットする場合:")
        print("   >>> from database import update_setting")
        print("   >>> update_setting('all_replied_notification_sent_date', '')")
    elif len(managers) == 0:
        print("❌ 問題: 通知先社員が設定されていません")
        print("   解決策: 設定ページから通知先社員を設定してください")
    elif not any(m['line_user_id'] for m in managers):
        print("❌ 問題: 通知先社員のLINE IDが設定されていません")
        print("   解決策: 通知先社員にLINE登録してもらってください")
    else:
        print("✅ すべての条件を満たしています")
        print("   通知が送られない場合、以下を確認:")
        print("   1. Renderのログを確認")
        print("   2. LINE Bot APIのトークンが正しいか確認")
        print("   3. 従業員が返信した後にwebhookが正しく動作しているか確認")

    conn.close()
    print("=" * 60)

if __name__ == '__main__':
    debug_notification_issue()
