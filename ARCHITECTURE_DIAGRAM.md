# Architecture Transformation Diagram

## Current Architecture (Monolithic)

```
┌─────────────────────────────────────────────────────────────────┐
│                          Flask App                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              app.py (1,155 LOC)                          │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────┐    │  │
│  │  │  Routes (39 endpoints)                         │    │  │
│  │  │  - /api/employees/*                            │    │  │
│  │  │  - /api/schedules/*                            │    │  │
│  │  │  - /admin/*                                     │    │  │
│  │  │  - /liff/*                                      │    │  │
│  │  │  - /webhook                                     │    │  │
│  │  └────────────────────────────────────────────────┘    │  │
│  │                       ↓↑                                │  │
│  │  ┌────────────────────────────────────────────────┐    │  │
│  │  │  Business Logic (mixed in routes)              │    │  │
│  │  │  - Validation                                   │    │  │
│  │  │  - Business rules                               │    │  │
│  │  │  - Error handling                               │    │  │
│  │  └────────────────────────────────────────────────┘    │  │
│  │                       ↓↑                                │  │
│  │  ┌────────────────────────────────────────────────┐    │  │
│  │  │  Direct Database Calls                          │    │  │
│  │  │  - Raw SQL scattered                            │    │  │
│  │  │  - No abstraction                               │    │  │
│  │  └────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│              database.py (1,004 LOC)                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  47 scattered functions                                  │  │
│  │  - get_employee_by_id()                                  │  │
│  │  - get_employee_by_number()                              │  │
│  │  - get_part_time_employees()                             │  │
│  │  - get_full_time_employees()                             │  │
│  │  - add_employee()                                        │  │
│  │  - update_employee()                                     │  │
│  │  - add_work_schedule()                                   │  │
│  │  - get_schedules_with_reply_status()                    │  │
│  │  - ... (39 more functions)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                       SQLite Database                           │
│                        database.db                              │
└─────────────────────────────────────────────────────────────────┘

Problems:
❌ Tight coupling (everything depends on everything)
❌ Hard to test (requires full Flask + DB setup)
❌ Mixed concerns (routing + logic + data access)
❌ No abstraction (direct SQL everywhere)
❌ Code duplication (similar queries repeated)
❌ No type safety (raw tuples/dicts)
```

---

## Target Architecture (Layered)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Layer 1: API (Presentation)                      │
│                          src/api/                                    │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │ auth_routes.py │  │employee_routes │  │schedule_routes │       │
│  │                │  │     .py        │  │     .py        │       │
│  │ 5 routes       │  │ 12 routes      │  │ 10 routes      │       │
│  │ ~100 LOC       │  │ ~150 LOC       │  │ ~140 LOC       │       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐                            │
│  │ admin_routes   │  │ webhook_routes │                            │
│  │     .py        │  │     .py        │                            │
│  │ 8 routes       │  │ 4 routes       │                            │
│  │ ~120 LOC       │  │ ~90 LOC        │                            │
│  └────────────────┘  └────────────────┘                            │
│                                                                      │
│  Responsibilities:                                                  │
│  ✅ HTTP request/response handling                                  │
│  ✅ Authentication/authorization                                    │
│  ✅ Input parsing                                                   │
│  ✅ Response formatting                                             │
│  ❌ NO business logic                                               │
│  ❌ NO database access                                              │
└──────────────────────────────────────────────────────────────────────┘
                              ↓↑
┌──────────────────────────────────────────────────────────────────────┐
│                   Layer 2: Services (Business Logic)                 │
│                         src/services/                                │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │ employee_service.py  │  │ schedule_service.py  │                │
│  │                      │  │                      │                │
│  │ - register()         │  │ - create_schedule()  │                │
│  │ - link_line()        │  │ - send_notification()│                │
│  │ - deactivate()       │  │ - track_reply()      │                │
│  │ - get_by_type()      │  │ - get_pending()      │                │
│  │                      │  │                      │                │
│  │ ~200 LOC             │  │ ~180 LOC             │                │
│  └──────────────────────┘  └──────────────────────┘                │
│                                                                      │
│  ┌──────────────────────┐                                           │
│  │notification_service  │                                           │
│  │        .py           │                                           │
│  │                      │                                           │
│  │ - send_bulk()        │                                           │
│  │ - send_single()      │                                           │
│  │ - send_late_notice() │                                           │
│  │                      │                                           │
│  │ ~150 LOC             │                                           │
│  └──────────────────────┘                                           │
│                                                                      │
│  Responsibilities:                                                  │
│  ✅ Business rules enforcement                                      │
│  ✅ Validation                                                      │
│  ✅ Orchestration (multiple repositories)                           │
│  ✅ Transaction management                                          │
│  ❌ NO HTTP handling                                                │
│  ❌ NO direct SQL                                                   │
└──────────────────────────────────────────────────────────────────────┘
                              ↓↑
┌──────────────────────────────────────────────────────────────────────┐
│                Layer 3: Repositories (Data Access)                   │
│                       src/repositories/                              │
│                                                                      │
│  ┌────────────────────┐                                             │
│  │base_repository.py  │  (Generic CRUD operations)                 │
│  │                    │                                             │
│  │ - get_by_id()      │                                             │
│  │ - get_all()        │                                             │
│  │ - delete()         │                                             │
│  │ - _from_row()      │  (abstract)                                │
│  │                    │                                             │
│  │ ~100 LOC           │                                             │
│  └────────────────────┘                                             │
│           ↑                                                          │
│  ┌────────┴────────┬──────────────────┬──────────────────┐         │
│  │                 │                  │                  │         │
│  ├─────────────────┤  ├───────────────┤  ├──────────────┤         │
│  │employee_repo.py │  │schedule_repo  │  │workplace_repo│         │
│  │                 │  │    .py        │  │    .py       │         │
│  │ - get_by_number │  │ - get_pending │  │ - get_active │         │
│  │ - get_by_line_id│  │ - get_by_date │  │ - create()   │         │
│  │ - create()      │  │ - create()    │  │ - update()   │         │
│  │ - update()      │  │ - update()    │  │              │         │
│  │                 │  │               │  │              │         │
│  │ ~150 LOC        │  │ ~140 LOC      │  │ ~120 LOC     │         │
│  └─────────────────┘  └───────────────┘  └──────────────┘         │
│                                                                      │
│  Responsibilities:                                                  │
│  ✅ Database operations (SQL)                                       │
│  ✅ Row to domain model conversion                                  │
│  ✅ Query optimization                                              │
│  ❌ NO business logic                                               │
│  ❌ NO validation                                                   │
└──────────────────────────────────────────────────────────────────────┘
                              ↓↑
┌──────────────────────────────────────────────────────────────────────┐
│                   Layer 4: Models (Domain)                           │
│                        src/models/                                   │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │  employee.py   │  │  schedule.py   │  │ workplace.py   │       │
│  │                │  │                │  │                │       │
│  │  @dataclass    │  │  @dataclass    │  │  @dataclass    │       │
│  │  Employee:     │  │  WorkSchedule: │  │  Workplace:    │       │
│  │  - id          │  │  - id          │  │  - id          │       │
│  │  - name        │  │  - employee_id │  │  - name        │       │
│  │  - number      │  │  - work_date   │  │  - sort_order  │       │
│  │  - line_id     │  │  - workplace   │  │                │       │
│  │  - type        │  │  - work_time   │  │  Methods:      │       │
│  │  - is_active   │  │  - sent_at     │  │  - is_active() │       │
│  │                │  │                │  │                │       │
│  │  Methods:      │  │  Methods:      │  │                │       │
│  │  - is_linked() │  │  - is_sent()   │  │                │       │
│  │  - can_receive│  │  - get_start() │  │                │       │
│  │  - is_part_time│  │  - get_end()   │  │                │       │
│  │                │  │                │  │                │       │
│  │  ~80 LOC       │  │  ~90 LOC       │  │  ~60 LOC       │       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
│                                                                      │
│  Responsibilities:                                                  │
│  ✅ Domain logic                                                    │
│  ✅ Data structures                                                 │
│  ✅ Type safety                                                     │
│  ✅ Conversion utilities                                            │
│  ❌ NO database access                                              │
│  ❌ NO HTTP handling                                                │
└──────────────────────────────────────────────────────────────────────┘
                              ↓↑
┌──────────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                              │
│                        src/core/                                     │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │  database.py   │  │   config.py    │  │  logging.py    │       │
│  │                │  │                │  │                │       │
│  │ - get_conn()   │  │ - Config       │  │ - get_logger() │       │
│  │ - init_db()    │  │ - Development  │  │ - Structured   │       │
│  │ - WAL mode     │  │ - Production   │  │ - Context      │       │
│  │                │  │ - Testing      │  │                │       │
│  │ ~100 LOC       │  │ ~120 LOC       │  │ ~80 LOC        │       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
│                                                                      │
│  ┌────────────────┐                                                 │
│  │ exceptions.py  │                                                 │
│  │                │                                                 │
│  │ - ValidationError                                               │
│  │ - NotFoundError                                                 │
│  │ - DuplicateError                                                │
│  │                │                                                 │
│  │ ~60 LOC        │                                                 │
│  └────────────────┘                                                 │
└──────────────────────────────────────────────────────────────────────┘
                              ↓↑
┌──────────────────────────────────────────────────────────────────────┐
│                       SQLite Database                                │
│                        database.db                                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Comparison

### Before: Direct Path (High Coupling)

```
HTTP Request
    ↓
┌───────────────────────────────────────────┐
│         app.py route function             │
│                                           │
│  1. Parse request ────────────────┐      │
│  2. Validate input                │      │
│  3. Business logic                │      │
│  4. database.py function call     │      │
│  5. Format response               │      │
│                                   │      │
│  ALL IN ONE FUNCTION (61 lines)   │      │
└───────────────────────────────────┼───────┘
                                    ↓
                            ┌───────────────┐
                            │ database.py   │
                            │ Raw SQL       │
                            └───────┬───────┘
                                    ↓
                            ┌───────────────┐
                            │   Database    │
                            └───────────────┘

Problems:
❌ Everything in one place
❌ Can't test without full stack
❌ Hard to modify
❌ Duplicated code
```

---

### After: Layered Path (Loose Coupling)

```
HTTP Request
    ↓
┌────────────────────────────────────────┐
│  Layer 1: API Route (employee_routes)  │  ← 15 lines
│                                        │
│  - Parse request                       │
│  - Call service                        │
│  - Format response                     │
└────────────────┬───────────────────────┘
                 ↓
┌────────────────────────────────────────┐
│  Layer 2: Service (EmployeeService)    │  ← 25 lines
│                                        │
│  - Validate input                      │
│  - Apply business rules                │
│  - Coordinate repositories             │
│  - Return domain model                 │
└────────────────┬───────────────────────┘
                 ↓
┌────────────────────────────────────────┐
│  Layer 3: Repository (EmployeeRepo)    │  ← 18 lines
│                                        │
│  - Execute SQL                         │
│  - Convert row to model                │
│  - Return Employee object              │
└────────────────┬───────────────────────┘
                 ↓
┌────────────────────────────────────────┐
│  Layer 4: Model (Employee)             │  ← 8 lines
│                                        │
│  - Type-safe data structure            │
│  - Domain logic methods                │
└────────────────┬───────────────────────┘
                 ↓
          ┌─────────────┐
          │  Database   │
          └─────────────┘

Benefits:
✅ Each layer testable independently
✅ Clear responsibilities
✅ Easy to modify
✅ Reusable components
✅ Type safety
```

---

## Data Flow Example: Employee Registration

### Before (Monolithic)

```
POST /api/employees/register
         ↓
┌─────────────────────────────────────────────────────────┐
│            app.py (61 lines)                            │
│                                                         │
│  request.json ──→ validate ──→ check duplicate         │
│                     ↓                                    │
│              conn = get_db_connection()                 │
│              cursor.execute("SELECT ...")               │
│              existing = cursor.fetchone()               │
│                     ↓                                    │
│              if existing and active:                    │
│                  return error                           │
│                     ↓                                    │
│              cursor.execute("INSERT ...")               │
│              employee_id = cursor.lastrowid             │
│                     ↓                                    │
│              return jsonify({'id': employee_id})        │
└─────────────────────────────────────────────────────────┘

Problems:
❌ All logic in route (61 lines)
❌ Raw SQL mixed with business logic
❌ Hard to test
❌ No reusability
```

---

### After (Layered)

```
POST /api/employees/register
         ↓
┌─────────────────────────────────────────┐
│  employee_routes.py (15 lines)          │
│                                         │
│  data = request.json                    │
│  employee, reactivated =                │
│      employee_service.register(...)     │
│  return jsonify(employee.to_dict())     │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  employee_service.py (25 lines)         │
│                                         │
│  validate_employee_name(name)           │
│  validate_employee_number(number)       │
│         ↓                                │
│  existing = repo.get_by_number(number)  │
│         ↓                                │
│  if existing and active:                │
│      raise DuplicateError()             │
│         ↓                                │
│  if existing and not active:            │
│      return repo.reactivate()           │
│         ↓                                │
│  return repo.create(...)                │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  employee_repository.py (18 lines)      │
│                                         │
│  cursor.execute(                        │
│      "INSERT INTO employees ...",       │
│      (name, number, type)               │
│  )                                      │
│  employee_id = cursor.lastrowid         │
│         ↓                                │
│  row = self.get_by_id(employee_id)      │
│  return Employee.from_db_row(row)       │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  employee.py (8 lines)                  │
│                                         │
│  @dataclass                             │
│  class Employee:                        │
│      id: int                            │
│      name: str                          │
│      employee_number: str               │
│      ...                                 │
└─────────────────────────────────────────┘

Benefits:
✅ Each layer 8-25 lines
✅ Clear separation
✅ Fully testable
✅ Type-safe
✅ Reusable
```

---

## Testing Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Test Pyramid                         │
│                                                        │
│                    ┌──────┐                           │
│                   ╱  E2E   ╲  (5%)                    │
│                  ╱──────────╲                         │
│                 ╱ Integration ╲ (15%)                 │
│                ╱────────────────╲                     │
│               ╱   Unit Tests     ╲ (80%)              │
│              ╱──────────────────────╲                 │
│             └────────────────────────┘                │
│                                                        │
│  Unit Tests (Fast, Isolated):                         │
│  ├─ src/models/          (No dependencies)            │
│  ├─ src/repositories/    (Mock DB)                    │
│  └─ src/services/        (Mock repos)                 │
│                                                        │
│  Integration Tests (Medium):                          │
│  ├─ API + Service + Repository + DB                   │
│  └─ Real database (test DB)                           │
│                                                        │
│  E2E Tests (Slow, Comprehensive):                     │
│  └─ Full user flows                                   │
│                                                        │
│  Coverage Target: 85%+                                │
│  Execution Time: < 5 seconds                          │
└────────────────────────────────────────────────────────┘

Example Unit Test (Fast, No DB):
┌────────────────────────────────────────┐
│ test_employee_service.py               │
│                                        │
│ def test_register_duplicate_fails():   │
│     # Given: Mock repository          │
│     mock_repo = Mock()                │
│     mock_repo.get_by_number()         │
│         .return_value = existing      │
│                                        │
│     # When: Register duplicate        │
│     # Then: Raises error              │
│     with pytest.raises(DuplicateError)│
│                                        │
│ Speed: 0.01s                          │
└────────────────────────────────────────┘

Example Integration Test (Real DB):
┌────────────────────────────────────────┐
│ test_employee_flow.py                  │
│                                        │
│ def test_registration_flow(client):   │
│     # Given: Valid data               │
│     # When: POST to /api/employees    │
│     response = client.post(...)       │
│                                        │
│     # Then: Check DB state            │
│     assert employee in database       │
│                                        │
│ Speed: 0.5s                           │
└────────────────────────────────────────┘
```

---

## Metrics Comparison

```
┌──────────────────────────────────────────────────────────────┐
│                    CODE METRICS                              │
├──────────────────────────────────────────────────────────────┤
│  Metric              │  Before    │  After     │  Change    │
├──────────────────────┼────────────┼────────────┼────────────┤
│  Largest File        │  1,155 LOC │   240 LOC  │  ↓ 79%    │
│  Total Modules       │      2     │     19     │  ↑ 850%   │
│  Avg Module Size     │  1,080 LOC │   120 LOC  │  ↓ 89%    │
│  Functions/Module    │     47     │     12     │  ↓ 74%    │
│  Cyclomatic Complex. │    150     │     15     │  ↓ 90%    │
│  Test Coverage       │      0%    │     85%    │  ↑ 85%    │
│  Type Safety         │   None     │    Full    │  100%     │
│  Coupling            │   Tight    │   Loose    │  Better   │
│  Cohesion            │    Low     │    High    │  Better   │
└──────────────────────┴────────────┴────────────┴────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  MAINTAINABILITY                             │
├──────────────────────────────────────────────────────────────┤
│  Aspect              │  Before    │  After                  │
├──────────────────────┼────────────┼─────────────────────────┤
│  Time to Understand  │  2 days    │  2 hours                │
│  Time to Add Feature │  4 hours   │  1 hour                 │
│  Bug Rate            │  High      │  Low (tests catch)      │
│  Onboarding Time     │  1 week    │  1 day                  │
│  Change Confidence   │  Low       │  High (80%+ coverage)   │
│  Code Navigation     │  Difficult │  Easy (clear structure) │
└──────────────────────┴────────────┴─────────────────────────┘
```

---

## File Structure Comparison

### Before
```
project/
├── app.py (1,155 LOC) ────────────── ❌ Everything here
├── database.py (1,004 LOC) ──────── ❌ All DB operations
├── auth.py (103 LOC)
├── line_sender.py (219 LOC)
├── notification.py (153 LOC)
├── validators.py (256 LOC)
├── scheduler.py (173 LOC)
├── sheets_sync.py (247 LOC)
└── gunicorn_config.py (71 LOC)

Total: 3,507 LOC in 10 files
Avg: 351 LOC/file
Max: 1,155 LOC
```

### After
```
project/
├── app.py (50 LOC) ──────────────── ✅ Application factory
├── src/
│   ├── api/ (5 files)
│   │   ├── auth_routes.py (100 LOC)
│   │   ├── employee_routes.py (150 LOC)
│   │   ├── schedule_routes.py (140 LOC)
│   │   ├── admin_routes.py (120 LOC)
│   │   └── webhook_routes.py (90 LOC)
│   │
│   ├── services/ (3 files)
│   │   ├── employee_service.py (200 LOC)
│   │   ├── schedule_service.py (180 LOC)
│   │   └── notification_service.py (150 LOC)
│   │
│   ├── repositories/ (4 files)
│   │   ├── base_repository.py (100 LOC)
│   │   ├── employee_repository.py (150 LOC)
│   │   ├── schedule_repository.py (140 LOC)
│   │   └── workplace_repository.py (120 LOC)
│   │
│   ├── models/ (3 files)
│   │   ├── employee.py (80 LOC)
│   │   ├── schedule.py (90 LOC)
│   │   └── workplace.py (60 LOC)
│   │
│   ├── core/ (4 files)
│   │   ├── config.py (120 LOC)
│   │   ├── database.py (100 LOC)
│   │   ├── logging.py (80 LOC)
│   │   └── exceptions.py (60 LOC)
│   │
│   └── utils/ (3 files)
│       ├── validators.py (200 LOC)
│       ├── formatters.py (80 LOC)
│       └── constants.py (40 LOC)
│
├── tests/ (20+ files)
│   ├── unit/ (15 files, ~1500 LOC)
│   ├── integration/ (5 files, ~500 LOC)
│   └── conftest.py (100 LOC)
│
├── gunicorn_config.py (71 LOC)
├── scheduler.py (173 LOC)
└── sheets_sync.py (247 LOC)

Total Production: 2,940 LOC in 25 files
Total Tests: 2,100 LOC in 21 files
Avg Production: 118 LOC/file
Max Production: 200 LOC
Test Coverage: 85%+
```

---

## Dependency Graph

### Before (Circular Dependencies)

```
     app.py
    ↙  ↓  ↘
database ← line_sender
    ↓         ↓
notification ←
    ↑
    └─────────┘

❌ Circular dependencies
❌ Everything depends on database
❌ Hard to test in isolation
```

### After (Directed Acyclic Graph)

```
        app.py (Factory)
           ↓
     ┌─────────────┐
     ↓             ↓
API Routes    Scheduler
     ↓
Services
     ↓
Repositories
     ↓
Models
     ↓
Core (DB, Config, Logging)

✅ Clear dependency direction
✅ No circular dependencies
✅ Easy to test (mock lower layers)
```

---

*Architecture Diagram v1.0 - 2025-10-27*
