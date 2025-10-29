# LINE Bot Work Notification System - Refactoring Roadmap

## Executive Summary

**Current State Analysis**
- **Codebase Size**: 3,507 LOC Python
- **Main Issues**:
  - God objects (app.py: 1,155 LOC, 39 routes | database.py: 1,004 LOC, 47 functions)
  - Tight coupling (20+ imports in app.py)
  - Mixed concerns (routing + business logic + data access)
  - No test coverage
  - Inconsistent error handling (132+ logging/print statements)

**Target Architecture**
```
src/
├── api/                    # Flask routes (presentation layer)
│   ├── __init__.py
│   ├── auth_routes.py      # Authentication endpoints
│   ├── employee_routes.py  # Employee management
│   ├── schedule_routes.py  # Work schedule management
│   ├── admin_routes.py     # Admin dashboard
│   └── webhook_routes.py   # LINE webhook
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py
│   ├── employee_service.py
│   ├── schedule_service.py
│   ├── notification_service.py
│   └── sync_service.py
├── repositories/           # Data access layer
│   ├── __init__.py
│   ├── base_repository.py
│   ├── employee_repository.py
│   ├── schedule_repository.py
│   ├── workplace_repository.py
│   └── user_repository.py
├── models/                 # Domain models
│   ├── __init__.py
│   ├── employee.py
│   ├── schedule.py
│   ├── workplace.py
│   └── user.py
├── core/                   # Shared infrastructure
│   ├── __init__.py
│   ├── database.py         # Connection management
│   ├── config.py           # Configuration
│   ├── logging.py          # Logging setup
│   └── exceptions.py       # Custom exceptions
└── utils/                  # Utility functions
    ├── __init__.py
    ├── validators.py
    ├── formatters.py
    └── constants.py
tests/
├── unit/
├── integration/
└── fixtures/
```

---

## Phase 1: Foundation & Safety (Week 1)

**Objective**: Establish testing infrastructure and safety net before refactoring

### Step 1.1: Test Infrastructure Setup (4 hours)

**Actions**:
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock pytest-flask factory-boy faker
```

**Create**: `tests/conftest.py`
```python
import pytest
import tempfile
import os
from app import app as flask_app
from database import init_db, get_db_connection

@pytest.fixture
def app():
    """Create test Flask application"""
    db_fd, db_path = tempfile.mkstemp()
    os.environ['DATABASE_PATH'] = db_path

    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })

    # Initialize test database
    init_db()

    yield flask_app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()

@pytest.fixture
def db():
    """Database connection for tests"""
    conn = get_db_connection()
    yield conn
    conn.close()
```

**Success Criteria**:
- ✅ pytest runs successfully
- ✅ Test database isolated from production
- ✅ Fixtures can create/cleanup test data

**Rollback**: Simply remove test files - no impact on production

---

### Step 1.2: Characterization Tests (8 hours)

**Purpose**: Capture current behavior before refactoring

**Create**: `tests/characterization/test_critical_flows.py`
```python
import pytest
from datetime import datetime

class TestCriticalFlows:
    """Tests to ensure refactoring doesn't break existing behavior"""

    def test_employee_registration_flow(self, client, db):
        """Test complete employee registration process"""
        # Given: Employee data
        employee_data = {
            'name': '山田太郎',
            'employee_number': 'K001',
            'employee_type': 'part_time'
        }

        # When: Register employee
        response = client.post('/api/employees/register',
                              json=employee_data)

        # Then: Employee created
        assert response.status_code == 201
        data = response.get_json()
        assert data['name'] == '山田太郎'
        assert data['employee_number'] == 'K001'

    def test_line_user_linking_flow(self, client, db):
        """Test LINE user ID linking"""
        # Setup: Create employee
        from database import add_employee
        emp_id = add_employee('テスト', 'K002', 'part_time')

        # When: Link LINE user
        response = client.post('/liff/register', json={
            'employee_number': 'K002',
            'name': 'テスト',
            'line_user_id': 'U1234567890abcdef'
        })

        # Then: Link successful
        assert response.status_code == 200

    def test_work_schedule_notification_flow(self, client, db):
        """Test sending work schedule notification"""
        # Setup: Create employee with LINE ID
        from database import add_employee, update_employee_line_id
        emp_id = add_employee('通知テスト', 'K003', 'part_time')
        update_employee_line_id('K003', 'U9876543210')

        # When: Send schedule
        response = client.post('/api/schedules/send', json={
            'employee_id': emp_id,
            'work_date': '2025-11-01',
            'workplace': '本店',
            'work_time': '09:00-17:00'
        })

        # Then: Notification sent (or scheduled)
        assert response.status_code in [200, 202]
```

**Coverage Target**: >60% critical path coverage

**Metrics to Track**:
```python
# Run with coverage
pytest --cov=app --cov=database --cov-report=html
```

**Success Criteria**:
- ✅ 15+ characterization tests passing
- ✅ Critical flows documented
- ✅ Baseline coverage established

**Risk**: Low - Tests only observe, don't modify

---

### Step 1.3: Configuration Extraction (3 hours)

**Objective**: Separate configuration from code

**Create**: `src/core/config.py`
```python
import os
from datetime import timedelta
from typing import Optional

class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=24)

    # Session Security
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'

    # Database
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'database.db')

    # LINE
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
    LINE_CHANNEL_SECRET: str = os.getenv('LINE_CHANNEL_SECRET', '')
    LIFF_ID: str = os.getenv('LIFF_ID', '')

    # Rate Limiting
    RATELIMIT_STORAGE_URI: str = "memory://"
    RATELIMIT_DEFAULT: str = "200 per day, 50 per hour"

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required = ['SECRET_KEY', 'LINE_CHANNEL_ACCESS_TOKEN',
                   'LINE_CHANNEL_SECRET', 'LIFF_ID']
        missing = [key for key in required if not getattr(cls, key)]

        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        return True

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    TESTING = False

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    TESTING = False

class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False

def get_config(env: Optional[str] = None) -> Config:
    """Get configuration for environment"""
    env = env or os.getenv('FLASK_ENV', 'development')

    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }

    config_class = configs.get(env, DevelopmentConfig)
    config_class.validate()
    return config_class
```

**Migration in app.py**:
```python
# Before (lines 70-85 in app.py)
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set!")
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
# ... more scattered config

# After
from src.core.config import get_config

config = get_config()
app.config.from_object(config)
```

**Success Criteria**:
- ✅ All configuration centralized
- ✅ Environment-specific configs work
- ✅ Tests pass with TestingConfig
- ✅ Production config validated on startup

**Effort**: 3 hours
**Risk**: Low - Config object pattern is well-tested

---

### Step 1.4: Logging Standardization (4 hours)

**Objective**: Replace inconsistent logging with structured logging

**Create**: `src/core/logging.py`
```python
import logging
import sys
from typing import Optional

class StructuredLogger:
    """Structured logging with consistent format"""

    def __init__(self, name: str, level: str = 'INFO'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Avoid duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message: str, **context):
        """Log info with context"""
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context):
        """Log warning with context"""
        self._log(logging.WARNING, message, context)

    def error(self, message: str, error: Optional[Exception] = None, **context):
        """Log error with context and exception"""
        if error:
            context['error_type'] = type(error).__name__
            context['error_message'] = str(error)
        self._log(logging.ERROR, message, context)

    def debug(self, message: str, **context):
        """Log debug with context"""
        self._log(logging.DEBUG, message, context)

    def _log(self, level: int, message: str, context: dict):
        """Internal logging with context"""
        if context:
            context_str = ' | '.join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"
        self.logger.log(level, message)

def get_logger(name: str) -> StructuredLogger:
    """Get logger instance"""
    from src.core.config import get_config
    config = get_config()
    return StructuredLogger(name, config.LOG_LEVEL)
```

**Migration Pattern**:
```python
# Before (scattered in app.py, database.py)
print(f"✅ 環境変数チェック完了")
logging.info(f"Employee {employee_id} registered")
print(f"❌ エラー: {error}")

# After
from src.core.logging import get_logger
logger = get_logger(__name__)

logger.info("環境変数チェック完了")
logger.info("従業員登録完了", employee_id=employee_id, name=name)
logger.error("処理エラー", error=error, operation="employee_registration")
```

**Migration Strategy**: Gradual replacement module-by-module

**Success Criteria**:
- ✅ Consistent log format across all modules
- ✅ Structured context in all logs
- ✅ No more print() statements in production code
- ✅ Log levels properly configured

**Effort**: 4 hours (2h setup + 2h migration)
**Risk**: Low - Non-breaking change

---

## Phase 2: Data Access Layer (Week 2)

**Objective**: Extract database.py into Repository Pattern

### Step 2.1: Create Domain Models (4 hours)

**Create**: `src/models/employee.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Employee:
    """Employee domain model"""
    id: Optional[int]
    name: str
    employee_number: str
    line_user_id: Optional[str]
    employee_type: str  # 'part_time' or 'full_time'
    is_active: bool
    created_at: datetime

    def is_linked_to_line(self) -> bool:
        """Check if employee is linked to LINE"""
        return self.line_user_id is not None

    def can_receive_notifications(self) -> bool:
        """Check if employee can receive notifications"""
        return self.is_active and self.is_linked_to_line()

    @staticmethod
    def from_db_row(row) -> 'Employee':
        """Create Employee from database row"""
        return Employee(
            id=row['id'],
            name=row['name'],
            employee_number=row['employee_number'],
            line_user_id=row.get('line_user_id'),
            employee_type=row['employee_type'],
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at'])
        )
```

**Create**: `src/models/schedule.py`
```python
from dataclasses import dataclass
from datetime import datetime, date, time
from typing import Optional

@dataclass
class WorkSchedule:
    """Work schedule domain model"""
    id: Optional[int]
    employee_id: int
    work_date: date
    workplace: str
    work_time: str  # Format: "HH:MM-HH:MM"
    sent_at: Optional[datetime]
    created_at: datetime

    def is_sent(self) -> bool:
        """Check if schedule notification was sent"""
        return self.sent_at is not None

    def get_start_time(self) -> time:
        """Extract start time from work_time"""
        start_str = self.work_time.split('-')[0]
        return datetime.strptime(start_str, '%H:%M').time()

    def get_end_time(self) -> time:
        """Extract end time from work_time"""
        end_str = self.work_time.split('-')[1]
        return datetime.strptime(end_str, '%H:%M').time()

    @staticmethod
    def from_db_row(row) -> 'WorkSchedule':
        """Create WorkSchedule from database row"""
        return WorkSchedule(
            id=row['id'],
            employee_id=row['employee_id'],
            work_date=datetime.strptime(row['work_date'], '%Y-%m-%d').date(),
            workplace=row['workplace'],
            work_time=row['work_time'],
            sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None,
            created_at=datetime.fromisoformat(row['created_at'])
        )
```

**Before/After Comparison**:
```python
# Before: Raw database tuples
employee = get_employee_by_id(123)
if employee and employee[3]:  # What is index 3?
    send_notification(employee[3])

# After: Type-safe domain models
employee = employee_repo.get_by_id(123)
if employee and employee.can_receive_notifications():
    send_notification(employee.line_user_id)
```

**Success Criteria**:
- ✅ Type-safe models with clear interfaces
- ✅ Business logic methods in models
- ✅ Conversion methods for database rows
- ✅ Tests verify model behavior

**Effort**: 4 hours
**Risk**: Low - New code, doesn't modify existing

---

### Step 2.2: Base Repository Pattern (5 hours)

**Create**: `src/repositories/base_repository.py`
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List
from src.core.database import get_db_connection
from src.core.logging import get_logger

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository with common CRUD operations"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def _table_name(self) -> str:
        """Return table name"""
        pass

    @abstractmethod
    def _from_row(self, row) -> T:
        """Convert database row to domain model"""
        pass

    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name()} WHERE id = ?",
                (id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                self.logger.debug(f"取得成功", entity_id=id, table=self._table_name())
                return self._from_row(row)
            return None
        except Exception as e:
            self.logger.error(f"取得エラー", error=e, entity_id=id)
            raise

    def get_all(self, active_only: bool = True) -> List[T]:
        """Get all entities"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            query = f"SELECT * FROM {self._table_name()}"
            if active_only and self._has_active_column():
                query += " WHERE is_active = 1"

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            entities = [self._from_row(row) for row in rows]
            self.logger.info(f"全件取得", count=len(entities), table=self._table_name())
            return entities
        except Exception as e:
            self.logger.error(f"全件取得エラー", error=e)
            raise

    def delete(self, id: int) -> bool:
        """Delete entity by ID"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM {self._table_name()} WHERE id = ?",
                (id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()

            if deleted:
                self.logger.info(f"削除成功", entity_id=id, table=self._table_name())
            return deleted
        except Exception as e:
            self.logger.error(f"削除エラー", error=e, entity_id=id)
            raise

    def _has_active_column(self) -> bool:
        """Check if table has is_active column"""
        # Override in child classes if needed
        return False
```

**Success Criteria**:
- ✅ Base CRUD operations abstracted
- ✅ Consistent error handling
- ✅ Logging in all operations
- ✅ Type safety with generics

---

### Step 2.3: Employee Repository (6 hours)

**Create**: `src/repositories/employee_repository.py`
```python
from typing import Optional, List
from src.repositories.base_repository import BaseRepository
from src.models.employee import Employee
from src.core.database import get_db_connection

class EmployeeRepository(BaseRepository[Employee]):
    """Repository for employee data access"""

    def _table_name(self) -> str:
        return "employees"

    def _from_row(self, row) -> Employee:
        return Employee.from_db_row(row)

    def _has_active_column(self) -> bool:
        return True

    def get_by_employee_number(self, employee_number: str) -> Optional[Employee]:
        """Get employee by employee number (case-insensitive)"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM employees WHERE LOWER(employee_number) = LOWER(?)",
                (employee_number,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                self.logger.debug("従業員番号で取得", employee_number=employee_number)
                return self._from_row(row)
            return None
        except Exception as e:
            self.logger.error("従業員番号取得エラー", error=e, employee_number=employee_number)
            raise

    def get_by_line_user_id(self, line_user_id: str) -> Optional[Employee]:
        """Get employee by LINE user ID"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM employees WHERE line_user_id = ?",
                (line_user_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                self.logger.debug("LINE IDで取得", line_user_id=line_user_id)
                return self._from_row(row)
            return None
        except Exception as e:
            self.logger.error("LINE ID取得エラー", error=e, line_user_id=line_user_id)
            raise

    def create(self, name: str, employee_number: str, employee_type: str) -> Employee:
        """Create new employee"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO employees (name, employee_number, employee_type, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (name, employee_number, employee_type)
            )
            employee_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.logger.info("従業員作成", employee_id=employee_id,
                           name=name, employee_number=employee_number)

            return self.get_by_id(employee_id)
        except Exception as e:
            self.logger.error("従業員作成エラー", error=e,
                            name=name, employee_number=employee_number)
            raise

    def update_line_user_id(self, employee_id: int, line_user_id: str) -> bool:
        """Link LINE user ID to employee"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE employees SET line_user_id = ? WHERE id = ?",
                (line_user_id, employee_id)
            )
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()

            if updated:
                self.logger.info("LINE ID紐付け", employee_id=employee_id,
                               line_user_id=line_user_id)
            return updated
        except Exception as e:
            self.logger.error("LINE ID紐付けエラー", error=e,
                            employee_id=employee_id)
            raise

    def get_by_type(self, employee_type: str, active_only: bool = True) -> List[Employee]:
        """Get employees by type"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM employees WHERE employee_type = ?"
            params = [employee_type]

            if active_only:
                query += " AND is_active = 1"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            employees = [self._from_row(row) for row in rows]
            self.logger.info("タイプ別取得", employee_type=employee_type, count=len(employees))
            return employees
        except Exception as e:
            self.logger.error("タイプ別取得エラー", error=e, employee_type=employee_type)
            raise

    def get_available_employee_numbers(self) -> List[str]:
        """Get list of available (deleted) employee numbers"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT employee_number
                FROM employees
                WHERE is_active = 0
                ORDER BY employee_number
                """
            )
            rows = cursor.fetchall()
            conn.close()

            numbers = [row['employee_number'] for row in rows]
            self.logger.debug("利用可能番号取得", count=len(numbers))
            return numbers
        except Exception as e:
            self.logger.error("利用可能番号取得エラー", error=e)
            raise
```

**Migration Strategy**:
```python
# Before (in database.py - 47 functions)
def get_employee_by_id(employee_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
    return cursor.fetchone()

# After (in service layer)
from src.repositories.employee_repository import EmployeeRepository

employee_repo = EmployeeRepository()
employee = employee_repo.get_by_id(employee_id)
```

**Success Criteria**:
- ✅ All employee database operations in repository
- ✅ Type-safe Employee objects returned
- ✅ Consistent error handling
- ✅ Tests cover all repository methods
- ✅ Old database.py functions still work (parallel operation)

**Effort**: 6 hours
**Risk**: Medium - Running parallel with old code during migration

---

### Step 2.4: Schedule & Workplace Repositories (6 hours)

**Similar pattern for**:
- `src/repositories/schedule_repository.py` - Work schedule operations
- `src/repositories/workplace_repository.py` - Workplace master data
- `src/repositories/reply_repository.py` - Reply tracking

**Consolidation Result**:
```
Before: database.py (1,004 LOC, 47 functions)
After:  4 repositories (avg 150 LOC each, 8-12 methods)

Complexity Reduction:
- Cyclomatic complexity: 47 → 12 (per module)
- Cognitive load: One file → Four focused files
- Testability: Monolithic → Isolated repositories
```

**Success Criteria**:
- ✅ Each repository < 200 LOC
- ✅ Single Responsibility Principle adhered
- ✅ 80%+ test coverage for repositories
- ✅ database.py deprecated but not removed yet

**Effort**: 6 hours total
**Risk**: Medium

---

## Phase 3: Service Layer (Week 3)

**Objective**: Extract business logic from app.py into services

### Step 3.1: Employee Service (8 hours)

**Create**: `src/services/employee_service.py`
```python
from typing import List, Optional, Tuple
from src.repositories.employee_repository import EmployeeRepository
from src.models.employee import Employee
from src.core.logging import get_logger
from src.core.exceptions import (
    EmployeeNotFoundError,
    DuplicateEmployeeNumberError,
    ValidationError
)
from src.utils.validators import (
    validate_employee_number,
    validate_employee_name,
    validate_employee_type
)

class EmployeeService:
    """Business logic for employee management"""

    def __init__(self):
        self.repo = EmployeeRepository()
        self.logger = get_logger(__name__)

    def register_employee(
        self,
        name: str,
        employee_number: str,
        employee_type: str
    ) -> Tuple[Employee, bool]:
        """
        Register new employee

        Returns:
            (Employee, is_reactivated): Employee object and whether it was reactivated

        Raises:
            ValidationError: Invalid input data
            DuplicateEmployeeNumberError: Employee number already in use
        """
        # Validation
        validate_employee_name(name)
        validate_employee_number(employee_number)
        validate_employee_type(employee_type)

        # Check if employee number exists
        existing = self.repo.get_by_employee_number(employee_number)

        if existing and existing.is_active:
            self.logger.warning("従業員番号重複", employee_number=employee_number)
            raise DuplicateEmployeeNumberError(
                f"従業員番号 {employee_number} は既に使用されています"
            )

        if existing and not existing.is_active:
            # Reactivate deleted employee
            employee = self._reactivate_employee(existing.id, name, employee_type)
            self.logger.info("従業員再登録", employee_id=employee.id,
                           employee_number=employee_number)
            return employee, True

        # Create new employee
        employee = self.repo.create(name, employee_number, employee_type)
        self.logger.info("従業員新規登録", employee_id=employee.id,
                       employee_number=employee_number)
        return employee, False

    def link_line_account(
        self,
        employee_number: str,
        name: str,
        line_user_id: str
    ) -> Employee:
        """
        Link LINE account to employee

        Security: Requires name confirmation to prevent unauthorized linking

        Raises:
            EmployeeNotFoundError: Employee not found
            ValidationError: Name doesn't match
        """
        # Find employee
        employee = self.repo.get_by_employee_number(employee_number)
        if not employee:
            self.logger.warning("従業員未登録", employee_number=employee_number)
            raise EmployeeNotFoundError(
                f"従業員番号 {employee_number} が見つかりません"
            )

        # Name confirmation (security check)
        if employee.name != name:
            self.logger.warning("名前不一致",
                              employee_number=employee_number,
                              expected=employee.name,
                              provided=name)
            raise ValidationError(
                "名前が一致しません。正しい名前を入力してください。"
            )

        # Check if already linked to another employee
        existing_link = self.repo.get_by_line_user_id(line_user_id)
        if existing_link and existing_link.id != employee.id:
            self.logger.warning("LINE ID重複",
                              line_user_id=line_user_id,
                              existing_employee=existing_link.employee_number)
            raise ValidationError(
                "このLINEアカウントは既に別の従業員番号に紐付けられています"
            )

        # Link LINE ID
        self.repo.update_line_user_id(employee.id, line_user_id)
        self.logger.info("LINE紐付け成功",
                       employee_id=employee.id,
                       employee_number=employee_number)

        return self.repo.get_by_id(employee.id)

    def get_employees_by_type(
        self,
        employee_type: str,
        active_only: bool = True
    ) -> List[Employee]:
        """Get employees filtered by type"""
        validate_employee_type(employee_type)
        return self.repo.get_by_type(employee_type, active_only)

    def deactivate_employee(self, employee_id: int) -> bool:
        """Soft delete employee"""
        employee = self.repo.get_by_id(employee_id)
        if not employee:
            raise EmployeeNotFoundError(f"従業員ID {employee_id} が見つかりません")

        success = self.repo.update_active_status(employee_id, False)
        if success:
            self.logger.info("従業員無効化", employee_id=employee_id)
        return success

    def _reactivate_employee(
        self,
        employee_id: int,
        new_name: str,
        new_type: str
    ) -> Employee:
        """Reactivate previously deleted employee"""
        # Update details and reactivate
        self.repo.update(employee_id, name=new_name, employee_type=new_type)
        self.repo.update_active_status(employee_id, True)
        return self.repo.get_by_id(employee_id)
```

**Before/After Comparison**:
```python
# Before (in app.py route)
@app.route('/api/employees/register', methods=['POST'])
def register_employee():
    data = request.json
    name = data.get('name')
    employee_number = data.get('employee_number')
    employee_type = data.get('employee_type')

    # Validation scattered
    if not name or len(name) > 50:
        return jsonify({'error': 'Invalid name'}), 400

    # Business logic in route
    existing = get_employee_by_number(employee_number)
    if existing:
        if existing['is_active']:
            return jsonify({'error': 'Duplicate'}), 400
        else:
            # Reactivation logic here...
            pass

    # Database call directly from route
    employee_id = add_employee(name, employee_number, employee_type)
    return jsonify({'id': employee_id}), 201

# After (in app.py route)
@app.route('/api/employees/register', methods=['POST'])
def register_employee():
    try:
        data = request.json
        employee, is_reactivated = employee_service.register_employee(
            name=data['name'],
            employee_number=data['employee_number'],
            employee_type=data['employee_type']
        )

        status = 200 if is_reactivated else 201
        return jsonify({
            'id': employee.id,
            'name': employee.name,
            'employee_number': employee.employee_number,
            'reactivated': is_reactivated
        }), status
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except DuplicateEmployeeNumberError as e:
        return jsonify({'error': str(e)}), 409
```

**Benefits**:
- ✅ Business logic testable without Flask
- ✅ Validation centralized
- ✅ Clear error handling
- ✅ Reusable across endpoints

**Success Criteria**:
- ✅ All employee business logic in service
- ✅ 90%+ test coverage (unit tests without Flask)
- ✅ Routes become thin controllers

**Effort**: 8 hours
**Risk**: Medium

---

### Step 3.2: Schedule Service (8 hours)

**Create**: `src/services/schedule_service.py`
```python
from typing import List, Optional
from datetime import date, datetime
from src.repositories.schedule_repository import ScheduleRepository
from src.repositories.employee_repository import EmployeeRepository
from src.models.schedule import WorkSchedule
from src.core.logging import get_logger
from src.core.exceptions import EmployeeNotFoundError, ValidationError

class ScheduleService:
    """Business logic for work schedule management"""

    def __init__(self):
        self.schedule_repo = ScheduleRepository()
        self.employee_repo = EmployeeRepository()
        self.logger = get_logger(__name__)

    def create_schedule(
        self,
        employee_id: int,
        work_date: date,
        workplace: str,
        work_time: str
    ) -> WorkSchedule:
        """
        Create work schedule for employee

        Raises:
            EmployeeNotFoundError: Employee doesn't exist
            ValidationError: Invalid schedule data
        """
        # Validate employee exists and can receive notifications
        employee = self.employee_repo.get_by_id(employee_id)
        if not employee:
            raise EmployeeNotFoundError(f"従業員ID {employee_id} が見つかりません")

        if not employee.can_receive_notifications():
            raise ValidationError(
                f"従業員 {employee.name} は通知を受信できません。"
                "LINE連携が必要です。"
            )

        # Create schedule
        schedule = self.schedule_repo.create(
            employee_id=employee_id,
            work_date=work_date,
            workplace=workplace,
            work_time=work_time
        )

        self.logger.info("勤務予定作成",
                       schedule_id=schedule.id,
                       employee_id=employee_id,
                       work_date=str(work_date))

        return schedule

    def get_pending_schedules(self, work_date: date) -> List[WorkSchedule]:
        """Get schedules without replies for given date"""
        return self.schedule_repo.get_pending_by_date(work_date)

    def check_all_replied(self, work_date: date) -> bool:
        """Check if all employees replied for given date"""
        pending = self.get_pending_schedules(work_date)
        return len(pending) == 0
```

**Success Criteria**:
- ✅ Schedule business logic isolated
- ✅ Cross-repository coordination handled
- ✅ Validation before database operations

**Effort**: 8 hours

---

### Step 3.3: Notification Service (6 hours)

**Consolidate**: `notification.py` + `line_sender.py` → `src/services/notification_service.py`

**Result**:
- Unified notification logic
- Consistent error handling
- Better retry mechanisms
- Centralized LINE API interaction

**Effort**: 6 hours

---

## Phase 4: Route Layer (Week 4)

**Objective**: Break down app.py into focused route modules

### Step 4.1: Route Modularization (10 hours)

**Split app.py (1,155 LOC, 39 routes) into**:

1. `src/api/auth_routes.py` (5 routes)
   - `/login`, `/logout`, `/change-password`

2. `src/api/employee_routes.py` (12 routes)
   - Employee CRUD, LINE linking, type management

3. `src/api/schedule_routes.py` (10 routes)
   - Schedule creation, sending, reply tracking

4. `src/api/admin_routes.py` (8 routes)
   - Settings, managers, dashboard

5. `src/api/webhook_routes.py` (4 routes)
   - LINE webhook, LIFF endpoints

**Example**: `src/api/employee_routes.py`
```python
from flask import Blueprint, request, jsonify
from src.services.employee_service import EmployeeService
from src.core.exceptions import ValidationError, DuplicateEmployeeNumberError
from src.core.logging import get_logger
from auth import require_auth

employee_bp = Blueprint('employees', __name__, url_prefix='/api/employees')
employee_service = EmployeeService()
logger = get_logger(__name__)

@employee_bp.route('/register', methods=['POST'])
@require_auth
def register():
    """Register new employee"""
    try:
        data = request.json
        employee, is_reactivated = employee_service.register_employee(
            name=data['name'],
            employee_number=data['employee_number'],
            employee_type=data['employee_type']
        )

        return jsonify({
            'id': employee.id,
            'name': employee.name,
            'employee_number': employee.employee_number,
            'reactivated': is_reactivated
        }), 200 if is_reactivated else 201

    except ValidationError as e:
        logger.warning("登録バリデーションエラー", error=str(e))
        return jsonify({'error': str(e)}), 400
    except DuplicateEmployeeNumberError as e:
        logger.warning("従業員番号重複", error=str(e))
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        logger.error("登録エラー", error=e)
        return jsonify({'error': '内部エラーが発生しました'}), 500

@employee_bp.route('/<int:employee_id>', methods=['GET'])
@require_auth
def get_employee(employee_id):
    """Get employee details"""
    try:
        employee = employee_service.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': '従業員が見つかりません'}), 404

        return jsonify({
            'id': employee.id,
            'name': employee.name,
            'employee_number': employee.employee_number,
            'employee_type': employee.employee_type,
            'has_line_id': employee.is_linked_to_line(),
            'is_active': employee.is_active
        }), 200
    except Exception as e:
        logger.error("取得エラー", error=e, employee_id=employee_id)
        return jsonify({'error': '内部エラーが発生しました'}), 500

# ... more routes
```

**Main app.py becomes**:
```python
from flask import Flask
from src.core.config import get_config
from src.core.logging import get_logger
from src.core.database import init_db
from src.api.auth_routes import auth_bp
from src.api.employee_routes import employee_bp
from src.api.schedule_routes import schedule_bp
from src.api.admin_routes import admin_bp
from src.api.webhook_routes import webhook_bp

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)

    # Configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Initialize extensions
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(app=app, key_func=get_remote_address)

    # Initialize database
    init_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(webhook_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run()
```

**Result**:
```
Before: app.py (1,155 LOC, 39 routes, cyclomatic complexity ~150)
After:
  - app.py (50 LOC, 0 routes, application factory)
  - 5 route modules (avg 120 LOC, 5-12 routes each)

Benefits:
- Easier to navigate
- Focused testing
- Clear separation of concerns
- Application factory pattern
```

**Success Criteria**:
- ✅ All routes migrated to blueprints
- ✅ Each blueprint < 200 LOC
- ✅ app.py < 100 LOC
- ✅ All tests still pass

**Effort**: 10 hours
**Risk**: Medium (requires careful route migration)

---

## Phase 5: Testing & Quality (Week 5)

### Step 5.1: Comprehensive Unit Tests (12 hours)

**Target Coverage**: 80%+

**Create tests for**:
1. **Repositories** (`tests/unit/repositories/`)
   - Database operations
   - Error handling
   - Edge cases

2. **Services** (`tests/unit/services/`)
   - Business logic
   - Validation
   - Cross-service coordination

3. **Models** (`tests/unit/models/`)
   - Domain logic
   - Conversions
   - Utilities

**Example**: `tests/unit/services/test_employee_service.py`
```python
import pytest
from src.services.employee_service import EmployeeService
from src.core.exceptions import (
    DuplicateEmployeeNumberError,
    ValidationError,
    EmployeeNotFoundError
)

class TestEmployeeService:

    @pytest.fixture
    def service(self):
        return EmployeeService()

    def test_register_new_employee_success(self, service, db):
        """Test successful employee registration"""
        # Given: Valid employee data
        name = "山田太郎"
        employee_number = "K001"
        employee_type = "part_time"

        # When: Register employee
        employee, is_reactivated = service.register_employee(
            name, employee_number, employee_type
        )

        # Then: Employee created
        assert employee.name == name
        assert employee.employee_number == employee_number
        assert employee.employee_type == employee_type
        assert not is_reactivated
        assert employee.is_active

    def test_register_duplicate_active_employee_fails(self, service, db):
        """Test registering duplicate active employee fails"""
        # Given: Existing active employee
        service.register_employee("山田太郎", "K001", "part_time")

        # When/Then: Registering duplicate fails
        with pytest.raises(DuplicateEmployeeNumberError):
            service.register_employee("佐藤花子", "K001", "full_time")

    def test_register_reactivates_deleted_employee(self, service, db):
        """Test reactivating previously deleted employee"""
        # Given: Deleted employee
        emp, _ = service.register_employee("山田太郎", "K001", "part_time")
        service.deactivate_employee(emp.id)

        # When: Register with same number but different details
        reactivated, is_reactivated = service.register_employee(
            "佐藤花子", "K001", "full_time"
        )

        # Then: Employee reactivated with new details
        assert is_reactivated
        assert reactivated.id == emp.id
        assert reactivated.name == "佐藤花子"
        assert reactivated.employee_type == "full_time"
        assert reactivated.is_active

    def test_link_line_account_success(self, service, db):
        """Test successful LINE account linking"""
        # Given: Registered employee
        emp, _ = service.register_employee("山田太郎", "K001", "part_time")

        # When: Link LINE account with correct name
        linked = service.link_line_account(
            employee_number="K001",
            name="山田太郎",
            line_user_id="U1234567890"
        )

        # Then: LINE ID linked
        assert linked.line_user_id == "U1234567890"
        assert linked.is_linked_to_line()

    def test_link_line_account_wrong_name_fails(self, service, db):
        """Test LINE linking fails with wrong name"""
        # Given: Registered employee
        service.register_employee("山田太郎", "K001", "part_time")

        # When/Then: Link with wrong name fails (security check)
        with pytest.raises(ValidationError, match="名前が一致しません"):
            service.link_line_account(
                employee_number="K001",
                name="佐藤花子",  # Wrong name
                line_user_id="U1234567890"
            )

    def test_link_line_account_to_nonexistent_employee_fails(self, service, db):
        """Test linking to non-existent employee fails"""
        # When/Then: Link to non-existent employee fails
        with pytest.raises(EmployeeNotFoundError):
            service.link_line_account(
                employee_number="K999",
                name="誰か",
                line_user_id="U1234567890"
            )

    @pytest.mark.parametrize("invalid_number", [
        "",           # Empty
        "K",          # Too short
        "K12345",     # Too long
        "A001",       # Wrong prefix
        "k001",       # Lowercase (should normalize)
    ])
    def test_register_invalid_employee_number_fails(
        self, service, db, invalid_number
    ):
        """Test registration with invalid employee numbers"""
        with pytest.raises(ValidationError):
            service.register_employee(
                name="山田太郎",
                employee_number=invalid_number,
                employee_type="part_time"
            )
```

**Success Criteria**:
- ✅ 80%+ code coverage
- ✅ All critical paths tested
- ✅ Edge cases covered
- ✅ Fast test execution (< 5 seconds)

**Effort**: 12 hours
**Risk**: Low

---

### Step 5.2: Integration Tests (8 hours)

**Create**: `tests/integration/test_employee_flow.py`
```python
import pytest
from flask import json

class TestEmployeeIntegrationFlow:
    """Test complete employee management flows"""

    def test_complete_employee_registration_and_linking_flow(self, client, db):
        """Test full flow: register → link LINE → receive notification"""

        # Step 1: Register employee via admin
        response = client.post('/api/employees/register',
            headers={'Authorization': 'Basic YWRtaW46cGFzc3dvcmQ='},
            json={
                'name': '山田太郎',
                'employee_number': 'K001',
                'employee_type': 'part_time'
            }
        )
        assert response.status_code == 201
        employee_id = response.json['id']

        # Step 2: Employee links LINE account via LIFF
        response = client.post('/liff/register', json={
            'employee_number': 'K001',
            'name': '山田太郎',
            'line_user_id': 'U1234567890'
        })
        assert response.status_code == 200

        # Step 3: Admin sends work schedule
        response = client.post('/api/schedules/send',
            headers={'Authorization': 'Basic YWRtaW46cGFzc3dvcmQ='},
            json={
                'employee_id': employee_id,
                'work_date': '2025-11-01',
                'workplace': '本店',
                'work_time': '09:00-17:00'
            }
        )
        assert response.status_code == 200

        # Step 4: Verify schedule in database
        response = client.get(f'/api/schedules?employee_id={employee_id}',
            headers={'Authorization': 'Basic YWRtaW46cGFzc3dvcmQ='}
        )
        assert response.status_code == 200
        schedules = response.json['schedules']
        assert len(schedules) > 0
        assert schedules[0]['employee_id'] == employee_id
```

**Success Criteria**:
- ✅ All critical user flows tested end-to-end
- ✅ Database state verified
- ✅ API contracts validated

**Effort**: 8 hours
**Risk**: Low

---

### Step 5.3: Code Quality Enforcement (4 hours)

**Setup linting and formatting**:

`pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 100

[tool.pylint.messages_control]
max-line-length = 100
disable = [
    "C0111",  # missing-docstring (handled by ruff)
]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

**Pre-commit hooks**: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100']
```

**Success Criteria**:
- ✅ All code formatted consistently
- ✅ No linting errors
- ✅ Pre-commit hooks installed
- ✅ CI pipeline runs checks

**Effort**: 4 hours
**Risk**: Low

---

## Phase 6: Deprecation & Cleanup (Week 6)

### Step 6.1: Parallel Operation Validation (8 hours)

**Ensure both old and new code work simultaneously**

Create comparison tests:
```python
def test_old_vs_new_employee_creation():
    """Verify old and new implementations produce same results"""
    # Old way
    from database import add_employee as old_add
    old_id = old_add("山田太郎", "K001", "part_time")

    # New way
    from src.services.employee_service import EmployeeService
    service = EmployeeService()
    new_emp, _ = service.register_employee("山田太郎", "K002", "part_time")

    # Verify both work
    assert old_id > 0
    assert new_emp.id > 0
```

**Success Criteria**:
- ✅ All routes work with new services
- ✅ Old database.py functions still work
- ✅ No breaking changes in API

**Effort**: 8 hours
**Risk**: Low (validation only)

---

### Step 6.2: Gradual Deprecation (6 hours)

**Mark old code as deprecated**:

```python
# database.py
import warnings

def add_employee(name, employee_number, employee_type):
    """
    DEPRECATED: Use src.services.employee_service.EmployeeService.register_employee

    This function will be removed in version 2.0
    """
    warnings.warn(
        "database.add_employee is deprecated. "
        "Use EmployeeService.register_employee instead",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing implementation
```

**Success Criteria**:
- ✅ All deprecated functions marked
- ✅ Deprecation warnings logged
- ✅ Migration guide documented

**Effort**: 6 hours
**Risk**: Low

---

### Step 6.3: Final Cleanup (4 hours)

**Remove old code**:
1. Delete `database.py` (replaced by repositories)
2. Delete old `app.py` (replaced by blueprints)
3. Remove deprecated functions
4. Clean up unused imports

**Final structure**:
```
Before:
  app.py (1,155 LOC)
  database.py (1,004 LOC)
  Total: 2,159 LOC in 2 files

After:
  src/api/ (5 files, avg 120 LOC) = 600 LOC
  src/services/ (3 files, avg 200 LOC) = 600 LOC
  src/repositories/ (4 files, avg 150 LOC) = 600 LOC
  src/models/ (3 files, avg 80 LOC) = 240 LOC
  src/core/ (4 files, avg 100 LOC) = 400 LOC
  Total: 2,440 LOC in 19 files

Metrics:
  - Cyclomatic complexity: 150 → ~15 (per module)
  - Average function length: 45 → 12 lines
  - Test coverage: 0% → 80%+
  - Module cohesion: Low → High
```

**Success Criteria**:
- ✅ No old code remaining
- ✅ All tests pass
- ✅ Code quality metrics improved
- ✅ Documentation updated

**Effort**: 4 hours
**Risk**: Low (well-tested at this point)

---

## Success Metrics & Validation

### Quantitative Metrics

| Metric | Before | After | Target |
|--------|---------|-------|---------|
| Lines of Code (largest file) | 1,155 | 240 | < 300 |
| Functions per module | 47 | 12 | < 15 |
| Cyclomatic Complexity | 150 | 15 | < 20 |
| Test Coverage | 0% | 85% | > 80% |
| Import Count (main) | 20 | 5 | < 10 |
| Average Function Length | 45 | 12 | < 20 |

### Qualitative Improvements

**Before Refactoring**:
- ❌ Hard to test (tight coupling)
- ❌ Difficult to navigate (1000+ LOC files)
- ❌ Unclear responsibilities
- ❌ Mixed concerns (routing + logic + data)
- ❌ No type safety

**After Refactoring**:
- ✅ Highly testable (80%+ coverage)
- ✅ Easy to navigate (focused modules)
- ✅ Clear responsibilities (SOLID)
- ✅ Separated concerns (layered architecture)
- ✅ Type-safe domain models

### Risk Mitigation Strategies

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| Breaking existing functionality | Medium | High | Characterization tests + parallel operation |
| Performance degradation | Low | Medium | Performance testing + profiling |
| Team resistance | Medium | Low | Gradual migration + documentation |
| Incomplete migration | Low | Medium | Phase-by-phase validation |
| Test maintenance burden | Medium | Low | Focus on integration tests |

---

## Timeline Summary

| Phase | Duration | Cumulative | Risk Level |
|-------|----------|------------|------------|
| Phase 1: Foundation | 1 week | 1 week | 🟢 Low |
| Phase 2: Data Layer | 1 week | 2 weeks | 🟡 Medium |
| Phase 3: Service Layer | 1 week | 3 weeks | 🟡 Medium |
| Phase 4: Route Layer | 1 week | 4 weeks | 🟡 Medium |
| Phase 5: Testing | 1 week | 5 weeks | 🟢 Low |
| Phase 6: Cleanup | 1 week | 6 weeks | 🟢 Low |

**Total Effort**: 6 weeks (120 hours)

**Recommended Pace**: 20 hours/week = 6 weeks calendar time

---

## Rollback Strategy

Each phase has a rollback plan:

1. **Phase 1-2**: Simply remove new files, no changes to existing code
2. **Phase 3-4**: Keep old code parallel until validation complete
3. **Phase 5**: Tests only, no rollback needed
4. **Phase 6**: Git branch per phase, can revert individual commits

**Git Branching Strategy**:
```
main
├── refactor/phase-1-foundation
├── refactor/phase-2-repositories
├── refactor/phase-3-services
├── refactor/phase-4-routes
├── refactor/phase-5-testing
└── refactor/phase-6-cleanup
```

---

## Conclusion

This refactoring plan transforms a monolithic 3,507 LOC codebase into a clean, maintainable, testable architecture following SOLID principles. The incremental approach ensures safety, with each phase delivering measurable value and providing rollback points.

**Key Benefits**:
- 🎯 80%+ test coverage (from 0%)
- 📦 Modular architecture (19 focused modules vs 2 monoliths)
- 🔧 Easy to maintain (avg 120 LOC/module)
- 🚀 Fast onboarding (clear separation of concerns)
- 🛡️ Type-safe (domain models + validation)
- 🧪 Highly testable (layered architecture)

**Next Steps**:
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1 (Foundation)
4. Weekly progress reviews
5. Adjust timeline based on actual velocity

---

*Generated: 2025-10-27*
*Version: 1.0*
