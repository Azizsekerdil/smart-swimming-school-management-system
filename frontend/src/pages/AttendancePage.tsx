/** Yoklama ekranı: ders seçimi, yoklama listesi, QR üretimi ve yoklama geçmişi. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  History,
  QrCode,
  Save,
  Users,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  Alert,
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  PageHeader,
  Pagination,
  Spinner,
  StatusBadge,
  TableWrapper,
  Tabs,
  type BadgeTone,
} from '@/components/ui'
import { get, post } from '@/lib/api'
import { formatDateTime, formatDuration, formatNumber, formatTimeRange, toISODate } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  AttendanceRecord,
  AttendanceSheet,
  AttendanceStatus,
  Lesson,
  Page,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------
const STATUS_OPTIONS: AttendanceStatus[] = [
  'present',
  'absent',
  'late',
  'excused',
  'cancelled',
  'makeup',
]

/** Seçili durum butonunun rengi */
const STATUS_ACTIVE_STYLES: Record<AttendanceStatus, string> = {
  present: 'border-emerald-600 bg-emerald-600 text-white',
  absent: 'border-rose-600 bg-rose-600 text-white',
  late: 'border-amber-500 bg-amber-500 text-white',
  excused: 'border-sky-600 bg-sky-600 text-white',
  cancelled: 'border-slate-500 bg-slate-500 text-white',
  makeup: 'border-violet-600 bg-violet-600 text-white',
}

const STATUS_BADGE_TONES: Record<AttendanceStatus, BadgeTone> = {
  present: 'success',
  absent: 'danger',
  late: 'warning',
  excused: 'info',
  cancelled: 'neutral',
  makeup: 'info',
}

const QR_MINUTE_OPTIONS = [30, 60, 90, 120]

/** POST /attendance/qr/generate/{lesson_id} yanıtı */
interface QrTokenResponse {
  token: string
  lesson_id: number
  lesson_title: string
  expires_at: string
  qr_payload: string
}

interface AttendanceEntryPayload {
  student_id: number
  status: AttendanceStatus
  late_minutes: number | null
  excuse_reason: string | null
  notes: string | null
}

/** Tablodaki tek satırın düzenlenebilir hâli */
interface DraftEntry {
  status: AttendanceStatus | null
  lateMinutes: string
  excuseReason: string
  notes: string
}

const EMPTY_DRAFT: DraftEntry = { status: null, lateMinutes: '', excuseReason: '', notes: '' }

export default function AttendancePage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const todayISO = useMemo(() => toISODate(new Date()), [])
  const canWrite = can('attendance:write')

  const [activeTab, setActiveTab] = useState<'sheet' | 'history'>('sheet')
  const [selectedDate, setSelectedDate] = useState(todayISO)
  const [selectedLessonId, setSelectedLessonId] = useState<number | null>(null)
  const [drafts, setDrafts] = useState<Record<number, DraftEntry>>({})
  const [consumeCredits, setConsumeCredits] = useState(true)
  const [qrMinutes, setQrMinutes] = useState(90)
  const [qrToken, setQrToken] = useState<QrTokenResponse | null>(null)

  // Geçmiş sekmesi filtreleri
  const [historyFrom, setHistoryFrom] = useState('')
  const [historyTo, setHistoryTo] = useState('')
  const [historyStatus, setHistoryStatus] = useState('')
  const [historyPage, setHistoryPage] = useState(1)
  const [historyPageSize, setHistoryPageSize] = useState(25)

  // -------------------------------------------------------------------------
  // Sorgular
  // -------------------------------------------------------------------------
  const lessonsQuery = useQuery({
    queryKey: ['attendance-lessons', selectedDate, todayISO],
    queryFn: async (): Promise<Lesson[]> => {
      if (selectedDate === todayISO) return get<Lesson[]>('/lessons/today/list')
      const page = await get<Page<Lesson>>('/lessons', {
        date_from: selectedDate,
        date_to: selectedDate,
        page: 1,
        page_size: 100,
      })
      return page.items
    },
  })

  // Seçili günün yoklama kayıtları -> hangi derste yoklama alındığını gösterir
  const recordedQuery = useQuery({
    queryKey: ['attendance-recorded', selectedDate],
    queryFn: () =>
      get<Page<AttendanceRecord>>('/attendance', {
        date_from: selectedDate,
        date_to: selectedDate,
        page: 1,
        page_size: 200,
      }),
  })

  const recordedLessonIds = useMemo(
    () => new Set((recordedQuery.data?.items ?? []).map((item) => item.lesson_id)),
    [recordedQuery.data],
  )

  const sheetQuery = useQuery({
    queryKey: ['attendance-sheet', selectedLessonId],
    queryFn: () => get<AttendanceSheet>(`/attendance/sheet/${selectedLessonId}`),
    enabled: selectedLessonId !== null,
  })

  const historyQuery = useQuery({
    queryKey: ['attendance-history', historyFrom, historyTo, historyStatus, historyPage, historyPageSize],
    queryFn: () =>
      get<Page<AttendanceRecord>>('/attendance', {
        page: historyPage,
        page_size: historyPageSize,
        date_from: historyFrom || undefined,
        date_to: historyTo || undefined,
        status: historyStatus || undefined,
      }),
    enabled: activeTab === 'history',
  })

  const lessons = lessonsQuery.data ?? []
  const sheet = sheetQuery.data

  // Ders listesi değişince geçerli bir ders seçili kalsın
  useEffect(() => {
    const items = lessonsQuery.data
    if (!items || items.length === 0) {
      setSelectedLessonId(null)
      return
    }
    setSelectedLessonId((current) =>
      current !== null && items.some((lesson) => lesson.id === current) ? current : items[0].id,
    )
  }, [lessonsQuery.data])

  // Yoklama listesi geldiğinde taslağı sunucudaki değerlerle doldur
  useEffect(() => {
    if (!sheet) {
      setDrafts({})
      return
    }
    const next: Record<number, DraftEntry> = {}
    for (const row of sheet.rows) {
      next[row.student_id] = {
        status: row.status ?? null,
        lateMinutes: row.late_minutes !== null && row.late_minutes !== undefined ? String(row.late_minutes) : '',
        excuseReason: '',
        notes: row.notes ?? '',
      }
    }
    setDrafts(next)
  }, [sheet])

  // Ders değişince üretilmiş QR bilgisini temizle
  useEffect(() => {
    setQrToken(null)
  }, [selectedLessonId])

  // -------------------------------------------------------------------------
  // Mutasyonlar
  // -------------------------------------------------------------------------
  const saveMutation = useMutation({
    mutationFn: (payload: {
      lesson_id: number
      method: string
      entries: AttendanceEntryPayload[]
      consume_credits: boolean
    }) => post<AttendanceRecord[]>('/attendance', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance-sheet'] })
      queryClient.invalidateQueries({ queryKey: ['attendance-recorded'] })
      queryClient.invalidateQueries({ queryKey: ['attendance-history'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toastSuccess(t('common.success'), t('attendance.recorded'))
    },
    onError: (error) => toastError(error),
  })

  const qrMutation = useMutation({
    mutationFn: (lessonId: number) =>
      post<QrTokenResponse>(`/attendance/qr/generate/${lessonId}`, undefined, {
        valid_minutes: qrMinutes,
      }),
    onSuccess: (data) => {
      setQrToken(data)
      toastSuccess(t('common.success'), t('attendance.qrCode'))
    },
    onError: (error) => toastError(error),
  })

  // -------------------------------------------------------------------------
  // Yardımcılar
  // -------------------------------------------------------------------------
  function updateDraft(studentId: number, patch: Partial<DraftEntry>) {
    setDrafts((current) => ({
      ...current,
      [studentId]: { ...(current[studentId] ?? EMPTY_DRAFT), ...patch },
    }))
  }

  function markAllPresent() {
    if (!sheet) return
    setDrafts((current) => {
      const next: Record<number, DraftEntry> = { ...current }
      for (const row of sheet.rows) {
        next[row.student_id] = {
          ...(current[row.student_id] ?? EMPTY_DRAFT),
          status: 'present',
          lateMinutes: '',
        }
      }
      return next
    })
  }

  const entries: AttendanceEntryPayload[] = useMemo(() => {
    if (!sheet) return []
    return sheet.rows
      .map((row) => {
        const draft = drafts[row.student_id]
        if (!draft?.status) return null
        const entry: AttendanceEntryPayload = {
          student_id: row.student_id,
          status: draft.status,
          late_minutes:
            draft.status === 'late' && draft.lateMinutes.trim() !== ''
              ? Number(draft.lateMinutes)
              : null,
          excuse_reason:
            draft.status === 'excused' && draft.excuseReason.trim() !== ''
              ? draft.excuseReason.trim()
              : null,
          notes: draft.notes.trim() !== '' ? draft.notes.trim() : null,
        }
        return entry
      })
      .filter((entry): entry is AttendanceEntryPayload => entry !== null)
  }, [sheet, drafts])

  const statusCounts = useMemo(() => {
    const counts = new Map<AttendanceStatus, number>()
    for (const entry of entries) {
      counts.set(entry.status, (counts.get(entry.status) ?? 0) + 1)
    }
    return counts
  }, [entries])

  function handleSave() {
    if (!sheet || entries.length === 0) return
    saveMutation.mutate({
      lesson_id: sheet.lesson_id,
      method: 'manual',
      entries,
      consume_credits: consumeCredits,
    })
  }

  async function copyToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      toastSuccess(t('common.copied'))
    } catch (error) {
      toastError(error)
    }
  }

  function clearHistoryFilters() {
    setHistoryFrom('')
    setHistoryTo('')
    setHistoryStatus('')
    setHistoryPage(1)
  }

  // -------------------------------------------------------------------------
  // Görünüm
  // -------------------------------------------------------------------------
  return (
    <>
      <PageHeader
        title={t('attendance.title')}
        subtitle={t('attendance.sheet')}
        icon={<ClipboardCheck className="h-5 w-5" />}
        actions={
          <div className="flex items-center gap-2">
            <input
              type="date"
              className="input w-auto py-1.5 text-xs"
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value)}
              aria-label={t('common.date')}
            />
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => setSelectedDate(todayISO)}
              disabled={selectedDate === todayISO}
            >
              <CalendarDays className="h-3.5 w-3.5" />
              {t('common.today')}
            </button>
          </div>
        }
      />

      <Tabs
        tabs={[
          { id: 'sheet', label: t('attendance.take'), icon: <ClipboardCheck className="h-4 w-4" /> },
          {
            id: 'history',
            label: `${t('attendance.title')} · ${t('student.timeline')}`,
            icon: <History className="h-4 w-4" />,
          },
        ]}
        active={activeTab}
        onChange={(id) => setActiveTab(id === 'history' ? 'history' : 'sheet')}
      />

      {activeTab === 'sheet' && (
        <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
          {/* Sol panel: seçilen günün dersleri */}
          <Card title={t('lesson.title')} bodyClassName="p-0">
            {lessonsQuery.isLoading ? (
              <LoadingState />
            ) : lessonsQuery.error ? (
              <ErrorState error={lessonsQuery.error} onRetry={() => void lessonsQuery.refetch()} />
            ) : lessons.length === 0 ? (
              <EmptyState
                title={t('dashboard.noLessonsToday')}
                description={t('calendar.noEvents')}
                icon={<CalendarDays className="h-6 w-6" />}
              />
            ) : (
              <ul className="max-h-[70vh] divide-y divide-slate-100 overflow-y-auto dark:divide-slate-700/60">
                {lessons.map((lesson) => {
                  const isRecorded = recordedLessonIds.has(lesson.id)
                  const isSelected = lesson.id === selectedLessonId
                  return (
                    <li key={lesson.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedLessonId(lesson.id)}
                        className={clsx(
                          'w-full px-4 py-3 text-left transition-colors',
                          isSelected
                            ? 'bg-brand-50 dark:bg-brand-900/25'
                            : 'hover:bg-slate-50 dark:hover:bg-slate-700/30',
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            {formatTimeRange(lesson.start_at, lesson.end_at)}
                          </span>
                          <span className={isRecorded ? 'badge-success' : 'badge-neutral'}>
                            {isRecorded ? t('attendance.recorded') : t('attendance.notRecorded')}
                          </span>
                        </div>
                        <p className="mt-1 truncate text-sm text-slate-700 dark:text-slate-300">
                          {lesson.title}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">
                          {[lesson.pool_name, lesson.lane_name, lesson.instructor_name]
                            .filter(Boolean)
                            .join(' · ') || '—'}
                        </p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {t('lesson.enrolled')}: {lesson.enrolled_count}/{lesson.capacity}
                        </p>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>

          {/* Sağ panel: yoklama listesi + QR */}
          <div className="space-y-4">
            {selectedLessonId === null ? (
              <Card>
                <EmptyState
                  title={t('common.noData')}
                  description={t('dashboard.noLessonsToday')}
                  icon={<Users className="h-6 w-6" />}
                />
              </Card>
            ) : sheetQuery.isLoading ? (
              <Card>
                <LoadingState />
              </Card>
            ) : sheetQuery.error ? (
              <Card>
                <ErrorState error={sheetQuery.error} onRetry={() => void sheetQuery.refetch()} />
              </Card>
            ) : sheet ? (
              <>
                <Card
                  title={sheet.lesson_title}
                  actions={
                    canWrite && (
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={markAllPresent}
                          disabled={sheet.rows.length === 0}
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          {t('attendance.markAllPresent')}
                        </button>
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          onClick={handleSave}
                          disabled={entries.length === 0 || saveMutation.isPending}
                        >
                          {saveMutation.isPending ? <Spinner /> : <Save className="h-3.5 w-3.5" />}
                          {t('common.save')}
                        </button>
                      </div>
                    )
                  }
                  bodyClassName="p-0"
                >
                  <div className="space-y-3 border-b border-slate-200 px-5 py-4 dark:border-slate-700">
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                      <span>{formatTimeRange(sheet.start_at, sheet.end_at)}</span>
                      {sheet.pool_name && <span>{sheet.pool_name}</span>}
                      {sheet.lane_name && <span>{sheet.lane_name}</span>}
                      {sheet.instructor_name && <span>{sheet.instructor_name}</span>}
                      <span>
                        {t('lesson.enrolled')}: {formatNumber(sheet.rows.length)}
                      </span>
                    </div>

                    {sheet.is_recorded && (
                      <Alert tone="success" title={t('attendance.recorded')} />
                    )}
                    {statusCounts.size > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {STATUS_OPTIONS.filter((status) => (statusCounts.get(status) ?? 0) > 0).map(
                          (status) => (
                            <Badge key={status} tone={STATUS_BADGE_TONES[status]}>
                              {t(`attendance.statuses.${status}`)}: {formatNumber(statusCounts.get(status) ?? 0)}
                            </Badge>
                          ),
                        )}
                      </div>
                    )}

                    <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
                        checked={consumeCredits}
                        onChange={(event) => setConsumeCredits(event.target.checked)}
                        disabled={!canWrite}
                      />
                      {t('attendance.consumeCredits')}
                    </label>
                  </div>

                  {sheet.rows.length === 0 ? (
                    <EmptyState
                      title={t('common.noData')}
                      description={t('lesson.roster')}
                      icon={<Users className="h-6 w-6" />}
                    />
                  ) : (
                    <TableWrapper>
                      <thead>
                        <tr>
                          <th>{t('student.number')}</th>
                          <th>{t('student.fullName')}</th>
                          <th className="hidden md:table-cell">{t('attendance.remainingCredits')}</th>
                          <th>{t('common.status')}</th>
                          <th>{t('common.notes')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sheet.rows.map((row) => {
                          const draft = drafts[row.student_id] ?? EMPTY_DRAFT
                          const lowCredit =
                            row.membership_remaining !== null &&
                            row.membership_remaining !== undefined &&
                            row.membership_remaining <= 2
                          return (
                            <tr key={row.student_id}>
                              <td className="whitespace-nowrap font-mono text-xs">
                                {row.student_number}
                              </td>
                              <td className="whitespace-nowrap font-medium text-slate-900 dark:text-slate-100">
                                {row.full_name}
                              </td>
                              <td className="hidden md:table-cell">
                                {row.membership_remaining === null ||
                                row.membership_remaining === undefined ? (
                                  <span className="text-xs text-slate-400">—</span>
                                ) : (
                                  <Badge tone={lowCredit ? 'danger' : 'neutral'}>
                                    {formatNumber(row.membership_remaining)}
                                  </Badge>
                                )}
                              </td>
                              <td>
                                <div className="flex flex-wrap gap-1">
                                  {STATUS_OPTIONS.map((status) => (
                                    <button
                                      key={status}
                                      type="button"
                                      disabled={!canWrite}
                                      onClick={() =>
                                        updateDraft(row.student_id, {
                                          status: draft.status === status ? null : status,
                                        })
                                      }
                                      className={clsx(
                                        'rounded-md border px-2 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50',
                                        draft.status === status
                                          ? STATUS_ACTIVE_STYLES[status]
                                          : 'border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700',
                                      )}
                                    >
                                      {t(`attendance.statuses.${status}`)}
                                    </button>
                                  ))}
                                </div>
                                {draft.status === 'late' && (
                                  <input
                                    type="number"
                                    min={0}
                                    max={240}
                                    className="input mt-2 w-32 py-1 text-xs"
                                    placeholder={t('attendance.lateMinutes')}
                                    aria-label={t('attendance.lateMinutes')}
                                    value={draft.lateMinutes}
                                    disabled={!canWrite}
                                    onChange={(event) =>
                                      updateDraft(row.student_id, { lateMinutes: event.target.value })
                                    }
                                  />
                                )}
                                {draft.status === 'excused' && (
                                  <input
                                    type="text"
                                    className="input mt-2 w-full min-w-[10rem] py-1 text-xs"
                                    placeholder={t('attendance.excuseReason')}
                                    aria-label={t('attendance.excuseReason')}
                                    value={draft.excuseReason}
                                    disabled={!canWrite}
                                    onChange={(event) =>
                                      updateDraft(row.student_id, { excuseReason: event.target.value })
                                    }
                                  />
                                )}
                              </td>
                              <td>
                                <input
                                  type="text"
                                  className="input w-full min-w-[10rem] py-1 text-xs"
                                  placeholder={t('common.notes')}
                                  aria-label={t('common.notes')}
                                  value={draft.notes}
                                  disabled={!canWrite}
                                  onChange={(event) =>
                                    updateDraft(row.student_id, { notes: event.target.value })
                                  }
                                />
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </TableWrapper>
                  )}
                </Card>

                {/* QR bölümü */}
                {canWrite && (
                  <Card title={t('attendance.qrCode')}>
                    <div className="flex flex-wrap items-end gap-3">
                      <Field label={t('lesson.duration')} className="w-40">
                        <select
                          className="select"
                          value={qrMinutes}
                          onChange={(event) => setQrMinutes(Number(event.target.value))}
                        >
                          {QR_MINUTE_OPTIONS.map((minutes) => (
                            <option key={minutes} value={minutes}>
                              {formatDuration(minutes)}
                            </option>
                          ))}
                        </select>
                      </Field>
                      <button
                        type="button"
                        className="btn-primary"
                        onClick={() => qrMutation.mutate(sheet.lesson_id)}
                        disabled={qrMutation.isPending}
                      >
                        {qrMutation.isPending ? <Spinner /> : <QrCode className="h-4 w-4" />}
                        {t('attendance.generateQr')}
                      </button>
                    </div>

                    {qrToken ? (
                      <div className="mt-4 space-y-3">
                        <div className="rounded-lg border border-slate-300 bg-slate-50 p-4 dark:border-slate-600 dark:bg-slate-800">
                          <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                            {t('attendance.qrCode')}
                          </p>
                          <p className="break-all font-mono text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                            {qrToken.qr_payload}
                          </p>
                        </div>
                        <div className="grid gap-2 sm:grid-cols-2">
                          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                            <p className="text-xs text-slate-500 dark:text-slate-400">Token</p>
                            <p className="mt-1 break-all font-mono text-sm text-slate-800 dark:text-slate-200">
                              {qrToken.token}
                            </p>
                          </div>
                          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              {t('membership.endDate')}
                            </p>
                            <p className="mt-1 text-sm text-slate-800 dark:text-slate-200">
                              {formatDateTime(qrToken.expires_at)}
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => void copyToClipboard(qrToken.qr_payload)}
                        >
                          <Copy className="h-3.5 w-3.5" />
                          {t('common.copy')}
                        </button>
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                        {t('attendance.methods.qr')} · {t('attendance.studentCard')}
                      </p>
                    )}
                  </Card>
                )}
              </>
            ) : null}
          </div>
        </div>
      )}

      {activeTab === 'history' && (
        <Card
          title={`${t('attendance.title')} · ${t('student.timeline')}`}
          actions={
            <button type="button" className="btn-ghost btn-sm" onClick={clearHistoryFilters}>
              {t('common.clearFilters')}
            </button>
          }
          bodyClassName="p-0"
        >
          <div className="grid gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-700 sm:grid-cols-3">
            <Field label={t('lesson.start')}>
              <input
                type="date"
                className="input"
                value={historyFrom}
                onChange={(event) => {
                  setHistoryFrom(event.target.value)
                  setHistoryPage(1)
                }}
              />
            </Field>
            <Field label={t('lesson.end')}>
              <input
                type="date"
                className="input"
                value={historyTo}
                onChange={(event) => {
                  setHistoryTo(event.target.value)
                  setHistoryPage(1)
                }}
              />
            </Field>
            <Field label={t('common.status')}>
              <select
                className="select"
                value={historyStatus}
                onChange={(event) => {
                  setHistoryStatus(event.target.value)
                  setHistoryPage(1)
                }}
              >
                <option value="">{t('common.all')}</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {t(`attendance.statuses.${status}`)}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {historyQuery.isLoading ? (
            <LoadingState />
          ) : historyQuery.error ? (
            <ErrorState error={historyQuery.error} onRetry={() => void historyQuery.refetch()} />
          ) : (historyQuery.data?.items.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noResults')} description={t('common.clearFilters')} />
          ) : (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('common.date')}</th>
                    <th>{t('student.singular')}</th>
                    <th className="hidden md:table-cell">{t('lesson.singular')}</th>
                    <th>{t('common.status')}</th>
                    <th className="hidden lg:table-cell">{t('attendance.lateMinutes')}</th>
                    <th className="hidden lg:table-cell">{t('attendance.method')}</th>
                    <th className="hidden xl:table-cell">{t('common.notes')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(historyQuery.data?.items ?? []).map((record) => (
                    <tr key={record.id}>
                      <td className="whitespace-nowrap text-xs">
                        {formatDateTime(record.lesson_start)}
                      </td>
                      <td className="whitespace-nowrap">
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {record.student_name ?? '—'}
                        </span>
                        {record.student_number && (
                          <span className="ml-2 font-mono text-xs text-slate-400">
                            {record.student_number}
                          </span>
                        )}
                      </td>
                      <td className="hidden md:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {record.lesson_title ?? '—'}
                      </td>
                      <td>
                        <StatusBadge
                          status={record.status}
                          label={t(`attendance.statuses.${record.status}`)}
                        />
                      </td>
                      <td className="hidden lg:table-cell text-xs">
                        {record.late_minutes ? formatNumber(record.late_minutes) : '—'}
                      </td>
                      <td className="hidden lg:table-cell text-xs">
                        {t(`attendance.methods.${record.method}`, record.method)}
                      </td>
                      <td className="hidden xl:table-cell max-w-xs truncate text-xs text-slate-500 dark:text-slate-400">
                        {record.excuse_reason ?? record.notes ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={historyPage}
                pageSize={historyPageSize}
                total={historyQuery.data?.total ?? 0}
                onPageChange={setHistoryPage}
                onPageSizeChange={(size) => {
                  setHistoryPageSize(size)
                  setHistoryPage(1)
                }}
              />
            </>
          )}
        </Card>
      )}
    </>
  )
}
