# LINE Bot 勤務連絡システム - 完全リファクタリング仕様書

## 📋 概要

**作成日**: 2025-10-27
**総工数**: 90時間（6週間）
**変更総数**: 43件
**目標**: コード品質とメンテナンス性の5倍改善

### 期待される成果

| 指標 | 現状 | 目標 | 改善率 |
|------|------|------|--------|
| テストカバレッジ | 0% | 85% | ∞ |
| app.py サイズ | 1,155行 | 200行 | 83%削減 |
| 新機能開発時間 | 4-6時間 | 1-2時間 | 66%短縮 |
| バグ修正時間 | 2-3時間 | 30-60分 | 75%短縮 |
| 開発者オンボーディング | 2週間 | 3-5日 | 70%短縮 |
| コードレビュー時間 | ベースライン | -60% | 60%短縮 |

---

## 🗺️ 全体アーキテクチャ

### 現在の構造（モノリシック）
```
app.py (1,155行, 54ルート)
  ├─ 全ビジネスロジック混在
  ├─ 直接データベース操作
  └─ ルート、ロジック、データアクセスが密結合

database.py (1,004行, 47+関数)
  ├─ すべてのデータベース操作
  ├─ 抽象化レイヤーなし
  └─ God Object パターン
```

### 目標の構造（レイヤードアーキテクチャ）
```
┌─────────────────────────────────────┐
│   Templates (Jinja2)                │  プレゼンテーション層
├─────────────────────────────────────┤
│   Routes (Flask Blueprints)         │  ルート層（薄いコントローラー）
│   - auth, employees, schedules      │
│   - webhooks, settings, liff        │
├─────────────────────────────────────┤
│   Services (Business Logic)         │  サービス層（ビジネスロジック）
│   - EmployeeService                 │
│   - WorkScheduleService             │
│   - NotificationService             │
├─────────────────────────────────────┤
│   Repositories (Data Access)        │  リポジトリ層（データアクセス）
│   - EmployeeRepository              │
│   - WorkScheduleRepository          │
│   - NotificationRepository          │
├─────────────────────────────────────┤
│   Database (SQLite + WAL)           │  データ層
└─────────────────────────────────────┘
```

---

## 📅 実装スケジュール

### Week 1: 基礎構築
- **Day 1-2**: Phase 0 (Quick Wins) - 2時間
- **Day 3-5**: Phase 1 (Testing Foundation) - 12時間

### Week 2-3: データ層
- **Week 2**: Phase 2 (Repository Pattern) - 14時間

### Week 3-4: ビジネスロジック層
- **Week 3-4**: Phase 3 (Service Layer) - 16時間

### Week 5: ルート層リファクタリング
- **Week 5**: Phase 4 (Blueprint Splitting) - 20時間 ⚠️ **最高リスク**

### Week 6: テストと文書化
- **Day 1-3**: Phase 5 (Comprehensive Testing) - 18時間
- **Day 4-5**: Phase 6 (Cleanup & Documentation) - 8時間

---

## Phase 0: Quick Wins (2時間)

**リスクレベル**: 🟢 VERY LOW
**ロールバック時間**: 1分

### Change 0.1: requirements-dev.txt 作成 (5分)

**ファイル**: `requirements-dev.txt`

```text
pytest==7.4.0
pytest-cov==4.1.0
pytest-flask==1.2.0
black==23.7.0
flake8==6.1.0
mypy==1.5.0
```

**実行**:
```bash
touch requirements-dev.txt
# 上記内容を記述
pip install -r requirements-dev.txt
```

**検証**:
```bash
pytest --version  # pytest 7.4.0
mypy --version    # mypy 1.5.0
```

---

### Change 0.2: config.py 作成 (30分)

**ファイル**: `config.py`

```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    """アプリケーション設定"""

    # Database
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'database.db')
    DATABASE_TIMEOUT: int = int(os.getenv('DATABASE_TIMEOUT', '30'))

    # LINE Bot
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET: str = os.getenv('LINE_CHANNEL_SECRET')

    # Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY')
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'

    # Application
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5001'))

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = 'json'  # json or text

config = Config()
```

**検証**:
```bash
python3 -c "from config import config; print(config.DATABASE_PATH)"
# 出力: database.db
```

---

### Change 0.3: database.py に型ヒント追加 (1時間)

**ファイル**: `database.py`

**変更前**:
```python
def update_employee_line_id(employee_number, line_user_id, employee_name=None):
    """従業員のLINEユーザーIDを更新"""
    # ...
```

**変更後**:
```python
from typing import Optional, List, Dict, Tuple, Any

def update_employee_line_id(
    employee_number: str,
    line_user_id: str,
    employee_name: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """従業員のLINEユーザーIDを更新

    Args:
        employee_number: 従業員番号 (K001形式)
        line_user_id: LINEユーザーID
        employee_name: 従業員名（オプション）

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    # ...
```

**対象**: database.py の全47+関数

**検証**:
```bash
mypy database.py
# 出力: Success: no issues found
```

---

### Change 0.4: notification.py のログ標準化 (30分)

**ファイル**: `notification.py`

**変更**: すべての `print()` を `logger.info()` または `logger.error()` に置き換え

**変更前**:
```python
print("✅ 全員返信完了を通知しました")
print(f"❌ {manager['name']}への通知失敗: {e}")
```

**変更後**:
```python
logger.info("全員返信完了を通知しました")
logger.error(f"{manager['name']}への通知失敗: {e}")
```

**検証**: ログファイルに構造化ログが出力されることを確認

---

### Change 0.5: .gitignore 更新 (5分)

**ファイル**: `.gitignore`

**追加**:
```
# Testing
.pytest_cache/
htmlcov/
.coverage
*.cover

# Type checking
.mypy_cache/

# Logs
logs/
*.log

# Development
.vscode/
.idea/
```

**検証**:
```bash
git status  # 不要なファイルが表示されないこと
```

---

### Phase 0 検証チェックリスト

- [ ] `pip install -r requirements-dev.txt` が成功
- [ ] `python3 -c "from config import config; print(config.DATABASE_PATH)"` が動作
- [ ] `mypy database.py` がエラーなし
- [ ] ログファイルに構造化ログが出力される
- [ ] `git status` が不要なファイルを表示しない

### Phase 0 ロールバック手順

```bash
# Step 1: 新規ファイルを削除
rm requirements-dev.txt config.py

# Step 2: 変更ファイルを復元
git checkout database.py notification.py .gitignore

# Step 3: 確認
git status  # クリーンな状態
```

---

## Phase 1: Testing Foundation (12時間)

**リスクレベル**: 🟢 LOW
**ロールバック時間**: 2分

### Change 1.1: pytest環境セットアップ (2時間)

**ファイル**: `tests/conftest.py`

```python
import pytest
import tempfile
import os
from app import app as flask_app
from database import init_db

@pytest.fixture
def app():
    """テスト用のFlaskアプリ"""
    db_fd, db_path = tempfile.mkstemp()

    flask_app.config['TESTING'] = True
    flask_app.config['DATABASE'] = db_path

    with flask_app.app_context():
        init_db()

    yield flask_app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLIランナー"""
    return app.test_cli_runner()
```

**検証**:
```bash
pytest --collect-only  # テストが発見される
```

---

### Change 1.2: characterization tests 作成 (6時間)

**ファイル**: `tests/test_characterization.py`

```python
"""
既存機能の動作を保証するキャラクタリゼーションテスト
リファクタリング前に既存の動作を記録する
"""
import pytest
from database import (
    update_employee_line_id,
    get_notification_managers,
    check_all_replied_today,
    get_today_all_replies_with_time
)

def test_update_employee_line_id_success(app):
    """従業員LINE ID更新が成功すること"""
    with app.app_context():
        success, error = update_employee_line_id('K001', 'U123456', '山田太郎')
        assert success is True
        assert error is None

def test_update_employee_line_id_name_mismatch(app):
    """従業員名が一致しない場合エラーになること"""
    with app.app_context():
        success, error = update_employee_line_id('K001', 'U123456', '間違った名前')
        assert success is False
        assert '一致しません' in error

def test_get_notification_managers(app):
    """通知先社員リストが取得できること"""
    with app.app_context():
        managers = get_notification_managers()
        assert isinstance(managers, list)
        for manager in managers:
            assert 'id' in manager
            assert 'name' in manager
            assert 'line_user_id' in manager

def test_check_all_replied_today(app):
    """本日の全員返信チェックが動作すること"""
    with app.app_context():
        all_replied, total, replied = check_all_replied_today()
        assert isinstance(all_replied, bool)
        assert total >= 0
        assert replied >= 0
        assert replied <= total

# ... 全主要機能に対してテストを作成（約30-40テスト）
```

**検証**:
```bash
pytest tests/test_characterization.py -v
# すべてのテストが PASSED
```

---

### Change 1.3: logging_config.py 作成 (2時間)

**ファイル**: `logging_config.py`

```python
import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
from config import config

class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(app):
    """ログ設定をセットアップ"""

    # ログディレクトリ作成
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # ファイルハンドラ（JSON形式）
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # コンソールハンドラ（テキスト形式）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    root_logger.addHandler(console_handler)

    app.logger.info('Logging configured successfully')
```

**検証**:
```bash
ls logs/app.log  # ログファイルが作成される
cat logs/app.log | head -1 | python3 -m json.tool  # 有効なJSON
```

---

### Change 1.4: app.py にログ適用 (2時間)

**ファイル**: `app.py`

**追加**:
```python
import logging
from logging_config import setup_logging

logger = logging.getLogger(__name__)

# アプリ初期化後
setup_logging(app)
```

**変更**: 全 `print()` を `logger.info()` または `logger.error()` に置き換え

**検証**:
```bash
python3 app.py
# logs/app.log にJSON形式のログが出力される
```

---

### Phase 1 検証チェックリスト

- [ ] `pytest --version` が正しいバージョンを表示
- [ ] `pytest --collect-only` がテストを発見
- [ ] `pytest tests/test_characterization.py -v` がすべて PASSED
- [ ] `pytest --cov` がカバレッジレポートを生成
- [ ] `ls logs/app.log` が存在
- [ ] ログがJSON形式で出力される

### Phase 1 ロールバック手順

```bash
# Step 1: テストディレクトリ削除
rm -rf tests/ .pytest_cache/ htmlcov/

# Step 2: ログ設定削除
rm logging_config.py

# Step 3: app.py復元
git checkout app.py

# 時間: 2分
```

---

## Phase 2: Data Layer - Repository Pattern (14時間)

**リスクレベル**: 🟡 MEDIUM
**ロールバック時間**: 1分

### Change 2.1: app/repositories/__init__.py 作成 (5分)

**ファイル**: `app/repositories/__init__.py`

```python
from .employee_repository import EmployeeRepository
from .work_schedule_repository import WorkScheduleRepository
from .notification_repository import NotificationRepository

__all__ = ['EmployeeRepository', 'WorkScheduleRepository', 'NotificationRepository']
```

---

### Change 2.2: app/repositories/base_repository.py 作成 (30分)

**ファイル**: `app/repositories/base_repository.py`

```python
from typing import Dict, List, Optional
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    """ベースリポジトリクラス"""

    def _get_connection(self):
        """データベース接続を取得"""
        return get_db_connection()

    def _execute_query(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """単一行を返すクエリを実行"""
        conn = self._get_connection()
        try:
            result = conn.execute(query, params).fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Query failed: {query[:50]}... - {e}")
            raise
        finally:
            conn.close()

    def _execute_query_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """複数行を返すクエリを実行"""
        conn = self._get_connection()
        try:
            results = conn.execute(query, params).fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Query failed: {query[:50]}... - {e}")
            raise
        finally:
            conn.close()

    def _execute_write(self, query: str, params: tuple = ()) -> int:
        """書き込みクエリを実行（INSERT/UPDATE/DELETE）"""
        conn = self._get_connection()
        try:
            conn.execute('BEGIN IMMEDIATE')
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"Write failed: {query[:50]}... - {e}")
            raise
        finally:
            conn.close()
```

**検証**:
```bash
python3 -c "from app.repositories.base_repository import BaseRepository"
# エラーなし
```

---

### Change 2.3: app/repositories/employee_repository.py 作成 (2時間)

**ファイル**: `app/repositories/employee_repository.py`

```python
from typing import List, Optional, Dict
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class EmployeeRepository(BaseRepository):
    """従業員データアクセスリポジトリ"""

    def find_by_id(self, employee_id: int) -> Optional[Dict]:
        """IDから従業員を取得"""
        return self._execute_query(
            'SELECT * FROM employees WHERE id = ?',
            (employee_id,)
        )

    def find_by_employee_number(self, employee_number: str) -> Optional[Dict]:
        """従業員番号から従業員を取得（大文字小文字区別なし）"""
        return self._execute_query(
            'SELECT * FROM employees WHERE LOWER(employee_number) = LOWER(?)',
            (employee_number,)
        )

    def find_all_active(self) -> List[Dict]:
        """有効な従業員全員を取得"""
        return self._execute_query_all(
            'SELECT * FROM employees WHERE is_deleted = 0 ORDER BY employee_number'
        )

    def find_by_line_user_id(self, line_user_id: str) -> Optional[Dict]:
        """LINE IDから従業員を取得"""
        return self._execute_query(
            'SELECT * FROM employees WHERE line_user_id = ?',
            (line_user_id,)
        )

    def update_line_id(
        self,
        employee_number: str,
        line_user_id: str,
        employee_name: Optional[str] = None
    ) -> None:
        """LINE IDを更新"""
        if employee_name:
            self._execute_write(
                '''UPDATE employees
                   SET line_user_id = ?, name = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE LOWER(employee_number) = LOWER(?)''',
                (line_user_id, employee_name, employee_number)
            )
        else:
            self._execute_write(
                '''UPDATE employees
                   SET line_user_id = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE LOWER(employee_number) = LOWER(?)''',
                (line_user_id, employee_number)
            )
        logger.info(f"Updated LINE ID for employee: {employee_number}")

    def create(
        self,
        employee_number: str,
        name: str,
        line_user_id: Optional[str] = None
    ) -> int:
        """新規従業員作成"""
        employee_id = self._execute_write(
            'INSERT INTO employees (employee_number, name, line_user_id) VALUES (?, ?, ?)',
            (employee_number, name, line_user_id)
        )
        logger.info(f"Created employee: {employee_number} (ID: {employee_id})")
        return employee_id

    def update(
        self,
        employee_id: int,
        employee_number: str,
        name: str
    ) -> None:
        """従業員情報更新"""
        self._execute_write(
            '''UPDATE employees
               SET employee_number = ?, name = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (employee_number, name, employee_id)
        )
        logger.info(f"Updated employee: {employee_id}")

    def soft_delete(self, employee_id: int) -> None:
        """論理削除"""
        self._execute_write(
            'UPDATE employees SET is_deleted = 1 WHERE id = ?',
            (employee_id,)
        )
        logger.info(f"Soft deleted employee: {employee_id}")

    def hard_delete(self, employee_id: int) -> None:
        """物理削除（番号再利用のため）"""
        self._execute_write(
            'DELETE FROM employees WHERE id = ?',
            (employee_id,)
        )
        logger.info(f"Hard deleted employee: {employee_id}")
```

**検証**:
```bash
python3 -c "from app.repositories import EmployeeRepository; repo = EmployeeRepository()"
# エラーなし
```

---

### Change 2.4: app/repositories/work_schedule_repository.py 作成 (3時間)

**ファイル**: `app/repositories/work_schedule_repository.py`

```python
from typing import List, Optional, Dict
from datetime import date
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class WorkScheduleRepository(BaseRepository):
    """勤務連絡データアクセスリポジトリ"""

    def find_by_id(self, schedule_id: int) -> Optional[Dict]:
        """IDから勤務連絡を取得"""
        return self._execute_query(
            '''SELECT ws.*, e.name as employee_name, e.employee_number
               FROM work_schedules ws
               JOIN employees e ON ws.employee_id = e.id
               WHERE ws.id = ?''',
            (schedule_id,)
        )

    def find_today_schedules(self) -> List[Dict]:
        """本日の勤務連絡を取得"""
        today = str(date.today())
        return self._execute_query_all(
            '''SELECT ws.*, e.name as employee_name, e.employee_number
               FROM work_schedules ws
               JOIN employees e ON ws.employee_id = e.id
               WHERE DATE(ws.sent_at) = ?
               ORDER BY ws.sent_at DESC''',
            (today,)
        )

    def find_not_replied_today(self) -> List[Dict]:
        """本日の未返信を取得"""
        today = str(date.today())
        return self._execute_query_all(
            '''SELECT ws.*, e.name as employee_name, e.employee_number
               FROM work_schedules ws
               JOIN employees e ON ws.employee_id = e.id
               WHERE DATE(ws.sent_at) = ? AND ws.reply_status = 'pending'
               ORDER BY ws.sent_at''',
            (today,)
        )

    def find_replied_today(self) -> List[Dict]:
        """本日の返信済みを取得"""
        today = str(date.today())
        return self._execute_query_all(
            '''SELECT ws.*, e.name as employee_name, e.employee_number
               FROM work_schedules ws
               JOIN employees e ON ws.employee_id = e.id
               WHERE DATE(ws.sent_at) = ? AND ws.reply_status = 'replied'
               ORDER BY ws.replied_at''',
            (today,)
        )

    def create(
        self,
        employee_id: int,
        message: str,
        work_date: str,
        work_time: Optional[str]
    ) -> int:
        """勤務連絡作成"""
        schedule_id = self._execute_write(
            '''INSERT INTO work_schedules
               (employee_id, message, work_date, work_time, reply_status, sent_at)
               VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)''',
            (employee_id, message, work_date, work_time)
        )
        logger.info(f"Created work schedule: {schedule_id} for employee: {employee_id}")
        return schedule_id

    def update_reply_status(
        self,
        schedule_id: int,
        reply_status: str,
        reply_message: Optional[str] = None
    ) -> None:
        """返信ステータス更新"""
        self._execute_write(
            '''UPDATE work_schedules
               SET reply_status = ?, reply_message = ?, replied_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (reply_status, reply_message, schedule_id)
        )
        logger.info(f"Updated reply status: {schedule_id} -> {reply_status}")

    def increment_reminder_count(self, schedule_id: int) -> None:
        """リマインダー送信回数をインクリメント"""
        self._execute_write(
            '''UPDATE work_schedules
               SET reminder_count = reminder_count + 1
               WHERE id = ?''',
            (schedule_id,)
        )
```

---

### Change 2.5: app/repositories/notification_repository.py 作成 (2時間)

**ファイル**: `app/repositories/notification_repository.py`

```python
from typing import List, Dict
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class NotificationRepository(BaseRepository):
    """通知データアクセスリポジトリ"""

    def create(
        self,
        notification_type: str,
        recipient_id: int,
        schedule_id: Optional[int],
        message: str
    ) -> int:
        """通知履歴を記録"""
        notification_id = self._execute_write(
            '''INSERT INTO notifications
               (notification_type, recipient_id, schedule_id, message)
               VALUES (?, ?, ?, ?)''',
            (notification_type, recipient_id, schedule_id, message)
        )
        logger.info(f"Recorded notification: {notification_type} for recipient: {recipient_id}")
        return notification_id

    def find_by_schedule_id(self, schedule_id: int) -> List[Dict]:
        """特定勤務連絡の通知履歴を取得"""
        return self._execute_query_all(
            '''SELECT * FROM notifications
               WHERE schedule_id = ?
               ORDER BY created_at DESC''',
            (schedule_id,)
        )

    def find_recent(self, limit: int = 100) -> List[Dict]:
        """最近の通知履歴を取得"""
        return self._execute_query_all(
            '''SELECT n.*, e.name as recipient_name
               FROM notifications n
               LEFT JOIN employees e ON n.recipient_id = e.id
               ORDER BY n.created_at DESC
               LIMIT ?''',
            (limit,)
        )
```

---

### Change 2.6: tests/test_repositories.py 作成 (6時間)

**ファイル**: `tests/test_repositories.py`

```python
import pytest
from app.repositories import EmployeeRepository, WorkScheduleRepository, NotificationRepository

class TestEmployeeRepository:
    """従業員リポジトリテスト"""

    def test_find_by_id(self, app):
        """IDで従業員を取得できること"""
        with app.app_context():
            repo = EmployeeRepository()

            # テストデータ作成
            employee_id = repo.create('K999', 'テスト太郎')

            # 取得
            employee = repo.find_by_id(employee_id)

            assert employee is not None
            assert employee['employee_number'] == 'K999'
            assert employee['name'] == 'テスト太郎'

    def test_find_by_employee_number_case_insensitive(self, app):
        """従業員番号で取得（大文字小文字区別なし）"""
        with app.app_context():
            repo = EmployeeRepository()

            # 大文字で作成
            repo.create('K999', 'テスト太郎')

            # 小文字で検索
            employee = repo.find_by_employee_number('k999')

            assert employee is not None
            assert employee['employee_number'] == 'K999'

    def test_update_line_id(self, app):
        """LINE ID更新ができること"""
        with app.app_context():
            repo = EmployeeRepository()

            employee_id = repo.create('K999', 'テスト太郎')
            repo.update_line_id('K999', 'U123456')

            employee = repo.find_by_id(employee_id)
            assert employee['line_user_id'] == 'U123456'

    def test_soft_delete(self, app):
        """論理削除ができること"""
        with app.app_context():
            repo = EmployeeRepository()

            employee_id = repo.create('K999', 'テスト太郎')
            repo.soft_delete(employee_id)

            # find_all_activeには含まれない
            active_employees = repo.find_all_active()
            assert not any(e['id'] == employee_id for e in active_employees)

            # find_by_idでは取得できる（is_deleted=1）
            employee = repo.find_by_id(employee_id)
            assert employee['is_deleted'] == 1

class TestWorkScheduleRepository:
    """勤務連絡リポジトリテスト"""

    def test_create_and_find(self, app):
        """勤務連絡の作成と取得"""
        with app.app_context():
            emp_repo = EmployeeRepository()
            ws_repo = WorkScheduleRepository()

            employee_id = emp_repo.create('K999', 'テスト太郎', 'U123456')
            schedule_id = ws_repo.create(employee_id, 'テストメッセージ', '2024-01-15', '13:00')

            schedule = ws_repo.find_by_id(schedule_id)
            assert schedule is not None
            assert schedule['message'] == 'テストメッセージ'
            assert schedule['employee_name'] == 'テスト太郎'

    def test_update_reply_status(self, app):
        """返信ステータス更新"""
        with app.app_context():
            emp_repo = EmployeeRepository()
            ws_repo = WorkScheduleRepository()

            employee_id = emp_repo.create('K999', 'テスト太郎', 'U123456')
            schedule_id = ws_repo.create(employee_id, 'テストメッセージ', '2024-01-15', '13:00')

            ws_repo.update_reply_status(schedule_id, 'replied', '出勤します')

            schedule = ws_repo.find_by_id(schedule_id)
            assert schedule['reply_status'] == 'replied'
            assert schedule['reply_message'] == '出勤します'
            assert schedule['replied_at'] is not None

# ... 全リポジトリメソッドに対してテスト作成（約40-50テスト）
```

**検証**:
```bash
pytest tests/test_repositories.py -v
pytest tests/test_repositories.py --cov=app.repositories
# Coverage: ≥95%
```

---

### Phase 2 検証チェックリスト

- [ ] `python3 -c "from app.repositories import EmployeeRepository"` が成功
- [ ] BaseRepository の単体テストがすべてPASS
- [ ] EmployeeRepository のすべてのCRUD操作がテスト済み
- [ ] WorkScheduleRepository のすべての操作がテスト済み
- [ ] NotificationRepository のすべての操作がテスト済み
- [ ] `pytest tests/test_repositories.py --cov=app.repositories` で ≥95% カバレッジ

### Phase 2 ロールバック手順

```bash
# Step 1: リポジトリ層削除
rm -rf app/repositories/

# Step 2: リポジトリテスト削除
rm tests/test_repositories.py

# Step 3: データベース確認（変更なし）
sqlite3 database.db "SELECT name FROM sqlite_master WHERE type='table';"

# 時間: 1分
# データ損失リスク: なし
```

---

## Phase 3: Service Layer - Business Logic (16時間)

**リスクレベル**: 🟡 MEDIUM
**ロールバック時間**: 3分

### Change 3.1: app/services/__init__.py 作成 (5分)

**ファイル**: `app/services/__init__.py`

```python
from .employee_service import EmployeeService
from .work_schedule_service import WorkScheduleService
from .notification_service import NotificationService

__all__ = ['EmployeeService', 'WorkScheduleService', 'NotificationService']
```

---

### Change 3.2: app/services/employee_service.py 作成 (3時間)

**ファイル**: `app/services/employee_service.py`

```python
from typing import Optional, List, Dict, Tuple
from app.repositories.employee_repository import EmployeeRepository
import logging

logger = logging.getLogger(__name__)

class EmployeeService:
    """従業員ビジネスロジック"""

    def __init__(self):
        self.repo = EmployeeRepository()

    def get_employee_by_number(self, employee_number: str) -> Optional[Dict]:
        """従業員番号から従業員を取得"""
        try:
            return self.repo.find_by_employee_number(employee_number)
        except Exception as e:
            logger.error(f"Failed to get employee {employee_number}: {e}")
            raise

    def get_employee_by_line_id(self, line_user_id: str) -> Optional[Dict]:
        """LINE IDから従業員を取得"""
        try:
            return self.repo.find_by_line_user_id(line_user_id)
        except Exception as e:
            logger.error(f"Failed to get employee by LINE ID: {e}")
            raise

    def register_line_user(
        self,
        employee_number: str,
        line_user_id: str,
        employee_name: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """LINE登録処理

        Returns:
            (success: bool, error_message: Optional[str])
        """
        try:
            # 従業員の存在確認
            employee = self.repo.find_by_employee_number(employee_number)
            if not employee:
                return (False, "従業員番号が見つかりません")

            # 名前確認（指定された場合）
            if employee_name and employee['name'] != employee_name:
                return (False, "従業員名が一致しません")

            # 既に別のLINEアカウントに紐付いている場合
            if employee['line_user_id'] and employee['line_user_id'] != line_user_id:
                return (False, "この従業員番号は既に別のLINEアカウントに登録されています")

            # LINE ID更新
            self.repo.update_line_id(employee_number, line_user_id, employee_name)
            logger.info(f"LINE registration successful: {employee_number}")
            return (True, None)

        except Exception as e:
            logger.error(f"LINE registration failed: {e}")
            return (False, f"登録処理でエラーが発生しました: {str(e)}")

    def list_all_employees(self) -> List[Dict]:
        """全従業員リストを取得"""
        try:
            return self.repo.find_all_active()
        except Exception as e:
            logger.error(f"Failed to list employees: {e}")
            raise

    def create_employee(
        self,
        employee_number: str,
        name: str
    ) -> Tuple[bool, Optional[str]]:
        """新規従業員作成

        Returns:
            (success: bool, error_message: Optional[str])
        """
        try:
            # 重複チェック
            existing = self.repo.find_by_employee_number(employee_number)
            if existing:
                return (False, "この従業員番号は既に存在します")

            employee_id = self.repo.create(employee_number, name)
            logger.info(f"Employee created: {employee_number} (ID: {employee_id})")
            return (True, None)

        except Exception as e:
            logger.error(f"Failed to create employee: {e}")
            return (False, f"作成処理でエラーが発生しました: {str(e)}")

    def update_employee(
        self,
        employee_id: int,
        employee_number: str,
        name: str
    ) -> Tuple[bool, Optional[str]]:
        """従業員情報更新"""
        try:
            # 存在確認
            employee = self.repo.find_by_id(employee_id)
            if not employee:
                return (False, "従業員が見つかりません")

            # 番号重複チェック（自分以外）
            existing = self.repo.find_by_employee_number(employee_number)
            if existing and existing['id'] != employee_id:
                return (False, "この従業員番号は既に使用されています")

            self.repo.update(employee_id, employee_number, name)
            logger.info(f"Employee updated: {employee_id}")
            return (True, None)

        except Exception as e:
            logger.error(f"Failed to update employee: {e}")
            return (False, str(e))

    def soft_delete_employee(self, employee_id: int) -> Tuple[bool, Optional[str]]:
        """従業員を論理削除"""
        try:
            self.repo.soft_delete(employee_id)
            logger.info(f"Employee soft deleted: {employee_id}")
            return (True, None)
        except Exception as e:
            logger.error(f"Failed to soft delete employee: {e}")
            return (False, str(e))

    def hard_delete_employee(self, employee_id: int) -> Tuple[bool, Optional[str]]:
        """従業員を物理削除（番号再利用のため）"""
        try:
            self.repo.hard_delete(employee_id)
            logger.info(f"Employee hard deleted: {employee_id}")
            return (True, None)
        except Exception as e:
            logger.error(f"Failed to hard delete employee: {e}")
            return (False, str(e))
```

---

### Change 3.3: app/services/work_schedule_service.py 作成 (4時間)

**ファイル**: `app/services/work_schedule_service.py`

```python
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
from app.repositories.work_schedule_repository import WorkScheduleRepository
from app.repositories.employee_repository import EmployeeRepository
from line_sender import send_work_schedule_message
import logging

logger = logging.getLogger(__name__)

class WorkScheduleService:
    """勤務連絡ビジネスロジック"""

    def __init__(self):
        self.ws_repo = WorkScheduleRepository()
        self.emp_repo = EmployeeRepository()

    def send_work_schedule(
        self,
        employee_number: str,
        work_time: str,
        work_date: Optional[str] = None
    ) -> Dict:
        """勤務連絡を送信

        Returns:
            {'success': bool, 'schedule_id': int, 'error': Optional[str]}
        """
        try:
            # 従業員取得
            employee = self.emp_repo.find_by_employee_number(employee_number)
            if not employee:
                return {'success': False, 'error': '従業員が見つかりません'}

            if not employee['line_user_id']:
                return {'success': False, 'error': 'LINE IDが未登録です'}

            # 日付デフォルト値
            if not work_date:
                work_date = str(date.today())

            # メッセージ作成
            message = self._create_work_schedule_message(
                employee['name'],
                work_time,
                work_date
            )

            # データベースに保存
            schedule_id = self.ws_repo.create(
                employee['id'],
                message,
                work_date,
                work_time
            )

            # LINE送信
            send_work_schedule_message(
                employee['line_user_id'],
                message,
                schedule_id
            )

            logger.info(f"Work schedule sent: {schedule_id} to {employee_number}")
            return {'success': True, 'schedule_id': schedule_id}

        except Exception as e:
            logger.error(f"Failed to send work schedule: {e}")
            return {'success': False, 'error': str(e)}

    def record_reply(
        self,
        schedule_id: int,
        reply_message: str
    ) -> bool:
        """返信を記録"""
        try:
            self.ws_repo.update_reply_status(schedule_id, 'replied', reply_message)
            logger.info(f"Recorded reply for schedule: {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to record reply: {e}")
            return False

    def get_today_status(self) -> Dict:
        """本日の勤務連絡状況を取得"""
        try:
            all_schedules = self.ws_repo.find_today_schedules()
            replied = self.ws_repo.find_replied_today()
            not_replied = self.ws_repo.find_not_replied_today()

            return {
                'total': len(all_schedules),
                'replied': len(replied),
                'not_replied': len(not_replied),
                'replied_list': replied,
                'not_replied_list': not_replied
            }
        except Exception as e:
            logger.error(f"Failed to get today status: {e}")
            raise

    def check_all_replied(self) -> Tuple[bool, int, int]:
        """全員返信済みかチェック

        Returns:
            (all_replied: bool, total_count: int, replied_count: int)
        """
        try:
            status = self.get_today_status()
            all_replied = status['total'] > 0 and status['not_replied'] == 0
            return (all_replied, status['total'], status['replied'])
        except Exception as e:
            logger.error(f"Failed to check all replied: {e}")
            return (False, 0, 0)

    def _create_work_schedule_message(
        self,
        employee_name: str,
        work_time: str,
        work_date: str
    ) -> str:
        """勤務連絡メッセージを作成"""
        if work_time == 'なるべく早めに出勤':
            return f"{employee_name}さん\n\n本日 {work_date} は{work_time}お願いします。"
        else:
            return f"{employee_name}さん\n\n本日 {work_date} {work_time}出勤でお願いします。"
```

---

### Change 3.4: app/services/notification_service.py 作成 (3時間)

**ファイル**: `app/services/notification_service.py`

```python
from typing import List, Dict
from app.repositories.notification_repository import NotificationRepository
from app.repositories.employee_repository import EmployeeRepository
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
import os
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """通知ビジネスロジック"""

    def __init__(self):
        self.notification_repo = NotificationRepository()
        self.employee_repo = EmployeeRepository()
        self.line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))

    def send_to_managers(self, message_text: str) -> int:
        """通知先社員全員にメッセージを送信

        Returns:
            送信成功件数
        """
        managers = self._get_notification_managers()

        if not managers:
            logger.warning("通知先社員が設定されていません")
            return 0

        success_count = 0
        for manager in managers:
            if not manager['line_user_id']:
                logger.warning(f"{manager['name']}のLINE IDが未設定")
                continue

            try:
                self.line_bot_api.push_message(
                    manager['line_user_id'],
                    TextSendMessage(text=message_text)
                )
                self.notification_repo.create(
                    'manager_notification',
                    manager['id'],
                    None,
                    message_text
                )
                logger.info(f"{manager['name']}に通知送信")
                success_count += 1
            except LineBotApiError as e:
                logger.error(f"{manager['name']}への通知失敗: {e}")

        return success_count

    def send_reply_summary(
        self,
        replied_list: List[Dict],
        not_replied_list: List[Dict]
    ) -> None:
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

        self.send_to_managers(message)
        logger.info("返信状況まとめ通知を送信しました")

    def send_late_reply_notification(
        self,
        employee_name: str,
        reply_time: str,
        pending_employees: List[Dict]
    ) -> None:
        """遅延返信の即時通知（未返信者リスト付き）"""
        message = f"📨 遅延返信がありました\n\n{employee_name}さんから返信 ({reply_time})\n"

        if pending_employees:
            message += f"\n⚠️ 残り未返信者 ({len(pending_employees)}人):\n"
            for emp in pending_employees:
                message += f"  • {emp['employee_name']}\n"
        else:
            message += "\n✅ 全員返信完了"

        self.send_to_managers(message)
        logger.info(f"{employee_name}の遅延返信を通知しました")

    def send_all_replied_notification(self, all_replies_info: List[Dict]) -> None:
        """全員返信完了の即時通知"""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from database import check_all_replied_notification_sent_today, mark_all_replied_notification_sent

        # 重複防止チェック
        if check_all_replied_notification_sent_today():
            logger.info("全員返信完了通知は既に送信済み（スキップ）")
            return

        message = "✅ 全員分の返信が集まりました\n\n返信状況:\n"

        for reply in all_replies_info:
            replied_at_str = reply['replied_at']
            try:
                replied_at_utc = datetime.strptime(
                    replied_at_str.split('.')[0],
                    '%Y-%m-%d %H:%M:%S'
                )
                replied_at_utc = replied_at_utc.replace(tzinfo=ZoneInfo('UTC'))
                replied_at_jst = replied_at_utc.astimezone(ZoneInfo('Asia/Tokyo'))
                time_display = replied_at_jst.strftime('%H:%M')
            except Exception as e:
                logger.warning(f"時刻パースエラー: {replied_at_str} - {e}")
                time_display = "??:??"

            message += f"  • {reply['employee_name']}さん {time_display}\n"

        self.send_to_managers(message)
        mark_all_replied_notification_sent()
        logger.info("全員返信完了を通知しました")

    def _get_notification_managers(self) -> List[Dict]:
        """通知先社員を取得（is_notification_manager=1）"""
        # database.pyのget_notification_managers()を使用
        from database import get_notification_managers
        return get_notification_managers()
```

---

### Change 3.5: notification.py をサービス層に委譲 (2時間)

**ファイル**: `notification.py`

**変更後**:
```python
"""通知システム - サービス層への委譲"""
from app.services.notification_service import NotificationService

notification_service = NotificationService()

def send_to_managers(message_text):
    """通知先社員全員にメッセージを送信"""
    return notification_service.send_to_managers(message_text)

def send_reply_summary(replied_list, not_replied_list):
    """13:00の返信状況まとめ通知"""
    return notification_service.send_reply_summary(replied_list, not_replied_list)

def send_late_reply_notification(employee_name, reply_time, pending_employees):
    """遅延返信の即時通知"""
    return notification_service.send_late_reply_notification(
        employee_name, reply_time, pending_employees
    )

def send_all_replied_notification(all_replies_info):
    """全員返信完了の即時通知"""
    return notification_service.send_all_replied_notification(all_replies_info)

def send_second_reminder_alert(not_replied_list):
    """14:00時点の未返信通知"""
    if not not_replied_list:
        return

    message = "🚨 14:00時点でまだ未返信\n\n"
    for emp in not_replied_list:
        message += f"  • {emp['employee_name']}\n"

    message += "\n※3回連続で送信しました"
    send_to_managers(message)

def record_notification(notification_type, recipient_id, schedule_id, message):
    """通知履歴をDBに記録"""
    return notification_service.notification_repo.create(
        notification_type, recipient_id, schedule_id, message
    )
```

---

### Change 3.6: tests/test_services.py 作成 (4時間)

**ファイル**: `tests/test_services.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services import EmployeeService, WorkScheduleService, NotificationService

class TestEmployeeService:
    """従業員サービステスト"""

    def test_register_line_user_success(self, app):
        """LINE登録が成功すること"""
        with app.app_context():
            service = EmployeeService()

            # テストデータ作成
            service.create_employee('K999', 'テスト太郎')

            # LINE登録
            success, error = service.register_line_user('K999', 'U123456', 'テスト太郎')

            assert success is True
            assert error is None

    def test_register_line_user_name_mismatch(self, app):
        """名前が一致しない場合エラーになること"""
        with app.app_context():
            service = EmployeeService()

            service.create_employee('K999', 'テスト太郎')

            success, error = service.register_line_user('K999', 'U123456', '間違った名前')

            assert success is False
            assert '一致しません' in error

    def test_create_employee_duplicate(self, app):
        """重複する従業員番号でエラーになること"""
        with app.app_context():
            service = EmployeeService()

            success1, _ = service.create_employee('K999', 'テスト太郎')
            success2, error = service.create_employee('K999', '別の人')

            assert success1 is True
            assert success2 is False
            assert '既に存在' in error

class TestWorkScheduleService:
    """勤務連絡サービステスト"""

    @patch('app.services.work_schedule_service.send_work_schedule_message')
    def test_send_work_schedule_success(self, mock_send, app):
        """勤務連絡送信が成功すること"""
        with app.app_context():
            emp_service = EmployeeService()
            ws_service = WorkScheduleService()

            emp_service.create_employee('K999', 'テスト太郎')
            emp_service.register_line_user('K999', 'U123456')

            result = ws_service.send_work_schedule('K999', '13:00', '2024-01-15')

            assert result['success'] is True
            assert 'schedule_id' in result
            mock_send.assert_called_once()

    def test_check_all_replied(self, app):
        """全員返信チェックが動作すること"""
        with app.app_context():
            ws_service = WorkScheduleService()

            all_replied, total, replied = ws_service.check_all_replied()

            assert isinstance(all_replied, bool)
            assert total >= 0
            assert replied >= 0

class TestNotificationService:
    """通知サービステスト"""

    @patch('app.services.notification_service.LineBotApi')
    def test_send_to_managers(self, mock_line_api, app):
        """通知先社員へのメッセージ送信"""
        with app.app_context():
            mock_instance = MagicMock()
            mock_line_api.return_value = mock_instance

            service = NotificationService()
            result = service.send_to_managers('テストメッセージ')

            assert result >= 0  # 送信成功件数

# ... 全サービスメソッドに対してテスト作成（約30-40テスト）
```

**検証**:
```bash
pytest tests/test_services.py -v
pytest tests/test_services.py --cov=app.services
# Coverage: ≥90%
```

---

### Phase 3 検証チェックリスト

- [ ] `python3 -c "from app.services import EmployeeService"` が成功
- [ ] EmployeeService のすべてのビジネスロジックがテスト済み
- [ ] WorkScheduleService のすべてのフローがテスト済み
- [ ] NotificationService のLINE送信がモックでテスト済み
- [ ] notification.py がサービス層に委譲されている
- [ ] `pytest tests/test_services.py --cov=app.services` で ≥90% カバレッジ
- [ ] エンドツーエンドの統合テストが動作

### Phase 3 ロールバック手順

```bash
# Step 1: 元のnotification.pyを復元
git checkout notification.py

# Step 2: サービス層削除
rm -rf app/services/

# Step 3: サービステスト削除
rm tests/test_services.py tests/test_integration.py

# Step 4: アプリ再起動
pkill -f "python3 app.py"
python3 app.py

# 時間: 3分
# データ損失リスク: なし
```

---

## Phase 4: Route Layer - Blueprint Splitting (20時間)

**リスクレベル**: 🔴 HIGH
**ロールバック時間**: 5分

⚠️ **重要**: この Phase は最もリスクが高いため、慎重に実施してください。

### 事前準備: app.py のバックアップ

```bash
cp app.py app_legacy.py
git add app_legacy.py
git commit -m "Backup: Save original app.py before blueprint migration"
```

---

### Change 4.1: app/blueprints/__init__.py 作成 (5分)

**ファイル**: `app/blueprints/__init__.py`

```python
from .auth_routes import auth_bp
from .employee_routes import employee_bp
from .schedule_routes import schedule_bp
from .webhook_routes import webhook_bp
from .settings_routes import settings_bp
from .liff_routes import liff_bp

__all__ = [
    'auth_bp',
    'employee_bp',
    'schedule_bp',
    'webhook_bp',
    'settings_bp',
    'liff_bp'
]
```

---

### Change 4.2: app/blueprints/auth_routes.py 作成 (2時間)

**ファイル**: `app/blueprints/auth_routes.py`

```python
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from auth import login_user, logout_user, require_auth
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if login_user(username, password):
            logger.info(f"User logged in: {username}")
            return redirect(url_for('schedules.index'))

        logger.warning(f"Failed login attempt: {username}")
        flash('ユーザー名またはパスワードが間違っています')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """ログアウト"""
    username = session.get('username')
    logout_user()
    logger.info(f"User logged out: {username}")
    return redirect(url_for('auth.login'))
```

---

### Change 4.3: app/blueprints/employee_routes.py 作成 (3時間)

**ファイル**: `app/blueprints/employee_routes.py`

```python
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from auth import require_auth
from app.services.employee_service import EmployeeService
import logging

logger = logging.getLogger(__name__)
employee_bp = Blueprint('employees', __name__, url_prefix='/employees')
employee_service = EmployeeService()

@employee_bp.route('/')
@require_auth
def list_employees():
    """従業員一覧"""
    try:
        employees = employee_service.list_all_employees()
        return render_template('employees.html', employees=employees)
    except Exception as e:
        logger.error(f"Failed to list employees: {e}")
        flash('従業員リストの取得に失敗しました')
        return render_template('employees.html', employees=[])

@employee_bp.route('/create', methods=['POST'])
@require_auth
def create_employee():
    """従業員作成"""
    employee_number = request.form.get('employee_number')
    name = request.form.get('name')

    if not employee_number or not name:
        return jsonify({'success': False, 'error': '従業員番号と名前は必須です'}), 400

    success, error = employee_service.create_employee(employee_number, name)

    if success:
        logger.info(f"Employee created: {employee_number}")
        return jsonify({'success': True})
    else:
        logger.warning(f"Failed to create employee: {error}")
        return jsonify({'success': False, 'error': error}), 400

@employee_bp.route('/<int:employee_id>/update', methods=['POST'])
@require_auth
def update_employee(employee_id):
    """従業員更新"""
    employee_number = request.form.get('employee_number')
    name = request.form.get('name')

    if not employee_number or not name:
        return jsonify({'success': False, 'error': '従業員番号と名前は必須です'}), 400

    success, error = employee_service.update_employee(employee_id, employee_number, name)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 400

@employee_bp.route('/<int:employee_id>/delete', methods=['POST'])
@require_auth
def delete_employee(employee_id):
    """従業員削除（論理削除）"""
    success, error = employee_service.soft_delete_employee(employee_id)

    if success:
        flash('従業員を削除しました')
    else:
        flash(f'削除に失敗しました: {error}')

    return redirect(url_for('employees.list_employees'))

@employee_bp.route('/<int:employee_id>/hard-delete', methods=['POST'])
@require_auth
def hard_delete_employee(employee_id):
    """従業員完全削除（物理削除）"""
    success, error = employee_service.hard_delete_employee(employee_id)

    if success:
        flash('従業員を完全に削除しました（番号再利用可能）')
    else:
        flash(f'削除に失敗しました: {error}')

    return redirect(url_for('employees.list_employees'))
```

---

### Change 4.4: app/blueprints/schedule_routes.py 作成 (4時間)

**ファイル**: `app/blueprints/schedule_routes.py`

```python
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from auth import require_auth
from app.services.work_schedule_service import WorkScheduleService
from app.services.employee_service import EmployeeService
import logging

logger = logging.getLogger(__name__)
schedule_bp = Blueprint('schedules', __name__, url_prefix='/schedules')
ws_service = WorkScheduleService()
emp_service = EmployeeService()

@schedule_bp.route('/')
@require_auth
def index():
    """勤務連絡メイン画面"""
    try:
        employees = emp_service.list_all_employees()
        status = ws_service.get_today_status()

        return render_template(
            'index.html',
            employees=employees,
            today_status=status
        )
    except Exception as e:
        logger.error(f"Failed to load schedule page: {e}")
        return render_template('index.html', employees=[], today_status={})

@schedule_bp.route('/send', methods=['POST'])
@require_auth
def send_schedules():
    """勤務連絡一括送信"""
    try:
        # フォームから送信データを取得
        # employee_number, work_time のペアのリスト
        schedules = []  # リクエストから取得

        results = []
        for schedule in schedules:
            result = ws_service.send_work_schedule(
                schedule['employee_number'],
                schedule['work_time']
            )
            results.append(result)

        success_count = sum(1 for r in results if r['success'])

        return jsonify({
            'success': True,
            'sent_count': success_count,
            'total': len(schedules)
        })
    except Exception as e:
        logger.error(f"Failed to send schedules: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/today')
@require_auth
def today_status():
    """本日の勤務連絡状況"""
    try:
        status = ws_service.get_today_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Failed to get today status: {e}")
        return jsonify({'error': str(e)}), 500

@schedule_bp.route('/manual-send', methods=['POST'])
@require_auth
def manual_send():
    """個別手動送信"""
    employee_number = request.form.get('employee_number')
    work_time = request.form.get('work_time')

    if not employee_number or not work_time:
        return jsonify({'success': False, 'error': '必須項目が不足しています'}), 400

    result = ws_service.send_work_schedule(employee_number, work_time)

    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400
```

---

### Change 4.5: app/blueprints/webhook_routes.py 作成 (3時間)

**ファイル**: `app/blueprints/webhook_routes.py`

```python
from flask import Blueprint, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
from app.services.work_schedule_service import WorkScheduleService
from app.services.employee_service import EmployeeService
import os
import logging

logger = logging.getLogger(__name__)
webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
ws_service = WorkScheduleService()
emp_service = EmployeeService()

@webhook_bp.route('/callback', methods=['POST'])
def callback():
    """LINE webhook コールバック"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """メッセージイベント処理"""
    line_user_id = event.source.user_id
    message_text = event.message.text

    try:
        # LINE IDから従業員を特定
        employee = emp_service.get_employee_by_line_id(line_user_id)

        if not employee:
            logger.warning(f"Unknown LINE user: {line_user_id}")
            return

        # 本日の勤務連絡を取得し、返信として記録
        # ... 返信処理ロジック

        logger.info(f"Message handled from {employee['name']}: {message_text}")

    except Exception as e:
        logger.error(f"Failed to handle message: {e}")
```

---

### Change 4.6: app/blueprints/settings_routes.py 作成 (2時間)

**ファイル**: `app/blueprints/settings_routes.py`

```python
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from auth import require_auth
from database import get_notification_managers, update_notification_managers
import logging

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@require_auth
def index():
    """設定画面"""
    try:
        managers = get_notification_managers()
        return render_template('settings.html', managers=managers)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return render_template('settings.html', managers=[])

@settings_bp.route('/managers', methods=['POST'])
@require_auth
def update_managers():
    """通知先社員設定更新"""
    try:
        manager_ids = request.form.getlist('manager_ids')
        update_notification_managers(manager_ids)

        logger.info(f"Updated notification managers: {len(manager_ids)} managers")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to update managers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

### Change 4.7: app/blueprints/liff_routes.py 作成 (2時間)

**ファイル**: `app/blueprints/liff_routes.py`

```python
from flask import Blueprint, render_template, request, jsonify
from app.services.employee_service import EmployeeService
import logging

logger = logging.getLogger(__name__)
liff_bp = Blueprint('liff', __name__, url_prefix='/liff')
employee_service = EmployeeService()

@liff_bp.route('/register')
def register_page():
    """LIFF登録画面"""
    return render_template('liff_register.html')

@liff_bp.route('/register', methods=['POST'])
def register():
    """LINE登録処理"""
    try:
        data = request.get_json()
        employee_number = data.get('employee_number')
        employee_name = data.get('employee_name')
        line_user_id = data.get('line_user_id')

        if not all([employee_number, employee_name, line_user_id]):
            return jsonify({
                'success': False,
                'error': '必須項目が不足しています'
            }), 400

        success, error = employee_service.register_line_user(
            employee_number,
            line_user_id,
            employee_name
        )

        if success:
            logger.info(f"LIFF registration successful: {employee_number}")
            return jsonify({'success': True})
        else:
            logger.warning(f"LIFF registration failed: {error}")
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"LIFF registration error: {e}")
        return jsonify({'success': False, 'error': 'サーバーエラーが発生しました'}), 500
```

---

### Change 4.8: app.py をBlueprint登録に変更 (2時間)

**ファイル**: `app.py`

**変更後** (1,155行 → 約200行):
```python
from flask import Flask, redirect, url_for
from flask_talisman import Talisman
from config import config
from app.blueprints import (
    auth_bp,
    employee_bp,
    schedule_bp,
    webhook_bp,
    settings_bp,
    liff_bp
)
import logging_config
import logging

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config)

# Security headers
Talisman(app, content_security_policy=None)

# Setup logging
logging_config.setup_logging(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(schedule_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(liff_bp)

logger.info("All blueprints registered successfully")

# Root redirect
@app.route('/')
def root():
    """ルートはログイン画面にリダイレクト"""
    return redirect(url_for('auth.login'))

# Health check endpoint
@app.route('/health')
def health():
    """ヘルスチェック"""
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    logger.info(f"Starting application on {config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
```

**検証**:
```bash
# アプリケーション起動
python3 app.py

# すべてのルートが登録されているか確認
flask routes

# 主要エンドポイントのテスト
curl http://localhost:5001/health  # {"status": "ok"}
curl http://localhost:5001/auth/login  # ログイン画面
```

---

### Change 4.9: tests/test_blueprints.py 作成 (2時間)

**ファイル**: `tests/test_blueprints.py`

```python
import pytest

class TestAuthBlueprint:
    """認証Blueprintテスト"""

    def test_login_page_loads(self, client):
        """ログインページが表示されること"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_login_success(self, client):
        """ログインが成功すること"""
        response = client.post('/auth/login', data={
            'username': 'test_user',
            'password': 'test_pass'
        }, follow_redirects=False)
        assert response.status_code == 302  # リダイレクト

    def test_logout(self, client):
        """ログアウトが動作すること"""
        # ログイン
        client.post('/auth/login', data={
            'username': 'test_user',
            'password': 'test_pass'
        })

        # ログアウト
        response = client.get('/auth/logout')
        assert response.status_code == 302  # ログインページへリダイレクト

class TestEmployeeBlueprint:
    """従業員Blueprintテスト"""

    def test_employees_requires_auth(self, client):
        """認証なしでは従業員一覧にアクセスできないこと"""
        response = client.get('/employees/')
        assert response.status_code == 302  # ログインへリダイレクト

    def test_employees_list_with_auth(self, client):
        """認証後、従業員一覧が表示されること"""
        # ログイン
        client.post('/auth/login', data={
            'username': 'test_user',
            'password': 'test_pass'
        })

        # 従業員一覧
        response = client.get('/employees/')
        assert response.status_code == 200

class TestScheduleBlueprint:
    """勤務連絡Blueprintテスト"""

    def test_schedule_index_requires_auth(self, client):
        """認証なしではアクセスできないこと"""
        response = client.get('/schedules/')
        assert response.status_code == 302

    def test_schedule_index_with_auth(self, client):
        """認証後、勤務連絡画面が表示されること"""
        client.post('/auth/login', data={
            'username': 'test_user',
            'password': 'test_pass'
        })

        response = client.get('/schedules/')
        assert response.status_code == 200

class TestWebhookBlueprint:
    """Webhook Blueprintテスト"""

    def test_webhook_callback_invalid_signature(self, client):
        """無効な署名では400エラーになること"""
        response = client.post('/webhook/callback',
                              data='test',
                              headers={'X-Line-Signature': 'invalid'})
        assert response.status_code == 400

class TestSettingsBlueprint:
    """設定Blueprintテスト"""

    def test_settings_requires_auth(self, client):
        """認証なしではアクセスできないこと"""
        response = client.get('/settings/')
        assert response.status_code == 302

class TestLiffBlueprint:
    """LIFF Blueprintテスト"""

    def test_liff_register_page_loads(self, client):
        """LIFF登録ページが表示されること（認証不要）"""
        response = client.get('/liff/register')
        assert response.status_code == 200

# ... 全ルートに対してテスト作成（約40-50テスト）
```

**検証**:
```bash
pytest tests/test_blueprints.py -v
pytest tests/test_blueprints.py --cov=app.blueprints
# すべてのルートがテスト済み
```

---

### Phase 4 検証チェックリスト（11項目）

- [ ] `flask routes` ですべてのエンドポイントが表示される
- [ ] すべての既存URLが動作（404なし）
- [ ] 認証フロー（ログイン・ログアウト）が動作
- [ ] 従業員管理のすべてのCRUD操作が動作
- [ ] 勤務連絡送信フローが動作
- [ ] LINE webhook処理が動作
- [ ] 設定画面が動作
- [ ] LIFF登録フローが動作
- [ ] `pytest tests/test_blueprints.py -v` がすべてPASS
- [ ] 手動テスト: 全ユーザーフローを確認
- [ ] パフォーマンス: レスポンス時間がベースライン±5%以内

### Phase 4 ロールバック手順（CRITICAL）

```bash
# Step 1: アプリケーション即時停止
pkill -f "python3 app.py"

# Step 2: 元のapp.pyを復元
cp app_legacy.py app.py

# Step 3: Blueprint ディレクトリ削除
rm -rf app/blueprints/

# Step 4: Blueprint テスト削除
rm tests/test_blueprints.py

# Step 5: アプリケーション再起動
python3 app.py

# Step 6: 動作確認
curl http://localhost:5001/auth/login  # 200 OK

# 時間: 5分
# ダウンタイム: ~5分
# データ損失リスク: なし
```

---

## Phase 5: Comprehensive Testing (18時間)

**リスクレベル**: 🟢 LOW
**ロールバック時間**: 2分

### Change 5.1: tests/test_integration.py 作成 (4時間)

**ファイル**: `tests/test_integration.py`

```python
import pytest
from app.services import EmployeeService, WorkScheduleService, NotificationService

def test_complete_work_schedule_flow(app, client):
    """完全な勤務連絡フロー統合テスト"""
    with app.app_context():
        emp_service = EmployeeService()
        ws_service = WorkScheduleService()

        # 1. 従業員作成
        success, error = emp_service.create_employee('K999', 'テスト太郎')
        assert success is True

        # 2. LINE登録
        success, error = emp_service.register_line_user('K999', 'U999999', 'テスト太郎')
        assert success is True

        # 3. 勤務連絡送信
        result = ws_service.send_work_schedule('K999', '13:00', '2024-01-15')
        assert result['success'] is True
        schedule_id = result['schedule_id']

        # 4. 返信処理
        success = ws_service.record_reply(schedule_id, '出勤します')
        assert success is True

        # 5. ステータス確認
        schedule = ws_service.ws_repo.find_by_id(schedule_id)
        assert schedule['reply_status'] == 'replied'
        assert schedule['reply_message'] == '出勤します'

def test_multiple_employees_workflow(app):
    """複数従業員の勤務連絡フロー"""
    with app.app_context():
        emp_service = EmployeeService()
        ws_service = WorkScheduleService()

        # 複数従業員作成
        for i in range(3):
            emp_service.create_employee(f'K99{i}', f'テスト{i}')
            emp_service.register_line_user(f'K99{i}', f'U99999{i}')

        # 一括送信
        for i in range(3):
            result = ws_service.send_work_schedule(f'K99{i}', '13:00')
            assert result['success'] is True

        # ステータス確認
        status = ws_service.get_today_status()
        assert status['total'] == 3
        assert status['not_replied'] == 3  # まだ誰も返信していない

def test_notification_flow(app):
    """通知フローの統合テスト"""
    # ... 通知フローのエンドツーエンドテスト
    pass

# ... さらに統合テストを追加
```

---

### Change 5.2: tests/test_database.py 作成 (3時間)

**ファイル**: `tests/test_database.py`

```python
import pytest
from database import (
    get_db_connection,
    init_db,
    check_all_replied_today,
    get_today_all_replies_with_time,
    update_setting,
    get_setting
)

def test_database_connection(app):
    """データベース接続テスト"""
    with app.app_context():
        conn = get_db_connection()
        assert conn is not None

        # WAL mode確認
        result = conn.execute('PRAGMA journal_mode').fetchone()
        assert result['journal_mode'] == 'wal'

        # Timeout確認
        result = conn.execute('PRAGMA busy_timeout').fetchone()
        assert result['busy_timeout'] > 0

        conn.close()

def test_all_replied_check(app):
    """全員返信チェックのテスト"""
    with app.app_context():
        all_replied, total, replied = check_all_replied_today()

        assert isinstance(all_replied, bool)
        assert total >= 0
        assert replied >= 0
        assert replied <= total

def test_settings_crud(app):
    """設定のCRUDテスト"""
    with app.app_context():
        # 設定を保存
        update_setting('test_key', 'test_value')

        # 設定を取得
        value = get_setting('test_key')
        assert value == 'test_value'

        # 設定を更新
        update_setting('test_key', 'new_value')
        value = get_setting('test_key')
        assert value == 'new_value'

# ... さらにデータベース関数のテストを追加
```

---

### Change 5.3: tests/test_line_integration.py 作成 (3時間)

**ファイル**: `tests/test_line_integration.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from notification import (
    send_to_managers,
    send_all_replied_notification,
    send_reply_summary
)

@patch('notification.line_bot_api')
def test_send_to_managers(mock_line_api, app):
    """通知先社員へのメッセージ送信テスト"""
    with app.app_context():
        mock_line_api.push_message = MagicMock()

        result = send_to_managers('テストメッセージ')

        assert result > 0  # 少なくとも1件送信成功
        mock_line_api.push_message.assert_called()

@patch('notification.line_bot_api')
def test_all_replied_notification(mock_line_api, app):
    """全員返信完了通知のテスト"""
    with app.app_context():
        mock_line_api.push_message = MagicMock()

        test_replies = [
            {'employee_name': '山田太郎', 'replied_at': '2024-01-15 04:30:00'},  # UTC
            {'employee_name': '佐藤花子', 'replied_at': '2024-01-15 05:00:00'}   # UTC
        ]

        send_all_replied_notification(test_replies)

        # LINE APIが呼ばれたことを確認
        mock_line_api.push_message.assert_called()

        # 時刻がJSTに変換されていることを確認
        call_args = mock_line_api.push_message.call_args
        message = call_args[0][1].text
        assert '13:30' in message  # UTC 04:30 → JST 13:30
        assert '14:00' in message  # UTC 05:00 → JST 14:00

@patch('notification.line_bot_api')
def test_reply_summary(mock_line_api, app):
    """返信状況まとめ通知のテスト"""
    with app.app_context():
        mock_line_api.push_message = MagicMock()

        replied = [{'employee_name': '山田太郎'}]
        not_replied = [{'employee_name': '佐藤花子'}]

        send_reply_summary(replied, not_replied)

        mock_line_api.push_message.assert_called()

# ... さらにLINE統合テストを追加
```

---

### Change 5.4: tests/test_validators.py 作成 (2時間)

**ファイル**: `tests/test_validators.py`

```python
import pytest
from validators import (
    validate_employee_number,
    validate_time_format,
    validate_date_format
)

class TestEmployeeNumberValidation:
    """従業員番号バリデーション"""

    def test_valid_employee_numbers(self):
        """有効な従業員番号"""
        assert validate_employee_number('K001') is True
        assert validate_employee_number('K999') is True
        assert validate_employee_number('k001') is True  # 小文字OK
        assert validate_employee_number('K1') is True

    def test_invalid_employee_numbers(self):
        """無効な従業員番号"""
        assert validate_employee_number('001') is False  # Kなし
        assert validate_employee_number('') is False
        assert validate_employee_number(None) is False
        assert validate_employee_number('A001') is False  # K以外

class TestTimeFormatValidation:
    """時刻フォーマットバリデーション"""

    def test_valid_time_formats(self):
        """有効な時刻フォーマット"""
        assert validate_time_format('00:00') is True
        assert validate_time_format('13:00') is True
        assert validate_time_format('23:59') is True
        assert validate_time_format('なるべく早めに出勤') is True  # 特殊ケース

    def test_invalid_time_formats(self):
        """無効な時刻フォーマット"""
        assert validate_time_format('24:00') is False  # 不正な時刻
        assert validate_time_format('13:60') is False  # 不正な分
        assert validate_time_format('1:00') is False   # 0パディングなし
        assert validate_time_format('') is False
        assert validate_time_format(None) is False

class TestDateFormatValidation:
    """日付フォーマットバリデーション"""

    def test_valid_date_formats(self):
        """有効な日付フォーマット"""
        assert validate_date_format('2024-01-01') is True
        assert validate_date_format('2024-12-31') is True

    def test_invalid_date_formats(self):
        """無効な日付フォーマット"""
        assert validate_date_format('2024-13-01') is False  # 不正な月
        assert validate_date_format('2024-01-32') is False  # 不正な日
        assert validate_date_format('24-01-01') is False     # 2桁年
        assert validate_date_format('') is False
```

---

### Change 5.5: tests/test_auth.py 作成 (2時間)

**ファイル**: `tests/test_auth.py`

```python
import pytest
from auth import verify_password, login_user, logout_user, require_auth

def test_password_verification():
    """パスワード検証テスト"""
    # テスト用認証情報を使用
    assert verify_password('test_user', 'test_pass') is True
    assert verify_password('test_user', 'wrong_pass') is False
    assert verify_password('nonexistent', 'pass') is False

def test_login_logout_flow(client):
    """ログイン・ログアウトフローテスト"""
    # ログイン
    response = client.post('/auth/login', data={
        'username': 'test_user',
        'password': 'test_pass'
    })
    assert response.status_code == 302  # リダイレクト

    # 認証が必要なページにアクセス可能
    response = client.get('/schedules/')
    assert response.status_code == 200

    # ログアウト
    response = client.get('/auth/logout')
    assert response.status_code == 302  # ログインページへリダイレクト

    # ログアウト後は認証が必要なページにアクセス不可
    response = client.get('/schedules/')
    assert response.status_code == 302  # ログインページへリダイレクト

def test_require_auth_decorator(client):
    """認証デコレーターテスト"""
    # 未ログインでアクセス
    response = client.get('/employees/')
    assert response.status_code == 302  # ログインへリダイレクト

    # ログイン
    client.post('/auth/login', data={
        'username': 'test_user',
        'password': 'test_pass'
    })

    # ログイン後はアクセス可能
    response = client.get('/employees/')
    assert response.status_code == 200
```

---

### Change 5.6: tests/test_scheduler.py 作成 (2時間)

**ファイル**: `tests/test_scheduler.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from scheduler import (
    send_morning_schedules,
    send_afternoon_reminder,
    send_second_reminder
)

@patch('scheduler.WorkScheduleService')
@patch('scheduler.EmployeeService')
def test_morning_schedule_job(mock_emp_service, mock_ws_service, app):
    """朝の勤務連絡送信ジョブテスト"""
    with app.app_context():
        # モック設定
        mock_emp_service.return_value.list_all_employees.return_value = [
            {'employee_number': 'K001', 'name': '山田太郎', 'line_user_id': 'U001'}
        ]

        result = send_morning_schedules()

        assert 'success' in result
        assert 'sent_count' in result

@patch('scheduler.NotificationService')
@patch('scheduler.WorkScheduleService')
def test_afternoon_reminder_job(mock_ws_service, mock_notif_service, app):
    """13時リマインダージョブテスト"""
    with app.app_context():
        mock_ws_service.return_value.get_today_status.return_value = {
            'total': 3,
            'replied': 1,
            'not_replied': 2,
            'replied_list': [{'employee_name': '山田太郎'}],
            'not_replied_list': [
                {'employee_name': '佐藤花子'},
                {'employee_name': '鈴木一郎'}
            ]
        }

        result = send_afternoon_reminder()

        assert 'success' in result
        mock_notif_service.return_value.send_reply_summary.assert_called_once()

@patch('scheduler.WorkScheduleService')
def test_second_reminder_job(mock_ws_service, app):
    """14時リマインダージョブテスト"""
    with app.app_context():
        mock_ws_service.return_value.get_today_status.return_value = {
            'not_replied_list': [{'employee_name': '佐藤花子'}]
        }

        result = send_second_reminder()

        assert 'success' in result
```

---

### Change 5.7: pyproject.toml にpytest設定追加 (30分)

**ファイル**: `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=app",
    "--cov=database",
    "--cov=notification",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=85",
    "-v"
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**検証**:
```bash
pytest
# すべてのテストがPASS
# Coverage: ≥85%
```

---

### Change 5.8: GitHub Actions CI ワークフロー作成 (1時間)

**ファイル**: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linter
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Run type checker
        run: |
          mypy app/ database.py notification.py

      - name: Run tests
        run: |
          pytest --cov --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

**検証**:
```bash
# ローカルでCIコマンドを実行
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
mypy app/ database.py notification.py
pytest --cov --cov-report=xml
```

---

### Phase 5 検証チェックリスト（10項目）

- [ ] `pytest` ですべてのテストがPASS
- [ ] `pytest --cov` で85%以上のカバレッジ
- [ ] 統合テストが完全なワークフローをカバー
- [ ] データベーステストがすべての関数をカバー
- [ ] LINE統合テストがモックで動作
- [ ] バリデーターテストがすべてのケースをカバー
- [ ] 認証テストがログインフローをカバー
- [ ] スケジューラテストがすべてのジョブをカバー
- [ ] CIパイプラインがローカルで動作
- [ ] `pytest --cov-fail-under=85` がPASS

### Phase 5 ロールバック手順

```bash
# Step 1: 新しいテストファイル削除
rm tests/test_integration.py
rm tests/test_database.py
rm tests/test_line_integration.py
rm tests/test_validators.py
rm tests/test_auth.py
rm tests/test_scheduler.py

# Step 2: CIワークフロー削除
rm .github/workflows/ci.yml

# Step 3: pytest設定を復元
git checkout pyproject.toml

# 時間: 2分
# データ損失リスク: なし
```

---

## Phase 6: Cleanup and Documentation (8時間)

**リスクレベル**: 🟢 VERY LOW
**ロールバック時間**: 1分

### Change 6.1: すべてのprint()をloggingに置き換え (1時間)

**対象ファイル**: すべての.pyファイル

**検索**:
```bash
grep -r "print(" --include="*.py" app/ database.py notification.py
```

**置き換えパターン**:
```python
# Before:
print("✅ 成功しました")
print(f"❌ エラー: {error}")

# After:
logger.info("成功しました")
logger.error(f"エラー: {error}")
```

**検証**:
```bash
# print()が残っていないことを確認
grep -r "print(" --include="*.py" app/ database.py notification.py
# 出力: なし（テストファイル以外）
```

---

### Change 6.2: 全関数に型ヒント追加 (3時間)

**対象**: すべての.pyファイル

**例**:
```python
from typing import Optional, List, Dict, Tuple, Any

# Before:
def get_employees():
    # ...

# After:
def get_employees() -> List[Dict[str, Any]]:
    """全従業員を取得

    Returns:
        従業員リスト
    """
    # ...
```

**検証**:
```bash
mypy .
# 出力: Success: no issues found in XX source files
```

---

### Change 6.3: README.md 作成 (2時間)

**ファイル**: `README.md`

```markdown
# LINE Bot 勤務連絡システム

従業員への勤務連絡を自動化し、返信状況を管理するLINE Botシステム

## 📋 目次

- [機能](#機能)
- [アーキテクチャ](#アーキテクチャ)
- [セットアップ](#セットアップ)
- [開発](#開発)
- [デプロイ](#デプロイ)
- [トラブルシューティング](#トラブルシューティング)

## 🎯 機能

- 従業員管理（CRUD操作）
- LINE Bot連携（勤務連絡の送信・受信）
- 勤務連絡の一括送信
- 返信状況のリアルタイム追跡
- 自動リマインダー送信
- 通知先社員への状況通知
- LIFF（LINE Front-end Framework）による従業員登録

## 🏗️ アーキテクチャ

### レイヤー構造

```
┌─────────────────────────────────────┐
│   Templates (Jinja2)                │  プレゼンテーション層
├─────────────────────────────────────┤
│   Routes (Flask Blueprints)         │  ルート層
│   - auth, employees, schedules      │
│   - webhooks, settings, liff        │
├─────────────────────────────────────┤
│   Services (Business Logic)         │  サービス層
│   - EmployeeService                 │
│   - WorkScheduleService             │
│   - NotificationService             │
├─────────────────────────────────────┤
│   Repositories (Data Access)        │  リポジトリ層
│   - EmployeeRepository              │
│   - WorkScheduleRepository          │
│   - NotificationRepository          │
├─────────────────────────────────────┤
│   Database (SQLite + WAL)           │  データ層
└─────────────────────────────────────┘
```

### 技術スタック

- **フレームワーク**: Flask 2.x
- **データベース**: SQLite (WAL mode)
- **LINE SDK**: linebot-sdk-python
- **テスト**: pytest, pytest-cov
- **型チェック**: mypy
- **デプロイ**: Render

## 🚀 セットアップ

### 必要な環境変数

```bash
# LINE Bot設定
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_CHANNEL_SECRET=your_channel_secret

# Flask設定
SECRET_KEY=your_secret_key
FLASK_DEBUG=False

# データベース設定
DATABASE_PATH=database.db
DATABASE_TIMEOUT=30
```

### インストール

```bash
# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 開発用依存関係（開発環境のみ）
pip install -r requirements-dev.txt
```

### データベース初期化

```bash
python3 -c "from database import init_db; init_db()"
```

## 🛠️ 開発

### ローカル実行

```bash
# 開発サーバー起動
python3 app.py

# または Gunicorn
gunicorn app:app -c gunicorn_config.py
```

### テスト実行

```bash
# すべてのテスト実行
pytest

# カバレッジ付き
pytest --cov

# 詳細出力
pytest -v

# 特定のテストファイル
pytest tests/test_integration.py
```

### コーディング規約

- **型ヒント**: すべての関数に型ヒント必須
- **ログ**: `print()` 禁止、`logging` 使用
- **エラーハンドリング**: 例外は適切にログ記録
- **テスト**: 新機能には必ずテスト追加
- **カバレッジ目標**: 85%以上

### ブランチ戦略

- `main`: 本番環境
- `develop`: 開発環境
- `feature/*`: 機能開発
- `hotfix/*`: 緊急修正

## 📦 デプロイ

### Render

```bash
# main branchへのpushで自動デプロイ
git push origin main
```

### 手動デプロイ

```bash
# Renderコンソールから「Manual Deploy」を実行
```

## 🐛 トラブルシューティング

### データベースロック

```bash
# WAL mode確認
sqlite3 database.db "PRAGMA journal_mode;"
# 出力: wal
```

### 通知が送られない

```bash
# デバッグスクリプト実行
python3 debug_notification.py
```

### ログ確認

```bash
# アプリケーションログ
tail -f logs/app.log

# JSON形式で整形
tail -f logs/app.log | jq
```

## 📚 関連ドキュメント

- [API Documentation](API_DOCUMENTATION.md)
- [Refactoring Specification](REFACTORING_SPECIFICATION.md)

## 📄 ライセンス

Private - 京晶蘭株式会社

## 🤝 コントリビューション

プロジェクトメンバーのみ
```

---

### Change 6.4: API_DOCUMENTATION.md 作成 (1時間)

**ファイル**: `API_DOCUMENTATION.md`

```markdown
# API Documentation

LINE Bot 勤務連絡システムのAPI仕様書

## 認証エンドポイント

### POST /auth/login
ログイン

**リクエスト**:
```json
{
  "username": "string",
  "password": "string"
}
```

**レスポンス**:
- 成功: 302 Redirect to /schedules/
- 失敗: 200 with error message

---

### GET /auth/logout
ログアウト

**レスポンス**:
- 302 Redirect to /auth/login

---

## 従業員エンドポイント

### GET /employees/
従業員一覧取得

**認証**: 必須

**レスポンス**:
```html
<!-- employees.html テンプレート -->
```

---

### POST /employees/create
従業員作成

**認証**: 必須

**リクエスト**:
```json
{
  "employee_number": "K001",
  "name": "山田太郎"
}
```

**レスポンス**:
```json
{
  "success": true
}
```

---

### POST /employees/<id>/update
従業員情報更新

**認証**: 必須

**リクエスト**:
```json
{
  "employee_number": "K001",
  "name": "山田太郎"
}
```

---

### POST /employees/<id>/delete
従業員論理削除

**認証**: 必須

**レスポンス**:
- 302 Redirect to /employees/

---

### POST /employees/<id>/hard-delete
従業員物理削除

**認証**: 必須

**レスポンス**:
- 302 Redirect to /employees/

---

## 勤務連絡エンドポイント

### GET /schedules/
勤務連絡メイン画面

**認証**: 必須

---

### POST /schedules/send
勤務連絡一括送信

**認証**: 必須

**リクエスト**:
```json
{
  "schedules": [
    {
      "employee_number": "K001",
      "work_time": "13:00"
    }
  ]
}
```

**レスポンス**:
```json
{
  "success": true,
  "sent_count": 10,
  "total": 10
}
```

---

### GET /schedules/today
本日の勤務連絡状況

**認証**: 必須

**レスポンス**:
```json
{
  "total": 10,
  "replied": 7,
  "not_replied": 3,
  "replied_list": [...],
  "not_replied_list": [...]
}
```

---

## Webhook エンドポイント

### POST /webhook/callback
LINE webhook コールバック

**ヘッダー**:
- X-Line-Signature: string (必須)

**リクエスト**:
```json
{
  "events": [...]
}
```

**レスポンス**:
```text
OK
```

---

## 設定エンドポイント

### GET /settings/
設定画面

**認証**: 必須

---

### POST /settings/managers
通知先社員設定更新

**認証**: 必須

**リクエスト**:
```json
{
  "manager_ids": [1, 2, 3]
}
```

---

## LIFF エンドポイント

### GET /liff/register
LIFF登録画面

**認証**: 不要

---

### POST /liff/register
LINE登録処理

**リクエスト**:
```json
{
  "employee_number": "K001",
  "employee_name": "山田太郎",
  "line_user_id": "U123456"
}
```

**レスポンス**:
```json
{
  "success": true
}
```

---

## ヘルスチェック

### GET /health
ヘルスチェック

**レスポンス**:
```json
{
  "status": "ok"
}
```
```

---

### Change 6.5: 複雑な関数にdocstring追加 (1時間)

**対象**: すべての複雑な関数

**例**:
```python
def send_all_replied_notification(all_replies_info: List[Dict]) -> None:
    """全員返信完了の即時通知（重複防止付き、全員分の時刻表示）

    この関数は以下の処理を行います:
    1. 本日既に通知済みかチェック（重複防止）
    2. 全員分の返信時刻をUTC→JSTに変換
    3. 通知先社員全員にメッセージ送信
    4. 通知済みフラグを記録

    Args:
        all_replies_info: 返信情報のリスト
            各要素: {'employee_name': str, 'replied_at': str (UTC)}

    Returns:
        None

    Raises:
        LineBotApiError: LINE API呼び出しに失敗した場合

    Notes:
        - replied_atはUTC時刻のため、JSTへの変換が必要
        - 重複防止のため、1日1回のみ送信可能
        - 通知済みフラグはsettingsテーブルに記録される

    Examples:
        >>> replies = [
        ...     {'employee_name': '山田太郎', 'replied_at': '2024-01-15 04:30:00'}
        ... ]
        >>> send_all_replied_notification(replies)
    """
    # 実装...
```

---

### Phase 6 検証チェックリスト

- [ ] `grep -r "print(" --include="*.py"` が空（テスト以外）
- [ ] `mypy .` がエラーなし
- [ ] README.md がGitHubで正しく表示される
- [ ] API_DOCUMENTATION.md がすべてのエンドポイントをカバー
- [ ] すべての公開関数にdocstringがある

### Phase 6 ロールバック手順

```bash
# Step 1: print()を含むファイルを復元
git checkout notification.py database.py app.py

# Step 2: ドキュメント削除（任意）
rm README.md API_DOCUMENTATION.md

# 時間: 1分
# データ損失リスク: なし
```

---

## 📊 全体サマリー

### 工数サマリー

| Phase | 内容 | 工数 | リスク |
|-------|------|------|--------|
| Phase 0 | Quick Wins | 2時間 | 🟢 VERY LOW |
| Phase 1 | Testing Foundation | 12時間 | 🟢 LOW |
| Phase 2 | Data Layer | 14時間 | 🟡 MEDIUM |
| Phase 3 | Service Layer | 16時間 | 🟡 MEDIUM |
| Phase 4 | Route Layer | 20時間 | 🔴 HIGH |
| Phase 5 | Comprehensive Testing | 18時間 | 🟢 LOW |
| Phase 6 | Cleanup & Documentation | 8時間 | 🟢 VERY LOW |
| **合計** | | **90時間** | |

### 変更サマリー

| カテゴリ | 変更数 |
|----------|--------|
| 新規ファイル作成 | 30+ |
| 既存ファイル変更 | 10+ |
| テストケース | 100+ |
| **合計** | **43変更** |

### 期待される成果

| 指標 | Before | After | 改善率 |
|------|--------|-------|--------|
| app.py サイズ | 1,155行 | 200行 | **83%削減** |
| テストカバレッジ | 0% | 85% | **∞** |
| 機能開発時間 | 4-6h | 1-2h | **66%短縮** |
| バグ修正時間 | 2-3h | 30-60m | **75%短縮** |

---

## 🚀 実装ガイド

### 開始前チェックリスト

- [ ] Gitリポジトリが最新状態
- [ ] データベースバックアップ作成済み
- [ ] ステージング環境準備済み
- [ ] 本仕様書を全員が確認

### 実装順序

1. **Phase 0**: すぐに開始可能（2時間）
2. **Phase 1**: Phase 0完了後（12時間）
3. **Phase 2**: Phase 1のテスト全PASS後（14時間）
4. **Phase 3**: Phase 2のテスト全PASS後（16時間）
5. **Phase 4**: Phase 3完了後、ステージング環境で検証（20時間）⚠️
6. **Phase 5**: Phase 4安定後（18時間）
7. **Phase 6**: 最後に実施（8時間）

### 重要な注意事項

⚠️ **Phase 4（Blueprint分割）は最もリスクが高い**
- 必ずステージング環境で検証
- 段階的デプロイ（10% → 50% → 100%）
- 48時間のモニタリング期間
- ロールバック手順を事前テスト

---

## 📞 サポート

質問や問題が発生した場合は、開発チームに連絡してください。

---

**作成日**: 2025-10-27
**バージョン**: 1.0
**ステータス**: READY FOR IMPLEMENTATION
