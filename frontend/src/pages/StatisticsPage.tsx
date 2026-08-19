/** İstatistik ve analitik merkezi: öğrenci, eğitmen, havuz, yoklama, KPI ve gelişmiş analizler. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CalendarCheck,
  FlaskConical,
  GraduationCap,
  Minus,
  Target,
  Users,
  Waves,
} from 'lucide-react'
import { Fragment, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  Alert,
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  ProgressBar,
  StatCard,
  TableWrapper,
  Tabs,
} from '@/components/ui'
import { get, put } from '@/lib/api'
import {
  formatCompact,
  formatCurrency,
  formatDate,
  formatDecimal,
  formatDelta,
  formatDuration,
  formatNumber,
  formatPercent,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  AttendanceStatistics,
  CohortAnalysis,
  ComparisonMetric,
  CorrelationResult,
  Distribution,
  Group,
  HeatmapCell,
  InstructorStatistics,
  KpiDashboard,
  KpiValue,
  Pool,
  PoolStatistics,
  StudentStatistics,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler ve yerel tipler
// ---------------------------------------------------------------------------
const CHART_COLORS = ['#0ea5e9', '#38bdf8', '#6366f1', '#8b5cf6', '#f59e0b', '#10b981', '#f43f5e']
const PERIODS = [
  'today',
  'week',
  'month',
  'quarter',
  'half_year',
  'year',
  'last_year',
  'custom',
] as const
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6]
const TARGET_PERIODS: Array<{ value: string; labelKey: string }> = [
  { value: 'monthly', labelKey: 'membership.types.monthly' },
  { value: 'quarterly', labelKey: 'membership.types.quarterly' },
  { value: 'yearly', labelKey: 'membership.types.annual' },
]
const DISTRIBUTION_METRICS: Array<{ value: string; labelKey: string }> = [
  { value: 'student_age', labelKey: 'statistics.ageDistribution' },
  { value: 'attendance_rate', labelKey: 'attendance.rate' },
  { value: 'lesson_occupancy', labelKey: 'lesson.occupancy' },
]

type PeriodKey = (typeof PERIODS)[number]
type StatTab = 'students' | 'instructors' | 'pools' | 'attendance' | 'kpi' | 'advanced'

interface OutlierRow {
  entity_type: string
  entity_id: number
  label: string
  value: number
  z_score: number
  direction: string
}

interface DistributionAnalysis {
  metric: string
  count: number
  mean: number
  median: number
  std_dev: number
  min_value: number
  max_value: number
  percentile_25: number
  percentile_75: number
  percentile_90: number
  histogram: Distribution[]
}

interface KpiTargetOut {
  id: number
  kpi_key: string
  target_value: number
  unit: string
  period: string
  notes?: string | null
  is_active: boolean
}

// ---------------------------------------------------------------------------
// Yardımcılar
// ---------------------------------------------------------------------------
function firstDayOfMonth(): Date {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), 1)
}

function isoDate(value: Date): string {
  const offset = value.getTimezoneOffset()
  return new Date(value.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

/** KPI değerini birimine göre biçimlendirir */
function formatByUnit(value: number, unit: string): string {
  if (unit === 'percent') return formatPercent(value)
  if (unit === 'currency') return formatCurrency(value)
  return formatNumber(value)
}

/** Korelasyon gücünü mevcut çeviri anahtarlarına eşler */
function strengthLabelKey(strength: string): string {
  if (strength === 'very_strong' || strength === 'strong') return 'caio.severity.high'
  if (strength === 'moderate') return 'caio.severity.medium'
  return 'caio.severity.low'
}

function kpiTone(status: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (status === 'good') return 'success'
  if (status === 'warning') return 'warning'
  if (status === 'bad') return 'danger'
  return 'neutral'
}

/** Brand tonlarıyla ısı rengi: 0 = şeffaf, maksimum = koyu brand */
function heatBackground(value: number, max: number): string {
  if (value <= 0 || max <= 0) return 'transparent'
  const ratio = Math.min(1, value / max)
  return `rgba(14, 165, 233, ${(0.12 + ratio * 0.8).toFixed(3)})`
}

// ---------------------------------------------------------------------------
// Karşılaştırma kartı (önceki döneme göre değişim)
// ---------------------------------------------------------------------------
function ComparisonCard({ metric }: { metric: ComparisonMetric }) {
  const { t, i18n } = useTranslation()
  const label = i18n.language === 'tr' ? metric.label_tr : metric.label_en
  const change = metric.change_percent ?? 0
  const isGood = metric.direction === 'down_good' ? change < 0 : change > 0
  const isFlat = Math.abs(change) < 0.05
  const ChangeIcon = isFlat ? Minus : change > 0 ? ArrowUpRight : ArrowDownRight
  const changeClass = isFlat
    ? 'text-slate-500 dark:text-slate-400'
    : isGood
      ? 'text-emerald-600 dark:text-emerald-400'
      : 'text-rose-600 dark:text-rose-400'

  return (
    <div className="card p-4">
      <p className="truncate text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        {metric.unit === 'percent' ? formatPercent(metric.current) : formatNumber(metric.current)}
      </p>
      <p className={`mt-1 flex items-center gap-1 text-xs font-medium ${changeClass}`}>
        <ChangeIcon className="h-3.5 w-3.5" />
        {formatPercent(Math.abs(change))}
        <span className="font-normal text-slate-400">{t('statistics.vsPrevious')}</span>
      </p>
      <p className="mt-0.5 text-[11px] text-slate-400">
        {t('common.previous')}: {formatNumber(metric.previous ?? 0)} (
        {formatDelta(metric.change_absolute ?? 0)})
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Yoğunluk haritası (gün x saat)
// ---------------------------------------------------------------------------
function LoadHeatmap({ cells }: { cells: HeatmapCell[] }) {
  const { t } = useTranslation()

  if (cells.length === 0) {
    return <EmptyState title={t('common.noData')} />
  }

  const hours = Array.from(new Set(cells.map((cell) => cell.hour))).sort((a, b) => a - b)
  const max = Math.max(...cells.map((cell) => cell.value))
  const lookup = new Map<string, HeatmapCell>()
  cells.forEach((cell) => lookup.set(`${cell.weekday}-${cell.hour}`, cell))

  return (
    <div className="overflow-x-auto">
      <div
        className="grid min-w-max gap-1"
        style={{ gridTemplateColumns: `72px repeat(${hours.length}, 34px)` }}
      >
        <div />
        {hours.map((hour) => (
          <div
            key={`head-${hour}`}
            className="text-center text-[10px] text-slate-500 dark:text-slate-400"
          >
            {String(hour).padStart(2, '0')}
          </div>
        ))}
        {WEEKDAYS.map((weekday) => (
          <Fragment key={weekday}>
            <div className="pr-2 text-right text-[11px] leading-7 text-slate-500 dark:text-slate-400">
              {t(`weekdays.short.${weekday}`)}
            </div>
            {hours.map((hour) => {
              const cell = lookup.get(`${weekday}-${hour}`)
              const value = cell?.value ?? 0
              const ratio = max > 0 ? value / max : 0
              return (
                <div
                  key={`${weekday}-${hour}`}
                  title={`${t(`weekdays.${weekday}`)} ${String(hour).padStart(2, '0')}:00 · ${formatDuration(value)} · ${t('instructor.lessonCount')}: ${cell?.lesson_count ?? 0}`}
                  className="h-7 rounded border border-slate-200/70 text-center text-[10px] leading-7 text-slate-700 dark:border-slate-700/70 dark:text-slate-200"
                  style={{
                    backgroundColor: heatBackground(value, max),
                    color: ratio > 0.55 ? '#ffffff' : undefined,
                  }}
                >
                  {cell?.lesson_count ? cell.lesson_count : ''}
                </div>
              )
            })}
          </Fragment>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
        {t('statistics.heatmapSubtitle')}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
export default function StatisticsPage() {
  const { t, i18n } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()
  const isTR = i18n.language === 'tr'

  const [tab, setTab] = useState<StatTab>('students')
  const [period, setPeriod] = useState<PeriodKey>('month')
  const [customRange, setCustomRange] = useState(() => ({
    from: isoDate(firstDayOfMonth()),
    to: isoDate(new Date()),
  }))
  const [groupId, setGroupId] = useState('')
  const [poolId, setPoolId] = useState('')
  const [cohortMonths, setCohortMonths] = useState(12)
  const [correlationDays, setCorrelationDays] = useState(180)
  const [distributionMetric, setDistributionMetric] = useState('student_age')

  const [targetKpi, setTargetKpi] = useState<KpiValue | null>(null)
  const [targetValue, setTargetValue] = useState('')
  const [targetPeriod, setTargetPeriod] = useState('monthly')
  const [targetNotes, setTargetNotes] = useState('')

  const periodParams = {
    period,
    date_from: period === 'custom' ? customRange.from : undefined,
    date_to: period === 'custom' ? customRange.to : undefined,
  }

  // -------------------------------------------------------------------------
  // Filtre kaynakları
  // -------------------------------------------------------------------------
  const groupsQuery = useQuery({
    queryKey: ['groups'],
    queryFn: () => get<Group[]>('/groups'),
    enabled: tab === 'students' || tab === 'attendance',
    staleTime: 5 * 60_000,
  })

  const poolsQuery = useQuery({
    queryKey: ['pools'],
    queryFn: () => get<Pool[]>('/pools'),
    enabled: tab === 'pools',
    staleTime: 5 * 60_000,
  })

  // -------------------------------------------------------------------------
  // İstatistik sorguları
  // -------------------------------------------------------------------------
  const studentsQuery = useQuery({
    queryKey: ['statistics', 'students', periodParams, groupId],
    queryFn: () =>
      get<StudentStatistics>('/statistics/students', {
        ...periodParams,
        group_id: groupId || undefined,
      }),
    enabled: tab === 'students',
  })

  const instructorsQuery = useQuery({
    queryKey: ['statistics', 'instructors', periodParams],
    queryFn: () => get<InstructorStatistics>('/statistics/instructors', periodParams),
    enabled: tab === 'instructors',
  })

  const poolsStatsQuery = useQuery({
    queryKey: ['statistics', 'pools', periodParams, poolId],
    queryFn: () =>
      get<PoolStatistics>('/statistics/pools', {
        ...periodParams,
        pool_id: poolId || undefined,
      }),
    enabled: tab === 'pools',
  })

  const attendanceQuery = useQuery({
    queryKey: ['statistics', 'attendance', periodParams, groupId],
    queryFn: () =>
      get<AttendanceStatistics>('/statistics/attendance', {
        ...periodParams,
        group_id: groupId || undefined,
      }),
    enabled: tab === 'attendance',
  })

  const kpiQuery = useQuery({
    queryKey: ['statistics', 'kpi', periodParams],
    queryFn: () => get<KpiDashboard>('/statistics/kpi', periodParams),
    enabled: tab === 'kpi',
  })

  const cohortQuery = useQuery({
    queryKey: ['statistics', 'cohort', cohortMonths],
    queryFn: () => get<CohortAnalysis>('/statistics/cohort', { months: cohortMonths }),
    enabled: tab === 'advanced',
  })

  const correlationQuery = useQuery({
    queryKey: ['statistics', 'correlation', correlationDays],
    queryFn: () =>
      get<CorrelationResult | null>('/statistics/correlation/attendance-performance', {
        days: correlationDays,
      }),
    enabled: tab === 'advanced',
  })

  const distributionQuery = useQuery({
    queryKey: ['statistics', 'distribution', distributionMetric],
    queryFn: () => get<DistributionAnalysis>(`/statistics/distribution/${distributionMetric}`),
    enabled: tab === 'advanced',
  })

  const outliersQuery = useQuery({
    queryKey: ['statistics', 'outliers', periodParams],
    queryFn: () => get<OutlierRow[]>('/statistics/outliers/attendance', periodParams),
    enabled: tab === 'advanced',
  })

  // -------------------------------------------------------------------------
  // KPI hedefi
  // -------------------------------------------------------------------------
  const saveTarget = useMutation({
    mutationFn: () =>
      put<KpiTargetOut>('/statistics/kpi/targets', {
        kpi_key: targetKpi?.key ?? '',
        target_value: Number(targetValue.replace(',', '.')) || 0,
        unit: targetKpi?.unit ?? 'percent',
        period: targetPeriod,
        notes: targetNotes.trim() || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['statistics', 'kpi'] })
      setTargetKpi(null)
      setTargetValue('')
      setTargetNotes('')
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  // -------------------------------------------------------------------------
  // Sabitlenmiş veriler (kapanış içinde tip daraltmasını korumak için)
  // -------------------------------------------------------------------------
  const studentStats = studentsQuery.data
  const instructorStats = instructorsQuery.data
  const poolStats = poolsStatsQuery.data
  const attendanceStats = attendanceQuery.data
  const kpiData = kpiQuery.data
  const cohortData = cohortQuery.data
  const correlationData = correlationQuery.data
  const distributionData = distributionQuery.data
  const outlierRows = outliersQuery.data

  const periodLabel =
    studentStats ??
    instructorStats ??
    poolStats ??
    attendanceStats ??
    kpiData ??
    null

  const tabs = [
    { id: 'students', label: t('statistics.tabs.students'), icon: <Users className="h-4 w-4" /> },
    {
      id: 'instructors',
      label: t('statistics.tabs.instructors'),
      icon: <GraduationCap className="h-4 w-4" />,
    },
    { id: 'pools', label: t('statistics.tabs.pools'), icon: <Waves className="h-4 w-4" /> },
    {
      id: 'attendance',
      label: t('statistics.tabs.attendance'),
      icon: <CalendarCheck className="h-4 w-4" />,
    },
    { id: 'kpi', label: t('statistics.tabs.kpi'), icon: <Target className="h-4 w-4" /> },
    {
      id: 'advanced',
      label: t('statistics.tabs.advanced'),
      icon: <FlaskConical className="h-4 w-4" />,
    },
  ]

  const attendanceStatusData = attendanceStats
    ? [
        { key: 'present', value: attendanceStats.present_count },
        { key: 'absent', value: attendanceStats.absent_count },
        { key: 'late', value: attendanceStats.late_count },
        { key: 'excused', value: attendanceStats.excused_count },
        { key: 'cancelled', value: attendanceStats.cancelled_count },
        { key: 'makeup', value: attendanceStats.makeup_count },
      ]
        .filter((item) => item.value > 0)
        .map((item) => ({ name: t(`attendance.statuses.${item.key}`), value: item.value }))
    : []

  const lowestStudents = (attendanceStats?.lowest_students ?? []).map((row) => ({
    studentId: Number(row.student_id ?? 0),
    studentName: String(row.student_name ?? '—'),
    attendanceRate: Number(row.attendance_rate ?? 0),
    records: Number(row.records ?? 0),
  }))

  return (
    <>
      <PageHeader
        title={t('statistics.title')}
        subtitle={
          periodLabel
            ? `${formatDate(periodLabel.period_start)} – ${formatDate(periodLabel.period_end)}`
            : t('statistics.subtitle')
        }
        icon={<BarChart3 className="h-5 w-5" />}
        actions={
          <div className="flex flex-wrap items-end gap-2">
            <Field label={t('statistics.period')} className="w-44">
              <select
                className="select py-1.5"
                value={period}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                  setPeriod(event.target.value as PeriodKey)
                }
              >
                {PERIODS.map((key) => (
                  <option key={key} value={key}>
                    {t(`statistics.periods.${key}`)}
                  </option>
                ))}
              </select>
            </Field>
            {period === 'custom' && (
              <>
                <Field label={t('lesson.start')} className="w-40">
                  <input
                    type="date"
                    className="input py-1.5"
                    value={customRange.from}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                      setCustomRange((current) => ({ ...current, from: event.target.value }))
                    }
                  />
                </Field>
                <Field label={t('lesson.end')} className="w-40">
                  <input
                    type="date"
                    className="input py-1.5"
                    value={customRange.to}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                      setCustomRange((current) => ({ ...current, to: event.target.value }))
                    }
                  />
                </Field>
              </>
            )}
          </div>
        }
      />

      <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as StatTab)} />

      {/* ------------------------------------------------------------------ */}
      {/* Öğrenci istatistikleri */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'students' && (
        <>
          <div className="mb-4 max-w-xs">
            <Field label={t('student.group')}>
              <select
                className="select"
                value={groupId}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                  setGroupId(event.target.value)
                }
              >
                <option value="">{t('common.all')}</option>
                {(groupsQuery.data ?? []).map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {studentsQuery.isLoading && <LoadingState />}
          {studentsQuery.error && (
            <ErrorState error={studentsQuery.error} onRetry={() => void studentsQuery.refetch()} />
          )}

          {studentStats && (
            <>
              <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label={t('dashboard.totalStudents')}
                  value={formatNumber(studentStats.total_students)}
                  hint={`${t('studentStatus.trial')}: ${formatNumber(studentStats.trial_students)}`}
                  icon={<Users className="h-5 w-5" />}
                  tone="brand"
                />
                <StatCard
                  label={t('dashboard.activeStudents')}
                  value={formatNumber(studentStats.active_students)}
                  hint={`${t('studentStatus.passive')}: ${formatNumber(studentStats.passive_students)}`}
                  tone="success"
                />
                <StatCard
                  label={t('statistics.newRegistrations')}
                  value={formatNumber(studentStats.new_registrations)}
                  trend={{ value: studentStats.growth_rate, label: t('statistics.growthRate') }}
                  tone="success"
                />
                <StatCard
                  label={t('statistics.lostStudents')}
                  value={formatNumber(studentStats.lost_students)}
                  tone={studentStats.lost_students > 0 ? 'danger' : 'neutral'}
                />
              </div>

              <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label={t('statistics.retentionRate')}
                  value={formatPercent(studentStats.retention_rate)}
                  tone={studentStats.retention_rate >= 80 ? 'success' : 'warning'}
                />
                <StatCard
                  label={t('statistics.churnRate')}
                  value={formatPercent(studentStats.churn_rate)}
                  tone={studentStats.churn_rate <= 10 ? 'success' : 'danger'}
                />
                <StatCard
                  label={t('statistics.avgMembershipDays')}
                  value={formatNumber(studentStats.average_membership_days)}
                  tone="neutral"
                />
                <StatCard
                  label={t('attendance.rate')}
                  value={formatPercent(studentStats.attendance_rate)}
                  tone={studentStats.attendance_rate >= 80 ? 'success' : 'warning'}
                />
              </div>

              {studentStats.comparisons.length > 0 && (
                <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {studentStats.comparisons.map((metric) => (
                    <ComparisonCard key={metric.key} metric={metric} />
                  ))}
                </div>
              )}

              <div className="grid gap-4 lg:grid-cols-2">
                <Card title={t('statistics.ageDistribution')}>
                  {studentStats.age_distribution.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={studentStats.age_distribution}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                        <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} width={40} />
                        <Tooltip
                          formatter={(value: number) => formatNumber(value)}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Bar dataKey="value" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card title={t('statistics.levelDistribution')}>
                  {studentStats.level_distribution.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <PieChart>
                        <Pie
                          data={studentStats.level_distribution.map((item) => ({
                            ...item,
                            name: t(`swimLevel.${item.label}`, item.label),
                          }))}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={45}
                          outerRadius={85}
                          paddingAngle={2}
                        >
                          {studentStats.level_distribution.map((_, index) => (
                            <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: number, name: string) => [formatNumber(value), name]}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card title={t('statistics.groupDistribution')}>
                  {studentStats.group_distribution.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart
                        data={studentStats.group_distribution}
                        layout="vertical"
                        margin={{ left: 8, right: 16 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                        <XAxis type="number" tick={{ fontSize: 10 }} />
                        <YAxis type="category" dataKey="label" tick={{ fontSize: 10 }} width={110} />
                        <Tooltip
                          formatter={(value: number) => formatNumber(value)}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card title={t('statistics.genderDistribution')}>
                  {studentStats.gender_distribution.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <PieChart>
                        <Pie
                          data={studentStats.gender_distribution.map((item) => ({
                            ...item,
                            name: t(`gender.${item.label}`, item.label),
                          }))}
                          dataKey="value"
                          nameKey="name"
                          outerRadius={85}
                          paddingAngle={2}
                        >
                          {studentStats.gender_distribution.map((_, index) => (
                            <Cell key={index} fill={CHART_COLORS[(index + 2) % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: number, name: string) => [formatNumber(value), name]}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card title={t('statistics.registrationTrend')} className="lg:col-span-2">
                  {studentStats.registration_trend.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={260}>
                      <AreaChart data={studentStats.registration_trend}>
                        <defs>
                          <linearGradient id="registrationGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
                            <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                        <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} width={40} />
                        <Tooltip
                          formatter={(value: number) => formatNumber(value)}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Area
                          type="monotone"
                          dataKey="value"
                          stroke="#0ea5e9"
                          strokeWidth={2}
                          fill="url(#registrationGradient)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  )}
                </Card>
              </div>
            </>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Eğitmen istatistikleri */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'instructors' && (
        <>
          {instructorsQuery.isLoading && <LoadingState />}
          {instructorsQuery.error && (
            <ErrorState
              error={instructorsQuery.error}
              onRetry={() => void instructorsQuery.refetch()}
            />
          )}

          {instructorStats && (
            <>
              <div className="mb-6 grid gap-3 sm:grid-cols-3">
                <StatCard
                  label={t('instructor.weeklyHours')}
                  value={formatNumber(instructorStats.total_hours, 1)}
                  icon={<GraduationCap className="h-5 w-5" />}
                  tone="brand"
                />
                <StatCard
                  label={t('instructor.studentCount')}
                  value={formatNumber(instructorStats.average_students_per_instructor, 1)}
                  tone="neutral"
                />
                <StatCard
                  label={t('instructor.occupancyRate')}
                  value={formatPercent(instructorStats.average_occupancy)}
                  tone={instructorStats.average_occupancy >= 70 ? 'success' : 'warning'}
                />
              </div>

              <Card title={t('instructor.workload')} className="mb-4">
                {instructorStats.rows.length === 0 ? (
                  <EmptyState title={t('common.noData')} />
                ) : (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={instructorStats.rows} margin={{ left: 8, right: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                      <XAxis dataKey="full_name" tick={{ fontSize: 10 }} interval={0} angle={-15} height={50} />
                      <YAxis
                        tick={{ fontSize: 10 }}
                        width={45}
                        tickFormatter={(value: number) => formatCompact(value)}
                      />
                      <Tooltip
                        formatter={(value: number) => formatNumber(value, 1)}
                        contentStyle={{ fontSize: 12, borderRadius: 8 }}
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar
                        dataKey="total_hours"
                        name={t('instructor.weeklyHours')}
                        fill="#0ea5e9"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>

              <Card title={t('instructor.title')} bodyClassName="p-0" className="mb-4">
                {instructorStats.rows.length === 0 ? (
                  <EmptyState title={t('common.noData')} />
                ) : (
                  <TableWrapper>
                    <thead>
                      <tr>
                        <th>{t('instructor.singular')}</th>
                        <th>{t('instructor.studentCount')}</th>
                        <th>{t('instructor.lessonCount')}</th>
                        <th>{t('instructor.weeklyHours')}</th>
                        <th>{t('instructor.occupancyRate')}</th>
                        <th className="hidden md:table-cell">{t('attendance.rate')}</th>
                        <th className="hidden lg:table-cell">{t('instructor.cancellationRate')}</th>
                        <th className="hidden lg:table-cell">{t('instructor.privateRatio')}</th>
                        <th className="text-right">{t('performance.improvementPercent')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {instructorStats.rows.map((row) => (
                        <tr key={row.instructor_id}>
                          <td className="font-medium">{row.full_name}</td>
                          <td>{formatNumber(row.student_count)}</td>
                          <td>{formatNumber(row.lesson_count)}</td>
                          <td>{formatNumber(row.total_hours, 1)}</td>
                          <td>
                            <div className="w-24">
                              <ProgressBar
                                value={row.occupancy_rate}
                                tone={row.occupancy_rate >= 70 ? 'success' : 'warning'}
                                showLabel
                              />
                            </div>
                          </td>
                          <td className="hidden md:table-cell">
                            {formatPercent(row.attendance_rate)}
                          </td>
                          <td className="hidden lg:table-cell">
                            {formatPercent(row.cancellation_rate)}
                          </td>
                          <td className="hidden lg:table-cell">
                            {formatPercent(row.private_ratio)}
                          </td>
                          <td className="text-right">
                            {row.student_improvement_percent === null ||
                            row.student_improvement_percent === undefined ? (
                              <span className="text-xs text-slate-400">—</span>
                            ) : (
                              <span
                                className={
                                  row.student_improvement_percent > 0
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : 'text-rose-600 dark:text-rose-400'
                                }
                              >
                                {formatDelta(row.student_improvement_percent)}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </TableWrapper>
                )}
              </Card>

              <Alert tone="info" title={t('statistics.tabs.instructors')}>
                {isTR ? instructorStats.disclaimer_tr : instructorStats.disclaimer_en}
              </Alert>
            </>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Havuz istatistikleri */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'pools' && (
        <>
          <div className="mb-4 max-w-xs">
            <Field label={t('pool.singular')}>
              <select
                className="select"
                value={poolId}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                  setPoolId(event.target.value)
                }
              >
                <option value="">{t('common.all')}</option>
                {(poolsQuery.data ?? []).map((pool) => (
                  <option key={pool.id} value={pool.id}>
                    {pool.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {poolsStatsQuery.isLoading && <LoadingState />}
          {poolsStatsQuery.error && (
            <ErrorState
              error={poolsStatsQuery.error}
              onRetry={() => void poolsStatsQuery.refetch()}
            />
          )}

          {poolStats && (
            <>
              <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <StatCard
                  label={t('dashboard.poolOccupancy')}
                  value={formatPercent(poolStats.overall_occupancy)}
                  icon={<Waves className="h-5 w-5" />}
                  tone={poolStats.overall_occupancy >= 60 ? 'success' : 'warning'}
                />
                <StatCard
                  label={t('statistics.freeCapacity')}
                  value={formatNumber(poolStats.free_capacity_hours, 1)}
                  tone="neutral"
                />
                <StatCard
                  label={`${t('lane.singular')} / ${t('lesson.singular')}`}
                  value={formatNumber(poolStats.average_lanes_per_lesson, 2)}
                  tone="neutral"
                />
              </div>

              <div className="mb-6 grid gap-3 sm:grid-cols-3">
                <StatCard
                  label={t('statistics.busiestHour')}
                  value={poolStats.busiest_hour ?? '—'}
                  tone="brand"
                />
                <StatCard
                  label={t('statistics.quietestHour')}
                  value={poolStats.quietest_hour ?? '—'}
                  tone="neutral"
                />
                <StatCard
                  label={t('statistics.mostUsedLane')}
                  value={poolStats.most_used_lane ?? '—'}
                  tone="neutral"
                />
              </div>

              <div className="mb-4 grid gap-4 lg:grid-cols-2">
                <Card title={t('dashboard.hourlyLoad')}>
                  {poolStats.hourly_load.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={poolStats.hourly_load}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                        <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={1} />
                        <YAxis
                          tick={{ fontSize: 10 }}
                          width={45}
                          tickFormatter={(value: number) => formatCompact(value)}
                        />
                        <Tooltip
                          formatter={(value: number) => formatDuration(value)}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Bar dataKey="value" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card title={t('lesson.weekdays')}>
                  {poolStats.daily_load.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={poolStats.daily_load}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                        <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                        <YAxis
                          tick={{ fontSize: 10 }}
                          width={45}
                          tickFormatter={(value: number) => formatCompact(value)}
                        />
                        <Tooltip
                          formatter={(value: number) => formatDuration(value)}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </Card>
              </div>

              <Card title={t('lane.title')} className="mb-4" bodyClassName="p-0">
                {poolStats.lane_usage.length === 0 ? (
                  <EmptyState title={t('common.noData')} />
                ) : (
                  <TableWrapper>
                    <thead>
                      <tr>
                        <th>{t('lane.singular')}</th>
                        <th>{t('common.total')}</th>
                        <th className="w-1/2">{t('lesson.occupancy')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {poolStats.lane_usage.map((lane) => (
                        <tr key={lane.label}>
                          <td className="font-medium">{lane.label}</td>
                          <td className="whitespace-nowrap">{formatDuration(lane.value)}</td>
                          <td>
                            <ProgressBar value={lane.percent} tone="brand" showLabel />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </TableWrapper>
                )}
              </Card>

              <Card title={t('statistics.heatmap')}>
                <LoadHeatmap cells={poolStats.heatmap} />
              </Card>
            </>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Yoklama istatistikleri */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'attendance' && (
        <>
          <div className="mb-4 max-w-xs">
            <Field label={t('student.group')}>
              <select
                className="select"
                value={groupId}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                  setGroupId(event.target.value)
                }
              >
                <option value="">{t('common.all')}</option>
                {(groupsQuery.data ?? []).map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {attendanceQuery.isLoading && <LoadingState />}
          {attendanceQuery.error && (
            <ErrorState
              error={attendanceQuery.error}
              onRetry={() => void attendanceQuery.refetch()}
            />
          )}

          {attendanceStats && (
            <>
              <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <StatCard
                  label={t('attendance.rate')}
                  value={formatPercent(attendanceStats.overall_rate)}
                  icon={<CalendarCheck className="h-5 w-5" />}
                  tone={attendanceStats.overall_rate >= 80 ? 'success' : 'warning'}
                />
                <StatCard
                  label={t('attendance.noShowRate')}
                  value={formatPercent(attendanceStats.no_show_rate)}
                  tone={attendanceStats.no_show_rate <= 10 ? 'success' : 'danger'}
                />
                <StatCard
                  label={t('attendance.statuses.late')}
                  value={formatPercent(attendanceStats.late_rate)}
                  tone="neutral"
                />
                <StatCard
                  label={t('attendance.statuses.excused')}
                  value={formatPercent(attendanceStats.excuse_rate)}
                  tone="neutral"
                />
                <StatCard
                  label={t('attendance.statuses.makeup')}
                  value={formatPercent(attendanceStats.makeup_rate)}
                  tone="neutral"
                />
              </div>

              <div className="mb-4 grid gap-4 lg:grid-cols-2">
                <Card title={t('attendance.summary')}>
                  {attendanceStatusData.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie
                          data={attendanceStatusData}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={50}
                          outerRadius={90}
                          paddingAngle={2}
                        >
                          {attendanceStatusData.map((_, index) => (
                            <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: number, name: string) => [formatNumber(value), name]}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card title={t('dashboard.attendanceTrend')}>
                  {attendanceStats.trend.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={attendanceStats.trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                        <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                        <YAxis tick={{ fontSize: 10 }} width={45} domain={[0, 100]} />
                        <Tooltip
                          formatter={(value: number) => formatPercent(value)}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#10b981"
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </Card>
              </div>

              <div className="mb-4 grid gap-4 lg:grid-cols-2">
                <Card title={t('statistics.groupDistribution')} bodyClassName="p-0">
                  {attendanceStats.by_group.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <TableWrapper>
                      <thead>
                        <tr>
                          <th>{t('student.group')}</th>
                          <th className="w-1/2">{t('attendance.rate')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attendanceStats.by_group.map((row) => (
                          <tr key={row.label}>
                            <td className="font-medium">{row.label}</td>
                            <td>
                              <ProgressBar
                                value={row.value}
                                tone={row.value >= 80 ? 'success' : 'warning'}
                                showLabel
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </TableWrapper>
                  )}
                </Card>

                <Card title={t('instructor.title')} bodyClassName="p-0">
                  {attendanceStats.by_instructor.length === 0 ? (
                    <EmptyState title={t('common.noData')} />
                  ) : (
                    <TableWrapper>
                      <thead>
                        <tr>
                          <th>{t('instructor.singular')}</th>
                          <th className="w-1/2">{t('attendance.rate')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attendanceStats.by_instructor.map((row) => (
                          <tr key={row.label}>
                            <td className="font-medium">{row.label}</td>
                            <td>
                              <ProgressBar
                                value={row.value}
                                tone={row.value >= 80 ? 'success' : 'warning'}
                                showLabel
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </TableWrapper>
                  )}
                </Card>
              </div>

              <Card title={t('performance.declining')} bodyClassName="p-0">
                {lowestStudents.length === 0 ? (
                  <EmptyState title={t('common.noData')} description={t('dashboard.noAlerts')} />
                ) : (
                  <TableWrapper>
                    <thead>
                      <tr>
                        <th>{t('student.singular')}</th>
                        <th>{t('attendance.rate')}</th>
                        <th className="text-right">{t('student.totalLessons')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lowestStudents.map((row) => (
                        <tr key={row.studentId}>
                          <td className="font-medium">{row.studentName}</td>
                          <td>
                            <div className="w-40">
                              <ProgressBar
                                value={row.attendanceRate}
                                tone={row.attendanceRate >= 60 ? 'warning' : 'danger'}
                                showLabel
                              />
                            </div>
                          </td>
                          <td className="text-right">{formatNumber(row.records)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </TableWrapper>
                )}
              </Card>
            </>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* KPI */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'kpi' && (
        <>
          {kpiQuery.isLoading && <LoadingState />}
          {kpiQuery.error && (
            <ErrorState error={kpiQuery.error} onRetry={() => void kpiQuery.refetch()} />
          )}

          {kpiData && kpiData.kpis.length === 0 && (
            <EmptyState title={t('common.noData')} icon={<Target className="h-6 w-6" />} />
          )}

          {kpiData && kpiData.kpis.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {kpiData.kpis.map((kpi) => {
                const tone = kpiTone(kpi.status)
                const achievement = kpi.achievement_percent ?? 0
                return (
                  <div key={kpi.key} className="card p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                          {isTR ? kpi.label_tr : kpi.label_en}
                        </p>
                        <p className="mt-1.5 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                          {formatByUnit(kpi.value, kpi.unit)}
                        </p>
                      </div>
                      {can('kpi:write') && (
                        <button
                          type="button"
                          className="btn-ghost btn-sm"
                          title={t('statistics.setTarget')}
                          aria-label={t('statistics.setTarget')}
                          onClick={() => {
                            setTargetKpi(kpi)
                            setTargetValue(kpi.target !== null && kpi.target !== undefined ? String(kpi.target) : '')
                            setTargetPeriod('monthly')
                            setTargetNotes('')
                          }}
                        >
                          <Target className="h-4 w-4" />
                        </button>
                      )}
                    </div>

                    <div className="mt-3 flex items-center justify-between text-xs">
                      <span className="text-slate-500 dark:text-slate-400">
                        {t('statistics.target')}:{' '}
                        {kpi.target !== null && kpi.target !== undefined
                          ? formatByUnit(kpi.target, kpi.unit)
                          : '—'}
                      </span>
                      <Badge tone={tone}>
                        {t('statistics.achievement')}: {formatPercent(achievement)}
                      </Badge>
                    </div>

                    <div className="mt-2">
                      <ProgressBar value={achievement} tone={tone === 'neutral' ? 'brand' : tone} />
                    </div>

                    {kpi.change_percent !== null && kpi.change_percent !== undefined && (
                      <p className="mt-2 text-[11px] text-slate-400">
                        {t('statistics.vsPrevious')}: {formatPercent(kpi.change_percent)}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Gelişmiş analizler */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'advanced' && (
        <div className="grid gap-4">
          {/* Cohort */}
          <Card
            title={t('statistics.cohort')}
            actions={
              <select
                className="select w-auto py-1 text-xs"
                value={cohortMonths}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                  setCohortMonths(Number(event.target.value))
                }
                aria-label={t('statistics.cohort')}
              >
                {[6, 12, 18, 24].map((months) => (
                  <option key={months} value={months}>
                    {months}
                  </option>
                ))}
              </select>
            }
          >
            {cohortQuery.isLoading && <LoadingState />}
            {cohortQuery.error && (
              <ErrorState error={cohortQuery.error} onRetry={() => void cohortQuery.refetch()} />
            )}
            {cohortData && cohortData.cohorts.length === 0 && (
              <EmptyState title={t('common.noData')} />
            )}
            {cohortData && cohortData.cohorts.length > 0 && (
              <>
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>{t('common.date')}</th>
                        <th>{t('common.total')}</th>
                        {Array.from({ length: cohortData.months }).map((_, index) => (
                          <th key={index} className="text-center">
                            {index}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cohortData.cohorts.map((row) => (
                        <tr key={row.cohort}>
                          <td className="whitespace-nowrap font-medium">{row.cohort}</td>
                          <td>{formatNumber(row.size)}</td>
                          {Array.from({ length: cohortData.months }).map((_, index) => {
                            const value =
                              index < row.retention_by_month.length
                                ? row.retention_by_month[index]
                                : null
                            if (value === null) {
                              return (
                                <td key={index} className="text-center text-slate-300">
                                  —
                                </td>
                              )
                            }
                            return (
                              <td
                                key={index}
                                className="text-center text-xs font-medium"
                                style={{
                                  backgroundColor: heatBackground(value, 100),
                                  color: value > 55 ? '#ffffff' : undefined,
                                }}
                              >
                                {formatNumber(value, 0)}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                  {isTR ? cohortData.note_tr : cohortData.note_en}
                </p>
              </>
            )}
          </Card>

          {/* Korelasyon */}
          <Card
            title={t('statistics.correlation')}
            actions={
              <select
                className="select w-auto py-1 text-xs"
                value={correlationDays}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                  setCorrelationDays(Number(event.target.value))
                }
                aria-label={t('statistics.correlation')}
              >
                {[90, 180, 365].map((days) => (
                  <option key={days} value={days}>
                    {days}
                  </option>
                ))}
              </select>
            }
          >
            {correlationQuery.isLoading && <LoadingState />}
            {correlationQuery.error && (
              <ErrorState
                error={correlationQuery.error}
                onRetry={() => void correlationQuery.refetch()}
              />
            )}
            {correlationQuery.isSuccess && !correlationData && (
              <EmptyState title={t('ai.insufficientData')} />
            )}
            {correlationData && (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <StatCard
                    label={t('statistics.correlation')}
                    value={formatDecimal(correlationData.coefficient, 3)}
                    hint={t(strengthLabelKey(correlationData.strength))}
                    tone={Math.abs(correlationData.coefficient) >= 0.5 ? 'brand' : 'neutral'}
                  />
                  <StatCard
                    label={t('common.total')}
                    value={formatNumber(correlationData.sample_size)}
                    hint={`${correlationData.variable_a} ↔ ${correlationData.variable_b}`}
                    tone="neutral"
                  />
                </div>
                <div className="mt-4">
                  <Alert tone="warning" title={t('statistics.correlation')}>
                    {isTR ? correlationData.disclaimer_tr : correlationData.disclaimer_en}
                  </Alert>
                </div>
              </>
            )}
          </Card>

          {/* Dağılım */}
          <Card
            title={t('statistics.distribution')}
            actions={
              <select
                className="select w-auto py-1 text-xs"
                value={distributionMetric}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                  setDistributionMetric(event.target.value)
                }
                aria-label={t('statistics.distribution')}
              >
                {DISTRIBUTION_METRICS.map((metric) => (
                  <option key={metric.value} value={metric.value}>
                    {t(metric.labelKey)}
                  </option>
                ))}
              </select>
            }
          >
            {distributionQuery.isLoading && <LoadingState />}
            {distributionQuery.error && (
              <ErrorState
                error={distributionQuery.error}
                onRetry={() => void distributionQuery.refetch()}
              />
            )}
            {distributionData && distributionData.count === 0 && (
              <EmptyState title={t('ai.insufficientData')} />
            )}
            {distributionData && distributionData.count > 0 && (
              <>
                <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <StatCard
                    label={t('performance.meanTime')}
                    value={formatDecimal(distributionData.mean, 1)}
                    tone="brand"
                  />
                  <StatCard
                    label={t('performance.medianTime')}
                    value={formatDecimal(distributionData.median, 1)}
                    tone="neutral"
                  />
                  <StatCard
                    label={t('performance.stdDev')}
                    value={formatDecimal(distributionData.std_dev, 2)}
                    tone="neutral"
                  />
                  <StatCard
                    label={t('common.total')}
                    value={formatNumber(distributionData.count)}
                    hint={`${formatDecimal(distributionData.min_value, 1)} – ${formatDecimal(distributionData.max_value, 1)}`}
                    tone="neutral"
                  />
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={distributionData.histogram}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} width={40} />
                    <Tooltip
                      formatter={(value: number) => formatNumber(value)}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                  P25 {formatDecimal(distributionData.percentile_25, 1)} · P75{' '}
                  {formatDecimal(distributionData.percentile_75, 1)} · P90{' '}
                  {formatDecimal(distributionData.percentile_90, 1)}
                </p>
              </>
            )}
          </Card>

          {/* Aykırı değerler */}
          <Card title={t('statistics.outliers')} bodyClassName="p-0">
            {outliersQuery.isLoading && <LoadingState />}
            {outliersQuery.error && (
              <ErrorState error={outliersQuery.error} onRetry={() => void outliersQuery.refetch()} />
            )}
            {outlierRows && outlierRows.length === 0 && (
              <EmptyState title={t('common.noData')} description={t('dashboard.noAlerts')} />
            )}
            {outlierRows && outlierRows.length > 0 && (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('student.singular')}</th>
                    <th>{t('attendance.rate')}</th>
                    <th>{t('performance.stdDev')}</th>
                    <th className="text-right">{t('performance.trend')}</th>
                  </tr>
                </thead>
                <tbody>
                  {outlierRows.map((row) => (
                    <tr key={`${row.entity_type}-${row.entity_id}`}>
                      <td className="font-medium">{row.label}</td>
                      <td>{formatPercent(row.value)}</td>
                      <td>{formatDecimal(row.z_score, 2)}</td>
                      <td className="text-right">
                        <Badge tone={row.direction === 'above' ? 'success' : 'danger'}>
                          {row.direction === 'above'
                            ? t('performance.trends.improving')
                            : t('performance.trends.declining')}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </Card>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* KPI hedef modalı */}
      {/* ------------------------------------------------------------------ */}
      <Modal
        open={targetKpi !== null}
        onClose={() => setTargetKpi(null)}
        title={t('statistics.setTarget')}
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setTargetKpi(null)}
              disabled={saveTarget.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={targetValue.trim().length === 0 || saveTarget.isPending}
              onClick={() => saveTarget.mutate()}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <div className="grid gap-4">
          {targetKpi && (
            <Alert tone="info" title={isTR ? targetKpi.label_tr : targetKpi.label_en}>
              {t('common.total')}: {formatByUnit(targetKpi.value, targetKpi.unit)}
            </Alert>
          )}
          <Field label={t('statistics.target')} required>
            <input
              type="number"
              step="0.01"
              className="input"
              value={targetValue}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setTargetValue(event.target.value)
              }
            />
          </Field>
          <Field label={t('statistics.period')} required>
            <select
              className="select"
              value={targetPeriod}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setTargetPeriod(event.target.value)
              }
            >
              {TARGET_PERIODS.map((item) => (
                <option key={item.value} value={item.value}>
                  {t(item.labelKey)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('common.notes')}>
            <textarea
              className="textarea"
              value={targetNotes}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setTargetNotes(event.target.value)
              }
            />
          </Field>
        </div>
      </Modal>
    </>
  )
}
