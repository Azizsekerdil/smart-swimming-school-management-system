/** Ders takvimi: gün / hafta / ay görünümü, çakışma denetimli ders ve seri oluşturma. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Ban,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Plus,
  Repeat,
  Users,
} from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import {
  Alert,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  Spinner,
  StatusBadge,
} from '@/components/ui'
import { ApiError, get, post } from '@/lib/api'
import {
  formatCurrency,
  formatDate,
  formatDateLong,
  formatNumber,
  formatPercent,
  formatTime,
  formatTimeRange,
  toISODate,
  toISODateTime,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  CalendarEvent,
  ConflictCheckResponse,
  ConflictItem,
  Group,
  Instructor,
  LessonDetail,
  LessonType,
  Message,
  Page,
  Pool,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler ve yerel tipler
// ---------------------------------------------------------------------------
type CalendarView = 'day' | 'week' | 'month'
type ColorMode = 'type' | 'instructor' | 'pool' | 'group'

/** Backend CalendarResponse şeması */
interface CalendarResponse {
  start: string
  end: string
  events: CalendarEvent[]
  total: number
}

/** POST /lessons/series yanıtı (üretilen ders sayısını taşır) */
interface LessonSeriesResult {
  id: number
  title: string
  generated_lesson_count: number
}

const LESSON_TYPES: LessonType[] = [
  'group', 'private', 'kids', 'baby', 'adult', 'beginner', 'intermediate',
  'advanced', 'competition_team', 'adaptive', 'conditioning', 'trial', 'makeup',
]

const PALETTE = [
  '#0ea5e9', '#6366f1', '#10b981', '#f59e0b', '#8b5cf6', '#f43f5e',
  '#38bdf8', '#14b8a6', '#a855f7', '#ef4444', '#22c55e', '#eab308',
]

/** Bir saat satırının piksel yüksekliği */
const HOUR_HEIGHT = 54

// ---------------------------------------------------------------------------
// Tarih yardımcıları
// ---------------------------------------------------------------------------
function startOfDay(value: Date): Date {
  const copy = new Date(value)
  copy.setHours(0, 0, 0, 0)
  return copy
}

function addDays(value: Date, amount: number): Date {
  const copy = new Date(value)
  copy.setDate(copy.getDate() + amount)
  return copy
}

/** Hafta pazartesi başlar (0 = Pazartesi) */
function startOfWeek(value: Date): Date {
  const copy = startOfDay(value)
  return addDays(copy, -((copy.getDay() + 6) % 7))
}

function startOfMonth(value: Date): Date {
  const copy = startOfDay(value)
  copy.setDate(1)
  return copy
}

function addMonths(value: Date, amount: number): Date {
  const copy = startOfMonth(value)
  copy.setMonth(copy.getMonth() + amount)
  return copy
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

/** Gün içindeki dakika karşılığı (00:00 = 0) */
function minutesOfDay(value: string): number {
  const date = new Date(value)
  return date.getHours() * 60 + date.getMinutes()
}

/** Saat etiketini yerel biçimde üretir (08:00 / 8 AM) */
function hourLabel(hour: number): string {
  const date = new Date(2000, 0, 1, hour, 0, 0)
  return formatTime(date)
}

/**
 * Aynı gün içinde çakışan dersleri yan yana sütunlara yerleştirir.
 * Her ders için sütun indeksi ve o kümedeki toplam sütun sayısı döner.
 */
function layoutDayEvents(
  events: CalendarEvent[],
): Array<{ event: CalendarEvent; column: number; columns: number }> {
  const sorted = [...events].sort(
    (a, b) => new Date(a.start).getTime() - new Date(b.start).getTime(),
  )
  const placed: Array<{ event: CalendarEvent; column: number; columns: number }> = []
  let cluster: CalendarEvent[] = []
  let clusterEnd = 0

  const flush = () => {
    const columnEnds: number[] = []
    const assigned = cluster.map((event) => {
      const start = new Date(event.start).getTime()
      const end = new Date(event.end).getTime()
      let index = columnEnds.findIndex((columnEnd) => columnEnd <= start)
      if (index === -1) {
        columnEnds.push(end)
        index = columnEnds.length - 1
      } else {
        columnEnds[index] = end
      }
      return { event, column: index }
    })
    for (const item of assigned) {
      placed.push({ ...item, columns: columnEnds.length })
    }
    cluster = []
    clusterEnd = 0
  }

  for (const event of sorted) {
    const start = new Date(event.start).getTime()
    if (cluster.length > 0 && start >= clusterEnd) flush()
    cluster.push(event)
    clusterEnd = Math.max(clusterEnd, new Date(event.end).getTime())
  }
  if (cluster.length > 0) flush()
  return placed
}

// ---------------------------------------------------------------------------
// Sayfa
// ---------------------------------------------------------------------------
export default function CalendarPage() {
  const { t, i18n } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const [view, setView] = useState<CalendarView>('week')
  const [anchor, setAnchor] = useState<Date>(() => new Date())
  const [colorMode, setColorMode] = useState<ColorMode>('type')
  const [poolFilter, setPoolFilter] = useState('')
  const [instructorFilter, setInstructorFilter] = useState('')
  const [groupFilter, setGroupFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [cancelReason, setCancelReason] = useState('')

  const [lessonFormOpen, setLessonFormOpen] = useState(false)
  const [seriesFormOpen, setSeriesFormOpen] = useState(false)

  // Görüntülenen tarih aralığı
  const range = useMemo(() => {
    if (view === 'day') return { start: startOfDay(anchor), end: startOfDay(anchor) }
    if (view === 'week') {
      const start = startOfWeek(anchor)
      return { start, end: addDays(start, 6) }
    }
    const start = startOfWeek(startOfMonth(anchor))
    return { start, end: addDays(start, 41) }
  }, [view, anchor])

  const isoStart = toISODate(range.start)
  const isoEnd = toISODate(range.end)

  // Referans veriler
  const { data: pools } = useQuery({
    queryKey: ['pools'],
    queryFn: () => get<Pool[]>('/pools'),
    staleTime: 300_000,
  })
  const { data: instructors } = useQuery({
    queryKey: ['instructors', 'options'],
    queryFn: () => get<Page<Instructor>>('/instructors', { page: 1, page_size: 200 }),
    staleTime: 300_000,
  })
  const { data: groups } = useQuery({
    queryKey: ['groups'],
    queryFn: () => get<Group[]>('/groups'),
    staleTime: 300_000,
  })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['calendar', isoStart, isoEnd, poolFilter, instructorFilter, groupFilter, typeFilter],
    queryFn: () =>
      get<CalendarResponse>('/lessons/calendar', {
        start: isoStart,
        end: isoEnd,
        pool_id: poolFilter || undefined,
        instructor_id: instructorFilter || undefined,
        group_id: groupFilter || undefined,
        lesson_type: typeFilter || undefined,
      }),
  })

  const events = useMemo(() => data?.events ?? [], [data])

  // Renklendirme: seçilen ölçüte göre sabit palet ataması
  const colorMap = useMemo(() => {
    const keys = Array.from(
      new Set(
        events.map((event) => {
          if (colorMode === 'instructor') return event.instructor_name ?? '—'
          if (colorMode === 'pool') return event.pool_name
          if (colorMode === 'group') return event.group_name ?? '—'
          return event.lesson_type
        }),
      ),
    ).sort()
    const map = new Map<string, string>()
    keys.forEach((key, index) => map.set(key, PALETTE[index % PALETTE.length]))
    return map
  }, [events, colorMode])

  const eventColor = (event: CalendarEvent): string => {
    const raw =
      colorMode === 'instructor'
        ? event.instructor_name ?? '—'
        : colorMode === 'pool'
          ? event.pool_name
          : colorMode === 'group'
            ? event.group_name ?? '—'
            : event.lesson_type
    return colorMap.get(raw) ?? event.color
  }

  const legendLabel = (key: string): string =>
    colorMode === 'type' ? t(`lesson.types.${key}`, key) : key

  // Saat aralığı: dersler dışına taşmayacak şekilde daraltılır
  const hourBounds = useMemo(() => {
    let min = 8
    let max = 20
    for (const event of events) {
      const startMinutes = minutesOfDay(event.start)
      const endMinutes = minutesOfDay(event.end) || 24 * 60
      min = Math.min(min, Math.floor(startMinutes / 60))
      max = Math.max(max, Math.ceil(endMinutes / 60))
    }
    return { start: Math.max(0, min), end: Math.min(24, Math.max(max, min + 4)) }
  }, [events])

  const hours = useMemo(
    () =>
      Array.from({ length: hourBounds.end - hourBounds.start }, (_, index) => hourBounds.start + index),
    [hourBounds],
  )
  const gridHeight = hours.length * HOUR_HEIGHT

  const days = useMemo(() => {
    const count = view === 'day' ? 1 : 7
    return Array.from({ length: count }, (_, index) => addDays(range.start, index))
  }, [view, range])

  const monthCells = useMemo(
    () => Array.from({ length: 42 }, (_, index) => addDays(range.start, index)),
    [range],
  )

  const eventsOfDay = (day: Date): CalendarEvent[] =>
    events.filter((event) => isSameDay(new Date(event.start), day))

  // Başlık etiketi
  const periodLabel = useMemo(() => {
    if (view === 'day') return formatDateLong(anchor)
    if (view === 'week') return `${formatDate(range.start)} – ${formatDate(range.end)}`
    // Ay görünümünde "Ağustos 2026" biçimi
    return new Intl.DateTimeFormat(i18n.language === 'en' ? 'en-US' : 'tr-TR', {
      month: 'long',
      year: 'numeric',
    }).format(startOfMonth(anchor))
  }, [view, anchor, range, i18n.language])

  function shift(direction: number) {
    if (view === 'day') setAnchor(addDays(anchor, direction))
    else if (view === 'week') setAnchor(addDays(anchor, 7 * direction))
    else setAnchor(addMonths(anchor, direction))
  }

  // Ders detayı
  const detailQuery = useQuery({
    queryKey: ['lesson', selectedId],
    queryFn: () => get<LessonDetail>(`/lessons/${selectedId}`),
    enabled: selectedId !== null,
  })

  const cancelLesson = useMutation({
    mutationFn: (payload: { id: number; reason: string }) =>
      post<Message>(`/lessons/${payload.id}/cancel`, undefined, { reason: payload.reason }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['calendar'] })
      void queryClient.invalidateQueries({ queryKey: ['lesson'] })
      toastSuccess(t('common.success'))
      setCancelOpen(false)
      setCancelReason('')
      setSelectedId(null)
    },
    onError: (mutationError) => toastError(mutationError),
  })

  const today = new Date()

  return (
    <>
      <PageHeader
        title={t('calendar.title')}
        subtitle={`${formatNumber(data?.total ?? 0)} ${t('lesson.title').toLowerCase()}`}
        icon={<CalendarDays className="h-5 w-5" />}
        actions={
          <>
            {can('lesson:write') && (
              <button type="button" className="btn-primary" onClick={() => setLessonFormOpen(true)}>
                <Plus className="h-4 w-4" />
                {t('lesson.new')}
              </button>
            )}
            {can('lesson:schedule') && (
              <button type="button" className="btn-secondary" onClick={() => setSeriesFormOpen(true)}>
                <Repeat className="h-4 w-4" />
                {t('lesson.series')}
              </button>
            )}
          </>
        }
      />

      {/* Gezinme çubuğu */}
      <div className="mb-4 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-surface-dark-alt lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => shift(-1)}
            aria-label={t('common.previous')}
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button type="button" className="btn-secondary btn-sm" onClick={() => setAnchor(new Date())}>
            {t('calendar.today')}
          </button>
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => shift(1)}
            aria-label={t('common.next')}
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <p className="ml-1 text-sm font-semibold text-slate-800 dark:text-slate-100">{periodLabel}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex overflow-hidden rounded-lg border border-slate-200 dark:border-slate-600">
            {(['day', 'week', 'month'] as CalendarView[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setView(item)}
                className={
                  view === item
                    ? 'bg-brand-500 px-3 py-1.5 text-xs font-medium text-white'
                    : 'px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700'
                }
              >
                {t(`calendar.${item}`)}
              </button>
            ))}
          </div>
          <select
            className="select w-auto py-1.5 text-xs"
            value={colorMode}
            onChange={(event) => setColorMode(event.target.value as ColorMode)}
            aria-label={t('calendar.colorBy')}
          >
            <option value="type">{t('calendar.colorByType')}</option>
            <option value="instructor">{t('calendar.colorByInstructor')}</option>
            <option value="pool">{t('calendar.colorByPool')}</option>
            <option value="group">{t('calendar.colorByGroup')}</option>
          </select>
        </div>
      </div>

      {/* Filtreler */}
      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <select
          className="select"
          value={poolFilter}
          onChange={(event) => setPoolFilter(event.target.value)}
          aria-label={t('pool.singular')}
        >
          <option value="">{t('pool.singular')} — {t('common.all')}</option>
          {(pools ?? []).map((pool) => (
            <option key={pool.id} value={pool.id}>
              {pool.name}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={instructorFilter}
          onChange={(event) => setInstructorFilter(event.target.value)}
          aria-label={t('instructor.singular')}
        >
          <option value="">{t('instructor.singular')} — {t('common.all')}</option>
          {(instructors?.items ?? []).map((instructor) => (
            <option key={instructor.id} value={instructor.id}>
              {instructor.full_name}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={groupFilter}
          onChange={(event) => setGroupFilter(event.target.value)}
          aria-label={t('student.group')}
        >
          <option value="">{t('student.group')} — {t('common.all')}</option>
          {(groups ?? []).map((group) => (
            <option key={group.id} value={group.id}>
              {group.name}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={typeFilter}
          onChange={(event) => setTypeFilter(event.target.value)}
          aria-label={t('lesson.type')}
        >
          <option value="">{t('lesson.type')} — {t('common.all')}</option>
          {LESSON_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`lesson.types.${type}`)}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => {
            setPoolFilter('')
            setInstructorFilter('')
            setGroupFilter('')
            setTypeFilter('')
          }}
        >
          {t('common.clearFilters')}
        </button>
      </div>

      {/* Renk açıklaması */}
      {colorMap.size > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600 dark:text-slate-300">
          <span className="font-medium text-slate-500 dark:text-slate-400">{t('calendar.colorBy')}:</span>
          {Array.from(colorMap.entries()).map(([key, color]) => (
            <span key={key} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
              {legendLabel(key)}
            </span>
          ))}
        </div>
      )}

      <Card bodyClassName="p-0">
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : events.length === 0 ? (
          <EmptyState title={t('calendar.noEvents')} icon={<CalendarDays className="h-6 w-6" />} />
        ) : view === 'month' ? (
          /* --------------------------- AY GÖRÜNÜMÜ --------------------------- */
          <div className="overflow-x-auto">
            <div className="min-w-[720px]">
              <div className="grid grid-cols-7 border-b border-slate-200 dark:border-slate-700">
                {Array.from({ length: 7 }, (_, index) => (
                  <div
                    key={index}
                    className="px-2 py-2 text-center text-xs font-semibold text-slate-500 dark:text-slate-400"
                  >
                    {t(`weekdays.short.${index}`)}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7">
                {monthCells.map((day) => {
                  const dayEvents = eventsOfDay(day)
                  const outside = day.getMonth() !== anchor.getMonth()
                  return (
                    <div
                      key={day.toISOString()}
                      className={`min-h-[110px] border-b border-r border-slate-200 p-1.5 dark:border-slate-700 ${
                        outside ? 'bg-slate-50 dark:bg-slate-800/40' : ''
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <span
                          className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                            isSameDay(day, today)
                              ? 'bg-brand-500 font-semibold text-white'
                              : outside
                                ? 'text-slate-400 dark:text-slate-600'
                                : 'text-slate-600 dark:text-slate-300'
                          }`}
                        >
                          {day.getDate()}
                        </span>
                        {dayEvents.length > 0 && (
                          <span className="badge-info text-[10px]">{formatNumber(dayEvents.length)}</span>
                        )}
                      </div>
                      <div className="space-y-1">
                        {dayEvents.slice(0, 3).map((event) => (
                          <button
                            key={event.id}
                            type="button"
                            onClick={() => setSelectedId(event.id)}
                            title={`${event.title} · ${formatTimeRange(event.start, event.end)}`}
                            className="flex w-full items-center gap-1 rounded border-l-2 px-1 py-0.5 text-left text-[11px] text-slate-700 hover:opacity-80 dark:text-slate-100"
                            style={{
                              backgroundColor: `${eventColor(event)}26`,
                              borderLeftColor: eventColor(event),
                            }}
                          >
                            <span className="shrink-0 tabular-nums opacity-70">
                              {formatTime(event.start)}
                            </span>
                            <span className="truncate">{event.title}</span>
                          </button>
                        ))}
                        {dayEvents.length > 3 && (
                          <button
                            type="button"
                            className="w-full text-left text-[11px] text-brand-600 hover:underline dark:text-brand-400"
                            onClick={() => {
                              setAnchor(day)
                              setView('day')
                            }}
                          >
                            +{formatNumber(dayEvents.length - 3)}
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        ) : (
          /* ----------------------- GÜN / HAFTA GÖRÜNÜMÜ ---------------------- */
          <div className="overflow-x-auto">
            <div className={view === 'week' ? 'min-w-[820px]' : 'min-w-[360px]'}>
              {/* Gün başlıkları */}
              <div className="flex border-b border-slate-200 dark:border-slate-700">
                <div className="w-16 shrink-0" />
                <div
                  className="grid flex-1"
                  style={{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }}
                >
                  {days.map((day) => (
                    <div
                      key={day.toISOString()}
                      className={`border-l border-slate-200 px-2 py-2 text-center dark:border-slate-700 ${
                        isSameDay(day, today) ? 'bg-brand-50 dark:bg-brand-900/20' : ''
                      }`}
                    >
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                        {t(`weekdays.short.${(day.getDay() + 6) % 7}`)}
                      </p>
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                        {formatDate(day)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Saat ızgarası */}
              <div className="flex">
                <div className="w-16 shrink-0" style={{ height: gridHeight }}>
                  {hours.map((hour, index) => (
                    <div
                      key={hour}
                      className="relative text-right text-[11px] text-slate-400 dark:text-slate-500"
                      style={{ height: HOUR_HEIGHT }}
                    >
                      <span className={index === 0 ? 'absolute right-2 top-0' : 'absolute right-2 -top-1.5'}>
                        {hourLabel(hour)}
                      </span>
                    </div>
                  ))}
                </div>
                <div
                  className="grid flex-1"
                  style={{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }}
                >
                  {days.map((day) => {
                    const placed = layoutDayEvents(eventsOfDay(day))
                    return (
                      <div
                        key={day.toISOString()}
                        className="relative border-l border-slate-200 dark:border-slate-700"
                        style={{ height: gridHeight }}
                      >
                        {hours.map((hour, index) => (
                          <div
                            key={hour}
                            className="absolute left-0 right-0 border-t border-slate-100 dark:border-slate-700/60"
                            style={{ top: index * HOUR_HEIGHT }}
                          />
                        ))}
                        {placed.map(({ event, column, columns }) => {
                          const startMinutes = minutesOfDay(event.start)
                          const endMinutes = minutesOfDay(event.end) || 24 * 60
                          const top = ((startMinutes - hourBounds.start * 60) / 60) * HOUR_HEIGHT
                          const height = Math.max(24, ((endMinutes - startMinutes) / 60) * HOUR_HEIGHT - 2)
                          const color = eventColor(event)
                          return (
                            <button
                              key={event.id}
                              type="button"
                              onClick={() => setSelectedId(event.id)}
                              title={`${event.title} · ${formatTimeRange(event.start, event.end)}`}
                              className={`absolute overflow-hidden rounded-md border-l-4 px-1.5 py-1 text-left text-[11px] leading-tight text-slate-800 shadow-sm transition hover:z-10 hover:shadow-md dark:text-slate-100 ${
                                event.status === 'cancelled' ? 'line-through opacity-60' : ''
                              }`}
                              style={{
                                top,
                                height,
                                left: `calc(${(column / columns) * 100}% + 2px)`,
                                width: `calc(${100 / columns}% - 4px)`,
                                backgroundColor: `${color}2e`,
                                borderLeftColor: color,
                              }}
                            >
                              <span className="block truncate font-semibold">{event.title}</span>
                              <span className="block truncate opacity-80">
                                {formatTimeRange(event.start, event.end)}
                              </span>
                              {height > 54 && (
                                <span className="block truncate opacity-70">
                                  {event.lane_name ?? event.pool_name}
                                  {event.instructor_name ? ` · ${event.instructor_name}` : ''}
                                </span>
                              )}
                              {height > 74 && (
                                <span className="block truncate opacity-70">
                                  {formatNumber(event.enrolled_count)}/{formatNumber(event.capacity)}
                                </span>
                              )}
                            </button>
                          )
                        })}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* ------------------------------ DETAY MODALI ------------------------------ */}
      <Modal
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
        title={detailQuery.data?.title ?? t('lesson.singular')}
        size="lg"
        footer={
          detailQuery.data && (
            <>
              <Link
                to={`/attendance?lesson=${detailQuery.data.id}`}
                className="btn-secondary"
                onClick={() => setSelectedId(null)}
              >
                <ClipboardList className="h-4 w-4" />
                {t('attendance.take')}
              </Link>
              {can('lesson:write') && detailQuery.data.status !== 'cancelled' && (
                <button type="button" className="btn-danger" onClick={() => setCancelOpen(true)}>
                  <Ban className="h-4 w-4" />
                  {t('lesson.cancel')}
                </button>
              )}
            </>
          )
        }
      >
        {detailQuery.isLoading ? (
          <LoadingState />
        ) : detailQuery.error ? (
          <ErrorState error={detailQuery.error} onRetry={detailQuery.refetch} />
        ) : detailQuery.data ? (
          <LessonDetailBody detail={detailQuery.data} />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        onConfirm={() => {
          if (selectedId && cancelReason.trim()) {
            cancelLesson.mutate({ id: selectedId, reason: cancelReason.trim() })
          }
        }}
        title={t('lesson.cancel')}
        confirmLabel={t('lesson.cancel')}
        loading={cancelLesson.isPending}
        message={
          <Field label={t('lesson.cancelReason')} required>
            <textarea
              className="textarea"
              rows={3}
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
            />
          </Field>
        }
      />

      {/* ------------------------------ FORMLAR ------------------------------ */}
      {lessonFormOpen && (
        <LessonFormModal
          defaultDate={anchor}
          pools={pools ?? []}
          instructors={instructors?.items ?? []}
          groups={groups ?? []}
          onClose={() => setLessonFormOpen(false)}
          onCreated={() => {
            setLessonFormOpen(false)
            void queryClient.invalidateQueries({ queryKey: ['calendar'] })
          }}
        />
      )}

      {seriesFormOpen && (
        <SeriesFormModal
          defaultDate={anchor}
          pools={pools ?? []}
          instructors={instructors?.items ?? []}
          groups={groups ?? []}
          onClose={() => setSeriesFormOpen(false)}
          onCreated={() => {
            setSeriesFormOpen(false)
            void queryClient.invalidateQueries({ queryKey: ['calendar'] })
          }}
        />
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Ders detay gövdesi
// ---------------------------------------------------------------------------
function LessonDetailBody({ detail }: { detail: LessonDetail }) {
  const { t } = useTranslation()
  const occupancy = detail.capacity > 0 ? (detail.enrolled_count / detail.capacity) * 100 : 0

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <InfoRow label={t('common.date')} value={formatDateLong(detail.start_at)} />
        <InfoRow label={t('common.time')} value={formatTimeRange(detail.start_at, detail.end_at)} />
        <InfoRow label={t('lesson.type')} value={t(`lesson.types.${detail.lesson_type}`)} />
        <InfoRow
          label={t('common.status')}
          value={<StatusBadge status={detail.status} label={t(`lesson.statuses.${detail.status}`)} />}
        />
        <InfoRow
          label={t('pool.singular')}
          value={`${detail.pool_name ?? '—'}${detail.lane_name ? ` · ${detail.lane_name}` : ''}`}
        />
        <InfoRow label={t('instructor.singular')} value={detail.instructor_name ?? '—'} />
        <InfoRow label={t('student.group')} value={detail.group_name ?? '—'} />
        <InfoRow
          label={t('lesson.enrolled')}
          value={`${formatNumber(detail.enrolled_count)} / ${formatNumber(detail.capacity)} · ${formatPercent(occupancy)}`}
        />
        <InfoRow
          label={t('lesson.price')}
          value={detail.price !== null && detail.price !== undefined ? formatCurrency(detail.price) : '—'}
        />
        <InfoRow
          label={t('attendance.title')}
          value={detail.attendance_recorded ? t('attendance.recorded') : t('attendance.notRecorded')}
        />
      </div>

      {detail.cancellation_reason && (
        <Alert tone="danger" title={t('lesson.cancelReason')}>
          {detail.cancellation_reason}
        </Alert>
      )}
      {detail.notes && (
        <Alert tone="info" title={t('common.notes')}>
          {detail.notes}
        </Alert>
      )}

      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
          <Users className="h-4 w-4" />
          {t('lesson.roster')}
        </h3>
        {detail.enrollments.length === 0 ? (
          <EmptyState title={t('common.noData')} icon={<Users className="h-6 w-6" />} />
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{t('student.number')}</th>
                  <th>{t('student.fullName')}</th>
                  <th>{t('common.status')}</th>
                </tr>
              </thead>
              <tbody>
                {detail.enrollments.map((enrollment) => (
                  <tr key={enrollment.id}>
                    <td className="text-xs text-slate-500">{enrollment.student_number ?? '—'}</td>
                    <td>
                      <Link
                        to={`/students/${enrollment.student_id}`}
                        className="hover:text-brand-600 dark:hover:text-brand-400"
                      >
                        {enrollment.student_name ?? `#${enrollment.student_id}`}
                      </Link>
                    </td>
                    <td>
                      <StatusBadge status={enrollment.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      <div className="mt-0.5 text-sm font-medium text-slate-800 dark:text-slate-100">{value}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Çakışma listesi
// ---------------------------------------------------------------------------
function ConflictList({ items, tone }: { items: ConflictItem[]; tone: 'danger' | 'warning' }) {
  const { t } = useTranslation()
  if (items.length === 0) return null
  return (
    <Alert
      tone={tone}
      title={tone === 'danger' ? t('lesson.conflict.title') : t('lesson.conflict.warningTitle')}
    >
      <ul className="space-y-1">
        {items.map((item, index) => (
          <li key={`${item.kind}-${index}`} className="flex flex-col">
            <span className="font-medium">{t(`lesson.conflict.${item.kind}`, item.kind)}</span>
            <span>{item.message}</span>
            {item.start_at && item.end_at && (
              <span className="opacity-80">
                {formatDate(item.start_at)} · {formatTimeRange(item.start_at, item.end_at)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </Alert>
  )
}

// ---------------------------------------------------------------------------
// Yeni ders formu
// ---------------------------------------------------------------------------
interface FormOptions {
  pools: Pool[]
  instructors: Instructor[]
  groups: Group[]
  defaultDate: Date
  onClose: () => void
  onCreated: () => void
}

function LessonFormModal({ pools, instructors, groups, defaultDate, onClose, onCreated }: FormOptions) {
  const { t } = useTranslation()

  const defaultStart = useMemo(() => {
    const date = new Date(defaultDate)
    date.setHours(17, 0, 0, 0)
    return date
  }, [defaultDate])

  const [title, setTitle] = useState('')
  const [lessonType, setLessonType] = useState<LessonType>('group')
  const [poolId, setPoolId] = useState(pools[0] ? String(pools[0].id) : '')
  const [laneId, setLaneId] = useState('')
  const [instructorId, setInstructorId] = useState('')
  const [groupId, setGroupId] = useState('')
  const [startAt, setStartAt] = useState(toISODateTime(defaultStart))
  const [endAt, setEndAt] = useState(toISODateTime(new Date(defaultStart.getTime() + 60 * 60_000)))
  const [capacity, setCapacity] = useState('10')
  const [price, setPrice] = useState('')
  const [color, setColor] = useState('#0ea5e9')
  const [formError, setFormError] = useState<string | null>(null)
  const [check, setCheck] = useState<ConflictCheckResponse | null>(null)

  const lanes = pools.find((pool) => String(pool.id) === poolId)?.lanes ?? []

  const payload = () => ({
    title: title.trim(),
    lesson_type: lessonType,
    start_at: startAt,
    end_at: endAt,
    pool_id: Number(poolId),
    lane_id: laneId ? Number(laneId) : null,
    instructor_id: instructorId ? Number(instructorId) : null,
    group_id: groupId ? Number(groupId) : null,
    capacity: Number(capacity) || 1,
    price: price ? Number(price) : null,
    color,
  })

  const createLesson = useMutation({
    mutationFn: (force: boolean) =>
      post<LessonDetail>('/lessons', { ...payload(), student_ids: [], force }),
    onSuccess: () => {
      toastSuccess(t('common.success'))
      onCreated()
    },
    onError: (mutationError) => {
      if (mutationError instanceof ApiError && mutationError.conflicts.length > 0) {
        setCheck({
          has_conflict: true,
          conflicts: mutationError.conflicts as unknown as ConflictItem[],
          warnings: [],
        })
      }
      toastError(mutationError)
    },
  })

  const checkConflicts = useMutation({
    mutationFn: () =>
      post<ConflictCheckResponse>('/lessons/check-conflicts', {
        start_at: startAt,
        end_at: endAt,
        pool_id: Number(poolId),
        lane_id: laneId ? Number(laneId) : null,
        instructor_id: instructorId ? Number(instructorId) : null,
        student_ids: [],
      }),
    onSuccess: (result) => {
      setCheck(result)
      // Çakışma yoksa doğrudan oluştur
      if (!result.has_conflict) createLesson.mutate(false)
    },
    onError: (mutationError) => toastError(mutationError),
  })

  function submit() {
    setFormError(null)
    setCheck(null)
    if (!title.trim()) return setFormError(t('common.required'))
    if (!poolId) return setFormError(t('common.required'))
    if (!startAt || !endAt || new Date(endAt) <= new Date(startAt)) {
      return setFormError(`${t('lesson.end')} > ${t('lesson.start')}`)
    }
    checkConflicts.mutate()
  }

  const busy = checkConflicts.isPending || createLesson.isPending

  return (
    <Modal
      open
      onClose={onClose}
      title={t('lesson.new')}
      size="lg"
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>
            {t('common.cancel')}
          </button>
          {check?.has_conflict ? (
            <button
              type="button"
              className="btn-danger"
              onClick={() => createLesson.mutate(true)}
              disabled={busy}
            >
              {busy && <Spinner />}
              {t('lesson.conflict.forceCreate')}
            </button>
          ) : (
            <button type="button" className="btn-primary" onClick={submit} disabled={busy}>
              {busy && <Spinner />}
              {t('common.save')}
            </button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        {formError && <Alert tone="danger">{formError}</Alert>}
        {check && !check.has_conflict && check.warnings.length === 0 && (
          <Alert tone="success">{t('lesson.conflict.noConflict')}</Alert>
        )}
        <ConflictList items={check?.conflicts ?? []} tone="danger" />
        <ConflictList items={check?.warnings ?? []} tone="warning" />

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t('lesson.lessonTitle')} required className="sm:col-span-2">
            <input
              className="input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={t('lesson.lessonTitle')}
            />
          </Field>
          <Field label={t('lesson.type')} required>
            <select
              className="select"
              value={lessonType}
              onChange={(event) => setLessonType(event.target.value as LessonType)}
            >
              {LESSON_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`lesson.types.${type}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('pool.singular')} required>
            <select
              className="select"
              value={poolId}
              onChange={(event) => {
                setPoolId(event.target.value)
                setLaneId('')
              }}
            >
              <option value="">—</option>
              {pools.map((pool) => (
                <option key={pool.id} value={pool.id}>
                  {pool.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('lane.singular')}>
            <select className="select" value={laneId} onChange={(event) => setLaneId(event.target.value)}>
              <option value="">{t('common.all')}</option>
              {lanes.map((lane) => (
                <option key={lane.id} value={lane.id}>
                  {lane.display_name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('instructor.singular')}>
            <select
              className="select"
              value={instructorId}
              onChange={(event) => setInstructorId(event.target.value)}
            >
              <option value="">—</option>
              {instructors.map((instructor) => (
                <option key={instructor.id} value={instructor.id}>
                  {instructor.full_name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('student.group')}>
            <select className="select" value={groupId} onChange={(event) => setGroupId(event.target.value)}>
              <option value="">—</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('lesson.start')} required>
            <input
              type="datetime-local"
              className="input"
              value={startAt}
              onChange={(event) => setStartAt(event.target.value)}
            />
          </Field>
          <Field label={t('lesson.end')} required>
            <input
              type="datetime-local"
              className="input"
              value={endAt}
              onChange={(event) => setEndAt(event.target.value)}
            />
          </Field>
          <Field label={t('lesson.capacity')} required>
            <input
              type="number"
              min={1}
              max={100}
              className="input"
              value={capacity}
              onChange={(event) => setCapacity(event.target.value)}
            />
          </Field>
          <Field label={t('lesson.price')}>
            <input
              type="number"
              min={0}
              step="0.01"
              className="input"
              value={price}
              onChange={(event) => setPrice(event.target.value)}
            />
          </Field>
          <Field label={t('lesson.color')}>
            <input
              type="color"
              className="input h-10 p-1"
              value={color}
              onChange={(event) => setColor(event.target.value)}
            />
          </Field>
        </div>
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Tekrarlanan ders (seri) formu
// ---------------------------------------------------------------------------
function SeriesFormModal({ pools, instructors, groups, defaultDate, onClose, onCreated }: FormOptions) {
  const { t } = useTranslation()

  const [title, setTitle] = useState('')
  const [lessonType, setLessonType] = useState<LessonType>('group')
  const [poolId, setPoolId] = useState(pools[0] ? String(pools[0].id) : '')
  const [laneId, setLaneId] = useState('')
  const [instructorId, setInstructorId] = useState('')
  const [groupId, setGroupId] = useState('')
  const [weekdays, setWeekdays] = useState<number[]>([0, 2, 4])
  const [startTime, setStartTime] = useState('17:00')
  const [endTime, setEndTime] = useState('18:00')
  const [startDate, setStartDate] = useState(toISODate(defaultDate))
  const [endDate, setEndDate] = useState(toISODate(addDays(defaultDate, 60)))
  const [capacity, setCapacity] = useState('10')
  const [color, setColor] = useState('#0ea5e9')
  const [skipHolidays, setSkipHolidays] = useState(true)
  const [force, setForce] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const lanes = pools.find((pool) => String(pool.id) === poolId)?.lanes ?? []

  const createSeries = useMutation({
    mutationFn: () =>
      post<LessonSeriesResult>('/lessons/series', {
        title: title.trim(),
        lesson_type: lessonType,
        pool_id: Number(poolId),
        lane_id: laneId ? Number(laneId) : null,
        instructor_id: instructorId ? Number(instructorId) : null,
        group_id: groupId ? Number(groupId) : null,
        weekdays,
        start_time: startTime,
        end_time: endTime,
        start_date: startDate,
        end_date: endDate,
        capacity: Number(capacity) || 1,
        color,
        student_ids: [],
        skip_holidays: skipHolidays,
        force,
      }),
    onSuccess: (result) => {
      toastSuccess(
        t('lesson.generatedLessons', { count: result.generated_lesson_count }),
        result.title,
      )
      onCreated()
    },
    onError: (mutationError) => toastError(mutationError),
  })

  function toggleWeekday(day: number) {
    setWeekdays((current) =>
      current.includes(day) ? current.filter((item) => item !== day) : [...current, day].sort(),
    )
  }

  function submit() {
    setFormError(null)
    if (!title.trim() || !poolId) return setFormError(t('common.required'))
    if (weekdays.length === 0) return setFormError(t('lesson.weekdays'))
    if (endTime <= startTime) return setFormError(`${t('lesson.end')} > ${t('lesson.start')}`)
    if (new Date(endDate) < new Date(startDate)) return setFormError(t('lesson.dateRange'))
    createSeries.mutate()
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t('lesson.newSeries')}
      size="lg"
      footer={
        <>
          <button
            type="button"
            className="btn-secondary"
            onClick={onClose}
            disabled={createSeries.isPending}
          >
            {t('common.cancel')}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={submit}
            disabled={createSeries.isPending}
          >
            {createSeries.isPending && <Spinner />}
            {t('common.save')}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {formError && <Alert tone="danger">{formError}</Alert>}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t('lesson.lessonTitle')} required className="sm:col-span-2">
            <input className="input" value={title} onChange={(event) => setTitle(event.target.value)} />
          </Field>
          <Field label={t('lesson.type')} required>
            <select
              className="select"
              value={lessonType}
              onChange={(event) => setLessonType(event.target.value as LessonType)}
            >
              {LESSON_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`lesson.types.${type}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('pool.singular')} required>
            <select
              className="select"
              value={poolId}
              onChange={(event) => {
                setPoolId(event.target.value)
                setLaneId('')
              }}
            >
              <option value="">—</option>
              {pools.map((pool) => (
                <option key={pool.id} value={pool.id}>
                  {pool.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('lane.singular')}>
            <select className="select" value={laneId} onChange={(event) => setLaneId(event.target.value)}>
              <option value="">{t('common.all')}</option>
              {lanes.map((lane) => (
                <option key={lane.id} value={lane.id}>
                  {lane.display_name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('instructor.singular')}>
            <select
              className="select"
              value={instructorId}
              onChange={(event) => setInstructorId(event.target.value)}
            >
              <option value="">—</option>
              {instructors.map((instructor) => (
                <option key={instructor.id} value={instructor.id}>
                  {instructor.full_name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('student.group')}>
            <select className="select" value={groupId} onChange={(event) => setGroupId(event.target.value)}>
              <option value="">—</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label={t('lesson.weekdays')} required>
          <div className="flex flex-wrap gap-1.5">
            {Array.from({ length: 7 }, (_, index) => index).map((day) => (
              <button
                key={day}
                type="button"
                onClick={() => toggleWeekday(day)}
                className={
                  weekdays.includes(day)
                    ? 'rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-medium text-white'
                    : 'rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700'
                }
              >
                {t(`weekdays.short.${day}`)}
              </button>
            ))}
          </div>
        </Field>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label={t('lesson.start')} required>
            <input
              type="time"
              className="input"
              value={startTime}
              onChange={(event) => setStartTime(event.target.value)}
            />
          </Field>
          <Field label={t('lesson.end')} required>
            <input
              type="time"
              className="input"
              value={endTime}
              onChange={(event) => setEndTime(event.target.value)}
            />
          </Field>
          <Field label={t('membership.startDate')} required>
            <input
              type="date"
              className="input"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </Field>
          <Field label={t('membership.endDate')} required>
            <input
              type="date"
              className="input"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </Field>
          <Field label={t('lesson.capacity')} required>
            <input
              type="number"
              min={1}
              max={100}
              className="input"
              value={capacity}
              onChange={(event) => setCapacity(event.target.value)}
            />
          </Field>
          <Field label={t('lesson.color')}>
            <input
              type="color"
              className="input h-10 p-1"
              value={color}
              onChange={(event) => setColor(event.target.value)}
            />
          </Field>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input
              type="checkbox"
              checked={skipHolidays}
              onChange={(event) => setSkipHolidays(event.target.checked)}
            />
            {t('lesson.skipHolidays')}
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input type="checkbox" checked={force} onChange={(event) => setForce(event.target.checked)} />
            {t('lesson.conflict.forceCreate')}
          </label>
        </div>
      </div>
    </Modal>
  )
}
