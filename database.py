import sqlite3
from datetime import datetime
import os
import hashlib

DB_PATH = 'database.db'

def hash_password(password):
    """パスワードをSHA256でハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, password_hash):
    """パスワードを検証"""
    return hash_password(password) == password_hash

def init_db():
    """データベースを初期化"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 従業員テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            employee_number TEXT UNIQUE NOT NULL,
            line_user_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 勤務場所マスタテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workplaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            sort_order INTEGER DEFAULT 0
        )
    ''')

    # 勤務予定・送信履歴テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            workplace TEXT NOT NULL,
            work_time TEXT NOT NULL,
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # 返信テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            schedule_id INTEGER,
            message_text TEXT NOT NULL,
            replied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id),
            FOREIGN KEY (schedule_id) REFERENCES work_schedules (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ データベース初期化完了")

def migrate_database():
    """データベースをv2スキーマにマイグレーション"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. employees テーブルに employee_type カラムを追加
        cursor.execute("PRAGMA table_info(employees)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'employee_type' not in columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN employee_type TEXT DEFAULT 'part_time'")
            print("✅ employees.employee_type カラム追加")

        # 2. work_schedules テーブルに追跡カラムを追加
        cursor.execute("PRAGMA table_info(work_schedules)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'reply_status' not in columns:
            cursor.execute("ALTER TABLE work_schedules ADD COLUMN reply_status TEXT DEFAULT 'pending'")
            print("✅ work_schedules.reply_status カラム追加")

        if 'first_reminder_sent_at' not in columns:
            cursor.execute("ALTER TABLE work_schedules ADD COLUMN first_reminder_sent_at TIMESTAMP")
            print("✅ work_schedules.first_reminder_sent_at カラム追加")

        if 'second_reminder_sent_at' not in columns:
            cursor.execute("ALTER TABLE work_schedules ADD COLUMN second_reminder_sent_at TIMESTAMP")
            print("✅ work_schedules.second_reminder_sent_at カラム追加")

        # 3. replies テーブルに is_late_reply フラグを追加
        cursor.execute("PRAGMA table_info(replies)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'is_late_reply' not in columns:
            cursor.execute("ALTER TABLE replies ADD COLUMN is_late_reply BOOLEAN DEFAULT 0")
            print("✅ replies.is_late_reply カラム追加")

        # 4. system_settings テーブル作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ system_settings テーブル作成")

        # 初期設定値の投入
        cursor.execute("SELECT COUNT(*) FROM system_settings WHERE setting_key='reply_deadline_time'")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
                ('reply_deadline_time', '13:00')
            )
            print("✅ 初期設定: reply_deadline_time = 13:00")

        cursor.execute("SELECT COUNT(*) FROM system_settings WHERE setting_key='admin_password_hash'")
        if cursor.fetchone()[0] == 0:
            initial_password_hash = hash_password('kyoshoran')
            cursor.execute(
                "INSERT INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
                ('admin_password_hash', initial_password_hash)
            )
            print("✅ 初期設定: admin_password_hash (パスワード: kyoshoran)")

        # 5. notification_managers テーブル作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        ''')
        print("✅ notification_managers テーブル作成")

        # 6. notifications テーブル作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_type TEXT NOT NULL,
                recipient_id INTEGER NOT NULL,
                schedule_id INTEGER,
                message TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipient_id) REFERENCES employees (id),
                FOREIGN KEY (schedule_id) REFERENCES work_schedules (id)
            )
        ''')
        print("✅ notifications テーブル作成")

        conn.commit()
        print("🎉 マイグレーション完了")

    except Exception as e:
        conn.rollback()
        print(f"❌ マイグレーションエラー: {e}")
        raise
    finally:
        conn.close()

def get_db_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 従業員関連の関数
def add_employee(name, employee_number, line_user_id=None):
    """従業員を追加"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO employees (name, employee_number, line_user_id) VALUES (?, ?, ?)',
            (name, employee_number, line_user_id)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        print(f"❌ 従業員追加エラー: {e}")
        return None
    finally:
        conn.close()

def get_all_employees():
    """全従業員を取得"""
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employees ORDER BY name').fetchall()
    conn.close()
    return employees

def get_employee_by_line_id(line_user_id):
    """LINEユーザーIDから従業員を取得"""
    conn = get_db_connection()
    employee = conn.execute(
        'SELECT * FROM employees WHERE line_user_id = ?',
        (line_user_id,)
    ).fetchone()
    conn.close()
    return employee

def update_employee_line_id(employee_number, line_user_id):
    """従業員のLINEユーザーIDを更新"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE employees SET line_user_id = ? WHERE employee_number = ?',
        (line_user_id, employee_number)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

# 勤務場所関連の関数
def add_workplace(name, sort_order=0):
    """勤務場所を追加"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO workplaces (name, sort_order) VALUES (?, ?)',
            (name, sort_order)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_all_workplaces():
    """全勤務場所を取得"""
    conn = get_db_connection()
    workplaces = conn.execute(
        'SELECT * FROM workplaces ORDER BY sort_order, name'
    ).fetchall()
    conn.close()
    return workplaces

# 勤務予定関連の関数
def add_work_schedule(employee_id, work_date, workplace, work_time):
    """勤務予定を追加"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO work_schedules
           (employee_id, work_date, workplace, work_time, sent_at)
           VALUES (?, ?, ?, ?, ?)''',
        (employee_id, work_date, workplace, work_time, datetime.now())
    )
    conn.commit()
    schedule_id = cursor.lastrowid
    conn.close()
    return schedule_id

def get_recent_schedules(limit=50):
    """最近の送信履歴を取得"""
    conn = get_db_connection()
    schedules = conn.execute(
        '''SELECT ws.*, e.name as employee_name
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           ORDER BY ws.sent_at DESC
           LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return schedules

# 返信関連の関数
def add_reply(employee_id, message_text, schedule_id=None):
    """返信を記録"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO replies (employee_id, message_text, schedule_id)
           VALUES (?, ?, ?)''',
        (employee_id, message_text, schedule_id)
    )
    conn.commit()
    reply_id = cursor.lastrowid
    conn.close()
    return reply_id

def get_replies_by_employee(employee_id, limit=10):
    """従業員の返信履歴を取得"""
    conn = get_db_connection()
    replies = conn.execute(
        '''SELECT r.*, e.name as employee_name
           FROM replies r
           JOIN employees e ON r.employee_id = e.id
           WHERE r.employee_id = ?
           ORDER BY r.replied_at DESC
           LIMIT ?''',
        (employee_id, limit)
    ).fetchall()
    conn.close()
    return replies

def get_recent_replies(limit=50):
    """最近の返信を取得"""
    conn = get_db_connection()
    replies = conn.execute(
        '''SELECT r.*, e.name as employee_name
           FROM replies r
           JOIN employees e ON r.employee_id = e.id
           ORDER BY r.replied_at DESC
           LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return replies

def get_schedules_with_reply_status(limit=50):
    """送信履歴と返信状況を取得"""
    conn = get_db_connection()
    schedules = conn.execute(
        '''SELECT
               ws.*,
               e.name as employee_name,
               r.id as reply_id,
               r.message_text as reply_text,
               r.replied_at
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           LEFT JOIN replies r ON r.id = (
               SELECT id FROM replies
               WHERE employee_id = ws.employee_id
                 AND replied_at >= ws.sent_at
               ORDER BY replied_at ASC
               LIMIT 1
           )
           ORDER BY ws.sent_at DESC
           LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return schedules

# 設定管理関数
def get_setting(key, default=None):
    """設定値を取得"""
    conn = get_db_connection()
    row = conn.execute(
        'SELECT setting_value FROM system_settings WHERE setting_key = ?',
        (key,)
    ).fetchone()
    conn.close()
    return row['setting_value'] if row else default

def update_setting(key, value):
    """設定値を更新"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO system_settings (setting_key, setting_value, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(setting_key) DO UPDATE SET
               setting_value = excluded.setting_value,
               updated_at = excluded.updated_at''',
        (key, value, datetime.now())
    )
    conn.commit()
    conn.close()

# 通知先管理関数
def get_notification_managers():
    """通知先社員を取得"""
    conn = get_db_connection()
    managers = conn.execute(
        '''SELECT e.id, e.name, e.line_user_id, nm.is_active
           FROM notification_managers nm
           JOIN employees e ON nm.employee_id = e.id
           WHERE nm.is_active = 1 AND e.employee_type = 'full_time'
           ORDER BY e.name'''
    ).fetchall()
    conn.close()
    return managers

def add_notification_manager(employee_id):
    """通知先社員を追加"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO notification_managers (employee_id) VALUES (?)',
        (employee_id,)
    )
    conn.commit()
    conn.close()

def remove_notification_manager(employee_id):
    """通知先社員を削除"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE notification_managers SET is_active = 0 WHERE employee_id = ?',
        (employee_id,)
    )
    conn.commit()
    conn.close()

# 従業員種別管理関数
def update_employee_type(employee_id, employee_type):
    """従業員種別を更新"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE employees SET employee_type = ? WHERE id = ?',
        (employee_type, employee_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_part_time_employees():
    """アルバイト従業員のみ取得"""
    conn = get_db_connection()
    employees = conn.execute(
        "SELECT * FROM employees WHERE employee_type = 'part_time' ORDER BY name"
    ).fetchall()
    conn.close()
    return employees

def get_full_time_employees():
    """社員のみ取得"""
    conn = get_db_connection()
    employees = conn.execute(
        "SELECT * FROM employees WHERE employee_type = 'full_time' ORDER BY name"
    ).fetchall()
    conn.close()
    return employees

# work_schedules 更新関数
def update_work_schedule_reply_status(schedule_id, status):
    """勤務予定の返信状況を更新"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE work_schedules SET reply_status = ? WHERE id = ?',
        (status, schedule_id)
    )
    conn.commit()
    conn.close()

def update_first_reminder_sent(schedule_id):
    """1回目のリマインダー送信時刻を記録"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE work_schedules SET first_reminder_sent_at = ? WHERE id = ?',
        (datetime.now(), schedule_id)
    )
    conn.commit()
    conn.close()

def update_second_reminder_sent(schedule_id):
    """2回目のリマインダー送信時刻を記録"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE work_schedules SET second_reminder_sent_at = ? WHERE id = ?',
        (datetime.now(), schedule_id)
    )
    conn.commit()
    conn.close()

def get_schedules_by_date(work_date):
    """指定日の勤務予定を取得（送信日ベース）"""
    conn = get_db_connection()
    schedules = conn.execute(
        '''SELECT ws.*, e.name as employee_name, e.line_user_id
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           WHERE DATE(ws.sent_at) = ?
           ORDER BY ws.sent_at DESC''',
        (work_date,)
    ).fetchall()
    conn.close()
    return schedules

def get_latest_pending_schedule(employee_id):
    """従業員の最新の未返信勤務予定を取得"""
    conn = get_db_connection()
    schedule = conn.execute(
        '''SELECT * FROM work_schedules
           WHERE employee_id = ? AND reply_status = 'pending'
           ORDER BY sent_at DESC LIMIT 1''',
        (employee_id,)
    ).fetchone()
    conn.close()
    return schedule

def get_today_schedules_by_reply_status():
    """本日送信分の勤務予定を返信状況別に取得"""
    conn = get_db_connection()
    today = str(datetime.now().date())
    schedules = conn.execute(
        '''SELECT ws.*, e.name as employee_name, e.line_user_id
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           WHERE DATE(ws.sent_at) = ?
           ORDER BY ws.sent_at DESC''',
        (today,)
    ).fetchall()
    conn.close()
    return schedules

def get_available_employee_numbers(limit=10):
    """使用可能な従業員番号を取得（k00000形式）"""
    conn = get_db_connection()

    # 既存の従業員番号を取得（k形式のみ）
    existing = conn.execute(
        "SELECT employee_number FROM employees WHERE employee_number LIKE 'k%'"
    ).fetchall()
    conn.close()

    # 既存番号を数値に変換
    used_numbers = set()
    for row in existing:
        try:
            num_part = row['employee_number'][1:]  # 'k'を除去
            used_numbers.add(int(num_part))
        except (ValueError, IndexError):
            continue

    # 使用可能な番号を生成（最小の空き番号から）
    available = []
    for i in range(100000):  # k00000 から k99999 まで
        if i not in used_numbers:
            available.append(f'k{i:05d}')
            if len(available) >= limit:
                break

    return available

if __name__ == '__main__':
    # データベース初期化
    init_db()

    # サンプルデータを投入（初回のみ）
    if not get_all_workplaces():
        print("📝 サンプルデータを投入中...")
        add_workplace('東京オフィス', 1)
        add_workplace('大阪オフィス', 2)
        add_workplace('名古屋オフィス', 3)
        add_workplace('福岡オフィス', 4)
        add_workplace('在宅勤務', 5)
        print("✅ サンプル勤務場所を追加しました")
