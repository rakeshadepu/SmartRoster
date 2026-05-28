# Timetable Planner — Phase 1: Backend Foundation

Django REST Framework backend with SQLite, JWT auth, role-based permissions,
and Base64url user ID generation.

---

## Quick Start

```bash
cd backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Seed development data (creates org, employee, 3 workers)
python setup_dev.py

# 4. Start server
python manage.py runserver
```

API runs at: **http://127.0.0.1:8000/api/**
Django Admin: **http://127.0.0.1:8000/admin/**

---

## Dev Credentials (after setup_dev.py)

| Role     | user_id (auto)     | password        |
|----------|--------------------|-----------------|
| Employee | printed by script  | `Employee@123`  |
| Workers  | printed by script  | printed by script |

> Worker credentials are printed once by `setup_dev.py` — copy them.

---

## user_id Format

Every user gets an **11-character Base64url** ID on account creation:

| Property    | Value                                      |
|-------------|--------------------------------------------|
| Alphabet    | A–Z (26) + a–z (26) + 0–9 (10) + `-` + `_` |
| Total chars | 64                                         |
| Length      | 11 characters                              |
| Combinations| 64¹¹ ≈ **73.8 quintillion**               |
| Uniqueness  | Global — same namespace across all orgs    |
| Generation  | `secrets.choice()` — cryptographically secure |

Example IDs: `ZqIcABVMxeq`, `1vI13ftv4vG`, `w7YAUCGzkAN`

---

## API Endpoints

### Auth
| Method | URL                  | Auth | Description                  |
|--------|----------------------|------|------------------------------|
| POST   | `/api/auth/login/`   | ❌   | Login → returns JWT tokens   |
| POST   | `/api/auth/logout/`  | ✅   | Logout (blacklist token)     |
| POST   | `/api/auth/refresh/` | ❌   | Refresh access token         |
| GET    | `/api/auth/me/`      | ✅   | Get current user profile     |

### Worker Login Flow
1. `GET /api/workers/public/?org=<id>` — fetch name list (no auth needed)
2. Worker selects name → `user_id` auto-fills
3. Worker enters password → `POST /api/auth/login/`

### Organisation (Employee only)
| Method | URL        | Description                     |
|--------|------------|---------------------------------|
| GET    | `/api/org/` | Get shop hours & org info      |
| PATCH  | `/api/org/` | Update shop open/close times   |

### Work Type Limits (Employee only)
| Method | URL               | Description                        |
|--------|-------------------|------------------------------------|
| GET    | `/api/work-limits/` | List hour limits per work type   |
| POST   | `/api/work-limits/` | Set/update limit for a work type |

Default limits: `FULL_TIME=40h`, `PART_TIME=20h`, `MINIJOB=10h`

### Workers (Employee only)
| Method | URL                              | Description                         |
|--------|----------------------------------|-------------------------------------|
| GET    | `/api/workers/public/`           | Name + user_id list (no auth)       |
| GET    | `/api/workers/`                  | List all workers in org             |
| POST   | `/api/workers/`                  | Create worker (returns password once)|
| GET    | `/api/workers/<pk>/`             | Get worker detail                   |
| PATCH  | `/api/workers/<pk>/`             | Update work_type / name / status    |
| DELETE | `/api/workers/<pk>/`             | Soft-deactivate worker              |
| POST   | `/api/workers/<pk>/reset-password/` | Reset password (shown once)      |

### Availability
| Method | URL                      | Who          | Description                   |
|--------|--------------------------|--------------|-------------------------------|
| GET    | `/api/availability/`     | Both         | Employee: all · Worker: own   |
| POST   | `/api/availability/`     | Worker only  | Submit availability (no edit) |
| GET    | `/api/availability/<pk>/`| Both         | View one record               |
| PATCH  | `/api/availability/<pk>/`| Employee only| Modify a record               |
| DELETE | `/api/availability/<pk>/`| Employee only| Delete a record               |

### Timetable (Phase 2 — read-only stub now)
| Method | URL                  | Description        |
|--------|----------------------|--------------------|
| GET    | `/api/timetable/`    | List timetables    |
| GET    | `/api/timetable/<pk>/`| View one timetable|

---

## Permission Matrix

| Action                    | Employee | Worker |
|---------------------------|:--------:|:------:|
| Login                     | ✅       | ✅     |
| Create / delete workers   | ✅       | ❌     |
| Set work type & limits    | ✅       | ❌     |
| Set shop hours            | ✅       | ❌     |
| View all availability     | ✅       | ❌     |
| Submit own availability   | ❌       | ✅     |
| Edit availability         | ✅       | ❌     |
| Generate timetable        | ✅       | ❌     |
| View timetable            | ✅       | ✅     |
| Edit own profile          | ✅       | ❌     |

---

## Worker Creation Flow

```
Employee fills "Create Worker" form
         │
         ▼
POST /api/workers/  { full_name, work_type }
         │
         ▼
Django pre_save signal fires:
  ├── assigns user_id  (11-char Base64url, globally unique)
  └── generates password (10-char random, hashed immediately)
         │
         ▼
Response includes plain_password  ← shown ONCE, then cleared from DB
         │
         ▼
Employee copies credentials → hands to worker
```

---

## Project Structure

```
backend/
├── manage.py
├── db.sqlite3               ← auto-created on migrate
├── requirements.txt
├── setup_dev.py             ← seed script
├── test_phase1.py           ← 70-test API test suite
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── timetable_app/
    ├── models.py            ← Organisation, User, WorkTypeLimit,
    │                           Availability, Timetable, Shift
    ├── serializers.py       ← DRF serializers for all models
    ├── views.py             ← All API views
    ├── permissions.py       ← IsEmployee, IsWorker, IsEmployeeOrReadOnly
    ├── signals.py           ← Auto user_id + password generation
    ├── apps.py              ← Registers signals on startup
    ├── admin.py             ← Django admin registration
    └── urls.py              ← URL routing
```

---

## Running Tests

```bash
cd backend
python test_phase1.py
```

**70 tests, 100% pass rate** covering:
- Base64url user_id format + uniqueness (1000 IDs)
- Auth login/logout/refresh/me for both roles
- Organisation CRUD + validation
- Work type limits CRUD + validation
- Worker create/read/update/soft-delete
- Auto user_id generation + plain_password once-only flow
- Availability submit/view/edit permissions
- All cross-role security checks (401 / 403 enforcement)

---

## What's Next — Phase 2

- `scheduler.py` — timetable generation algorithm
- `POST /api/timetable/generate/` — run scheduler
- `GET /api/timetable/<pk>/pdf/` — PDF export with WeasyPrint
- `PATCH /api/timetable/<pk>/` — employee manual edits
- Publish/draft timetable status flow
