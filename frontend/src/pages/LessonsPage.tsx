/** Ders ve seri yönetimi: filtreli liste, kayıt, iptal ve silme işlemleri. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Ban,
  CalendarDays,
  ClipboardList,
  Eye,
  Repeat,
  Trash2,
  UserMinus,
  UserPlus,
  Users,
} from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import {
  Alert,
  Badge,
  Card,
  ConfirmDialog,
  DemoBadge,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  Pagination,
  ProgressBar,
  Spinner,
  StatusBadge,
  TableWrapper,
  Tabs,
} from '@/components/ui'
import { del, get, post } from '@/lib/api'
import {
  formatCurrency,
  formatDate,
  formatDateLong,
  formatNumber,
  formatPercent,
  formatTimeRange,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  Enrollment,
  Group,
  Instructor,
  Lesson,
  LessonDetail,
  LessonStatus,
  LessonType,
  Message,
  Page,
  Pool,
  Student,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler ve yerel tipler
// ---------------------------------------------------------------------------
const LESSON_TYPES: LessonType[] = [
  'group', 'private', 'kids', 'baby', 'adult', 'beginner', 'intermediate',
  'advanced', 'competition_team', 'adaptive', 'conditioning', 'trial', 'makeup',
]

const LESSON_STATUSES: LessonStatus[] = [
  'scheduled', 'in_progress', 'completed', 'cancelled', 'postponed',
]

/** GET /lessons/series yanıt satırı (backend LessonSeriesOut) */
interface LessonSeries {
  id: number
  title: string
  lesson_type: LessonType
  pool_id: number
  lane_id?: number | null
  instructor_id?: number | null
  group_id?: number | null
  weekdays: number[]
  start_time: string
  end_time: string
  start_date: string
  end_date: string
  capacity: number
  color: string
  notes?: string | null
  is_active: boolean
  generated_lesson_count: number
}

interface LessonFilters {
  date_from: string
  date_to: string
  pool_id: string
  instructor_id: string
  group_id: string
  lesson_type: string
  status: string
}

const EMPTY_FILTERS: LessonFilters = {
  date_from: '',
  date_to: '',
  pool_id: '',
  instructor_id: '',
  group_id: '',
  lesson_type: '',
  status: '',
}

/** Seri saat aralığını yerel biçimde gösterir (time alanları "HH:MM:SS" gelir) */
function seriesTimeRange(series: LessonSeries): string {
  return formatTimeRange(
    `${series.start_date}T${series.start_time}`,
    `${series.start_date}T${series.end_time}`,
  )
}

// ---------------------------------------------------------------------------
// Sayfa
// ---------------------------------------------------------------------------
export default function LessonsPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<'lessons' | 'series'>('lessons')
  const [filters, setFilters] = useState<LessonFilters>(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const [detailId, setDetailId] = useState<number | null>(null)
  const [enrollFor, setEnrollFor] = useState<number | null>(null)
  const [cancelTarget, setCancelTarget] = useState<Lesson | null>(null)
  const [cancelReason, setCancelReason] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<Lesson | null>(null)
  const [unenrollTarget, setUnenrollTarget] = useState<
    { lessonId: number; studentId: number; name: string } | null
  >(null)
  const [seriesTarget, setSeriesTarget] = useState<LessonSeries | null>(null)
  const [seriesFutureOnly, setSeriesFutureOnly] = useState(true)

  function updateFilter(key: keyof LessonFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }))
    setPage(1)
  }

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

  const lessonsQuery = useQuery({
    queryKey: ['lessons', page, pageSize, filters],
    queryFn: () =>
      get<Page<Lesson>>('/lessons', {
        page,
        page_size: pageSize,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        pool_id: filters.pool_id || undefined,
        instructor_id: filters.instructor_id || undefined,
        group_id: filters.group_id || undefined,
        lesson_type: filters.lesson_type || undefined,
        status: filters.status || undefined,
      }),
    enabled: tab === 'lessons',
  })

  const seriesQuery = useQuery({
    queryKey: ['lesson-series'],
    queryFn: () => get<LessonSeries[]>('/lessons/series'),
    enabled: tab === 'series',
  })

  const detailQuery = useQuery({
    queryKey: ['lesson', detailId],
    queryFn: () => get<LessonDetail>(`/lessons/${detailId}`),
    enabled: detailId !== null,
  })

  function invalidateLessons() {
    void queryClient.invalidateQueries({ queryKey: ['lessons'] })
    void queryClient.invalidateQueries({ queryKey: ['lesson'] })
    void queryClient.invalidateQueries({ queryKey: ['calendar'] })
  }

  const cancelLesson = useMutation({
    mutationFn: (payload: { id: number; reason: string }) =>
      post<Message>(`/lessons/${payload.id}/cancel`, undefined, { reason: payload.reason }),
    onSuccess: () => {
      invalidateLessons()
      toastSuccess(t('common.success'))
      setCancelTarget(null)
      setCancelReason('')
    },
    onError: (error) => toastError(error),
  })

  const deleteLesson = useMutation({
    mutationFn: (id: number) => del<Message>(`/lessons/${id}`),
    onSuccess: () => {
      invalidateLessons()
      toastSuccess(t('common.success'))
      setDeleteTarget(null)
      setDetailId(null)
    },
    onError: (error) => toastError(error),
  })

  const unenroll = useMutation({
    mutationFn: (payload: { lessonId: number; studentId: number }) =>
      del<Message>(`/lessons/${payload.lessonId}/enroll/${payload.studentId}`),
    onSuccess: () => {
      invalidateLessons()
      toastSuccess(t('common.success'))
      setUnenrollTarget(null)
    },
    onError: (error) => toastError(error),
  })

  const deleteSeries = useMutation({
    mutationFn: (payload: { id: number; futureOnly: boolean }) =>
      del<Message>(`/lessons/series/${payload.id}`, { future_only: payload.futureOnly }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ['lesson-series'] })
      invalidateLessons()
      const removed = Number(result.data?.removed ?? 0)
      toastSuccess(t('common.success'), `${formatNumber(removed)} ${t('lesson.title').toLowerCase()}`)
      setSeriesTarget(null)
    },
    onError: (error) => toastError(error),
  })

  const lessons = lessonsQuery.data?.items ?? []
  const detail = detailQuery.data

  const tabs = useMemo(
    () => [
      {
        id: 'lessons',
        label: t('lesson.title'),
        icon: <CalendarDays className="h-4 w-4" />,
        badge: lessonsQuery.data?.total ?? 0,
      },
      {
        id: 'series',
        label: t('lesson.series'),
        icon: <Repeat className="h-4 w-4" />,
        badge: seriesQuery.data?.length ?? 0,
      },
    ],
    [t, lessonsQuery.data, seriesQuery.data],
  )

  return (
    <>
      <PageHeader
        title={t('lesson.title')}
        subtitle={`${t('common.total')}: ${formatNumber(lessonsQuery.data?.total ?? 0)}`}
        icon={<CalendarDays className="h-5 w-5" />}
        actions={
          <Link to="/calendar" className="btn-secondary">
            <CalendarDays className="h-4 w-4" />
            {t('calendar.title')}
          </Link>
        }
      />

      <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as 'lessons' | 'series')} />

      {tab === 'lessons' ? (
        <>
          {/* Filtreler */}
          <Card title={t('common.filters')} className="mb-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Field label={t('lesson.start')}>
                <input
                  type="date"
                  className="input"
                  value={filters.date_from}
                  onChange={(event) => updateFilter('date_from', event.target.value)}
                />
              </Field>
              <Field label={t('lesson.end')}>
                <input
                  type="date"
                  className="input"
                  value={filters.date_to}
                  onChange={(event) => updateFilter('date_to', event.target.value)}
                />
              </Field>
              <Field label={t('pool.singular')}>
                <select
                  className="select"
                  value={filters.pool_id}
                  onChange={(event) => updateFilter('pool_id', event.target.value)}
                >
                  <option value="">{t('common.all')}</option>
                  {(pools ?? []).map((pool) => (
                    <option key={pool.id} value={pool.id}>
                      {pool.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('instructor.singular')}>
                <select
                  className="select"
                  value={filters.instructor_id}
                  onChange={(event) => updateFilter('instructor_id', event.target.value)}
                >
                  <option value="">{t('common.all')}</option>
                  {(instructors?.items ?? []).map((instructor) => (
                    <option key={instructor.id} value={instructor.id}>
                      {instructor.full_name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('student.group')}>
                <select
                  className="select"
                  value={filters.group_id}
                  onChange={(event) => updateFilter('group_id', event.target.value)}
                >
                  <option value="">{t('common.all')}</option>
                  {(groups ?? []).map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('lesson.type')}>
                <select
                  className="select"
                  value={filters.lesson_type}
                  onChange={(event) => updateFilter('lesson_type', event.target.value)}
                >
                  <option value="">{t('common.all')}</option>
                  {LESSON_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {t(`lesson.types.${type}`)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('common.status')}>
                <select
                  className="select"
                  value={filters.status}
                  onChange={(event) => updateFilter('status', event.target.value)}
                >
                  <option value="">{t('common.all')}</option>
                  {LESSON_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {t(`lesson.statuses.${status}`)}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="flex items-end gap-2">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    setFilters(EMPTY_FILTERS)
                    setPage(1)
                  }}
                >
                  {t('common.clearFilters')}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void lessonsQuery.refetch()}
                >
                  {t('common.refresh')}
                </button>
              </div>
            </div>
          </Card>

          {/* Ders tablosu */}
          <Card bodyClassName="p-0">
            {lessonsQuery.isLoading ? (
              <LoadingState />
            ) : lessonsQuery.error ? (
              <ErrorState error={lessonsQuery.error} onRetry={lessonsQuery.refetch} />
            ) : lessons.length === 0 ? (
              <EmptyState
                title={t('common.noResults')}
                description={t('calendar.noEvents')}
                icon={<CalendarDays className="h-6 w-6" />}
              />
            ) : (
              <>
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('common.date')}</th>
                      <th>{t('lesson.singular')}</th>
                      <th className="hidden md:table-cell">{t('lesson.type')}</th>
                      <th className="hidden lg:table-cell">{t('pool.singular')}</th>
                      <th className="hidden lg:table-cell">{t('instructor.singular')}</th>
                      <th>{t('lesson.enrolled')}</th>
                      <th>{t('common.status')}</th>
                      <th className="text-right">{t('common.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lessons.map((lesson) => {
                      const occupancy =
                        lesson.capacity > 0 ? (lesson.enrolled_count / lesson.capacity) * 100 : 0
                      return (
                        <tr key={lesson.id}>
                          <td className="whitespace-nowrap">
                            <p className="font-medium text-slate-800 dark:text-slate-100">
                              {formatDate(lesson.start_at)}
                            </p>
                            <p className="text-xs text-slate-500">
                              {formatTimeRange(lesson.start_at, lesson.end_at)}
                            </p>
                          </td>
                          <td>
                            <div className="flex items-center gap-2">
                              <span
                                className="h-2.5 w-2.5 shrink-0 rounded-full"
                                style={{ backgroundColor: lesson.color }}
                              />
                              <button
                                type="button"
                                className="text-left hover:text-brand-600 dark:hover:text-brand-400"
                                onClick={() => setDetailId(lesson.id)}
                              >
                                {lesson.title}
                              </button>
                              {lesson.is_demo && <DemoBadge />}
                            </div>
                          </td>
                          <td className="hidden md:table-cell text-xs text-slate-500">
                            {t(`lesson.types.${lesson.lesson_type}`)}
                          </td>
                          <td className="hidden lg:table-cell text-xs text-slate-500">
                            {lesson.pool_name ?? '—'}
                            {lesson.lane_name ? ` · ${lesson.lane_name}` : ''}
                          </td>
                          <td className="hidden lg:table-cell text-xs text-slate-500">
                            {lesson.instructor_name ?? '—'}
                          </td>
                          <td className="min-w-[120px]">
                            <p className="mb-1 text-xs text-slate-600 dark:text-slate-300">
                              {formatNumber(lesson.enrolled_count)} / {formatNumber(lesson.capacity)}
                            </p>
                            <ProgressBar
                              value={occupancy}
                              tone={occupancy >= 100 ? 'danger' : occupancy >= 70 ? 'success' : 'brand'}
                            />
                          </td>
                          <td>
                            <StatusBadge
                              status={lesson.status}
                              label={t(`lesson.statuses.${lesson.status}`)}
                            />
                          </td>
                          <td>
                            <div className="flex items-center justify-end gap-1">
                              <button
                                type="button"
                                className="btn-ghost btn-sm"
                                onClick={() => setDetailId(lesson.id)}
                                title={t('common.details')}
                                aria-label={t('common.details')}
                              >
                                <Eye className="h-4 w-4" />
                              </button>
                              {can('lesson:write') && (
                                <button
                                  type="button"
                                  className="btn-ghost btn-sm"
                                  onClick={() => setEnrollFor(lesson.id)}
                                  title={t('lesson.enroll')}
                                  aria-label={t('lesson.enroll')}
                                >
                                  <UserPlus className="h-4 w-4" />
                                </button>
                              )}
                              {can('lesson:write') && lesson.status !== 'cancelled' && (
                                <button
                                  type="button"
                                  className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                                  onClick={() => {
                                    setCancelReason('')
                                    setCancelTarget(lesson)
                                  }}
                                  title={t('lesson.cancel')}
                                  aria-label={t('lesson.cancel')}
                                >
                                  <Ban className="h-4 w-4" />
                                </button>
                              )}
                              {can('lesson:delete') && (
                                <button
                                  type="button"
                                  className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                                  onClick={() => setDeleteTarget(lesson)}
                                  title={t('common.delete')}
                                  aria-label={t('common.delete')}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </TableWrapper>
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={lessonsQuery.data?.total ?? 0}
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
      ) : (
        /* ------------------------------- SERİLER ------------------------------- */
        <Card bodyClassName="p-0">
          {seriesQuery.isLoading ? (
            <LoadingState />
          ) : seriesQuery.error ? (
            <ErrorState error={seriesQuery.error} onRetry={seriesQuery.refetch} />
          ) : (seriesQuery.data ?? []).length === 0 ? (
            <EmptyState
              title={t('common.noData')}
              description={t('lesson.newSeries')}
              icon={<Repeat className="h-6 w-6" />}
              action={
                <Link to="/calendar" className="btn-primary btn-sm">
                  {t('lesson.newSeries')}
                </Link>
              }
            />
          ) : (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('lesson.lessonTitle')}</th>
                  <th>{t('lesson.weekdays')}</th>
                  <th>{t('common.time')}</th>
                  <th className="hidden md:table-cell">{t('lesson.dateRange')}</th>
                  <th>{t('instructor.lessonCount')}</th>
                  <th>{t('common.status')}</th>
                  <th className="text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {(seriesQuery.data ?? []).map((series) => (
                  <tr key={series.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: series.color }}
                        />
                        <div>
                          <p className="font-medium text-slate-800 dark:text-slate-100">
                            {series.title}
                          </p>
                          <p className="text-xs text-slate-500">
                            {t(`lesson.types.${series.lesson_type}`)}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {series.weekdays.map((day) => (
                          <span
                            key={day}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                          >
                            {t(`weekdays.short.${day}`)}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="whitespace-nowrap text-sm">{seriesTimeRange(series)}</td>
                    <td className="hidden md:table-cell whitespace-nowrap text-xs text-slate-500">
                      {formatDate(series.start_date)} – {formatDate(series.end_date)}
                    </td>
                    <td>
                      <Badge tone="info">{formatNumber(series.generated_lesson_count)}</Badge>
                    </td>
                    <td>
                      <StatusBadge
                        status={series.is_active ? 'active' : 'passive'}
                        label={series.is_active ? t('common.active') : t('common.passive')}
                      />
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          to={`/calendar?series=${series.id}`}
                          className="btn-ghost btn-sm"
                          title={t('calendar.title')}
                          aria-label={t('calendar.title')}
                        >
                          <CalendarDays className="h-4 w-4" />
                        </Link>
                        {can('lesson:delete') && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            onClick={() => {
                              setSeriesFutureOnly(true)
                              setSeriesTarget(series)
                            }}
                            title={t('common.delete')}
                            aria-label={t('common.delete')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </Card>
      )}

      {/* ------------------------------ DETAY MODALI ------------------------------ */}
      <Modal
        open={detailId !== null}
        onClose={() => setDetailId(null)}
        title={detail?.title ?? t('lesson.singular')}
        size="lg"
        footer={
          detail && (
            <>
              <Link
                to={`/attendance?lesson=${detail.id}`}
                className="btn-secondary"
                onClick={() => setDetailId(null)}
              >
                <ClipboardList className="h-4 w-4" />
                {t('attendance.take')}
              </Link>
              {can('lesson:write') && (
                <button type="button" className="btn-primary" onClick={() => setEnrollFor(detail.id)}>
                  <UserPlus className="h-4 w-4" />
                  {t('lesson.enroll')}
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
        ) : detail ? (
          <LessonDetailBody
            detail={detail}
            canWrite={can('lesson:write')}
            onUnenroll={(studentId, name) =>
              setUnenrollTarget({ lessonId: detail.id, studentId, name })
            }
          />
        ) : null}
      </Modal>

      {/* ---------------------------- ÖĞRENCİ EKLEME ---------------------------- */}
      {enrollFor !== null && (
        <EnrollModal
          lessonId={enrollFor}
          onClose={() => setEnrollFor(null)}
          onDone={() => {
            setEnrollFor(null)
            invalidateLessons()
          }}
        />
      )}

      {/* ------------------------------- ONAYLAR ------------------------------- */}
      <ConfirmDialog
        open={cancelTarget !== null}
        onClose={() => setCancelTarget(null)}
        onConfirm={() => {
          if (cancelTarget && cancelReason.trim()) {
            cancelLesson.mutate({ id: cancelTarget.id, reason: cancelReason.trim() })
          }
        }}
        title={t('lesson.cancel')}
        confirmLabel={t('lesson.cancel')}
        loading={cancelLesson.isPending}
        message={
          <div className="space-y-3">
            <p>{cancelTarget?.title}</p>
            <Field label={t('lesson.cancelReason')} required>
              <textarea
                className="textarea"
                rows={3}
                value={cancelReason}
                onChange={(event) => setCancelReason(event.target.value)}
              />
            </Field>
          </div>
        }
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteLesson.mutate(deleteTarget.id)}
        title={t('common.delete')}
        confirmLabel={t('common.delete')}
        loading={deleteLesson.isPending}
        message={
          <span>
            {deleteTarget?.title} · {deleteTarget ? formatDateLong(deleteTarget.start_at) : ''}
          </span>
        }
      />

      <ConfirmDialog
        open={unenrollTarget !== null}
        onClose={() => setUnenrollTarget(null)}
        onConfirm={() =>
          unenrollTarget &&
          unenroll.mutate({
            lessonId: unenrollTarget.lessonId,
            studentId: unenrollTarget.studentId,
          })
        }
        title={t('lesson.unenroll')}
        confirmLabel={t('lesson.unenroll')}
        loading={unenroll.isPending}
        message={<span>{unenrollTarget?.name}</span>}
      />

      <ConfirmDialog
        open={seriesTarget !== null}
        onClose={() => setSeriesTarget(null)}
        onConfirm={() =>
          seriesTarget &&
          deleteSeries.mutate({ id: seriesTarget.id, futureOnly: seriesFutureOnly })
        }
        title={t('common.delete')}
        confirmLabel={t('common.delete')}
        loading={deleteSeries.isPending}
        message={
          <div className="space-y-3">
            <p>{seriesTarget?.title}</p>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={seriesFutureOnly}
                onChange={(event) => setSeriesFutureOnly(event.target.checked)}
              />
              {t('guardian.upcomingLessons')}
            </label>
          </div>
        }
      />
    </>
  )
}

// ---------------------------------------------------------------------------
// Ders detay gövdesi (roster dahil)
// ---------------------------------------------------------------------------
function LessonDetailBody({
  detail,
  canWrite,
  onUnenroll,
}: {
  detail: LessonDetail
  canWrite: boolean
  onUnenroll: (studentId: number, name: string) => void
}) {
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
          label={t('lesson.occupancy')}
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
          <TableWrapper>
            <thead>
              <tr>
                <th>{t('student.number')}</th>
                <th>{t('student.fullName')}</th>
                <th>{t('common.status')}</th>
                {canWrite && <th className="text-right">{t('common.actions')}</th>}
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
                  {canWrite && (
                    <td>
                      <div className="flex justify-end">
                        <button
                          type="button"
                          className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                          onClick={() =>
                            onUnenroll(
                              enrollment.student_id,
                              enrollment.student_name ?? `#${enrollment.student_id}`,
                            )
                          }
                          title={t('lesson.unenroll')}
                          aria-label={t('lesson.unenroll')}
                        >
                          <UserMinus className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </TableWrapper>
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
// Çoklu öğrenci seçici + kayıt
// ---------------------------------------------------------------------------
function EnrollModal({
  lessonId,
  onClose,
  onDone,
}: {
  lessonId: number
  onClose: () => void
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<Student[]>([])
  const [useMembership, setUseMembership] = useState(true)
  const [force, setForce] = useState(false)

  const studentsQuery = useQuery({
    queryKey: ['students', 'picker', query],
    queryFn: () =>
      get<Page<Student>>('/students', {
        q: query || undefined,
        status: 'active',
        page: 1,
        page_size: 20,
      }),
    staleTime: 60_000,
  })

  const enroll = useMutation({
    mutationFn: () =>
      post<Enrollment[]>(`/lessons/${lessonId}/enroll`, {
        student_ids: selected.map((student) => student.id),
        use_membership: useMembership,
        force,
      }),
    onSuccess: () => {
      toastSuccess(t('common.success'), `${formatNumber(selected.length)} ${t('student.singular')}`)
      onDone()
    },
    onError: (error) => toastError(error),
  })

  function toggle(student: Student) {
    setSelected((current) =>
      current.some((item) => item.id === student.id)
        ? current.filter((item) => item.id !== student.id)
        : [...current, student],
    )
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t('lesson.enroll')}
      size="lg"
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose} disabled={enroll.isPending}>
            {t('common.cancel')}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => enroll.mutate()}
            disabled={selected.length === 0 || enroll.isPending}
          >
            {enroll.isPending && <Spinner />}
            {t('common.save')}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label={t('common.search')}>
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('common.searchPlaceholder')}
          />
        </Field>

        {selected.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {selected.map((student) => (
              <button
                key={student.id}
                type="button"
                onClick={() => toggle(student)}
                className="flex items-center gap-1 rounded-full bg-brand-100 px-2.5 py-1 text-xs text-brand-800 hover:bg-brand-200 dark:bg-brand-900/40 dark:text-brand-200 dark:hover:bg-brand-900/70"
              >
                {student.full_name}
                <UserMinus className="h-3 w-3" />
              </button>
            ))}
            <span className="self-center text-xs text-slate-500">
              {formatNumber(selected.length)} {t('common.selected')}
            </span>
          </div>
        )}

        <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-700">
          {studentsQuery.isLoading ? (
            <LoadingState />
          ) : studentsQuery.error ? (
            <ErrorState error={studentsQuery.error} onRetry={studentsQuery.refetch} />
          ) : (studentsQuery.data?.items ?? []).length === 0 ? (
            <EmptyState title={t('common.noResults')} />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-700">
              {(studentsQuery.data?.items ?? []).map((student) => {
                const checked = selected.some((item) => item.id === student.id)
                return (
                  <li key={student.id}>
                    <label className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/40">
                      <input type="checkbox" checked={checked} onChange={() => toggle(student)} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm text-slate-800 dark:text-slate-100">
                          {student.full_name}
                        </p>
                        <p className="truncate text-xs text-slate-500">
                          {student.student_number} · {t(`swimLevel.${student.swim_level}`)}
                        </p>
                      </div>
                      {student.is_demo && <DemoBadge />}
                    </label>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input
              type="checkbox"
              checked={useMembership}
              onChange={(event) => setUseMembership(event.target.checked)}
            />
            {t('attendance.consumeCredits')}
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
