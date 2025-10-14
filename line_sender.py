import os
import time
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

def send_work_notification(line_user_id, work_date, workplace, work_time):
    """
    指定したLINEユーザーに勤務連絡を送信

    Args:
        line_user_id: LINEユーザーID
        work_date: 勤務日（例: "2024年1月15日"）
        workplace: 勤務場所（例: "東京オフィス"）
        work_time: 出勤時間（例: "9:00"）

    Returns:
        bool: 送信成功したかどうか
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        return False

    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

    # メッセージを組み立て
    message = f"{work_date} {workplace} {work_time} お願いします"

    try:
        line_bot_api.push_message(
            line_user_id,
            TextSendMessage(text=message)
        )
        print(f"✅ 送信成功: {message}")
        return True
    except LineBotApiError as e:
        print(f"❌ 送信失敗: {e.status_code} - {e.error.message}")
        return False

def send_bulk_notifications(notifications):
    """
    複数の従業員に一斉送信

    Args:
        notifications: 送信情報のリスト
            [
                {
                    'line_user_id': 'U1234...',
                    'work_date': '2024年1月15日',
                    'workplace': '東京オフィス',
                    'work_time': '9:00'
                },
                ...
            ]

    Returns:
        dict: {'success': 成功数, 'failed': 失敗数, 'results': 結果リスト}
    """
    results = []
    success_count = 0
    failed_count = 0

    for notification in notifications:
        success = send_work_notification(
            notification['line_user_id'],
            notification['work_date'],
            notification['workplace'],
            notification['work_time']
        )

        results.append({
            'line_user_id': notification['line_user_id'],
            'success': success
        })

        if success:
            success_count += 1
        else:
            failed_count += 1

    return {
        'success': success_count,
        'failed': failed_count,
        'results': results
    }

def send_work_notification_triple(line_user_id, work_date, workplace, work_time):
    """
    勤務通知を3回連続送信（14:00の未返信者用）

    Args:
        line_user_id: LINEユーザーID
        work_date: 勤務日
        workplace: 勤務場所
        work_time: 出勤時間

    Returns:
        bool: 少なくとも1回送信成功したかどうか
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        return False

    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    message = f"{work_date} {workplace} {work_time} お願いします"

    success_count = 0
    for i in range(3):
        try:
            line_bot_api.push_message(
                line_user_id,
                TextSendMessage(text=message)
            )
            success_count += 1
            print(f"✅ 勤務通知送信 ({i+1}/3): {message}")
            if i < 2:  # 最後の送信後は待たない
                time.sleep(1)  # 1秒待機
        except LineBotApiError as e:
            print(f"❌ 送信失敗 ({i+1}/3): {e.status_code} - {e.error.message}")
            # 1回でも成功していれば継続
            if success_count == 0:
                return False  # 1回も成功していない場合のみ失敗扱い

    print(f"📊 3回送信完了: {success_count}/3回成功")
    return success_count > 0  # 少なくとも1回成功していればOK

if __name__ == '__main__':
    # テスト用コード
    print("🧪 LINE送信機能のテスト")
    print("環境変数が正しく設定されているか確認してください")
    print(f"ACCESS_TOKEN設定済み: {bool(LINE_CHANNEL_ACCESS_TOKEN)}")
