# Administrator Guide

This guide covers everything a system administrator or school director needs to run the Smart Swimming School Management System: installation, user and role management, authorisation, organisation settings, KPIs, statistics, auditing, backups, maintenance and updates. Day-to-day operational work — enrolling students, taking attendance, collecting payments — is documented separately in [USER_GUIDE_EN.md](USER_GUIDE_EN.md).

**Version:** 0.9.0 · **Licence:** MIT

---

## Table of contents

1. [Installation](#1-installation)
2. [The setup wizard (onboarding)](#2-the-setup-wizard-onboarding)
3. [User and role management](#3-user-and-role-management)
4. [How authorisation works](#4-how-authorisation-works)
5. [Organisation settings](#5-organisation-settings)
6. [Setting KPI targets](#6-setting-kpi-targets)
7. [Using the Statistics Center](#7-using-the-statistics-center)
8. [The audit log](#8-the-audit-log)
9. [Backup management](#9-backup-management)
10. [System health](#10-system-health)
11. [Training mode](#11-training-mode)
12. [Demo data](#12-demo-data)
13. [Maintenance tasks](#13-maintenance-tasks)
14. [Update procedure](#14-update-procedure)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Installation

### 1.1 Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Operating system | Windows 10 / 11 | The desktop launcher uses Edge WebView2, which ships with Windows 11 and current Windows 10. The backend itself is platform-neutral. |
| Python | 3.11+ | Install with "Add Python to PATH" ticked. |
| Node.js | 18+ | Only needed to build the interface, not to run it. |
| RAM | 4 GB | 8 GB if you also run a local AI model. |
| Disk | 2 GB free | Database, backups, logs and uploads grow over time. |
| Database | SQLite (bundled) | PostgreSQL is supported by the data layer; see §1.4. |

Optional: **LM Studio** for local AI (privacy-preserving, nothing leaves the machine) and/or an **NVIDIA Build** API key for cloud AI. Both are optional — the system runs fully without any AI provider.

### 1.2 First run

Double-click **`START_SWIMMING_SCHOOL.bat`**. On the first run it performs the whole installation for you:

1. Creates the Python virtual environment in `.venv` and installs `backend\requirements.txt` plus `pywebview`.
2. Copies `.env.example` to `.env` and generates a random 64-byte `SECRET_KEY` in place of the placeholder.
3. Runs `alembic upgrade head` to create the 50-table schema.
4. Warns if `frontend\dist\index.html` is missing (run `BUILD_FRONTEND.bat` once to produce it).
5. Starts the backend and opens the desktop window.

At startup the application also seeds itself idempotently: it synchronises the 21 system roles with their permission sets, creates the first administrator if it does not exist, and inserts the default settings, KPI targets and packages.

The startup log confirms what happened:

```
Veritabanı hazır | roller: 21, yönetici: admin@yuzmeokulu.local
API hazır: http://127.0.0.1:8000/docs
```

**Immediately after the first login, change the administrator password.** The default is whatever `FIRST_ADMIN_PASSWORD` holds in `.env`, and it must not survive into real use.

To build the interface (needed once, and again after any frontend change):

```bat
BUILD_FRONTEND.bat
```

For development with hot reload, use the dev script instead — it starts uvicorn with `--reload` on port 8000 and the Vite dev server on port 5173:

```powershell
.\scripts\dev.ps1
.\scripts\dev.ps1 -BackendOnly
```

### 1.3 Configuring `.env`

All configuration lives in `.env` at the project root. Nothing secret is ever hardcoded in the source. **`.env` must never be committed to version control** — it is in `.gitignore`, and `FINAL_CHECK.bat` fails the release gate if that ever stops being true.

#### Application

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_NAME` | Akıllı Yüzme Okulu Yönetim Sistemi | Shown in the window title and API docs. |
| `APP_ENV` | `development` | `development`, `production` or `test`. Production enables HSTS and blocks demo-data generation. |
| `APP_DEBUG` | `true` | Set to `false` in production. |
| `APP_HOST` | `127.0.0.1` | Keep on loopback unless you deliberately expose the API. |
| `APP_PORT` | `8000` | |
| `APP_DEFAULT_LANGUAGE` | `tr` | `tr` or `en`. |
| `APP_TIMEZONE` | `Europe/Istanbul` | |
| `APP_CURRENCY` | `TRY` | |

#### Security

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | generated | JWT signing key. Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Changing it invalidates all existing sessions. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Access token lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | Refresh token lifetime. |
| `JWT_ALGORITHM` | `HS256` | |
| `FIRST_ADMIN_EMAIL` | `admin@yuzmeokulu.local` | Created on first start only. |
| `FIRST_ADMIN_PASSWORD` | — | Change after first login. |
| `RATE_LIMIT_ENABLED` | `true` | Leave on. |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Failed logins per e-mail per minute before requests are refused. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allow-list. Narrow this in production. |

#### Database

```dotenv
DATABASE_URL=sqlite:///./data/swimming_school.db
DATABASE_ECHO=false
```

Relative SQLite paths are resolved against the project root automatically.

#### AI providers

Local (LM Studio), NVIDIA Build and any OpenAI-compatible endpoint are configured independently, with a routing block deciding which is tried first:

```dotenv
LOCAL_AI_ENABLED=true
LOCAL_AI_BASE_URL=http://localhost:1234/v1
NVIDIA_ENABLED=false
NVIDIA_API_KEY=
AI_FALLBACK_CHAIN=local,nvidia
AI_DEFAULT_MODE=automatic
AI_RESPONSE_LANGUAGE=auto
AI_LOG_PROMPTS=false
```

Leave `AI_LOG_PROMPTS=false` in production — it is a privacy setting, not a debugging convenience. API keys are masked everywhere they are surfaced (`nva************1a2b`); the full value is never returned by the API, written to a log, or included in a backup. Full AI configuration is documented in [AI_GUIDE_EN.md](AI_GUIDE_EN.md).

#### Backup, logging, demo data

```dotenv
BACKUP_DIR=./backups
BACKUP_SCHEDULE_ENABLED=false
BACKUP_SCHEDULE_CRON=0 23 * * *
BACKUP_RETENTION_DAILY=7
BACKUP_RETENTION_WEEKLY=4
BACKUP_RETENTION_MONTHLY=12

LOG_DIR=./logs
LOG_LEVEL=INFO
LOG_JSON=false

SEED_DEMO_DATA=true
```

Set `SEED_DEMO_DATA=false` before going live.

#### A production checklist

```dotenv
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=<a fresh 64-byte random value>
FIRST_ADMIN_PASSWORD=<changed, and the admin password rotated after first login>
CORS_ORIGINS=<only the origins you actually serve>
AI_LOG_PROMPTS=false
AI_DEVELOPER_ALLOW_APPLY=false
AI_DEVELOPER_ALLOW_SHELL=false
BACKUP_SCHEDULE_ENABLED=true
SEED_DEMO_DATA=false
```

### 1.4 Migrations

Schema changes are managed with Alembic from the `backend` directory:

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head      # apply all pending migrations
..\.venv\Scripts\python.exe -m alembic current           # show the current revision
..\.venv\Scripts\python.exe -m alembic history           # list revisions
..\.venv\Scripts\python.exe -m alembic check             # models vs. migrations in sync?
..\.venv\Scripts\python.exe -m alembic downgrade -1      # step back one revision
```

`START_SWIMMING_SCHOOL.bat` runs `upgrade head` on every start, so in normal operation you never need to do this by hand. The current revision is also visible in the interface under **Settings → About** as the database version.

**Always take a backup before running a migration manually.** See §14.

#### Moving to PostgreSQL

The data layer is database-agnostic. Point `DATABASE_URL` at PostgreSQL and run the migrations:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/swimming_school
```

One caveat: **backup and restore currently support SQLite only.** On PostgreSQL, use `pg_dump` / `pg_restore` for the time being. The `pg_dump` flow is on the roadmap for 1.0.0.

---

## 2. The setup wizard (onboarding)

The first time an administrator signs in, the setup wizard opens. It has nine steps, and it does not merely tick boxes — each step's completion is inferred from real data in the database, so a step marked done really is done.

| # | Step | What to do | Detected by | Screen |
|---|------|-----------|-------------|--------|
| 1 | **Organisation details** | Enter the school name, contact details, currency and language. | Organisation name has been changed from the default "Akıllı Yüzme Okulu". | Settings → General |
| 2 | **First administrator** | Change the administrator password. | The account no longer has the must-change-password flag. | Settings → Profile |
| 3 | **Create a pool** | Define at least one pool. | At least one pool record exists. | Pools → New |
| 4 | **Define lanes** | Set the lane count and each lane's purpose. | Satisfied together with step 3. | Pools |
| 5 | **Add the first instructor** | Create at least one instructor. | At least one instructor record exists. | Instructors → New |
| 6 | **Add the first student** | Create your first student. | At least one student record exists. | Students → New |
| 7 | **AI settings** (optional) | Configure local or cloud AI. | Local AI or NVIDIA is enabled in configuration. | AI Center |
| 8 | **Backup settings** | Enable scheduled backups. | Scheduling is enabled, or at least one backup exists. | Settings → Backup |
| 9 | **Finish setup** | Continue into the Training Center. | Marked complete by the user. | Training Center |

**Skip for now** is available and marks onboarding complete without forcing you through every step; you can pick the remaining work up from the Training Center at any time. Because progress is derived from data rather than stored as a checklist, restoring a backup or importing records updates the wizard's view automatically.

---

## 3. User and role management

### 3.1 Adding a user

Go to **Settings → Users → New User**:

| Field | Notes |
|-------|-------|
| E-mail | Must be unique; stored lower-cased and used as the login name. |
| Password | Minimum 8 characters, at least one letter and one digit. Obvious passwords (`password`, `admin123`, `123456789`, `parola123`) are rejected. |
| Full name | |
| Phone | Optional. |
| Language | Interface language for this user. |
| Roles | One or more. The effective permission set is the union of all assigned roles. |
| Active | Uncheck to suspend access without removing the account. |
| Must change password at first login | Recommended for every account you create for someone else. |

Assigning roles at creation requires `user:write`; **changing** the roles of an existing user additionally requires `role:manage`, which by design only the System Administrator holds. Every create and update is written to the audit log, with role changes recorded as before/after.

### 3.2 The 21 roles

Roles are seeded as system roles and re-synchronised on every application start, so their permission sets stay consistent with the code.

#### Management roles

| Role | Code | What it can access |
|------|------|--------------------|
| System Administrator | `system_admin` | Everything — all 52 permissions, including the AI Developer Console, role management, user deletion and backup restore. Reserve this for one or two people. |
| School Director | `school_director` | Everything operational: all modules, full finance, reports and exports, statistics and KPI targets, settings, users, backups **including restore**, CAIO. Cannot use the AI Developer Console, manage roles, or delete users. |
| Operations Manager | `operations_manager` | Students, guardians, instructors (read/write); pools including maintenance; lessons full (write, schedule, delete); attendance; memberships; **finance read-only**; performance; competitions; reports and exports; statistics and KPI targets; notifications including sending; settings read; backup read and create; system health. No user management. |
| Finance / Accounting | `finance` | Students, guardians and instructors read-only; memberships read/write; **finance full** (read, write, delete); reports and exports; statistics. No lessons, no attendance, no performance. |
| Human Resources | `hr` | Instructors full (read, write, delete); **users read/write**; lessons and attendance read-only; reports and exports; statistics. No students, no finance. |
| Reception | `reception` | The daily counter role: students and guardians read/write; instructors and pools read-only; lessons read, write and schedule; attendance read/write; memberships read/write; finance read/write (take payments); reports read. No delete permissions anywhere, no statistics, no user management. |
| Sales / Marketing | `sales_marketing` | Students and guardians read/write; memberships read/write; finance read-only; reports and exports; statistics; notifications including sending. No lessons, no attendance. |

#### Education roles

All education roles share an **instructor baseline**: read access to students, guardians, instructors, pools and lessons; attendance read **and write**; performance read **and write**; competitions read; reports read; statistics read; AI use; notifications; own portal.

| Role | Code | Beyond the baseline |
|------|------|---------------------|
| Head Coach | `head_coach` | Instructor write; lessons write, schedule and delete; competition write; report export; KPI targets; student write; **sensitive student data** (health notes); send notifications. The education side's manager. |
| Swimming Coach | `swim_coach` | Lesson write and competition write. |
| Swimming Instructor | `swim_instructor` | Baseline only. |
| Kids Swimming Instructor | `kids_instructor` | Baseline only. |
| Baby Swimming Instructor | `baby_instructor` | Baseline only. |
| Private Lesson Instructor | `private_instructor` | Baseline only. |
| Adaptive Swimming Instructor | `adaptive_instructor` | **Sensitive student data** — necessary, since adaptive teaching depends on knowing the condition being adapted for. |
| Conditioning Coach | `conditioning_coach` | Baseline only. |

#### Other roles

| Role | Code | What it can access |
|------|------|--------------------|
| Lifeguard | `lifeguard` | Read-only view of students, guardians, instructors, pools, lessons and attendance, plus notifications. Enough to know who is in the water and who is supervising; nothing writable. |
| Pool Technician | `pool_technician` | Pools read/write **and maintenance**; lessons read (to schedule work around classes); system health; notifications. No access to people or money. |
| Medical Staff | `medical_staff` | Students read **including sensitive health data**; guardians read; lessons and attendance read; notifications including sending. Deliberately narrow: clinical need, nothing else. |
| Athlete | `athlete` | Own portal only: own lessons, attendance, performance, competitions and notifications. **Row-scoped.** |
| Student | `student` | Own portal only: own lessons, attendance, performance and notifications. **Row-scoped.** |
| Parent | `parent` | Own children only: their lessons, attendance, performance, membership and financial balance. **Row-scoped.** |

A user may hold several roles; permissions add up. There is no "deny" rule — the effective set is simply the union — so grant the narrowest role that does the job rather than layering roles for convenience.

### 3.3 Resetting a password

**Settings → Users → (select user) → Reset password**. Requires `user:write`.

Enter the new password (the same strength policy applies) and decide whether to force a change at next login — normally yes, so the person you hand it to sets their own.

The reset also clears the failed-login counter and any active lockout, which makes it the fastest way to help someone locked out after eight bad attempts. The action is written to the audit log as `reset_password` against the target user; the password itself never appears anywhere in the log.

### 3.4 Deactivating a user

**Users are never deleted.** The delete action sets `is_active = false`, which blocks sign-in while preserving every record the person created and their trail in the audit log. Deleting the row would orphan history and make past reports unexplainable.

Deactivation requires `user:delete` (System Administrator only) and you cannot deactivate your own account — the check exists so an administrator cannot accidentally lock everyone out.

When a staff member leaves: deactivate the account the same day, then check whether they were set as a primary instructor on any student and reassign.

---

## 4. How authorisation works

### 4.1 Permission codes

Authorisation is role-based with fine-grained permissions in `resource:action` form. There are **52 permissions across 21 resources**:

| Resource | Permissions |
|----------|-------------|
| `student` | `read`, `write`, `delete`, `read_sensitive` |
| `guardian` | `read`, `write`, `delete` |
| `instructor` | `read`, `write`, `delete` |
| `pool` | `read`, `write`, `delete`, `maintenance` |
| `lesson` | `read`, `write`, `delete`, `schedule` |
| `attendance` | `read`, `write` |
| `membership` | `read`, `write`, `delete` |
| `finance` | `read`, `write`, `delete` |
| `performance` | `read`, `write` |
| `competition` | `read`, `write` |
| `report` | `read`, `export` |
| `statistics` | `read` |
| `kpi` | `write` |
| `ai` | `use`, `configure`, `developer`, `caio` |
| `user` | `read`, `write`, `delete` |
| `role` | `manage` |
| `settings` | `read`, `write` |
| `audit` | `read` |
| `backup` | `read`, `create`, `restore` |
| `notification` | `read`, `send` |
| `system` | `health` |
| `self` | `portal` |

Two are worth singling out:

- **`student:read_sensitive`** gates health notes and special-needs information. Users without it see those fields marked hidden on the profile rather than blank, so nobody mistakes "not permitted" for "not recorded". Held by System Administrator, School Director, Head Coach, Adaptive Instructor and Medical Staff.
- **`ai:developer`** gates the AI Developer Console, which can propose and apply source-code patches. Held only by the System Administrator, and additionally gated by `AI_DEVELOPER_ALLOW_APPLY` in `.env`.

The full list, grouped by resource, is available at `GET /api/v1/users/permissions` for anyone with `role:manage`, and in the interface under **Settings → Roles**.

Enforcement happens at three layers:

1. **Menu** — entries the user lacks permission for are not rendered.
2. **Route** — navigating to the address directly returns an access-denied screen.
3. **API** — every endpoint declares its required permission and returns HTTP 403 regardless of what the client sends. This is the layer that actually protects the data; the first two are usability.

A **superuser** flag exists and bypasses permission checks entirely. Use it for the break-glass account only.

### 4.2 Row-level scoping

Permissions answer "which screens?"; scoping answers "which rows?". A parent with `lesson:read` must not see every lesson in the school, so a second filter applies on top of permissions.

**Self-scoped roles** — Athlete, Student, Parent. Such a user sees only:

- their own student record, or
- for a guardian account, the students linked to that guardian.

If no linked record exists, the filter returns nothing rather than everything — failing closed is deliberate.

Self-scoping is skipped for a user who also holds `student:write`, which prevents a staff member who happens to also be enrolled as an athlete from losing access to their job.

**Instructor-scoped roles** — Swimming Coach, Swimming Instructor, Kids, Baby, Private, Adaptive and Conditioning instructors. These users primarily see their own lessons and the students in them.

**Unscoped roles** — System Administrator, School Director and Operations Manager (and any superuser) see all rows.

Two further data-level rules:

- **Sensitive student data** requires `student:read_sensitive`, checked per record.
- **Salary information** is limited to System Administrator, School Director, Finance and HR — a separate check from instructor read access, so a head coach can manage staff without seeing their pay.

---

## 5. Organisation settings

**Settings → General** stores the organisation record. It is saved as a single settings entry, and every change is audited with its before and after values.

| Setting | Default | Effect |
|---------|---------|--------|
| Name | Akıllı Yüzme Okulu | Appears on every report header and PDF export. Changing it from the default is what marks step 1 of the setup wizard complete. |
| Logo | — | Shown on reports. |
| Phone / E-mail / Address / Website | — | Used on invoices and reports. |
| Tax office / Tax number | — | Printed on invoices. |
| Currency | `TRY` | Changes amount formatting across every screen at once; no per-screen edit needed. Symbols are known for TRY (₺), USD ($), EUR (€) and GBP (£); other codes display as the code itself. |
| Language | `tr` | Default interface language for new users. Individuals can override it for themselves. |
| Time zone | `Europe/Istanbul` | |
| Date format | `DD.MM.YYYY` | Display format for dates. |

Number formatting follows the language rather than this record: Turkish renders `1.250,50`, English `1,250.50`.

Other settings groups on the same screen:

| Group | Contains |
|-------|----------|
| **Attendance** | Late threshold (10 minutes — a QR check-in later than this is recorded as Late), auto-consume credit, allow make-ups, make-up window (30 days). |
| **Membership** | Expiry warning window (14 days) and low-credit warning threshold (2 lessons). These drive the dashboard alerts and the expiring/low-credit lists. |
| **Finance** | Overdue grace period (3 days), tax rate, invoice prefix (`FT`). |
| **Developer** | AI Developer Console enabled, allow apply, allow shell, auto-test, patch policy (`review_required`). |
| **Backup** | Schedule enabled, cron expression, daily/weekly/monthly retention. |
| **AI runtime** | Mode, fallback chain, response language, selected models. Contains no secrets — API keys stay in `.env`. |

Changing a setting requires `settings:write`.

---

## 6. Setting KPI targets

The system computes **eleven KPIs** and compares each with a target you set.

| KPI key | Label | Unit | Better when |
|---------|-------|------|-------------|
| `active_students` | Active Students | count | higher |
| `new_students_monthly` | Monthly New Students | count | higher |
| `student_retention` | Student Retention | percent | higher |
| `attendance_rate` | Attendance Rate | percent | higher |
| `pool_occupancy` | Pool Occupancy | percent | higher |
| `lane_occupancy` | Lane Occupancy | percent | higher |
| `monthly_revenue` | Monthly Revenue | currency | higher |
| `revenue_per_student` | Revenue per Student | currency | higher |
| `outstanding_payments` | Outstanding Payments | currency | **lower** |
| `collection_rate` | Collection Rate | percent | higher |
| `average_performance_improvement` | Avg. Performance Improvement | percent | higher |

### 6.1 Defaults

Five targets are seeded at installation:

| KPI | Default target |
|-----|---------------:|
| Attendance rate | 90% |
| Pool occupancy | 80% |
| Collection rate | 95% |
| Student retention | 85% |
| Lane occupancy | 75% |

The other six have no target until you set one. A KPI without a target still shows its value and its change against the previous period; it simply has no achievement percentage and displays as neutral.

### 6.2 Setting a target

**Analytics → Statistics → KPI tab**, then edit the target on the indicator you want (requires `kpi:write`). Achievement is calculated against it:

```
achievement = value / target × 100                (higher-is-better KPIs)
achievement = target / value × 100                (outstanding_payments)
```

| Achievement | Status |
|-------------|--------|
| 100% or more | **Good** (green) |
| 85–99% | **Warning** (amber) |
| Below 85% | **Bad** (red) |

Each KPI also shows its previous-period value and the percentage change, computed over an equal-length preceding window.

### 6.3 Choosing sensible targets

Two rules make targets useful rather than decorative:

1. **Set them from your own baseline, not from an ideal.** Run the statistics for the last two quarters first, then set a target that is 5–10% better than what you actually achieved. A 95% attendance target against a real 78% produces a permanently red dashboard, which teaches everyone to ignore the colour.
2. **Review quarterly.** A target that has been comfortably met for two quarters is no longer doing any work.

---

## 7. Using the Statistics Center

**Analytics → Statistics** is where measured data lives. Everything on these screens is computed from the database with no estimation, smoothing or model inference.

### 7.1 Period selection

All tabs share one period selector:

| Option | Range |
|--------|-------|
| Today | The current day |
| This Week | The current week |
| This Month | The current month |
| Last 3 Months | Rolling quarter |
| Last 6 Months | Rolling half-year |
| This Year | Year to date |
| Last Year | The previous calendar year |
| Custom Range | Explicit start and end dates |

Comparisons against the previous period use an equal-length window immediately before the selected one, so a 30-day selection is compared with the preceding 30 days rather than with "last month".

### 7.2 The tabs

| Tab | What it holds |
|-----|---------------|
| **Students** | New registrations, lost students, growth rate, retention and churn, average membership length, and distributions by age, level, group and gender, plus the registration trend. |
| **Instructors** | Lessons and hours per instructor, student counts, occupancy of their classes, and workload balance across the team. |
| **Pools** | Pool and lane utilisation, hourly load (06:00–24:00), daily and weekly load, busiest and quietest hour, most-used lane, free capacity in hours, and the heatmap. |
| **Attendance** | Overall attendance rate, rates by group, instructor and lesson type, and absence patterns. |
| **Finance** | Income, expenses and net result over the period, with method and category breakdowns. |
| **KPI** | The eleven indicators with targets, achievement and period-on-period change (§6). |
| **Advanced** | Cohort retention, attendance outliers, distribution analysis and the attendance–performance correlation. |

### 7.3 Reading the heatmap

The heatmap is a weekday × hour grid of pool usage. Each cell holds the total lesson-minutes in that slot and the number of lessons; darker means busier.

What to look for:

- **A dark block at 17:00–19:00 on weekdays with pale mornings** is the normal shape of a swimming school. The question it raises is whether the pale hours can be sold at a lower price rather than left empty.
- **A single dark cell surrounded by pale ones** usually means one popular instructor or one group everybody wants. That is a capacity risk: if that person is ill, a large share of your week is affected.
- **A pale patch inside an otherwise dark band** is the most actionable finding — capacity at a time people already come, which is the cheapest growth available.

The summary figures beside it — busiest hour, quietest hour, most-used lane, free capacity in hours — quantify what the grid shows.

### 7.4 Cohort analysis

Cohort analysis groups students by the month they registered and tracks how many of each group are still active N months later.

Read it as rows: the January cohort's row shows 100% in month 0, then its survival month by month. Comparing rows tells you whether retention is improving — if the June cohort is at 80% in month 3 while January's was at 60%, something you changed in spring is working.

This is a more honest retention measure than a single churn percentage, because it separates "we are losing people" from "we grew quickly and the new intake has not been here long enough to leave yet".

### 7.5 The correlation caveat

The Advanced tab includes an **attendance–performance correlation**: for each student with at least 5 attendance records and 3 performance records in the window (180 days by default), it computes their attendance rate and their percentage improvement in times, then correlates the two.

**Correlation is not causation, and the interface says so.** A strong positive correlation between attendance and improvement does not prove that attending more causes faster swimming. At least three other explanations fit the same number equally well:

- **Reverse causation** — students who are improving enjoy it and therefore attend more.
- **A common cause** — motivated families both attend reliably and practise outside lessons.
- **Selection** — students who were going to drop out left before accumulating enough records to enter the calculation at all.

Use the correlation to decide **what to investigate**, never as evidence for a policy on its own. The same caution applies to the outlier and distribution analyses: an outlier is a student worth a phone call, not a verdict about that student.

The system enforces this distinction structurally elsewhere too: in AI analysis screens the computed data appears in one panel and the model's interpretation in a visibly separate one, so a measurement is never mistaken for an inference.

---

## 8. The audit log

**Settings → Audit** (requires `audit:read`).

### 8.1 What is recorded

Every state-changing action writes an audit entry containing:

| Field | Contents |
|-------|----------|
| User | The account id and e-mail of whoever acted. |
| Action | `create`, `update`, `delete`, `deactivate`, `reset_password`, `record_attendance`, `export`, `seed_heats`, `restore`, and so on. |
| Entity type / id | The record affected, e.g. `user` / `42` or `app_setting` / `organization`. |
| Summary | A human-readable line, e.g. "Lesson created: Beginners A @ 12.09.2026 17:00". |
| Changes | Field-by-field before/after values. |
| IP address | Where the request came from. |
| Timestamp | UTC. |

Actions worth knowing are recorded specifically:

- **Forced lessons** — creating a lesson with "Create anyway" records that it was forced and how many conflicts were overridden.
- **Payment deletions and refunds** — with their mandatory reason.
- **Settings changes** — the previous and new value of the setting.
- **Role changes** — the user's roles before and after.
- **Report exports** — which report, in which format.
- **Restores** — every attempt, successful or not.

Audit entries are written in the **same database transaction** as the business change, so it is not possible for a change to succeed while its audit record is lost.

### 8.2 What is never recorded

Sensitive fields are masked as `***` before anything is written: passwords in any form (`password`, `new_password`, `current_password`, `hashed_password`), API keys (`api_key`, `nvidia_api_key`, `local_ai_api_key`), `secret_key`, and tokens (`token`, `access_token`, `refresh_token`). The masking is applied recursively to nested structures and to any field whose name contains "password" or "secret". Long strings are truncated at 500 characters.

The same redaction runs on the log files, so an API key cannot reach `application.log` either.

### 8.3 Filtering

| Filter | Notes |
|--------|-------|
| User | Everything one person did. |
| Action | E.g. all `delete` actions. |
| Entity type | E.g. all changes to `payment`. |
| Entity id | The full history of one specific record — the most useful filter when investigating a dispute. |
| Days | Defaults to the last 30 days. |

Results are paginated, newest first.

For a question like "why does this student's balance look wrong?", filter by entity type `payment` and that student's records, and read the sequence.

---

## 9. Backup management

**Full procedures — including restore, verification and disaster recovery — are in [BACKUP_RESTORE_EN.md](BACKUP_RESTORE_EN.md).** This section covers what an administrator needs to know day to day.

### 9.1 What a backup contains

A backup is a ZIP archive containing the database, a `backup_manifest.json` with SHA-256 digests of every file, and optionally uploads and logs.

**API keys and passwords are deliberately excluded.** The manifest carries an `excludes_secrets` flag, and verification fails if that flag is ever missing — a restored backup can never leak credentials, which also means `.env` must be protected separately.

### 9.2 Taking a backup

**Settings → Backup → New Backup**: choose the type, add a note explaining why, and decide whether uploads and logs are included. The archive is written to `backups\` (configurable via `BACKUP_DIR`).

Mark backups you must not lose — the one taken before a version upgrade, the end-of-year snapshot — as **protected**. The retention cleanup never deletes a protected backup.

### 9.3 Verification

Verification runs a series of integrity checks: the file exists, its size matches, the SHA-256 checksum matches what was recorded, the ZIP is not corrupt, the manifest is present and belongs to this backup, the secrets-excluded flag is set, and the database inside is readable.

A backup that has not been verified is a hope, not a backup. Verify after taking one, and always verify before restoring.

### 9.4 Scheduling and retention

Set `BACKUP_SCHEDULE_ENABLED=true` and a cron expression (default `0 23 * * *`, daily at 23:00). The scheduler starts with the application and posts each result as a notification.

Retention keeps 7 daily, 4 weekly and 12 monthly backups by default. Cleanup respects protected backups.

### 9.5 Restore, in one paragraph

Restoring overwrites the current database. The flow is: verify → automatic safety backup of the current state → preview showing which tables and how many records will be written → explicit confirmation → restore → integrity check → automatic rollback if anything fails. Every attempt is logged with date, user and outcome. Nobody else should be using the system while it runs. Details in [BACKUP_RESTORE_EN.md](BACKUP_RESTORE_EN.md).

### 9.6 The 3-2-1 rule

Backups in `backups\` on the same machine protect against mistakes, not against disk failure, theft or ransomware. Copy the archive somewhere else: three copies, on two different media, one off-site. A weekly copy to external storage takes a minute and is the difference between an incident and a catastrophe.

---

## 10. System health

**Settings → About / System health** (requires `system:health`), also available at `GET /api/v1/health` for external monitoring.

| Component | Status meanings |
|-----------|-----------------|
| `backend` | `ok` with the version number. |
| `database` | `ok` with the engine name (SQLite or the dialect in use) and query latency in milliseconds; `down` with the exception type if the connectivity check fails. |
| `ai:<provider>` | One entry per configured AI provider, with status, detail and latency. |
| `frontend` | `ok` when a built interface exists at `frontend\dist\index.html`; `degraded` when it does not, meaning a dev server is required. |

**Overall status is derived from `backend` and `database` only.** AI providers being down never degrades the system status, because the school runs perfectly well without AI — that is a design decision, not an oversight.

What to do with each result:

| Symptom | Action |
|---------|--------|
| `database: down` | Stop and investigate immediately. Check disk space and file permissions on `data\swimming_school.db`, then `logs\database.log`. |
| `database` latency climbing over time | Usually growth. Confirm with the database file size, then plan for PostgreSQL. |
| `frontend: degraded` | Run `BUILD_FRONTEND.bat`. |
| `ai:*: down` | Optional component. If local AI, check LM Studio is running and a model is loaded; if NVIDIA, check the key and connectivity. Nothing else is affected. |

A useful liveness endpoint that needs no authentication is `GET /api/ping`, which returns the application name and version. Every response also carries an `X-Process-Time` header with the server-side duration in milliseconds, which is the quickest way to tell a slow server from a slow network.

---

## 11. Training mode

Training mode is a per-user switch that makes it obvious you are practising rather than working. When it is on, the interface shows a persistent banner and demo records are highlighted.

Turn it on from **Settings → Profile → Training Mode**, or via `POST /api/v1/training/mode/true`.

Use it when:

- Onboarding a new staff member who is working through the Training Center tutorials.
- Demonstrating the system to a prospective client or a board.
- Testing a workflow you are unsure about.

Two important limits, stated plainly:

1. **Training mode is a visual warning, not a sandbox.** It does not redirect writes to a separate database. Anything you save in training mode is saved for real.
2. **For genuinely risk-free practice, use a separate installation** with its own `DATABASE_URL` and demo data, or take a backup first.

The honest use of training mode is "remind me I am in a lesson, not in production", and for that it works well.

---

## 12. Demo data

### 12.1 Generating it

```powershell
.\scripts\seed_demo.ps1
.\scripts\seed_demo.ps1 -Reset -Students 100 -Instructors 15
```

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `-Students` | 50 | Number of students to generate. |
| `-Instructors` | 10 | Number of instructors. |
| `-Reset` | off | Clear existing demo data first. |

The generator produces a coherent, interlinked dataset: pools with lanes, groups, instructors, guardians and students, memberships with invoices, payments and expenses, lessons with attendance, performance records with personal bests, and competitions with entries and results.

If students already exist and you did not pass `-Reset`, the script stops and tells you so rather than duplicating data.

It also creates one demo login per role, all with the password `Demo!2026`:

| Account | Role |
|---------|------|
| `mudur@yuzmeokulu.local` | School Director |
| `resepsiyon@yuzmeokulu.local` | Reception |
| `finans@yuzmeokulu.local` | Finance |
| `basantrenor@yuzmeokulu.local` | Head Coach |
| `egitmen@yuzmeokulu.local` | Swimming Instructor |
| `veli@yuzmeokulu.local` | Parent |

These are the fastest way to see exactly what each role can and cannot reach — sign in as `resepsiyon@` and the Finance and Statistics modules are simply absent from the menu.

### 12.2 Clearing it

Every generated record carries an `is_demo = true` flag, and clearing removes exactly those rows:

```powershell
.\scripts\seed_demo.ps1 -Reset
```

Because the flag is on the record rather than inferred from names or dates, clearing demo data never touches real records that happen to look similar.

### 12.3 Why not in production

**`APP_ENV=production` blocks demo-data generation outright.** The script refuses with an error and the underlying function raises rather than proceeding. This is intentional, and you should not work around it:

- Demo records contaminate every statistic. Revenue, attendance rates, occupancy, retention and KPI achievement all become meaningless if half the rows are invented.
- Demo accounts have known passwords. Six live logins with a published password is not an acceptable risk on a system holding children's health information.
- Demo and real records become impossible to distinguish once staff start editing them.

Before going live, set `SEED_DEMO_DATA=false`, run `-Reset` once, and verify with a student count that matches your actual roster.

---

## 13. Maintenance tasks

### Daily

| Task | Where | Why |
|------|-------|-----|
| Review dashboard alerts | Dashboard | Overdue payments, expiring memberships and missing attendance are all cheaper to fix on the day. |
| Confirm every lesson has attendance | Dashboard → Today's schedule | Missing attendance corrupts both statistics and credit consumption. |
| Confirm the scheduled backup ran | Notifications, or Settings → Backup | A backup that silently stopped a fortnight ago is the classic disaster. |
| Glance at system health | Settings → About | Ten seconds. |

### Weekly

| Task | Where | Why |
|------|-------|-----|
| Work the expiring-membership and low-credit lists | Memberships | Renewal is far easier before expiry than after. |
| Work the receivables ageing report | Finance → Outstanding | Debt gets harder to collect with age; the 60+ bucket needs a decision, not a reminder. |
| Review instructor workload | Statistics → Instructors | Catch imbalance before it becomes resignation. |
| Check expiring certificates | Instructors → Certificates | A lapsed lifeguard qualification is a legal problem, not an admin one. |
| Copy a backup off-site | `backups\` | See §9.6. |
| Scan the audit log for unexpected activity | Settings → Audit | Especially deletions, forced lessons and refunds. |

### Monthly

| Task | Where | Why |
|------|-------|-----|
| Refresh membership statuses | Memberships → Refresh statuses | Bulk-updates memberships whose end date has passed. Run at the start of each month. |
| Run the notification scan | Settings → Maintenance | Regenerates notifications for expiring memberships, overdue payments and upcoming competitions. |
| Produce the monthly management report | Reports | KPIs, revenue and student movement in one document. |
| Review KPI achievement and targets | Statistics → KPI | See §6.3. |
| Verify a backup by restoring it into a test installation | — | An unverified restore path is not a restore path. |
| Review user accounts | Settings → Users | Deactivate anyone who has left; confirm nobody has more roles than their job needs. |
| Check disk space | `data\`, `backups\`, `logs\` | Logs rotate at 5 MB with 5 generations per category, but backups grow without limit beyond the retention policy. |

### Quarterly

- Rotate the administrator password and any AI API keys.
- Review the correlation between what you thought your capacity problem was and what the heatmap actually shows.
- Run `FINAL_CHECK.bat` and read every warning, not just the failures.

---

## 14. Update procedure

Follow the four steps in order. The third one is the one people skip and regret.

### Step 1 — Back up

```
Settings → Backup → New Backup
  note: "before upgrade to <version>"
  include uploads: yes
  → Verify
  → Mark as protected
  → Copy the archive to external storage
```

Do not proceed until verification passes.

### Step 2 — Update the code

Stop the application (close the window). Then obtain the new version — `git pull` if you are working from the repository, or unpack the release archive over the installation, keeping your `.env`, `data\` and `backups\` untouched.

Install any new dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

If the interface changed, rebuild it:

```bat
BUILD_FRONTEND.bat
```

### Step 3 — Migrate

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
```

`START_SWIMMING_SCHOOL.bat` also runs `upgrade head` automatically, but running it manually lets you read the output rather than have it hidden behind a progress line.

If a migration fails, **stop**. Do not start the application on a half-migrated schema. Restore the backup from step 1 and investigate before trying again.

### Step 4 — Verify

Start the application and check, in this order:

1. **System health** — all components `ok`.
2. **Settings → About** — the application version and the database revision are what you expect.
3. **Dashboard** — student and lesson counts match what you saw before the upgrade.
4. **One record of each main type** — open a student, a lesson, a payment and a performance record. Cheap, and it catches almost everything a migration can get wrong.
5. **`FINAL_CHECK.bat`** — the full quality gate.

The release gate runs backend lint, formatting, type checking and the 395-test-function suite; migration application and model/migration synchronisation; backend and frontend translation completeness (1,027 keys, equal in both languages); a backup-and-verify smoke test; frontend type check, lint and build; secret scanning across the source tree and the git index; dependency vulnerability audit; and a check that all required documentation files exist. It reports PASS / FAIL / WARNING per check and exits non-zero on any failure.

If anything is wrong after the upgrade: stop the application, restore the step 1 backup, restart, and confirm the dashboard counts. Then report the problem with the version numbers and the relevant log excerpt.

---

## 15. Troubleshooting

### 15.1 Where the logs are

All logs are in `logs\` (configurable via `LOG_DIR`). Each category rotates at 5 MB and keeps 5 generations. Set `LOG_JSON=true` for one-line JSON records if you are feeding a log aggregator.

| File | Contents |
|------|----------|
| `application.log` | Startup and shutdown, general application events, unhandled errors. **Start here.** |
| `database.log` | Database connection and query-level events. |
| `security.log` | Login attempts, rate limiting, lockouts, authentication failures. |
| `audit.log` | A mirror of the audit trail in text form. |
| `ai.log` | AI provider calls, model selection, failures and fallbacks. Prompt contents only if `AI_LOG_PROMPTS=true`. |
| `developer-agent.log` | AI Developer Console activity: reads, searches, plans, patches, tests, applies and rollbacks. |

Sensitive values are redacted before writing, so it is safe to send a log excerpt to support — but read it first anyway.

Text format is `timestamp | LEVEL | logger | message`.

### 15.2 Common problems

**The program will not start; the window flashes and closes.**
Open `logs\application.log` and read the last 30 lines. The usual causes are a port 8000 conflict (another instance still running — check Task Manager for `python.exe`), a malformed `.env`, or a failed migration.

**"Address already in use" on port 8000.**
An earlier instance did not shut down. End the `python.exe` process, or change `APP_PORT` in `.env`.

**Startup logs "Başlangıç verisi yüklenemedi" (seed data could not be loaded).**
The application starts anyway by design, but roles or the admin account may be missing. Almost always a database permission or disk-space problem. Check that `data\swimming_school.db` is writable and that the disk is not full, then restart.

**Login always fails, even with the right password.**
Check `logs\security.log`. If you see rate-limit entries, wait a minute. If the account is locked (8 consecutive failures, 15 minutes), reset the password from another administrator account — the reset clears the lock. If `SECRET_KEY` was changed, all existing sessions are invalid and everyone must sign in again, but passwords still work.

**A user cannot see a screen they should.**
Check their roles under Settings → Users, and cross-reference §3.2. Remember that permissions are additive and there is no deny rule: if they hold a role with the permission, they will see it. If they hold the role and still cannot, have them sign out and back in — permissions are resolved at sign-in.

**Reports export but Turkish characters are wrong in the PDF.**
The PDF generator looks for DejaVu Sans, Arial or Calibri on the machine and falls back to Helvetica if none is found, which cannot render every Turkish character. Install one of those fonts. `application.log` records a warning when the fallback happens.

**A migration fails.**
Do not start the application. Restore the pre-upgrade backup, then reproduce the failure with the Alembic output visible. `alembic check` tells you whether models and migrations are in sync.

**The database is growing quickly / queries feel slow.**
Check the size of `data\swimming_school.db`. SQLite handles a single school comfortably; multi-site installations with years of attendance and performance history should plan the PostgreSQL move. Note the backup limitation in §1.4 before switching.

**AI features return errors.**
Run the health check from the AI Center. For local AI, confirm LM Studio's server is started and a model is loaded; for NVIDIA, confirm the key in `.env` and outbound connectivity. Check `ai.log`. Nothing else in the system is affected — statistics, reports and every operational screen are computed from the database.

**A scheduled backup did not run.**
Confirm `BACKUP_SCHEDULE_ENABLED=true` and that the cron expression is valid. The scheduler starts with the application, so it does not run while the program is closed — on a machine that is switched off at night, move the schedule to working hours. `application.log` records a warning if the scheduler fails to start.

**Disk full.**
Check `backups\` first; retention limits the count but not the total size. Then `logs\` (capped at roughly 30 MB per category) and `data\uploads\`.

### 15.3 Information to collect before asking for help

1. Application version and database revision (Settings → About).
2. The system health report.
3. The last 50 lines of `application.log`, plus the category log matching the problem area.
4. The relevant audit log entries — who did what, when.
5. Exact reproduction steps and the exact error message.

Those five turn a two-day investigation into a ten-minute one.

---

## Related documents

| Document | Contents |
|----------|----------|
| [USER_GUIDE_EN.md](USER_GUIDE_EN.md) | Day-to-day operational use. |
| [BACKUP_RESTORE_EN.md](BACKUP_RESTORE_EN.md) | Backup and restore procedures in full. |
| [STATISTICS_GUIDE_EN.md](STATISTICS_GUIDE_EN.md) | The statistics engine and how to interpret its output. |
| [AI_GUIDE_EN.md](AI_GUIDE_EN.md) | AI providers, configuration and the statistics/AI separation. |
| [SECURITY.md](SECURITY.md) | Security model and hardening. |
| [ARCHITECTURE.md](ARCHITECTURE.md) · [DATABASE.md](DATABASE.md) · [API.md](API.md) | Technical reference. |
| [CHANGELOG.md](../CHANGELOG.md) | Release history and known limitations. |
