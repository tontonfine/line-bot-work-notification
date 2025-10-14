from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import (
    init_db, get_all_employees, get_all_workplaces,
    add_employee, update_employee_line_id, add_work_schedule,
    get_recent_schedules, get_employee_by_line_id, add_reply,
    get_schedules_with_reply_status, migrate_database,
    get_part_time_employees, get_full_time_employees,
    update_employee_type, get_setting, update_setting,
    get_notification_managers, add_notification_manager, remove_notification_manager,
    update_work_schedule_reply_status, get_latest_pending_schedule,
    get_available_employee_numbers, get_active_employees, update_employee_active_status
)
from line_sender import send_bulk_notifications
from auth import require_auth, login_user, logout_user, change_password, is_authenticated
from notification import send_late_reply_notification
import scheduler

# 環境変数読み込み
load_dotenv()

def check_environment_variables():
    """必須環境変数の存在をチェック"""
    required_vars = {
        'LINE_CHANNEL_ACCESS_TOKEN': 'LINE Channel Access Token',
        'LINE_CHANNEL_SECRET': 'LINE Channel Secret',
        'LIFF_ID': 'LIFF ID'
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var} ({description})")

    if missing_vars:
        print("❌ 必須環境変数が設定されていません:")
        print("\n".join(missing_vars))
        print("\n.envファイルを確認してください。")
        return False

    print("✅ 環境変数チェック完了")
    return True

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LIFF_ID = os.getenv('LIFF_ID')

# 環境変数チェック
if not check_environment_variables():
    print("⚠️ 警告: 環境変数が不足していますが、アプリケーションを起動します")
    print("LINE機能は正常に動作しない可能性があります\n")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# データベース初期化とマイグレーション
init_db()
migrate_database()

# スケジューラー初期化
scheduler.setup_scheduler()
print("✅ スケジューラーセットアップ完了")


@app.route('/')
def index():
    """メイン画面（送信管理画面）"""
    employees = get_all_employees()
    workplaces = get_all_workplaces()
    recent_schedules = get_schedules_with_reply_status(20)
    return render_template(
        'index.html',
        employees=employees,
        workplaces=workplaces,
        recent_schedules=recent_schedules,
        liff_id=LIFF_ID
    )


@app.route('/send', methods=['POST'])
def send_notifications():
    """勤務連絡を一斉送信（履歴保存あり）"""
    data = request.json

    # 送信データの検証
    if not data or 'notifications' not in data:
        return jsonify({'error': '送信データが不正です'}), 400

    notifications = data['notifications']
    if not notifications:
        return jsonify({'error': '送信対象が選択されていません'}), 400

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
                    work_time=notification['work_time']
                )
                recorded_count += 1

    return jsonify({
        'success': True,
        'sent_count': results['success'],
        'failed_count': results['failed'],
        'recorded_count': recorded_count,
        'message': f'{results["success"]}件送信しました（DB記録: {recorded_count}件）'
    })


@app.route('/wizard/send', methods=['POST'])
def wizard_send_notifications():
    """ウィザード専用送信（履歴保存なし）"""
    data = request.json

    # 送信データの検証
    if not data or 'notifications' not in data:
        return jsonify({'error': '送信データが不正です'}), 400

    notifications = data['notifications']
    if not notifications:
        return jsonify({'error': '送信対象が選択されていません'}), 400

    # 送信実行（データベース記録なし）
    results = send_bulk_notifications(notifications)

    return jsonify({
        'success': True,
        'sent_count': results['success'],
        'failed_count': results['failed'],
        'message': f'{results["success"]}件送信しました（履歴には保存されません）'
    })


@app.route('/register')
def register_page():
    """LIFF登録画面"""
    return render_template('register.html', liff_id=LIFF_ID)


@app.route('/wizard')
def wizard():
    """ウィザード形式の送信画面"""
    workplaces = get_all_workplaces()
    return render_template('wizard.html', workplaces=workplaces)


@app.route('/employees')
def employees_list():
    """従業員一覧"""
    employees = get_all_employees()
    return render_template('employees.html', employees=employees)


@app.route('/employees/add', methods=['POST'])
def add_employee_route():
    """従業員を手動追加（管理用）"""
    data = request.json
    name = data.get('name')
    employee_number = data.get('employee_number')

    if not name or not employee_number:
        return jsonify({'error': '名前と従業員番号は必須です'}), 400

    employee_id = add_employee(name, employee_number)

    if employee_id:
        return jsonify({'success': True, 'employee_id': employee_id})
    else:
        return jsonify({'error': '従業員の追加に失敗しました（重複の可能性）'}), 400


@app.route('/webhook', methods=['POST'])
def webhook():
    """LINE Webhook（LIFF登録用）"""
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400

    return 'OK'


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
                    TextSendMessage(text=f"返信を承りました。ありがとうございます。")
                )
            except LineBotApiError as e:
                print(f"❌ 返信エラー: {e}")
            return

        # 返信期限時刻を取得
        deadline_time = get_setting('reply_deadline_time', '13:00')
        deadline_hour, deadline_minute = map(int, deadline_time.split(':'))

        # 現在時刻と比較
        now = datetime.now()
        deadline = now.replace(hour=deadline_hour, minute=deadline_minute, second=0, microsecond=0)
        is_late = now > deadline

        # 返信を記録（scheduleと紐付け）
        add_reply(employee['id'], message_text, schedule['id'])

        if is_late:
            # 遅延返信 - 即座に社員に通知
            print(f"⏰ 遅延返信: {employee['name']} - {message_text}")
            send_late_reply_notification(employee['name'], message_text)
            # reply_statusを'late_replied'に更新
            update_work_schedule_reply_status(schedule['id'], 'late_replied')
        else:
            # 通常返信
            print(f"✅ 返信を記録: {employee['name']} - {message_text}")
            # reply_statusを'replied'に更新
            update_work_schedule_reply_status(schedule['id'], 'replied')

        # 確認メッセージを返信
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"返信を承りました。ありがとうございます。")
            )
        except LineBotApiError as e:
            print(f"❌ 返信エラー: {e}")
    else:
        print(f"⚠️ 未登録のユーザーからのメッセージ: {line_user_id}")


@app.route('/api/register', methods=['POST'])
def register_employee():
    """従業員登録API（LIFFから呼ばれる）"""
    data = request.json

    employee_number = data.get('employee_number')
    line_user_id = data.get('line_user_id')

    if not employee_number or not line_user_id:
        return jsonify({'error': '従業員番号とLINEユーザーIDは必須です'}), 400

    # LINEユーザーIDを更新
    success = update_employee_line_id(employee_number, line_user_id)

    if success:
        return jsonify({'success': True, 'message': '登録が完了しました'})
    else:
        return jsonify({'error': '従業員番号が見つかりません'}), 404


@app.route('/api/employees')
def api_employees():
    """従業員一覧API"""
    employees = get_all_employees()
    return jsonify([dict(emp) for emp in employees])


@app.route('/api/workplaces')
def api_workplaces():
    """勤務場所一覧API"""
    workplaces = get_all_workplaces()
    return jsonify([dict(wp) for wp in workplaces])


# ========== 認証関連 ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン画面"""
    if request.method == 'POST':
        password = request.form.get('password')
        success, message = login_user(password)

        if success:
            flash(message, 'success')
            return redirect(url_for('settings'))
        else:
            flash(message, 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """ログアウト"""
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))


# ========== 設定管理 ==========

@app.route('/settings')
@require_auth
def settings():
    """設定画面"""
    deadline_time = get_setting('reply_deadline_time', '13:00')
    managers = get_notification_managers()
    all_employees = get_all_employees()
    full_time = get_full_time_employees()

    return render_template(
        'settings.html',
        deadline_time=deadline_time,
        managers=managers,
        all_employees=all_employees,
        full_time=full_time
    )


@app.route('/settings/deadline', methods=['POST'])
@require_auth
def update_deadline():
    """返信期限時刻を更新"""
    data = request.json
    new_time = data.get('deadline_time')

    if not new_time:
        return jsonify({'error': '時刻が指定されていません'}), 400

    update_setting('reply_deadline_time', new_time)

    # スケジューラーを再セットアップ
    scheduler.stop_scheduler()
    scheduler.setup_scheduler()

    return jsonify({'success': True, 'message': f'返信期限を{new_time}に変更しました'})


@app.route('/settings/password', methods=['POST'])
@require_auth
def update_password():
    """パスワードを変更"""
    data = request.json
    current = data.get('current_password')
    new = data.get('new_password')

    if not current or not new:
        return jsonify({'error': 'パスワードを入力してください'}), 400

    success, message = change_password(current, new)

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 400


@app.route('/settings/managers', methods=['POST'])
@require_auth
def update_managers():
    """通知先社員を更新"""
    data = request.json
    employee_id = data.get('employee_id')
    action = data.get('action')  # 'add' or 'remove'

    if not employee_id or not action:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    if action == 'add':
        add_notification_manager(employee_id)
        return jsonify({'success': True, 'message': '通知先に追加しました'})
    elif action == 'remove':
        remove_notification_manager(employee_id)
        return jsonify({'success': True, 'message': '通知先から削除しました'})
    else:
        return jsonify({'error': '不正なアクションです'}), 400


# ========== 従業員管理 ==========

@app.route('/employees/type', methods=['POST'])
@require_auth
def update_employee_type_route():
    """従業員種別を変更（アルバイト⇔社員）"""
    data = request.json
    employee_id = data.get('employee_id')
    employee_type = data.get('employee_type')  # 'part_time' or 'full_time'

    if not employee_id or not employee_type:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    if employee_type not in ['part_time', 'full_time']:
        return jsonify({'error': '不正な従業員種別です'}), 400

    success = update_employee_type(employee_id, employee_type)

    if success:
        type_name = 'アルバイト' if employee_type == 'part_time' else '社員'
        return jsonify({'success': True, 'message': f'{type_name}に変更しました'})
    else:
        return jsonify({'error': '従業員種別の変更に失敗しました'}), 400


@app.route('/api/part_time_employees')
def api_part_time_employees():
    """アルバイト従業員一覧API"""
    employees = get_part_time_employees()
    return jsonify([dict(emp) for emp in employees])


@app.route('/api/full_time_employees')
def api_full_time_employees():
    """社員一覧API"""
    employees = get_full_time_employees()
    return jsonify([dict(emp) for emp in employees])


@app.route('/api/available_employee_numbers')
def api_available_employee_numbers():
    """使用可能な従業員番号を取得"""
    limit = request.args.get('limit', 10, type=int)
    available_numbers = get_available_employee_numbers(limit)
    return jsonify(available_numbers)


@app.route('/employees/status', methods=['POST'])
def update_employee_status():
    """従業員の在籍状況を更新"""
    data = request.json
    employee_id = data.get('employee_id')
    is_active = data.get('is_active')  # 1 or 0

    if employee_id is None or is_active is None:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    if is_active not in [0, 1]:
        return jsonify({'error': '不正なステータスです'}), 400

    success = update_employee_active_status(employee_id, is_active)

    if success:
        status_name = '在籍' if is_active == 1 else '退職'
        return jsonify({'success': True, 'message': f'ステータスを{status_name}に変更しました'})
    else:
        return jsonify({'error': 'ステータス変更に失敗しました'}), 400


if __name__ == '__main__':
    print("🚀 アプリケーションを起動します...")
    print(f"📍 http://127.0.0.1:5001 でアクセスできます")
    app.run(debug=True, host='0.0.0.0', port=5001)
