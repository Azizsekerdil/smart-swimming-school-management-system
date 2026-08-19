/** Ana kontrol paneli / Main dashboard. */
import { useQuery } from '@tanstack/react-query'
import {
  Activity, AlertTriangle, Award, CalendarDays, CheckCircle2, CreditCard,
  Grid3x3, TrendingUp, Trophy, UserPlus, Users, Waves,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

import {
  Alert, Card, EmptyState, ErrorState, LoadingState, PageHeader, ProgressBar,
  StatCard, StatusBadge,
} from '@/components/ui'
import { get } from '@/lib/api'
import { formatCompact, formatCurrency, formatNumber, formatPercent, formatTimeRange } from '@/lib/format'
import { useAuth } from '@/lib/store'
import type { DashboardSummary } from '@/lib/types'

const LEVEL_COLORS = ['#38bdf8', '#0ea5e9', '#0284c7', '#6366f1', '#8b5cf6', '#d946ef']

export default function DashboardPage() {
  const { t, i18n } = useTranslation()
  const can = useAuth((state) => state.can)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => get<DashboardSummary>('/statistics/dashboard'),
    refetchInterval: 120_000,
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error} onRetry={refetch} />
  if (!data) return null

  const netIncome = data.monthly_revenue - data.monthly_expense
  const laneUsagePercent = data.total_lanes
    ? (data.lanes_in_use / data.total_lanes) * 100
    : 0

  return (
    <>
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        icon={<Waves className="h-5 w-5" />}
      />

      {/* Uyarılar */}
      {data.alerts.length > 0 && (
        <div className="mb-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {data.alerts.map((alert) => (
            <Link key={alert.key} to={alert.link ?? '#'} className="block">
              <Alert
                tone={alert.severity === 'error' ? 'danger' : alert.severity === 'warning' ? 'warning' : 'info'}
                title={i18n.language === 'tr' ? alert.title_tr : alert.title_en}
              />
            </Link>
          ))}
        </div>
      )}

      {/* Ana sayaçlar */}
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={t('dashboard.activeStudents')}
          value={formatNumber(data.active_students)}
          hint={`${t('dashboard.totalStudents')}: ${formatNumber(data.total_students)}`}
          icon={<Users className="h-5 w-5" />}
          tone="brand"
        />
        <StatCard
          label={t('dashboard.lessonsToday')}
          value={formatNumber(data.lessons_today)}
          hint={`${data.lessons_completed_today} ${t('lesson.statuses.completed').toLowerCase()}`}
          icon={<CalendarDays className="h-5 w-5" />}
          tone="neutral"
        />
        <StatCard
          label={t('dashboard.poolOccupancy')}
          value={formatPercent(data.pool_occupancy_rate)}
          hint={`${data.lanes_in_use}/${data.total_lanes} ${t('nav.lanes').toLowerCase()}`}
          icon={<Grid3x3 className="h-5 w-5" />}
          tone={data.pool_occupancy_rate >= 70 ? 'success' : 'warning'}
        />
        <StatCard
          label={t('dashboard.activeInstructors')}
          value={formatNumber(data.active_instructors)}
          icon={<Award className="h-5 w-5" />}
          tone="neutral"
        />
      </div>

      {/* Finans sayaçları */}
      {can('finance:read') && (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label={t('dashboard.collectedToday')}
            value={formatCurrency(data.collected_today)}
            hint={`${t('dashboard.dueToday')}: ${formatCurrency(data.due_today)}`}
            icon={<CreditCard className="h-5 w-5" />}
            tone="success"
          />
          <StatCard
            label={t('dashboard.monthlyRevenue')}
            value={formatCurrency(data.monthly_revenue)}
            icon={<TrendingUp className="h-5 w-5" />}
            tone="brand"
          />
          <StatCard
            label={t('dashboard.netIncome')}
            value={formatCurrency(netIncome)}
            hint={`${t('dashboard.monthlyExpense')}: ${formatCurrency(data.monthly_expense)}`}
            icon={<Activity className="h-5 w-5" />}
            tone={netIncome >= 0 ? 'success' : 'danger'}
          />
          <StatCard
            label={t('dashboard.overduePayments')}
            value={formatCurrency(data.overdue_amount)}
            hint={`${data.overdue_count} kayıt`}
            icon={<AlertTriangle className="h-5 w-5" />}
            tone={data.overdue_count > 0 ? 'danger' : 'neutral'}
          />
        </div>
      )}

      {/* Operasyon sayaçları */}
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={t('dashboard.attendanceToday')}
          value={data.attendance_today_rate !== null ? formatPercent(data.attendance_today_rate) : '—'}
          hint={`${data.attendance_pending_lessons} ${t('dashboard.pendingAttendance').toLowerCase()}`}
          icon={<CheckCircle2 className="h-5 w-5" />}
          tone={data.attendance_pending_lessons > 0 ? 'warning' : 'success'}
        />
        <StatCard
          label={t('dashboard.newRegistrations')}
          value={formatNumber(data.new_registrations_this_month)}
          hint={t('common.thisMonth')}
          icon={<UserPlus className="h-5 w-5" />}
          tone="success"
        />
        <StatCard
          label={t('dashboard.expiringMemberships')}
          value={formatNumber(data.expiring_memberships)}
          hint="14 gün içinde"
          icon={<CreditCard className="h-5 w-5" />}
          tone={data.expiring_memberships > 0 ? 'warning' : 'neutral'}
        />
        <StatCard
          label={t('dashboard.upcomingCompetitions')}
          value={formatNumber(data.upcoming_competitions)}
          hint={`${data.declining_athletes} ${t('dashboard.decliningAthletes').toLowerCase()}`}
          icon={<Trophy className="h-5 w-5" />}
          tone="neutral"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Bugünün programı */}
        <Card title={t('dashboard.todaySchedule')} className="lg:col-span-2" bodyClassName="p-0">
          {data.today_lessons.length === 0 ? (
            <EmptyState title={t('dashboard.noLessonsToday')} icon={<CalendarDays className="h-6 w-6" />} />
          ) : (
            <div className="max-h-[420px] overflow-y-auto">
              <table className="table">
                <thead className="sticky top-0 bg-white dark:bg-surface-dark-alt">
                  <tr>
                    <th>{t('common.time')}</th>
                    <th>{t('lesson.singular')}</th>
                    <th className="hidden md:table-cell">{t('nav.pools')}</th>
                    <th className="hidden lg:table-cell">{t('instructor.singular')}</th>
                    <th>{t('lesson.enrolled')}</th>
                    <th>{t('common.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.today_lessons.map((lesson) => (
                    <tr key={lesson.id}>
                      <td className="whitespace-nowrap font-medium">
                        {formatTimeRange(lesson.start_at, lesson.end_at)}
                      </td>
                      <td>
                        <Link to={`/calendar?lesson=${lesson.id}`} className="hover:text-brand-600">
                          {lesson.title}
                        </Link>
                      </td>
                      <td className="hidden md:table-cell text-xs text-slate-500">
                        {lesson.pool_name}
                        {lesson.lane_name ? ` · ${lesson.lane_name}` : ''}
                      </td>
                      <td className="hidden lg:table-cell text-xs text-slate-500">
                        {lesson.instructor_name ?? '—'}
                      </td>
                      <td className="whitespace-nowrap">
                        <span className="text-sm">
                          {lesson.enrolled_count}/{lesson.capacity}
                        </span>
                      </td>
                      <td>
                        {lesson.attendance_recorded ? (
                          <span className="badge-success">{t('dashboard.attendanceTaken')}</span>
                        ) : (
                          <StatusBadge
                            status={lesson.status}
                            label={t(`lesson.statuses.${lesson.status}`)}
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Seviye dağılımı */}
        <Card title={t('dashboard.levelDistribution')}>
          {data.level_distribution.length === 0 ? (
            <EmptyState title={t('common.noData')} />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={data.level_distribution.map((item) => ({
                    ...item,
                    name: t(`swimLevel.${item.label}`, item.label),
                  }))}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={95}
                  paddingAngle={2}
                >
                  {data.level_distribution.map((_, index) => (
                    <Cell key={index} fill={LEVEL_COLORS[index % LEVEL_COLORS.length]} />
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
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Gelir eğilimi */}
        {can('finance:read') && (
          <Card title={t('dashboard.revenueTrend')}>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={data.revenue_trend}>
                <defs>
                  <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={4} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(value) => formatCompact(value)} width={50} />
                <Tooltip
                  formatter={(value: number) => formatCurrency(value)}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                  fill="url(#revenueGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* Saatlik havuz yoğunluğu */}
        <Card title={t('dashboard.hourlyLoad')}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.pool_load}>
              <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={1} />
              <YAxis tick={{ fontSize: 10 }} width={40} />
              <Tooltip
                formatter={(value: number) => [`${formatNumber(value)} dk`, t('dashboard.hourlyLoad')]}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="value" fill="#38bdf8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-3">
            <p className="mb-1.5 text-xs text-slate-500">
              {t('dashboard.lanesInUse')}: {data.lanes_in_use} / {data.total_lanes}
            </p>
            <ProgressBar value={laneUsagePercent} tone={laneUsagePercent > 80 ? 'warning' : 'brand'} showLabel />
          </div>
        </Card>
      </div>
    </>
  )
}
