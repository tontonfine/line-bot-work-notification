import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import hashlib
import bcrypt
import secrets

# データベースパス: 環境変数で指定可能（Render永続ディスク対応）
# Renderの場合: DATABASE_PATH=/opt/render/project/data/database.db
# ローカル開発: デフォルトで ./database.db
DB_PATH = os.getenv('DATABASE_PATH', 'database.db')

# データベースディレクトリが存在しない場合は作成
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
    print(f"📁 データベースディレクトリを作成しました: {db_dir}")

def hash_password(password):
    """パスワードをbcryptでハッシュ化（強力な暗号化）"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, password_hash):
    """パスワードを検証（bcryptとSHA256の両方をサポート - 後方互換性）"""
    try:
        # bcryptハッシュかどうか確認（$2b$で始まる）
        if password_hash.startswith('$2b$') or password_hash.startswith('$2a$') or password_hash.startswith('$2y$'):
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        else:
            # 旧SHA256ハッシュの場合（後方互換性のため）
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            return sha256_hash == password_hash
    except Exception as e:
        print(f"パスワード検証エラー: {e}")
        return False

def generate_secure_password(length=16):
    """安全なランダムパスワードを生成"""
    return secrets.token_urlsafe(length)

def get_db_connection():
    """
    データベース接続を取得（マルチワーカー対応）
    - WALモード有効化: 読み取りと書き込みの競合を削減
    - タイムアウト30秒: ロック待機時間を延長
    - ジャーナルモード: WAL (Write-Ahead Logging)
    """
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30.0,  # 30秒待機（デフォルトは5秒）
        check_same_thread=False  # マルチスレッド対応
    )
    # 行を辞書形式でアクセス可能に
    conn.row_factory = sqlite3.Row
    # WALモード有効化（高い同時実行性）
    conn.execute('PRAGMA journal_mode=WAL')
    # 同期モードをNORMALに（パフォーマンス向上）
    conn.execute('PRAGMA synchronous=NORMAL')
    # 一時ファイルをメモリに保存
    conn.execute('PRAGMA temp_store=MEMORY')
    return conn

def init_db():
    """データベースを初期化"""
    conn = get_db_connection()
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
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. employees テーブルに employee_type カラムを追加
        cursor.execute("PRAGMA table_info(employees)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'employee_type' not in columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN employee_type TEXT DEFAULT 'part_time'")
            print("✅ employees.employee_type カラム追加")

        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN is_active INTEGER DEFAULT 1")
            print("✅ employees.is_active カラム追加")

        # 1-2. workplaces テーブルに is_active カラムを追加
        cursor.execute("PRAGMA table_info(workplaces)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE workplaces ADD COLUMN is_active INTEGER DEFAULT 1")
            print("✅ workplaces.is_active カラム追加")

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

        if 'message_content' not in columns:
            cursor.execute("ALTER TABLE work_schedules ADD COLUMN message_content TEXT")
            print("✅ work_schedules.message_content カラム追加")

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

        # 固定パスワードに強制更新（既存の場合も上書き）
        admin_password = "kyoshoran"
        initial_password_hash = hash_password(admin_password)
        cursor.execute(
            "INSERT OR REPLACE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
            ('admin_password_hash', initial_password_hash)
        )
        print("\n" + "="*70)
        print("🔐 トップページアクセス用パスワードを設定しました")
        print("="*70)
        print(f"   基本パスワード: kyoshoran")
        print("   用途: トップページ（送信画面）へのログイン")
        print("="*70 + "\n")

        # 固定パスワードに強制更新（既存の場合も上書き）
        employee_mgmt_password = "owneradmin"
        employee_mgmt_hash = hash_password(employee_mgmt_password)
        cursor.execute(
            "INSERT OR REPLACE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
            ('employee_mgmt_password_hash', employee_mgmt_hash)
        )
        print("="*70)
        print("🔐 管理者ページアクセス用パスワードを設定しました")
        print("="*70)
        print(f"   管理者パスワード: owneradmin")
        print("   用途: 従業員管理・設定画面へのログイン")
        print("="*70 + "\n")

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

        # 5-2. notification_managers に workplace_id カラムを追加
        cursor.execute("PRAGMA table_info(notification_managers)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'workplace_id' not in columns:
            cursor.execute("ALTER TABLE notification_managers ADD COLUMN workplace_id INTEGER")
            print("✅ notification_managers.workplace_id カラム追加")
            # 既存データはNULLのままにする（全勤務地向けとして扱う）

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

# 従業員関連の関数
def add_employee(name, employee_number, line_user_id=None, employee_type='part_time'):
    """従業員を追加"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO employees (name, employee_number, line_user_id, employee_type) VALUES (?, ?, ?, ?)',
            (name, employee_number, line_user_id, employee_type)
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

def update_employee_line_id(employee_number, line_user_id, employee_name=None):
    """従業員のLINEユーザーIDを更新（大文字小文字を区別しない、名前確認あり）

    UNIQUE制約対応: 同じLINE IDが既に別の従業員に割り当てられている場合、
    古い割り当てをクリアしてから新しい従業員に割り当てる（トランザクション安全）

    Args:
        employee_number: 従業員番号
        line_user_id: LINEユーザーID
        employee_name: 従業員名（オプション、名前確認用）

    Returns:
        tuple: (成功フラグ, エラーメッセージまたはNone)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # トランザクション開始
        conn.execute('BEGIN IMMEDIATE')

        # 1. 対象従業員が存在するか確認（名前確認あり）
        if employee_name:
            employee_name_no_space = employee_name.replace(' ', '').replace('　', '')
            cursor.execute(
                '''SELECT id, name, employee_number FROM employees
                   WHERE LOWER(employee_number) = LOWER(?)
                   AND REPLACE(REPLACE(name, ' ', ''), '　', '') = ?''',
                (employee_number, employee_name_no_space)
            )
        else:
            cursor.execute(
                'SELECT id, name, employee_number FROM employees WHERE LOWER(employee_number) = LOWER(?)',
                (employee_number,)
            )

        target_employee = cursor.fetchone()
        if not target_employee:
            conn.rollback()
            conn.close()
            return (False, '従業員番号または氏名が一致しません')

        target_employee_id = target_employee[0]

        # 2. 同じLINE IDが既に別の従業員に割り当てられているかチェック
        cursor.execute(
            'SELECT id, name, employee_number FROM employees WHERE line_user_id = ? AND id != ?',
            (line_user_id, target_employee_id)
        )
        existing_employee = cursor.fetchone()

        if existing_employee:
            # 既に割り当てられている → 古い割り当てをクリア
            old_employee_id = existing_employee[0]
            old_employee_name = existing_employee[1]
            old_employee_number = existing_employee[2]

            cursor.execute(
                'UPDATE employees SET line_user_id = NULL WHERE id = ?',
                (old_employee_id,)
            )
            print(f"🔄 LINE ID再割り当て: {old_employee_number}({old_employee_name})から解除")

        # 3. 新しい従業員にLINE IDを割り当て
        cursor.execute(
            'UPDATE employees SET line_user_id = ? WHERE id = ?',
            (line_user_id, target_employee_id)
        )

        # トランザクションコミット
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        if affected > 0:
            return (True, None)
        else:
            return (False, '更新に失敗しました')

    except sqlite3.IntegrityError as e:
        # UNIQUE制約違反などのデータベースエラー
        conn.rollback()
        conn.close()
        error_msg = f'データベースエラー: {str(e)}'
        print(f"❌ IntegrityError: {error_msg}")
        return (False, error_msg)

    except Exception as e:
        # その他の予期しないエラー
        conn.rollback()
        conn.close()
        error_msg = f'予期しないエラー: {str(e)}'
        print(f"❌ Exception: {error_msg}")
        return (False, error_msg)

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

def get_active_workplaces():
    """有効な勤務場所のみ取得"""
    conn = get_db_connection()
    workplaces = conn.execute(
        'SELECT * FROM workplaces WHERE is_active = 1 ORDER BY sort_order, name'
    ).fetchall()
    conn.close()
    return workplaces

def update_workplace(workplace_id, name, sort_order):
    """勤務場所を更新"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE workplaces SET name = ?, sort_order = ? WHERE id = ?',
            (name, sort_order, workplace_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_workplace(workplace_id):
    """勤務場所を削除（物理削除）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM workplaces WHERE id = ?',
        (workplace_id,)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

# 勤務予定関連の関数
def add_work_schedule(employee_id, work_date, workplace, work_time, message_content=None):
    """勤務予定を追加"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO work_schedules
           (employee_id, work_date, workplace, work_time, sent_at, message_content)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (employee_id, work_date, workplace, work_time, datetime.now(ZoneInfo('Asia/Tokyo')), message_content)
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

def get_filtered_schedules(work_date=None, workplace=None, limit=100):
    """送信履歴をフィルタリングして取得（日付・勤務地）"""
    conn = get_db_connection()

    query = '''SELECT
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
           WHERE 1=1'''

    params = []

    if work_date:
        query += ' AND ws.work_date = ?'
        params.append(work_date)

    if workplace:
        query += ' AND ws.workplace = ?'
        params.append(workplace)

    query += ' ORDER BY ws.sent_at DESC LIMIT ?'
    params.append(limit)

    schedules = conn.execute(query, tuple(params)).fetchall()
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
        (key, value, datetime.now(ZoneInfo('Asia/Tokyo')))
    )
    conn.commit()
    conn.close()

# 通知先管理関数
def get_notification_managers():
    """通知先社員を取得（勤務地情報付き）"""
    conn = get_db_connection()
    managers = conn.execute(
        '''SELECT e.id, e.name, e.line_user_id, nm.is_active, nm.workplace_id,
                  w.name as workplace_name
           FROM notification_managers nm
           JOIN employees e ON nm.employee_id = e.id
           LEFT JOIN workplaces w ON nm.workplace_id = w.id
           WHERE nm.is_active = 1 AND e.employee_type = 'full_time'
           ORDER BY nm.workplace_id, e.name'''
    ).fetchall()
    conn.close()
    return managers

def get_notification_managers_for_workplace(workplace_name):
    """特定の勤務地の通知先社員を取得"""
    conn = get_db_connection()
    managers = conn.execute(
        '''SELECT e.id, e.name, e.line_user_id
           FROM notification_managers nm
           JOIN employees e ON nm.employee_id = e.id
           LEFT JOIN workplaces w ON nm.workplace_id = w.id
           WHERE nm.is_active = 1
             AND e.employee_type = 'full_time'
             AND (nm.workplace_id IS NULL OR w.name = ?)
           ORDER BY e.name''',
        (workplace_name,)
    ).fetchall()
    conn.close()
    return managers

def add_notification_manager(employee_id, workplace_id=None):
    """通知先社員を追加（勤務地指定可能）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO notification_managers (employee_id, workplace_id) VALUES (?, ?)',
        (employee_id, workplace_id)
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
    """アルバイト従業員のみ取得（在籍中のみ）"""
    conn = get_db_connection()
    employees = conn.execute(
        "SELECT * FROM employees WHERE employee_type = 'part_time' AND is_active = 1 ORDER BY name"
    ).fetchall()
    conn.close()
    return employees

def get_full_time_employees():
    """社員のみ取得（在籍中のみ）"""
    conn = get_db_connection()
    employees = conn.execute(
        "SELECT * FROM employees WHERE employee_type = 'full_time' AND is_active = 1 ORDER BY name"
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
        (datetime.now(ZoneInfo('Asia/Tokyo')), schedule_id)
    )
    conn.commit()
    conn.close()

def update_second_reminder_sent(schedule_id):
    """2回目のリマインダー送信時刻を記録"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE work_schedules SET second_reminder_sent_at = ? WHERE id = ?',
        (datetime.now(ZoneInfo('Asia/Tokyo')), schedule_id)
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

def get_schedule_message_content(schedule_id):
    """勤務予定のメッセージ内容を取得"""
    conn = get_db_connection()
    schedule = conn.execute(
        'SELECT message_content FROM work_schedules WHERE id = ?',
        (schedule_id,)
    ).fetchone()
    conn.close()
    return schedule['message_content'] if schedule else None

def get_today_schedules_by_reply_status():
    """本日送信分の勤務予定を返信状況別に取得"""
    conn = get_db_connection()
    today = str(datetime.now(ZoneInfo('Asia/Tokyo')).date())
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

def get_active_employees():
    """在籍中の従業員のみ取得"""
    conn = get_db_connection()
    employees = conn.execute(
        'SELECT * FROM employees WHERE is_active = 1 ORDER BY name'
    ).fetchall()
    conn.close()
    return employees

def update_employee_active_status(employee_id, is_active):
    """従業員の在籍状況を更新"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE employees SET is_active = ? WHERE id = ?',
        (is_active, employee_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def delete_employee_permanent(employee_id):
    """従業員を物理削除（関連データも削除）

    Args:
        employee_id: 削除する従業員ID

    Returns:
        bool: 削除成功時True

    Note:
        - 関連する勤務予定(work_schedules)も削除
        - 関連する返信(replies)も削除
        - 関連する通知先設定(notification_managers)も削除
        - トランザクションで安全に削除
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # トランザクション開始
        cursor.execute('BEGIN TRANSACTION')

        # 1. 関連する返信を削除
        cursor.execute('DELETE FROM replies WHERE employee_id = ?', (employee_id,))

        # 2. 関連する勤務予定を削除
        cursor.execute('DELETE FROM work_schedules WHERE employee_id = ?', (employee_id,))

        # 3. 関連する通知先設定を削除
        cursor.execute('DELETE FROM notification_managers WHERE employee_id = ?', (employee_id,))

        # 4. 従業員を削除
        cursor.execute('DELETE FROM employees WHERE id = ?', (employee_id,))

        affected = cursor.rowcount

        # コミット
        conn.commit()
        return affected > 0

    except Exception as e:
        # エラー時はロールバック
        conn.rollback()
        print(f"❌ 従業員削除エラー: {e}")
        return False
    finally:
        conn.close()

def check_all_replied_today():
    """本日送信分の勤務連絡に全員が返信済みかチェック

    Returns:
        tuple: (all_replied: bool, total_count: int, replied_count: int)
    """
    conn = get_db_connection()
    today = str(datetime.now(ZoneInfo('Asia/Tokyo')).date())

    # 本日送信した全勤務予定を取得
    all_schedules = conn.execute(
        '''SELECT ws.id, ws.reply_status, e.name as employee_name
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           WHERE DATE(ws.sent_at) = ?''',
        (today,)
    ).fetchall()

    conn.close()

    if not all_schedules:
        # 本日の送信がない場合
        return False, 0, 0

    total_count = len(all_schedules)
    replied_count = sum(1 for s in all_schedules if s['reply_status'] in ['replied', 'late_replied'])

    all_replied = (replied_count == total_count)

    return all_replied, total_count, replied_count

def get_today_all_replies_with_time():
    """本日送信分の全返信情報を時刻順に取得

    Returns:
        list: [{'employee_name': str, 'replied_at': str}, ...]
    """
    conn = get_db_connection()
    today = str(datetime.now(ZoneInfo('Asia/Tokyo')).date())

    # 本日送信した勤務予定とその返信情報を取得
    replies = conn.execute(
        '''SELECT e.name as employee_name, r.replied_at
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           LEFT JOIN replies r ON r.schedule_id = ws.id
           WHERE DATE(ws.sent_at) = ?
             AND ws.reply_status IN ('replied', 'late_replied')
           ORDER BY r.replied_at ASC''',
        (today,)
    ).fetchall()

    conn.close()
    return replies

def get_today_pending_employees():
    """本日送信分の未返信者リストを取得

    Returns:
        list: [{'employee_name': str}, ...]
    """
    conn = get_db_connection()
    today = str(datetime.now(ZoneInfo('Asia/Tokyo')).date())

    # 本日送信した勤務予定で未返信の従業員を取得
    pending = conn.execute(
        '''SELECT e.name as employee_name
           FROM work_schedules ws
           JOIN employees e ON ws.employee_id = e.id
           WHERE DATE(ws.sent_at) = ?
             AND ws.reply_status = 'pending'
           ORDER BY e.name''',
        (today,)
    ).fetchall()

    conn.close()
    return pending

def check_all_replied_notification_sent_today():
    """本日既に全員返信完了通知を送信済みかチェック

    Returns:
        bool: 本日既に通知済みの場合True
    """
    today = str(datetime.now(ZoneInfo('Asia/Tokyo')).date())
    notification_date = get_setting('all_replied_notification_sent_date')
    return notification_date == today

def mark_all_replied_notification_sent():
    """全員返信完了通知を送信済みとして記録"""
    today = str(datetime.now(ZoneInfo('Asia/Tokyo')).date())
    update_setting('all_replied_notification_sent_date', today)

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
