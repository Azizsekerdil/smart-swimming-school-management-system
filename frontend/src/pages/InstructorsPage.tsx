/** Eğitmen yönetimi ve iş yükü analizi / Instructor management and workload. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Award,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Clock,
  GraduationCap,
  Pencil,
  Plus,
  Search,
  Trash2,
  Users,
  UserX,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

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
  StatCard,
  TableWrapper,
  Tabs,
} from '@/components/ui'
import { del, get, patch, post } from '@/lib/api'
import {
  formatCurrency,
  formatDate,
  formatDecimal,
  formatNumber,
  formatPercent,
  formatTime,
  initials,
  toISODate,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  Availability,
  Certificate,
  Gender,
  Instructor,
  InstructorDetail,
  InstructorWorkload,
  Message,
  Page,
} from '@/lib/types'

const GENDERS: Gender[] = ['female', 'male', 'unspecified']
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6]

// ---------------------------------------------------------------------------
// Saat yardımcıları — backend "HH:MM:SS" biçiminde time döndürür
// ---------------------------------------------------------------------------
function toMinutes(value: string): number {
  const [hours, minutes] = value.split(':')
  const total = Number(hours) * 60 + Number(minutes)
  return Number.isFinite(total) ? total : 0
}

function minutesToLabel(minutes: number): string {
  return formatTime(new Date(1970, 0, 1, Math.floor(minutes / 60), minutes % 60))
}

// ---------------------------------------------------------------------------
// Form tipleri
// ---------------------------------------------------------------------------
interface InstructorForm {
  first_name: string
  last_name: string
  birth_date: string
  gender: Gender
  phone: string
  email: string
  title: string
  specialties: string
  hire_date: string
  max_weekly_hours: string
  hourly_rate: string
  monthly_salary: string
  bio: string
}

const EMPTY_FORM: InstructorForm = {
  first_name: '',
  last_name: '',
  birth_date: '',
  gender: 'unspecified',
  phone: '',
  email: '',
  title: '',
  specialties: '',
  hire_date: '',
  max_weekly_hours: '40',
  hourly_rate: '',
  monthly_salary: '',
  bio: '',
}

interface CertificateForm {
  name: string
  issuer: string
  issued_date: string
  expiry_date: string
}

const EMPTY_CERT: CertificateForm = { name: '', issuer: '', issued_date: '', expiry_date: '' }

/** Formu backend gövdesine çevirir; ücret alanları yalnızca yetkiliyse gönderilir */
function toInstructorPayload(form: InstructorForm, includeSalary: boolean) {
  const clean = (value: string): string | null => (value.trim() ? value.trim() : null)
  const money = (value: string): number | null => {
    const parsed = Number(value.replace(',', '.'))
    return value.trim() && Number.isFinite(parsed) ? parsed : null
  }
  const base: Record<string, unknown> = {
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    birth_date: form.birth_date || null,
    gender: form.gender,
    phone: clean(form.phone),
    email: clean(form.email),
    title: clean(form.title),
    // "Serbest, Kelebek, Bebek" -> ["Serbest", "Kelebek", "Bebek"]
    specialties: form.specialties
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0),
    hire_date: form.hire_date || null,
    max_weekly_hours: Number(form.max_weekly_hours) > 0 ? Number(form.max_weekly_hours) : 40,
    bio: clean(form.bio),
  }
  if (includeSalary) {
    base.hourly_rate = money(form.hourly_rate)
    base.monthly_salary = money(form.monthly_salary)
  }
  return base
}

// ---------------------------------------------------------------------------
// Müsaitlik takvimi: 7 gün x saat aralığı görselleştirmesi
// ---------------------------------------------------------------------------
function AvailabilityCalendar({ slots }: { slots: Availability[] }) {
  const { t } = useTranslation()

  if (slots.length === 0) {
    return <EmptyState title={t('common.noData')} icon={<CalendarDays className="h-6 w-6" />} />
  }

  const starts = slots.map((slot) => toMinutes(slot.start_time))
  const ends = slots.map((slot) => toMinutes(slot.end_time))
  const min = Math.floor(Math.min(...starts) / 60) * 60
  const max = Math.ceil(Math.max(...ends) / 60) * 60
  const span = Math.max(60, max - min)

  const ticks: number[] = []
  for (let minute = min; minute <= max; minute += 60) ticks.push(minute)

  return (
    <div className="space-y-1.5">
      {/* Saat cetveli */}
      <div className="flex items-center gap-2">
        <span className="w-10 shrink-0" />
        <div className="relative h-4 flex-1">
          {ticks.map((tick, index) => (
            <span
              key={tick}
              className={
                index === 0
                  ? 'absolute text-[10px] text-slate-400'
                  : index === ticks.length - 1
                    ? 'absolute -translate-x-full text-[10px] text-slate-400'
                    : 'absolute -translate-x-1/2 text-[10px] text-slate-400'
              }
              style={{ left: `${((tick - min) / span) * 100}%` }}
            >
              {minutesToLabel(tick)}
            </span>
          ))}
        </div>
      </div>

      {WEEKDAYS.map((weekday) => {
        const daySlots = slots.filter((slot) => slot.weekday === weekday)
        return (
          <div key={weekday} className="flex items-center gap-2">
            <span className="w-10 shrink-0 text-xs font-medium text-slate-500 dark:text-slate-400">
              {t(`weekdays.short.${weekday}`)}
            </span>
            <div className="relative h-7 flex-1 rounded-md bg-slate-100 dark:bg-slate-800">
              {daySlots.map((slot) => {
                const from = toMinutes(slot.start_time)
                const to = toMinutes(slot.end_time)
                const left = ((from - min) / span) * 100
                const width = Math.max(((to - from) / span) * 100, 6)
                return (
                  <div
                    key={slot.id}
                    title={`${t(`weekdays.${weekday}`)} · ${minutesToLabel(from)} – ${minutesToLabel(to)}`}
                    className="absolute top-1 flex h-5 items-center justify-center overflow-hidden whitespace-nowrap rounded bg-brand-500 px-1.5 text-[10px] font-medium text-white dark:bg-brand-600"
                    style={{ left: `${left}%`, width: `${width}%` }}
                  >
                    {minutesToLabel(from)}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sayfa
// ---------------------------------------------------------------------------
export default function InstructorsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const can = useAuth((state) => state.can)
  const hasRole = useAuth((state) => state.hasRole)
  const canSeeSalary = can('finance:read') || hasRole('hr', 'system_admin', 'school_director')
  const canWrite = can('instructor:write')

  const [tab, setTab] = useState('list')
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const [detailId, setDetailId] = useState<number | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Instructor | null>(null)
  const [form, setForm] = useState<InstructorForm>(EMPTY_FORM)
  const [errors, setErrors] = useState<Partial<Record<keyof InstructorForm, string>>>({})

  const [certFormOpen, setCertFormOpen] = useState(false)
  const [certForm, setCertForm] = useState<CertificateForm>(EMPTY_CERT)
  const [certError, setCertError] = useState('')
  const [certDeleteTarget, setCertDeleteTarget] = useState<Certificate | null>(null)
  const [deactivateTarget, setDeactivateTarget] = useState<InstructorDetail | null>(null)

  const [workloadFrom, setWorkloadFrom] = useState(
    toISODate(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)),
  )
  const [workloadTo, setWorkloadTo] = useState(toISODate(new Date()))

  // Arama kutusunu geciktir
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const listQuery = useQuery({
    queryKey: ['instructors', query, activeFilter, page, pageSize],
    queryFn: () =>
      get<Page<Instructor>>('/instructors', {
        q: query || undefined,
        is_active: activeFilter === 'all' ? undefined : activeFilter === 'active',
        page,
        page_size: pageSize,
      }),
  })

  const detailQuery = useQuery({
    queryKey: ['instructor', detailId],
    queryFn: () => get<InstructorDetail>(`/instructors/${detailId}`),
    enabled: detailId !== null,
  })

  const workloadQuery = useQuery({
    queryKey: ['instructor-workload', workloadFrom, workloadTo],
    queryFn: () =>
      get<InstructorWorkload[]>('/instructors/workload', {
        date_from: workloadFrom || undefined,
        date_to: workloadTo || undefined,
      }),
    enabled: tab === 'workload',
  })

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editing
        ? patch<Instructor>(`/instructors/${editing.id}`, payload)
        : post<Instructor>('/instructors', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructors'] })
      queryClient.invalidateQueries({ queryKey: ['instructor'] })
      toastSuccess(t('common.success'))
      setFormOpen(false)
      setEditing(null)
      setForm(EMPTY_FORM)
    },
    onError: (error: unknown) => toastError(error),
  })

  const certMutation = useMutation({
    mutationFn: (payload: { instructorId: number; body: Record<string, unknown> }) =>
      post<Certificate>(`/instructors/${payload.instructorId}/certificates`, payload.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructor'] })
      queryClient.invalidateQueries({ queryKey: ['instructors'] })
      toastSuccess(t('common.success'))
      setCertForm(EMPTY_CERT)
      setCertFormOpen(false)
    },
    onError: (error: unknown) => toastError(error),
  })

  const certDeleteMutation = useMutation({
    mutationFn: (certificate: Certificate) =>
      del<Message>(`/instructors/${certificate.instructor_id}/certificates/${certificate.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructor'] })
      queryClient.invalidateQueries({ queryKey: ['instructors'] })
      toastSuccess(t('common.success'))
      setCertDeleteTarget(null)
    },
    onError: (error: unknown) => toastError(error),
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => del<Message>(`/instructors/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructors'] })
      queryClient.invalidateQueries({ queryKey: ['instructor'] })
      toastSuccess(t('common.success'))
      setDeactivateTarget(null)
      setDetailId(null)
    },
    onError: (error: unknown) => toastError(error),
  })

  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setErrors({})
    setFormOpen(true)
  }

  function openEdit(instructor: Instructor) {
    setEditing(instructor)
    setForm({
      first_name: instructor.first_name,
      last_name: instructor.last_name,
      birth_date: instructor.birth_date ? toISODate(instructor.birth_date) : '',
      gender: instructor.gender,
      phone: instructor.phone ?? '',
      email: instructor.email ?? '',
      title: instructor.title ?? '',
      specialties: instructor.specialties.join(', '),
      hire_date: instructor.hire_date ? toISODate(instructor.hire_date) : '',
      max_weekly_hours: String(instructor.max_weekly_hours),
      hourly_rate: instructor.hourly_rate !== null && instructor.hourly_rate !== undefined ? String(instructor.hourly_rate) : '',
      monthly_salary:
        instructor.monthly_salary !== null && instructor.monthly_salary !== undefined
          ? String(instructor.monthly_salary)
          : '',
      bio: instructor.bio ?? '',
    })
    setErrors({})
    setFormOpen(true)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors: Partial<Record<keyof InstructorForm, string>> = {}
    if (!form.first_name.trim()) nextErrors.first_name = t('common.required')
    if (!form.last_name.trim()) nextErrors.last_name = t('common.required')
    const hours = Number(form.max_weekly_hours)
    if (!Number.isFinite(hours) || hours < 1 || hours > 80) {
      nextErrors.max_weekly_hours = t('common.required')
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    saveMutation.mutate(toInstructorPayload(form, canSeeSalary))
  }

  function updateField(key: keyof InstructorForm, value: string) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  function handleCertSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!certForm.name.trim()) {
      setCertError(t('common.required'))
      return
    }
    if (detailId === null) return
    setCertError('')
    certMutation.mutate({
      instructorId: detailId,
      body: {
        name: certForm.name.trim(),
        issuer: certForm.issuer.trim() || null,
        issued_date: certForm.issued_date || null,
        expiry_date: certForm.expiry_date || null,
      },
    })
  }

  const instructors = listQuery.data?.items ?? []
  const detail = detailQuery.data ?? null
  const workload = workloadQuery.data ?? []
  const chartData = workload.map((row) => ({ name: row.full_name, hours: row.total_hours }))

  return (
    <>
      <PageHeader
        title={t('instructor.title')}
        icon={<Award className="h-5 w-5" />}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={openCreate}>
              <Plus className="h-4 w-4" />
              {t('instructor.new')}
            </button>
          )
        }
      />

      <Tabs
        tabs={[
          { id: 'list', label: t('instructor.title'), icon: <Users className="h-4 w-4" /> },
          { id: 'workload', label: t('instructor.workload'), icon: <BarChart3 className="h-4 w-4" /> },
        ]}
        active={tab}
        onChange={setTab}
      />

      {/* --------------------------------------------------------------- */}
      {/* Eğitmenler sekmesi                                              */}
      {/* --------------------------------------------------------------- */}
      {tab === 'list' && (
        <Card bodyClassName="p-0">
          <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 p-4 dark:border-slate-700">
            <div className="relative min-w-[220px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                className="input pl-9"
                placeholder={t('common.search')}
                value={searchInput}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setSearchInput(event.target.value)
                }
                aria-label={t('common.search')}
              />
            </div>
            <select
              className="select w-auto"
              value={activeFilter}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                setActiveFilter(event.target.value)
                setPage(1)
              }}
              aria-label={t('common.status')}
            >
              <option value="all">{t('common.all')}</option>
              <option value="active">{t('common.active')}</option>
              <option value="passive">{t('common.passive')}</option>
            </select>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {t('common.total')}: {formatNumber(listQuery.data?.total ?? 0)}
            </span>
          </div>

          {listQuery.isLoading ? (
            <LoadingState />
          ) : listQuery.error ? (
            <ErrorState error={listQuery.error} onRetry={listQuery.refetch} />
          ) : instructors.length === 0 ? (
            <EmptyState
              title={t('common.noResults')}
              icon={<Award className="h-6 w-6" />}
              action={
                canWrite ? (
                  <button type="button" className="btn-secondary btn-sm" onClick={openCreate}>
                    <Plus className="h-4 w-4" />
                    {t('instructor.new')}
                  </button>
                ) : undefined
              }
            />
          ) : (
            <>
              <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
                {instructors.map((instructor) => {
                  const expiredCount = instructor.certificates.filter((item) => item.is_expired).length
                  return (
                    <button
                      key={instructor.id}
                      type="button"
                      onClick={() => setDetailId(instructor.id)}
                      className="card card-hover flex w-full flex-col gap-3 p-4 text-left hover:border-brand-300 dark:hover:border-brand-700"
                    >
                      <div className="flex items-start gap-3">
                        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                          {initials(instructor.full_name)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-slate-900 dark:text-slate-100">
                            {instructor.full_name}
                          </p>
                          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                            {instructor.title ?? instructor.employee_number}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-1">
                          <Badge tone={instructor.is_active ? 'success' : 'neutral'}>
                            {instructor.is_active ? t('common.active') : t('common.passive')}
                          </Badge>
                          {instructor.is_demo && <DemoBadge />}
                        </div>
                      </div>

                      {instructor.specialties.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {instructor.specialties.slice(0, 4).map((specialty) => (
                            <Badge key={specialty} tone="info">
                              {specialty}
                            </Badge>
                          ))}
                          {instructor.specialties.length > 4 && (
                            <Badge tone="neutral">+{instructor.specialties.length - 4}</Badge>
                          )}
                        </div>
                      )}

                      <div className="mt-auto flex flex-wrap items-center gap-3 border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                        <span className="flex items-center gap-1">
                          <GraduationCap className="h-3.5 w-3.5" />
                          {t('instructor.certificates')}: {formatNumber(instructor.certificates.length)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" />
                          {t('instructor.maxWeeklyHours')}: {formatNumber(instructor.max_weekly_hours)}
                        </span>
                        {expiredCount > 0 && (
                          <span className="text-rose-600 dark:text-rose-400">
                            {t('instructor.expired')}: {formatNumber(expiredCount)}
                          </span>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
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
            </>
          )}
        </Card>
      )}

      {/* --------------------------------------------------------------- */}
      {/* İş yükü sekmesi                                                 */}
      {/* --------------------------------------------------------------- */}
      {tab === 'workload' && (
        <div className="space-y-4">
          <Card>
            <div className="flex flex-wrap items-end gap-3">
              <Field label={t('lesson.start')} className="w-44">
                <input
                  type="date"
                  className="input"
                  value={workloadFrom}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    setWorkloadFrom(event.target.value)
                  }
                />
              </Field>
              <Field label={t('lesson.end')} className="w-44">
                <input
                  type="date"
                  className="input"
                  value={workloadTo}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    setWorkloadTo(event.target.value)
                  }
                />
              </Field>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => workloadQuery.refetch()}
              >
                {t('common.refresh')}
              </button>
            </div>
          </Card>

          {workloadQuery.isLoading ? (
            <LoadingState />
          ) : workloadQuery.error ? (
            <Card>
              <ErrorState error={workloadQuery.error} onRetry={workloadQuery.refetch} />
            </Card>
          ) : workload.length === 0 ? (
            <Card>
              <EmptyState title={t('common.noData')} icon={<BarChart3 className="h-6 w-6" />} />
            </Card>
          ) : (
            <>
              <Card title={t('instructor.workload')}>
                <ResponsiveContainer width="100%" height={Math.max(260, chartData.length * 34)}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                    <XAxis type="number" tick={{ fontSize: 10 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 10 }}
                      width={130}
                      interval={0}
                    />
                    <Tooltip
                      formatter={(value: number) => [formatDecimal(value, 1), t('common.time')]}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Bar dataKey="hours" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <Card bodyClassName="p-0">
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('instructor.singular')}</th>
                      <th className="text-right">{t('instructor.lessonCount')}</th>
                      <th className="text-right">{t('common.time')}</th>
                      <th className="text-right">{t('instructor.studentCount')}</th>
                      <th className="text-right">{t('instructor.occupancyRate')}</th>
                      <th className="text-right">{t('instructor.cancellationRate')}</th>
                      <th className="text-right">{t('instructor.privateRatio')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workload.map((row) => (
                      <tr key={row.instructor_id}>
                        <td>
                          <button
                            type="button"
                            className="font-medium text-brand-600 hover:underline dark:text-brand-400"
                            onClick={() => setDetailId(row.instructor_id)}
                          >
                            {row.full_name}
                          </button>
                        </td>
                        <td className="text-right">{formatNumber(row.lesson_count)}</td>
                        <td className="text-right font-medium">{formatDecimal(row.total_hours, 1)}</td>
                        <td className="text-right">{formatNumber(row.student_count)}</td>
                        <td className="text-right">
                          <span
                            className={
                              row.occupancy_rate >= 70
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : row.occupancy_rate >= 40
                                  ? 'text-amber-600 dark:text-amber-400'
                                  : 'text-rose-600 dark:text-rose-400'
                            }
                          >
                            {formatPercent(row.occupancy_rate)}
                          </span>
                        </td>
                        <td className="text-right">
                          <span
                            className={
                              row.cancellation_rate > 15
                                ? 'text-rose-600 dark:text-rose-400'
                                : 'text-slate-600 dark:text-slate-300'
                            }
                          >
                            {formatPercent(row.cancellation_rate)}
                          </span>
                        </td>
                        <td className="text-right">{formatPercent(row.private_ratio)}</td>
                      </tr>
                    ))}
                  </tbody>
                </TableWrapper>
              </Card>

              <Alert tone="info">{t('statistics.instructorDisclaimer')}</Alert>
            </>
          )}
        </div>
      )}

      {/* --------------------------------------------------------------- */}
      {/* Eğitmen detay modalı                                            */}
      {/* --------------------------------------------------------------- */}
      <Modal
        open={detailId !== null}
        onClose={() => {
          setDetailId(null)
          setCertFormOpen(false)
        }}
        title={detail ? detail.full_name : t('instructor.singular')}
        size="xl"
        footer={
          detail ? (
            <>
              {can('instructor:delete') && detail.is_active && (
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => setDeactivateTarget(detail)}
                >
                  <UserX className="h-4 w-4" />
                  {t('users.deactivate')}
                </button>
              )}
              {canWrite && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setDetailId(null)
                    openEdit(detail)
                  }}
                >
                  <Pencil className="h-4 w-4" />
                  {t('common.edit')}
                </button>
              )}
            </>
          ) : undefined
        }
      >
        {detailQuery.isLoading ? (
          <LoadingState />
        ) : detailQuery.error ? (
          <ErrorState error={detailQuery.error} onRetry={detailQuery.refetch} />
        ) : detail ? (
          <div className="space-y-5">
            {/* Kimlik bilgileri */}
            <div className="flex flex-wrap items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-base font-semibold text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                {initials(detail.full_name)}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {detail.title ?? t('instructor.singular')}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {t('instructor.employeeNumber')}: {detail.employee_number}
                  {detail.hire_date ? ` · ${t('instructor.hireDate')}: ${formatDate(detail.hire_date)}` : ''}
                </p>
              </div>
              <div className="ml-auto flex items-center gap-2">
                <Badge tone={detail.is_active ? 'success' : 'neutral'}>
                  {detail.is_active ? t('common.active') : t('common.passive')}
                </Badge>
                {detail.is_demo && <DemoBadge />}
              </div>
            </div>

            {/* Sayaçlar */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label={t('instructor.studentCount')}
                value={formatNumber(detail.student_count)}
                icon={<Users className="h-5 w-5" />}
                tone="brand"
              />
              <StatCard
                label={t('instructor.weeklyHours')}
                value={formatDecimal(detail.weekly_hours, 1)}
                hint={`${formatNumber(detail.weekly_lesson_count)} ${t('instructor.lessonCount')} · ${t('instructor.maxWeeklyHours')}: ${formatNumber(detail.max_weekly_hours)}`}
                icon={<Clock className="h-5 w-5" />}
                tone={detail.weekly_hours > detail.max_weekly_hours ? 'danger' : 'neutral'}
              />
              <StatCard
                label={t('guardian.upcomingLessons')}
                value={formatNumber(detail.upcoming_lessons)}
                icon={<CalendarDays className="h-5 w-5" />}
                tone="neutral"
              />
              <StatCard
                label={t('attendance.rate')}
                value={detail.attendance_rate !== null && detail.attendance_rate !== undefined
                  ? formatPercent(detail.attendance_rate)
                  : '—'}
                icon={<CheckCircle2 className="h-5 w-5" />}
                tone={
                  detail.attendance_rate !== null && detail.attendance_rate !== undefined
                    ? detail.attendance_rate >= 80
                      ? 'success'
                      : 'warning'
                    : 'neutral'
                }
              />
            </div>

            {/* İletişim / uzmanlık */}
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {t('common.phone')}
                </dt>
                <dd className="mt-0.5 text-sm text-slate-800 dark:text-slate-200">
                  {detail.phone ?? '—'}
                </dd>
              </div>
              <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {t('common.email')}
                </dt>
                <dd className="mt-0.5 break-words text-sm text-slate-800 dark:text-slate-200">
                  {detail.email ?? '—'}
                </dd>
              </div>
              <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {t('student.birthDate')}
                </dt>
                <dd className="mt-0.5 text-sm text-slate-800 dark:text-slate-200">
                  {detail.birth_date ? formatDate(detail.birth_date) : '—'}
                </dd>
              </div>
              <div className="rounded-lg border border-slate-200 p-3 sm:col-span-2 lg:col-span-3 dark:border-slate-700">
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {t('instructor.specialties')}
                </dt>
                <dd className="mt-1 flex flex-wrap gap-1">
                  {detail.specialties.length === 0 ? (
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                      {t('common.none')}
                    </span>
                  ) : (
                    detail.specialties.map((specialty) => (
                      <Badge key={specialty} tone="info">
                        {specialty}
                      </Badge>
                    ))
                  )}
                </dd>
              </div>
            </dl>

            {detail.bio && (
              <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                <p className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {t('instructor.bio')}
                </p>
                {detail.bio}
              </div>
            )}

            {/* Ücret bilgisi */}
            {canSeeSalary ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                    {t('instructor.hourlyRate')}
                  </p>
                  <p className="mt-0.5 text-sm font-medium text-slate-800 dark:text-slate-200">
                    {detail.hourly_rate !== null && detail.hourly_rate !== undefined
                      ? formatCurrency(detail.hourly_rate)
                      : '—'}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                    {t('instructor.monthlySalary')}
                  </p>
                  <p className="mt-0.5 text-sm font-medium text-slate-800 dark:text-slate-200">
                    {detail.monthly_salary !== null && detail.monthly_salary !== undefined
                      ? formatCurrency(detail.monthly_salary)
                      : '—'}
                  </p>
                </div>
              </div>
            ) : (
              <Alert tone="warning">{t('instructor.salaryHidden')}</Alert>
            )}

            {/* Sertifikalar */}
            <section>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                  <GraduationCap className="h-4 w-4" />
                  {t('instructor.certificates')} ({formatNumber(detail.certificates.length)})
                </h3>
                {canWrite && (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => {
                      setCertForm(EMPTY_CERT)
                      setCertError('')
                      setCertFormOpen((previous) => !previous)
                    }}
                  >
                    <Plus className="h-4 w-4" />
                    {t('common.add')}
                  </button>
                )}
              </div>

              {certFormOpen && canWrite && (
                <form
                  onSubmit={handleCertSubmit}
                  className="mb-3 grid gap-3 rounded-lg border border-slate-200 p-3 sm:grid-cols-2 dark:border-slate-700"
                >
                  <Field label={t('instructor.certificateName')} required error={certError || undefined}>
                    <input
                      className="input"
                      value={certForm.name}
                      onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                        setCertForm((previous) => ({ ...previous, name: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label={t('instructor.issuer')}>
                    <input
                      className="input"
                      value={certForm.issuer}
                      onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                        setCertForm((previous) => ({ ...previous, issuer: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label={t('instructor.issuedDate')}>
                    <input
                      type="date"
                      className="input"
                      value={certForm.issued_date}
                      onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                        setCertForm((previous) => ({ ...previous, issued_date: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label={t('instructor.expiryDate')}>
                    <input
                      type="date"
                      className="input"
                      value={certForm.expiry_date}
                      onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                        setCertForm((previous) => ({ ...previous, expiry_date: event.target.value }))
                      }
                    />
                  </Field>
                  <div className="flex items-center justify-end gap-2 sm:col-span-2">
                    <button
                      type="button"
                      className="btn-ghost btn-sm"
                      onClick={() => setCertFormOpen(false)}
                    >
                      {t('common.cancel')}
                    </button>
                    <button type="submit" className="btn-primary btn-sm" disabled={certMutation.isPending}>
                      {t('common.save')}
                    </button>
                  </div>
                </form>
              )}

              {detail.certificates.length === 0 ? (
                <EmptyState title={t('common.noData')} icon={<GraduationCap className="h-6 w-6" />} />
              ) : (
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('instructor.certificateName')}</th>
                      <th>{t('instructor.issuer')}</th>
                      <th>{t('instructor.issuedDate')}</th>
                      <th>{t('instructor.expiryDate')}</th>
                      {canWrite && <th className="text-right">{t('common.actions')}</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.certificates.map((certificate) => (
                      <tr
                        key={certificate.id}
                        className={certificate.is_expired ? 'bg-rose-50/60 dark:bg-rose-900/10' : undefined}
                      >
                        <td className="font-medium text-slate-800 dark:text-slate-200">
                          {certificate.name}
                        </td>
                        <td className="text-xs text-slate-500 dark:text-slate-400">
                          {certificate.issuer ?? '—'}
                        </td>
                        <td className="whitespace-nowrap text-xs">
                          {certificate.issued_date ? formatDate(certificate.issued_date) : '—'}
                        </td>
                        <td className="whitespace-nowrap text-xs">
                          {certificate.expiry_date ? (
                            <span
                              className={
                                certificate.is_expired
                                  ? 'font-medium text-rose-600 dark:text-rose-400'
                                  : 'text-slate-600 dark:text-slate-300'
                              }
                            >
                              {formatDate(certificate.expiry_date)}
                              {certificate.is_expired ? ` · ${t('instructor.expired')}` : ''}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        {canWrite && (
                          <td className="text-right">
                            <button
                              type="button"
                              className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                              onClick={() => setCertDeleteTarget(certificate)}
                              title={t('common.delete')}
                              aria-label={t('common.delete')}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </TableWrapper>
              )}
            </section>

            {/* Müsaitlik takvimi */}
            <section>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <CalendarDays className="h-4 w-4" />
                {t('instructor.availability')}
              </h3>
              <AvailabilityCalendar slots={detail.availabilities} />
            </section>

            {/* İzinler */}
            <section>
              <h3 className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                {t('instructor.leaves')}
              </h3>
              {detail.leaves.length === 0 ? (
                <EmptyState title={t('common.noData')} icon={<CalendarDays className="h-6 w-6" />} />
              ) : (
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('lesson.start')}</th>
                      <th>{t('lesson.end')}</th>
                      <th>{t('instructor.leaveType')}</th>
                      <th>{t('common.description')}</th>
                      <th>{t('common.status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.leaves.map((leave) => (
                      <tr key={leave.id}>
                        <td className="whitespace-nowrap">{formatDate(leave.start_date)}</td>
                        <td className="whitespace-nowrap">{formatDate(leave.end_date)}</td>
                        <td className="text-xs text-slate-500 dark:text-slate-400">{leave.leave_type}</td>
                        <td className="text-xs text-slate-500 dark:text-slate-400">
                          {leave.reason ?? '—'}
                        </td>
                        <td>
                          <Badge tone={leave.approved ? 'success' : 'warning'}>
                            {leave.approved ? t('common.yes') : t('common.no')}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableWrapper>
              )}
            </section>
          </div>
        ) : (
          <EmptyState title={t('common.noData')} />
        )}
      </Modal>

      {/* --------------------------------------------------------------- */}
      {/* Yeni / düzenle formu                                            */}
      {/* --------------------------------------------------------------- */}
      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `${t('common.edit')} — ${editing.full_name}` : t('instructor.new')}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setFormOpen(false)}
              disabled={saveMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              form="instructor-form"
              className="btn-primary"
              disabled={saveMutation.isPending}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <form id="instructor-form" onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <Field label={t('student.firstName')} required error={errors.first_name}>
            <input
              className="input"
              value={form.first_name}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('first_name', event.target.value)
              }
            />
          </Field>
          <Field label={t('student.lastName')} required error={errors.last_name}>
            <input
              className="input"
              value={form.last_name}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('last_name', event.target.value)
              }
            />
          </Field>
          <Field label={t('student.birthDate')}>
            <input
              type="date"
              className="input"
              value={form.birth_date}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('birth_date', event.target.value)
              }
            />
          </Field>
          <Field label={t('student.gender')}>
            <select
              className="select"
              value={form.gender}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setForm((previous) => ({ ...previous, gender: event.target.value as Gender }))
              }
            >
              {GENDERS.map((gender) => (
                <option key={gender} value={gender}>
                  {t(`gender.${gender}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('common.phone')}>
            <input
              className="input"
              value={form.phone}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('phone', event.target.value)
              }
            />
          </Field>
          <Field label={t('common.email')}>
            <input
              type="email"
              className="input"
              value={form.email}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('email', event.target.value)
              }
            />
          </Field>
          <Field label={t('instructor.jobTitle')}>
            <input
              className="input"
              value={form.title}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('title', event.target.value)
              }
            />
          </Field>
          <Field label={t('instructor.hireDate')}>
            <input
              type="date"
              className="input"
              value={form.hire_date}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('hire_date', event.target.value)
              }
            />
          </Field>
          <Field
            label={t('instructor.specialties')}
            hint={form.specialties
              .split(',')
              .map((item) => item.trim())
              .filter((item) => item.length > 0)
              .join(' · ')}
            className="sm:col-span-2"
          >
            <input
              className="input"
              value={form.specialties}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('specialties', event.target.value)
              }
            />
          </Field>
          <Field label={t('instructor.maxWeeklyHours')} required error={errors.max_weekly_hours}>
            <input
              type="number"
              min={1}
              max={80}
              className="input"
              value={form.max_weekly_hours}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('max_weekly_hours', event.target.value)
              }
            />
          </Field>

          {/* Ücret alanları yalnızca yetkili kullanıcılara açılır */}
          {canSeeSalary ? (
            <>
              <Field label={t('instructor.hourlyRate')}>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  className="input"
                  value={form.hourly_rate}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    updateField('hourly_rate', event.target.value)
                  }
                />
              </Field>
              <Field label={t('instructor.monthlySalary')}>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  className="input"
                  value={form.monthly_salary}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    updateField('monthly_salary', event.target.value)
                  }
                />
              </Field>
            </>
          ) : (
            <div className="sm:col-span-2">
              <Alert tone="warning">{t('instructor.salaryHidden')}</Alert>
            </div>
          )}

          <Field label={t('instructor.bio')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={3}
              value={form.bio}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                updateField('bio', event.target.value)
              }
            />
          </Field>
        </form>
      </Modal>

      {/* Sertifika silme onayı */}
      <ConfirmDialog
        open={certDeleteTarget !== null}
        onClose={() => setCertDeleteTarget(null)}
        onConfirm={() => certDeleteTarget && certDeleteMutation.mutate(certDeleteTarget)}
        title={t('common.delete')}
        message={`${t('instructor.certificateName')}: ${certDeleteTarget?.name ?? ''}`}
        confirmLabel={t('common.delete')}
        loading={certDeleteMutation.isPending}
      />

      {/* Eğitmeni pasife alma onayı */}
      <ConfirmDialog
        open={deactivateTarget !== null}
        onClose={() => setDeactivateTarget(null)}
        onConfirm={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)}
        title={t('users.deactivate')}
        message={`${t('instructor.singular')}: ${deactivateTarget?.full_name ?? ''}`}
        confirmLabel={t('users.deactivate')}
        loading={deactivateMutation.isPending}
      />
    </>
  )
}
