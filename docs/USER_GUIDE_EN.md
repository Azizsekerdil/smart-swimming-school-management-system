# User Guide

This guide explains how to run the daily work of a swimming school in the Smart Swimming School Management System: enrolling students, planning lessons, taking attendance, collecting payments, recording performance and producing reports. It is written for reception staff, instructors and coaches who use the program every day; system-wide configuration is covered separately in [ADMIN_GUIDE_EN.md](ADMIN_GUIDE_EN.md).

**Version:** 0.9.0 · **Licence:** MIT · **Interface languages:** Turkish and English

---

## Table of contents

1. [Getting started](#1-getting-started)
2. [Using the dashboard](#2-using-the-dashboard)
3. [Student management](#3-student-management)
4. [Guardian management](#4-guardian-management)
5. [Instructor management](#5-instructor-management)
6. [Pools and lanes](#6-pools-and-lanes)
7. [Creating a lesson](#7-creating-a-lesson)
8. [Recurring lessons](#8-recurring-lessons)
9. [The calendar](#9-the-calendar)
10. [Lane planning](#10-lane-planning)
11. [Taking attendance](#11-taking-attendance)
12. [Memberships and packages](#12-memberships-and-packages)
13. [Taking payments](#13-taking-payments)
14. [Recording performance](#14-recording-performance)
15. [Competition management](#15-competition-management)
16. [Building reports](#16-building-reports)
17. [Notifications](#17-notifications)
18. [Changing language and theme](#18-changing-language-and-theme)
19. [Keyboard shortcuts](#19-keyboard-shortcuts)
20. [Frequently asked questions](#20-frequently-asked-questions)
21. [Troubleshooting](#21-troubleshooting)

---

## 1. Getting started

### 1.1 Launching the program

Double-click **`START_SWIMMING_SCHOOL.bat`** in the project folder (`C:\SwimmingSchool`). No command line is needed.

On the very first run the launcher does several things automatically, which is why the first start takes a few minutes longer than later ones:

| Step | What happens |
|------|--------------|
| 1 | Checks for the Python virtual environment in `.venv`. If it is missing, it creates one and installs the backend dependencies from `backend\requirements.txt` plus `pywebview`. |
| 2 | Checks for the `.env` configuration file. If it is missing, it copies `.env.example` to `.env` and generates a fresh random `SECRET_KEY`. |
| 3 | Runs `alembic upgrade head` so the database schema is current. |
| 4 | Checks that the interface build exists at `frontend\dist\index.html`. If not, it warns you to run `BUILD_FRONTEND.bat` first. |
| 5 | Starts the backend and opens the program in a desktop window (Edge WebView2). If `pywebview` is unavailable it falls back to your default browser. |

The program window title is **Akıllı Yüzme Okulu Yönetim Sistemi**. Behind it the API runs on `http://127.0.0.1:8000`. Closing the window stops the backend cleanly.

> If Python is not installed at all, the launcher stops and tells you to install Python 3.11 or newer from python.org with the "Add Python to PATH" option ticked.

### 1.2 Signing in

The login screen asks for an e-mail address and a password. The default administrator account created on first start is:

```
E-mail:   admin@yuzmeokulu.local
Password: (the value of FIRST_ADMIN_PASSWORD in .env)
```

Change this password immediately after the first login. Everyday users should each have their own account — shared logins destroy the value of the audit log.

Points to know about signing in:

- **Forced password change.** If your administrator ticked "must change password at first login", you cannot reach any other screen until you set a new one. Passwords must be at least 8 characters and contain at least one letter and one digit; a handful of obvious passwords (`password`, `admin123`, `123456789`, `parola123`) are rejected outright.
- **Rate limiting.** After 10 failed attempts for the same e-mail within one minute the system refuses further tries for a short period.
- **Account lockout.** After 8 consecutive failed attempts the account locks for 15 minutes. An administrator can clear the lock immediately by resetting the password.
- **Session length.** Your access token lasts 120 minutes and is renewed silently while you work. If you leave the program idle for a long time you may be asked to sign in again.

### 1.3 A tour of the interface

**The sidebar (left).** Modules are grouped into sections: Overview, People, Operations, Finance, Sports, Analytics, Artificial Intelligence, and System. You only see the entries your roles allow — for example, someone without `finance:read` never sees the Finance module at all. The chevron button at the bottom collapses the sidebar to icons only, which is useful on small screens.

| Section | Screens |
|---------|---------|
| Overview | Dashboard |
| People | Students, Guardians, Instructors |
| Operations | Calendar, Lessons, Pools, Lanes, Attendance |
| Finance | Memberships, Finance |
| Sports | Performance, Competitions |
| Analytics | Statistics, Reports |
| Artificial Intelligence | AI Center, AI Developer, CAIO |
| System | Training Center, User Guide, Notifications, Settings |

**The top bar.** From left to right: the sidebar toggle, the global search box, the notification bell with an unread counter (refreshed every minute), the language button, the theme button, and your user menu.

**Global search.** Typing in the search box queries students, guardians, instructors, lessons, payments, pools and competitions at the same time and shows results grouped by type. Press <kbd>/</kbd> anywhere outside a text field to jump straight into it, and <kbd>Esc</kbd> to close it.

**Command palette (<kbd>Ctrl</kbd>+<kbd>K</kbd>).** The palette lists actions such as "New student" or "Take attendance" with the screen each one leads to. Type to filter, move with <kbd>↑</kbd>/<kbd>↓</kbd>, run with <kbd>Enter</kbd>, close with <kbd>Esc</kbd>. It works from any screen, so you never need to navigate back to a list just to start a new record. On macOS-style keyboards <kbd>⌘</kbd>+<kbd>K</kbd> works too.

**Theme.** The sun/moon button switches between light and dark. The choice is stored on your account, so it follows you to another computer.

**Language.** The language button switches the whole interface between Turkish and English instantly, with no page reload.

### 1.4 The Training Center

**System → Training Center** contains twelve step-by-step interactive tutorials that walk you through the program with links straight to the relevant screen. Tutorials are grouped into tracks (Getting Started, Operations Training, Manager Training, Coach Training, AI Training, System Administrator Training), and the tracks recommended for you are chosen automatically from your roles. Your progress through each tutorial is saved, so you can stop and come back later.

**System → User Guide** is a searchable in-program version of this document with 28 sections, available in both languages.

---

## 2. Using the dashboard

The dashboard is the landing screen and answers one question: *what needs my attention right now?* Figures refresh automatically every two minutes.

### 2.1 Alert cards

Alert cards appear across the top only when there is something to act on. Each one is clickable and takes you to a pre-filtered list.

| Alert | Severity | Where it takes you |
|-------|----------|--------------------|
| Overdue payments | Error (red) | Finance → Outstanding tab |
| Memberships expiring | Warning | Memberships, filtered to the next 14 days |
| Attendance missing for N lessons | Warning | Attendance |
| Performance decline in N athletes | Warning | Performance, declining filter |
| Upcoming competitions | Info | Competitions |

### 2.2 The counter cards

**Row 1 — core counters (everyone sees these):**

| Card | Meaning |
|------|---------|
| Active students | Students with status *active*. The hint underneath shows the total number of student records including inactive ones. |
| Lessons today | Lessons scheduled for today; the hint shows how many are already completed. |
| Pool occupancy | Share of lane capacity in use, with lanes-in-use / total-lanes underneath. Turns green at 70% and above. |
| Active instructors | Instructors currently marked active. |

**Row 2 — financial counters (only with `finance:read`):** collected today (with today's due amount as a hint), monthly revenue, net income (revenue minus monthly expenses, red when negative), and overdue receivables with the number of overdue records.

**Row 3 — operational counters:** today's attendance rate with the number of lessons still awaiting attendance, new registrations this month, memberships expiring within 14 days, and upcoming competitions with the count of declining athletes.

### 2.3 Today's schedule

The main table lists every lesson today with its time, pool, lane, instructor and enrolled count. Lessons whose attendance has already been recorded carry a green badge, so the ones still to do stand out at a glance. Click a row to open the lesson.

Below the table, two charts show the 30-day revenue trend and the hourly pool load, so you can see both the money and the crowding pattern of the month without leaving the screen.

---

## 3. Student management

### 3.1 Adding a student field by field

Open **People → Students** and click **New Student** (or press <kbd>Ctrl</kbd>+<kbd>K</kbd> and choose "New student").

| Field | Required | Notes |
|-------|:--------:|-------|
| First name | Yes | 1–80 characters. |
| Last name | Yes | 1–80 characters. |
| Student number | No | Leave blank and the system generates one in the `OGR00001` format. Supply your own only if you are migrating from another system. |
| Birth date | No | Cannot be in the future. Age is derived from it and used by age-range filters and reports. |
| Gender | No | Female / Male / Unspecified. Defaults to unspecified. |
| Phone | No | Up to 30 characters. |
| E-mail | No | Validated as an e-mail address when filled. |
| Address | No | Up to 400 characters. |
| Emergency contact name | No | Shown prominently on the profile. |
| Emergency contact phone | No | Keep this current — it is what reception reaches for in an incident. |
| Swim level | Yes (defaults to Beginner) | Beginner, Elementary, Intermediate, Advanced, Competitive, Elite. Used when filtering for lesson placement and in progress reports. |
| Status | Yes (defaults to Active) | Active, Passive, Trial, Frozen, Left. |
| Group | No | Optional; can be assigned or changed at any time. |
| Primary instructor | No | Used by the instructor filter across the program. |
| Registration date | No | Defaults to today. |
| Goals | No | Free text, e.g. "swim 25 m freestyle unaided by June". |
| Notes | No | General free text. |
| Health notes | No | **Protected.** Only visible to users with `student:read_sensitive`. |
| Special needs | No | **Protected**, same permission as health notes. |
| Consent | No, but strongly recommended | Records explicit consent to process personal data. Records without it are flagged as incomplete by the CAIO audit module. |
| Guardians | No | You can link existing guardian records here, or do it later from the profile. |

Click **Save**. The student is created and its profile opens.

### 3.2 Searching and filtering

The student list supports free-text search across name, student number, phone and e-mail, plus filters for status, swim level, group, primary instructor and age range. Results are paginated; sorting is available on the main columns.

A list that looks empty is nearly always a filter problem, not a data problem — use the **Clear filters** link before concluding a record is missing.

### 3.3 The profile tabs

Opening a student shows tabs that pull together everything about that person:

- **Overview** — identity, contact details, level, group, instructor, goals, and the attendance rate.
- **Membership** — current and past memberships, remaining credits, end date.
- **Payments** — payments, invoices and balance for this student.
- **Performance** — recorded times, personal bests and the progression chart.
- **Timeline** — a merged chronological history of enrolments, attendance, payments, membership changes and performance records.

### 3.4 Editing and deactivating

Edit from the profile with **Edit**; only the fields you actually change are written, and the change is recorded in the audit log.

To take a student off the active roster, set **Status** to *Left* (or *Passive* for a temporary pause). Deleting a student is a separate, permission-gated action and should be reserved for genuine data-entry mistakes — status changes keep the history intact, which is what reports and receivables depend on.

---

## 4. Guardian management

### 4.1 Adding a guardian

Open **People → Guardians → New Guardian**.

| Field | Required | Notes |
|-------|:--------:|-------|
| First name / Last name | Yes | |
| Relationship | Yes (defaults to *parent*) | Mother, father, parent, grandparent, sibling, other. Used in contact lists and reports. |
| Phone | Yes | 5–30 characters. This is the number notifications and call lists use. |
| Secondary phone | No | |
| E-mail | No | |
| Address | No | |
| Occupation | No | |
| Notes | No | |
| Students | No | You can link one or more students right away. |
| Create portal user | No | Ticking this creates a login so the guardian can see their own children's data. |

### 4.2 Linking guardians to students

One guardian record can be linked to any number of students, so siblings never need duplicate guardian entries. Link from either side — the guardian form or the student profile.

Each link carries three flags:

- **Primary guardian** — this contact is listed first in an emergency.
- **Can pick up** — whether this person may collect the child.
- **Billing contact** — whether invoices and payment reminders are addressed to them.

### 4.3 The guardian portal

A guardian with a portal account signs in with their own e-mail and password and sees only their own children. The portal shows upcoming lessons, recent attendance, membership status with remaining credits, payment history and outstanding balance, and performance progress.

This restriction is enforced at the data layer, not just by hiding menu items: a guardian account simply cannot retrieve another family's records, whatever address they type.

---

## 5. Instructor management

### 5.1 Adding an instructor

Open **People → Instructors → New Instructor**. Enter first name, last name and job title; the employee number is generated automatically in the `EGT0001` format.

Set the **specialties** (baby swimming, kids swimming, adaptive swimming, competition coaching, conditioning and so on). Specialties act as filters when you assign an instructor to a lesson, which is what stops a baby-swimming lesson being handed to someone who has never taught one.

### 5.2 Certificates

On the **Certificates** tab add lifeguard, first-aid and coaching qualifications, each with an issuing body and an expiry date. Certificates that have expired — or are about to — are highlighted in the list, so a lapsed lifeguard qualification is visible before it becomes a problem rather than after.

### 5.3 Availability

Availability is defined as a weekly pattern: for each weekday, the hours the instructor can teach. When you schedule a lesson outside that pattern the conflict engine raises a warning naming the instructor and the hour.

### 5.4 Leave

Enter planned leave with start and end dates and a reason. Lessons that fall inside a leave period are flagged during conflict checking, which means holiday clashes surface while you are still planning rather than on the morning of the lesson.

The **workload** view shows total lessons and teaching hours per instructor for a selected date range — the fastest way to see who is over- or under-loaded before you publish next month's timetable.

---

## 6. Pools and lanes

### 6.1 Defining a pool

Open **Operations → Pools → New Pool**.

| Field | Default | Notes |
|-------|---------|-------|
| Name | — | Required. |
| Code | — | Short code for reports, e.g. `MAIN`. |
| Location | — | Building or site. |
| Length (m) | 25 | Determines short-course / long-course classification of performance times. |
| Width (m) | — | Optional. |
| Min / Max depth (m) | — | Optional; useful for baby and beginner placement. |
| Lane count | 6 | 1–20. |
| Capacity | 60 | Total swimmers the pool can hold. |
| Course type | Short (25 m) | Short or Long (50 m). |
| Opening / Closing time | 07:00 / 22:00 | Closing must be later than opening. Lessons outside these hours raise a warning. |
| Status | Operational | Operational, Maintenance, Closed. |
| Water / Air temperature (°C) | — | Informational. |
| Indoor / Heated | Yes / Yes | |

### 6.2 Editing lanes

Lanes belong to a pool. Each lane has a number, an optional name, width, depth, maximum swimmers, an intended purpose (for example "beginners" or "competition team") and an active flag.

Deactivate a lane rather than deleting it when it is temporarily out of use — an inactive lane drops out of occupancy calculations and lesson suggestions but keeps its history.

If you create a lesson without choosing a lane, the system suggests a free one for that time slot.

### 6.3 Water-quality logging

On the pool's **Water quality** tab record a measurement with its timestamp, pH (0–14), free chlorine (ppm), temperature and turbidity (NTU), plus who measured it. Each entry is marked as within limits or outside them, and readings outside the acceptable band generate an automatic notification. The history view lets you see drift over days rather than judging each reading in isolation.

### 6.4 Maintenance

Schedule maintenance with a date range, type and description. While maintenance is booked the pool counts as closed for those dates and lesson scheduling raises a warning for anything that overlaps. Public holidays are handled separately in the holiday calendar, which recurring lessons can skip automatically.

---

## 7. Creating a lesson

### 7.1 The form

Open **Operations → Lessons → New Lesson**.

| Field | Notes |
|-------|-------|
| Title | Required, up to 160 characters. |
| Lesson type | 13 types: Group, Private, Kids, Baby, Adult, Beginner, Intermediate, Advanced, Competition team, Adaptive, Conditioning, Trial, Make-up. |
| Start / End | Date and time. |
| Pool | Required. |
| Lane | Optional — leave blank and the system proposes a free lane. |
| Instructor | Optional but normally set. |
| Group | Optional; links the lesson to a defined group. |
| Capacity | 1–100. |
| Colour | Used in the calendar. |
| Students | Enrol students here to open the lesson with its roster ready. |
| Notes | Free text. |

### 7.2 Reading conflict warnings

Before saving, the conflict engine checks four things:

1. Another lesson already occupies that **lane** at that time.
2. The **instructor** is teaching another lesson, is outside their availability pattern, or is on leave.
3. One of the selected **students** is already booked in another lesson at that hour.
4. The **pool** is closed — outside operating hours, under maintenance, or on a holiday.

Blocking conflicts are returned as errors and the lesson is not saved; the error message lists each clashing record so you can see exactly what to move. Softer issues (for instance, a time slightly outside the usual operating window) come back as warnings that do not block saving.

### 7.3 "Create anyway"

Sometimes overlap is deliberate — two coaches sharing a lane for a squad session, or a one-off arrangement agreed with the family. Ticking **Create anyway** forces the lesson past the conflict check.

Use it sparingly, and know that it is not invisible: the audit log records that the lesson was forced and how many conflicts were overridden, together with your name and the time.

---

## 8. Recurring lessons

Most of the timetable repeats weekly, so build it as a series rather than one lesson at a time.

Open **Operations → Lessons → New Series** and set:

| Field | Notes |
|-------|-------|
| Title, lesson type, group | As for a single lesson. |
| Pool, lane, instructor | Applied to every lesson in the series. |
| Weekdays | One or more, from Monday (0) to Sunday (6). Pick every day the class meets. |
| Start time / End time | End must be later than start. |
| Start date / End date | The span of the series. Maximum 400 days. |
| Capacity | 1–100. |
| Students | Enrolled into every generated lesson. |
| Skip holidays | On by default — no lessons are generated on days marked as holidays. |
| Create anyway | Forces generation past conflicts, exactly as for a single lesson. |

The system generates one lesson for every matching weekday in the range and runs the conflict check across the whole set, so a single clash in week six is reported before anything is written.

Deleting a series removes its future lessons. Lessons that already happened — and their attendance — are preserved, so historical reports stay correct.

---

## 9. The calendar

**Operations → Calendar** shows every lesson in the selected range, colour-coded by lesson type or group.

**Views.** Day, week and month. Day view is the practical one for reception; week view is best for planning; month view is for spotting gaps and overloaded periods.

**Filters.** Narrow by pool, instructor, group and lesson type. Filters persist as you move between dates, so you can follow one instructor through a whole month without re-selecting.

**Lesson details.** Clicking a lesson opens a panel with the enrolled students, lane, instructor and status, plus a direct link to the attendance screen.

**Drag and drop.** Drag a lesson to a new time slot to move it. The move runs through the same conflict check as creation: if the new slot clashes you get the list of conflicts and the option to force. You can also move a lesson by editing its time, lane or instructor.

**Cancelled lessons.** Cancelling asks for a reason. The lesson stays on the calendar in a distinct colour rather than disappearing, because deleting it would silently change last month's attendance statistics.

---

## 10. Lane planning

**Operations → Lanes** opens the lane plan: an hour-by-lane grid for one pool on one day. Each cell shows the lesson occupying that lane in that hour with its instructor and enrolled count; empty cells are free capacity.

Three things this screen is good for:

- **Finding a free lane.** The free-lane query answers "which lanes are available between 17:00 and 18:00 next Tuesday?" directly, instead of making you read the calendar and infer it.
- **Slot suggestions.** Ask the system for suitable time slots for a lesson of a given length and it returns conflict-free options within the pool's operating hours.
- **Seeing waste.** A grid with holes at peak hours is money left on the table; a solid block at 17:00 with nothing at 14:00 tells you where to steer new enrolments.

---

## 11. Taking attendance

### 11.1 Manual attendance

Open **Operations → Attendance**, pick the lesson, and the enrolled students are listed with their photos and student numbers.

The six status codes are:

| Status | When to use it |
|--------|----------------|
| Present | Attended normally. |
| Absent | Did not attend, no valid excuse. |
| Late | Attended but arrived late — enter the number of minutes. |
| Excused | Did not attend with a valid reason — enter the reason. |
| Cancelled | The lesson did not run for this student. |
| Make-up | This attendance is a make-up for a previously missed lesson. |

### 11.2 Bulk marking

Use **Mark all present** to set the whole roster at once, then correct the handful of exceptions. For a twenty-student squad this turns a minute of clicking into five seconds.

### 11.3 Credit consumption

The **Consume credits** switch controls whether saving attendance deducts a lesson from the student's active membership.

- **On (normal use):** each student marked *Present* or *Late* has one credit deducted from their active membership. When a membership reaches zero remaining credits its status changes to *Expired* automatically.
- **Off:** attendance is recorded but no entitlement is spent. Use this for free trial sessions, make-up lessons already paid for, or a class the school is running as a gift.

Double deduction is prevented: each enrolment carries a `credit consumed` flag, so re-saving or correcting an attendance record never charges the student twice.

### 11.4 QR check-in

For busy entrances, generate a QR code for the lesson and let students scan themselves in.

1. On the attendance screen choose **Generate QR** for the lesson. The token is valid for 90 minutes by default; you can shorten or extend it.
2. Display the code at the entrance.
3. Each student presents their student card (issued from the student profile — it produces a card code and its own QR payload).
4. On a scan, attendance is recorded automatically with the check-in time.

Two behaviours worth knowing: a student who scans more than 10 minutes after the lesson start is recorded as **Late** with the exact number of minutes; and a second scan by the same student for the same lesson is rejected rather than duplicated.

Expired tokens are refused, so a code photographed last week cannot be reused.

### 11.5 Make-up lessons

For a student marked **Absent** or **Excused**, open the attendance record and choose **Assign make-up**, then pick the replacement lesson. The student is enrolled into that lesson if they are not already, and the make-up is linked back to the original absence so it appears in the student's history as a resolved miss rather than a second, unrelated booking.

Make-ups can only be assigned against *Absent* or *Excused* records — you cannot assign one against a lesson the student attended.

---

## 12. Memberships and packages

### 12.1 Choosing a package

Packages define what is being sold. Nine are created at installation and can be edited or extended:

| Package | Type | Lessons | Valid for |
|---------|------|--------:|----------:|
| 4 Lessons | Lesson pack | 4 | 60 days |
| 8 Lessons | Lesson pack | 8 | 90 days |
| 12 Lessons | Lesson pack | 12 | 120 days |
| Monthly Unlimited | Monthly | unlimited | 30 days |
| Quarterly | Quarterly | 36 | 90 days |
| 6 Months | Biannual | 72 | 180 days |
| Annual | Annual | 144 | 365 days |
| Private Lesson x10 | Private pack | 10 | 120 days |
| Trial Lesson | Trial | 1 | 14 days |

Each package also carries a price, a currency, a colour and a **maximum freeze days** limit (30 by default). Packages you no longer sell should be deactivated, not deleted, so existing memberships keep their reference.

### 12.2 Creating a membership

Open **Finance → Memberships → New Membership**:

1. Select the **student**.
2. Select the **package**. Credits and duration come from it.
3. Set the **start date** (defaults to today). The end date is calculated from the package duration.
4. Optionally enter a **discount amount** and the reason for it.
5. Optionally set **auto-renew**.
6. Optionally tick **Create payment** to open the collection record at the same time, choosing the amount and method. This is the usual path at reception: one action produces both the membership and the receipt.

### 12.3 Freezing

Freezing suspends a membership for an agreed period — illness, a long holiday, an injury.

Enter the freeze start and end dates and a reason. The number of frozen days is added to the membership end date, so the family loses nothing. The package's maximum freeze days limit is enforced, which prevents a membership being frozen indefinitely.

**Unfreeze** resumes the membership from where it left off.

### 12.4 Renewing

**Renew** opens a new membership continuing from the current one. You can keep the same package or move to a different one, apply a discount, and optionally generate the payment record in the same step.

Two lists make renewals systematic rather than reactive:

- **Expiring memberships** — memberships ending within the warning window (14 days by default).
- **Low credit** — students down to their last couple of lessons (2 by default).

Working these two lists weekly is the single highest-return habit in the program.

### 12.5 Cancelling

Cancelling sets the membership status to *Cancelled* and stops further credit consumption. The record and its history remain, because refunds and revenue reports depend on knowing what was sold and when.

---

## 13. Taking payments

### 13.1 Recording a collection

Open **Finance → Payments → New Payment**:

| Field | Notes |
|-------|-------|
| Student | Who the payment is for. |
| Amount | Must be greater than zero. |
| Currency | Defaults to the organisation currency. |
| Method | Cash, Card (POS), Bank transfer, Online, Other. Used as a breakdown in the end-of-day report. |
| Payment date | Defaults to today. |
| Membership / Invoice | Linking the payment updates the related balance automatically. |
| Reference | Receipt or transaction number. |
| Description | Free text. |

Every payment gets a receipt number automatically.

### 13.2 Invoices

Invoices are issued against a student and optionally a membership, with an issue date, a due date and line items. The invoice tracks its total, the amount paid and the remaining balance, and marks itself overdue once the due date passes (a grace period of 3 days is applied by default). Payments linked to an invoice update its paid amount as they arrive.

### 13.3 Refunds

Choose the payment and select **Refund**. Both an **amount** and a **reason** (at least 3 characters) are required.

The original payment is never deleted. The refund is added as a separate movement in the cash ledger, so the day's till still reconciles and the history shows what actually happened rather than a silently altered figure.

Cancelling a payment outright is a distinct, permission-gated action that also requires a reason and is written to the audit log.

### 13.4 Outstanding receivables

The **Outstanding** tab groups open balances by age:

| Bucket | Meaning |
|--------|---------|
| Current | Not yet due. |
| 1–30 days | Recently overdue — usually a reminder is enough. |
| 31–60 days | Needs a phone call. |
| 60+ days | Needs a decision, not another reminder. |

Work the list from the oldest bucket down. The same data is available as the **Outstanding Receivables** report for printing or sending to management.

### 13.5 Expenses and discounts

Expenses are recorded with a category (salary, rent, utilities, chemicals, maintenance, equipment, marketing, tax, insurance, other), an amount and a date; the monthly distribution appears as a chart on the Finance screen. Discount definitions hold a campaign name, a rate or fixed amount and validity dates, and are selectable when creating a membership.

---

## 14. Recording performance

### 14.1 Entering a time

Open **Sports → Performance → New Record**:

| Field | Required | Notes |
|-------|:--------:|-------|
| Student | Yes | |
| Stroke | Yes | Freestyle, Backstroke, Breaststroke, Butterfly, Medley. |
| Distance | Yes | 10–10,000 m. |
| Course type | Yes | Short (25 m) or Long (50 m). |
| Time | Yes | Type it as `1:35.12`. `95.12` (plain seconds) and `1.35.12` also parse correctly, and a comma is accepted instead of a decimal point. Stored internally in seconds. |
| Date | Yes | The date the time was swum. |
| Competition result | No | Tick when the time came from a meet. |

A time of `1:35.12` means one minute, thirty-five point one two seconds. Times are always displayed back in the same `M:SS.ss` form (or `SS.ss` under a minute), so what you type is what you see.

### 14.2 Splits and extra metrics

All optional, but they are what turn a stopwatch log into coaching data:

| Metric | Range | What it tells you |
|--------|-------|-------------------|
| Splits | list of seconds | Pacing across the race — a fast first 50 and a collapsing second 50 is a pacing problem, not a fitness problem. |
| Stroke rate | 0–200 | Cycles per minute. |
| Stroke count | 0–1000 | Efficiency per length; falling stroke count at the same speed is real technical progress. |
| Reaction time | 0–10 s | Start reaction off the block. |
| Turn time | 0–60 s | Where many races are actually lost. |
| Average heart rate | 30–240 | Physiological load. |
| Perceived effort | 1–10 | The athlete's own rating. |

### 14.3 Personal-best tracking

Personal bests are maintained automatically. When a new record beats the existing best for that student, stroke, distance and course type, the personal best is updated and the record is flagged.

Competition and training times are tracked separately, so a fast training swim never quietly displaces a genuine competition best.

### 14.4 Reading the progress chart

The student's performance summary shows:

- **Progression curve** — times over the season for a chosen event. Because a lower time is better, the line should trend *downwards*; the chart is drawn accordingly.
- **Personal bests** — best time per event with the date it was set.
- **Weakest stroke analysis** — where this athlete is furthest from their own standard, which is usually the highest-return place to spend coaching time.
- **Competition readiness** — an indicator combining recent form and training consistency.

The system also maintains two school-wide lists: **top improvers** and **declining athletes**. The declining list is a prompt to have a conversation, not a verdict — illness, a growth spurt and a technique change all look identical in the numbers.

---

## 15. Competition management

### 15.1 Creating a competition

Open **Sports → Competitions → New Competition** and enter the name, organiser, level (Club, Local, Regional, National, International), venue, date range and registration deadline.

### 15.2 Adding events

An event is a stroke + distance + gender/age category combination, for example "Girls 11–12, 100 m Freestyle". Add every event your athletes will enter.

### 15.3 Entering athletes

Enter athletes into events with a **seed time** — their expected performance, usually their current personal best. Entries without a seed time are treated as the slowest when heats are drawn.

### 15.4 Seeding heats

Choose **Seed heats** on an event and set the lanes per heat (6 by default). The system distributes athletes following standard swimming practice:

- The fastest seeds are placed in the **final heat**.
- Within each heat, the fastest athlete gets the **centre lane**, with the rest alternating outwards (for 6 lanes: 3, 4, 2, 5, 1, 6).

The resulting heat sheet lists every heat with its lane assignments, athlete names and formatted seed times, ready to print.

### 15.5 Results

After the meet, enter each entry's result time, rank and medal. A disqualification requires a reason — this is enforced, because "DQ" with no explanation is useless to the athlete a week later.

When a result beats the club record threshold for that event, the club record list is updated automatically. The **medal summary** gives the gold/silver/bronze distribution for a selected year with a per-athlete breakdown, and the **competition results report** produces the whole meet as a printable document.

---

## 16. Building reports

### 16.1 Choosing a report

Open **Analytics → Reports**. The catalogue lists only reports you have permission to run — sixteen in total:

| Report | Category | Filters |
|--------|----------|---------|
| Daily Manager Report | Management | date |
| Weekly Management Report | Management | period |
| Monthly Management Report | Management | period |
| Student List | Students | group, status, level |
| Student Progress Report | Students | student, period |
| Attendance Report | Operations | period, group, instructor |
| Instructor Workload Report | Staff | period |
| Pool Usage Report | Facility | period, pool |
| Lane Occupancy Report | Facility | period, pool |
| Finance Report | Finance | period |
| Collections Report | Finance | period |
| Outstanding Receivables | Finance | — |
| Membership Report | Finance | period, status |
| Sales Report | Finance | period |
| Performance Report | Sports | period, student, group |
| Competition Report | Sports | competition |

### 16.2 Filters

Set the **period** — Today, This week, This month, Last 3 months, Last 6 months, This year, Last year, or Custom range (which asks for explicit start and end dates) — then apply whichever of pool, instructor, group, student and membership-status filters the report supports.

### 16.3 Preview

**Preview** renders the report on screen with its column definitions, row count and totals before anything is generated. Always preview first: it takes a second and it catches the wrong-date-range mistake that otherwise produces a 400-page PDF.

### 16.4 Exporting

Four formats are available:

| Format | Best for |
|--------|----------|
| **PDF** | Printing, signing, sending to a board or a parent. Charts can be included or omitted. |
| **XLSX** | Further analysis in Excel. |
| **CSV** | Importing into another system. |
| **JSON** | Feeding another tool or script. |

You can also pick the **report language** independently of your interface language — keep working in English and hand a Turkish PDF to a parent, or the reverse. PDF output uses a Turkish-character-capable font where one is available on the machine.

### 16.5 Saved templates

A filter set you use regularly can be saved as a **template** with a name and recalled with one click next time. Templates can be kept private or shared with colleagues. You can delete templates you own.

---

## 17. Notifications

The bell in the top bar shows unread notifications and refreshes every minute. **System → Notifications** opens the full list, filterable to unread only, where you can mark items read individually or all at once.

The system generates notifications for:

| Type | Trigger |
|------|---------|
| Membership expiring | Membership end date is within the warning window (14 days by default). |
| Payment overdue | An invoice passes its due date plus the grace period. |
| Lesson cancelled | A lesson is cancelled. |
| Instructor leave | Leave is recorded that affects scheduled lessons. |
| Pool maintenance | Maintenance is scheduled or a pool is closed. |
| Performance drop | An athlete's times deteriorate consistently. |
| Competition upcoming | A competition approaches its date or registration deadline. |
| AI report ready | An AI analysis you requested has finished. |
| Backup result | A scheduled backup succeeded or failed. |
| Trial lesson | A trial lesson is booked. |
| New registration | A new student is registered. |
| System | General system messages. |

Each notification carries a severity — info, success, warning or error — and most link straight to the relevant record.

Notifications addressed to you personally and school-wide announcements both appear in your list. Users with `notification:send` can send a message to specific users or to everyone.

---

## 18. Changing language and theme

**Language.** Click the language button in the top bar and choose Turkish or English. The change is instant and applies to interface text, error messages from the server, and the formatting of dates, times, numbers and currency. In Turkish, numbers appear as `1.250,50` and dates as `15.08.2026`; in English, `1,250.50`. Report exports have their own language selector, so the interface language and the report language are independent.

**Theme.** The sun/moon button switches between light and dark.

Both preferences are stored on your account, not in the browser, so signing in from another machine gives you the same setup. The date format itself (`DD.MM.YYYY` by default) is an organisation-wide setting your administrator controls.

---

## 19. Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| <kbd>Ctrl</kbd>+<kbd>K</kbd> (or <kbd>⌘</kbd>+<kbd>K</kbd>) | Open the command palette |
| <kbd>/</kbd> | Focus global search (when not already typing in a field) |
| <kbd>↑</kbd> / <kbd>↓</kbd> | Move through palette or search results |
| <kbd>Enter</kbd> | Run the highlighted command / open the highlighted result |
| <kbd>Esc</kbd> | Close the palette, the search box, or the open dialog |

Inside the command palette the footer always shows these three keys, so you never have to remember them.

---

## 20. Frequently asked questions

**1. I created a student but cannot find them in the list. Where did they go?**
Almost always a filter. The list keeps your last status, level, group, instructor and age filters. Click **Clear filters** and search by name or student number again.

**2. The system will not let me save a lesson and shows a conflict list. What should I do?**
Read the list — it names each clashing record. Usually the lane or the instructor is already booked. Change the time, lane or instructor and save again. Only if the overlap is genuinely intended should you tick **Create anyway**, and remember that the override is recorded in the audit log with your name.

**3. A student attended but no credit was deducted. Why?**
Either the **Consume credits** switch was off when attendance was saved, or the student has no *Active* membership, or the credit for that enrolment had already been consumed (the flag prevents a second deduction). Check the student's Membership tab.

**4. I marked the wrong student present. Can I fix it?**
Yes. Open the attendance record and correct the status. Correcting an existing record does not deduct another credit. The correction is written to the audit log.

**5. How do I record a lesson for someone who missed a session?**
Find the original attendance record (it must be *Absent* or *Excused*), choose **Assign make-up**, and pick the replacement lesson. The student is enrolled in that lesson and the make-up is linked to the original miss.

**6. A family paid but the balance still shows as owed.**
The payment was probably not linked to the membership or invoice. Open the payment and set the membership or invoice link; balances update automatically once linked.

**7. A parent wants a refund. Should I delete the payment?**
No. Use **Refund** with the amount and a reason. The original payment stays and the refund appears as its own movement, so the till reconciles and the history is honest. Deleting payments breaks the cash ledger.

**8. Why can I see the Students screen but not the Finance screen?**
Menu entries are shown based on your roles' permissions. Finance screens need `finance:read`. If you need access, ask your administrator to add the appropriate role — do not share another person's account.

**9. Some fields on a student profile show as hidden.**
Health notes and special needs are protected by the separate `student:read_sensitive` permission. Instructors who need them (adaptive swimming, medical staff, head coach) have it; general reception roles do not.

**10. How do I enter a time of one minute thirty-five point one two seconds?**
Type `1:35.12`. The formats `95.12` (plain seconds), `1.35.12` and `95,12` are all accepted too and normalise to the same value.

**11. The QR code from yesterday will not scan.**
QR tokens expire — 90 minutes by default from generation. Generate a new one for today's lesson. Tokens are also lesson-specific, so a code for one class cannot check students into another.

**12. Why did the membership status change to Expired by itself?**
Either the end date passed, or the last credit was consumed by an attendance record. Both are automatic. Use **Renew** to continue, choosing the same or a different package.

**13. A cancelled lesson is still on the calendar. Can I remove it?**
Cancelled lessons remain visible in a distinct colour on purpose. Deleting them would change the attendance and occupancy figures already reported for that period. If it was created entirely in error, delete it — but a lesson that genuinely was cancelled should stay as cancelled.

**14. Can I get a report in Turkish while using the English interface?**
Yes. The export dialog has its own language selector, independent of the interface language.

**15. Two guardians for the same family — do I create the student twice?**
No. Create the student once and link both guardians to it. Each link has its own primary / can-pick-up / billing-contact flags.

**16. How do I know which lessons still need attendance today?**
The dashboard's "Today's schedule" table badges every lesson whose attendance is recorded; the unbadged ones are outstanding. The attendance alert card at the top gives the count and links straight to the list.

---

## 21. Troubleshooting

### A screen is empty

Clear the filters and refresh. A date range or status filter narrows results far more often than data actually goes missing. Every list has a **Clear filters** link for exactly this.

### "Your session has expired"

Sign in again. Sessions close after a period of inactivity for security. Work already saved is unaffected.

### "Permission denied" / a menu entry is missing

Your account does not hold the permission that screen requires. Menu items are hidden rather than shown-and-blocked, and typing the address manually returns an access-denied screen. Contact your administrator with the name of the screen you need.

### A lesson will not save

The conflict check is blocking it. Read the listed conflicts — lane, instructor, student or pool availability — and adjust. Use **Create anyway** only when the overlap is deliberate.

### The program will not start

- If the launcher reports that Python was not found, install Python 3.11 or newer with "Add Python to PATH" ticked, then run `START_SWIMMING_SCHOOL.bat` again.
- If the window opens but shows only API documentation, the interface has not been built. Run `BUILD_FRONTEND.bat` once (it needs Node.js 18 or newer), then start the program again.
- If the window closes unexpectedly, open `logs\application.log` — the last lines state the reason.

### AI analyses return an error

Open the AI Center and run the provider health check. The error message states the cause plainly: no model loaded in the local service, an invalid cloud key, or a timeout. Note that AI being unavailable never blocks the rest of the program — statistics, reports and every operational screen are computed from the database and keep working. In AI analysis screens the computed-data panel still appears; only the interpretation panel is replaced by a warning.

### Something looks wrong and you need help

Collect two things before asking:

1. The status shown on the **System health** screen (Settings → About / System health).
2. The last few entries in the **Audit log** relating to the record in question — who changed what and when.

Those two together are enough for an administrator to diagnose nearly any issue without guesswork.

---

## Where to go next

| Document | Contents |
|----------|----------|
| [ADMIN_GUIDE_EN.md](ADMIN_GUIDE_EN.md) | Installation, users and roles, organisation settings, KPIs, audit log, maintenance and updates. |
| [BACKUP_RESTORE_EN.md](BACKUP_RESTORE_EN.md) | Backup and restore procedures in detail. |
| [CHANGELOG.md](../CHANGELOG.md) | What changed in each release. |
| In-program **Training Center** | Twelve interactive tutorials with links to live screens. |
| In-program **User Guide** | A searchable version of this guide, in both languages. |
