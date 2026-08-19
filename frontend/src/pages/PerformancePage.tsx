/** Sporcu performans yönetimi / Athlete performance management. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity, BarChart3, Gauge, Pencil, Plus, Timer, Trash2, TrendingDown, TrendingUp, Trophy, X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

import {
  Alert, Badge, Card, ConfirmDialog, EmptyState, ErrorState, Field, LoadingState, Modal,
  PageHeader, Pagination, ProgressBar, StatCard, TableWrapper, Tabs,
} from '@/components/ui'
import { del, get, patch, post } from '@/lib/api'
import {
  formatDate, formatDecimal, formatNumber, formatPercent, formatSwimTime, formatTimeDelta,
  parseSwimTime, toISODate,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  DecliningAthlete, Page, PerformanceEventAnalysis, PerformanceRecord, PersonalBest,
  Student, StudentPerformanceSummary, TopImprover,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Tipler ve sabitler
// ---------------------------------------------------------------------------
type TabId = 'records' | 'analysis' | 'improvers' | 'declining' | 'readiness'

/** GET /performance/events/catalog yanıtı */
interface EventCatalog {
  strokes: Array<{ value: string; label: string }>
  distances: number[]
  course_types: Array<{ value: string; label: string }>
  common_events: string[]
}

/** GET /performance/readiness satırı - tamamen istatistiksel skor */
interface ReadinessRow {
  student_id: number
  student_name: string
  event_name: string
  stroke: string
  distance_m: number
  best_time: number
  best_time_formatted: string
  recent_mean: number
  recent_mean_formatted: string
  consistency_std?: number | null
  trend: string
  records_last_period: number
  readiness_score: number
  readiness_basis: string
}

interface ReadinessResponse {
  period_days: number
  count: number
  rows: ReadinessRow[]
  note_tr: string
  note_en: string
}

interface RecordFormState {
  studentId: number | null
  studentName: string
  stroke: string
  distance: string
  courseType: string
  timeText: string
  splitsText: string
  strokeRate: string
  strokeCount: string
  reactionTime: string
  turnTime: string
  recordedDate: string
  isCompetition: boolean
  heartRate: string
  perceivedEffort: string
  notes: string
}

interface RecordFilters {
  studentId: number | null
  studentName: string
  stroke: string
  distance: string
  courseType: string
  dateFrom: string
  dateTo: string
  competition: string
}

const FALLBACK_STROKES = ['freestyle', 'backstroke', 'breaststroke', 'butterfly', 'medley']
const FALLBACK_DISTANCES = [25, 50, 100, 200, 400, 800, 1500]

const EMPTY_FILTERS: RecordFilters = {
  studentId: null,
  studentName: '',
  stroke: '',
  distance: '',
  courseType: '',
  dateFrom: '',
  dateTo: '',
  competition: '',
}

function emptyForm(): RecordFormState {
  return {
    studentId: null,
    studentName: '',
    stroke: 'freestyle',
    distance: '50',
    courseType: 'short',
    timeText: '',
    splitsText: '',
    strokeRate: '',
    strokeCount: '',
    reactionTime: '',
    turnTime: '',
    recordedDate: toISODate(new Date()),
    isCompetition: false,
    heartRate: '',
    perceivedEffort: '',
    notes: '',
  }
}

/** Boş metni null'a çevirir, sayısal alanlar için */
function numberOrNull(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number(trimmed.replace(',', '.'))
  return Number.isNaN(parsed) ? null : parsed
}

// ---------------------------------------------------------------------------
// Öğrenci seçici (arama + seçim)
// ---------------------------------------------------------------------------
function StudentPicker({
  value,
  label,
  onSelect,
}: {
  value: number | null
  label: string
  onSelect: (id: number | null, name: string) => void
}) {
  const { t } = useTranslation()
  const [term, setTerm] = useState('')
  const [debounced, setDebounced] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(term.trim()), 300)
    return () => clearTimeout(timer)
  }, [term])

  const { data, isFetching } = useQuery({
    queryKey: ['student-picker', debounced],
    queryFn: () => get<Page<Student>>('/students', { q: debounced, page_size: 12 }),
    enabled: debounced.length > 0,
  })

  if (value !== null) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-surface-dark-alt">
        <span className="truncate text-sm text-slate-800 dark:text-slate-100">{label}</span>
        <button
          type="button"
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700"
          onClick={() => {
            onSelect(null, '')
            setTerm('')
          }}
          aria-label={t('common.clearFilters')}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div className="relative">
      <input
        className="input"
        value={term}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) => setTerm(event.target.value)}
        placeholder={t('common.search')}
      />
      {debounced.length > 0 && (
        <div className="absolute z-30 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-panel dark:border-slate-700 dark:bg-surface-dark-alt">
          {isFetching && (
            <p className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">{t('common.loading')}</p>
          )}
          {!isFetching && (data?.items.length ?? 0) === 0 && (
            <p className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">{t('common.noResults')}</p>
          )}
          {data?.items.map((student) => (
            <button
              key={student.id}
              type="button"
              className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-700/60"
              onClick={() => {
                onSelect(student.id, student.full_name)
                setTerm('')
                setDebounced('')
              }}
            >
              <span className="truncate text-slate-800 dark:text-slate-100">{student.full_name}</span>
              <span className="shrink-0 text-xs text-slate-400">{student.student_number}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Küçük istatistik kutusu
// ---------------------------------------------------------------------------
function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-2.5 py-2 dark:bg-slate-800/60">
      <p className="text-[11px] leading-tight text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tek etkinlik analizi kartı (istatistik + grafik)
// ---------------------------------------------------------------------------
function EventAnalysisCard({ analysis }: { analysis: PerformanceEventAnalysis }) {
  const { t } = useTranslation()
  const title = `${analysis.distance_m} m ${t(`performance.strokes.${analysis.stroke}`, analysis.stroke)}`

  return (
    <Card
      title={title}
      actions={
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {formatNumber(analysis.record_count)}
          </span>
          <Badge
            tone={
              analysis.trend === 'improving' ? 'success' : analysis.trend === 'declining' ? 'danger' : 'neutral'
            }
          >
            {t(`performance.trends.${analysis.trend}`, analysis.trend)}
          </Badge>
        </div>
      }
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        <StatBox label={t('performance.bestTime')} value={formatSwimTime(analysis.best_time)} />
        <StatBox label={t('performance.meanTime')} value={formatSwimTime(analysis.mean_time)} />
        <StatBox label={t('performance.medianTime')} value={formatSwimTime(analysis.median_time)} />
        <StatBox
          label={t('performance.stdDev')}
          value={analysis.std_dev !== null && analysis.std_dev !== undefined ? formatDecimal(analysis.std_dev, 2) : '—'}
        />
        <StatBox
          label="25%"
          value={analysis.percentile_25 !== null && analysis.percentile_25 !== undefined
            ? formatSwimTime(analysis.percentile_25)
            : '—'}
        />
        <StatBox
          label="75%"
          value={analysis.percentile_75 !== null && analysis.percentile_75 !== undefined
            ? formatSwimTime(analysis.percentile_75)
            : '—'}
        />
        <StatBox
          label={t('performance.change30d')}
          value={analysis.change_30d !== null && analysis.change_30d !== undefined
            ? formatTimeDelta(analysis.change_30d)
            : '—'}
        />
        <StatBox
          label={t('performance.change90d')}
          value={analysis.change_90d !== null && analysis.change_90d !== undefined
            ? formatTimeDelta(analysis.change_90d)
            : '—'}
        />
        <StatBox label={t('performance.improvement')} value={formatTimeDelta(analysis.improvement_seconds)} />
        <StatBox
          label={t('performance.improvementPercent')}
          value={formatPercent(analysis.improvement_percent)}
        />
      </div>

      {/* Y ekseni ters: düşük derece daha iyidir */}
      <div className="mt-4">
        <ResponsiveContainer width="100%" height={230}>
          <LineChart data={analysis.points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              tickFormatter={(value: string) => formatDate(value)}
              minTickGap={24}
            />
            <YAxis
              reversed
              domain={['dataMin - 1', 'dataMax + 1']}
              tick={{ fontSize: 10 }}
              width={58}
              tickFormatter={(value: number) => formatSwimTime(value)}
            />
            <Tooltip
              formatter={(value: number) => formatSwimTime(value)}
              labelFormatter={(label: string) => formatDate(label)}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="time_seconds"
              name={t('performance.timeSeconds')}
              stroke="#0ea5e9"
              strokeWidth={2}
              dot={{ r: 2 }}
            />
            <Line
              type="monotone"
              dataKey="moving_average"
              name={t('performance.meanTime')}
              stroke="#8b5cf6"
              strokeWidth={2}
              strokeDasharray="4 3"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Sayfa
// ---------------------------------------------------------------------------
export default function PerformancePage() {
  const { t, i18n } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<TabId>('records')

  // Kayıtlar sekmesi
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [filters, setFilters] = useState<RecordFilters>(EMPTY_FILTERS)

  // Kayıt formu
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<RecordFormState>(emptyForm)
  const [formErrors, setFormErrors] = useState<{ student?: string; time?: string }>({})
  const [deleteTarget, setDeleteTarget] = useState<PerformanceRecord | null>(null)

  // Analiz sekmesi
  const [analysisStudent, setAnalysisStudent] = useState<{ id: number | null; name: string }>({
    id: null,
    name: '',
  })

  // Liste sekmelerinin dönem seçimi
  const [lookbackDays, setLookbackDays] = useState(90)

  function updateFilter(patchValue: Partial<RecordFilters>) {
    setFilters((current) => ({ ...current, ...patchValue }))
    setPage(1)
  }

  // --- Sorgular ---------------------------------------------------------
  const catalogQuery = useQuery({
    queryKey: ['performance-catalog', i18n.language],
    queryFn: () => get<EventCatalog>('/performance/events/catalog'),
    staleTime: 30 * 60_000,
  })

  const recordsQuery = useQuery({
    queryKey: ['performance', page, pageSize, filters],
    queryFn: () =>
      get<Page<PerformanceRecord>>('/performance', {
        page,
        page_size: pageSize,
        student_id: filters.studentId ?? undefined,
        stroke: filters.stroke || undefined,
        distance_m: filters.distance || undefined,
        course_type: filters.courseType || undefined,
        date_from: filters.dateFrom || undefined,
        date_to: filters.dateTo || undefined,
        is_competition: filters.competition === '' ? undefined : filters.competition === 'true',
      }),
    enabled: tab === 'records',
  })

  const summaryQuery = useQuery({
    queryKey: ['performance-summary', analysisStudent.id],
    queryFn: () => get<StudentPerformanceSummary>(`/performance/student/${analysisStudent.id}/summary`),
    enabled: tab === 'analysis' && analysisStudent.id !== null,
  })

  const personalBestsQuery = useQuery({
    queryKey: ['performance-personal-bests', analysisStudent.id],
    queryFn: () => get<PersonalBest[]>(`/performance/student/${analysisStudent.id}/personal-bests`),
    enabled: tab === 'analysis' && analysisStudent.id !== null,
  })

  const improversQuery = useQuery({
    queryKey: ['performance-improvers', lookbackDays],
    queryFn: () => get<TopImprover[]>('/performance/top-improvers', { days: lookbackDays, limit: 25 }),
    enabled: tab === 'improvers',
  })

  const decliningQuery = useQuery({
    queryKey: ['performance-declining', lookbackDays],
    queryFn: () => get<DecliningAthlete[]>('/performance/declining', { days: lookbackDays, limit: 25 }),
    enabled: tab === 'declining',
  })

  const readinessQuery = useQuery({
    queryKey: ['performance-readiness', lookbackDays],
    queryFn: () => get<ReadinessResponse>('/performance/readiness', { days: lookbackDays, limit: 50 }),
    enabled: tab === 'readiness',
  })

  // --- Mutasyonlar ------------------------------------------------------
  const saveMutation = useMutation({
    mutationFn: (payload: { id: number | null; body: Record<string, unknown> }) =>
      payload.id === null
        ? post<PerformanceRecord>('/performance', payload.body)
        : patch<PerformanceRecord>(`/performance/${payload.id}`, payload.body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['performance'] })
      void queryClient.invalidateQueries({ queryKey: ['performance-summary'] })
      void queryClient.invalidateQueries({ queryKey: ['performance-personal-bests'] })
      toastSuccess(t('common.success'))
      closeModal()
    },
    onError: (error) => toastError(error),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => del(`/performance/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['performance'] })
      void queryClient.invalidateQueries({ queryKey: ['performance-summary'] })
      toastSuccess(t('common.success'))
      setDeleteTarget(null)
    },
    onError: (error) => toastError(error),
  })

  // --- Form yardımcıları ------------------------------------------------
  function closeModal() {
    setModalOpen(false)
    setEditingId(null)
    setFormErrors({})
    setForm(emptyForm())
  }

  function openCreate() {
    setForm(emptyForm())
    setEditingId(null)
    setFormErrors({})
    setModalOpen(true)
  }

  function openEdit(record: PerformanceRecord) {
    setForm({
      studentId: record.student_id,
      studentName: record.student_name ?? '',
      stroke: record.stroke,
      distance: String(record.distance_m),
      courseType: record.course_type,
      timeText: formatSwimTime(record.time_seconds),
      splitsText: record.splits.map((split) => formatSwimTime(split)).join(', '),
      strokeRate: record.stroke_rate !== null && record.stroke_rate !== undefined ? String(record.stroke_rate) : '',
      strokeCount:
        record.stroke_count !== null && record.stroke_count !== undefined ? String(record.stroke_count) : '',
      reactionTime:
        record.reaction_time !== null && record.reaction_time !== undefined ? String(record.reaction_time) : '',
      turnTime: record.turn_time !== null && record.turn_time !== undefined ? String(record.turn_time) : '',
      recordedDate: toISODate(record.recorded_date),
      isCompetition: record.is_competition,
      heartRate:
        record.heart_rate_avg !== null && record.heart_rate_avg !== undefined ? String(record.heart_rate_avg) : '',
      perceivedEffort:
        record.perceived_effort !== null && record.perceived_effort !== undefined
          ? String(record.perceived_effort)
          : '',
      notes: record.notes ?? '',
    })
    setEditingId(record.id)
    setFormErrors({})
    setModalOpen(true)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const errors: { student?: string; time?: string } = {}
    if (form.studentId === null) errors.student = t('common.required')

    const seconds = parseSwimTime(form.timeText)
    if (seconds === null || seconds <= 0) errors.time = t('performance.timeHint')

    setFormErrors(errors)
    if (seconds === null || Object.keys(errors).length > 0) return

    const splits = form.splitsText
      .split(',')
      .map((part) => parseSwimTime(part))
      .filter((split): split is number => split !== null && split > 0)

    const body: Record<string, unknown> = {
      stroke: form.stroke,
      distance_m: Number(form.distance),
      course_type: form.courseType,
      time_seconds: Number(seconds.toFixed(2)),
      splits,
      stroke_rate: numberOrNull(form.strokeRate),
      stroke_count: numberOrNull(form.strokeCount),
      reaction_time: numberOrNull(form.reactionTime),
      turn_time: numberOrNull(form.turnTime),
      recorded_date: form.recordedDate,
      is_competition: form.isCompetition,
      heart_rate_avg: numberOrNull(form.heartRate),
      perceived_effort: numberOrNull(form.perceivedEffort),
      notes: form.notes.trim() ? form.notes.trim() : null,
    }
    if (editingId === null) body.student_id = form.studentId

    saveMutation.mutate({ id: editingId, body })
  }

  const strokeOptions = catalogQuery.data?.strokes.map((item) => item.value) ?? FALLBACK_STROKES
  const distanceOptions = catalogQuery.data?.distances ?? FALLBACK_DISTANCES
  const courseTypes = catalogQuery.data?.course_types ?? [
    { value: 'short', label: t('pool.shortCourse') },
    { value: 'long', label: t('pool.longCourse') },
  ]

  const eventLabel = (distance: number, stroke: string) =>
    `${distance} m ${t(`performance.strokes.${stroke}`, stroke)}`

  const canWrite = can('performance:write')

  const tabs = [
    { id: 'records', label: t('competition.entries'), icon: <Timer className="h-4 w-4" /> },
    { id: 'analysis', label: t('performance.summary'), icon: <BarChart3 className="h-4 w-4" /> },
    { id: 'improvers', label: t('performance.topImprovers'), icon: <TrendingUp className="h-4 w-4" /> },
    { id: 'declining', label: t('performance.declining'), icon: <TrendingDown className="h-4 w-4" /> },
    { id: 'readiness', label: t('performance.readiness'), icon: <Gauge className="h-4 w-4" /> },
  ]

  const daySelector = (
    <select
      className="select w-auto py-1 text-xs"
      value={lookbackDays}
      onChange={(event: React.ChangeEvent<HTMLSelectElement>) => setLookbackDays(Number(event.target.value))}
      aria-label={t('statistics.period')}
    >
      <option value={30}>30</option>
      <option value={60}>60</option>
      <option value={90}>90</option>
      <option value={180}>180</option>
      <option value={365}>365</option>
    </select>
  )

  return (
    <>
      <PageHeader
        title={t('performance.title')}
        subtitle={t('statistics.subtitle')}
        icon={<Activity className="h-5 w-5" />}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={openCreate}>
              <Plus className="h-4 w-4" />
              {t('performance.newRecord')}
            </button>
          )
        }
      />

      <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as TabId)} />

      {/* ------------------------------------------------------------------ */}
      {/* Kayıtlar */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'records' && (
        <>
          <Card title={t('common.filters')} className="mb-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Field label={t('student.singular')}>
                <StudentPicker
                  value={filters.studentId}
                  label={filters.studentName}
                  onSelect={(id, name) => updateFilter({ studentId: id, studentName: name })}
                />
              </Field>
              <Field label={t('performance.stroke')}>
                <select
                  className="select"
                  value={filters.stroke}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                    updateFilter({ stroke: event.target.value })
                  }
                >
                  <option value="">{t('common.all')}</option>
                  {strokeOptions.map((stroke) => (
                    <option key={stroke} value={stroke}>
                      {t(`performance.strokes.${stroke}`, stroke)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('performance.distance')}>
                <select
                  className="select"
                  value={filters.distance}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                    updateFilter({ distance: event.target.value })
                  }
                >
                  <option value="">{t('common.all')}</option>
                  {distanceOptions.map((distance) => (
                    <option key={distance} value={distance}>
                      {distance} m
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('pool.courseType')}>
                <select
                  className="select"
                  value={filters.courseType}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                    updateFilter({ courseType: event.target.value })
                  }
                >
                  <option value="">{t('common.all')}</option>
                  {courseTypes.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('common.date')}>
                <input
                  type="date"
                  className="input"
                  value={filters.dateFrom}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    updateFilter({ dateFrom: event.target.value })
                  }
                />
              </Field>
              <Field label={t('common.date')}>
                <input
                  type="date"
                  className="input"
                  value={filters.dateTo}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    updateFilter({ dateTo: event.target.value })
                  }
                />
              </Field>
              <Field label={t('performance.isCompetition')}>
                <select
                  className="select"
                  value={filters.competition}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                    updateFilter({ competition: event.target.value })
                  }
                >
                  <option value="">{t('common.all')}</option>
                  <option value="true">{t('common.yes')}</option>
                  <option value="false">{t('common.no')}</option>
                </select>
              </Field>
              <div className="flex items-end">
                <button
                  type="button"
                  className="btn-secondary w-full"
                  onClick={() => {
                    setFilters(EMPTY_FILTERS)
                    setPage(1)
                  }}
                >
                  {t('common.clearFilters')}
                </button>
              </div>
            </div>
          </Card>

          <Card bodyClassName="p-0">
            {recordsQuery.isLoading ? (
              <LoadingState />
            ) : recordsQuery.error ? (
              <ErrorState error={recordsQuery.error} onRetry={() => void recordsQuery.refetch()} />
            ) : (recordsQuery.data?.items.length ?? 0) === 0 ? (
              <EmptyState title={t('performance.noRecords')} icon={<Timer className="h-6 w-6" />} />
            ) : (
              <>
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('common.date')}</th>
                      <th>{t('student.singular')}</th>
                      <th>{t('competition.events')}</th>
                      <th>{t('performance.timeSeconds')}</th>
                      <th className="hidden md:table-cell">{t('performance.pace100')}</th>
                      <th className="hidden lg:table-cell">{t('performance.speed')}</th>
                      <th className="hidden lg:table-cell">{t('performance.strokeCount')}</th>
                      <th>{t('common.status')}</th>
                      {canWrite && <th className="text-right">{t('common.actions')}</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {recordsQuery.data?.items.map((record) => (
                      <tr key={record.id}>
                        <td className="whitespace-nowrap">{formatDate(record.recorded_date)}</td>
                        <td className="font-medium text-slate-800 dark:text-slate-100">
                          {record.student_name ?? '—'}
                        </td>
                        <td className="whitespace-nowrap">
                          {eventLabel(record.distance_m, record.stroke)}
                          <span className="ml-1.5 text-xs text-slate-400">
                            {record.course_type === 'long' ? '50 m' : '25 m'}
                          </span>
                        </td>
                        <td className="whitespace-nowrap font-semibold tabular-nums">
                          {formatSwimTime(record.time_seconds)}
                        </td>
                        <td className="hidden whitespace-nowrap tabular-nums md:table-cell">
                          {record.pace_per_100m !== null && record.pace_per_100m !== undefined
                            ? formatSwimTime(record.pace_per_100m)
                            : '—'}
                        </td>
                        <td className="hidden whitespace-nowrap tabular-nums lg:table-cell">
                          {record.speed_ms !== null && record.speed_ms !== undefined
                            ? `${formatDecimal(record.speed_ms, 2)} m/s`
                            : '—'}
                        </td>
                        <td className="hidden tabular-nums lg:table-cell">
                          {record.stroke_count !== null && record.stroke_count !== undefined
                            ? formatNumber(record.stroke_count)
                            : '—'}
                        </td>
                        <td>
                          <div className="flex flex-wrap items-center gap-1">
                            {record.is_personal_best && (
                              <Badge tone="success">
                                <Trophy className="mr-1 inline h-3 w-3" />
                                {t('performance.personalBest')}
                              </Badge>
                            )}
                            {record.is_competition && <Badge tone="info">{t('competition.singular')}</Badge>}
                          </div>
                        </td>
                        {canWrite && (
                          <td>
                            <div className="flex items-center justify-end gap-1">
                              <button
                                type="button"
                                className="btn-ghost btn-sm"
                                onClick={() => openEdit(record)}
                                title={t('common.edit')}
                                aria-label={t('common.edit')}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                                onClick={() => setDeleteTarget(record)}
                                title={t('common.delete')}
                                aria-label={t('common.delete')}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </TableWrapper>
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={recordsQuery.data?.total ?? 0}
                  onPageChange={setPage}
                  onPageSizeChange={(size) => {
                    setPageSize(size)
                    setPage(1)
                  }}
                />
              </>
            )}
          </Card>
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Sporcu analizi */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'analysis' && (
        <>
          <Card className="mb-4">
            <div className="max-w-md">
              <Field label={t('student.singular')} required>
                <StudentPicker
                  value={analysisStudent.id}
                  label={analysisStudent.name}
                  onSelect={(id, name) => setAnalysisStudent({ id, name })}
                />
              </Field>
            </div>
          </Card>

          {analysisStudent.id === null ? (
            <EmptyState title={t('student.singular')} description={t('common.searchPlaceholder')} />
          ) : summaryQuery.isLoading ? (
            <LoadingState />
          ) : summaryQuery.error ? (
            <ErrorState error={summaryQuery.error} onRetry={() => void summaryQuery.refetch()} />
          ) : summaryQuery.data ? (
            <>
              <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label={t('common.total')}
                  value={formatNumber(summaryQuery.data.total_records)}
                  hint={`${formatNumber(summaryQuery.data.training_count)} / ${formatNumber(
                    summaryQuery.data.competition_count,
                  )}`}
                  icon={<Timer className="h-5 w-5" />}
                  tone="brand"
                />
                <StatCard
                  label={t('performance.personalBests')}
                  value={formatNumber(summaryQuery.data.personal_best_count)}
                  icon={<Trophy className="h-5 w-5" />}
                  tone="success"
                />
                <StatCard
                  label={t('performance.strongestStroke')}
                  value={
                    summaryQuery.data.strongest_stroke
                      ? t(`performance.strokes.${summaryQuery.data.strongest_stroke}`, summaryQuery.data.strongest_stroke)
                      : '—'
                  }
                  hint={
                    summaryQuery.data.weakest_stroke
                      ? `${t('performance.weakestStroke')}: ${t(
                          `performance.strokes.${summaryQuery.data.weakest_stroke}`,
                          summaryQuery.data.weakest_stroke,
                        )}`
                      : undefined
                  }
                  icon={<BarChart3 className="h-5 w-5" />}
                />
                <StatCard
                  label={t('performance.improvementPercent')}
                  value={
                    summaryQuery.data.overall_improvement_percent !== null &&
                    summaryQuery.data.overall_improvement_percent !== undefined
                      ? formatPercent(summaryQuery.data.overall_improvement_percent)
                      : '—'
                  }
                  hint={
                    summaryQuery.data.first_record_date && summaryQuery.data.last_record_date
                      ? `${formatDate(summaryQuery.data.first_record_date)} – ${formatDate(
                          summaryQuery.data.last_record_date,
                        )}`
                      : undefined
                  }
                  icon={<TrendingUp className="h-5 w-5" />}
                  tone={
                    (summaryQuery.data.overall_improvement_percent ?? 0) > 0 ? 'success' : 'neutral'
                  }
                />
              </div>

              {summaryQuery.data.events.length === 0 ? (
                <Card>
                  <EmptyState title={t('performance.noRecords')} />
                </Card>
              ) : (
                <div className="grid gap-4 xl:grid-cols-2">
                  {summaryQuery.data.events.map((analysis) => (
                    <EventAnalysisCard
                      key={`${analysis.stroke}-${analysis.distance_m}-${analysis.course_type}`}
                      analysis={analysis}
                    />
                  ))}
                </div>
              )}

              <Card title={t('performance.personalBests')} className="mt-4" bodyClassName="p-0">
                {personalBestsQuery.isLoading ? (
                  <LoadingState />
                ) : (personalBestsQuery.data?.length ?? 0) === 0 ? (
                  <EmptyState title={t('common.noData')} icon={<Trophy className="h-6 w-6" />} />
                ) : (
                  <TableWrapper>
                    <thead>
                      <tr>
                        <th>{t('competition.events')}</th>
                        <th>{t('pool.courseType')}</th>
                        <th>{t('performance.bestTime')}</th>
                        <th>{t('common.date')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {personalBestsQuery.data?.map((best) => (
                        <tr key={best.id}>
                          <td>{eventLabel(best.distance_m, best.stroke)}</td>
                          <td className="text-xs text-slate-500 dark:text-slate-400">
                            {best.course_type === 'long' ? t('pool.longCourse') : t('pool.shortCourse')}
                          </td>
                          <td className="font-semibold tabular-nums">{formatSwimTime(best.time_seconds)}</td>
                          <td className="whitespace-nowrap">{formatDate(best.achieved_date)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </TableWrapper>
                )}
              </Card>
            </>
          ) : null}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* En çok gelişenler */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'improvers' && (
        <Card title={t('performance.topImprovers')} actions={daySelector} bodyClassName="p-0">
          {improversQuery.isLoading ? (
            <LoadingState />
          ) : improversQuery.error ? (
            <ErrorState error={improversQuery.error} onRetry={() => void improversQuery.refetch()} />
          ) : (improversQuery.data?.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<TrendingUp className="h-6 w-6" />} />
          ) : (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('student.singular')}</th>
                  <th>{t('competition.events')}</th>
                  <th>{t('performance.bestTime')}</th>
                  <th>{t('performance.improvement')}</th>
                  <th>{t('performance.improvementPercent')}</th>
                  <th className="hidden md:table-cell">{t('common.total')}</th>
                </tr>
              </thead>
              <tbody>
                {improversQuery.data?.map((row) => (
                  <tr key={`${row.student_id}-${row.stroke}-${row.distance_m}`}>
                    <td className="font-medium text-slate-800 dark:text-slate-100">{row.student_name}</td>
                    <td className="whitespace-nowrap">{eventLabel(row.distance_m, row.stroke)}</td>
                    <td className="whitespace-nowrap tabular-nums">
                      {formatSwimTime(row.first_time)} → {formatSwimTime(row.last_time)}
                    </td>
                    <td className="whitespace-nowrap tabular-nums text-emerald-600 dark:text-emerald-400">
                      {formatTimeDelta(-Math.abs(row.improvement_seconds))}
                    </td>
                    <td className="tabular-nums">{formatPercent(row.improvement_percent)}</td>
                    <td className="hidden md:table-cell">{formatNumber(row.record_count)}</td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Performansı düşenler */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'declining' && (
        <Card title={t('performance.declining')} actions={daySelector} bodyClassName="p-0">
          {decliningQuery.isLoading ? (
            <LoadingState />
          ) : decliningQuery.error ? (
            <ErrorState error={decliningQuery.error} onRetry={() => void decliningQuery.refetch()} />
          ) : (decliningQuery.data?.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<TrendingDown className="h-6 w-6" />} />
          ) : (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('student.singular')}</th>
                  <th>{t('competition.events')}</th>
                  <th>{t('performance.meanTime')}</th>
                  <th>{t('performance.improvement')}</th>
                  <th>{t('performance.improvementPercent')}</th>
                  <th className="hidden md:table-cell">{t('common.date')}</th>
                </tr>
              </thead>
              <tbody>
                {decliningQuery.data?.map((row) => (
                  <tr key={`${row.student_id}-${row.stroke}-${row.distance_m}`}>
                    <td className="font-medium text-slate-800 dark:text-slate-100">{row.student_name}</td>
                    <td className="whitespace-nowrap">{eventLabel(row.distance_m, row.stroke)}</td>
                    <td className="whitespace-nowrap tabular-nums">
                      {formatSwimTime(row.baseline_mean)} → {formatSwimTime(row.recent_mean)}
                    </td>
                    <td className="whitespace-nowrap tabular-nums text-rose-600 dark:text-rose-400">
                      {formatTimeDelta(Math.abs(row.decline_seconds))}
                    </td>
                    <td className="tabular-nums">{formatPercent(row.decline_percent)}</td>
                    <td className="hidden whitespace-nowrap md:table-cell">
                      {formatDate(row.last_record_date)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Yarışma hazırlığı */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'readiness' && (
        <>
          {readinessQuery.data && (
            <div className="mb-4">
              <Alert tone="info" title={t('performance.readinessScore')}>
                {i18n.language === 'tr' ? readinessQuery.data.note_tr : readinessQuery.data.note_en}
              </Alert>
            </div>
          )}
          <Card title={t('performance.readiness')} actions={daySelector} bodyClassName="p-0">
            {readinessQuery.isLoading ? (
              <LoadingState />
            ) : readinessQuery.error ? (
              <ErrorState error={readinessQuery.error} onRetry={() => void readinessQuery.refetch()} />
            ) : (readinessQuery.data?.rows.length ?? 0) === 0 ? (
              <EmptyState title={t('common.noData')} icon={<Gauge className="h-6 w-6" />} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('student.singular')}</th>
                    <th>{t('competition.events')}</th>
                    <th>{t('performance.bestTime')}</th>
                    <th>{t('performance.meanTime')}</th>
                    <th>{t('performance.trend')}</th>
                    <th className="hidden md:table-cell">{t('common.total')}</th>
                    <th className="w-48">{t('performance.readinessScore')}</th>
                  </tr>
                </thead>
                <tbody>
                  {readinessQuery.data?.rows.map((row) => (
                    <tr key={`${row.student_id}-${row.stroke}-${row.distance_m}`}>
                      <td className="font-medium text-slate-800 dark:text-slate-100">{row.student_name}</td>
                      <td className="whitespace-nowrap">{eventLabel(row.distance_m, row.stroke)}</td>
                      <td className="whitespace-nowrap tabular-nums">{row.best_time_formatted}</td>
                      <td className="whitespace-nowrap tabular-nums">{row.recent_mean_formatted}</td>
                      <td>
                        <Badge
                          tone={
                            row.trend === 'improving' ? 'success' : row.trend === 'declining' ? 'danger' : 'neutral'
                          }
                        >
                          {t(`performance.trends.${row.trend}`, row.trend)}
                        </Badge>
                      </td>
                      <td className="hidden md:table-cell">{formatNumber(row.records_last_period)}</td>
                      <td>
                        <ProgressBar
                          value={row.readiness_score}
                          tone={
                            row.readiness_score >= 75 ? 'success' : row.readiness_score >= 50 ? 'brand' : 'warning'
                          }
                          showLabel
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </Card>
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Yeni / düzenle derece modalı */}
      {/* ------------------------------------------------------------------ */}
      <Modal
        open={modalOpen}
        onClose={closeModal}
        title={editingId === null ? t('performance.newRecord') : t('common.edit')}
        size="lg"
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={closeModal}>
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              form="performance-form"
              className="btn-primary"
              disabled={saveMutation.isPending}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <form id="performance-form" onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-2">
          <Field label={t('student.singular')} required error={formErrors.student} className="sm:col-span-2">
            {editingId === null ? (
              <StudentPicker
                value={form.studentId}
                label={form.studentName}
                onSelect={(id, name) =>
                  setForm((current) => ({ ...current, studentId: id, studentName: name }))
                }
              />
            ) : (
              <input className="input" value={form.studentName} disabled readOnly />
            )}
          </Field>

          <Field label={t('performance.stroke')} required>
            <select
              className="select"
              value={form.stroke}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setForm((current) => ({ ...current, stroke: event.target.value }))
              }
            >
              {strokeOptions.map((stroke) => (
                <option key={stroke} value={stroke}>
                  {t(`performance.strokes.${stroke}`, stroke)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('performance.distance')} required>
            <select
              className="select"
              value={form.distance}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setForm((current) => ({ ...current, distance: event.target.value }))
              }
            >
              {distanceOptions.map((distance) => (
                <option key={distance} value={distance}>
                  {distance} m
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('pool.courseType')} required>
            <select
              className="select"
              value={form.courseType}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setForm((current) => ({ ...current, courseType: event.target.value }))
              }
            >
              {courseTypes.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </Field>

          <Field
            label={t('performance.timeSeconds')}
            required
            error={formErrors.time}
            hint={t('performance.timeHint')}
          >
            <input
              className="input"
              value={form.timeText}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, timeText: event.target.value }))
              }
              placeholder="1:35.12"
            />
          </Field>

          <Field label={t('performance.splits')} hint="25.10, 27.40" className="sm:col-span-2">
            <input
              className="input"
              value={form.splitsText}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, splitsText: event.target.value }))
              }
            />
          </Field>

          <Field label={t('performance.strokeRate')}>
            <input
              type="number"
              step="0.1"
              min="0"
              max="200"
              className="input"
              value={form.strokeRate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, strokeRate: event.target.value }))
              }
            />
          </Field>

          <Field label={t('performance.strokeCount')}>
            <input
              type="number"
              min="0"
              max="1000"
              className="input"
              value={form.strokeCount}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, strokeCount: event.target.value }))
              }
            />
          </Field>

          <Field label={t('performance.reactionTime')}>
            <input
              type="number"
              step="0.01"
              min="0"
              max="10"
              className="input"
              value={form.reactionTime}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, reactionTime: event.target.value }))
              }
            />
          </Field>

          <Field label={t('performance.turnTime')}>
            <input
              type="number"
              step="0.01"
              min="0"
              max="60"
              className="input"
              value={form.turnTime}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, turnTime: event.target.value }))
              }
            />
          </Field>

          <Field label={t('performance.recordedDate')} required>
            <input
              type="date"
              className="input"
              value={form.recordedDate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, recordedDate: event.target.value }))
              }
            />
          </Field>

          <Field label={t('performance.heartRate')}>
            <input
              type="number"
              min="30"
              max="240"
              className="input"
              value={form.heartRate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, heartRate: event.target.value }))
              }
            />
          </Field>

          <Field label={t('performance.perceivedEffort')}>
            <input
              type="number"
              min="1"
              max="10"
              className="input"
              value={form.perceivedEffort}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setForm((current) => ({ ...current, perceivedEffort: event.target.value }))
              }
            />
          </Field>

          <div className="flex items-center sm:col-span-2">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
              <input
                type="checkbox"
                checked={form.isCompetition}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setForm((current) => ({ ...current, isCompetition: event.target.checked }))
                }
              />
              {t('performance.isCompetition')}
            </label>
          </div>

          <Field label={t('common.notes')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={2}
              value={form.notes}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setForm((current) => ({ ...current, notes: event.target.value }))
              }
            />
          </Field>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id)
        }}
        title={t('common.delete')}
        message={
          deleteTarget
            ? `${deleteTarget.student_name ?? ''} · ${eventLabel(
                deleteTarget.distance_m,
                deleteTarget.stroke,
              )} · ${formatSwimTime(deleteTarget.time_seconds)}`
            : ''
        }
        confirmLabel={t('common.delete')}
        loading={deleteMutation.isPending}
      />
    </>
  )
}
