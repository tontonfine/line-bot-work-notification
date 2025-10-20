"""入力検証モジュール - セキュリティ強化のための検証関数"""
import re
from datetime import datetime

def validate_employee_number(employee_number):
    """
    従業員番号のフォーマットを検証

    Args:
        employee_number: 検証する従業員番号（例: "k00001" または "K00001"）

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not employee_number:
        return False, "従業員番号は必須です"

    # k + 5桁の数字のパターン（大文字小文字どちらも可）
    pattern = r'^[kK]\d{5}$'
    if not re.match(pattern, employee_number):
        return False, "従業員番号は'k'と5桁の数字の形式である必要があります（例: k00001）"

    return True, None


def validate_work_date(date_str):
    """
    勤務日のフォーマットを検証

    Args:
        date_str: 検証する日付文字列（例: "2025年10月15日"）

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not date_str:
        return False, "勤務日は必須です"

    # YYYY年MM月DD日のパターン
    pattern = r'^\d{4}年\d{1,2}月\d{1,2}日$'
    if not re.match(pattern, date_str):
        return False, "勤務日は'YYYY年MM月DD日'の形式である必要があります"

    # 実際に有効な日付かチェック
    try:
        datetime.strptime(date_str, "%Y年%m月%d日")
    except ValueError:
        return False, "無効な日付です"

    return True, None


def validate_work_time(time_str):
    """
    出勤時間のフォーマットを検証

    Args:
        time_str: 検証する時刻文字列（例: "9:00"）

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not time_str:
        return False, "出勤時間は必須です"

    # 時刻フォーマット（H:MM または HH:MM）またはテキスト
    # テキストの場合は最大50文字まで許可
    time_pattern = r'^\d{1,2}:\d{2}$'

    if re.match(time_pattern, time_str):
        # 時刻形式の場合、有効性をチェック
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1])

        if hour < 0 or hour > 23:
            return False, "時刻の時間は0-23の範囲である必要があります"
        if minute < 0 or minute > 59:
            return False, "時刻の分は0-59の範囲である必要があります"
    else:
        # テキスト形式の場合（例: "なるべく早めに出勤"）
        if len(time_str) > 50:
            return False, "出勤時間の説明は50文字以内である必要があります"

    return True, None


def validate_workplace_name(workplace):
    """
    勤務場所名のフォーマットを検証

    Args:
        workplace: 検証する勤務場所名

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not workplace:
        return False, "勤務場所は必須です"

    if len(workplace) > 100:
        return False, "勤務場所名は100文字以内である必要があります"

    # 危険な文字をチェック（<, >, &, ", 'など）
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        if char in workplace:
            return False, f"勤務場所名に使用できない文字が含まれています: {char}"

    return True, None


def validate_employee_name(name):
    """
    従業員名のフォーマットを検証

    Args:
        name: 検証する従業員名

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not name:
        return False, "従業員名は必須です"

    if len(name) > 50:
        return False, "従業員名は50文字以内である必要があります"

    # 最低2文字必要
    if len(name) < 2:
        return False, "従業員名は2文字以上である必要があります"

    return True, None


def validate_line_user_id(line_user_id):
    """
    LINE User IDのフォーマットを検証

    Args:
        line_user_id: 検証するLINE User ID

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not line_user_id:
        return False, "LINE User IDは必須です"

    # LINE User IDは通常U + 32文字の英数字
    pattern = r'^U[0-9a-f]{32}$'
    if not re.match(pattern, line_user_id):
        return False, "無効なLINE User IDフォーマットです"

    return True, None


def validate_employee_type(employee_type):
    """
    従業員種別を検証

    Args:
        employee_type: 検証する従業員種別

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    valid_types = ['part_time', 'full_time']

    if employee_type not in valid_types:
        return False, f"従業員種別は {', '.join(valid_types)} のいずれかである必要があります"

    return True, None


def validate_reply_deadline_time(time_str):
    """
    返信期限時刻のフォーマットを検証

    Args:
        time_str: 検証する時刻文字列（例: "13:00"）

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not time_str:
        return False, "返信期限時刻は必須です"

    # HH:MM形式
    pattern = r'^\d{1,2}:\d{2}$'
    if not re.match(pattern, time_str):
        return False, "返信期限時刻は'HH:MM'の形式である必要があります（例: 13:00）"

    # 有効性をチェック
    parts = time_str.split(':')
    hour = int(parts[0])
    minute = int(parts[1])

    if hour < 0 or hour > 23:
        return False, "時刻の時間は0-23の範囲である必要があります"
    if minute < 0 or minute > 59:
        return False, "時刻の分は0-59の範囲である必要があります"

    return True, None


def sanitize_string(input_str, max_length=None):
    """
    文字列をサニタイズ（危険な文字を除去）

    Args:
        input_str: サニタイズする文字列
        max_length: 最大長（オプション）

    Returns:
        str: サニタイズされた文字列
    """
    if not input_str:
        return ""

    # 基本的なサニタイズ（HTMLタグを除去）
    sanitized = re.sub(r'<[^>]*>', '', input_str)

    # 制御文字を除去
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')

    # 最大長チェック
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def validate_message_template(template):
    """
    メッセージテンプレートを検証

    Args:
        template: 検証するテンプレート

    Returns:
        tuple: (検証成功したか, エラーメッセージ)
    """
    if not template:
        return False, "メッセージテンプレートは必須です"

    if len(template) > 1000:
        return False, "メッセージテンプレートは1000文字以内である必要があります"

    # 必須のプレースホルダーをチェック
    required_placeholders = ['{date}', '{workplace}', '{time}']
    missing_placeholders = [p for p in required_placeholders if p not in template]

    if missing_placeholders:
        return False, f"必須のプレースホルダーが不足しています: {', '.join(missing_placeholders)}"

    return True, None
