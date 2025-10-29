# Refactoring Quick Reference Guide

## 🎯 What This Refactoring Achieves

### Before → After

```
┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│      BEFORE REFACTORING         │      │       AFTER REFACTORING         │
│                                 │      │                                 │
│  app.py (1,155 LOC)            │      │  src/                           │
│  ├─ 39 routes                  │      │  ├─ api/ (5 modules)           │
│  ├─ Business logic             │      │  │   └─ Thin controllers        │
│  ├─ Validation                 │      │  ├─ services/ (3 modules)      │
│  └─ Mixed concerns             │      │  │   └─ Business logic          │
│                                 │      │  ├─ repositories/ (4 modules)  │
│  database.py (1,004 LOC)       │      │  │   └─ Data access             │
│  ├─ 47 functions               │      │  ├─ models/ (3 modules)        │
│  ├─ Raw SQL everywhere         │      │  │   └─ Domain objects          │
│  └─ No abstraction             │      │  └─ core/ (4 modules)          │
│                                 │      │      └─ Infrastructure          │
│  0% Test Coverage              │      │                                 │
│  No Types                       │      │  85% Test Coverage             │
│  Tight Coupling                 │      │  Type Safety                    │
│                                 │      │  Loose Coupling                 │
└─────────────────────────────────┘      └─────────────────────────────────┘
```

---

## 📊 Metrics Improvement

| Metric | Before | After | Improvement |
|--------|---------|-------|-------------|
| **Largest File** | 1,155 LOC | 240 LOC | ↓ 79% |
| **Functions/Module** | 47 | 12 | ↓ 74% |
| **Cyclomatic Complexity** | 150 | 15 | ↓ 90% |
| **Test Coverage** | 0% | 85% | ↑ 85% |
| **Modules** | 2 monoliths | 19 focused | ↑ 850% |
| **Avg Function Length** | 45 lines | 12 lines | ↓ 73% |

---

## 🗺️ Migration Path (6 Weeks)

```
Week 1: FOUNDATION          Week 2: DATA LAYER       Week 3: SERVICE LAYER
┌──────────────────┐        ┌──────────────────┐     ┌──────────────────┐
│ ✅ Test setup    │        │ ✅ Models        │     │ ✅ Employee svc  │
│ ✅ Config        │   →    │ ✅ Base repo     │  →  │ ✅ Schedule svc  │
│ ✅ Logging       │        │ ✅ 4 repos       │     │ ✅ Notify svc    │
│ ✅ Char tests    │        │ ⚠️  Old code OK  │     │ ⚠️  Old code OK  │
└──────────────────┘        └──────────────────┘     └──────────────────┘
        ↓                           ↓                         ↓
Week 4: ROUTE LAYER         Week 5: TESTING          Week 6: CLEANUP
┌──────────────────┐        ┌──────────────────┐     ┌──────────────────┐
│ ✅ 5 blueprints  │        │ ✅ Unit tests    │     │ ✅ Remove old    │
│ ✅ App factory   │   →    │ ✅ Integration   │  →  │ ✅ Documentation │
│ ✅ Thin routes   │        │ ✅ 85% coverage  │     │ ✅ Final polish  │
│ ⚠️  Old code OK  │        │ ✅ Quality gates │     │ 🎉 DONE!         │
└──────────────────┘        └──────────────────┘     └──────────────────┘
```

---

## 🎨 New Architecture Layers

### Layer 1: API (Presentation)
```python
# src/api/employee_routes.py
@employee_bp.route('/register', methods=['POST'])
@require_auth
def register():
    employee, _ = employee_service.register_employee(...)
    return jsonify(employee.to_dict()), 201
```
**Responsibility**: HTTP handling, request/response, auth decorators

---

### Layer 2: Services (Business Logic)
```python
# src/services/employee_service.py
class EmployeeService:
    def register_employee(self, name, number, type):
        # Validation
        validate_employee_name(name)

        # Business rules
        if existing and existing.is_active:
            raise DuplicateError()

        # Coordination
        return self.repo.create(name, number, type)
```
**Responsibility**: Business rules, validation, orchestration

---

### Layer 3: Repositories (Data Access)
```python
# src/repositories/employee_repository.py
class EmployeeRepository(BaseRepository[Employee]):
    def create(self, name, number, type) -> Employee:
        # Pure data access
        cursor.execute("INSERT INTO employees ...")
        return Employee.from_db_row(row)
```
**Responsibility**: Database operations, SQL queries

---

### Layer 4: Models (Domain)
```python
# src/models/employee.py
@dataclass
class Employee:
    id: int
    name: str
    employee_number: str

    def can_receive_notifications(self) -> bool:
        return self.is_active and self.line_user_id
```
**Responsibility**: Domain logic, data structures

---

## 🔧 Code Examples: Before → After

### Example 1: Employee Registration

**BEFORE** (app.py - 45 lines, mixed concerns):
```python
@app.route('/api/employees/register', methods=['POST'])
def register_employee():
    data = request.json
    name = data.get('name')
    employee_number = data.get('employee_number')

    # Validation scattered
    if not name or len(name) > 50:
        return jsonify({'error': 'Invalid name'}), 400
    if not re.match(r'^[Kk]\d{3}$', employee_number):
        return jsonify({'error': 'Invalid number'}), 400

    # Business logic in route
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE employee_number = ?",
                   (employee_number,))
    existing = cursor.fetchone()

    if existing:
        if existing['is_active']:
            return jsonify({'error': 'Duplicate'}), 400
        else:
            # Reactivation logic...
            cursor.execute("UPDATE employees SET ...")
    else:
        cursor.execute("INSERT INTO employees ...")

    conn.commit()
    return jsonify({'id': cursor.lastrowid}), 201
```

**AFTER** (Separated into layers - 12 lines per layer):

```python
# src/api/employee_routes.py (12 lines)
@employee_bp.route('/register', methods=['POST'])
@require_auth
def register():
    try:
        data = request.json
        employee, is_reactivated = employee_service.register_employee(
            name=data['name'],
            employee_number=data['employee_number'],
            employee_type=data['employee_type']
        )
        return jsonify(employee.to_dict()), 200 if is_reactivated else 201
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400

# src/services/employee_service.py (18 lines)
def register_employee(self, name, number, type):
    validate_employee_name(name)
    validate_employee_number(number)

    existing = self.repo.get_by_employee_number(number)

    if existing and existing.is_active:
        raise DuplicateEmployeeNumberError()

    if existing and not existing.is_active:
        return self._reactivate(existing.id, name, type), True

    return self.repo.create(name, number, type), False

# src/repositories/employee_repository.py (10 lines)
def create(self, name, number, type) -> Employee:
    cursor.execute(
        "INSERT INTO employees (name, employee_number, employee_type) VALUES (?, ?, ?)",
        (name, number, type)
    )
    return self.get_by_id(cursor.lastrowid)
```

**Benefits**:
- ✅ Each layer < 20 lines
- ✅ Clear responsibilities
- ✅ Fully testable
- ✅ Type-safe
- ✅ Reusable

---

### Example 2: Database Query

**BEFORE** (database.py - scattered):
```python
def get_employee_by_id(employee_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
    row = cursor.fetchone()
    conn.close()
    return row  # Returns tuple or None
```

**AFTER** (Repository pattern):
```python
# src/repositories/employee_repository.py
def get_by_id(self, id: int) -> Optional[Employee]:
    cursor.execute("SELECT * FROM employees WHERE id = ?", (id,))
    row = cursor.fetchone()
    return Employee.from_db_row(row) if row else None
```

**Benefits**:
- ✅ Returns type-safe Employee object
- ✅ Consistent error handling
- ✅ Logging integrated
- ✅ Easier to mock in tests

---

## 🧪 Testing Strategy

### Test Pyramid

```
                    ┌─────────┐
                   ╱  E2E (5%) ╲     ← Full user flows
                  ╱─────────────╲
                 ╱  Integration  ╲   ← API + DB + Services
                ╱     (15%)       ╲
               ╱───────────────────╲
              ╱       Unit          ╲  ← Repositories, Services, Models
             ╱       (80%)           ╲
            └─────────────────────────┘
```

### Test Examples

**Unit Test (Fast, Isolated)**:
```python
def test_employee_can_receive_notifications():
    # Given: Employee with LINE ID
    employee = Employee(
        id=1, name="山田", employee_number="K001",
        line_user_id="U123", is_active=True, ...
    )

    # When/Then
    assert employee.can_receive_notifications() == True
```

**Integration Test (Medium Speed)**:
```python
def test_employee_registration_flow(client, db):
    # Given: Valid registration data
    response = client.post('/api/employees/register', json={
        'name': '山田太郎',
        'employee_number': 'K001',
        'employee_type': 'part_time'
    })

    # Then: Employee created in database
    assert response.status_code == 201
    employee = db.execute("SELECT * FROM employees WHERE id = ?",
                         (response.json['id'],)).fetchone()
    assert employee['name'] == '山田太郎'
```

---

## 🚀 How to Start Refactoring

### Step-by-Step Process

1. **Week 1: Setup** (No risk)
   ```bash
   # Install dependencies
   pip install pytest pytest-cov pytest-mock

   # Create test structure
   mkdir -p tests/{unit,integration,fixtures}

   # Run existing code
   pytest  # Should pass (even with 0 tests)
   ```

2. **Week 2: Add Models** (No risk - new code)
   ```bash
   mkdir -p src/{models,repositories}
   # Create Employee, Schedule models
   # Old code still works!
   ```

3. **Week 3: Add Services** (Low risk - parallel operation)
   ```bash
   mkdir -p src/services
   # Create EmployeeService
   # Both old and new code work
   ```

4. **Week 4: Migrate Routes** (Medium risk - test thoroughly)
   ```bash
   mkdir -p src/api
   # Move routes to blueprints one-by-one
   # Test after each migration
   ```

5. **Week 5: Write Tests** (No risk)
   ```bash
   # Achieve 85% coverage
   pytest --cov=src --cov-report=html
   ```

6. **Week 6: Remove Old Code** (Low risk - well-tested)
   ```bash
   # Delete database.py
   # Delete old app.py
   # Celebrate! 🎉
   ```

---

## 🎯 Success Checklist

### Phase 1: Foundation ✅
- [ ] pytest running
- [ ] Test fixtures working
- [ ] Configuration extracted
- [ ] Logging standardized
- [ ] 15+ characterization tests

### Phase 2: Data Layer ✅
- [ ] Domain models created
- [ ] BaseRepository implemented
- [ ] 4 repositories working
- [ ] 80%+ repository test coverage
- [ ] Old database.py still works

### Phase 3: Service Layer ✅
- [ ] EmployeeService implemented
- [ ] ScheduleService implemented
- [ ] NotificationService implemented
- [ ] 90%+ service test coverage
- [ ] Business logic extracted from routes

### Phase 4: Route Layer ✅
- [ ] 5 blueprints created
- [ ] app.py < 100 LOC
- [ ] Application factory pattern
- [ ] All routes migrated
- [ ] API tests passing

### Phase 5: Testing ✅
- [ ] 85%+ total coverage
- [ ] Unit tests for all modules
- [ ] Integration tests for flows
- [ ] Performance acceptable
- [ ] Code quality enforced

### Phase 6: Cleanup ✅
- [ ] Old code removed
- [ ] Documentation updated
- [ ] Metrics improved
- [ ] Team trained
- [ ] Production deployment successful

---

## 🔄 Rollback Plan

Each week has a rollback strategy:

| Week | Changes | Rollback |
|------|---------|----------|
| 1 | New test files | Delete tests/ directory |
| 2 | New models/repos | Delete src/ directory |
| 3 | New services | Delete src/services/ |
| 4 | Route migration | Revert to previous blueprint |
| 5 | Tests only | N/A (no production code changed) |
| 6 | Delete old code | Restore from git |

**Git Strategy**: Branch per phase
```bash
git checkout -b refactor/phase-1-foundation
git checkout -b refactor/phase-2-repositories
# ... etc
```

---

## 📖 Key Principles Applied

### SOLID Principles

1. **Single Responsibility**: Each class/module has one reason to change
   - ❌ Before: app.py did everything
   - ✅ After: Separate routes, services, repositories

2. **Open/Closed**: Open for extension, closed for modification
   - ✅ BaseRepository allows new repositories without changes

3. **Liskov Substitution**: Derived classes substitutable
   - ✅ All repositories inherit from BaseRepository

4. **Interface Segregation**: No unused interfaces
   - ✅ Each service exposes only what clients need

5. **Dependency Inversion**: Depend on abstractions
   - ✅ Services depend on repository interfaces

### Clean Code Patterns

- **DRY**: BaseRepository eliminates duplication
- **KISS**: Simple, focused modules
- **YAGNI**: Only build what's needed now
- **Separation of Concerns**: Layered architecture
- **Repository Pattern**: Abstracts data access
- **Service Pattern**: Encapsulates business logic

---

## 💡 Common Pitfalls & Solutions

### Pitfall 1: "Big Bang" Refactoring
❌ **Don't**: Rewrite everything at once
✅ **Do**: Incremental, phase-by-phase approach

### Pitfall 2: Skipping Tests
❌ **Don't**: Refactor without safety net
✅ **Do**: Write characterization tests first

### Pitfall 3: Breaking API Contracts
❌ **Don't**: Change external interfaces
✅ **Do**: Keep API responses identical

### Pitfall 4: Over-Engineering
❌ **Don't**: Add complexity for future needs
✅ **Do**: Solve current problems simply

### Pitfall 5: Incomplete Migration
❌ **Don't**: Leave both old and new code forever
✅ **Do**: Set deprecation timeline and follow through

---

## 📞 Need Help?

### Questions to Ask

1. **Scope**: Which phase am I in?
2. **Risk**: What's my rollback plan?
3. **Validation**: How do I verify this works?
4. **Testing**: What tests should I write?
5. **Timeline**: Am I on track?

### Red Flags

- 🚨 Tests failing
- 🚨 Coverage dropping
- 🚨 Performance degrading
- 🚨 Team confused
- 🚨 Production issues

If you see red flags, STOP and review the phase.

---

## 🎉 Expected Outcomes

After 6 weeks:

✅ **Maintainability**: Easy to understand and modify
✅ **Testability**: 85% coverage, fast tests
✅ **Scalability**: Easy to add features
✅ **Performance**: No degradation
✅ **Documentation**: Clear architecture
✅ **Team Confidence**: Well-understood codebase

---

*Quick Reference Version 1.0 - 2025-10-27*
