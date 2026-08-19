/** Üyelik ve paket yönetimi: üyelikler, paketler, süresi dolacaklar, ders hakkı azalanlar. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Ban,
  CreditCard,
  Layers,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Search,
  Snowflake,
  Timer,
  TrendingDown,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  Badge,
  Card,
  ConfirmDialog,
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
import { del, get, patch, post } from '@/lib/api'
import { formatCurrency, formatDate, formatNumber, toISODate } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  Membership,
  MembershipStatus,
  Message,
  Package,
  Page,
  PaymentMethod,
  Student,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------
const TAB_IDS = ['memberships', 'packages', 'expiring', 'lowCredit'] as const
type TabId = (typeof TAB_IDS)[number]

function isTabId(value: string): value is TabId {
  return (TAB_IDS as readonly string[]).includes(value)
}

const MEMBERSHIP_STATUSES: MembershipStatus[] = [
  'active',
  'expired',
  'frozen',
  'cancelled',
  'pending',
]

const PACKAGE_TYPES = [
  'lesson_pack',
  'monthly',
  'quarterly',
  'biannual',
  'annual',
  'private_pack',
  'trial',
]

const PAYMENT_METHODS: PaymentMethod[] = ['cash', 'card', 'transfer', 'online', 'other']

const EXPIRING_DAY_OPTIONS = [7, 14, 30, 60]
const LOW_CREDIT_OPTIONS = [1, 2, 3, 5]

/** Öğrenci seçicide tutulan asgari bilgi */
interface PickedStudent {
  id: number
  full_name: string
  student_number: string
}

interface MembershipFormState {
  student: PickedStudent | null
  packageId: string
  startDate: string
  discountAmount: string
  discountReason: string
  autoRenew: boolean
  createPayment: boolean
  paymentAmount: string
  paymentMethod: PaymentMethod
}

interface FreezeFormState {
  startDate: string
  endDate: string
  reason: string
}

interface RenewFormState {
  packageId: string
  startDate: string
  discountAmount: string
  createPayment: boolean
  paymentMethod: PaymentMethod
}

interface PackageFormState {
  id: number | null
  name: string
  nameEn: string
  packageType: string
  description: string
  lessonCount: string
  durationDays: string
  price: string
  maxFreezeDays: string
  color: string
  isActive: boolean
}

function emptyPackageForm(): PackageFormState {
  return {
    id: null,
    name: '',
    nameEn: '',
    packageType: 'lesson_pack',
    description: '',
    lessonCount: '',
    durationDays: '',
    price: '',
    maxFreezeDays: '30',
    color: '#6366f1',
    isActive: true,
  }
}

// ---------------------------------------------------------------------------
// Öğrenci seçici (arama ile)
// ---------------------------------------------------------------------------
function StudentPicker({
  value,
  onChange,
  label,
  required,
}: {
  value: PickedStudent | null
  onChange: (student: PickedStudent | null) => void
  label: string
  required?: boolean
}) {
  const { t } = useTranslation()
  const [term, setTerm] = useState('')
  const trimmed = term.trim()

  const { data, isFetching } = useQuery({
    queryKey: ['membership-student-search', trimmed],
    queryFn: () => get<Page<Student>>('/students', { q: trimmed, page: 1, page_size: 8 }),
    enabled: trimmed.length >= 2 && value === null,
  })

  if (value) {
    return (
      <Field label={label} required={required}>
        <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800">
          <span className="truncate text-sm text-slate-800 dark:text-slate-100">
            {value.full_name}
            <span className="ml-2 font-mono text-xs text-slate-400">{value.student_number}</span>
          </span>
          <button
            type="button"
            className="rounded p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
            onClick={() => {
              onChange(null)
              setTerm('')
            }}
            aria-label={t('common.close')}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </Field>
    )
  }

  return (
    <Field label={label} required={required}>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input
          type="text"
          className="input pl-9"
          value={term}
          placeholder={t('common.search')}
          onChange={(event) => setTerm(event.target.value)}
        />
        {trimmed.length >= 2 && (
          <div className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-panel dark:border-slate-700 dark:bg-surface-dark-alt">
            {isFetching ? (
              <p className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                {t('common.loading')}
              </p>
            ) : (data?.items.length ?? 0) === 0 ? (
              <p className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                {t('common.noResults')}
              </p>
            ) : (
              (data?.items ?? []).map((student) => (
                <button
                  key={student.id}
                  type="button"
                  className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-700/50"
                  onClick={() => {
                    onChange({
                      id: student.id,
                      full_name: student.full_name,
                      student_number: student.student_number,
                    })
                    setTerm('')
                  }}
                >
                  <span className="truncate text-slate-800 dark:text-slate-100">
                    {student.full_name}
                  </span>
                  <span className="font-mono text-xs text-slate-400">{student.student_number}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </Field>
  )
}

// ---------------------------------------------------------------------------
// Kalan ders hücresi
// ---------------------------------------------------------------------------
function CreditsCell({ membership }: { membership: Membership }) {
  const { t } = useTranslation()
  if (membership.total_credits === null || membership.total_credits === undefined) {
    return <span className="text-xs text-slate-500 dark:text-slate-400">{t('membership.unlimited')}</span>
  }
  const remaining = membership.remaining_credits ?? 0
  return (
    <div className="min-w-[7rem]">
      <p className="text-xs font-medium text-slate-700 dark:text-slate-200">
        {formatNumber(remaining)} / {formatNumber(membership.total_credits)}
      </p>
      <div className="mt-1">
        <ProgressBar
          value={membership.usage_rate}
          tone={remaining <= 2 ? 'danger' : remaining <= 5 ? 'warning' : 'brand'}
        />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sayfa
// ---------------------------------------------------------------------------
export default function MembershipsPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const canWrite = can('membership:write')
  const todayISO = toISODate(new Date())

  const [tab, setTab] = useState<TabId>('memberships')

  // Üyelik listesi filtreleri
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [filterStudent, setFilterStudent] = useState<PickedStudent | null>(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPackage, setFilterPackage] = useState('')

  const [expiringDays, setExpiringDays] = useState(14)
  const [lowThreshold, setLowThreshold] = useState(2)

  // Diyaloglar
  const [membershipForm, setMembershipForm] = useState<MembershipFormState | null>(null)
  const [freezeTarget, setFreezeTarget] = useState<Membership | null>(null)
  const [freezeForm, setFreezeForm] = useState<FreezeFormState>({
    startDate: todayISO,
    endDate: todayISO,
    reason: '',
  })
  const [unfreezeTarget, setUnfreezeTarget] = useState<Membership | null>(null)
  const [renewTarget, setRenewTarget] = useState<Membership | null>(null)
  const [renewForm, setRenewForm] = useState<RenewFormState>({
    packageId: '',
    startDate: '',
    discountAmount: '0',
    createPayment: true,
    paymentMethod: 'cash',
  })
  const [cancelTarget, setCancelTarget] = useState<Membership | null>(null)
  const [cancelReason, setCancelReason] = useState('')
  const [packageForm, setPackageForm] = useState<PackageFormState | null>(null)
  const [packageDeleteTarget, setPackageDeleteTarget] = useState<Package | null>(null)

  // -------------------------------------------------------------------------
  // Sorgular
  // -------------------------------------------------------------------------
  const packagesQuery = useQuery({
    queryKey: ['packages'],
    queryFn: () => get<Package[]>('/packages'),
  })

  const membershipsQuery = useQuery({
    queryKey: ['memberships', page, pageSize, filterStatus, filterPackage, filterStudent?.id ?? null],
    queryFn: () =>
      get<Page<Membership>>('/memberships', {
        page,
        page_size: pageSize,
        status: filterStatus || undefined,
        package_id: filterPackage ? Number(filterPackage) : undefined,
        student_id: filterStudent?.id,
      }),
    enabled: tab === 'memberships',
  })

  const expiringQuery = useQuery({
    queryKey: ['memberships-expiring', expiringDays],
    queryFn: () => get<Membership[]>('/memberships/expiring', { days: expiringDays }),
    enabled: tab === 'expiring',
  })

  const lowCreditQuery = useQuery({
    queryKey: ['memberships-low-credit', lowThreshold],
    queryFn: () => get<Membership[]>('/memberships/low-credit', { threshold: lowThreshold }),
    enabled: tab === 'lowCredit',
  })

  const packages = packagesQuery.data ?? []

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ['memberships'] })
    queryClient.invalidateQueries({ queryKey: ['memberships-expiring'] })
    queryClient.invalidateQueries({ queryKey: ['memberships-low-credit'] })
    queryClient.invalidateQueries({ queryKey: ['packages'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  // -------------------------------------------------------------------------
  // Mutasyonlar
  // -------------------------------------------------------------------------
  const createMembershipMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => post<Membership>('/memberships', payload),
    onSuccess: () => {
      invalidateAll()
      setMembershipForm(null)
      toastSuccess(t('common.success'), t('membership.new'))
    },
    onError: (error) => toastError(error),
  })

  const freezeMutation = useMutation({
    mutationFn: (input: { id: number; body: Record<string, unknown> }) =>
      post<Membership>(`/memberships/${input.id}/freeze`, input.body),
    onSuccess: () => {
      invalidateAll()
      setFreezeTarget(null)
      toastSuccess(t('common.success'), t('membership.freeze'))
    },
    onError: (error) => toastError(error),
  })

  const unfreezeMutation = useMutation({
    mutationFn: (id: number) => post<Membership>(`/memberships/${id}/unfreeze`),
    onSuccess: () => {
      invalidateAll()
      setUnfreezeTarget(null)
      toastSuccess(t('common.success'), t('membership.unfreeze'))
    },
    onError: (error) => toastError(error),
  })

  const renewMutation = useMutation({
    mutationFn: (input: { id: number; body: Record<string, unknown> }) =>
      post<Membership>(`/memberships/${input.id}/renew`, input.body),
    onSuccess: () => {
      invalidateAll()
      setRenewTarget(null)
      toastSuccess(t('common.success'), t('membership.renew'))
    },
    onError: (error) => toastError(error),
  })

  const cancelMutation = useMutation({
    mutationFn: (input: { id: number; reason: string }) =>
      post<Message>(`/memberships/${input.id}/cancel`, undefined, { reason: input.reason }),
    onSuccess: () => {
      invalidateAll()
      setCancelTarget(null)
      setCancelReason('')
      toastSuccess(t('common.success'), t('membership.cancel'))
    },
    onError: (error) => toastError(error),
  })

  const refreshStatusesMutation = useMutation({
    mutationFn: () => post<Message>('/memberships/refresh-statuses'),
    onSuccess: (data) => {
      invalidateAll()
      toastSuccess(t('common.success'), data.message)
    },
    onError: (error) => toastError(error),
  })

  const savePackageMutation = useMutation({
    mutationFn: (input: { id: number | null; body: Record<string, unknown> }) =>
      input.id === null
        ? post<Package>('/packages', input.body)
        : patch<Package>(`/packages/${input.id}`, input.body),
    onSuccess: () => {
      invalidateAll()
      setPackageForm(null)
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const deactivatePackageMutation = useMutation({
    mutationFn: (id: number) => del<Message>(`/packages/${id}`),
    onSuccess: () => {
      invalidateAll()
      setPackageDeleteTarget(null)
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  // -------------------------------------------------------------------------
  // Diyalog açıcılar
  // -------------------------------------------------------------------------
  function openNewMembership() {
    setMembershipForm({
      student: null,
      packageId: packages.find((item) => item.is_active)?.id.toString() ?? '',
      startDate: todayISO,
      discountAmount: '0',
      discountReason: '',
      autoRenew: false,
      createPayment: true,
      paymentAmount: '',
      paymentMethod: 'cash',
    })
  }

  function openFreeze(membership: Membership) {
    setFreezeForm({ startDate: todayISO, endDate: todayISO, reason: '' })
    setFreezeTarget(membership)
  }

  function openRenew(membership: Membership) {
    setRenewForm({
      packageId: membership.package_id.toString(),
      startDate: '',
      discountAmount: '0',
      createPayment: true,
      paymentMethod: 'cash',
    })
    setRenewTarget(membership)
  }

  function openCancel(membership: Membership) {
    setCancelReason('')
    setCancelTarget(membership)
  }

  function openEditPackage(item: Package) {
    setPackageForm({
      id: item.id,
      name: item.name,
      nameEn: item.name_en ?? '',
      packageType: item.package_type,
      description: item.description ?? '',
      lessonCount: item.lesson_count !== null && item.lesson_count !== undefined ? String(item.lesson_count) : '',
      durationDays:
        item.duration_days !== null && item.duration_days !== undefined ? String(item.duration_days) : '',
      price: String(item.price),
      maxFreezeDays: String(item.max_freeze_days),
      color: item.color,
      isActive: item.is_active,
    })
  }

  // -------------------------------------------------------------------------
  // Gönderimler
  // -------------------------------------------------------------------------
  function submitMembership() {
    if (!membershipForm?.student || !membershipForm.packageId) return
    createMembershipMutation.mutate({
      student_id: membershipForm.student.id,
      package_id: Number(membershipForm.packageId),
      start_date: membershipForm.startDate || null,
      discount_amount: Number(membershipForm.discountAmount || 0),
      discount_reason: membershipForm.discountReason.trim() || null,
      auto_renew: membershipForm.autoRenew,
      notes: null,
      create_payment: membershipForm.createPayment,
      payment_amount:
        membershipForm.createPayment && membershipForm.paymentAmount.trim() !== ''
          ? Number(membershipForm.paymentAmount)
          : null,
      payment_method: membershipForm.paymentMethod,
    })
  }

  function submitFreeze() {
    if (!freezeTarget) return
    freezeMutation.mutate({
      id: freezeTarget.id,
      body: {
        start_date: freezeForm.startDate,
        end_date: freezeForm.endDate,
        reason: freezeForm.reason.trim() || null,
      },
    })
  }

  function submitRenew() {
    if (!renewTarget) return
    renewMutation.mutate({
      id: renewTarget.id,
      body: {
        package_id: renewForm.packageId ? Number(renewForm.packageId) : null,
        start_date: renewForm.startDate || null,
        discount_amount: Number(renewForm.discountAmount || 0),
        create_payment: renewForm.createPayment,
        payment_method: renewForm.paymentMethod,
      },
    })
  }

  function submitPackage() {
    if (!packageForm || packageForm.name.trim() === '' || packageForm.price.trim() === '') return
    savePackageMutation.mutate({
      id: packageForm.id,
      body: {
        name: packageForm.name.trim(),
        name_en: packageForm.nameEn.trim() || null,
        package_type: packageForm.packageType,
        description: packageForm.description.trim() || null,
        lesson_count: packageForm.lessonCount.trim() !== '' ? Number(packageForm.lessonCount) : null,
        duration_days: packageForm.durationDays.trim() !== '' ? Number(packageForm.durationDays) : null,
        price: Number(packageForm.price),
        max_freeze_days: Number(packageForm.maxFreezeDays || 0),
        color: packageForm.color,
        is_active: packageForm.isActive,
      },
    })
  }

  // -------------------------------------------------------------------------
  // Ortak satır işlemleri
  // -------------------------------------------------------------------------
  function renderActions(membership: Membership) {
    if (!canWrite) return <span className="text-xs text-slate-400">—</span>
    return (
      <div className="flex flex-wrap items-center gap-1">
        {membership.status === 'active' && (
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => openFreeze(membership)}
            title={t('membership.freeze')}
          >
            <Snowflake className="h-3.5 w-3.5" />
          </button>
        )}
        {membership.status === 'frozen' && (
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => setUnfreezeTarget(membership)}
            title={t('membership.unfreeze')}
          >
            <Play className="h-3.5 w-3.5" />
          </button>
        )}
        <button
          type="button"
          className="btn-ghost btn-sm"
          onClick={() => openRenew(membership)}
          title={t('membership.renew')}
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
        {membership.status !== 'cancelled' && (
          <button
            type="button"
            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
            onClick={() => openCancel(membership)}
            title={t('membership.cancel')}
          >
            <Ban className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    )
  }

  function renderStudentCell(membership: Membership) {
    return (
      <>
        <span className="font-medium text-slate-900 dark:text-slate-100">
          {membership.student_name ?? '—'}
        </span>
        {membership.student_number && (
          <span className="ml-2 font-mono text-xs text-slate-400">{membership.student_number}</span>
        )}
      </>
    )
  }

  // -------------------------------------------------------------------------
  // Görünüm
  // -------------------------------------------------------------------------
  return (
    <>
      <PageHeader
        title={t('membership.title')}
        subtitle={t('membership.singular')}
        icon={<CreditCard className="h-5 w-5" />}
        actions={
          canWrite && (
            <>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => refreshStatusesMutation.mutate()}
                disabled={refreshStatusesMutation.isPending}
              >
                {refreshStatusesMutation.isPending ? (
                  <Spinner />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
                {t('common.status')} · {t('common.refresh')}
              </button>
              <button type="button" className="btn-primary btn-sm" onClick={openNewMembership}>
                <Plus className="h-3.5 w-3.5" />
                {t('membership.new')}
              </button>
            </>
          )
        }
      />

      <Tabs
        tabs={[
          {
            id: 'memberships',
            label: t('membership.title'),
            icon: <CreditCard className="h-4 w-4" />,
          },
          { id: 'packages', label: t('membership.packages'), icon: <Layers className="h-4 w-4" /> },
          { id: 'expiring', label: t('membership.expiring'), icon: <Timer className="h-4 w-4" /> },
          {
            id: 'lowCredit',
            label: t('membership.lowCredit'),
            icon: <TrendingDown className="h-4 w-4" />,
          },
        ]}
        active={tab}
        onChange={(id) => {
          if (isTabId(id)) setTab(id)
        }}
      />

      {/* ---------------------------------------------------------------- */}
      {/* Üyelikler                                                        */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'memberships' && (
        <Card
          title={t('membership.title')}
          actions={
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => {
                setFilterStudent(null)
                setFilterStatus('')
                setFilterPackage('')
                setPage(1)
              }}
            >
              {t('common.clearFilters')}
            </button>
          }
          bodyClassName="p-0"
        >
          <div className="grid gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-700 sm:grid-cols-3">
            <StudentPicker
              label={t('student.singular')}
              value={filterStudent}
              onChange={(student) => {
                setFilterStudent(student)
                setPage(1)
              }}
            />
            <Field label={t('common.status')}>
              <select
                className="select"
                value={filterStatus}
                onChange={(event) => {
                  setFilterStatus(event.target.value)
                  setPage(1)
                }}
              >
                <option value="">{t('common.all')}</option>
                {MEMBERSHIP_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`membership.statuses.${status}`)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('membership.package')}>
              <select
                className="select"
                value={filterPackage}
                onChange={(event) => {
                  setFilterPackage(event.target.value)
                  setPage(1)
                }}
              >
                <option value="">{t('common.all')}</option>
                {packages.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {membershipsQuery.isLoading ? (
            <LoadingState />
          ) : membershipsQuery.error ? (
            <ErrorState
              error={membershipsQuery.error}
              onRetry={() => void membershipsQuery.refetch()}
            />
          ) : (membershipsQuery.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              title={t('common.noResults')}
              description={t('student.noMembership')}
              icon={<CreditCard className="h-6 w-6" />}
            />
          ) : (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('student.singular')}</th>
                    <th>{t('membership.package')}</th>
                    <th className="hidden md:table-cell">
                      {t('membership.startDate')} – {t('membership.endDate')}
                    </th>
                    <th>{t('membership.remainingCredits')}</th>
                    <th className="hidden lg:table-cell">{t('membership.daysRemaining')}</th>
                    <th className="hidden lg:table-cell">{t('finance.amount')}</th>
                    <th>{t('common.status')}</th>
                    <th>{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(membershipsQuery.data?.items ?? []).map((membership) => (
                    <tr key={membership.id}>
                      <td className="whitespace-nowrap">{renderStudentCell(membership)}</td>
                      <td className="whitespace-nowrap">
                        <span className="text-sm">{membership.package_name ?? '—'}</span>
                        {membership.package_type && (
                          <p className="text-xs text-slate-400">
                            {t(`membership.types.${membership.package_type}`, membership.package_type)}
                          </p>
                        )}
                      </td>
                      <td className="hidden md:table-cell whitespace-nowrap text-xs">
                        {formatDate(membership.start_date)} – {formatDate(membership.end_date)}
                      </td>
                      <td>
                        <CreditsCell membership={membership} />
                      </td>
                      <td className="hidden lg:table-cell text-xs">
                        {membership.days_remaining !== null && membership.days_remaining !== undefined
                          ? formatNumber(membership.days_remaining)
                          : '—'}
                        {membership.is_expiring_soon && (
                          <Badge tone="warning" className="ml-2">
                            {t('membership.expiringSoon')}
                          </Badge>
                        )}
                      </td>
                      <td className="hidden lg:table-cell whitespace-nowrap text-xs">
                        {formatCurrency(membership.price_paid)}
                        {membership.discount_amount > 0 && (
                          <p className="text-xs text-emerald-600 dark:text-emerald-400">
                            {t('membership.discount')}: {formatCurrency(membership.discount_amount)}
                          </p>
                        )}
                      </td>
                      <td>
                        <StatusBadge
                          status={membership.status}
                          label={t(`membership.statuses.${membership.status}`)}
                        />
                      </td>
                      <td>{renderActions(membership)}</td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={membershipsQuery.data?.total ?? 0}
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

      {/* ---------------------------------------------------------------- */}
      {/* Paketler                                                         */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'packages' && (
        <>
          <div className="mb-4 flex justify-end">
            {canWrite && (
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={() => setPackageForm(emptyPackageForm())}
              >
                <Plus className="h-3.5 w-3.5" />
                {t('membership.newPackage')}
              </button>
            )}
          </div>

          {packagesQuery.isLoading ? (
            <LoadingState />
          ) : packagesQuery.error ? (
            <ErrorState error={packagesQuery.error} onRetry={() => void packagesQuery.refetch()} />
          ) : packages.length === 0 ? (
            <Card>
              <EmptyState
                title={t('common.noData')}
                description={t('membership.newPackage')}
                icon={<Layers className="h-6 w-6" />}
              />
            </Card>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {packages.map((item) => (
                <Card key={item.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: item.color }}
                        />
                        <h3 className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {item.name}
                        </h3>
                      </div>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {t(`membership.types.${item.package_type}`, item.package_type)}
                      </p>
                    </div>
                    <Badge tone={item.is_active ? 'success' : 'neutral'}>
                      {item.is_active ? t('common.active') : t('common.passive')}
                    </Badge>
                  </div>

                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <dt className="text-slate-500 dark:text-slate-400">
                        {t('membership.lessonCount')}
                      </dt>
                      <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-200">
                        {item.lesson_count !== null && item.lesson_count !== undefined
                          ? formatNumber(item.lesson_count)
                          : t('membership.unlimited')}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-500 dark:text-slate-400">
                        {t('membership.durationDays')}
                      </dt>
                      <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-200">
                        {item.duration_days !== null && item.duration_days !== undefined
                          ? formatNumber(item.duration_days)
                          : '—'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-500 dark:text-slate-400">{t('membership.price')}</dt>
                      <dd className="mt-0.5 font-semibold text-slate-900 dark:text-slate-100">
                        {formatCurrency(item.price)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-500 dark:text-slate-400">
                        {t('membership.title')}
                      </dt>
                      <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-200">
                        {formatNumber(item.active_membership_count)}
                      </dd>
                    </div>
                  </dl>

                  {item.description && (
                    <p className="mt-3 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
                      {item.description}
                    </p>
                  )}

                  {canWrite && (
                    <div className="mt-4 flex items-center gap-2 border-t border-slate-100 pt-3 dark:border-slate-700">
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        onClick={() => openEditPackage(item)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        {t('common.edit')}
                      </button>
                      {item.is_active && (
                        <button
                          type="button"
                          className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                          onClick={() => setPackageDeleteTarget(item)}
                        >
                          <Ban className="h-3.5 w-3.5" />
                          {t('common.passive')}
                        </button>
                      )}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Süresi dolacaklar                                                */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'expiring' && (
        <Card
          title={t('membership.expiring')}
          actions={
            <select
              className="select w-auto py-1 text-xs"
              value={expiringDays}
              onChange={(event) => setExpiringDays(Number(event.target.value))}
              aria-label={t('membership.daysRemaining')}
            >
              {EXPIRING_DAY_OPTIONS.map((days) => (
                <option key={days} value={days}>
                  {formatNumber(days)}
                </option>
              ))}
            </select>
          }
          bodyClassName="p-0"
        >
          {expiringQuery.isLoading ? (
            <LoadingState />
          ) : expiringQuery.error ? (
            <ErrorState error={expiringQuery.error} onRetry={() => void expiringQuery.refetch()} />
          ) : (expiringQuery.data?.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<Timer className="h-6 w-6" />} />
          ) : (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('student.singular')}</th>
                  <th>{t('membership.package')}</th>
                  <th>{t('membership.endDate')}</th>
                  <th>{t('membership.daysRemaining')}</th>
                  <th className="hidden md:table-cell">{t('membership.remainingCredits')}</th>
                  <th>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {(expiringQuery.data ?? []).map((membership) => (
                  <tr key={membership.id}>
                    <td className="whitespace-nowrap">{renderStudentCell(membership)}</td>
                    <td className="whitespace-nowrap text-sm">{membership.package_name ?? '—'}</td>
                    <td className="whitespace-nowrap text-xs">{formatDate(membership.end_date)}</td>
                    <td>
                      <Badge
                        tone={
                          (membership.days_remaining ?? 0) <= 3
                            ? 'danger'
                            : (membership.days_remaining ?? 0) <= 7
                              ? 'warning'
                              : 'neutral'
                        }
                      >
                        {membership.days_remaining !== null && membership.days_remaining !== undefined
                          ? formatNumber(membership.days_remaining)
                          : '—'}
                      </Badge>
                    </td>
                    <td className="hidden md:table-cell">
                      <CreditsCell membership={membership} />
                    </td>
                    <td>
                      {canWrite ? (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => openRenew(membership)}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          {t('membership.renew')}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </Card>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Ders hakkı azalanlar                                             */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'lowCredit' && (
        <Card
          title={t('membership.lowCredit')}
          actions={
            <select
              className="select w-auto py-1 text-xs"
              value={lowThreshold}
              onChange={(event) => setLowThreshold(Number(event.target.value))}
              aria-label={t('membership.remainingCredits')}
            >
              {LOW_CREDIT_OPTIONS.map((threshold) => (
                <option key={threshold} value={threshold}>
                  {formatNumber(threshold)}
                </option>
              ))}
            </select>
          }
          bodyClassName="p-0"
        >
          {lowCreditQuery.isLoading ? (
            <LoadingState />
          ) : lowCreditQuery.error ? (
            <ErrorState error={lowCreditQuery.error} onRetry={() => void lowCreditQuery.refetch()} />
          ) : (lowCreditQuery.data?.length ?? 0) === 0 ? (
            <EmptyState title={t('common.noData')} icon={<TrendingDown className="h-6 w-6" />} />
          ) : (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('student.singular')}</th>
                  <th>{t('membership.package')}</th>
                  <th>{t('membership.remainingCredits')}</th>
                  <th className="hidden md:table-cell">{t('membership.usedCredits')}</th>
                  <th className="hidden md:table-cell">{t('membership.endDate')}</th>
                  <th>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {(lowCreditQuery.data ?? []).map((membership) => (
                  <tr key={membership.id}>
                    <td className="whitespace-nowrap">{renderStudentCell(membership)}</td>
                    <td className="whitespace-nowrap text-sm">{membership.package_name ?? '—'}</td>
                    <td>
                      <Badge tone={(membership.remaining_credits ?? 0) <= 1 ? 'danger' : 'warning'}>
                        {formatNumber(membership.remaining_credits ?? 0)}
                      </Badge>
                    </td>
                    <td className="hidden md:table-cell text-xs">
                      {formatNumber(membership.used_credits)}
                    </td>
                    <td className="hidden md:table-cell text-xs">
                      {formatDate(membership.end_date)}
                    </td>
                    <td>
                      {canWrite ? (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => openRenew(membership)}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          {t('membership.renew')}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </Card>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Yeni üyelik modalı                                               */}
      {/* ---------------------------------------------------------------- */}
      <Modal
        open={membershipForm !== null}
        onClose={() => setMembershipForm(null)}
        title={t('membership.new')}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setMembershipForm(null)}
              disabled={createMembershipMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={submitMembership}
              disabled={
                createMembershipMutation.isPending ||
                !membershipForm?.student ||
                !membershipForm?.packageId
              }
            >
              {createMembershipMutation.isPending && <Spinner />}
              {t('common.save')}
            </button>
          </>
        }
      >
        {membershipForm && (
          <div className="grid gap-4 sm:grid-cols-2">
            <StudentPicker
              label={t('student.singular')}
              required
              value={membershipForm.student}
              onChange={(student) => setMembershipForm({ ...membershipForm, student })}
            />
            <Field label={t('membership.package')} required>
              <select
                className="select"
                value={membershipForm.packageId}
                onChange={(event) =>
                  setMembershipForm({ ...membershipForm, packageId: event.target.value })
                }
              >
                <option value="">{t('common.none')}</option>
                {packages
                  .filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · {formatCurrency(item.price)}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label={t('membership.startDate')}>
              <input
                type="date"
                className="input"
                value={membershipForm.startDate}
                onChange={(event) =>
                  setMembershipForm({ ...membershipForm, startDate: event.target.value })
                }
              />
            </Field>
            <Field label={t('membership.discount')}>
              <input
                type="number"
                min={0}
                step="0.01"
                className="input"
                value={membershipForm.discountAmount}
                onChange={(event) =>
                  setMembershipForm({ ...membershipForm, discountAmount: event.target.value })
                }
              />
            </Field>
            <Field label={t('membership.discountReason')} className="sm:col-span-2">
              <input
                type="text"
                className="input"
                value={membershipForm.discountReason}
                onChange={(event) =>
                  setMembershipForm({ ...membershipForm, discountReason: event.target.value })
                }
              />
            </Field>

            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
                checked={membershipForm.autoRenew}
                onChange={(event) =>
                  setMembershipForm({ ...membershipForm, autoRenew: event.target.checked })
                }
              />
              {t('membership.autoRenew')}
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
                checked={membershipForm.createPayment}
                onChange={(event) =>
                  setMembershipForm({ ...membershipForm, createPayment: event.target.checked })
                }
              />
              {t('membership.createPayment')}
            </label>

            {membershipForm.createPayment && (
              <>
                <Field label={t('finance.amount')} hint={t('common.optional')}>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    className="input"
                    value={membershipForm.paymentAmount}
                    onChange={(event) =>
                      setMembershipForm({ ...membershipForm, paymentAmount: event.target.value })
                    }
                  />
                </Field>
                <Field label={t('finance.method')}>
                  <select
                    className="select"
                    value={membershipForm.paymentMethod}
                    onChange={(event) =>
                      setMembershipForm({
                        ...membershipForm,
                        paymentMethod: event.target.value as PaymentMethod,
                      })
                    }
                  >
                    {PAYMENT_METHODS.map((method) => (
                      <option key={method} value={method}>
                        {t(`finance.methods.${method}`)}
                      </option>
                    ))}
                  </select>
                </Field>
              </>
            )}
          </div>
        )}
      </Modal>

      {/* ---------------------------------------------------------------- */}
      {/* Dondurma modalı                                                  */}
      {/* ---------------------------------------------------------------- */}
      <Modal
        open={freezeTarget !== null}
        onClose={() => setFreezeTarget(null)}
        title={t('membership.freeze')}
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setFreezeTarget(null)}
              disabled={freezeMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={submitFreeze}
              disabled={freezeMutation.isPending || freezeForm.endDate < freezeForm.startDate}
            >
              {freezeMutation.isPending && <Spinner />}
              {t('common.confirm')}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {freezeTarget?.student_name} · {freezeTarget?.package_name}
          </p>
          <Field label={t('membership.freezeStart')} required>
            <input
              type="date"
              className="input"
              value={freezeForm.startDate}
              onChange={(event) => setFreezeForm({ ...freezeForm, startDate: event.target.value })}
            />
          </Field>
          <Field
            label={t('membership.freezeEnd')}
            required
            error={
              freezeForm.endDate < freezeForm.startDate ? t('common.required') : undefined
            }
          >
            <input
              type="date"
              className="input"
              value={freezeForm.endDate}
              onChange={(event) => setFreezeForm({ ...freezeForm, endDate: event.target.value })}
            />
          </Field>
          <Field label={t('membership.freezeReason')}>
            <textarea
              className="textarea"
              value={freezeForm.reason}
              onChange={(event) => setFreezeForm({ ...freezeForm, reason: event.target.value })}
            />
          </Field>
        </div>
      </Modal>

      {/* ---------------------------------------------------------------- */}
      {/* Dondurmayı kaldır                                                */}
      {/* ---------------------------------------------------------------- */}
      <ConfirmDialog
        open={unfreezeTarget !== null}
        onClose={() => setUnfreezeTarget(null)}
        onConfirm={() => unfreezeTarget && unfreezeMutation.mutate(unfreezeTarget.id)}
        title={t('membership.unfreeze')}
        message={`${unfreezeTarget?.student_name ?? ''} · ${unfreezeTarget?.package_name ?? ''}`}
        confirmLabel={t('common.confirm')}
        tone="primary"
        loading={unfreezeMutation.isPending}
      />

      {/* ---------------------------------------------------------------- */}
      {/* Yenileme modalı                                                  */}
      {/* ---------------------------------------------------------------- */}
      <Modal
        open={renewTarget !== null}
        onClose={() => setRenewTarget(null)}
        title={t('membership.renew')}
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setRenewTarget(null)}
              disabled={renewMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={submitRenew}
              disabled={renewMutation.isPending}
            >
              {renewMutation.isPending && <Spinner />}
              {t('common.confirm')}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {renewTarget?.student_name} · {renewTarget?.package_name}
          </p>
          <Field label={t('membership.package')}>
            <select
              className="select"
              value={renewForm.packageId}
              onChange={(event) => setRenewForm({ ...renewForm, packageId: event.target.value })}
            >
              {packages
                .filter((item) => item.is_active || item.id.toString() === renewForm.packageId)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {formatCurrency(item.price)}
                  </option>
                ))}
            </select>
          </Field>
          <Field label={t('membership.startDate')} hint={t('common.optional')}>
            <input
              type="date"
              className="input"
              value={renewForm.startDate}
              onChange={(event) => setRenewForm({ ...renewForm, startDate: event.target.value })}
            />
          </Field>
          <Field label={t('membership.discount')}>
            <input
              type="number"
              min={0}
              step="0.01"
              className="input"
              value={renewForm.discountAmount}
              onChange={(event) =>
                setRenewForm({ ...renewForm, discountAmount: event.target.value })
              }
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
              checked={renewForm.createPayment}
              onChange={(event) =>
                setRenewForm({ ...renewForm, createPayment: event.target.checked })
              }
            />
            {t('membership.createPayment')}
          </label>
          {renewForm.createPayment && (
            <Field label={t('finance.method')}>
              <select
                className="select"
                value={renewForm.paymentMethod}
                onChange={(event) =>
                  setRenewForm({ ...renewForm, paymentMethod: event.target.value as PaymentMethod })
                }
              >
                {PAYMENT_METHODS.map((method) => (
                  <option key={method} value={method}>
                    {t(`finance.methods.${method}`)}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </div>
      </Modal>

      {/* ---------------------------------------------------------------- */}
      {/* İptal modalı                                                     */}
      {/* ---------------------------------------------------------------- */}
      <Modal
        open={cancelTarget !== null}
        onClose={() => setCancelTarget(null)}
        title={t('membership.cancel')}
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setCancelTarget(null)}
              disabled={cancelMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={() =>
                cancelTarget &&
                cancelMutation.mutate({ id: cancelTarget.id, reason: cancelReason.trim() })
              }
              disabled={cancelMutation.isPending || cancelReason.trim().length < 3}
            >
              {cancelMutation.isPending && <Spinner />}
              {t('common.confirm')}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {cancelTarget?.student_name} · {cancelTarget?.package_name}
          </p>
          <Field
            label={t('lesson.cancelReason')}
            required
            error={cancelReason.trim().length < 3 ? t('common.required') : undefined}
          >
            <textarea
              className="textarea"
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
            />
          </Field>
        </div>
      </Modal>

      {/* ---------------------------------------------------------------- */}
      {/* Paket formu                                                      */}
      {/* ---------------------------------------------------------------- */}
      <Modal
        open={packageForm !== null}
        onClose={() => setPackageForm(null)}
        title={packageForm?.id === null ? t('membership.newPackage') : t('common.edit')}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setPackageForm(null)}
              disabled={savePackageMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={submitPackage}
              disabled={
                savePackageMutation.isPending ||
                !packageForm ||
                packageForm.name.trim() === '' ||
                packageForm.price.trim() === ''
              }
            >
              {savePackageMutation.isPending && <Spinner />}
              {t('common.save')}
            </button>
          </>
        }
      >
        {packageForm && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('common.name')} required>
              <input
                type="text"
                className="input"
                value={packageForm.name}
                onChange={(event) => setPackageForm({ ...packageForm, name: event.target.value })}
              />
            </Field>
            <Field label={`${t('common.name')} (EN)`}>
              <input
                type="text"
                className="input"
                value={packageForm.nameEn}
                onChange={(event) => setPackageForm({ ...packageForm, nameEn: event.target.value })}
              />
            </Field>
            <Field label={t('membership.packageType')} required>
              <select
                className="select"
                value={packageForm.packageType}
                onChange={(event) =>
                  setPackageForm({ ...packageForm, packageType: event.target.value })
                }
              >
                {PACKAGE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`membership.types.${type}`)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('membership.price')} required>
              <input
                type="number"
                min={0}
                step="0.01"
                className="input"
                value={packageForm.price}
                onChange={(event) => setPackageForm({ ...packageForm, price: event.target.value })}
              />
            </Field>
            <Field label={t('membership.lessonCount')} hint={t('membership.unlimited')}>
              <input
                type="number"
                min={1}
                className="input"
                value={packageForm.lessonCount}
                onChange={(event) =>
                  setPackageForm({ ...packageForm, lessonCount: event.target.value })
                }
              />
            </Field>
            <Field label={t('membership.durationDays')} hint={t('common.optional')}>
              <input
                type="number"
                min={1}
                className="input"
                value={packageForm.durationDays}
                onChange={(event) =>
                  setPackageForm({ ...packageForm, durationDays: event.target.value })
                }
              />
            </Field>
            <Field label={t('membership.maxFreezeDays')}>
              <input
                type="number"
                min={0}
                className="input"
                value={packageForm.maxFreezeDays}
                onChange={(event) =>
                  setPackageForm({ ...packageForm, maxFreezeDays: event.target.value })
                }
              />
            </Field>
            <Field label={t('lesson.color')}>
              <input
                type="color"
                className="input h-10 p-1"
                value={packageForm.color}
                onChange={(event) => setPackageForm({ ...packageForm, color: event.target.value })}
              />
            </Field>
            <Field label={t('common.description')} className="sm:col-span-2">
              <textarea
                className="textarea"
                value={packageForm.description}
                onChange={(event) =>
                  setPackageForm({ ...packageForm, description: event.target.value })
                }
              />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
                checked={packageForm.isActive}
                onChange={(event) =>
                  setPackageForm({ ...packageForm, isActive: event.target.checked })
                }
              />
              {t('common.active')}
            </label>
          </div>
        )}
      </Modal>

      {/* ---------------------------------------------------------------- */}
      {/* Paketi pasife al                                                 */}
      {/* ---------------------------------------------------------------- */}
      <ConfirmDialog
        open={packageDeleteTarget !== null}
        onClose={() => setPackageDeleteTarget(null)}
        onConfirm={() =>
          packageDeleteTarget && deactivatePackageMutation.mutate(packageDeleteTarget.id)
        }
        title={t('common.passive')}
        message={packageDeleteTarget?.name ?? ''}
        confirmLabel={t('common.confirm')}
        loading={deactivatePackageMutation.isPending}
      />
    </>
  )
}
