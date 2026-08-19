/** Kulvar planlama ekranı (saat × kulvar ızgarası) / Lane planning board. */
import { useQuery } from '@tanstack/react-query'
import { CalendarDays, Clock, Grid3x3, Percent, Search, Users, Waves } from 'lucide-react'
import { Fragment, useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  Spinner,
  StatCard,
  StatusBadge,
  TableWrapper,
} from '@/components/ui'
import { get } from '@/lib/api'
import {
  formatDuration,
  formatNumber,
  formatPercent,
  formatTime,
  formatTimeRange,
  toISODate,
} from '@/lib/format'
import { useAuth } from '@/lib/store'
import type {
  Instructor,
  Lane,
  LanePlan,
  LaneSlot,
  LessonDetail,
  Page,
  Pool,
} from '@/lib/types'

/** GET /pools/{id}/free-lanes yanıtı */
interface FreeLanesResponse {
  pool_id: number
  start_at: string
  end_at: string
  free_lane_count: number
  lanes: Array<{ id: number; lane_number: number; name: string }>
}

/** GET /pools/{id}/suggest-slots yanıtı */
interface SlotSuggestion {
  start_at: string
  end_at: string
  free_lane_count: number
  lane_ids: number[]
  lane_names: string[]
}

interface SuggestSlotsResponse {
  pool_id: number
  date: string
  count: number
  suggestions: SlotSuggestion[]
}

/** Izgara üzerinde konumlanmış bir ders bloğu */
interface PlanBlock {
  slot: LaneSlot
  startIndex: number
  span: number
}

/** Izgara dilim uzunluğu (dakika) */
const SLOT_MINUTES = 30
const DURATION_OPTIONS = [30, 45, 60, 90, 120]

/** "07:00:00" -> "07:00" */
function toInputTime(value: string | null | undefined): string {
  return (value ?? '').slice(0, 5)
}

/** "HH:MM" -> dakika */
function minutesOfTime(value: string): number {
  const [hours, minutes] = value.split(':')
  return Number(hours) * 60 + Number(minutes ?? 0)
}

/** Ders rengini hem açık hem koyu temada okunabilir bir blok stiline çevirir */
function blockStyle(color: string) {
  const base = /^#[0-9a-fA-F]{6}$/.test(color) ? color : '#0ea5e9'
  return { backgroundColor: `${base}33`, borderColor: base }
}

export default function LanePlanPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const canSchedule = can('lesson:schedule')
  const canReadInstructors = can('instructor:read')

  const [selectedPoolId, setSelectedPoolId] = useState<number | null>(null)
  const [day, setDay] = useState(() => toISODate(new Date()))
  const [lessonId, setLessonId] = useState<number | null>(null)

  // Boş kulvar arama
  const [freeRange, setFreeRange] = useState({ start: '09:00', end: '10:00' })
  const [freeParams, setFreeParams] = useState<{ start_at: string; end_at: string } | null>(null)

  // Uygun saat önerisi
  const [suggestForm, setSuggestForm] = useState({ duration: '60', instructorId: '' })
  const [suggestParams, setSuggestParams] = useState<{
    day: string
    duration_minutes: number
    instructor_id?: number
  } | null>(null)

  // --- Sorgular ---
  const poolsQuery = useQuery({
    queryKey: ['pools', 'list'],
    queryFn: () => get<Pool[]>('/pools'),
  })

  const pools = useMemo(() => poolsQuery.data ?? [], [poolsQuery.data])
  const activePoolId = selectedPoolId ?? pools[0]?.id ?? null
  const activePool = pools.find((pool) => pool.id === activePoolId) ?? null

  const lanesQuery = useQuery({
    queryKey: ['pool-lanes', activePoolId],
    queryFn: () => get<Lane[]>(`/pools/${activePoolId}/lanes`),
    enabled: activePoolId !== null,
  })

  const planQuery = useQuery({
    queryKey: ['lane-plan', activePoolId, day],
    queryFn: () => get<LanePlan>(`/pools/${activePoolId}/lane-plan`, { day }),
    enabled: activePoolId !== null,
  })

  const instructorsQuery = useQuery({
    queryKey: ['instructors', 'lane-plan'],
    queryFn: () => get<Page<Instructor>>('/instructors', { is_active: true, page_size: 100 }),
    enabled: canReadInstructors && canSchedule,
  })

  const freeLanesQuery = useQuery({
    queryKey: ['free-lanes', activePoolId, freeParams],
    queryFn: () =>
      get<FreeLanesResponse>(`/pools/${activePoolId}/free-lanes`, {
        start_at: freeParams?.start_at,
        end_at: freeParams?.end_at,
      }),
    enabled: activePoolId !== null && freeParams !== null,
  })

  const suggestQuery = useQuery({
    queryKey: ['suggest-slots', activePoolId, suggestParams],
    queryFn: () =>
      get<SuggestSlotsResponse>(`/pools/${activePoolId}/suggest-slots`, {
        day: suggestParams?.day,
        duration_minutes: suggestParams?.duration_minutes,
        instructor_id: suggestParams?.instructor_id,
      }),
    enabled: activePoolId !== null && suggestParams !== null,
  })

  const lessonQuery = useQuery({
    queryKey: ['lesson', lessonId],
    queryFn: () => get<LessonDetail>(`/lessons/${lessonId}`),
    enabled: lessonId !== null,
  })

  // --- Izgara hesapları ---
  const openMinutes = activePool ? minutesOfTime(toInputTime(activePool.opening_time)) : 0
  const closeMinutes = activePool ? minutesOfTime(toInputTime(activePool.closing_time)) : 0
  const slotCount = Math.max(1, Math.ceil((closeMinutes - openMinutes) / SLOT_MINUTES))

  const slotLabels = useMemo(() => {
    const labels: string[] = []
    for (let index = 0; index < slotCount; index += 1) {
      const reference = new Date(`${day}T00:00:00`)
      reference.setMinutes(openMinutes + index * SLOT_MINUTES)
      labels.push(formatTime(reference))
    }
    return labels
  }, [day, openMinutes, slotCount])

  const blocksByLane = useMemo(() => {
    const map = new Map<number, PlanBlock[]>()
    const slots = planQuery.data?.slots ?? []
    for (const slot of slots) {
      const start = new Date(slot.start_at)
      const end = new Date(slot.end_at)
      let startMinutes = start.getHours() * 60 + start.getMinutes()
      let endMinutes = end.getHours() * 60 + end.getMinutes()
      // Gece yarısına taşan ders bitişini havuz kapanışına sabitle
      if (endMinutes <= startMinutes) endMinutes = closeMinutes
      startMinutes = Math.max(startMinutes, openMinutes)
      endMinutes = Math.min(endMinutes, closeMinutes)
      if (endMinutes <= startMinutes) continue

      const startIndex = Math.max(0, Math.floor((startMinutes - openMinutes) / SLOT_MINUTES))
      const endIndex = Math.min(slotCount, Math.ceil((endMinutes - openMinutes) / SLOT_MINUTES))
      const list = map.get(slot.lane_id) ?? []
      list.push({ slot, startIndex, span: Math.max(1, endIndex - startIndex) })
      map.set(slot.lane_id, list)
    }
    return map
  }, [planQuery.data, openMinutes, closeMinutes, slotCount])

  const lanes = useMemo(
    () => [...(lanesQuery.data ?? [])].sort((a, b) => a.lane_number - b.lane_number),
    [lanesQuery.data],
  )

  // --- Olay işleyicileri ---
  function changePool(value: number) {
    setSelectedPoolId(value)
    setFreeParams(null)
    setSuggestParams(null)
  }

  function changeDay(value: string) {
    setDay(value)
    setFreeParams(null)
    setSuggestParams(null)
  }

  function submitFreeLanes(event: FormEvent) {
    event.preventDefault()
    setFreeParams({
      start_at: `${day}T${freeRange.start}:00`,
      end_at: `${day}T${freeRange.end}:00`,
    })
  }

  function submitSuggest(event: FormEvent) {
    event.preventDefault()
    const instructorId = Number(suggestForm.instructorId)
    setSuggestParams({
      day,
      duration_minutes: Number(suggestForm.duration),
      instructor_id: Number.isFinite(instructorId) && instructorId > 0 ? instructorId : undefined,
    })
  }

  const freeRangeValid = freeRange.end > freeRange.start

  if (poolsQuery.isLoading) return <LoadingState />
  if (poolsQuery.error) return <ErrorState error={poolsQuery.error} onRetry={poolsQuery.refetch} />

  const plan = planQuery.data ?? null
  const gridWidth = 128 + slotCount * 76

  return (
    <>
      <PageHeader
        title={t('lane.plan')}
        subtitle={t('lane.planSubtitle')}
        icon={<Grid3x3 className="h-5 w-5" />}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="select w-auto"
              value={activePoolId ?? ''}
              onChange={(event) => changePool(Number(event.target.value))}
              aria-label={t('pool.singular')}
            >
              {pools.map((pool) => (
                <option key={pool.id} value={pool.id}>
                  {pool.name}
                </option>
              ))}
            </select>
            <div className="flex items-center gap-1">
              <CalendarDays className="h-4 w-4 text-slate-400" />
              <input
                className="input w-auto"
                type="date"
                value={day}
                onChange={(event) => changeDay(event.target.value)}
                aria-label={t('common.date')}
              />
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => changeDay(toISODate(new Date()))}
            >
              {t('common.today')}
            </button>
          </div>
        }
      />

      {pools.length === 0 ? (
        <Card>
          <EmptyState title={t('common.noData')} icon={<Waves className="h-6 w-6" />} />
        </Card>
      ) : (
        <>
          {/* Günün özeti */}
          <div className="mb-6 grid gap-3 sm:grid-cols-3">
            <StatCard
              label={t('dashboard.lanesFree')}
              value={plan ? formatNumber(plan.free_lane_count) : '—'}
              hint={activePool?.name}
              icon={<Waves className="h-5 w-5" />}
              tone="success"
            />
            <StatCard
              label={t('dashboard.lanesInUse')}
              value={plan ? formatNumber(plan.used_lane_count) : '—'}
              hint={`${t('lane.title')}: ${formatNumber(lanes.length)}`}
              icon={<Grid3x3 className="h-5 w-5" />}
              tone="brand"
            />
            <StatCard
              label={t('dashboard.poolOccupancy')}
              value={plan ? formatPercent(plan.occupancy_rate) : '—'}
              hint={activePool?.operating_hours}
              icon={<Percent className="h-5 w-5" />}
              tone={
                plan && plan.occupancy_rate >= 85
                  ? 'danger'
                  : plan && plan.occupancy_rate >= 50
                    ? 'success'
                    : 'warning'
              }
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-4">
            {/* -------------------------------------------------------- */}
            {/* Saat × kulvar ızgarası                                     */}
            {/* -------------------------------------------------------- */}
            <Card
              title={`${activePool?.name ?? ''} · ${activePool?.operating_hours ?? ''}`}
              className="xl:col-span-3"
              bodyClassName="p-0"
              actions={
                <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <span className="h-3 w-3 rounded border border-slate-300 bg-slate-100 dark:border-slate-600 dark:bg-slate-800" />
                    {t('lane.free')}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span
                      className="h-3 w-3 rounded border-l-4"
                      style={blockStyle('#0ea5e9')}
                    />
                    {t('lane.occupied')}
                  </span>
                </div>
              }
            >
              {planQuery.isLoading || lanesQuery.isLoading ? (
                <LoadingState />
              ) : planQuery.error ? (
                <ErrorState error={planQuery.error} onRetry={planQuery.refetch} />
              ) : lanesQuery.error ? (
                <ErrorState error={lanesQuery.error} onRetry={lanesQuery.refetch} />
              ) : lanes.length === 0 ? (
                <EmptyState title={t('common.noData')} icon={<Grid3x3 className="h-6 w-6" />} />
              ) : (
                <div className="overflow-x-auto p-3">
                  <div
                    className="grid gap-px"
                    style={{
                      minWidth: gridWidth,
                      gridTemplateColumns: `128px repeat(${slotCount}, minmax(76px, 1fr))`,
                      gridTemplateRows: `28px repeat(${lanes.length}, 60px)`,
                    }}
                  >
                    {/* Başlık satırı */}
                    <div
                      className="sticky left-0 z-20 bg-white text-xs font-semibold text-slate-500 dark:bg-surface-dark-alt dark:text-slate-400"
                      style={{ gridColumn: 1, gridRow: 1 }}
                    >
                      {t('lane.singular')}
                    </div>
                    {slotLabels.map((label, index) => (
                      <div
                        key={label + index}
                        className={
                          index % 2 === 0
                            ? 'border-l border-slate-300 pl-1 text-[10px] font-medium text-slate-500 dark:border-slate-600 dark:text-slate-400'
                            : 'text-[10px] text-slate-400'
                        }
                        style={{ gridColumn: index + 2, gridRow: 1 }}
                      >
                        {index % 2 === 0 ? label : ''}
                      </div>
                    ))}

                    {/* Kulvar satırları */}
                    {lanes.map((lane, laneIndex) => (
                      <Fragment key={lane.id}>
                        <div
                          className="sticky left-0 z-20 flex flex-col justify-center bg-white pr-2 dark:bg-surface-dark-alt"
                          style={{ gridColumn: 1, gridRow: laneIndex + 2 }}
                        >
                          <span className="truncate text-sm font-medium text-slate-800 dark:text-slate-200">
                            {lane.display_name}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {lane.purpose ??
                              `${t('lane.maxSwimmers')}: ${formatNumber(lane.max_swimmers)}`}
                          </span>
                        </div>

                        {/* Boş dilimler */}
                        {Array.from({ length: slotCount }).map((_, index) => (
                          <div
                            key={`${lane.id}-${index}`}
                            className={
                              lane.is_active
                                ? 'rounded-sm border-l border-slate-200 bg-slate-100/70 dark:border-slate-700 dark:bg-slate-800/60'
                                : 'rounded-sm border-l border-slate-200 bg-slate-200/60 dark:border-slate-700 dark:bg-slate-900/60'
                            }
                            style={{ gridColumn: index + 2, gridRow: laneIndex + 2 }}
                          />
                        ))}

                        {/* Ders blokları */}
                        {(blocksByLane.get(lane.id) ?? []).map((block) => (
                          <button
                            key={block.slot.lesson_id ?? `${lane.id}-${block.startIndex}`}
                            type="button"
                            onClick={() =>
                              block.slot.lesson_id !== null &&
                              block.slot.lesson_id !== undefined &&
                              setLessonId(block.slot.lesson_id)
                            }
                            title={`${block.slot.lesson_title ?? ''} · ${formatTimeRange(
                              block.slot.start_at,
                              block.slot.end_at,
                            )}`}
                            className="relative z-10 m-0.5 overflow-hidden rounded-md border border-l-4 px-1.5 py-1 text-left transition-shadow hover:shadow-panel"
                            style={{
                              ...blockStyle(block.slot.color),
                              gridColumn: `${block.startIndex + 2} / span ${block.span}`,
                              gridRow: laneIndex + 2,
                            }}
                          >
                            <span className="block truncate text-[11px] font-semibold text-slate-900 dark:text-slate-100">
                              {block.slot.lesson_title ?? t('lesson.singular')}
                            </span>
                            <span className="block truncate text-[10px] text-slate-600 dark:text-slate-300">
                              {formatTimeRange(block.slot.start_at, block.slot.end_at)}
                            </span>
                            <span className="block truncate text-[10px] text-slate-600 dark:text-slate-300">
                              {block.slot.instructor_name ?? '—'} · {block.slot.enrolled}/
                              {block.slot.capacity}
                            </span>
                          </button>
                        ))}
                      </Fragment>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            {/* -------------------------------------------------------- */}
            {/* Sağ panel                                                 */}
            {/* -------------------------------------------------------- */}
            <div className="space-y-4 xl:sticky xl:top-4 xl:self-start">
              {/* Boş kulvar bul */}
              <Card title={t('lane.findFree')}>
                <form className="space-y-3" onSubmit={submitFreeLanes}>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label={t('lesson.start')} required>
                      <input
                        className="input"
                        type="time"
                        required
                        value={freeRange.start}
                        onChange={(event) =>
                          setFreeRange((prev) => ({ ...prev, start: event.target.value }))
                        }
                      />
                    </Field>
                    <Field label={t('lesson.end')} required>
                      <input
                        className="input"
                        type="time"
                        required
                        value={freeRange.end}
                        onChange={(event) =>
                          setFreeRange((prev) => ({ ...prev, end: event.target.value }))
                        }
                      />
                    </Field>
                  </div>
                  <button
                    type="submit"
                    className="btn-primary w-full"
                    disabled={!freeRangeValid || activePoolId === null}
                  >
                    <Search className="h-4 w-4" />
                    {t('common.search')}
                  </button>
                </form>

                {freeParams !== null && (
                  <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-700">
                    {freeLanesQuery.isFetching ? (
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <Spinner />
                        {t('common.loading')}
                      </div>
                    ) : freeLanesQuery.error ? (
                      <ErrorState
                        error={freeLanesQuery.error}
                        onRetry={freeLanesQuery.refetch}
                      />
                    ) : (freeLanesQuery.data?.lanes.length ?? 0) === 0 ? (
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {t('common.noResults')}
                      </p>
                    ) : (
                      <>
                        <p className="mb-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                          {t('lane.freeCount', { count: freeLanesQuery.data?.free_lane_count ?? 0 })}
                        </p>
                        <ul className="flex flex-wrap gap-1.5">
                          {(freeLanesQuery.data?.lanes ?? []).map((lane) => (
                            <li key={lane.id}>
                              <Badge tone="success">{lane.name}</Badge>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </Card>

              {/* Uygun saat öner */}
              {canSchedule && (
                <Card title={t('lane.suggestSlots')}>
                  <form className="space-y-3" onSubmit={submitSuggest}>
                    <Field label={t('lesson.duration')} required>
                      <select
                        className="select"
                        value={suggestForm.duration}
                        onChange={(event) =>
                          setSuggestForm((prev) => ({ ...prev, duration: event.target.value }))
                        }
                      >
                        {DURATION_OPTIONS.map((minutes) => (
                          <option key={minutes} value={minutes}>
                            {formatDuration(minutes)}
                          </option>
                        ))}
                      </select>
                    </Field>
                    {canReadInstructors && (
                      <Field label={t('instructor.singular')}>
                        <select
                          className="select"
                          value={suggestForm.instructorId}
                          onChange={(event) =>
                            setSuggestForm((prev) => ({
                              ...prev,
                              instructorId: event.target.value,
                            }))
                          }
                        >
                          <option value="">{t('common.all')}</option>
                          {(instructorsQuery.data?.items ?? []).map((instructor) => (
                            <option key={instructor.id} value={instructor.id}>
                              {instructor.full_name}
                            </option>
                          ))}
                        </select>
                      </Field>
                    )}
                    <button
                      type="submit"
                      className="btn-primary w-full"
                      disabled={activePoolId === null}
                    >
                      <Clock className="h-4 w-4" />
                      {t('lane.suggestSlots')}
                    </button>
                  </form>

                  {suggestParams !== null && (
                    <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-700">
                      {suggestQuery.isFetching ? (
                        <div className="flex items-center gap-2 text-sm text-slate-500">
                          <Spinner />
                          {t('common.loading')}
                        </div>
                      ) : suggestQuery.error ? (
                        <ErrorState error={suggestQuery.error} onRetry={suggestQuery.refetch} />
                      ) : (suggestQuery.data?.suggestions.length ?? 0) === 0 ? (
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                          {t('common.noResults')}
                        </p>
                      ) : (
                        <ul className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
                          {(suggestQuery.data?.suggestions ?? []).map((suggestion) => (
                            <li
                              key={suggestion.start_at}
                              className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm dark:border-slate-700"
                            >
                              <span className="font-medium text-slate-800 dark:text-slate-200">
                                {formatTimeRange(suggestion.start_at, suggestion.end_at)}
                              </span>
                              <Badge tone="info">
                                {t('lane.freeCount', { count: suggestion.free_lane_count })}
                              </Badge>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </Card>
              )}
            </div>
          </div>
        </>
      )}

      {/* -------------------------------------------------------------- */}
      {/* Ders detay modalı                                               */}
      {/* -------------------------------------------------------------- */}
      <Modal
        open={lessonId !== null}
        onClose={() => setLessonId(null)}
        title={lessonQuery.data?.title ?? t('lesson.singular')}
        size="lg"
      >
        {lessonQuery.isLoading ? (
          <LoadingState />
        ) : lessonQuery.error ? (
          <ErrorState error={lessonQuery.error} onRetry={lessonQuery.refetch} />
        ) : lessonQuery.data ? (
          <div className="space-y-4">
            <dl className="grid gap-3 text-xs sm:grid-cols-3">
              <div>
                <dt className="text-slate-500 dark:text-slate-400">{t('common.time')}</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {formatTimeRange(lessonQuery.data.start_at, lessonQuery.data.end_at)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">{t('lesson.type')}</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {t(`lesson.types.${lessonQuery.data.lesson_type}`, lessonQuery.data.lesson_type)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">{t('common.status')}</dt>
                <dd>
                  <StatusBadge
                    status={lessonQuery.data.status}
                    label={t(`lesson.statuses.${lessonQuery.data.status}`)}
                  />
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">{t('pool.singular')}</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {lessonQuery.data.pool_name ?? '—'}
                  {lessonQuery.data.lane_name ? ` · ${lessonQuery.data.lane_name}` : ''}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">{t('instructor.singular')}</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {lessonQuery.data.instructor_name ?? '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">{t('lesson.occupancy')}</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {lessonQuery.data.enrolled_count}/{lessonQuery.data.capacity} ·{' '}
                  {formatPercent(lessonQuery.data.occupancy_rate)}
                </dd>
              </div>
            </dl>

            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              {t('lesson.roster')}
            </h3>
            {lessonQuery.data.enrollments.length === 0 ? (
              <EmptyState title={t('common.noData')} icon={<Users className="h-6 w-6" />} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('student.number')}</th>
                    <th>{t('student.fullName')}</th>
                    <th>{t('common.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {lessonQuery.data.enrollments.map((enrollment) => (
                    <tr key={enrollment.id}>
                      <td className="whitespace-nowrap font-medium">
                        {enrollment.student_number ?? '—'}
                      </td>
                      <td>{enrollment.student_name ?? '—'}</td>
                      <td>
                        <Badge
                          tone={
                            enrollment.status === 'enrolled'
                              ? 'success'
                              : enrollment.status === 'cancelled'
                                ? 'danger'
                                : 'warning'
                          }
                        >
                          {enrollment.status === 'enrolled'
                            ? t('lesson.enrolled')
                            : enrollment.status === 'cancelled'
                              ? t('lesson.statuses.cancelled')
                              : enrollment.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </div>
        ) : null}
      </Modal>
    </>
  )
}
