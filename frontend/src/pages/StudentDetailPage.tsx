/** Öğrenci detay ekranı / Student detail screen. */
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  ArrowLeft,
  CalendarCheck,
  ClipboardList,
  CreditCard,
  History,
  Trophy,
  User,
  Users,
  Wallet,
} from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  Alert,
  Badge,
  Card,
  DemoBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Pagination,
  ProgressBar,
  StatCard,
  StatusBadge,
  TableWrapper,
  Tabs,
  type BadgeTone,
} from '@/components/ui'
import { get } from '@/lib/api'
import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
  formatSwimTime,
  formatTimeDelta,
  initials,
} from '@/lib/format'
import { useAuth } from '@/lib/store'
import type {
  AttendanceRecord,
  Membership,
  Page,
  Payment,
  PerformanceEventAnalysis,
  PersonalBest,
  StudentDetail,
  StudentPerformanceSummary,
  SwimLevel,
} from '@/lib/types'

const LIST_PAGE_SIZE = 20

const LEVEL_TONES: Record<SwimLevel, BadgeTone> = {
  beginner: 'neutral',
  elementary: 'neutral',
  intermediate: 'info',
  advanced: 'info',
  competitive: 'success',
  elite: 'warning',
}

/** /attendance/student/{id}/summary yanıtı */
interface AttendanceSummary {
  student_id: number
  period_days: number
  total: number
  by_status: Record<string, number>
  attendance_rate: number | null
  absent_count: number
  late_count: number
  excused_count: number
}

/** /students/{id}/timeline yanıtı */
interface TimelineEvent {
  type: string
  at: string
  title: string
  status: string
  detail: string
}

interface TimelineResponse {
  student_id: number
  events: TimelineEvent[]
  total: number
}

// --- active_membership sözlüğünden güvenli okuma ---
function asText(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && !Number.isNaN(value) ? value : null
}

// ---------------------------------------------------------------------------
export default function StudentDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const can = useAuth((state) => state.can)

  const studentId = Number(id)
  const validId = Number.isFinite(studentId) && studentId > 0

  const [tab, setTab] = useState('overview')
  const [listPage, setListPage] = useState(1)

  const canAttendance = can('attendance:read')
  const canMembership = can('membership:read')
  const canFinance = can('finance:read')
  const canPerformance = can('performance:read')
  const canSensitive = can('student:read_sensitive')

  // --- Ana kayıt ---
  const studentQuery = useQuery({
    queryKey: ['student', studentId],
    queryFn: () => get<StudentDetail>(`/students/${studentId}`),
    enabled: validId,
  })

  // --- Sekme verileri ---
  const attendanceQuery = useQuery({
    queryKey: ['student', studentId, 'attendance', listPage],
    queryFn: () =>
      get<Page<AttendanceRecord>>('/attendance', {
        student_id: studentId,
        page: listPage,
        page_size: LIST_PAGE_SIZE,
      }),
    enabled: validId && canAttendance && tab === 'attendance',
  })

  const attendanceSummaryQuery = useQuery({
    queryKey: ['student', studentId, 'attendance-summary'],
    queryFn: () =>
      get<AttendanceSummary>(`/attendance/student/${studentId}/summary`, { days: 180 }),
    enabled: validId && canAttendance && tab === 'attendance',
  })

  const membershipsQuery = useQuery({
    queryKey: ['student', studentId, 'memberships', listPage],
    queryFn: () =>
      get<Page<Membership>>('/memberships', {
        student_id: studentId,
        page: listPage,
        page_size: LIST_PAGE_SIZE,
      }),
    enabled: validId && canMembership && tab === 'membership',
  })

  const paymentsQuery = useQuery({
    queryKey: ['student', studentId, 'payments', listPage],
    queryFn: () =>
      get<Page<Payment>>('/finance/payments', {
        student_id: studentId,
        page: listPage,
        page_size: LIST_PAGE_SIZE,
      }),
    enabled: validId && canFinance && tab === 'payments',
  })

  const performanceQuery = useQuery({
    queryKey: ['student', studentId, 'performance-summary'],
    queryFn: () => get<StudentPerformanceSummary>(`/performance/student/${studentId}/summary`),
    enabled: validId && canPerformance && tab === 'performance',
  })

  const personalBestsQuery = useQuery({
    queryKey: ['student', studentId, 'personal-bests'],
    queryFn: () => get<PersonalBest[]>(`/performance/student/${studentId}/personal-bests`),
    enabled: validId && canPerformance && tab === 'performance',
  })

  const timelineQuery = useQuery({
    queryKey: ['student', studentId, 'timeline'],
    queryFn: () => get<TimelineResponse>(`/students/${studentId}/timeline`, { limit: 60 }),
    enabled: validId && tab === 'timeline',
  })

  const tabs = useMemo(() => {
    const list: Array<{ id: string; label: string; icon: ReactNode }> = [
      { id: 'overview', label: t('student.tabs.overview'), icon: <User className="h-4 w-4" /> },
    ]
    if (canAttendance) {
      list.push({
        id: 'attendance',
        label: t('student.tabs.attendance'),
        icon: <ClipboardList className="h-4 w-4" />,
      })
    }
    if (canMembership) {
      list.push({
        id: 'membership',
        label: t('student.tabs.membership'),
        icon: <CreditCard className="h-4 w-4" />,
      })
    }
    if (canFinance) {
      list.push({
        id: 'payments',
        label: t('student.tabs.payments'),
        icon: <Wallet className="h-4 w-4" />,
      })
    }
    if (canPerformance) {
      list.push({
        id: 'performance',
        label: t('student.tabs.performance'),
        icon: <Activity className="h-4 w-4" />,
      })
    }
    list.push({
      id: 'timeline',
      label: t('student.tabs.timeline'),
      icon: <History className="h-4 w-4" />,
    })
    return list
  }, [canAttendance, canFinance, canMembership, canPerformance, t])

  if (!validId) {
    return <ErrorState error={new Error(t('errors.notFound'))} />
  }
  if (studentQuery.isLoading) return <LoadingState />
  if (studentQuery.error) {
    return <ErrorState error={studentQuery.error} onRetry={() => void studentQuery.refetch()} />
  }
  const student = studentQuery.data
  if (!student) return null

  // --- Aktif üyelik özeti ---
  const membership = student.active_membership
  const packageName = asText(membership?.package_name)
  const remainingCredits = asNumber(membership?.remaining_credits)
  const totalCredits = asNumber(membership?.total_credits)
  const membershipEnd = asText(membership?.end_date)
  const daysRemaining = asNumber(membership?.days_remaining)
  const membershipStatus = asText(membership?.status)
  const usagePercent =
    totalCredits && totalCredits > 0
      ? ((totalCredits - (remainingCredits ?? 0)) / totalCredits) * 100
      : null

  const guardianNames = student.guardians.map((guardian) => guardian.full_name).join(', ')

  function changeTab(next: string) {
    setTab(next)
    setListPage(1)
  }

  return (
    <>
      <PageHeader
        title={student.full_name}
        subtitle={`${t('student.number')}: ${student.student_number}`}
        icon={<User className="h-5 w-5" />}
        actions={
          <Link to="/students" className="btn-secondary">
            <ArrowLeft className="h-4 w-4" />
            {t('common.back')}
          </Link>
        }
      />

      {/* Profil kartı */}
      <Card className="mb-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <div className="grid h-16 w-16 shrink-0 place-items-center rounded-full bg-brand-100 text-xl font-semibold text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
            {initials(student.full_name)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {student.full_name}
              </h2>
              <StatusBadge
                status={student.status}
                label={t(`studentStatus.${student.status}`)}
              />
              <Badge tone={LEVEL_TONES[student.swim_level]}>
                {t(`swimLevel.${student.swim_level}`)}
              </Badge>
              {student.is_demo && <DemoBadge />}
            </div>
            <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <InfoItem label={t('student.number')} value={student.student_number} />
              <InfoItem
                label={t('student.age')}
                value={
                  student.age !== null && student.age !== undefined
                    ? formatNumber(student.age)
                    : '—'
                }
              />
              <InfoItem label={t('common.phone')} value={student.phone ?? '—'} />
              <InfoItem label={t('common.email')} value={student.email ?? '—'} />
              <InfoItem
                label={t('student.registrationDate')}
                value={formatDate(student.registration_date)}
              />
              <InfoItem label={t('student.guardians')} value={guardianNames || '—'} />
            </dl>
          </div>
        </div>
      </Card>

      {/* Özet sayaçlar */}
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={t('student.attendanceRate')}
          value={
            student.attendance_rate !== null && student.attendance_rate !== undefined
              ? formatPercent(student.attendance_rate)
              : '—'
          }
          icon={<CalendarCheck className="h-5 w-5" />}
          tone={
            student.attendance_rate !== null &&
            student.attendance_rate !== undefined &&
            student.attendance_rate < 70
              ? 'warning'
              : 'success'
          }
        />
        <StatCard
          label={t('student.totalLessons')}
          value={formatNumber(student.total_lessons)}
          icon={<ClipboardList className="h-5 w-5" />}
          tone="neutral"
        />
        <StatCard
          label={t('student.outstandingBalance')}
          value={formatCurrency(student.outstanding_balance)}
          icon={<Wallet className="h-5 w-5" />}
          tone={student.outstanding_balance > 0 ? 'danger' : 'success'}
        />
        <StatCard
          label={t('student.personalBests')}
          value={formatNumber(student.personal_best_count)}
          icon={<Trophy className="h-5 w-5" />}
          tone="brand"
        />
      </div>

      {/* Aktif üyelik */}
      <Card title={t('student.activeMembership')} className="mb-5">
        {!membership ? (
          <EmptyState
            title={t('student.noMembership')}
            icon={<CreditCard className="h-6 w-6" />}
          />
        ) : (
          <div className="grid gap-4 lg:grid-cols-4">
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('membership.package')}
              </p>
              <p className="mt-0.5 flex flex-wrap items-center gap-2 font-medium text-slate-900 dark:text-slate-100">
                {packageName ?? '—'}
                {membershipStatus && (
                  <StatusBadge
                    status={membershipStatus}
                    label={t(`membership.statuses.${membershipStatus}`, membershipStatus)}
                  />
                )}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('membership.remainingCredits')}
              </p>
              <p className="mt-0.5 font-medium text-slate-900 dark:text-slate-100">
                {remainingCredits !== null
                  ? `${formatNumber(remainingCredits)}${totalCredits !== null ? ` / ${formatNumber(totalCredits)}` : ''}`
                  : t('membership.unlimited')}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('membership.endDate')}
              </p>
              <p className="mt-0.5 font-medium text-slate-900 dark:text-slate-100">
                {membershipEnd ? formatDate(membershipEnd) : '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('membership.daysRemaining')}
              </p>
              <p className="mt-0.5 font-medium text-slate-900 dark:text-slate-100">
                {daysRemaining !== null ? formatNumber(daysRemaining) : '—'}
              </p>
            </div>
            {usagePercent !== null && (
              <div className="lg:col-span-4">
                <p className="mb-1.5 text-xs text-slate-500 dark:text-slate-400">
                  {t('membership.usageRate')}
                </p>
                <ProgressBar
                  value={usagePercent}
                  tone={usagePercent >= 85 ? 'warning' : 'brand'}
                  showLabel
                />
              </div>
            )}
          </div>
        )}
      </Card>

      <Tabs tabs={tabs} active={tab} onChange={changeTab} />

      {/* --- Genel --- */}
      {tab === 'overview' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title={t('student.goals')}>
            {student.goals ? (
              <p className="whitespace-pre-line text-sm text-slate-700 dark:text-slate-200">
                {student.goals}
              </p>
            ) : (
              <p className="text-sm text-slate-400">{t('common.none')}</p>
            )}
          </Card>

          <Card title={t('common.notes')}>
            {student.notes ? (
              <p className="whitespace-pre-line text-sm text-slate-700 dark:text-slate-200">
                {student.notes}
              </p>
            ) : (
              <p className="text-sm text-slate-400">{t('common.none')}</p>
            )}
          </Card>

          <Card
            title={
              <h2 className="card-title flex items-center gap-2">
                <Users className="h-4 w-4" />
                {t('student.guardians')}
              </h2>
            }
            bodyClassName={student.guardians.length > 0 ? 'p-0' : undefined}
          >
            {student.guardians.length === 0 ? (
              <p className="text-sm text-slate-400">{t('common.none')}</p>
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('common.name')}</th>
                    <th>{t('guardian.relationship')}</th>
                    <th>{t('common.phone')}</th>
                    <th className="hidden sm:table-cell">{t('common.email')}</th>
                  </tr>
                </thead>
                <tbody>
                  {student.guardians.map((guardian) => (
                    <tr key={guardian.id}>
                      <td className="font-medium text-slate-800 dark:text-slate-100">
                        {guardian.full_name}
                      </td>
                      <td className="text-xs text-slate-500 dark:text-slate-400">
                        {t(
                          `guardian.relationships.${guardian.relationship_type}`,
                          guardian.relationship_type,
                        )}
                      </td>
                      <td className="whitespace-nowrap">{guardian.phone}</td>
                      <td className="hidden sm:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {guardian.email ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </Card>

          <Card title={t('student.healthNotes')}>
            {!canSensitive ? (
              <Alert tone="warning" title={t('student.sensitiveHidden')} />
            ) : (
              <div className="space-y-4">
                <div>
                  <p className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                    {t('student.healthNotes')}
                  </p>
                  <p className="whitespace-pre-line text-sm text-slate-700 dark:text-slate-200">
                    {student.health_notes ?? t('common.none')}
                  </p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                    {t('student.specialNeeds')}
                  </p>
                  <p className="whitespace-pre-line text-sm text-slate-700 dark:text-slate-200">
                    {student.special_needs ?? t('common.none')}
                  </p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                    {t('student.emergencyContact')}
                  </p>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    {student.emergency_contact_name ?? t('common.none')}
                    {student.emergency_contact_phone
                      ? ` · ${student.emergency_contact_phone}`
                      : ''}
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* --- Yoklama --- */}
      {tab === 'attendance' && canAttendance && (
        <div className="space-y-4">
          {attendanceSummaryQuery.data && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label={t('attendance.rate')}
                value={
                  attendanceSummaryQuery.data.attendance_rate !== null
                    ? formatPercent(attendanceSummaryQuery.data.attendance_rate)
                    : '—'
                }
                hint={`${t('common.total')}: ${formatNumber(attendanceSummaryQuery.data.total)}`}
                icon={<CalendarCheck className="h-5 w-5" />}
                tone="success"
              />
              <StatCard
                label={t('attendance.statuses.absent')}
                value={formatNumber(attendanceSummaryQuery.data.absent_count)}
                icon={<ClipboardList className="h-5 w-5" />}
                tone={attendanceSummaryQuery.data.absent_count > 0 ? 'danger' : 'neutral'}
              />
              <StatCard
                label={t('attendance.statuses.late')}
                value={formatNumber(attendanceSummaryQuery.data.late_count)}
                icon={<ClipboardList className="h-5 w-5" />}
                tone={attendanceSummaryQuery.data.late_count > 0 ? 'warning' : 'neutral'}
              />
              <StatCard
                label={t('attendance.statuses.excused')}
                value={formatNumber(attendanceSummaryQuery.data.excused_count)}
                icon={<ClipboardList className="h-5 w-5" />}
                tone="neutral"
              />
            </div>
          )}

          <Card title={t('attendance.title')} bodyClassName="p-0">
            {attendanceQuery.isLoading ? (
              <LoadingState />
            ) : attendanceQuery.error ? (
              <ErrorState
                error={attendanceQuery.error}
                onRetry={() => void attendanceQuery.refetch()}
              />
            ) : (attendanceQuery.data?.items.length ?? 0) === 0 ? (
              <EmptyState title={t('common.noData')} icon={<ClipboardList className="h-6 w-6" />} />
            ) : (
              <>
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('common.date')}</th>
                      <th>{t('lesson.singular')}</th>
                      <th>{t('common.status')}</th>
                      <th className="hidden sm:table-cell">{t('attendance.lateMinutes')}</th>
                      <th className="hidden lg:table-cell">{t('attendance.method')}</th>
                      <th className="hidden xl:table-cell">{t('common.notes')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(attendanceQuery.data?.items ?? []).map((record) => (
                      <tr key={record.id}>
                        <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                          {formatDate(record.lesson_start)}
                        </td>
                        <td className="font-medium text-slate-800 dark:text-slate-100">
                          {record.lesson_title ?? '—'}
                        </td>
                        <td>
                          <StatusBadge
                            status={record.status}
                            label={t(`attendance.statuses.${record.status}`)}
                          />
                        </td>
                        <td className="hidden sm:table-cell">
                          {record.late_minutes ? formatNumber(record.late_minutes) : '—'}
                        </td>
                        <td className="hidden lg:table-cell text-xs text-slate-500 dark:text-slate-400">
                          {t(`attendance.methods.${record.method}`, record.method)}
                        </td>
                        <td className="hidden xl:table-cell text-xs text-slate-500 dark:text-slate-400">
                          {record.notes ?? record.excuse_reason ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableWrapper>
                <Pagination
                  page={listPage}
                  pageSize={LIST_PAGE_SIZE}
                  total={attendanceQuery.data?.total ?? 0}
                  onPageChange={setListPage}
                />
              </>
            )}
          </Card>
        </div>
      )}

      {/* --- Üyelik --- */}
      {tab === 'membership' && canMembership && (
        <Card title={t('membership.title')} bodyClassName="p-0">
          {membershipsQuery.isLoading ? (
            <LoadingState />
          ) : membershipsQuery.error ? (
            <ErrorState
              error={membershipsQuery.error}
              onRetry={() => void membershipsQuery.refetch()}
            />
          ) : (membershipsQuery.data?.items.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<CreditCard className="h-6 w-6" />} />
          ) : (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('membership.package')}</th>
                    <th>{t('membership.startDate')}</th>
                    <th>{t('membership.endDate')}</th>
                    <th>{t('membership.remainingCredits')}</th>
                    <th className="hidden lg:table-cell">{t('membership.usageRate')}</th>
                    <th className="hidden md:table-cell">{t('membership.price')}</th>
                    <th>{t('common.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(membershipsQuery.data?.items ?? []).map((row) => (
                    <tr key={row.id}>
                      <td className="font-medium text-slate-800 dark:text-slate-100">
                        {row.package_name ?? '—'}
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {formatDate(row.start_date)}
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {row.end_date ? formatDate(row.end_date) : '—'}
                      </td>
                      <td className="whitespace-nowrap">
                        {row.remaining_credits !== null && row.remaining_credits !== undefined
                          ? `${formatNumber(row.remaining_credits)} / ${formatNumber(row.total_credits ?? 0)}`
                          : t('membership.unlimited')}
                      </td>
                      <td className="hidden lg:table-cell w-40">
                        <ProgressBar
                          value={row.usage_rate}
                          tone={row.usage_rate >= 85 ? 'warning' : 'brand'}
                          showLabel
                        />
                      </td>
                      <td className="hidden whitespace-nowrap md:table-cell">
                        {formatCurrency(row.price_paid)}
                      </td>
                      <td>
                        <StatusBadge
                          status={row.status}
                          label={t(`membership.statuses.${row.status}`)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={listPage}
                pageSize={LIST_PAGE_SIZE}
                total={membershipsQuery.data?.total ?? 0}
                onPageChange={setListPage}
              />
            </>
          )}
        </Card>
      )}

      {/* --- Ödemeler --- */}
      {tab === 'payments' && canFinance && (
        <Card title={t('finance.payments')} bodyClassName="p-0">
          {paymentsQuery.isLoading ? (
            <LoadingState />
          ) : paymentsQuery.error ? (
            <ErrorState error={paymentsQuery.error} onRetry={() => void paymentsQuery.refetch()} />
          ) : (paymentsQuery.data?.items.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<Wallet className="h-6 w-6" />} />
          ) : (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('finance.receiptNumber')}</th>
                    <th>{t('finance.paymentDate')}</th>
                    <th>{t('finance.amount')}</th>
                    <th className="hidden sm:table-cell">{t('finance.method')}</th>
                    <th>{t('common.status')}</th>
                    <th className="hidden lg:table-cell">{t('common.description')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(paymentsQuery.data?.items ?? []).map((payment) => (
                    <tr key={payment.id}>
                      <td className="whitespace-nowrap font-mono text-xs text-slate-500 dark:text-slate-400">
                        {payment.receipt_number}
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {formatDate(payment.payment_date)}
                      </td>
                      <td className="whitespace-nowrap font-medium text-slate-800 dark:text-slate-100">
                        {formatCurrency(payment.net_amount)}
                        {payment.refunded_amount > 0 && (
                          <span className="ml-1 text-xs text-rose-500">
                            {`(${t('finance.refund')}: ${formatCurrency(payment.refunded_amount)})`}
                          </span>
                        )}
                      </td>
                      <td className="hidden sm:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {t(`finance.methods.${payment.method}`)}
                      </td>
                      <td>
                        <StatusBadge
                          status={payment.status}
                          label={t(`finance.statuses.${payment.status}`)}
                        />
                      </td>
                      <td className="hidden lg:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {payment.description ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={listPage}
                pageSize={LIST_PAGE_SIZE}
                total={paymentsQuery.data?.total ?? 0}
                onPageChange={setListPage}
              />
            </>
          )}
        </Card>
      )}

      {/* --- Performans --- */}
      {tab === 'performance' && canPerformance && (
        <div className="space-y-4">
          {performanceQuery.isLoading ? (
            <LoadingState />
          ) : performanceQuery.error ? (
            <ErrorState
              error={performanceQuery.error}
              onRetry={() => void performanceQuery.refetch()}
            />
          ) : !performanceQuery.data || performanceQuery.data.events.length === 0 ? (
            <Card>
              <EmptyState
                title={t('performance.noRecords')}
                icon={<Activity className="h-6 w-6" />}
              />
            </Card>
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label={t('common.total')}
                  value={formatNumber(performanceQuery.data.total_records)}
                  hint={`${t('competition.title')}: ${formatNumber(performanceQuery.data.competition_count)}`}
                  icon={<Activity className="h-5 w-5" />}
                  tone="brand"
                />
                <StatCard
                  label={t('performance.personalBests')}
                  value={formatNumber(performanceQuery.data.personal_best_count)}
                  icon={<Trophy className="h-5 w-5" />}
                  tone="success"
                />
                <StatCard
                  label={t('performance.strongestStroke')}
                  value={
                    performanceQuery.data.strongest_stroke
                      ? t(
                          `performance.strokes.${performanceQuery.data.strongest_stroke}`,
                          performanceQuery.data.strongest_stroke,
                        )
                      : '—'
                  }
                  icon={<Activity className="h-5 w-5" />}
                  tone="neutral"
                />
                <StatCard
                  label={t('performance.improvementPercent')}
                  value={
                    performanceQuery.data.overall_improvement_percent !== null &&
                    performanceQuery.data.overall_improvement_percent !== undefined
                      ? formatPercent(performanceQuery.data.overall_improvement_percent)
                      : '—'
                  }
                  icon={<Activity className="h-5 w-5" />}
                  tone={
                    (performanceQuery.data.overall_improvement_percent ?? 0) >= 0
                      ? 'success'
                      : 'danger'
                  }
                />
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                {performanceQuery.data.events.map((event) => (
                  <PerformanceEventCard
                    key={`${event.stroke}-${event.distance_m}-${event.course_type}`}
                    event={event}
                  />
                ))}
              </div>
            </>
          )}

          <Card title={t('performance.personalBests')} bodyClassName="p-0">
            {personalBestsQuery.isLoading ? (
              <LoadingState />
            ) : personalBestsQuery.error ? (
              <ErrorState
                error={personalBestsQuery.error}
                onRetry={() => void personalBestsQuery.refetch()}
              />
            ) : (personalBestsQuery.data?.length ?? 0) === 0 ? (
              <EmptyState title={t('common.noData')} icon={<Trophy className="h-6 w-6" />} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('performance.stroke')}</th>
                    <th>{t('performance.distance')}</th>
                    <th>{t('pool.courseType')}</th>
                    <th>{t('performance.bestTime')}</th>
                    <th>{t('common.date')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(personalBestsQuery.data ?? []).map((best) => (
                    <tr key={best.id}>
                      <td className="font-medium text-slate-800 dark:text-slate-100">
                        {t(`performance.strokes.${best.stroke}`, best.stroke)}
                      </td>
                      <td className="whitespace-nowrap">{`${formatNumber(best.distance_m)} m`}</td>
                      <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {best.course_type === 'long' ? '50 m' : '25 m'}
                      </td>
                      <td className="whitespace-nowrap font-mono font-medium text-brand-600 dark:text-brand-400">
                        {best.formatted_time}
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {formatDate(best.achieved_date)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </Card>
        </div>
      )}

      {/* --- Geçmiş --- */}
      {tab === 'timeline' && (
        <Card title={t('student.timeline')}>
          {timelineQuery.isLoading ? (
            <LoadingState />
          ) : timelineQuery.error ? (
            <ErrorState error={timelineQuery.error} onRetry={() => void timelineQuery.refetch()} />
          ) : (timelineQuery.data?.events.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<History className="h-6 w-6" />} />
          ) : (
            <ol className="relative space-y-4 border-l border-slate-200 pl-5 dark:border-slate-700">
              {(timelineQuery.data?.events ?? []).map((event, index) => (
                <TimelineItem key={`${event.type}-${event.at}-${index}`} event={event} />
              ))}
            </ol>
          )}
        </Card>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Yardımcı bileşenler
// ---------------------------------------------------------------------------
function InfoItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="truncate text-slate-800 dark:text-slate-100">{value}</dd>
    </div>
  )
}

/** Zaman çizelgesindeki tek olay: tür ikonu, başlık, durum ve ek bilgi */
function TimelineItem({ event }: { event: TimelineEvent }) {
  const { t } = useTranslation()

  const icon =
    event.type === 'payment' ? (
      <Wallet className="h-3 w-3 text-emerald-500" />
    ) : event.type === 'membership' ? (
      <CreditCard className="h-3 w-3 text-brand-500" />
    ) : (
      <ClipboardList className="h-3 w-3 text-slate-400" />
    )

  // Durum ve ek bilgi anahtarları olay türüne göre farklı sözlüklerde
  const statusLabel =
    event.type === 'payment'
      ? t(`finance.statuses.${event.status}`, event.status)
      : event.type === 'membership'
        ? t(`membership.statuses.${event.status}`, event.status)
        : t(`attendance.statuses.${event.status}`, event.status)

  const detailLabel =
    event.type === 'payment'
      ? t(`finance.methods.${event.detail}`, event.detail)
      : event.type === 'membership'
        ? event.detail
        : t(`lesson.types.${event.detail}`, event.detail)

  return (
    <li className="relative">
      <span className="absolute -left-[27px] top-1 grid h-5 w-5 place-items-center rounded-full bg-white ring-2 ring-slate-200 dark:bg-surface-dark-alt dark:ring-slate-700">
        {icon}
      </span>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium text-slate-800 dark:text-slate-100">{event.title}</span>
        <StatusBadge status={event.status} label={statusLabel} />
      </div>
      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
        {formatDate(event.at)} · {detailLabel}
      </p>
    </li>
  )
}

/** Tek bir yarışma etkinliği için özet + eğilim grafiği */
function PerformanceEventCard({ event }: { event: PerformanceEventAnalysis }) {
  const { t } = useTranslation()
  const improved = event.improvement_seconds > 0

  return (
    <Card
      title={
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="card-title">
            {`${t(`performance.strokes.${event.stroke}`, event.stroke)} ${formatNumber(event.distance_m)} m`}
          </h2>
          <Badge tone="neutral">{event.course_type === 'long' ? '50 m' : '25 m'}</Badge>
          <Badge tone={event.trend === 'improving' ? 'success' : event.trend === 'declining' ? 'danger' : 'neutral'}>
            {t(`performance.trends.${event.trend}`)}
          </Badge>
        </div>
      }
    >
      <div className="mb-3 grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60">
          <p className="text-xs text-slate-500 dark:text-slate-400">{t('performance.bestTime')}</p>
          <p className="mt-0.5 font-mono text-sm font-semibold text-brand-600 dark:text-brand-400">
            {formatSwimTime(event.best_time)}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60">
          <p className="text-xs text-slate-500 dark:text-slate-400">{t('performance.meanTime')}</p>
          <p className="mt-0.5 font-mono text-sm font-semibold text-slate-800 dark:text-slate-100">
            {formatSwimTime(event.mean_time)}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('performance.improvement')}
          </p>
          <p
            className={
              improved
                ? 'mt-0.5 font-mono text-sm font-semibold text-emerald-600 dark:text-emerald-400'
                : 'mt-0.5 font-mono text-sm font-semibold text-rose-600 dark:text-rose-400'
            }
          >
            {formatTimeDelta(event.improvement_seconds)}
          </p>
          <p className="text-[11px] text-slate-400">{formatPercent(event.improvement_percent)}</p>
        </div>
      </div>

      {event.points.length === 0 ? (
        <EmptyState title={t('common.noData')} icon={<Activity className="h-6 w-6" />} />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={event.points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              minTickGap={24}
              tickFormatter={(value: string) => formatDate(value)}
            />
            <YAxis
              tick={{ fontSize: 10 }}
              width={56}
              domain={['auto', 'auto']}
              tickFormatter={(value: number) => formatSwimTime(value)}
            />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
              formatter={(value: number, name: string) => [formatSwimTime(value), name]}
              labelFormatter={(label: string) => formatDate(label)}
            />
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
              strokeDasharray="4 4"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
        {`${t('common.total')}: ${formatNumber(event.record_count)} · ${t('performance.recordedDate')}: ${formatDate(event.points[event.points.length - 1]?.date)}`}
      </p>
    </Card>
  )
}
