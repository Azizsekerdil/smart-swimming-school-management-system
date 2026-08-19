# Backup and Restore Guide

This document explains the backup, integrity verification and disaster recovery
capabilities of the Smart Swimming School Management System end to end. Its purpose
is to make sure you already know what to do before you ever lose data.

> Version: 0.9.0 · Source: `backend/app/services/backup.py`, `backend/app/api/v1/backup.py`
> User interface: **Settings → Backup** tab

---

## 1. What a Backup Is and What Goes Into It

A backup is a single ZIP archive holding a copy of the system's state at one point
in time. Keep that file and you can return the school to that moment even if the
database is deleted or corrupted.

### 1.1 What is included

| Content | Path inside archive | Description |
|---|---|---|
| Database | `database/swimming_school.db` | All student, guardian, instructor, lesson, attendance, membership, finance, performance and competition records (50 tables) |
| Settings | `settings.json` | Version, environment, currency, language, timezone and the **secret-free** AI configuration |
| Uploaded documents | `uploads/...` | Every file under `data/uploads` (medical reports, photos, contracts) — optional |
| Log files | `logs/*.log` | Application logs — optional, **off by default** |
| Manifest | `backup_manifest.json` | The backup's identity card: id, timestamp, type, version, schema revision, record counts, file list and SHA-256 digests |

The database copy is taken through the `sqlite3.Connection.backup()` online backup
API. This produces a **consistent** copy even while the program is running and other
connections are open — no half-written transaction is captured.

The manifest's `record_counts` field stores the row count of these 12 tables and is
later used as the comparison baseline during verification: `users`, `students`,
`guardians`, `instructors`, `pools`, `lessons`, `attendances`, `memberships`,
`payments`, `invoices`, `performance_records`, `competitions`.

### 1.2 What is NEVER included — by security design

A backup file can be moved off the machine, e-mailed or copied to a USB stick.
Therefore no secret is placed inside it:

| Excluded | Reason |
|---|---|
| The `.env` file | It holds `SECRET_KEY`, `NVIDIA_API_KEY`, `FIRST_ADMIN_PASSWORD` and similar values |
| API keys | AI provider keys are stripped before `settings.json` is written (`_sanitized_ai_config`) — not even the masked form reaches the backup |
| `.key`, `.pem` files | Private keys / certificates |
| Files whose name contains `credentials`, `secrets`, `token`, `id_rsa` | Likely to carry credentials |

This filter is applied through the `EXCLUDED_PATTERNS` list while scanning both the
`uploads` and `logs` folders.

> **The accurate story about passwords:** the system never stores a plaintext
> password anywhere. User passwords live in the database only as bcrypt hashes, and
> the backup does contain those hashes — without them nobody could sign in after a
> restore. Plaintext credentials and API keys exist only in the `.env` file, and
> **that file is not backed up**. This is why you must supply `.env` separately after
> restoring onto a fresh machine (see §8c).

### 1.3 Structure of a backup file

```
bkp_20260818_230000_scheduled.zip
├── backup_manifest.json          ← identity + SHA-256 digests
├── database/
│   └── swimming_school.db        ← consistent SQLite snapshot
├── settings.json                 ← secret-free configuration
├── uploads/                      ← (when include_uploads = true)
│   └── ...
└── logs/                         ← (when include_logs = true)
    └── application.log
```

The backup id follows the pattern `bkp_YYYYMMDD_HHMMSS_<type>`.
Example: `bkp_20260818_230000_scheduled`.

The SHA-256 digest of the whole archive is stored in
`BackupRecord.checksum_sha256`; a single changed byte makes verification fail.

---

## 2. Backup Types

`BackupType` (see `backend/app/models/enums.py`) records **why** a backup was taken.
The content and verification flow are identical for every type.

| Type | Code | When it happens | Who triggers it |
|---|---|---|---|
| Full | `full` | Deliberate archive of the entire system | User (by choosing the type) |
| Manual | `manual` | The "Back Up Now" button — **default type** | User |
| Scheduled | `scheduled` | Automatically when the cron time arrives | System (APScheduler) |
| Pre-update | `pre_update` | Before upgrading the application version | User / upgrade step |
| Pre-migration | `pre_migration` | Before an Alembic schema change | User / administrator |
| Safety | `safety` | **Automatically before every restore** | System (restore flow) |
| Incremental | `incremental` | Defined in the model, **not implemented** in this release | — |

`safety` backups are automatically flagged `is_protected = true`, so the retention
policy can never delete them.

### 2.1 Backup statuses

| Status | Meaning |
|---|---|
| `creating` | The archive is being written |
| `completed` | Archive written, not verified yet |
| `verified` | Archive written **and every integrity check passed** — this is a trustworthy backup |
| `corrupted` | At least one integrity check failed |
| `failed` | The backup could not be produced; the half-written archive is deleted |

Only restore from backups in the `verified` state.

---

## 3. Creating a Backup

### 3.1 Step by step in the interface

1. Open **Settings** from the left menu.
2. Switch to the **Backup** tab. (The tab appears only if you hold `backup:read`.)
3. Press **Back Up Now** in the top-right. (Requires `backup:create`.)
4. Choose the options in the dialog:

| Option | Default | Description |
|---|---|---|
| **Backup type** | `manual` | One of the types in §2 |
| **Note** | empty | Write down why you took it ("before the v0.9 upgrade") |
| **Include documents** (`include_uploads`) | **On** | Adds everything under `data/uploads`. Turning it off makes the archive smaller, but the documents will not come back |
| **Include logs** (`include_logs`) | **Off** | Adds `logs/*.log`. Turn it on only when sending the archive for troubleshooting |
| **Protect** (`protect`) | Off | Exempts the backup from the retention policy; automatic cleanup will not delete it |

5. Confirm with **Back Up**. When it finishes the list refreshes and the row shows a
   status badge plus a verification message such as
   `All checks passed (11/11).`

Backups are written to `C:\SwimmingSchool\backups` by default. You can copy the
folder path from the **Backup Location** card.

### 3.2 Through the API

```bash
# Back up now (documents included, logs excluded, protected)
curl -X POST http://127.0.0.1:8000/api/v1/backup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "backup_type": "pre_update",
        "note": "Before the 0.9.0 -> 1.0.0 upgrade",
        "include_uploads": true,
        "include_logs": false,
        "protect": true
      }'
```

The response carries `backup_id`, `size_mb`, `status` and `verification_message`.

### 3.3 Backup endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/backup/status` | `backup:read` | Last backup, total size, protected count, next scheduled run |
| GET | `/api/v1/backup` | `backup:read` | Backup list (100 rows by default) |
| POST | `/api/v1/backup` | `backup:create` | Create a new backup |
| POST | `/api/v1/backup/{backup_id}/verify` | `backup:read` | Run integrity verification |
| GET | `/api/v1/backup/{backup_id}/restore-preview` | `backup:restore` | Restore preview (changes nothing) |
| POST | `/api/v1/backup/restore` | `backup:restore` | Restore (`confirm=true` mandatory) |
| POST | `/api/v1/backup/{backup_id}/protect` | `backup:create` | Toggle the protection flag |
| DELETE | `/api/v1/backup/{backup_id}` | `backup:create` | Delete a backup (protected ones cannot be deleted) |
| POST | `/api/v1/backup/cleanup` | `backup:create` | Apply the retention policy |
| GET | `/api/v1/backup/settings/current` | `backup:read` | Cron and retention settings |
| GET | `/api/v1/backup/location/open` | `backup:read` | Backup folder path, file count, 10 most recent files |
| GET | `/api/v1/backup/restores/history` | `backup:read` | Restore history |

### 3.4 Who can back up, who can restore

| Permission | Roles that hold it |
|---|---|
| `backup:read` | System Administrator, School Director, Operations Manager |
| `backup:create` | System Administrator, School Director, Operations Manager |
| `backup:restore` | **System Administrator and School Director only** |

Restore permission is deliberately the narrowest — it is the only operation that can
destroy data.

---

## 4. Integrity Verification

Every backup is verified **automatically right after it is created**. You can also
re-run verification at any time with the **Verify** button on each row.

Verification runs in 8 stages covering 11 individual checks. Each is reported as
`PASS` / `FAIL`; **if even one fails, the backup is marked `corrupted`.**

| # | Stage | Check code | What it proves | What a failure means |
|---|---|---|---|---|
| 1 | File exists | `file_exists` | The ZIP at `BackupRecord.file_path` is present on disk | The file was manually deleted or moved, or the drive is not mounted. Verification stops here |
| 2 | Size is sane | `size_reasonable` | The archive is larger than 1024 bytes | Writing was interrupted; an empty shell file |
| 3 | Checksum | `checksum_matches` | SHA-256 of the file on disk equals the digest recorded at creation time | The file **changed** after creation: bad copy, disk error or tampering |
| 4 | Archive integrity | `archive_intact` | `ZipFile.testzip()` — the CRC of every entry matches | One or more files inside the ZIP are damaged |
| 5 | Manifest | `manifest_present`, `manifest_valid`, `secrets_excluded`, `database_present` | `backup_manifest.json` exists; its `backup_id` matches the record; `excludes_secrets: true`; the `database/swimming_school.db` entry is present | The archive was mixed up with another backup, or carries no secret-exclusion guarantee |
| 6 | Database opens | `database_integrity` | The `.db` extracted to a temporary folder is opened and `PRAGMA integrity_check` returns `ok` | The SQLite file is corrupt at page level — restoring it would not work |
| 7 | Tables readable | `tables_readable` | Table count read from `sqlite_master` must exceed 10 | The schema is incomplete or an empty database was archived |
| 8 | Record counts match | `record_counts_match` | The `students` row count inside the archived database equals the expected value in the manifest | Snapshot and manifest disagree; the backup is not trustworthy |

When verification finishes a summary message is stored:
`All checks passed (11/11).` or `Verification failed: 9/11 checks passed.`
This text is shown in the **Integrity** column of the list.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/backup/bkp_20260818_230000_scheduled/verify \
  -H "Authorization: Bearer $TOKEN"
```

> Verification opens a temporary folder named `backups/.verify_<backup_id>` and
> removes it in every case when finished. The backup itself is never modified.

---

## 5. Scheduled Backups

Scheduled backups are enabled from the `.env` file and installed with APScheduler
at application start (`start_backup_scheduler`). The scheduler uses the timezone in
`APP_TIMEZONE` (default `Europe/Istanbul`).

```ini
# .env
BACKUP_SCHEDULE_ENABLED=true
BACKUP_SCHEDULE_CRON=0 23 * * *     # every day at 23:00
BACKUP_DIR=./backups
BACKUP_RETENTION_DAILY=7
BACKUP_RETENTION_WEEKLY=4
BACKUP_RETENTION_MONTHLY=12
```

Restart the application after changing these values (`START_SWIMMING_SCHOOL.bat`).

### 5.1 Cron expression examples

Format: `minute hour day-of-month month day-of-week`

| Expression | Meaning |
|---|---|
| `0 23 * * *` | **Every day at 23:00** (default) |
| `30 2 * * *` | Every night at 02:30 |
| `0 23 * * 0` | **Every Sunday at 23:00** (0 = Sunday) |
| `0 23 * * 6` | Every Saturday at 23:00 |
| `0 3 1 * *` | **First day of the month at 03:00** |
| `0 12,23 * * *` | Twice a day, at 12:00 and 23:00 |
| `0 23 * * 1-5` | Weekdays at 23:00 |
| `0 */6 * * *` | Every six hours |

Pick an hour when the pool is closed and nobody is entering data. A backup taken
during busy hours is still consistent, but it uses disk and CPU unnecessarily.

### 5.2 What happens when a scheduled backup runs

1. A `scheduled` backup is created and verified automatically.
2. The **retention policy is applied immediately afterwards** (`apply_retention`) —
   old backups are pruned.
3. A notification is sent to users holding the `system_admin` role. Title:
   *"Scheduled backup completed (24.6 MB)"*, with the verification message in the
   body. If the backup is not `verified`, the notification is sent at **warning**
   severity.

You can see the next run time on the **Settings → Backup → Next Backup** card.

---

## 6. Retention Policy

The retention policy thins out old backups **progressively** so the disk does not
fill: one per day for the recent past, one per week in the mid range, one per month
further back.

| Setting | Default | Meaning |
|---|---|---|
| `BACKUP_RETENTION_DAILY` | 7 | **Every** backup of the last 7 days is kept |
| `BACKUP_RETENTION_WEEKLY` | 4 | Between 7 and 28 (4×7) days old, **one backup per ISO week** is kept |
| `BACKUP_RETENTION_MONTHLY` | 12 | Between 28 and 372 (12×31) days old, **one backup per month** is kept |

Decision order (`apply_retention`, scanning newest to oldest):

1. If the backup's age is less than or equal to `daily` → **keep**.
2. Otherwise, if its age is within `weekly × 7` days and no backup from that ISO
   week has been kept yet → **keep** (the newest one of that week).
3. Otherwise, if its age is within `monthly × 31` days and no backup from that month
   has been kept yet → **keep** (the newest one of that month).
4. If none applies → **delete**.

### 6.1 Protected backups

Backups flagged `is_protected = true` are **excluded from this scan entirely**; the
retention policy never deletes them, and `DELETE /api/v1/backup/{id}` rejects them
with a `backup.protected` error. To make a backup permanent:

* Press the **Protect** button on the row, or
* Call `POST /api/v1/backup/{backup_id}/protect?protect=true`.

Send `protect=false` to the same endpoint to lift protection.

Recommended candidates for protection: end-of-season archive, the `pre_update`
backup taken before a major upgrade, and the audit / accounting close-out backup.

### 6.2 Running the policy manually

Use **Settings → Backup → Clean Up**, or:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/backup/cleanup \
  -H "Authorization: Bearer $TOKEN"
```

The response reports the number of deleted backups, their ids, the space freed (MB)
and how many were kept.

---

## 7. Restoring

A restore **replaces** the current database with the one inside the backup. Every
record entered after the backup was taken is lost. That is why the flow is
multi-step and reversible.

### 7.1 The safe restore flow

```
1. VERIFY          verify_backup() — 11 checks
                   ✗ failed → the operation STOPS here, nothing changes
2. SAFETY BACKUP   create_backup(type=safety, protect=true)
                   ✗ cannot be taken → the operation STOPS, nothing changes
3. PREVIEW         restore-preview — shows exactly what will change
4. CONFIRMATION    the endpoint refuses to run without confirm=true
5. RESTORE         close connections → copy to .db.pre_restore → clear -wal/-shm
                   → put the archived .db in place → write documents back
6. INTEGRITY       PRAGMA integrity_check + student count + SELECT 1 health test
7. ROLLBACK        if any step fails, .db.pre_restore is put back
```

The outcome of each step (`success` / `failed`) is stored in the `steps` array of the
response and in the `RestoreRecord` table; it is visible on the **Restore History**
card.

### 7.2 Step by step in the interface

1. Open **Settings → Backup**.
2. Find the backup you want. Confirm that its status is **`verified`**. If it is not,
   press **Verify** first.
3. Press **Restore** on the row. (Requires `backup:restore`.)
4. **The preview screen opens. Read it before closing** (see §7.3).
5. Make sure **Create safety backup** stays ticked (on by default).
6. Tick the confirmation box and click **Restore**.
7. When it finishes, the step list and the result message are shown.
8. **Close and restart the program.** The result message says so as well:
   *"Restore completed. Restart the application for all changes to take effect."*

### 7.3 How to read the preview screen

The preview (`GET /api/v1/backup/{backup_id}/restore-preview`) changes nothing; it
only compares.

| Field | What it shows | How to read it |
|---|---|---|
| `integrity_ok` | Whether the backup passed verification | If `false`, do not restore |
| `backup_created_at` | The moment the backup was taken | Everything after this moment will be lost |
| `backup_app_version` / current version | Application versions | A mismatch raises a warning |
| `backup_db_revision` / `current_db_revision` | Alembic schema revisions | If they differ, a migration may be needed after restoring |
| `revision_compatible` | Whether the schema revisions are identical | `false` → proceed carefully |
| `current_counts` | Row counts right now | For the 12 tracked tables |
| `backup_counts` | Row counts inside the backup | For the 12 tracked tables |
| `differences` | `backup − current` | **A negative number means you will lose records in that table** |
| `warnings` | Plain-language warnings | See below |

**The data-loss warning — the most important line.** If any difference is negative,
this warning is produced:

> Some records WILL BE LOST as a result of this restore: students: 14, payments: 37

It means "14 students and 37 payments were entered after the backup was taken, and
the restore will erase them". When you see this line:

* Export the records that will be lost first (Reports → Excel/CSV), or
* Pick a newer backup, or
* Accept the loss and continue — the safety backup lets you come back.

Other warning texts:

| Warning | Meaning |
|---|---|
| *The backup failed integrity verification. Restoring is not recommended.* | A `corrupted` backup — do not use it |
| *Database schema version differs (backup: `abc123`, current: `def456`)...* | The backup comes from an older schema; `alembic upgrade head` may be needed afterwards |
| *Application version differs (backup: 0.8.0, current: 0.9.0).* | The backup was taken by an older program version |

### 7.4 Restoring through the API

```bash
# 1) Preview first (changes nothing)
curl http://127.0.0.1:8000/api/v1/backup/bkp_20260818_230000_scheduled/restore-preview \
  -H "Authorization: Bearer $TOKEN"

# 2) Confirmed restore
curl -X POST http://127.0.0.1:8000/api/v1/backup/restore \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "backup_id": "bkp_20260818_230000_scheduled",
        "confirm": true,
        "create_safety_backup": true
      }'
```

If `confirm` is `false` or missing, the request is rejected with a
`confirmation_required` validation error. Do not set `create_safety_backup` to
`false` — that removes your own safety net.

Response:

```json
{
  "success": true,
  "backup_id": "bkp_20260818_230000_scheduled",
  "safety_backup_id": "bkp_20260819_101512_safety",
  "message": "Restore completed. Restart the application for all changes to take effect.",
  "rolled_back": false,
  "steps": [
    {"step": "verify_backup",   "status": "success", "detail": "All checks passed (11/11)."},
    {"step": "safety_backup",   "status": "success", "detail": "bkp_20260819_101512_safety"},
    {"step": "extract_archive", "status": "success", "detail": "128 documents"},
    {"step": "restore_database","status": "success", "detail": "C:\\SwimmingSchool\\data\\swimming_school.db"},
    {"step": "restore_uploads", "status": "success", "detail": ""},
    {"step": "integrity_check", "status": "success", "detail": "student count: 412"},
    {"step": "health_check",    "status": "success", "detail": "schema revision: a1b2c3d4e5f6"}
  ]
}
```

### 7.5 Rollback — when something goes wrong

Just before the database file is replaced, a copy of the current database is taken as
`swimming_school.db.pre_restore`. If any later step fails (file locked, disk full,
corrupt database) that copy is put back automatically and the response reports
`rolled_back: true`:

> Restore failed: RuntimeError. The system was returned to its previous state.

If the rollback itself fails, the response shows the **id of the safety backup**
created in step 2. You can attempt a second restore from that backup.

When everything succeeds the `.pre_restore` file is deleted.

---

## 8. Disaster Recovery Scenarios

### (a) Accidental bulk deletion

**Symptom:** someone deleted a group, a period's lessons or a large number of
students by mistake.

**Fix:**

1. **Stop new data entry immediately.** Every passing minute creates records that
   the restore will destroy.
2. Open **Settings → Backup** and find the newest `verified` backup taken **before**
   the deletion. The **Audit Log** screen tells you exactly when the deletion happened.
3. **Restore** → read the preview. The tables in the data-loss warning show the real
   new records entered after the deletion.
4. If new records will be lost, export them as a report first
   (Reports → Student List / Collections Report → Excel).
5. Confirm, restore, and restart the program.
6. Re-enter the records exported in step 4.

### (b) Database corruption

**Symptom:** the program will not start, an error such as "database disk image is
malformed" appears, screens come up empty, SQLite errors show in the logs.

**Fix:**

1. Close the program.
2. Do **not** delete `C:\SwimmingSchool\data\swimming_school.db`; rename it to
   `swimming_school.db.broken` and set it aside. It may need inspection.
3. Start the program — an empty database is created and the default roles are seeded.
4. Sign in as administrator (default e-mail: `admin@yuzmeokulu.local`).
5. **Settings → Backup** → pick the newest `verified` backup → **Verify** →
   **Restore**.
6. Restart the program and eyeball a few records: student count, recent payments.

> Because the backup list itself lives in the database, it may look empty on a fresh
> database. The ZIP files are still in the `backups` folder; follow the steps in §8c
> to bring one back.

### (c) Hardware failure — the computer is gone

**Symptom:** the disk died, or the machine was stolen or burned.

**Precondition:** a copy of the backups exists **off the machine** (see §9). A backup
living only on the same disk does not save you from a disk failure.

**Fix:**

1. Install the program on the new computer, run it once and close it
   (`START_SWIMMING_SCHOOL.bat`) so the folder structure is created.
2. Copy the `bkp_*.zip` files from the external medium into the new machine's
   `backups` folder.
3. Recreate the `.env` file — **it is not in the backup**. Copy `.env.example` and
   re-enter values such as `SECRET_KEY` and `NVIDIA_API_KEY`. Changing `SECRET_KEY`
   only invalidates open sessions; no data is lost.
4. Start the program and sign in as administrator.
5. The database is empty, so the backup list is empty too. The simplest path: extract
   `database/swimming_school.db` from the newest ZIP and copy it to
   `data\swimming_school.db`; extract the `uploads/` folder into `data\uploads`.
   Restart the program.
6. The **Settings → Backup** list now shows the old backups again, and the normal
   restore flow is available from here on.
7. Final step: take a fresh `manual` backup immediately and mark it **protected**.

### (d) A bad migration

**Symptom:** the schema was upgraded with Alembic and afterwards screens throw errors
or data looks wrong.

**Fix:**

1. Stop the program.
2. Use the `pre_migration` backup you took before the migration. (This is exactly why
   you take one before every schema change and mark it **protected**.)
3. Roll the schema back:
   ```bash
   cd C:\SwimmingSchool\backend
   alembic downgrade -1
   ```
4. Start the program, then **Settings → Backup** → the `pre_migration` backup →
   **Verify** → **Restore**.
5. Watch the `revision_compatible` field in the preview; the restored database's
   schema revision must match what the code expects.
6. Restart the program.

> Migration problems cause schema mismatches more often than data loss. The correct
> order is always **backup first, migration second**.

---

## 9. Copying Backups Off the Machine

This release has no cloud backup target (see §10). Backups are written to the local
disk only. That is a **single point of failure**: if the disk goes, the backups go
with it.

### 9.1 The 3-2-1 rule

| Number | Rule | What it means here |
|---|---|---|
| **3** | At least 3 copies | The live database + the `backups` folder + an off-machine copy |
| **2** | At least 2 different media | The computer's disk + an external drive / NAS / cloud drive |
| **1** | At least 1 copy in a different physical location | Off the premises: the director's office, a bank box or a cloud account |

### 9.2 Practical implementation

**Weekly manual copy (the simplest method):**

1. Copy the path with **Settings → Backup → Open Folder**
   (default `C:\SwimmingSchool\backups`).
2. Plug in the external drive.
3. Copy the `bkp_*.zip` files of the last one or two weeks. On Windows:
   ```powershell
   robocopy "C:\SwimmingSchool\backups" "E:\SwimSchool_Backup" bkp_*.zip /XO
   ```
   `/XO` copies only new or newer files.
4. Unplug the drive and store it **away from the computer**.

**Automatic copy via a cloud drive:** create a folder synchronised by the
OneDrive / Google Drive / Dropbox client and point the backup path at it in `.env`:

```ini
BACKUP_DIR=C:/Users/username/OneDrive/SwimSchool_Backup
```

The program then writes backups straight into the synchronised folder and the client
uploads them. Remember that the archive contains no API key and no `.env` — but do
not share the folder anyway; it **holds personal data about students (GDPR/KVKK)**.

### 9.3 Recovery drill

At least once a year, ideally at the start of a season:

1. Take one off-machine copy to **a different computer**.
2. Bring the system up there by following §8c.
3. Verify by eye: student count, last month's collection total and a few performance
   records.

An untested backup is not a backup.

---

## 10. Limitations

Deliberately out of scope in this release (0.9.0):

| Limitation | Detail | Planned |
|---|---|---|
| **SQLite only** | Automatic backup and restore work for SQLite. On PostgreSQL, `create_backup` raises: *"Automatic backup is only supported for SQLite in this release. Use pg_dump for PostgreSQL."* Restore is refused the same way | A `pg_dump` flow is planned for 1.0.0 |
| **No incremental backup** | `BackupType.INCREMENTAL` exists in the enum but is not implemented. Every backup is a full backup | On the roadmap |
| **No cloud target** | The `BackupProvider` abstraction is in place, but only `LocalDiskProvider` is implemented. No Drive / OneDrive / S3 connector | 1.1.0 |
| **No download endpoint** | The archive cannot be downloaded through the API; you need access to the folder. `GET /backup/location/open` returns only the path | — |
| **No encryption** | The ZIP has no password and no encryption. It contains personal data, so **restrict physical access** | — |
| **Only `.log` files** | `include_logs` picks up `*.log` in the `logs` folder; rotated files (`.log.1`) are not included | — |
| **Restart required** | After a restore, open connections may still point at the old file; the program must be restarted | — |

---

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The Backup tab is missing | You lack `backup:read` | Requires the System Administrator, School Director or Operations Manager role |
| No "Back Up Now" button | You lack `backup:create` | Same roles are required |
| No "Restore" button | You lack `backup:restore` | System Administrator and School Director only |
| The backup is `failed` | Disk full, folder not writable, or the database file was not found | Read the error message on the row; check that `backups` is writable and that free space exists |
| `file_exists` FAIL | The ZIP was manually deleted or moved | Put the file back, or delete the record and take a new backup |
| `checksum_matches` FAIL | The file changed after creation (bad copy, disk error) | Do not use this backup; try the off-machine copy, take a new backup, check the disk |
| `database_integrity` FAIL | The SQLite file inside the archive is corrupt | This backup is unrecoverable; go back to the previous `verified` one |
| `record_counts_match` FAIL | Manifest and snapshot disagree | Do not restore this backup; take a new one |
| A backup cannot be deleted | It is protected (`backup.protected` error) | Turn **Protect** off first (`protect=false`), then delete |
| Restore returns "confirmation_required" | The `confirm` field was not sent | Tick the confirmation box in the UI; send `"confirm": true` through the API |
| Restore reports "Safety backup could not be created" | Disk full or folder not writable | Free up space; nothing was changed and your data is intact |
| Restore failed with `rolled_back: true` | The file was locked or the copy failed | The system is back to its previous state. Close the program completely (check for stray `python`/`uvicorn` processes in Task Manager) and try again |
| Old data still shows after a restore | The application was not restarted | Close and reopen with `START_SWIMMING_SCHOOL.bat` |
| Scheduled backups do not run | `BACKUP_SCHEDULE_ENABLED=false` or a malformed cron expression | Set it to `true`, fix the expression per §5.1, restart the program. Look for *"Backup scheduler started: 0 23 * * *"* in the log |
| A scheduled backup ran but no notification arrived | The notification goes only to the `system_admin` role | Check the **Notifications** screen with an administrator account |
| The backup file is very large | `include_uploads` is on and there are many documents | Manage documents with a separate archiving strategy; disable documents on daily backups and take a document-inclusive backup weekly |
| PostgreSQL backup fails | Not supported in this release | Use `pg_dump` (§10) |

### 11.1 Following along in the log

Backup events are written to the application log in the `logs/` folder:

```
Backup created: bkp_20260818_230000_scheduled (24.63 MB, status: verified)
Retention policy: 3 backups deleted (71.20 MB)
Backup scheduler started: 0 23 * * *
```

On failure the full traceback goes to the same file; the interface shows only the
short message.

### 11.2 Audit trail

Every backup and restore operation is written to the audit log: `create`,
`restore_started`, `restore_finished`, `protect`, `unprotect`, `delete`, `cleanup`.
That is where you find out who did what, when, and from which IP address.

---

## Related documents

* `CHANGELOG.md` — release notes and known limitations
* `docs/STATISTICS_GUIDE_EN.md` — statistics and reporting guide
* `docs/AI_GUIDE_EN.md` — artificial intelligence user guide
* `.env.example` — every configuration key
