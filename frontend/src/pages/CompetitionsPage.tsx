/** Yarışma, kulüp rekoru ve madalya yönetimi / Competition, club record and medal management. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Award, CalendarDays, ListOrdered, MapPin, Medal, Plus, Shuffle, Trash2, Trophy, X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  Alert, Badge, Card, ConfirmDialog, EmptyState, ErrorState, Field, LoadingState, Modal,
  PageHeader, Pagination, StatCard, TableWrapper, Tabs, type BadgeTone,
} from '@/components/ui'
import { del, get, patch, post } from '@/lib/api'
import {
  formatDate, formatNumber, formatSwimTime, formatTimeDelta, parseSwimTime, toISODate,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type { ClubRecord, Competition, Page, Student } from '@/lib/types'

// ---------------------------------------------------------------------------
// Tipler ve sabitler
// ---------------------------------------------------------------------------
type TabId = 'list' | 'records' | 'medals'
type TimeFilter = 'all' | 'upcoming' | 'past'

interface MedalAthlete {
  student_id: number
  name: string
  gold: number
  silver: number
  bronze: number
  total: number
}

interface MedalSummary {
  totals: { gold: number; silver: number; bronze: number }
  total_medals: number
  athletes: MedalAthlete[]
}

interface HeatSheetLane {
  lane_number: number
  student_id?: number | null
  student_name?: string | null
  seed_time?: number | null
  formatted_seed?: string | null
}

interface HeatSheet {
  event_id: number
  event_name: string
  heat_number: number
  lanes: HeatSheetLane[]
}

interface ResultRow {
  rank: number
  student_id: number
  student_name?: string | null
  time: string
  time_seconds: number
  seed_time: string
  improvement?: number | null
  medal?: string | null
  is_personal_best: boolean
  is_club_record: boolean
}

interface ResultEvent {
  event_id: number
  event_name: string
  gender_category: string
  age_category?: string | null
  results: ResultRow[]
  disqualified: Array<{ student_name?: string | null; reason?: string | null }>
}

interface CompetitionResults {
  summary: { event_count: number; entry_count: number; personal_bests: number; club_records: number }
  events: ResultEvent[]
}

interface CompetitionFormState {
  name: string
  location: string
  organizer: string
  level: string
  courseType: string
  startDate: string
  endDate: string
  registrationDeadline: string
  description: string
}

interface EventFormState {
  stroke: string
  distance: string
  genderCategory: string
  ageCategory: string
  order: string
  scheduledDate: string
}

interface ResultFormState {
  timeText: string
  rank: string
  medal: string
  disqualified: boolean
  dqReason: string
}

const STROKES = ['freestyle', 'backstroke', 'breaststroke', 'butterfly', 'medley']
const DISTANCES = [25, 50, 100, 200, 400, 800, 1500]
const LEVELS = ['club', 'local', 'regional', 'national', 'international']
const GENDER_CATEGORIES = ['mixed', 'female', 'male']
const MEDALS = ['gold', 'silver', 'bronze']

function emptyCompetitionForm(): CompetitionFormState {
  const today = toISODate(new Date())
  return {
    name: '',
    location: '',
    organizer: '',
    level: 'club',
    courseType: 'short',
    startDate: today,
    endDate: today,
    registrationDeadline: '',
    description: '',
  }
}

function emptyEventForm(): EventFormState {
  return {
    stroke: 'freestyle',
    distance: '50',
    genderCategory: 'mixed',
    ageCategory: '',
    order: '1',
    scheduledDate: '',
  }
}

const EMPTY_RESULT_FORM: ResultFormState = {
  timeText: '',
  rank: '',
  medal: '',
  disqualified: false,
  dqReason: '',
}

function levelTone(level: string): BadgeTone {
  if (level === 'international') return 'success'
  if (level === 'national') return 'warning'
  if (level === 'regional') return 'info'
  return 'neutral'
}

function medalTone(medal: string): BadgeTone {
  if (medal === 'gold') return 'warning'
  if (medal === 'bronze') return 'danger'
  return 'neutral'
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
// Sayfa
// ---------------------------------------------------------------------------
export default function CompetitionsPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()
  const canWrite = can('competition:write')

  const [tab, setTab] = useState<TabId>('list')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all')
  const [year, setYear] = useState('')

  // Yeni yarışma
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<CompetitionFormState>(emptyCompetitionForm)
  const [createErrors, setCreateErrors] = useState<{ name?: string }>({})

  // Detay
  const [detailId, setDetailId] = useState<number | null>(null)
  const [detailView, setDetailView] = useState<'events' | 'results'>('events')
  const [eventFormOpen, setEventFormOpen] = useState(false)
  const [eventForm, setEventForm] = useState<EventFormState>(emptyEventForm)
  const [entryEventId, setEntryEventId] = useState<number | null>(null)
  const [entryForm, setEntryForm] = useState<{ studentId: number | null; studentName: string; seedText: string }>({
    studentId: null,
    studentName: '',
    seedText: '',
  })
  const [resultEntryId, setResultEntryId] = useState<number | null>(null)
  const [resultForm, setResultForm] = useState<ResultFormState>(EMPTY_RESULT_FORM)
  const [resultError, setResultError] = useState<string | undefined>(undefined)
  const [heats, setHeats] = useState<Record<number, HeatSheet[]>>({})

  const [confirmTarget, setConfirmTarget] = useState<
    { kind: 'competition' | 'event' | 'entry'; id: number; label: string } | null
  >(null)

  const currentYear = new Date().getFullYear()
  const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear + 1 - index)
  const today = toISODate(new Date())

  // --- Sorgular ---------------------------------------------------------
  const listQuery = useQuery({
    queryKey: ['competitions', page, pageSize, timeFilter, year],
    queryFn: () =>
      get<Page<Competition>>('/competitions', {
        page,
        page_size: pageSize,
        upcoming_only: timeFilter === 'upcoming' ? true : undefined,
        year: year || undefined,
      }),
    enabled: tab === 'list',
  })

  const recordsQuery = useQuery({
    queryKey: ['club-records'],
    queryFn: () => get<ClubRecord[]>('/competitions/records'),
    enabled: tab === 'records',
  })

  const medalsQuery = useQuery({
    queryKey: ['medal-summary', year],
    queryFn: () => get<MedalSummary>('/competitions/medals/summary', { year: year || undefined }),
    enabled: tab === 'medals',
  })

  const detailQuery = useQuery({
    queryKey: ['competition', detailId],
    queryFn: () => get<Competition>(`/competitions/${detailId}`),
    enabled: detailId !== null,
  })

  const resultsQuery = useQuery({
    queryKey: ['competition-results', detailId],
    queryFn: () => get<CompetitionResults>(`/competitions/${detailId}/results`),
    enabled: detailId !== null && detailView === 'results',
  })

  // --- Mutasyonlar ------------------------------------------------------
  function refreshDetail() {
    void queryClient.invalidateQueries({ queryKey: ['competition', detailId] })
    void queryClient.invalidateQueries({ queryKey: ['competition-results', detailId] })
    void queryClient.invalidateQueries({ queryKey: ['competitions'] })
  }

  const createCompetitionMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => post<Competition>('/competitions', body),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: ['competitions'] })
      toastSuccess(t('common.success'), created.name)
      setCreateOpen(false)
      setCreateForm(emptyCompetitionForm())
    },
    onError: (error) => toastError(error),
  })

  const deleteCompetitionMutation = useMutation({
    mutationFn: (id: number) => del(`/competitions/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['competitions'] })
      toastSuccess(t('common.success'))
      setConfirmTarget(null)
      setDetailId(null)
    },
    onError: (error) => toastError(error),
  })

  const createEventMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => post('/competitions/events', body),
    onSuccess: () => {
      refreshDetail()
      toastSuccess(t('common.success'))
      setEventFormOpen(false)
      setEventForm(emptyEventForm())
    },
    onError: (error) => toastError(error),
  })

  const deleteEventMutation = useMutation({
    mutationFn: (id: number) => del(`/competitions/events/${id}`),
    onSuccess: () => {
      refreshDetail()
      toastSuccess(t('common.success'))
      setConfirmTarget(null)
    },
    onError: (error) => toastError(error),
  })

  const createEntryMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => post('/competitions/entries', body),
    onSuccess: () => {
      refreshDetail()
      toastSuccess(t('common.success'))
      setEntryEventId(null)
      setEntryForm({ studentId: null, studentName: '', seedText: '' })
    },
    onError: (error) => toastError(error),
  })

  const deleteEntryMutation = useMutation({
    mutationFn: (id: number) => del(`/competitions/entries/${id}`),
    onSuccess: () => {
      refreshDetail()
      toastSuccess(t('common.success'))
      setConfirmTarget(null)
    },
    onError: (error) => toastError(error),
  })

  const saveResultMutation = useMutation({
    mutationFn: (payload: { id: number; body: Record<string, unknown> }) =>
      patch(`/competitions/entries/${payload.id}/result`, payload.body),
    onSuccess: () => {
      refreshDetail()
      void queryClient.invalidateQueries({ queryKey: ['club-records'] })
      void queryClient.invalidateQueries({ queryKey: ['medal-summary'] })
      toastSuccess(t('common.success'))
      setResultEntryId(null)
      setResultForm(EMPTY_RESULT_FORM)
    },
    onError: (error) => toastError(error),
  })

  const seedHeatsMutation = useMutation({
    mutationFn: (eventId: number) =>
      post<HeatSheet[]>(`/competitions/events/${eventId}/seed-heats`, undefined, { lanes_per_heat: 6 }),
    onSuccess: (sheets, eventId) => {
      setHeats((current) => ({ ...current, [eventId]: sheets }))
      refreshDetail()
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  // --- Yardımcılar ------------------------------------------------------
  const eventLabel = (distance: number, stroke: string) =>
    `${distance} m ${t(`performance.strokes.${stroke}`, stroke)}`

  const genderLabel = (value: string) => (value === 'mixed' ? t('common.all') : t(`gender.${value}`, value))

  function closeDetail() {
    setDetailId(null)
    setDetailView('events')
    setEventFormOpen(false)
    setEntryEventId(null)
    setResultEntryId(null)
    setResultError(undefined)
    setHeats({})
  }

  function submitCompetition(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!createForm.name.trim()) {
      setCreateErrors({ name: t('common.required') })
      return
    }
    setCreateErrors({})
    createCompetitionMutation.mutate({
      name: createForm.name.trim(),
      location: createForm.location.trim() || null,
      organizer: createForm.organizer.trim() || null,
      level: createForm.level,
      course_type: createForm.courseType,
      start_date: createForm.startDate,
      end_date: createForm.endDate,
      registration_deadline: createForm.registrationDeadline || null,
      description: createForm.description.trim() || null,
    })
  }

  function submitEvent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (detailId === null) return
    createEventMutation.mutate({
      competition_id: detailId,
      stroke: eventForm.stroke,
      distance_m: Number(eventForm.distance),
      gender_category: eventForm.genderCategory,
      age_category: eventForm.ageCategory.trim() || null,
      event_order: Number(eventForm.order) || 1,
      scheduled_date: eventForm.scheduledDate || null,
    })
  }

  function submitEntry(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (entryEventId === null || entryForm.studentId === null) return
    const seed = parseSwimTime(entryForm.seedText)
    createEntryMutation.mutate({
      event_id: entryEventId,
      student_id: entryForm.studentId,
      seed_time_seconds: seed !== null && seed > 0 ? Number(seed.toFixed(2)) : null,
    })
  }

  function submitResult(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (resultEntryId === null) return
    const seconds = parseSwimTime(resultForm.timeText)
    if (!resultForm.disqualified && (seconds === null || seconds <= 0)) {
      setResultError(t('performance.timeHint'))
      return
    }
    setResultError(undefined)
    saveResultMutation.mutate({
      id: resultEntryId,
      body: {
        result_time_seconds:
          !resultForm.disqualified && seconds !== null ? Number(seconds.toFixed(2)) : null,
        rank: resultForm.rank.trim() ? Number(resultForm.rank) : null,
        medal: resultForm.medal || null,
        is_disqualified: resultForm.disqualified,
        disqualification_reason: resultForm.disqualified ? resultForm.dqReason.trim() || null : null,
      },
    })
  }

  function handleConfirm() {
    if (!confirmTarget) return
    if (confirmTarget.kind === 'competition') deleteCompetitionMutation.mutate(confirmTarget.id)
    else if (confirmTarget.kind === 'event') deleteEventMutation.mutate(confirmTarget.id)
    else deleteEntryMutation.mutate(confirmTarget.id)
  }

  // "Geçmiş" filtresi sunucuda bulunmadığı için sayfa içeriği üzerinde uygulanır
  const competitions = (listQuery.data?.items ?? []).filter(
    (competition) => timeFilter !== 'past' || competition.end_date < today,
  )

  const tabs = [
    { id: 'list', label: t('competition.title'), icon: <Trophy className="h-4 w-4" /> },
    { id: 'records', label: t('competition.clubRecords'), icon: <Award className="h-4 w-4" /> },
    { id: 'medals', label: t('competition.medals'), icon: <Medal className="h-4 w-4" /> },
  ]

  const detail = detailQuery.data

  return (
    <>
      <PageHeader
        title={t('competition.title')}
        subtitle={t('statistics.subtitle')}
        icon={<Trophy className="h-5 w-5" />}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" />
              {t('competition.new')}
            </button>
          )
        }
      />

      <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as TabId)} />

      {/* ------------------------------------------------------------------ */}
      {/* Yarışmalar */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'list' && (
        <>
          <Card className="mb-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label={t('common.filter')}>
                <select
                  className="select"
                  value={timeFilter}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                    setTimeFilter(event.target.value as TimeFilter)
                    setPage(1)
                  }}
                >
                  <option value="all">{t('common.all')}</option>
                  <option value="upcoming">{t('dashboard.upcomingCompetitions')}</option>
                  <option value="past">{t('common.previous')}</option>
                </select>
              </Field>
              <Field label={t('common.date')}>
                <select
                  className="select"
                  value={year}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                    setYear(event.target.value)
                    setPage(1)
                  }}
                >
                  <option value="">{t('common.all')}</option>
                  {yearOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="flex items-end">
                <button
                  type="button"
                  className="btn-secondary w-full"
                  onClick={() => {
                    setTimeFilter('all')
                    setYear('')
                    setPage(1)
                  }}
                >
                  {t('common.clearFilters')}
                </button>
              </div>
            </div>
          </Card>

          {listQuery.isLoading ? (
            <LoadingState />
          ) : listQuery.error ? (
            <ErrorState error={listQuery.error} onRetry={() => void listQuery.refetch()} />
          ) : competitions.length === 0 ? (
            <Card>
              <EmptyState title={t('common.noData')} icon={<Trophy className="h-6 w-6" />} />
            </Card>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {competitions.map((competition) => (
                  <div key={competition.id} className="card card-hover flex flex-col p-4">
                    <div className="flex items-start justify-between gap-2">
                      <button
                        type="button"
                        className="min-w-0 flex-1 text-left"
                        onClick={() => {
                          setDetailId(competition.id)
                          setDetailView('events')
                        }}
                      >
                        <h3 className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {competition.name}
                        </h3>
                      </button>
                      <Badge tone={levelTone(competition.level)}>
                        {t(`competition.levels.${competition.level}`, competition.level)}
                      </Badge>
                    </div>

                    <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                      <CalendarDays className="h-3.5 w-3.5 shrink-0" />
                      {formatDate(competition.start_date)} – {formatDate(competition.end_date)}
                    </p>
                    {competition.location && (
                      <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                        <MapPin className="h-3.5 w-3.5 shrink-0" />
                        <span className="truncate">{competition.location}</span>
                      </p>
                    )}

                    <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                      <div className="rounded-lg bg-slate-50 py-1.5 dark:bg-slate-800/60">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {formatNumber(competition.event_count)}
                        </p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                          {t('competition.events')}
                        </p>
                      </div>
                      <div className="rounded-lg bg-slate-50 py-1.5 dark:bg-slate-800/60">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {formatNumber(competition.entry_count)}
                        </p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                          {t('competition.entries')}
                        </p>
                      </div>
                      <div className="rounded-lg bg-slate-50 py-1.5 dark:bg-slate-800/60">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {formatNumber(competition.medal_count)}
                        </p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                          {t('competition.medals')}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center justify-between gap-2">
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        onClick={() => {
                          setDetailId(competition.id)
                          setDetailView('events')
                        }}
                      >
                        {t('common.details')}
                      </button>
                      <div className="flex items-center gap-2">
                        {competition.start_date >= today && (
                          <Badge tone="info">{t('lesson.statuses.scheduled')}</Badge>
                        )}
                        {competition.is_completed && (
                          <Badge tone="success">{t('lesson.statuses.completed')}</Badge>
                        )}
                        {canWrite && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            title={t('common.delete')}
                            aria-label={t('common.delete')}
                            onClick={() =>
                              setConfirmTarget({
                                kind: 'competition',
                                id: competition.id,
                                label: competition.name,
                              })
                            }
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="card mt-4">
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={listQuery.data?.total ?? 0}
                  onPageChange={setPage}
                  onPageSizeChange={(size) => {
                    setPageSize(size)
                    setPage(1)
                  }}
                />
              </div>
            </>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Kulüp rekorları */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'records' && (
        <Card title={t('competition.clubRecords')} bodyClassName="p-0">
          {recordsQuery.isLoading ? (
            <LoadingState />
          ) : recordsQuery.error ? (
            <ErrorState error={recordsQuery.error} onRetry={() => void recordsQuery.refetch()} />
          ) : (recordsQuery.data?.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<Award className="h-6 w-6" />} />
          ) : (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('competition.events')}</th>
                  <th>{t('pool.courseType')}</th>
                  <th>{t('competition.genderCategory')}</th>
                  <th className="hidden md:table-cell">{t('competition.ageCategory')}</th>
                  <th>{t('student.singular')}</th>
                  <th>{t('performance.bestTime')}</th>
                  <th className="hidden lg:table-cell">{t('common.date')}</th>
                  <th className="hidden lg:table-cell">{t('competition.singular')}</th>
                </tr>
              </thead>
              <tbody>
                {recordsQuery.data?.map((record: ClubRecord) => (
                  <tr key={record.id}>
                    <td className="whitespace-nowrap">{eventLabel(record.distance_m, record.stroke)}</td>
                    <td className="text-xs text-slate-500 dark:text-slate-400">
                      {record.course_type === 'long' ? t('pool.longCourse') : t('pool.shortCourse')}
                    </td>
                    <td>{genderLabel(record.gender_category)}</td>
                    <td className="hidden md:table-cell">{record.age_category}</td>
                    <td className="font-medium text-slate-800 dark:text-slate-100">{record.holder_name}</td>
                    <td className="whitespace-nowrap font-semibold tabular-nums">{record.formatted_time}</td>
                    <td className="hidden whitespace-nowrap lg:table-cell">
                      {formatDate(record.achieved_date)}
                    </td>
                    <td className="hidden text-xs text-slate-500 lg:table-cell dark:text-slate-400">
                      {record.competition_name ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Madalya tablosu */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'medals' && (
        <>
          <Card className="mb-4">
            <div className="max-w-xs">
              <Field label={t('common.date')}>
                <select
                  className="select"
                  value={year}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) => setYear(event.target.value)}
                >
                  <option value="">{t('common.all')}</option>
                  {yearOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          </Card>

          {medalsQuery.isLoading ? (
            <LoadingState />
          ) : medalsQuery.error ? (
            <ErrorState error={medalsQuery.error} onRetry={() => void medalsQuery.refetch()} />
          ) : medalsQuery.data ? (
            <>
              <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label={t('competition.medalTypes.gold')}
                  value={formatNumber(medalsQuery.data.totals.gold)}
                  icon={<Medal className="h-5 w-5" />}
                  tone="warning"
                />
                <StatCard
                  label={t('competition.medalTypes.silver')}
                  value={formatNumber(medalsQuery.data.totals.silver)}
                  icon={<Medal className="h-5 w-5" />}
                  tone="neutral"
                />
                <StatCard
                  label={t('competition.medalTypes.bronze')}
                  value={formatNumber(medalsQuery.data.totals.bronze)}
                  icon={<Medal className="h-5 w-5" />}
                  tone="danger"
                />
                <StatCard
                  label={t('competition.medals')}
                  value={formatNumber(medalsQuery.data.total_medals)}
                  icon={<Trophy className="h-5 w-5" />}
                  tone="brand"
                />
              </div>

              <Card title={t('competition.medals')} bodyClassName="p-0">
                {medalsQuery.data.athletes.length === 0 ? (
                  <EmptyState title={t('common.noData')} icon={<Medal className="h-6 w-6" />} />
                ) : (
                  <TableWrapper>
                    <thead>
                      <tr>
                        <th className="w-12">#</th>
                        <th>{t('student.singular')}</th>
                        <th>{t('competition.medalTypes.gold')}</th>
                        <th>{t('competition.medalTypes.silver')}</th>
                        <th>{t('competition.medalTypes.bronze')}</th>
                        <th>{t('common.total')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {medalsQuery.data.athletes.map((athlete, index) => (
                        <tr key={athlete.student_id}>
                          <td className="text-slate-400">{index + 1}</td>
                          <td className="font-medium text-slate-800 dark:text-slate-100">{athlete.name}</td>
                          <td className="tabular-nums">{formatNumber(athlete.gold)}</td>
                          <td className="tabular-nums">{formatNumber(athlete.silver)}</td>
                          <td className="tabular-nums">{formatNumber(athlete.bronze)}</td>
                          <td className="font-semibold tabular-nums">{formatNumber(athlete.total)}</td>
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
      {/* Yeni yarışma modalı */}
      {/* ------------------------------------------------------------------ */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title={t('competition.new')}
        size="lg"
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setCreateOpen(false)}>
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              form="competition-form"
              className="btn-primary"
              disabled={createCompetitionMutation.isPending}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <form id="competition-form" onSubmit={submitCompetition} className="grid gap-3 sm:grid-cols-2">
          <Field label={t('common.name')} required error={createErrors.name} className="sm:col-span-2">
            <input
              className="input"
              value={createForm.name}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setCreateForm((current) => ({ ...current, name: event.target.value }))
              }
            />
          </Field>
          <Field label={t('pool.location')}>
            <input
              className="input"
              value={createForm.location}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setCreateForm((current) => ({ ...current, location: event.target.value }))
              }
            />
          </Field>
          <Field label={t('competition.organizer')}>
            <input
              className="input"
              value={createForm.organizer}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setCreateForm((current) => ({ ...current, organizer: event.target.value }))
              }
            />
          </Field>
          <Field label={t('competition.level')} required>
            <select
              className="select"
              value={createForm.level}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setCreateForm((current) => ({ ...current, level: event.target.value }))
              }
            >
              {LEVELS.map((level) => (
                <option key={level} value={level}>
                  {t(`competition.levels.${level}`, level)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('pool.courseType')} required>
            <select
              className="select"
              value={createForm.courseType}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setCreateForm((current) => ({ ...current, courseType: event.target.value }))
              }
            >
              <option value="short">{t('pool.shortCourse')}</option>
              <option value="long">{t('pool.longCourse')}</option>
            </select>
          </Field>
          <Field label={t('competition.startDate')} required>
            <input
              type="date"
              required
              className="input"
              value={createForm.startDate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setCreateForm((current) => ({ ...current, startDate: event.target.value }))
              }
            />
          </Field>
          <Field label={t('competition.endDate')} required>
            <input
              type="date"
              required
              className="input"
              value={createForm.endDate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setCreateForm((current) => ({ ...current, endDate: event.target.value }))
              }
            />
          </Field>
          <Field label={t('competition.registrationDeadline')}>
            <input
              type="date"
              className="input"
              value={createForm.registrationDeadline}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setCreateForm((current) => ({ ...current, registrationDeadline: event.target.value }))
              }
            />
          </Field>
          <Field label={t('common.description')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={2}
              value={createForm.description}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setCreateForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </Field>
        </form>
      </Modal>

      {/* ------------------------------------------------------------------ */}
      {/* Yarışma detayı */}
      {/* ------------------------------------------------------------------ */}
      <Modal
        open={detailId !== null}
        onClose={closeDetail}
        title={detail?.name ?? t('competition.singular')}
        size="full"
      >
        {detailQuery.isLoading ? (
          <LoadingState />
        ) : detailQuery.error ? (
          <ErrorState error={detailQuery.error} onRetry={() => void detailQuery.refetch()} />
        ) : detail ? (
          <>
            {/* Üst bilgi */}
            <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <Badge tone={levelTone(detail.level)}>
                {t(`competition.levels.${detail.level}`, detail.level)}
              </Badge>
              <span className="flex items-center gap-1">
                <CalendarDays className="h-3.5 w-3.5" />
                {formatDate(detail.start_date)} – {formatDate(detail.end_date)}
              </span>
              {detail.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  {detail.location}
                </span>
              )}
              <span>
                {detail.course_type === 'long' ? t('pool.longCourse') : t('pool.shortCourse')}
              </span>
              {detail.organizer && <span>{detail.organizer}</span>}
              {detail.registration_deadline && (
                <span>
                  {t('competition.registrationDeadline')}: {formatDate(detail.registration_deadline)}
                </span>
              )}
            </div>

            {/* Görünüm seçimi */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className={detailView === 'events' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                onClick={() => setDetailView('events')}
              >
                <ListOrdered className="h-3.5 w-3.5" />
                {t('competition.events')}
              </button>
              <button
                type="button"
                className={detailView === 'results' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                onClick={() => setDetailView('results')}
              >
                <Award className="h-3.5 w-3.5" />
                {t('competition.results')}
              </button>
              {detailView === 'events' && canWrite && (
                <button
                  type="button"
                  className="btn-secondary btn-sm ml-auto"
                  onClick={() => setEventFormOpen((current) => !current)}
                >
                  <Plus className="h-3.5 w-3.5" />
                  {t('competition.newEvent')}
                </button>
              )}
            </div>

            {/* Etkinlik ekleme formu */}
            {detailView === 'events' && eventFormOpen && canWrite && (
              <form
                onSubmit={submitEvent}
                className="mb-4 grid gap-3 rounded-lg border border-slate-200 p-3 sm:grid-cols-3 dark:border-slate-700"
              >
                <Field label={t('performance.stroke')} required>
                  <select
                    className="select"
                    value={eventForm.stroke}
                    onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                      setEventForm((current) => ({ ...current, stroke: event.target.value }))
                    }
                  >
                    {STROKES.map((stroke) => (
                      <option key={stroke} value={stroke}>
                        {t(`performance.strokes.${stroke}`, stroke)}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t('performance.distance')} required>
                  <select
                    className="select"
                    value={eventForm.distance}
                    onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                      setEventForm((current) => ({ ...current, distance: event.target.value }))
                    }
                  >
                    {DISTANCES.map((distance) => (
                      <option key={distance} value={distance}>
                        {distance} m
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t('competition.genderCategory')} required>
                  <select
                    className="select"
                    value={eventForm.genderCategory}
                    onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                      setEventForm((current) => ({ ...current, genderCategory: event.target.value }))
                    }
                  >
                    {GENDER_CATEGORIES.map((value) => (
                      <option key={value} value={value}>
                        {genderLabel(value)}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t('competition.ageCategory')}>
                  <input
                    className="input"
                    value={eventForm.ageCategory}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                      setEventForm((current) => ({ ...current, ageCategory: event.target.value }))
                    }
                  />
                </Field>
                <Field label={t('competition.rank')} required>
                  <input
                    type="number"
                    min="1"
                    className="input"
                    value={eventForm.order}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                      setEventForm((current) => ({ ...current, order: event.target.value }))
                    }
                  />
                </Field>
                <Field label={t('common.date')}>
                  <input
                    type="date"
                    className="input"
                    value={eventForm.scheduledDate}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                      setEventForm((current) => ({ ...current, scheduledDate: event.target.value }))
                    }
                  />
                </Field>
                <div className="flex items-end gap-2 sm:col-span-3">
                  <button type="submit" className="btn-primary btn-sm" disabled={createEventMutation.isPending}>
                    {t('common.save')}
                  </button>
                  <button type="button" className="btn-ghost btn-sm" onClick={() => setEventFormOpen(false)}>
                    {t('common.cancel')}
                  </button>
                </div>
              </form>
            )}

            {/* Etkinlik listesi */}
            {detailView === 'events' &&
              (detail.events.length === 0 ? (
                <EmptyState title={t('common.noData')} icon={<ListOrdered className="h-6 w-6" />} />
              ) : (
                <div className="space-y-3">
                  {detail.events.map((event) => (
                    <div
                      key={event.id}
                      className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="min-w-0">
                          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            {event.event_order}. {eventLabel(event.distance_m, event.stroke)}
                          </h3>
                          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                            {genderLabel(event.gender_category)}
                            {event.age_category ? ` · ${event.age_category}` : ''}
                            {event.scheduled_date ? ` · ${formatDate(event.scheduled_date)}` : ''}
                            {` · ${formatNumber(event.entry_count)} ${t('competition.entries')}`}
                          </p>
                        </div>
                        {canWrite && (
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              type="button"
                              className="btn-secondary btn-sm"
                              onClick={() => {
                                setEntryEventId((current) => (current === event.id ? null : event.id))
                                setEntryForm({ studentId: null, studentName: '', seedText: '' })
                              }}
                            >
                              <Plus className="h-3.5 w-3.5" />
                              {t('competition.newEntry')}
                            </button>
                            <button
                              type="button"
                              className="btn-secondary btn-sm"
                              onClick={() => seedHeatsMutation.mutate(event.id)}
                              disabled={seedHeatsMutation.isPending || event.entries.length === 0}
                            >
                              <Shuffle className="h-3.5 w-3.5" />
                              {t('competition.seedHeats')}
                            </button>
                            <button
                              type="button"
                              className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                              title={t('common.delete')}
                              aria-label={t('common.delete')}
                              onClick={() =>
                                setConfirmTarget({
                                  kind: 'event',
                                  id: event.id,
                                  label: eventLabel(event.distance_m, event.stroke),
                                })
                              }
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Sporcu kayıt formu */}
                      {entryEventId === event.id && canWrite && (
                        <form onSubmit={submitEntry} className="mt-3 grid gap-3 sm:grid-cols-3">
                          <Field label={t('student.singular')} required>
                            <StudentPicker
                              value={entryForm.studentId}
                              label={entryForm.studentName}
                              onSelect={(id, name) =>
                                setEntryForm((current) => ({ ...current, studentId: id, studentName: name }))
                              }
                            />
                          </Field>
                          <Field label={t('competition.seedTime')} hint={t('performance.timeHint')}>
                            <input
                              className="input"
                              value={entryForm.seedText}
                              placeholder="1:35.12"
                              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                                setEntryForm((current) => ({ ...current, seedText: event.target.value }))
                              }
                            />
                          </Field>
                          <div className="flex items-end gap-2">
                            <button
                              type="submit"
                              className="btn-primary btn-sm"
                              disabled={entryForm.studentId === null || createEntryMutation.isPending}
                            >
                              {t('common.save')}
                            </button>
                            <button
                              type="button"
                              className="btn-ghost btn-sm"
                              onClick={() => setEntryEventId(null)}
                            >
                              {t('common.cancel')}
                            </button>
                          </div>
                        </form>
                      )}

                      {/* Oluşturulan seriler */}
                      {heats[event.id] && heats[event.id].length > 0 && (
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          {heats[event.id].map((sheet) => (
                            <div
                              key={sheet.heat_number}
                              className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60"
                            >
                              <p className="mb-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200">
                                {t('competition.heat')} {sheet.heat_number}
                              </p>
                              <TableWrapper>
                                <thead>
                                  <tr>
                                    <th className="w-16">{t('competition.lane')}</th>
                                    <th>{t('student.singular')}</th>
                                    <th className="text-right">{t('competition.seedTime')}</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {sheet.lanes.map((lane) => (
                                    <tr key={lane.lane_number}>
                                      <td className="tabular-nums">{lane.lane_number}</td>
                                      <td>{lane.student_name ?? '—'}</td>
                                      <td className="text-right tabular-nums">
                                        {lane.formatted_seed ?? '—'}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </TableWrapper>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Kayıtlı sporcular */}
                      {event.entries.length === 0 ? (
                        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                          {t('common.noData')}
                        </p>
                      ) : (
                        <div className="mt-3">
                          <TableWrapper>
                            <thead>
                              <tr>
                                <th>{t('student.singular')}</th>
                                <th>{t('competition.seedTime')}</th>
                                <th className="hidden sm:table-cell">{t('competition.heat')}</th>
                                <th className="hidden sm:table-cell">{t('competition.lane')}</th>
                                <th>{t('competition.result')}</th>
                                <th>{t('competition.rank')}</th>
                                <th>{t('competition.medal')}</th>
                                {canWrite && <th className="text-right">{t('common.actions')}</th>}
                              </tr>
                            </thead>
                            <tbody>
                              {event.entries.map((entry) => (
                                <tr key={entry.id}>
                                  <td className="font-medium text-slate-800 dark:text-slate-100">
                                    {entry.student_name ?? '—'}
                                    <div className="mt-0.5 flex flex-wrap gap-1">
                                      {entry.is_personal_best && (
                                        <Badge tone="success">{t('performance.personalBest')}</Badge>
                                      )}
                                      {entry.is_club_record && (
                                        <Badge tone="warning">{t('competition.clubRecord')}</Badge>
                                      )}
                                      {entry.is_disqualified && (
                                        <Badge tone="danger">{t('competition.disqualified')}</Badge>
                                      )}
                                    </div>
                                  </td>
                                  <td className="whitespace-nowrap tabular-nums">
                                    {formatSwimTime(entry.seed_time_seconds)}
                                  </td>
                                  <td className="hidden tabular-nums sm:table-cell">
                                    {entry.heat_number ?? '—'}
                                  </td>
                                  <td className="hidden tabular-nums sm:table-cell">
                                    {entry.lane_number ?? '—'}
                                  </td>
                                  <td className="whitespace-nowrap font-semibold tabular-nums">
                                    {entry.result_time_seconds
                                      ? formatSwimTime(entry.result_time_seconds)
                                      : '—'}
                                    {entry.improvement_seconds !== null &&
                                      entry.improvement_seconds !== undefined && (
                                        <span className="ml-1.5 text-xs font-normal text-slate-400">
                                          {formatTimeDelta(entry.improvement_seconds)}
                                        </span>
                                      )}
                                  </td>
                                  <td className="tabular-nums">{entry.rank ?? '—'}</td>
                                  <td>
                                    {entry.medal ? (
                                      <Badge tone={medalTone(entry.medal)}>
                                        {t(`competition.medalTypes.${entry.medal}`, entry.medal)}
                                      </Badge>
                                    ) : (
                                      '—'
                                    )}
                                  </td>
                                  {canWrite && (
                                    <td>
                                      <div className="flex items-center justify-end gap-1">
                                        <button
                                          type="button"
                                          className="btn-ghost btn-sm"
                                          onClick={() => {
                                            setResultEntryId((current) =>
                                              current === entry.id ? null : entry.id,
                                            )
                                            setResultError(undefined)
                                            setResultForm({
                                              timeText: entry.result_time_seconds
                                                ? formatSwimTime(entry.result_time_seconds)
                                                : '',
                                              rank: entry.rank !== null && entry.rank !== undefined
                                                ? String(entry.rank)
                                                : '',
                                              medal: entry.medal ?? '',
                                              disqualified: entry.is_disqualified,
                                              dqReason: '',
                                            })
                                          }}
                                        >
                                          {t('competition.result')}
                                        </button>
                                        <button
                                          type="button"
                                          className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                                          title={t('common.delete')}
                                          aria-label={t('common.delete')}
                                          onClick={() =>
                                            setConfirmTarget({
                                              kind: 'entry',
                                              id: entry.id,
                                              label: entry.student_name ?? '',
                                            })
                                          }
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

                          {/* Sonuç giriş formu */}
                          {canWrite &&
                            resultEntryId !== null &&
                            event.entries.some((entry) => entry.id === resultEntryId) && (
                              <form
                                onSubmit={submitResult}
                                className="mt-3 grid gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-4 dark:bg-slate-800/60"
                              >
                                <Field
                                  label={t('competition.resultTime')}
                                  error={resultError}
                                  hint={t('performance.timeHint')}
                                >
                                  <input
                                    className="input"
                                    value={resultForm.timeText}
                                    placeholder="1:35.12"
                                    disabled={resultForm.disqualified}
                                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                                      setResultForm((current) => ({
                                        ...current,
                                        timeText: event.target.value,
                                      }))
                                    }
                                  />
                                </Field>
                                <Field label={t('competition.rank')}>
                                  <input
                                    type="number"
                                    min="1"
                                    className="input"
                                    value={resultForm.rank}
                                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                                      setResultForm((current) => ({ ...current, rank: event.target.value }))
                                    }
                                  />
                                </Field>
                                <Field label={t('competition.medal')}>
                                  <select
                                    className="select"
                                    value={resultForm.medal}
                                    onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                                      setResultForm((current) => ({ ...current, medal: event.target.value }))
                                    }
                                  >
                                    <option value="">{t('common.none')}</option>
                                    {MEDALS.map((medal) => (
                                      <option key={medal} value={medal}>
                                        {t(`competition.medalTypes.${medal}`, medal)}
                                      </option>
                                    ))}
                                  </select>
                                </Field>
                                <Field label={t('competition.dqReason')}>
                                  <input
                                    className="input"
                                    value={resultForm.dqReason}
                                    disabled={!resultForm.disqualified}
                                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                                      setResultForm((current) => ({
                                        ...current,
                                        dqReason: event.target.value,
                                      }))
                                    }
                                  />
                                </Field>
                                <div className="flex items-center sm:col-span-2">
                                  <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                                    <input
                                      type="checkbox"
                                      checked={resultForm.disqualified}
                                      onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                                        setResultForm((current) => ({
                                          ...current,
                                          disqualified: event.target.checked,
                                        }))
                                      }
                                    />
                                    {t('competition.disqualified')}
                                  </label>
                                </div>
                                <div className="flex items-end gap-2 sm:col-span-2">
                                  <button
                                    type="submit"
                                    className="btn-primary btn-sm"
                                    disabled={saveResultMutation.isPending}
                                  >
                                    {t('common.save')}
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-ghost btn-sm"
                                    onClick={() => setResultEntryId(null)}
                                  >
                                    {t('common.cancel')}
                                  </button>
                                </div>
                              </form>
                            )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}

            {/* Sonuçlar görünümü */}
            {detailView === 'results' &&
              (resultsQuery.isLoading ? (
                <LoadingState />
              ) : resultsQuery.error ? (
                <ErrorState error={resultsQuery.error} onRetry={() => void resultsQuery.refetch()} />
              ) : resultsQuery.data ? (
                <>
                  <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <StatCard
                      label={t('competition.events')}
                      value={formatNumber(resultsQuery.data.summary.event_count)}
                      icon={<ListOrdered className="h-5 w-5" />}
                    />
                    <StatCard
                      label={t('competition.entries')}
                      value={formatNumber(resultsQuery.data.summary.entry_count)}
                      icon={<Trophy className="h-5 w-5" />}
                      tone="brand"
                    />
                    <StatCard
                      label={t('performance.personalBests')}
                      value={formatNumber(resultsQuery.data.summary.personal_bests)}
                      icon={<Award className="h-5 w-5" />}
                      tone="success"
                    />
                    <StatCard
                      label={t('competition.clubRecords')}
                      value={formatNumber(resultsQuery.data.summary.club_records)}
                      icon={<Medal className="h-5 w-5" />}
                      tone="warning"
                    />
                  </div>

                  {resultsQuery.data.events.length === 0 ? (
                    <EmptyState title={t('common.noData')} icon={<Award className="h-6 w-6" />} />
                  ) : (
                    <div className="space-y-4">
                      {resultsQuery.data.events.map((resultEvent) => (
                        <div
                          key={resultEvent.event_id}
                          className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                        >
                          <h3 className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                            {resultEvent.event_name}
                            <span className="ml-2 text-xs font-normal text-slate-500 dark:text-slate-400">
                              {genderLabel(resultEvent.gender_category)}
                              {resultEvent.age_category ? ` · ${resultEvent.age_category}` : ''}
                            </span>
                          </h3>

                          {resultEvent.results.length === 0 ? (
                            <p className="text-xs text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
                          ) : (
                            <TableWrapper>
                              <thead>
                                <tr>
                                  <th className="w-12">{t('competition.rank')}</th>
                                  <th>{t('student.singular')}</th>
                                  <th>{t('competition.resultTime')}</th>
                                  <th className="hidden sm:table-cell">{t('competition.seedTime')}</th>
                                  <th className="hidden md:table-cell">{t('performance.improvement')}</th>
                                  <th>{t('competition.medal')}</th>
                                </tr>
                              </thead>
                              <tbody>
                                {resultEvent.results.map((row) => (
                                  <tr key={`${resultEvent.event_id}-${row.student_id}`}>
                                    <td className="tabular-nums">{row.rank}</td>
                                    <td className="font-medium text-slate-800 dark:text-slate-100">
                                      {row.student_name ?? '—'}
                                      <div className="mt-0.5 flex flex-wrap gap-1">
                                        {row.is_personal_best && (
                                          <Badge tone="success">{t('performance.personalBest')}</Badge>
                                        )}
                                        {row.is_club_record && (
                                          <Badge tone="warning">{t('competition.clubRecord')}</Badge>
                                        )}
                                      </div>
                                    </td>
                                    <td className="whitespace-nowrap font-semibold tabular-nums">
                                      {row.time}
                                    </td>
                                    <td className="hidden whitespace-nowrap tabular-nums sm:table-cell">
                                      {row.seed_time}
                                    </td>
                                    <td className="hidden whitespace-nowrap tabular-nums md:table-cell">
                                      {row.improvement !== null && row.improvement !== undefined
                                        ? formatTimeDelta(row.improvement)
                                        : '—'}
                                    </td>
                                    <td>
                                      {row.medal ? (
                                        <Badge tone={medalTone(row.medal)}>
                                          {t(`competition.medalTypes.${row.medal}`, row.medal)}
                                        </Badge>
                                      ) : (
                                        '—'
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </TableWrapper>
                          )}

                          {resultEvent.disqualified.length > 0 && (
                            <div className="mt-2">
                              <Alert tone="warning" title={t('competition.disqualified')}>
                                {resultEvent.disqualified
                                  .map(
                                    (item) =>
                                      `${item.student_name ?? '—'}${item.reason ? ` (${item.reason})` : ''}`,
                                  )
                                  .join(' · ')}
                              </Alert>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : null)}
          </>
        ) : null}
      </Modal>

      <ConfirmDialog
        open={confirmTarget !== null}
        onClose={() => setConfirmTarget(null)}
        onConfirm={handleConfirm}
        title={t('common.delete')}
        message={confirmTarget?.label ?? ''}
        confirmLabel={t('common.delete')}
        loading={
          deleteCompetitionMutation.isPending ||
          deleteEventMutation.isPending ||
          deleteEntryMutation.isPending
        }
      />
    </>
  )
}
