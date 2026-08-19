# Statistics and Reporting Guide

This document explains **how every number** in the Statistics Center is calculated and
how to read it correctly. Its purpose is to let you look at a percentage on screen and
answer precisely: "what exactly does this measure?"

> Version: 0.9.0 · Source: `backend/app/services/statistics_engine.py`,
> `backend/app/services/reporting.py`, `backend/app/api/v1/statistics.py`
> User interface: the **Statistics** and **Reports** screens

---

## 1. Statistics Center Overview

**Every number in the Statistics Center is computed directly from database records.**
There is no AI prediction, no model output and no "approximate value".

```
Database  →  Statistics Engine  →  The number on screen
  (SQL)        (pure functions)        (chart / table)
```

The engine is built on three rules:

1. **Pure functions.** Every helper — `mean`, `median`, `std_dev`, `percentile`,
   `moving_average`, `linear_slope`, `pearson_correlation`, `detect_outliers` — is a
   separate, testable function. A portion of the 395 backend test functions verifies these
   functions directly.
2. **AI is a separate layer.** There is no AI call anywhere in
   `statistics_engine.py`. The AI layer (`services/ai/analysis.py`) consumes this
   engine's **output as its input**; it never produces the numbers, only interprets
   them. See `docs/AI_GUIDE_EN.md`.
3. **Reproducibility.** Given the same period and the same data, the engine always
   returns the same result.

### 1.1 Screen tabs

| Tab | Content | Endpoint |
|---|---|---|
| Students | Registrations, retention, churn, distributions | `GET /api/v1/statistics/students` |
| Instructors | Lesson load, hours, occupancy, cancellations | `GET /api/v1/statistics/instructors` |
| Pools | Occupancy, hourly/daily load, heatmap | `GET /api/v1/statistics/pools` |
| Attendance | Present, absent, late, excused rates | `GET /api/v1/statistics/attendance` |
| KPI | 11 indicators, targets and achievement | `GET /api/v1/statistics/kpi` |
| Advanced | Cohort, correlation, distribution, outliers | `/cohort`, `/correlation/...`, `/distribution/{metric}`, `/outliers/attendance` |

Every statistics endpoint requires the `statistics:read` permission. Setting a KPI
target additionally requires `kpi:write`.

### 1.2 Main dashboard

`GET /api/v1/statistics/dashboard` produces the daily operational counters in a
single call: active students, today's lessons, completed lessons, lanes in use,
collected today, due today, overdue amount, monthly income/expense, today's
attendance rate, lessons still missing attendance, expiring memberships, upcoming
trial lessons, number of declining athletes and upcoming competitions. It also
returns a 30-day revenue trend and an attendance trend.

The dashboard also raises **alert cards**: overdue payments, expiring memberships,
missing attendance, performance decline, upcoming competitions.

---

## 2. Period Selection and Comparison

Every statistics screen has a period selector at the top. The selection is turned
into a concrete `(start, end)` date pair by `resolve_period()`.

### 2.1 The eight period options

| Key | Label | Range covered |
|---|---|---|
| `today` | Today | Today → today |
| `week` | This week | Monday → Sunday of the current week (a full 7 days, including the future) |
| `month` | This month | First day of the month → **today** (the rest of the month is not included) |
| `quarter` | This quarter | First day of the quarter's first month → **today** |
| `half_year` | Last 6 months | 182 days before today → today |
| `year` | This year | 1 January → **today** |
| `last_year` | Last year | 1 January → 31 December of the previous year (a full year) |
| `custom` | Custom | Your `date_from` → `date_to` |

> **Careful:** `month`, `quarter` and `year` measure the range **up to today**, not
> the whole month/quarter/year. On the 3rd of a month, "This month" shows only three
> days of data. Use `custom` for a full-month comparison.

### 2.2 Comparison with the previous period

`previous_period(start, end)` builds a period of **exactly the same length that ends
immediately before** the selected one:

```
span       = (end - start).days + 1
prev_end   = start - 1 day
prev_start = prev_end - (span - 1) days
```

Example: with 1–18 August selected (18 days), the previous period is 14–31 July
(18 days). It is not "last month" but "the preceding window of equal length" — equal
lengths make the ratios fairly comparable.

### 2.3 Percentage change

```
change_percent = (current - previous) / |previous| × 100
```

If the previous period is **0** or has no data, the change is not computed and
returns **null** — there is no division by zero and no misleading "+∞%".

Every comparison metric carries a `direction` field:

* `up_good` — an increase is good (new registrations, revenue, attendance rate)
* `down_good` — a decrease is good (lost students, outstanding payments)

The green/red colour in the interface follows this field; **not every increase is
green.**

---

## 3. Student Statistics

`GET /api/v1/statistics/students?period=month&group_id=3`

Student statistics are computed for the selected group (or the whole school).

### 3.1 Counters

| Metric | Definition and calculation |
|---|---|
| **Total students** | All student records in scope (any status, including those who left) |
| **Active students** | Records with `status = active` |
| **Passive students** | `status = passive` |
| **Trial students** | `status = trial` |
| **New registrations** | Students whose `registration_date` falls inside the selected period |
| **Lost students** | Students whose `left_date` is set **and** falls inside the selected period |

### 3.2 Retention rate

First the student base present at the start of the period is determined:

```
active_at_start = registration_date < start
                  AND (no left_date OR left_date >= start)
```

Then:

```
retention_rate = (active_at_start − lost) / active_at_start × 100
```

**The denominator is the base at the start of the period; students who registered
during the period are not counted in it.** This is deliberate: a student who joins
and leaves in the same month should not mechanically distort retention.

If `active_at_start = 0` (a newly opened school, a very short period), retention is
reported as **100.0%**. That does not mean "perfect performance" — it means **there
was nothing to measure**.

### 3.3 Churn rate

```
churn = 100 − retention_rate
```

It is the exact complement of retention, not a separate data source.

### 3.4 Growth rate

```
growth_rate = (new_registrations − lost) / active_at_start × 100
```

Net change relative to the base at the start of the period. A negative value means
shrinkage. If `active_at_start = 0`, growth returns **0.0**.

### 3.5 Average membership duration

```
per student: duration = (left_date ?? today) − registration_date   [days]
average_membership_days = mean(all durations)
```

Three things matter here:

* For students who have not left, **the time elapsed up to today** is used, so
  ongoing memberships push this average up a little every day.
* The calculation is **not limited to the selected period** — it spans the whole
  history of every student in scope. The period filter does not change this metric.
* Students who left are included, which makes the metric close to "average customer
  lifetime".

### 3.6 Attendance rate (on the Students tab)

```
attendance_rate = (present + late + makeup) / all_attendance_records × 100
```

`PRESENT_STATUSES` = `present`, `late`, `makeup`. So **a late student counts as
present**, and so does a student attending a make-up lesson.

The denominator is the number of **attendance rows** filtered by the lesson start
time within the period. That is a count of records, not of students: a student
attending three lessons a week contributes three times.

> This metric is **not affected by the group filter**; the attendance rate on the
> Students tab is always computed school-wide. Use the **Attendance** tab for
> group-level attendance.

### 3.7 Distributions

| Distribution | Breakdown |
|---|---|
| Age | `0-5`, `6-9`, `10-13`, `14-17`, `18-29`, `30-49`, `50+` (students without a birth date are excluded) |
| Level | By the `swim_level` field |
| Group | Students per group (empty groups are not listed) |
| Gender | By the `gender` field |

Every distribution row carries `value` (count) and `percent` (share of the total) and
is sorted from the largest count downwards.

### 3.8 Registration trend

Starting from the first month of the period, one point is produced per month with the
number of students registered in that month (`2026-06`, `2026-07`, `2026-08`). Short
periods may yield a single point; pick at least `quarter` to read a trend.

---

## 4. Instructor Statistics

`GET /api/v1/statistics/instructors?period=month`

Only instructors with `is_active = true` are listed. Rows are sorted by **total
hours**, descending.

| Metric | Calculation |
|---|---|
| **Student count** | Students whose `primary_instructor_id` is this instructor. **Independent of the period** — it shows the current assignment |
| **Lesson count** | Lessons starting in the period with `status ≠ cancelled` |
| **Total hours** | Sum of `duration_minutes` for non-cancelled lessons ÷ 60 |
| **Occupancy rate** | `Σ enrolled / Σ capacity × 100` (non-cancelled lessons only) |
| **Attendance rate** | `(present+late+makeup) / all_attendance × 100` across this instructor's lessons |
| **Cancellation rate** | `cancelled_lessons / all_lessons_in_period × 100` (the denominator **includes** cancellations) |
| **Private lesson count** | Non-cancelled lessons with `lesson_type = private` |
| **Group lesson count** | Non-cancelled lessons − private lessons |
| **Private ratio** | `private / non_cancelled_lessons × 100` |

Summary rows: total hours, average students per instructor, average occupancy.

### 4.1 DECISION-SUPPORT WARNING

**This table is not a staff appraisal tool.** It produces workload and operational
indicators. When making personnel decisions, keep the following in mind:

* **Occupancy is not under the instructor's control.** Capacity and enrolment are
  decided by whoever builds the schedule. Low occupancy usually means the lesson
  slot was chosen badly.
* **Attendance is decided by students.** Illness-driven absence is structurally
  higher in baby and toddler groups than in adult groups. Comparing instructors who
  work with different age groups through this metric is misleading.
* **The cancellation denominator includes cancellations.** An instructor with 4
  lessons of which 1 was cancelled reads 25%, and so does one with 40 lessons of
  which 4 were cancelled — but they are not the same thing. Always read the **lesson
  count** column next to it.
* **The reason for cancellation is not in this table.** Pool maintenance, holidays
  and water-quality closures land in the same number as an instructor not showing up.
  Read the reason on the **Lessons** screen.
* **Small-sample fallacy.** The ratios of an instructor who taught 3 lessons in the
  period are statistically meaningless. Do not compare ratios below roughly 15–20
  lessons.
* **Student count is not period-based.** An instructor who taught nothing this month
  still shows a full "student count".

Correct use: spotting workload imbalance, seeing who is free while scheduling, and
computing capacity when planning a season.

---

## 5. Pool and Lane Statistics

`GET /api/v1/statistics/pools?period=month&pool_id=1`

### 5.1 The occupancy calculation

Occupancy is computed **in minutes**:

```
USED MINUTES
  = Σ (duration of non-cancelled lessons assigned to a lane)

CAPACITY MINUTES
  = Σ_pool [ (closing_time − opening_time) in minutes
             × number_of_active_lanes
             × number_of_days_in_period ]

overall_occupancy   = used / capacity × 100
free_capacity_hours = max(0, capacity − used) / 60
```

This formula has three consequences, and all three must be read consciously:

1. **Lessons without a lane do not enter the numerator.** A lesson with an empty
   `lane_id` appears in the pool usage distribution but is not added to the occupancy
   numerator. If occupancy looks lower than expected, check the lane assignments first.
2. **The denominator counts every day.** Sundays when the pool is closed, public
   holidays and maintenance days are all included in capacity. This makes **100%
   occupancy practically impossible.**
3. **A pool with no active lanes counts as 1 lane** (to avoid dividing by zero).

A practical reference: for a pool open 6 days a week, 8 hours a day, the real ceiling
is around 70–75%. **45–55% is healthy, above 65% is very busy, below 25% signals
serious idle capacity.** Measure and note the realistic band of your own facility
during the first season.

### 5.2 Load distributions

| Chart | Content |
|---|---|
| **Pool usage** | Total lesson minutes and percentage share per pool |
| **Lane usage** | Total minutes per `Pool name - Lane name` |
| **Hourly load** | Total lesson minutes per hour between 06:00 and 23:00 |
| **Daily load** | Total lesson minutes for the 7 weekdays |
| **Weekly load** | Total minutes per ISO week (`2026-W33`) |

Derived values: **busiest hour** (maximum hourly load), **quietest hour** (minimum —
among hours that actually have lessons; an hour with no lesson at all does not enter
this list), **most used lane**, and **average lanes per lesson** (lessons assigned to
a lane ÷ total lessons).

### 5.3 How to read the heatmap

The heatmap consists of `(weekday, hour)` cells. Each cell carries two pieces of
information:

* `value` — total lesson **minutes** in that cell
* `lesson_count` — the **number of lessons** in that cell

Read it in this order:

1. **Find the dark bands.** These are the facility's real demand peaks — typically
   weekdays 17:00–20:00 and Saturday morning.
2. **Mark the light cells.** Hours when the pool is open but no lesson runs are
   sellable idle capacity. The weekday 10:00–15:00 band is typically empty and can be
   targeted at retirees, homemakers or corporate group programmes.
3. **Compare `value` with `lesson_count`.** High minutes + low lesson count = a few
   long sessions (a training squad). Low minutes + high lesson count = short private
   lessons.
4. **Do not confuse an empty cell with a closed hour.** The map only produces cells
   that have lessons, so a closed hour also looks empty. Confirm the pool's working
   hours on the **Pools** screen.

---

## 6. Attendance Statistics

`GET /api/v1/statistics/attendance?period=month&group_id=3`

Attendance rows enter a period based on the start time of the lesson they belong to.
Group and instructor filters can be applied.

### 6.1 Rate definitions

The denominator of every rate is the **total number of attendance records in the
period**.

| Rate | Formula | Note |
|---|---|---|
| **Overall attendance rate** | `(present + late + makeup) / total × 100` | Late students and make-up attendees count as **present** |
| **No-show rate** | `absent / total × 100` | Only `absent`; excused absence does not go here |
| **Late rate** | `late / total × 100` | These records are also in the numerator of the attendance rate |
| **Excuse rate** | `excused / total × 100` | **Not** in the attendance-rate numerator — an excused absence lowers the attendance rate |
| **Make-up rate** | `makeup / total × 100` | In the attendance-rate numerator |

Raw counters are returned as well: `present`, `absent`, `late`, `excused`,
`cancelled`, `makeup`.

> `overall + no-show + excuse` may not add up to 100% — records with the `cancelled`
> status sit in the denominator but enter no rate.

### 6.2 Breakdowns

* **By group** and **by instructor** attendance rate: `present / total × 100` for each
  label, sorted from the highest rate downwards.
* **Lowest-attendance students:** students with **at least 3 attendance records** in
  the period whose rate is **below 75%**; sorted ascending, top 20 rows. The 3-record
  threshold prevents a single absence from putting someone on the list.
* **Trend:** the attendance rate of each day (labelled `%d.%m`).

---

## 7. Performance Analysis

`analyze_event()` analyses all of an athlete's times for **one single event**
(stroke + distance + course type) in chronological order.

`GET /api/v1/performance/students/{id}/summary` produces this analysis separately for
every event.

### 7.1 Statistics computed

| Statistic | Method | Note |
|---|---|---|
| **Best time** | `min(times)` | In swimming the smallest time is the best |
| **Worst time** | `max(times)` | |
| **Mean** | `numpy.mean`, 3 decimals | A single slow outlier pulls the mean up |
| **Median** | `numpy.median` | Robust against outliers; a large gap from the mean means the distribution is skewed |
| **Standard deviation** | `numpy.std(ddof=1)` — sample deviation | Needs **at least 2 records**, otherwise returns null. A low value means a consistent athlete |
| **25th percentile** | `numpy.percentile(25)` | The boundary of the fastest 25% of times |
| **75th percentile** | `numpy.percentile(75)` | The boundary of the slowest 25% |
| **Moving average** | 3-point window, `min_periods=1` | The window expands for the first points; removes noise from the chart |
| **Slope** | `numpy.polyfit(x, y, 1)` least squares | Unit is **seconds / day**. `x` = days elapsed since the first record |

The slope needs at least 2 records on at least 2 different dates; records taken on the
same day count as a single point and the slope returns null.

### 7.2 How trend direction is decided

```python
def trend_direction(slope, lower_is_better=False):
    if slope is None or abs(slope) < 1e-6:
        return "stable"
    improving = slope < 0 if lower_is_better else slope > 0
    return "improving" if improving else "declining"
```

**Swim times use `lower_is_better=True`.** That is:

| Slope | Meaning | Label |
|---|---|---|
| Negative (time going down) | The athlete is getting **faster** | `improving` |
| Positive (time going up) | The athlete is getting **slower** | `declining` |
| \|slope\| < 0.000001 | No meaningful change | `stable` |

Metrics such as attendance rate, revenue and registration counts use
`lower_is_better=False`, which flips the sign: an increase becomes `improving`.

### 7.3 The improvement percentage formula

```
improvement_seconds = first_time − last_time         (positive = got faster)
improvement_percent = improvement_seconds / first_time × 100
```

Example: first record 35.20 s, last record 33.10 s →
`improvement = 2.10 s`, `improvement_percent = 2.10 / 35.20 × 100 = 5.97%`.

> This formula uses **only the first and last record**; it does not see the
> fluctuation in between. If the first record was a bad day, the improvement is
> exaggerated. Read the **slope** and the **moving average** chart alongside it for
> the real trend.

### 7.4 Short- and mid-term change

```
change_30d = mean(last 30 days) − mean(records older than 90 days)
change_90d = mean(last 90 days) − mean(records older than 90 days)
```

Computed only if both sides have data, otherwise null. **A negative value is good**
(the recent window is faster). `change_30d` is a form indicator, `change_90d` a
season indicator.

### 7.5 Top improvers and declining athletes

**Top improvers** (`find_top_improvers`, 90 days by default, at least 3 records):
grouped by the `(student, stroke, distance)` triple; those with `first − last > 0` are
sorted by improvement percentage.

**Declining athletes** (`find_declining_athletes`, 90 days by default, at least 4
records):

```
split           = max(1, record_count × 2 // 3)
baseline_mean   = mean(first 2/3 of records)
recent_mean     = mean(last 1/3 of records)
decline         = recent_mean − baseline_mean         (positive = got slower)
decline_percent = decline / baseline_mean × 100
```

Only rows with `decline > 0` **and** `decline_percent ≥ 1.0%` are listed. The 1%
threshold filters out ordinary day-to-day fluctuation (noise).

---

## 8. Competition Readiness Score

`competition_readiness()` — last **60 days**, at least **3 records** per event.

### 8.1 Components and weights

```
readiness_score = consistency × 0.25
                + form        × 0.35
                + trend       × 0.25
                + volume      × 0.15
```

| Component | Weight | Formula | What it measures |
|---|---|---|---|
| **Consistency** | **25%** | `max(0, 100 − (σ / recent_mean × 100) × 10)` | How settled the times are. σ = standard deviation. Every 1% of variability costs 10 points — a deliberately harsh penalty |
| **Form** | **35%** | `max(0, 100 − (recent_mean − best) / best × 100 × 5)` | Closeness to the athlete's **own best**. Being 1% above the personal best costs 5 points |
| **Trend** | **25%** | `clamp(50 − slope × 500, 0, 100)` | Direction of development. A negative slope (getting faster) lifts the score above 50; a positive slope pulls it down |
| **Volume** | **15%** | `min(100, record_count / 12 × 100)` | Training density. Saturates at 12 records |

Defaults: if the standard deviation cannot be computed, consistency is **100**; if
there is no best time, form is **50**; if the slope cannot be computed, trend is **50**.

Results are sorted by score, descending. Every row also carries a `readiness_basis`
field:

> `consistency 25% + closeness to form 35% + improvement trend 25% + training volume 15%
> (statistical, not AI)`

### 8.2 This score is STATISTICAL, not an AI prediction

The emphasis is written into the source code itself. The score:

* Is produced **only from the athlete's own past times**. Four formulas, four fixed
  weights. The same data always yields the same result.
* **Calls no language model.** It works exactly the same with every AI provider
  disabled.
* **Does not predict the race result.** Competitors' times, course type differences,
  warm-up quality, sleep, stress, illness, age group — none of them are in the model.
* **Is a relative, not an absolute tool.** "Is 80 good?" has no universal answer. Use
  it to rank athletes against each other within the same event, and to track one
  athlete's score across weeks.

Interpretation examples: high form + low consistency = fast but unsettled; work on
technical stability. High consistency + low form = regular but far from the personal
best; work on tapering/speed. Low volume = the score is not reliable yet, collect
enough records first.

---

## 9. Advanced Analyses

The **Statistics → Advanced** tab.

### 9.1 Cohort retention analysis

`GET /api/v1/statistics/cohort?months=12`

Students are grouped by their **registration month** (cohort). For each cohort, the
percentage of members still active in each subsequent month is computed:

```
month_N_retention = (members not left, or still registered at month N) / cohort_size × 100
```

The output is a triangular table: rows are cohort months (`2026-01`, `2026-02`, ...),
columns are the month index after registration. Month 0 is always 100%.

What to look for: **in which month is the drop steepest?** Months 2 and 3 are usually
the critical threshold. Another typical finding is that cohorts recruited during a
promotion erode faster than those from normal months.

Caveat: in a cohort of 5–10 people, a single departure shows as a 10–20% drop. Always
read the cohort-size column alongside.

### 9.2 Correlation — CAUSATION WARNING

`GET /api/v1/statistics/correlation/attendance-performance?days=180`

The Pearson correlation coefficient between **attendance rate** and **performance
improvement percentage** is computed per student. To enter the analysis a student must
have **at least 5 attendance records and at least 3 performance records** in the
period.

Coefficient interpretation table:

| \|r\| | Label |
|---|---|
| ≥ 0.80 | `very_strong` |
| ≥ 0.60 | `strong` |
| ≥ 0.40 | `moderate` |
| ≥ 0.20 | `weak` |
| < 0.20 | `negligible` |

At least 3 data pairs and variation in both variables are required; otherwise the
result is **null** (no fabricated value is produced).

> ### CORRELATION IS NOT CAUSATION
>
> This warning appears in the source code, both in the function docstring and in the
> endpoint description. Seeing `r = 0.7` does **not** mean "attending lessons improves
> performance". At least three alternative explanations are always on the table:
>
> 1. **Reverse direction:** an improving athlete gets motivated and shows up more
>    regularly. Cause and effect may be swapped.
> 2. **A third variable:** family support, health, financial situation, ease of
>    transport — these affect attendance and improvement at the same time. There may
>    be no direct link between the two.
> 3. **Selection bias:** only students with ≥5 attendance and ≥3 performance records
>    enter the analysis. Those who quit after a month are already outside the sample,
>    and that alone inflates the correlation.
>
> A causal claim requires a controlled comparison: for example, following two groups
> of similar age, level and baseline time under different attendance patterns.

### 9.3 Distribution analysis

`GET /api/v1/statistics/distribution/{metric}?days=180`

Supported metrics: `student_age`, `attendance_rate`, `lesson_occupancy`.

Output: `count`, `mean`, `median`, `std_dev`, `min_value`, `max_value`,
`percentile_25`, `percentile_75`, `percentile_90` and a **10-bin histogram**
(`numpy.histogram`, each bin with count and percentage).

Reading tip: **the gap between the mean and the median reveals skew.** If the mean is
noticeably above the median, a few large values are pulling the distribution to the
right; in that case the "average" does not represent the typical student — use the
median instead.

The `attendance_rate` metric requires at least 3 attendance records per student, and
`lesson_occupancy` requires lessons with a defined capacity.

### 9.4 Outlier detection

`GET /api/v1/statistics/outliers/attendance?period=month`

Finds students who are statistically unusual in attendance rate:

```
z = (student_rate − mean) / standard_deviation
|z| ≥ 2.0  →  outlier
```

Conditions: the student must have **at least 4 attendance records** in the period;
**at least 4 students** must qualify; the standard deviation must not be zero (if
everyone has the same rate there are no outliers).

Each row carries a `direction` field: `below` (under the mean — the student who needs
attention) or `above` (over the mean — the exemplary student).

> The z-score measures unusualness **relative to the mean**, not "bad". In a school
> with generally high attendance, even a student at 85% may come out as a `below`
> outlier.

---

## 10. The KPI System

`GET /api/v1/statistics/kpi?period=month` — all 11 indicators in one call.

### 10.1 Definition of the 11 KPIs

| Key | Label | Unit | Direction | Calculation |
|---|---|---|---|---|
| `active_students` | Active Students | count | up good | Number of students with `status = active` |
| `new_students_monthly` | Monthly New Students | count | up good | Students registered in the period (compared with the previous period) |
| `student_retention` | Student Retention | % | up good | The retention rate from §3.2 |
| `attendance_rate` | Attendance Rate | % | up good | The overall attendance rate from §6.1 |
| `pool_occupancy` | Pool Occupancy | % | up good | The overall occupancy from §5.1 |
| `lane_occupancy` | Lane Occupancy | % | up good | The same calculation — in this release it returns **the same value** as `pool_occupancy` |
| `monthly_revenue` | Monthly Revenue | currency | up good | `Σ (payment − refund)`, excluding cancelled payments (compared with the previous period) |
| `revenue_per_student` | Revenue per Student | currency | up good | `period_revenue / active_students` (0 if there are no active students) |
| `outstanding_payments` | Outstanding Payments | currency | **down good** | `Σ (invoice_total − paid)` across all time — independent of the period |
| `collection_rate` | Collection Rate | % | up good | `Σ paid / Σ invoiced × 100` (invoices issued in the period; 100% if there are none) |
| `average_performance_improvement` | Avg. Performance Improvement | % | up good | Looking back over the period plus 30 days, the mean improvement percentage of improving athletes with at least 2 records |

### 10.2 Setting a target

Press **Set Target** on an indicator in the **Statistics → KPI** tab.

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/statistics/kpi/targets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "kpi_key": "attendance_rate",
        "target_value": 85,
        "unit": "percent",
        "period": "monthly",
        "notes": "2026 season target"
      }'
```

Requires the `kpi:write` permission. Targets are stored in the `KpiTarget` table and
only those with `is_active = true` are taken into account.

### 10.3 Achievement calculation

Two different formulas are used depending on the direction label:

```
up good   : achievement = value / target × 100
down good : achievement = target / value × 100
```

The second formula makes the following work: with an outstanding-payments target of
10,000 and an actual value of 8,000, `10000 / 8000 = 125%` — staying below the target
counts as **success**.

Status colour:

| Achievement | Status | Colour |
|---|---|---|
| ≥ 100% | `good` | Green |
| 85% – 99.9% | `warning` | Amber |
| < 85% | `bad` | Red |
| No target defined | `neutral` | Grey |

If the target is **0** or undefined, achievement is not computed and the indicator
shows only its value.

---

## 11. Reports

The **Reports** screen. Endpoints: `GET /reports/definitions`,
`POST /reports/preview`, `POST /reports/export`,
`GET/POST/DELETE /reports/templates`.

Every report produces the same structure: **columns + rows + totals + summary**. That
is what lets one report be exported to four formats with identical content.

### 11.1 The 16 report types

| # | Key | Name | Category | Filters | Content | Permission |
|---|---|---|---|---|---|---|
| 1 | `daily_manager` | Daily Manager Report | management | date | Today's lessons, attendance and collections | `report:read` |
| 2 | `weekly_management` | Weekly Management Report | management | period | Weekly operations and finance summary | `report:read` |
| 3 | `monthly_management` | Monthly Management Report | management | period | Monthly KPIs, revenue and student movement | `report:read` |
| 4 | `student_list` | Student List | students | group, status, level | Number, name, age, level, status, group, instructor, registration date, phone | `student:read` |
| 5 | `student_progress` | Student Progress Report | students | student, period | One student's performance and attendance progress | `performance:read` |
| 6 | `attendance` | Attendance Report | operations | period, group, instructor | Attendance rates and absence analysis | `attendance:read` |
| 7 | `instructor_workload` | Instructor Workload Report | staff | period | Lessons, hours and occupancy per instructor | `instructor:read` |
| 8 | `pool_usage` | Pool Usage Report | facility | period, pool | Pool and hourly occupancy | `pool:read` |
| 9 | `lane_occupancy` | Lane Occupancy Report | facility | period, pool | Per-lane utilisation breakdown | `pool:read` |
| 10 | `finance` | Finance Report | finance | period | Income, expenses and net profit | `finance:read` |
| 11 | `collections` | Collections Report | finance | period | Collections and payment method breakdown | `finance:read` |
| 12 | `outstanding` | Outstanding Receivables | finance | — | Overdue and pending payments (aging) | `finance:read` |
| 13 | `membership` | Membership Report | sales | status | Active, expired and frozen memberships | `membership:read` |
| 14 | `sales` | Sales Report | sales | period | Package-level sales and revenue | `finance:read` |
| 15 | `performance` | Performance Report | sports | period, student | Athlete times and improvement | `performance:read` |
| 16 | `competition` | Competition Report | sports | period | Competition results and medals | `competition:read` |

The report catalogue (`GET /reports/definitions`) returns **only the reports your
permissions allow you to run**.

### 11.2 Export formats

| Format | File | MIME | Characteristics |
|---|---|---|---|
| `pdf` | `<report>_YYYYMMDD_HHMM.pdf` | `application/pdf` | Automatic landscape A4 beyond 5 columns. For correct diacritics it registers DejaVu Sans → Arial → Calibri in that order. **At most 1500 rows are printed**, with a note for the remainder |
| `xlsx` | `.xlsx` | `...spreadsheetml.sheet` | Organisation name + title + period + generation time in the header, blue header row, borders, automatic column widths, **frozen header row**, totals block at the bottom |
| `csv` | `.csv` | `text/csv; charset=utf-8` | **Semicolon (`;`) delimiter** and a **UTF-8 BOM** so Excel opens non-ASCII characters correctly |
| `json` | `.json` | `application/json` | The raw structure: column definitions, rows, totals, summary. For feeding another system |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reports/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -o report.xlsx \
  -d '{
        "report_key": "attendance",
        "format": "xlsx",
        "period": "month",
        "group_id": 3,
        "language": "en"
      }'
```

Exporting requires `report:export`; the preview (`/reports/preview`) only needs the
report's own permission.

### 11.3 Templates

You can save a frequently used filter set with **Save Template** (`ReportTemplate`).
Next time, one click produces the same report with the same filters.

---

## 12. Interpreting the Metrics Correctly

This section lists the most common interpretation mistakes made with this system and
how to avoid them.

### 12.1 The small-sample fallacy

The engine's own thresholds are already a warning list:

| Calculation | Minimum requirement | Below it |
|---|---|---|
| Standard deviation | 2 records | Returns null |
| Slope (trend) | 2 records on 2 different dates | Returns null |
| Correlation | 3 data pairs + variation in both variables | Returns null |
| Outliers | 4 values (4 attendance records per student, at least 4 students) | Empty list |
| Declining athlete | 4 records + ≥ 1% decline | Not listed |
| Top improver | 3 records | Not listed |
| Low-attendance student | 3 attendance records | Not listed |
| AI interpretation | 3 data points (`MIN_DATA_POINTS`) | AI is not called |

**Rule:** whenever you see a ratio, look for the **denominator** first. A student who
attended 1 of 2 lessons shows "50% attendance", and so does one who attended 20 of 40.
They are not the same information. The "record count" / "lesson count" columns exist
exactly for this.

### 12.2 Seasonality

A swimming school is a seasonal business and the engine does **not** correct for it.

* A registration surge in June–August and a dip in December–February are normal.
* Ramadan, mid-term breaks and exam periods structurally lower attendance.
* **The correct comparison is the same period last year.** Choose the `custom` period
  and enter last year's date range. `previous_period` gives you the preceding window
  of equal length — it compares August with July and hides the seasonality.
* `trend_analysis()` produces a crude seasonality hint: if a month's mean exceeds
  **125%** of the overall mean, that month is flagged as a "peak month". This is a
  rough marker, not a statistical seasonal decomposition.

### 12.3 Confusing correlation with causation

This is the most common and most expensive mistake. Checklist:

1. **Could causation run the other way?** (Does the improving athlete show up more, or
   does showing up produce improvement?)
2. **Is there a shared third factor?** (Family involvement raises both attendance and
   improvement.)
3. **How was the sample selected?** (Students below the threshold never entered the
   analysis.)
4. **How large is the sample?** (The `sample_size` field is in the response — always
   read it.)
5. **How strong is the coefficient?** (Do not build policy on results labelled `weak`
   or `negligible`.)

### 12.4 Other common mistakes

| Mistake | The correct reading |
|---|---|
| "Our pool occupancy is 48%, that is bad" | The denominator covers all opening hours and all days; 100% is impossible. Measure your own facility's realistic band |
| "Retention is 100%, excellent" | If there were no active students at the start of the period, the engine returns 100% by default. The denominator may be zero |
| "Our average membership is 240 days" | For students who have not left, time up to today is used; the number grows every day and is not affected by the period filter |
| "Attendance dropped, the instructor is the problem" | Excused absences (`excused`) also lower the rate. Separate the illness season and holiday effect |
| "Instructor A's occupancy is low" | Occupancy is set by the schedule, not by the instructor. Look at the lesson slot first |
| "This month's revenue is below last month's" | The `month` period measures **up to today**. On the 10th you are comparing 10 days with 30 |
| "A 25% cancellation rate is very high" | Check the denominator: 1 of 4 lessons, or 10 of 40? |
| "Readiness is 92, they will win" | The score knows nothing about competitors, race conditions or daily form. It measures preparation relative to the athlete's own history |
| "Correlation is 0.65, so that is the cause" | Correlation is not causation (§9.2) |
| "An outlier appeared, the student is a problem" | The z-score measures deviation from the mean; in a high-attendance school even 85% can be an outlier |
| "The AI panel gives a different number" | The AI interpretation is a textual inference. **The basis for a decision is always the computed number in the green panel** (see `docs/AI_GUIDE_EN.md`) |

### 12.5 A healthy reading routine

1. Pick the period, then check the **denominator**.
2. Compare the same period with last year (seasonality).
3. Look at the raw count next to the ratio (a percentage alone can lie).
4. Look at the last 3–4 points of the trend chart; never decide on a single spike.
5. When you see an odd result, first consider a **data-entry error** — a mistyped time
   or a double-recorded attendance is common.
6. When writing down a decision, note which metric you used, for which period, and
   with which denominator.

---

## Related documents

* `docs/AI_GUIDE_EN.md` — the real-data / AI-interpretation split and how to use AI
* `docs/BACKUP_RESTORE_EN.md` — backup and restore
* `CHANGELOG.md` — release notes
* `http://127.0.0.1:8000/docs` — live API documentation (240 endpoints)
