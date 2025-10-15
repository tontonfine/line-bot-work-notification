import os
import time
from datetime import datetime
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage
from dotenv import load_dotenv
from database import get_setting

# 環境変数を読み込み
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

def format_date_with_weekday(date_str):
    """
    日付文字列を曜日付きフォーマットに変換

    Args:
        date_str: "2025年10月14日" 形式の日付文字列

    Returns:
        str: "10月14日(火)" 形式の日付文字列
    """
    try:
        # "2025年10月14日" から日付をパース
        date_obj = datetime.strptime(date_str, "%Y年%m月%d日")

        # 曜日マッピング
        weekdays = ['月', '火', '水', '木', '金', '土', '日']
        weekday = weekdays[date_obj.weekday()]

        # "10月14日(火)" 形式にフォーマット
        return f"{date_obj.month}月{date_obj.day}日({weekday})"
    except:
        # パースに失敗した場合は元の文字列を返す
        return date_str

def get_message_from_template(work_date, workplace, work_time):
    """
    テンプレートからメッセージを生成

    Args:
        work_date: 勤務日（例: "2024年1月15日"）
        workplace: 勤務場所（例: "東京オフィス"）
        work_time: 出勤時間（例: "9:00" または "なるべく早めに出勤"）

    Returns:
        str: 生成されたメッセージ
    """
    # デフォルトテンプレート
    default_template = """【勤務連絡】

{date}の勤務についてお知らせします。

勤務場所: {workplace}
出勤時間: {time}

上記の内容で出勤をお願いします。
この連絡に返信をお願いします。"""

    template = get_setting('message_template', default_template)

    # 日付を曜日付きフォーマットに変換
    formatted_date = format_date_with_weekday(work_date)

    # テンプレート変数を置き換え
    message = template.replace('{date}', formatted_date)
    message = message.replace('{workplace}', workplace)
    message = message.replace('{time}', work_time)

    return message

def send_work_notification(line_user_id, work_date, workplace, work_time, custom_template=None):
    """
    指定したLINEユーザーに勤務連絡を送信

    Args:
        line_user_id: LINEユーザーID
        work_date: 勤務日（例: "2024年1月15日"）
        workplace: 勤務場所（例: "東京オフィス"）
        work_time: 出勤時間（例: "9:00" または "なるべく早めに出勤"）
        custom_template: カスタムテンプレート（オプション）

    Returns:
        tuple: (送信成功したかどうか, 送信したメッセージ内容)
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        return False, None

    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

    # カスタムテンプレートがある場合はそれを使用
    if custom_template:
        # 日付を曜日付きフォーマットに変換
        formatted_date = format_date_with_weekday(work_date)

        # テンプレート変数を置き換え
        message = custom_template.replace('{date}', formatted_date)
        message = message.replace('{workplace}', workplace)
        message = message.replace('{time}', work_time)
    else:
        # デフォルトテンプレートを使用
        message = get_message_from_template(work_date, workplace, work_time)

    try:
        line_bot_api.push_message(
            line_user_id,
            TextSendMessage(text=message)
        )
        print(f"✅ 送信成功: {message[:50]}...")
        return True, message
    except LineBotApiError as e:
        print(f"❌ 送信失敗: {e.status_code} - {e.error.message}")
        return False, message

def send_bulk_notifications(notifications, custom_template=None):
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
        custom_template: カスタムテンプレート（オプション）

    Returns:
        dict: {'success': 成功数, 'failed': 失敗数, 'results': 結果リスト}
    """
    results = []
    success_count = 0
    failed_count = 0

    for notification in notifications:
        success, message = send_work_notification(
            notification['line_user_id'],
            notification['work_date'],
            notification['workplace'],
            notification['work_time'],
            custom_template
        )

        results.append({
            'line_user_id': notification['line_user_id'],
            'success': success,
            'message': message
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

def send_work_notification_triple(line_user_id, work_date, workplace, work_time, message_content=None):
    """
    勤務通知を3回連続送信（14:00の未返信者用）

    Args:
        line_user_id: LINEユーザーID
        work_date: 勤務日
        workplace: 勤務場所
        work_time: 出勤時間
        message_content: 送信済みのメッセージ内容（オプション、Noneの場合はテンプレートから生成）

    Returns:
        bool: 少なくとも1回送信成功したかどうか
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        return False

    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

    # message_contentがあればそれを使用、なければテンプレートから生成
    if message_content:
        message = message_content
    else:
        message = get_message_from_template(work_date, workplace, work_time)

    success_count = 0
    for i in range(3):
        try:
            line_bot_api.push_message(
                line_user_id,
                TextSendMessage(text=message)
            )
            success_count += 1
            print(f"✅ 勤務通知送信 ({i+1}/3): {message[:50]}...")
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
