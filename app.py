from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from database import (
    init_db, get_all_employees, get_all_workplaces,
    add_employee, update_employee_line_id, add_work_schedule,
    get_recent_schedules, get_employee_by_line_id, add_reply,
    get_schedules_with_reply_status, migrate_database,
    get_part_time_employees, get_full_time_employees,
    update_employee_type, get_setting, update_setting,
    get_notification_managers, add_notification_manager, remove_notification_manager,
    update_work_schedule_reply_status, get_latest_pending_schedule,
    get_available_employee_numbers, get_active_employees, update_employee_active_status,
    get_active_workplaces, add_workplace, update_workplace, delete_workplace,
    get_filtered_schedules, get_schedule_message_content, check_all_replied_today,
    delete_employee_permanent
)
from line_sender import send_bulk_notifications, send_work_notification
from auth import require_auth, login_user, logout_user, change_password, is_authenticated
from notification import send_late_reply_notification, send_all_replied_notification
from sheets_sync import sync_employees_from_sheet
from validators import (
    validate_employee_number, validate_employee_name, validate_employee_type,
    validate_line_user_id, validate_work_date, validate_work_time,
    validate_workplace_name, validate_reply_deadline_time, validate_message_template
)
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

# 🔐 セキュリティ強化: SECRET_KEY必須化
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "❌ CRITICAL: SECRET_KEY environment variable must be set!\n"
        "   Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'\n"
        "   Then add to .env: SECRET_KEY=<generated_key>"
    )
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# 🔐 セキュアなセッション設定
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS必須（開発環境ではFalseに）
app.config['SESSION_COOKIE_HTTPONLY'] = True  # JavaScriptからアクセス不可
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF対策

# 🔐 CSRF保護（Webhookは除外）
csrf = CSRFProtect(app)

# 🔐 レート制限
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# 🔐 セキュリティヘッダー（本番環境のみ）
IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
if IS_PRODUCTION:
    Talisman(app, content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://static.line-scdn.net"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'img-src': ["'self'", "data:", "https:"],
        'connect-src': ["'self'", "https://api.line.me", "https://access.line.me", "https://liffsdk.line-scdn.net"],  # 🔐 LINE API接続を許可
    })

# 🔐 ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)

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
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外
@limiter.limit("20 per minute")  # 🔐 レート制限
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

    # 🔐 入力検証（各通知の内容をチェック）
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


@app.route('/wizard/send', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外
@limiter.limit("20 per minute")  # 🔐 レート制限
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

    # 🔐 入力検証（各通知の内容をチェック）
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


@app.route('/register')
def register_page():
    """LIFF登録画面"""
    return render_template('register.html', liff_id=LIFF_ID)


@app.route('/wizard')
def wizard():
    """ウィザード形式の送信画面"""
    workplaces = get_active_workplaces()
    return render_template('wizard.html', workplaces=workplaces)


@app.route('/employees')
def employees_list():
    """従業員一覧（パスワード認証必要）"""
    # 従業員管理パスワードのチェック
    if not session.get('employee_mgmt_authenticated'):
        return redirect(url_for('employee_login'))

    # is_active >= 0 のみ表示（-1は非表示）
    from database import get_db_connection
    conn = get_db_connection()
    # 従業員番号の数値部分でソート（k00001, k00002, ... の順）
    employees = conn.execute('''
        SELECT * FROM employees
        WHERE is_active >= 0
        ORDER BY CAST(SUBSTR(employee_number, 2) AS INTEGER)
    ''').fetchall()
    conn.close()

    return render_template('employees.html', employees=employees, liff_id=LIFF_ID)


@app.route('/employees/add', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
def add_employee_route():
    """従業員を手動追加（管理用）"""
    # 認証チェック
    if not session.get('employee_mgmt_authenticated'):
        logging.warning(f"Unauthorized employee add attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    data = request.json
    name = data.get('name')
    employee_number = data.get('employee_number')

    if not name or not employee_number:
        return jsonify({'error': '名前と従業員番号は必須です'}), 400

    # 🔐 入力検証
    valid, error_msg = validate_employee_name(name)
    if not valid:
        logging.warning(f"Invalid employee name from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    valid, error_msg = validate_employee_number(employee_number)
    if not valid:
        logging.warning(f"Invalid employee_number from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    employee_id = add_employee(name, employee_number)

    if employee_id:
        logging.info(f"Employee added: {employee_number} from {request.remote_addr}")
        return jsonify({'success': True, 'employee_id': employee_id})
    else:
        logging.warning(f"Failed to add employee: {employee_number} from {request.remote_addr}")
        return jsonify({'error': '従業員の追加に失敗しました（重複の可能性）'}), 400


@app.route('/webhook', methods=['POST'])
@csrf.exempt  # 🔐 LINE WebhookはCSRF除外
@limiter.limit("100 per minute")  # 🔐 レート制限（DoS対策）
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

        # 全員返信チェック
        all_replied, total_count, replied_count = check_all_replied_today()
        if all_replied and total_count > 0:
            # 全員が返信した場合、社員に即時通知
            reply_time = datetime.now().strftime('%H:%M')
            send_all_replied_notification(employee['name'], reply_time)
            print(f"🎉 全員返信完了: {replied_count}/{total_count}人")

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


@app.route('/api/register', methods=['POST'])
@csrf.exempt  # 🔐 LIFF APIはCSRF除外（LIFFから呼ばれる）
@limiter.limit("10 per minute")  # 🔐 レート制限
def register_employee():
    """従業員登録API（LIFFから呼ばれる）"""
    data = request.json

    employee_number = data.get('employee_number')
    employee_name = data.get('employee_name')
    line_user_id = data.get('line_user_id')

    if not employee_number or not line_user_id:
        logging.warning(f"Invalid registration attempt from {request.remote_addr}")
        return jsonify({'error': '従業員番号とLINEユーザーIDは必須です'}), 400

    if not employee_name:
        logging.warning(f"Missing employee name from {request.remote_addr}")
        return jsonify({'error': '氏名は必須です'}), 400

    # 🔐 入力検証
    valid, error_msg = validate_employee_number(employee_number)
    if not valid:
        logging.warning(f"Invalid employee_number format from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    valid, error_msg = validate_employee_name(employee_name)
    if not valid:
        logging.warning(f"Invalid employee_name format from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    valid, error_msg = validate_line_user_id(line_user_id)
    if not valid:
        logging.warning(f"Invalid line_user_id format from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    # LINEユーザーIDを更新（名前確認あり）
    success = update_employee_line_id(employee_number, line_user_id, employee_name)

    if success:
        logging.info(f"Employee registered: {employee_number} ({employee_name}) from {request.remote_addr}")
        return jsonify({'success': True, 'message': '登録が完了しました'})
    else:
        logging.warning(f"Failed registration for employee: {employee_number} ({employee_name}) from {request.remote_addr}")
        return jsonify({'error': '従業員番号または氏名が一致しません'}), 404


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


@app.route('/api/message_template')
def api_message_template():
    """メッセージテンプレート取得API"""
    default_template = """【勤務連絡】

{date}の勤務についてお知らせします。

勤務場所: {workplace}
出勤時間: {time}

上記の内容で出勤をお願いします。
この連絡に返信をお願いします。"""

    template = get_setting('message_template', default_template)
    return jsonify({'template': template})


@app.route('/api/work_schedules')
def api_work_schedules():
    """送信履歴取得API（フィルター対応）"""
    work_date = request.args.get('date')  # YYYY年MM月DD日 形式
    workplace = request.args.get('workplace')

    schedules = get_filtered_schedules(work_date, workplace)
    return jsonify([dict(schedule) for schedule in schedules])


# ========== 認証関連 ==========

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # 🔐 ブルートフォース攻撃対策
def login():
    """ログイン画面"""
    if request.method == 'POST':
        password = request.form.get('password')
        success, message = login_user(password)

        if success:
            flash(message, 'success')
            logging.info(f"Successful login from {request.remote_addr}")
            return redirect(url_for('settings'))
        else:
            flash(message, 'error')
            logging.warning(f"Failed login attempt from {request.remote_addr}")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """ログアウト"""
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))


@app.route('/employees/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # 🔐 ブルートフォース攻撃対策
def employee_login():
    """従業員管理ログイン"""
    if request.method == 'POST':
        password = request.form.get('password')
        stored_hash = get_setting('employee_mgmt_password_hash')

        from database import check_password
        if stored_hash and check_password(password, stored_hash):
            session['employee_mgmt_authenticated'] = True
            logging.info(f"Successful employee management login from {request.remote_addr}")
            return redirect(url_for('employees_list'))
        else:
            flash('パスワードが正しくありません', 'error')
            logging.warning(f"Failed employee management login from {request.remote_addr}")

    return render_template('employee_login.html')


@app.route('/employees/logout')
def employee_logout():
    """従業員管理ログアウト"""
    session.pop('employee_mgmt_authenticated', None)
    flash('従業員管理からログアウトしました', 'info')
    return redirect(url_for('index'))


# ========== 設定管理 ==========

@app.route('/settings')
@require_auth
def settings():
    """設定画面"""
    deadline_time = get_setting('reply_deadline_time', '13:00')

    # デフォルトのメッセージテンプレート
    default_template = """【勤務連絡】

{date}の勤務についてお知らせします。

勤務場所: {workplace}
出勤時間: {time}

上記の内容で出勤をお願いします。
この連絡に返信をお願いします。"""

    message_template = get_setting('message_template', default_template)
    managers = get_notification_managers()
    all_employees = get_all_employees()
    full_time = get_full_time_employees()
    workplaces = get_all_workplaces()

    return render_template(
        'settings.html',
        deadline_time=deadline_time,
        message_template=message_template,
        managers=managers,
        all_employees=all_employees,
        full_time=full_time,
        workplaces=workplaces
    )


@app.route('/settings/deadline', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def update_deadline():
    """返信期限時刻を更新"""
    data = request.json
    new_time = data.get('deadline_time')

    if not new_time:
        return jsonify({'error': '時刻が指定されていません'}), 400

    # 🔐 入力検証
    valid, error_msg = validate_reply_deadline_time(new_time)
    if not valid:
        logging.warning(f"Invalid deadline_time from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    update_setting('reply_deadline_time', new_time)

    # スケジューラーを再セットアップ
    scheduler.stop_scheduler()
    scheduler.setup_scheduler()

    logging.info(f"Deadline updated to {new_time} from {request.remote_addr}")
    return jsonify({'success': True, 'message': f'返信期限を{new_time}に変更しました'})


@app.route('/settings/password', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
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
        logging.info(f"Admin password changed from {request.remote_addr}")
        return jsonify({'success': True, 'message': message})
    else:
        logging.warning(f"Failed admin password change from {request.remote_addr}")
        return jsonify({'error': message}), 400


@app.route('/settings/employee_password', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def update_employee_password():
    """従業員管理パスワードを変更"""
    from database import hash_password, check_password

    data = request.json
    current = data.get('current_password')
    new = data.get('new_password')

    if not current or not new:
        return jsonify({'error': 'パスワードを入力してください'}), 400

    # 現在のパスワードを確認
    stored_hash = get_setting('employee_mgmt_password_hash')
    if not stored_hash or not check_password(current, stored_hash):
        logging.warning(f"Failed employee password change (wrong current password) from {request.remote_addr}")
        return jsonify({'error': '現在のパスワードが正しくありません'}), 400

    # 新しいパスワードをハッシュ化して保存
    new_hash = hash_password(new)
    update_setting('employee_mgmt_password_hash', new_hash)

    logging.info(f"Employee management password changed from {request.remote_addr}")
    return jsonify({'success': True, 'message': '従業員管理パスワードを変更しました'})


@app.route('/settings/managers', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def update_managers():
    """通知先社員を更新（勤務地指定可能）"""
    data = request.json
    employee_id = data.get('employee_id')
    action = data.get('action')  # 'add' or 'remove'
    workplace_id = data.get('workplace_id')  # None の場合は全勤務地向け

    if not employee_id or not action:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    if action == 'add':
        add_notification_manager(employee_id, workplace_id)
        logging.info(f"Notification manager added: employee_id={employee_id} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '通知先に追加しました'})
    elif action == 'remove':
        remove_notification_manager(employee_id)
        logging.info(f"Notification manager removed: employee_id={employee_id} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '通知先から削除しました'})
    else:
        return jsonify({'error': '不正なアクションです'}), 400


@app.route('/settings/message_template', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def update_message_template():
    """送信テンプレートを更新"""
    data = request.json
    template = data.get('template')

    if not template:
        return jsonify({'error': 'テンプレートが指定されていません'}), 400

    # 🔐 入力検証
    valid, error_msg = validate_message_template(template)
    if not valid:
        logging.warning(f"Invalid message template from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    update_setting('message_template', template)
    logging.info(f"Message template updated from {request.remote_addr}")
    return jsonify({'success': True, 'message': 'テンプレートを保存しました'})


@app.route('/settings/message_template/reset', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def reset_message_template():
    """送信テンプレートをデフォルトに戻す"""
    default_template = """【勤務連絡】

{date}の勤務についてお知らせします。

勤務場所: {workplace}
出勤時間: {time}

上記の内容で出勤をお願いします。
この連絡に返信をお願いします。"""

    update_setting('message_template', default_template)
    logging.info(f"Message template reset to default from {request.remote_addr}")
    return jsonify({'success': True, 'message': 'テンプレートをデフォルトに戻しました'})


# ========== 従業員管理 ==========

@app.route('/employees/type', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
def update_employee_type_route():
    """従業員種別を変更（アルバイト⇔社員）"""
    # 認証チェック
    if not session.get('employee_mgmt_authenticated'):
        logging.warning(f"Unauthorized employee type update attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    data = request.json
    employee_id = data.get('employee_id')
    employee_type = data.get('employee_type')  # 'part_time' or 'full_time'

    if not employee_id or not employee_type:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    # 🔐 入力検証
    valid, error_msg = validate_employee_type(employee_type)
    if not valid:
        logging.warning(f"Invalid employee_type from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    success = update_employee_type(employee_id, employee_type)

    if success:
        type_name = 'アルバイト' if employee_type == 'part_time' else '社員'
        logging.info(f"Employee type updated: id={employee_id} to {employee_type} from {request.remote_addr}")
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
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
def update_employee_status():
    """従業員の在籍状況を更新"""
    # 認証チェック
    if not session.get('employee_mgmt_authenticated'):
        logging.warning(f"Unauthorized employee status update attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

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
        logging.info(f"Employee status updated: id={employee_id} to {status_name} from {request.remote_addr}")
        return jsonify({'success': True, 'message': f'ステータスを{status_name}に変更しました'})
    else:
        return jsonify({'error': 'ステータス変更に失敗しました'}), 400


@app.route('/api/verify_password', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
def verify_password():
    """削除用パスワード検証API"""
    # 認証チェック
    if not session.get('employee_mgmt_authenticated'):
        logging.warning(f"Unauthorized password verification attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    from database import check_password

    data = request.json
    password = data.get('password')

    if not password:
        return jsonify({'error': 'パスワードが入力されていません'}), 400

    # 従業員管理パスワードと照合
    stored_hash = get_setting('employee_mgmt_password_hash')

    if stored_hash and check_password(password, stored_hash):
        logging.info(f"Password verification successful from {request.remote_addr}")
        return jsonify({'success': True, 'message': 'パスワードが正しいです'})
    else:
        logging.warning(f"Password verification failed from {request.remote_addr}")
        return jsonify({'success': False, 'error': 'パスワードが正しくありません'}), 401


@app.route('/employees/delete', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
def delete_employee():
    """従業員を物理削除（退職者のみ、関連データも削除）"""
    # 認証チェック
    if not session.get('employee_mgmt_authenticated'):
        logging.warning(f"Unauthorized employee delete attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    from database import get_db_connection

    data = request.json
    employee_id = data.get('employee_id')

    if employee_id is None:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    # 退職者のみ削除可能
    conn = get_db_connection()
    employee = conn.execute('SELECT is_active, employee_number, name FROM employees WHERE id = ?', (employee_id,)).fetchone()
    conn.close()

    if not employee:
        return jsonify({'error': '従業員が見つかりません'}), 404

    if employee['is_active'] == 1:
        return jsonify({'error': '在籍中の従業員は削除できません'}), 400

    # 物理削除（データベースから完全に削除、関連データも削除）
    success = delete_employee_permanent(employee_id)

    if success:
        logging.info(f"Employee permanently deleted: id={employee_id}, number={employee['employee_number']}, name={employee['name']} from {request.remote_addr}")
        return jsonify({'success': True, 'message': f'従業員を完全に削除しました（従業員番号 {employee["employee_number"]} は再利用可能です）'})
    else:
        logging.error(f"Failed to delete employee: id={employee_id} from {request.remote_addr}")
        return jsonify({'error': '削除に失敗しました'}), 400


@app.route('/employees/sync', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
def sync_employees():
    """Googleスプレッドシートから従業員データを同期"""
    # 認証チェック
    if not session.get('employee_mgmt_authenticated'):
        logging.warning(f"Unauthorized employee sync attempt from {request.remote_addr}")
        return jsonify({'error': '認証が必要です'}), 401

    try:
        logging.info(f"Employee sync started from {request.remote_addr}")
        result = sync_employees_from_sheet()

        if result['success']:
            message = f"✅ 同期完了: 新規{result['added']}件、更新{result['updated']}件"
            if result.get('errors'):
                message += f"（エラー{len(result['errors'])}件）"

            logging.info(f"Employee sync completed: added={result['added']}, updated={result['updated']} from {request.remote_addr}")
            return jsonify({
                'success': True,
                'message': message,
                'added': result['added'],
                'updated': result['updated'],
                'total': result['total'],
                'errors': result.get('errors', [])
            })
        else:
            logging.error(f"Employee sync failed from {request.remote_addr}: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '同期に失敗しました')
            }), 400

    except Exception as e:
        logging.error(f"Employee sync error from {request.remote_addr}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'同期エラー: {str(e)}'
        }), 500


# ========== 勤務場所管理 ==========

@app.route('/settings/workplaces/add', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def add_workplace_route():
    """勤務場所を追加"""
    data = request.json
    name = data.get('name')
    sort_order = data.get('sort_order', 999)

    if not name:
        return jsonify({'error': '勤務場所名は必須です'}), 400

    # 🔐 入力検証
    valid, error_msg = validate_workplace_name(name)
    if not valid:
        logging.warning(f"Invalid workplace name from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    workplace_id = add_workplace(name, sort_order)

    if workplace_id:
        logging.info(f"Workplace added: name={name} from {request.remote_addr}")
        return jsonify({'success': True, 'workplace_id': workplace_id, 'message': '勤務場所を追加しました'})
    else:
        logging.warning(f"Failed to add workplace: name={name} from {request.remote_addr}")
        return jsonify({'error': '勤務場所の追加に失敗しました（重複の可能性）'}), 400


@app.route('/settings/workplaces/update', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def update_workplace_route():
    """勤務場所を更新"""
    data = request.json
    workplace_id = data.get('workplace_id')
    name = data.get('name')
    sort_order = data.get('sort_order')

    if not workplace_id or not name or sort_order is None:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    # 🔐 入力検証
    valid, error_msg = validate_workplace_name(name)
    if not valid:
        logging.warning(f"Invalid workplace name for update from {request.remote_addr}: {error_msg}")
        return jsonify({'error': error_msg}), 400

    success = update_workplace(workplace_id, name, sort_order)

    if success:
        logging.info(f"Workplace updated: id={workplace_id}, name={name} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '勤務場所を更新しました'})
    else:
        return jsonify({'error': '勤務場所の更新に失敗しました'}), 400


@app.route('/settings/workplaces/delete', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
@require_auth
def delete_workplace_route():
    """勤務場所を削除（物理削除）"""
    data = request.json
    workplace_id = data.get('workplace_id')

    if not workplace_id:
        return jsonify({'error': 'パラメータが不足しています'}), 400

    success = delete_workplace(workplace_id)

    if success:
        logging.info(f"Workplace deleted: id={workplace_id} from {request.remote_addr}")
        return jsonify({'success': True, 'message': '勤務場所を完全に削除しました'})
    else:
        return jsonify({'error': '勤務場所の削除に失敗しました'}), 400


# ========== テスト用エンドポイント ==========

@app.route('/test/check_deadline', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
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


@app.route('/test/check_deadline_plus_1', methods=['POST'])
@csrf.exempt  # 🔐 JavaScript APIはCSRF除外（本番環境ではCSRFトークン実装推奨）
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


if __name__ == '__main__':
    print("🚀 アプリケーションを起動します...")
    print(f"📍 http://127.0.0.1:5001 でアクセスできます")

    # 🔐 セキュリティ: デバッグモードは開発環境のみ
    DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    if DEBUG_MODE:
        print("⚠️  WARNING: デバッグモードで起動中（本番環境では無効化してください）")

    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=5001)
