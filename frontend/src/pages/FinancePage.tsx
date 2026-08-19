/** Finans merkezi: tahsilat, fatura, bekleyen alacak, gider ve indirim yönetimi. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  Ban,
  CreditCard,
  FileText,
  Pencil,
  Percent,
  PiggyBank,
  Plus,
  Receipt,
  Trash2,
  TrendingDown,
  TrendingUp,
  Undo2,
  Wallet,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
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
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  Pagination,
  StatCard,
  StatusBadge,
  TableWrapper,
  Tabs,
} from '@/components/ui'
import { del, get, patch, post } from '@/lib/api'
import {
  formatCompact,
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
  toISODate,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  Expense,
  FinanceSummary,
  Invoice,
  Message,
  Page,
  Payment,
  PaymentMethod,
  PaymentStatus,
  Student,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler ve yerel tipler (backend şemalarıyla eşleşir)
// ---------------------------------------------------------------------------
const CHART_COLORS = ['#0ea5e9', '#38bdf8', '#6366f1', '#8b5cf6', '#f59e0b', '#10b981', '#f43f5e']
const PAYMENT_METHODS: PaymentMethod[] = ['cash', 'card', 'transfer', 'online', 'other']
const PAYMENT_STATUSES: PaymentStatus[] = [
  'paid',
  'pending',
  'partial',
  'overdue',
  'refunded',
  'cancelled',
]
const EXPENSE_CATEGORIES = [
  'salary',
  'rent',
  'utilities',
  'chemicals',
  'maintenance',
  'equipment',
  'marketing',
  'tax',
  'insurance',
  'other',
]
const AGING_BUCKETS: Array<{ key: string; labelKey: string }> = [
  { key: 'current', labelKey: 'finance.agingCurrent' },
  { key: '1_30', labelKey: 'finance.aging1_30' },
  { key: '31_60', labelKey: 'finance.aging31_60' },
  { key: '60_plus', labelKey: 'finance.aging60plus' },
]

type FinanceTab = 'payments' | 'invoices' | 'outstanding' | 'expenses' | 'discounts'

interface StudentOption {
  id: number
  full_name: string
}

interface OutstandingItem {
  invoice_id: number
  invoice_number: string
  student_id?: number | null
  student_name?: string | null
  due_date: string
  balance: number
  days_overdue: number
}

interface OutstandingResponse {
  total_outstanding: number
  aging: Record<string, number>
  count: number
  items: OutstandingItem[]
}

interface Discount {
  id: number
  code: string
  name: string
  description?: string | null
  percentage?: number | null
  fixed_amount?: number | null
  valid_from: string
  valid_until: string
  max_uses?: number | null
  is_active: boolean
  used_count: number
  is_valid_now: boolean
}

// ---------------------------------------------------------------------------
// Yardımcılar
// ---------------------------------------------------------------------------
function firstDayOfMonth(): string {
  const now = new Date()
  return toISODate(new Date(now.getFullYear(), now.getMonth(), 1))
}

/** Boş metinleri null'a çevirir (backend opsiyonel alanları için) */
function orNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function toAmount(value: string): number {
  const parsed = Number(value.replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : 0
}

// ---------------------------------------------------------------------------
// Öğrenci seçici (arama + öneri listesi)
// ---------------------------------------------------------------------------
function StudentPicker({
  value,
  onChange,
}: {
  value: StudentOption | null
  onChange: (student: StudentOption | null) => void
}) {
  const { t } = useTranslation()
  const [term, setTerm] = useState('')
  const [debounced, setDebounced] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(term), 300)
    return () => clearTimeout(timer)
  }, [term])

  const { data, isFetching } = useQuery({
    queryKey: ['students', 'picker', debounced],
    queryFn: () =>
      get<Page<Student>>('/students', {
        q: debounced || undefined,
        page: 1,
        page_size: 8,
      }),
    enabled: open,
  })

  if (value) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 dark:border-slate-600 dark:bg-slate-800">
        <span className="truncate text-sm text-slate-800 dark:text-slate-100">
          {value.full_name}
        </span>
        <button
          type="button"
          className="btn-ghost btn-sm"
          onClick={() => onChange(null)}
          aria-label={t('common.clearFilters')}
          title={t('common.clearFilters')}
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
        placeholder={t('common.searchPlaceholder')}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
          setTerm(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {open && (
        <div className="absolute z-30 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-panel dark:border-slate-700 dark:bg-surface-dark-alt">
          {isFetching && (
            <p className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
              {t('common.loading')}
            </p>
          )}
          {!isFetching && (data?.items.length ?? 0) === 0 && (
            <p className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
              {t('common.noResults')}
            </p>
          )}
          {data?.items.map((student) => (
            <button
              key={student.id}
              type="button"
              className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
              onClick={() => {
                onChange({ id: student.id, full_name: student.full_name })
                setOpen(false)
                setTerm('')
              }}
            >
              <span className="text-slate-800 dark:text-slate-100">{student.full_name}</span>
              <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
                {student.student_number}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Form başlangıç durumları
// ---------------------------------------------------------------------------
function emptyPaymentForm() {
  return {
    student: null as StudentOption | null,
    invoiceId: null as number | null,
    amount: '',
    method: 'cash' as PaymentMethod,
    paymentDate: toISODate(new Date()),
    reference: '',
    description: '',
  }
}

function emptyInvoiceForm() {
  return {
    student: null as StudentOption | null,
    issueDate: toISODate(new Date()),
    dueDate: toISODate(new Date()),
    subtotal: '',
    discountAmount: '0',
    taxAmount: '0',
    description: '',
  }
}

function emptyExpenseForm() {
  return {
    id: null as number | null,
    title: '',
    category: 'other',
    amount: '',
    expenseDate: toISODate(new Date()),
    method: 'transfer' as PaymentMethod,
    vendor: '',
    invoiceReference: '',
    description: '',
    isRecurring: false,
  }
}

function emptyDiscountForm() {
  return {
    code: '',
    name: '',
    description: '',
    percentage: '',
    fixedAmount: '',
    validFrom: toISODate(new Date()),
    validUntil: toISODate(new Date()),
    maxUses: '',
    isActive: true,
  }
}

// ---------------------------------------------------------------------------
export default function FinancePage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const canWrite = can('finance:write')
  const canDelete = can('finance:delete')

  const [tab, setTab] = useState<FinanceTab>('payments')
  const [range, setRange] = useState(() => ({
    from: firstDayOfMonth(),
    to: toISODate(new Date()),
  }))

  // Tahsilat filtreleri
  const [paymentMethod, setPaymentMethod] = useState('')
  const [paymentStatus, setPaymentStatus] = useState('')
  const [paymentStudent, setPaymentStudent] = useState<StudentOption | null>(null)
  const [paymentPage, setPaymentPage] = useState(1)
  const [paymentPageSize, setPaymentPageSize] = useState(25)

  // Fatura filtreleri
  const [invoiceStatus, setInvoiceStatus] = useState('')
  const [invoiceOverdueOnly, setInvoiceOverdueOnly] = useState(false)
  const [invoicePage, setInvoicePage] = useState(1)

  // Gider filtreleri
  const [expenseCategory, setExpenseCategory] = useState('')
  const [expensePage, setExpensePage] = useState(1)

  // İndirim filtresi
  const [discountActiveOnly, setDiscountActiveOnly] = useState(false)

  // Modal durumları
  const [paymentForm, setPaymentForm] = useState(emptyPaymentForm)
  const [paymentModalOpen, setPaymentModalOpen] = useState(false)
  const [refundTarget, setRefundTarget] = useState<Payment | null>(null)
  const [refundAmount, setRefundAmount] = useState('')
  const [refundReason, setRefundReason] = useState('')
  const [cancelTarget, setCancelTarget] = useState<Payment | null>(null)
  const [cancelReason, setCancelReason] = useState('')

  const [invoiceForm, setInvoiceForm] = useState(emptyInvoiceForm)
  const [invoiceModalOpen, setInvoiceModalOpen] = useState(false)

  const [expenseForm, setExpenseForm] = useState(emptyExpenseForm)
  const [expenseModalOpen, setExpenseModalOpen] = useState(false)
  const [expenseToDelete, setExpenseToDelete] = useState<Expense | null>(null)

  const [discountForm, setDiscountForm] = useState(emptyDiscountForm)
  const [discountModalOpen, setDiscountModalOpen] = useState(false)

  // -------------------------------------------------------------------------
  // Sorgular
  // -------------------------------------------------------------------------
  const summaryQuery = useQuery({
    queryKey: ['finance', 'summary', range.from, range.to],
    queryFn: () =>
      get<FinanceSummary>('/finance/summary', {
        date_from: range.from || undefined,
        date_to: range.to || undefined,
      }),
  })

  const paymentsQuery = useQuery({
    queryKey: [
      'finance',
      'payments',
      range.from,
      range.to,
      paymentMethod,
      paymentStatus,
      paymentStudent?.id ?? null,
      paymentPage,
      paymentPageSize,
    ],
    queryFn: () =>
      get<Page<Payment>>('/finance/payments', {
        date_from: range.from || undefined,
        date_to: range.to || undefined,
        method: paymentMethod || undefined,
        status: paymentStatus || undefined,
        student_id: paymentStudent?.id ?? undefined,
        page: paymentPage,
        page_size: paymentPageSize,
      }),
    enabled: tab === 'payments',
  })

  const invoicesQuery = useQuery({
    queryKey: ['finance', 'invoices', invoiceStatus, invoiceOverdueOnly, invoicePage],
    queryFn: () =>
      get<Page<Invoice>>('/finance/invoices', {
        status: invoiceStatus || undefined,
        overdue_only: invoiceOverdueOnly || undefined,
        page: invoicePage,
        page_size: 25,
      }),
    enabled: tab === 'invoices',
  })

  const outstandingQuery = useQuery({
    queryKey: ['finance', 'outstanding'],
    queryFn: () => get<OutstandingResponse>('/finance/outstanding'),
    enabled: tab === 'outstanding',
  })

  const expensesQuery = useQuery({
    queryKey: ['finance', 'expenses', range.from, range.to, expenseCategory, expensePage],
    queryFn: () =>
      get<Page<Expense>>('/finance/expenses', {
        date_from: range.from || undefined,
        date_to: range.to || undefined,
        category: expenseCategory || undefined,
        page: expensePage,
        page_size: 25,
      }),
    enabled: tab === 'expenses',
  })

  const discountsQuery = useQuery({
    queryKey: ['finance', 'discounts', discountActiveOnly],
    queryFn: () => get<Discount[]>('/finance/discounts', { active_only: discountActiveOnly }),
    enabled: tab === 'discounts',
  })

  // Kapanış (closure) içinde daraltmanın korunması için sabitlenmiş veri
  const outstanding = outstandingQuery.data

  // -------------------------------------------------------------------------
  // Mutasyonlar
  // -------------------------------------------------------------------------
  function invalidateFinance() {
    void queryClient.invalidateQueries({ queryKey: ['finance'] })
  }

  const createPayment = useMutation({
    mutationFn: () =>
      post<Payment>('/finance/payments', {
        student_id: paymentForm.student?.id ?? null,
        invoice_id: paymentForm.invoiceId,
        amount: toAmount(paymentForm.amount),
        currency: summaryQuery.data?.currency ?? 'TRY',
        method: paymentForm.method,
        payment_date: paymentForm.paymentDate || null,
        reference: orNull(paymentForm.reference),
        description: orNull(paymentForm.description),
      }),
    onSuccess: () => {
      invalidateFinance()
      setPaymentModalOpen(false)
      setPaymentForm(emptyPaymentForm())
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const refundPayment = useMutation({
    mutationFn: () =>
      post<Payment>(`/finance/payments/${refundTarget?.id}/refund`, {
        amount: toAmount(refundAmount),
        reason: refundReason.trim(),
      }),
    onSuccess: () => {
      invalidateFinance()
      setRefundTarget(null)
      setRefundAmount('')
      setRefundReason('')
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const cancelPayment = useMutation({
    mutationFn: () =>
      del<Message>(`/finance/payments/${cancelTarget?.id}`, { reason: cancelReason.trim() }),
    onSuccess: () => {
      invalidateFinance()
      setCancelTarget(null)
      setCancelReason('')
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const createInvoice = useMutation({
    mutationFn: () =>
      post<Invoice>('/finance/invoices', {
        student_id: invoiceForm.student?.id ?? null,
        issue_date: invoiceForm.issueDate || null,
        due_date: invoiceForm.dueDate,
        subtotal: toAmount(invoiceForm.subtotal),
        discount_amount: toAmount(invoiceForm.discountAmount),
        tax_amount: toAmount(invoiceForm.taxAmount),
        description: orNull(invoiceForm.description),
      }),
    onSuccess: () => {
      invalidateFinance()
      setInvoiceModalOpen(false)
      setInvoiceForm(emptyInvoiceForm())
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const saveExpense = useMutation({
    mutationFn: () => {
      const body = {
        title: expenseForm.title.trim(),
        category: expenseForm.category,
        amount: toAmount(expenseForm.amount),
        expense_date: expenseForm.expenseDate || null,
        method: expenseForm.method,
        vendor: orNull(expenseForm.vendor),
        invoice_reference: orNull(expenseForm.invoiceReference),
        description: orNull(expenseForm.description),
        is_recurring: expenseForm.isRecurring,
      }
      return expenseForm.id
        ? patch<Expense>(`/finance/expenses/${expenseForm.id}`, body)
        : post<Expense>('/finance/expenses', { ...body, currency: summaryQuery.data?.currency ?? 'TRY' })
    },
    onSuccess: () => {
      invalidateFinance()
      setExpenseModalOpen(false)
      setExpenseForm(emptyExpenseForm())
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const deleteExpense = useMutation({
    mutationFn: () => del<Message>(`/finance/expenses/${expenseToDelete?.id}`),
    onSuccess: () => {
      invalidateFinance()
      setExpenseToDelete(null)
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const createDiscount = useMutation({
    mutationFn: () =>
      post<Discount>('/finance/discounts', {
        code: discountForm.code.trim(),
        name: discountForm.name.trim(),
        description: orNull(discountForm.description),
        percentage: discountForm.percentage ? toAmount(discountForm.percentage) : null,
        fixed_amount: discountForm.fixedAmount ? toAmount(discountForm.fixedAmount) : null,
        valid_from: discountForm.validFrom,
        valid_until: discountForm.validUntil,
        max_uses: discountForm.maxUses ? Math.trunc(toAmount(discountForm.maxUses)) : null,
        is_active: discountForm.isActive,
      }),
    onSuccess: () => {
      invalidateFinance()
      setDiscountModalOpen(false)
      setDiscountForm(emptyDiscountForm())
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  // -------------------------------------------------------------------------
  // Grafik verileri
  // -------------------------------------------------------------------------
  const summary = summaryQuery.data

  const methodData = useMemo(
    () =>
      Object.entries(summary?.income_by_method ?? {})
        .map(([key, value]) => ({ name: t(`finance.methods.${key}`, key), value }))
        .filter((item) => item.value > 0),
    [summary, t],
  )

  const categoryData = useMemo(
    () =>
      Object.entries(summary?.expense_by_category ?? {})
        .map(([key, value]) => ({ name: t(`finance.categories.${key}`, key), value }))
        .filter((item) => item.value > 0)
        .sort((a, b) => b.value - a.value),
    [summary, t],
  )

  // -------------------------------------------------------------------------
  // Yardımcı arayüz parçaları
  // -------------------------------------------------------------------------
  function openPaymentForInvoice(invoice: Invoice) {
    setPaymentForm({
      ...emptyPaymentForm(),
      student:
        invoice.student_id && invoice.student_name
          ? { id: invoice.student_id, full_name: invoice.student_name }
          : null,
      invoiceId: invoice.id,
      amount: String(invoice.balance ?? 0),
      description: invoice.invoice_number,
    })
    setPaymentModalOpen(true)
  }

  const paymentFormValid = toAmount(paymentForm.amount) > 0
  const invoiceFormValid = toAmount(invoiceForm.subtotal) >= 0 && invoiceForm.dueDate.length > 0
  const expenseFormValid = expenseForm.title.trim().length > 0 && toAmount(expenseForm.amount) > 0
  const discountFormValid =
    discountForm.code.trim().length >= 2 &&
    discountForm.name.trim().length > 0 &&
    (discountForm.percentage !== '' || discountForm.fixedAmount !== '') &&
    discountForm.validFrom.length > 0 &&
    discountForm.validUntil.length > 0
  const refundFormValid = toAmount(refundAmount) > 0 && refundReason.trim().length >= 3

  const tabs = [
    { id: 'payments', label: t('finance.payments'), icon: <CreditCard className="h-4 w-4" /> },
    { id: 'invoices', label: t('finance.invoices'), icon: <FileText className="h-4 w-4" /> },
    {
      id: 'outstanding',
      label: t('finance.outstanding'),
      icon: <AlertTriangle className="h-4 w-4" />,
      badge: summary?.overdue_count,
    },
    { id: 'expenses', label: t('finance.expenses'), icon: <Receipt className="h-4 w-4" /> },
    { id: 'discounts', label: t('finance.discounts'), icon: <Percent className="h-4 w-4" /> },
  ]

  return (
    <>
      <PageHeader
        title={t('finance.title')}
        subtitle={
          summary
            ? `${formatDate(summary.period_start)} – ${formatDate(summary.period_end)}`
            : undefined
        }
        icon={<Wallet className="h-5 w-5" />}
        actions={
          <div className="flex flex-wrap items-end gap-2">
            <Field label={t('lesson.start')} className="w-40">
              <input
                type="date"
                className="input py-1.5"
                value={range.from}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setRange((current) => ({ ...current, from: event.target.value }))
                }
              />
            </Field>
            <Field label={t('lesson.end')} className="w-40">
              <input
                type="date"
                className="input py-1.5"
                value={range.to}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setRange((current) => ({ ...current, to: event.target.value }))
                }
              />
            </Field>
            <button
              type="button"
              className="btn-secondary btn-sm mb-0.5"
              onClick={() => setRange({ from: firstDayOfMonth(), to: toISODate(new Date()) })}
            >
              {t('common.thisMonth')}
            </button>
          </div>
        }
      />

      {/* Özet göstergeler */}
      {summaryQuery.isLoading && <LoadingState />}
      {summaryQuery.error && (
        <ErrorState error={summaryQuery.error} onRetry={() => void summaryQuery.refetch()} />
      )}

      {summary && (
        <>
          <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label={t('finance.totalIncome')}
              value={formatCurrency(summary.total_income)}
              hint={`${t('finance.revenuePerStudent')}: ${formatCurrency(summary.revenue_per_student)}`}
              icon={<TrendingUp className="h-5 w-5" />}
              tone="success"
            />
            <StatCard
              label={t('finance.totalExpense')}
              value={formatCurrency(summary.total_expense)}
              icon={<TrendingDown className="h-5 w-5" />}
              tone="warning"
            />
            <StatCard
              label={t('finance.netIncome')}
              value={formatCurrency(summary.net_income)}
              icon={<PiggyBank className="h-5 w-5" />}
              tone={summary.net_income >= 0 ? 'success' : 'danger'}
            />
            <StatCard
              label={t('finance.collectionRate')}
              value={formatPercent(summary.collection_rate)}
              hint={`${t('student.singular')}: ${formatNumber(summary.active_student_count)}`}
              icon={<Percent className="h-5 w-5" />}
              tone={summary.collection_rate >= 90 ? 'success' : 'warning'}
            />
          </div>

          <div className="mb-6 grid gap-3 sm:grid-cols-2">
            <StatCard
              label={t('finance.outstanding')}
              value={formatCurrency(summary.outstanding_total)}
              icon={<FileText className="h-5 w-5" />}
              tone={summary.outstanding_total > 0 ? 'warning' : 'neutral'}
              onClick={() => setTab('outstanding')}
            />
            <StatCard
              label={t('finance.statuses.overdue')}
              value={formatCurrency(summary.overdue_total)}
              hint={`${formatNumber(summary.overdue_count)} ${t('finance.invoices').toLowerCase()}`}
              icon={<AlertTriangle className="h-5 w-5" />}
              tone={summary.overdue_count > 0 ? 'danger' : 'neutral'}
              onClick={() => setTab('outstanding')}
            />
          </div>

          {/* Grafikler */}
          <div className="mb-6 grid gap-4 lg:grid-cols-2">
            <Card title={t('finance.monthlyTrend')} className="lg:col-span-2">
              {summary.monthly_series.length === 0 ? (
                <EmptyState title={t('common.noData')} />
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={summary.monthly_series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis
                      tick={{ fontSize: 10 }}
                      width={56}
                      tickFormatter={(value: number) => formatCompact(value)}
                    />
                    <Tooltip
                      formatter={(value: number, name: string) => [formatCurrency(value), name]}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar
                      dataKey="income"
                      name={t('finance.totalIncome')}
                      fill="#10b981"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="expense"
                      name={t('finance.totalExpense')}
                      fill="#f43f5e"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="net"
                      name={t('finance.netIncome')}
                      fill="#0ea5e9"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card title={t('finance.incomeByMethod')}>
              {methodData.length === 0 ? (
                <EmptyState title={t('common.noData')} />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={methodData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={50}
                      outerRadius={90}
                      paddingAngle={2}
                    >
                      {methodData.map((_, index) => (
                        <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number, name: string) => [formatCurrency(value), name]}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card title={t('finance.expenseByCategory')}>
              {categoryData.length === 0 ? (
                <EmptyState title={t('common.noData')} />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={categoryData} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(value: number) => formatCompact(value)}
                    />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={110} />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Bar dataKey="value" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
        </>
      )}

      <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as FinanceTab)} />

      {/* ------------------------------------------------------------------ */}
      {/* Tahsilatlar */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'payments' && (
        <Card
          title={t('finance.payments')}
          bodyClassName="p-0"
          actions={
            canWrite && (
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={() => {
                  setPaymentForm(emptyPaymentForm())
                  setPaymentModalOpen(true)
                }}
              >
                <Plus className="h-4 w-4" />
                {t('finance.newPayment')}
              </button>
            )
          }
        >
          <div className="grid gap-3 border-b border-slate-200 p-4 dark:border-slate-700 sm:grid-cols-2 lg:grid-cols-4">
            <Field label={t('student.singular')}>
              <StudentPicker
                value={paymentStudent}
                onChange={(student) => {
                  setPaymentStudent(student)
                  setPaymentPage(1)
                }}
              />
            </Field>
            <Field label={t('finance.method')}>
              <select
                className="select"
                value={paymentMethod}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                  setPaymentMethod(event.target.value)
                  setPaymentPage(1)
                }}
              >
                <option value="">{t('common.all')}</option>
                {PAYMENT_METHODS.map((method) => (
                  <option key={method} value={method}>
                    {t(`finance.methods.${method}`)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('common.status')}>
              <select
                className="select"
                value={paymentStatus}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                  setPaymentStatus(event.target.value)
                  setPaymentPage(1)
                }}
              >
                <option value="">{t('common.all')}</option>
                {PAYMENT_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`finance.statuses.${status}`)}
                  </option>
                ))}
              </select>
            </Field>
            <div className="flex items-end">
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => {
                  setPaymentMethod('')
                  setPaymentStatus('')
                  setPaymentStudent(null)
                  setPaymentPage(1)
                }}
              >
                {t('common.clearFilters')}
              </button>
            </div>
          </div>

          {paymentsQuery.isLoading && <LoadingState />}
          {paymentsQuery.error && (
            <ErrorState error={paymentsQuery.error} onRetry={() => void paymentsQuery.refetch()} />
          )}
          {paymentsQuery.data && paymentsQuery.data.items.length === 0 && (
            <EmptyState title={t('common.noData')} icon={<CreditCard className="h-6 w-6" />} />
          )}
          {paymentsQuery.data && paymentsQuery.data.items.length > 0 && (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('finance.receiptNumber')}</th>
                    <th>{t('student.singular')}</th>
                    <th>{t('finance.amount')}</th>
                    <th className="hidden md:table-cell">{t('finance.refund')}</th>
                    <th className="hidden lg:table-cell">{t('finance.method')}</th>
                    <th>{t('finance.paymentDate')}</th>
                    <th>{t('common.status')}</th>
                    <th className="text-right">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {paymentsQuery.data.items.map((payment) => (
                    <tr key={payment.id}>
                      <td className="whitespace-nowrap font-medium">{payment.receipt_number}</td>
                      <td>{payment.student_name ?? '—'}</td>
                      <td className="whitespace-nowrap font-medium">
                        {formatCurrency(payment.amount)}
                      </td>
                      <td className="hidden whitespace-nowrap md:table-cell">
                        {payment.refunded_amount > 0 ? (
                          <span className="text-rose-600 dark:text-rose-400">
                            {formatCurrency(payment.refunded_amount)}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="hidden lg:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {t(`finance.methods.${payment.method}`)}
                        {payment.reference ? ` · ${payment.reference}` : ''}
                      </td>
                      <td className="whitespace-nowrap">{formatDate(payment.payment_date)}</td>
                      <td>
                        <StatusBadge
                          status={payment.status}
                          label={t(`finance.statuses.${payment.status}`)}
                        />
                      </td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          {canWrite && payment.status !== 'cancelled' && (
                            <button
                              type="button"
                              className="btn-ghost btn-sm"
                              title={t('finance.refund')}
                              aria-label={t('finance.refund')}
                              onClick={() => {
                                setRefundTarget(payment)
                                setRefundAmount(
                                  String(Math.max(0, payment.amount - payment.refunded_amount)),
                                )
                                setRefundReason('')
                              }}
                            >
                              <Undo2 className="h-4 w-4" />
                            </button>
                          )}
                          {canDelete && payment.status !== 'cancelled' && (
                            <button
                              type="button"
                              className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                              title={t('common.cancel')}
                              aria-label={t('common.cancel')}
                              onClick={() => {
                                setCancelTarget(payment)
                                setCancelReason('')
                              }}
                            >
                              <Ban className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={paymentsQuery.data.page}
                pageSize={paymentsQuery.data.page_size}
                total={paymentsQuery.data.total}
                onPageChange={setPaymentPage}
                onPageSizeChange={(size) => {
                  setPaymentPageSize(size)
                  setPaymentPage(1)
                }}
              />
            </>
          )}
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Faturalar */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'invoices' && (
        <Card
          title={t('finance.invoices')}
          bodyClassName="p-0"
          actions={
            canWrite && (
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={() => {
                  setInvoiceForm(emptyInvoiceForm())
                  setInvoiceModalOpen(true)
                }}
              >
                <Plus className="h-4 w-4" />
                {t('finance.newInvoice')}
              </button>
            )
          }
        >
          <div className="grid gap-3 border-b border-slate-200 p-4 dark:border-slate-700 sm:grid-cols-3">
            <Field label={t('common.status')}>
              <select
                className="select"
                value={invoiceStatus}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                  setInvoiceStatus(event.target.value)
                  setInvoicePage(1)
                }}
              >
                <option value="">{t('common.all')}</option>
                {PAYMENT_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`finance.statuses.${status}`)}
                  </option>
                ))}
              </select>
            </Field>
            <div className="flex items-end">
              <label className="flex cursor-pointer items-center gap-2 pb-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-brand-600"
                  checked={invoiceOverdueOnly}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                    setInvoiceOverdueOnly(event.target.checked)
                    setInvoicePage(1)
                  }}
                />
                {t('finance.statuses.overdue')}
              </label>
            </div>
          </div>

          {invoicesQuery.isLoading && <LoadingState />}
          {invoicesQuery.error && (
            <ErrorState error={invoicesQuery.error} onRetry={() => void invoicesQuery.refetch()} />
          )}
          {invoicesQuery.data && invoicesQuery.data.items.length === 0 && (
            <EmptyState title={t('common.noData')} icon={<FileText className="h-6 w-6" />} />
          )}
          {invoicesQuery.data && invoicesQuery.data.items.length > 0 && (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('finance.invoiceNumber')}</th>
                    <th>{t('student.singular')}</th>
                    <th className="hidden md:table-cell">{t('finance.issueDate')}</th>
                    <th>{t('finance.dueDate')}</th>
                    <th>{t('finance.totalAmount')}</th>
                    <th className="hidden lg:table-cell">{t('finance.paidAmount')}</th>
                    <th>{t('finance.balance')}</th>
                    <th>{t('common.status')}</th>
                    <th className="text-right">{t('finance.daysOverdue')}</th>
                  </tr>
                </thead>
                <tbody>
                  {invoicesQuery.data.items.map((invoice) => (
                    <tr key={invoice.id}>
                      <td className="whitespace-nowrap font-medium">{invoice.invoice_number}</td>
                      <td>{invoice.student_name ?? '—'}</td>
                      <td className="hidden whitespace-nowrap md:table-cell">
                        {formatDate(invoice.issue_date)}
                      </td>
                      <td className="whitespace-nowrap">{formatDate(invoice.due_date)}</td>
                      <td className="whitespace-nowrap">{formatCurrency(invoice.total_amount)}</td>
                      <td className="hidden whitespace-nowrap lg:table-cell">
                        {formatCurrency(invoice.paid_amount)}
                      </td>
                      <td className="whitespace-nowrap font-medium">
                        {formatCurrency(invoice.balance)}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <StatusBadge
                            status={invoice.status}
                            label={t(`finance.statuses.${invoice.status}`)}
                          />
                          {canWrite && invoice.balance > 0 && (
                            <button
                              type="button"
                              className="btn-ghost btn-sm"
                              title={t('finance.newPayment')}
                              aria-label={t('finance.newPayment')}
                              onClick={() => openPaymentForInvoice(invoice)}
                            >
                              <CreditCard className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="text-right">
                        {invoice.is_overdue ? (
                          <Badge tone="danger">{formatNumber(invoice.days_overdue)}</Badge>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={invoicesQuery.data.page}
                pageSize={invoicesQuery.data.page_size}
                total={invoicesQuery.data.total}
                onPageChange={setInvoicePage}
              />
            </>
          )}
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Bekleyen alacaklar */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'outstanding' && (
        <>
          {outstandingQuery.isLoading && <LoadingState />}
          {outstandingQuery.error && (
            <ErrorState
              error={outstandingQuery.error}
              onRetry={() => void outstandingQuery.refetch()}
            />
          )}
          {outstanding && (
            <>
              <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <StatCard
                  label={t('finance.outstanding')}
                  value={formatCurrency(outstanding.total_outstanding)}
                  hint={`${formatNumber(outstanding.count)} ${t('finance.invoices').toLowerCase()}`}
                  icon={<FileText className="h-5 w-5" />}
                  tone="brand"
                />
                {AGING_BUCKETS.map((bucket, index) => (
                  <StatCard
                    key={bucket.key}
                    label={t(bucket.labelKey)}
                    value={formatCurrency(outstanding.aging[bucket.key] ?? 0)}
                    hint={t('finance.aging')}
                    tone={index === 0 ? 'neutral' : index === 1 ? 'warning' : 'danger'}
                  />
                ))}
              </div>

              <Card title={t('finance.outstanding')} bodyClassName="p-0">
                {outstanding.items.length === 0 ? (
                  <EmptyState
                    title={t('common.noData')}
                    description={t('dashboard.noAlerts')}
                    icon={<AlertTriangle className="h-6 w-6" />}
                  />
                ) : (
                  <TableWrapper>
                    <thead>
                      <tr>
                        <th>{t('finance.invoiceNumber')}</th>
                        <th>{t('student.singular')}</th>
                        <th>{t('finance.dueDate')}</th>
                        <th>{t('finance.balance')}</th>
                        <th className="text-right">{t('finance.daysOverdue')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {outstanding.items.map((item) => (
                        <tr key={item.invoice_id}>
                          <td className="whitespace-nowrap font-medium">{item.invoice_number}</td>
                          <td>{item.student_name ?? '—'}</td>
                          <td className="whitespace-nowrap">{formatDate(item.due_date)}</td>
                          <td className="whitespace-nowrap font-medium">
                            {formatCurrency(item.balance)}
                          </td>
                          <td className="text-right">
                            {item.days_overdue > 0 ? (
                              <Badge tone={item.days_overdue > 30 ? 'danger' : 'warning'}>
                                {formatNumber(item.days_overdue)}
                              </Badge>
                            ) : (
                              <Badge tone="neutral">{t('finance.agingCurrent')}</Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </TableWrapper>
                )}
              </Card>
            </>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Giderler */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'expenses' && (
        <Card
          title={t('finance.expenses')}
          bodyClassName="p-0"
          actions={
            canWrite && (
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={() => {
                  setExpenseForm(emptyExpenseForm())
                  setExpenseModalOpen(true)
                }}
              >
                <Plus className="h-4 w-4" />
                {t('finance.newExpense')}
              </button>
            )
          }
        >
          <div className="grid gap-3 border-b border-slate-200 p-4 dark:border-slate-700 sm:grid-cols-3">
            <Field label={t('finance.expenseByCategory')}>
              <select
                className="select"
                value={expenseCategory}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                  setExpenseCategory(event.target.value)
                  setExpensePage(1)
                }}
              >
                <option value="">{t('common.all')}</option>
                {EXPENSE_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {t(`finance.categories.${category}`)}
                  </option>
                ))}
              </select>
            </Field>
            <div className="flex items-end">
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => {
                  setExpenseCategory('')
                  setExpensePage(1)
                }}
              >
                {t('common.clearFilters')}
              </button>
            </div>
          </div>

          {expensesQuery.isLoading && <LoadingState />}
          {expensesQuery.error && (
            <ErrorState error={expensesQuery.error} onRetry={() => void expensesQuery.refetch()} />
          )}
          {expensesQuery.data && expensesQuery.data.items.length === 0 && (
            <EmptyState title={t('common.noData')} icon={<Receipt className="h-6 w-6" />} />
          )}
          {expensesQuery.data && expensesQuery.data.items.length > 0 && (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('common.name')}</th>
                    <th>{t('finance.expenseByCategory')}</th>
                    <th>{t('finance.amount')}</th>
                    <th>{t('common.date')}</th>
                    <th className="hidden md:table-cell">{t('finance.method')}</th>
                    <th className="hidden lg:table-cell">{t('finance.vendor')}</th>
                    <th className="text-right">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {expensesQuery.data.items.map((expense) => (
                    <tr key={expense.id}>
                      <td className="font-medium">
                        {expense.title}
                        {expense.is_recurring && (
                          <Badge tone="info" className="ml-2">
                            {t('finance.isRecurring')}
                          </Badge>
                        )}
                      </td>
                      <td>{t(`finance.categories.${expense.category}`, expense.category)}</td>
                      <td className="whitespace-nowrap font-medium">
                        {formatCurrency(expense.amount)}
                      </td>
                      <td className="whitespace-nowrap">{formatDate(expense.expense_date)}</td>
                      <td className="hidden md:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {t(`finance.methods.${expense.method}`)}
                      </td>
                      <td className="hidden lg:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {expense.vendor ?? '—'}
                      </td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          {canWrite && (
                            <button
                              type="button"
                              className="btn-ghost btn-sm"
                              title={t('common.edit')}
                              aria-label={t('common.edit')}
                              onClick={() => {
                                setExpenseForm({
                                  id: expense.id,
                                  title: expense.title,
                                  category: expense.category,
                                  amount: String(expense.amount),
                                  expenseDate: toISODate(expense.expense_date),
                                  method: expense.method,
                                  vendor: expense.vendor ?? '',
                                  invoiceReference: expense.invoice_reference ?? '',
                                  description: expense.description ?? '',
                                  isRecurring: expense.is_recurring,
                                })
                                setExpenseModalOpen(true)
                              }}
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                              title={t('common.delete')}
                              aria-label={t('common.delete')}
                              onClick={() => setExpenseToDelete(expense)}
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
              <Pagination
                page={expensesQuery.data.page}
                pageSize={expensesQuery.data.page_size}
                total={expensesQuery.data.total}
                onPageChange={setExpensePage}
              />
            </>
          )}
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* İndirimler */}
      {/* ------------------------------------------------------------------ */}
      {tab === 'discounts' && (
        <Card
          title={t('finance.discounts')}
          bodyClassName="p-0"
          actions={
            <div className="flex items-center gap-2">
              <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-brand-600"
                  checked={discountActiveOnly}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    setDiscountActiveOnly(event.target.checked)
                  }
                />
                {t('common.active')}
              </label>
              {canWrite && (
                <button
                  type="button"
                  className="btn-primary btn-sm"
                  onClick={() => {
                    setDiscountForm(emptyDiscountForm())
                    setDiscountModalOpen(true)
                  }}
                >
                  <Plus className="h-4 w-4" />
                  {t('common.new')}
                </button>
              )}
            </div>
          }
        >
          {discountsQuery.isLoading && <LoadingState />}
          {discountsQuery.error && (
            <ErrorState error={discountsQuery.error} onRetry={() => void discountsQuery.refetch()} />
          )}
          {discountsQuery.data && discountsQuery.data.length === 0 && (
            <EmptyState title={t('common.noData')} icon={<Percent className="h-6 w-6" />} />
          )}
          {discountsQuery.data && discountsQuery.data.length > 0 && (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('finance.reference')}</th>
                  <th>{t('common.name')}</th>
                  <th>{t('membership.discount')}</th>
                  <th>{t('membership.startDate')}</th>
                  <th>{t('membership.endDate')}</th>
                  <th>{t('membership.usedCredits')}</th>
                  <th className="text-right">{t('common.status')}</th>
                </tr>
              </thead>
              <tbody>
                {discountsQuery.data.map((discount) => (
                  <tr key={discount.id}>
                    <td className="whitespace-nowrap font-mono text-xs font-medium">
                      {discount.code}
                    </td>
                    <td>
                      {discount.name}
                      {discount.description && (
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {discount.description}
                        </p>
                      )}
                    </td>
                    <td className="whitespace-nowrap font-medium">
                      {discount.percentage !== null && discount.percentage !== undefined
                        ? formatPercent(discount.percentage)
                        : formatCurrency(discount.fixed_amount ?? 0)}
                    </td>
                    <td className="whitespace-nowrap">{formatDate(discount.valid_from)}</td>
                    <td className="whitespace-nowrap">{formatDate(discount.valid_until)}</td>
                    <td className="whitespace-nowrap">
                      {formatNumber(discount.used_count)}
                      {discount.max_uses ? ` / ${formatNumber(discount.max_uses)}` : ''}
                    </td>
                    <td className="text-right">
                      <StatusBadge
                        status={discount.is_valid_now ? 'active' : 'expired'}
                        label={
                          discount.is_valid_now ? t('common.active') : t('membership.statuses.expired')
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Yeni ödeme modalı */}
      {/* ------------------------------------------------------------------ */}
      <Modal
        open={paymentModalOpen}
        onClose={() => setPaymentModalOpen(false)}
        title={t('finance.newPayment')}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setPaymentModalOpen(false)}
              disabled={createPayment.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={!paymentFormValid || createPayment.isPending}
              onClick={() => createPayment.mutate()}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('student.singular')} className="sm:col-span-2">
            <StudentPicker
              value={paymentForm.student}
              onChange={(student) =>
                setPaymentForm((current) => ({ ...current, student }))
              }
            />
          </Field>
          <Field label={t('finance.amount')} required>
            <input
              type="number"
              min="0"
              step="0.01"
              className="input"
              value={paymentForm.amount}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setPaymentForm((current) => ({ ...current, amount: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.method')} required>
            <select
              className="select"
              value={paymentForm.method}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setPaymentForm((current) => ({
                  ...current,
                  method: event.target.value as PaymentMethod,
                }))
              }
            >
              {PAYMENT_METHODS.map((method) => (
                <option key={method} value={method}>
                  {t(`finance.methods.${method}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('finance.paymentDate')} required>
            <input
              type="date"
              className="input"
              value={paymentForm.paymentDate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setPaymentForm((current) => ({ ...current, paymentDate: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.reference')}>
            <input
              className="input"
              value={paymentForm.reference}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setPaymentForm((current) => ({ ...current, reference: event.target.value }))
              }
            />
          </Field>
          <Field label={t('common.description')} className="sm:col-span-2">
            <textarea
              className="textarea"
              value={paymentForm.description}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setPaymentForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </Field>
          {paymentForm.invoiceId !== null && (
            <div className="sm:col-span-2">
              <Alert tone="info" title={t('finance.invoiceNumber')}>
                {paymentForm.description}
              </Alert>
            </div>
          )}
        </div>
      </Modal>

      {/* İade modalı */}
      <Modal
        open={refundTarget !== null}
        onClose={() => setRefundTarget(null)}
        title={`${t('finance.refund')} · ${refundTarget?.receipt_number ?? ''}`}
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setRefundTarget(null)}
              disabled={refundPayment.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-danger"
              disabled={!refundFormValid || refundPayment.isPending}
              onClick={() => refundPayment.mutate()}
            >
              {t('finance.refund')}
            </button>
          </>
        }
      >
        <div className="grid gap-4">
          {refundTarget && (
            <Alert tone="warning" title={formatCurrency(refundTarget.amount)}>
              {t('finance.refundAmount')}:{' '}
              {formatCurrency(refundTarget.amount - refundTarget.refunded_amount)}
            </Alert>
          )}
          <Field label={t('finance.refundAmount')} required>
            <input
              type="number"
              min="0"
              step="0.01"
              className="input"
              value={refundAmount}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setRefundAmount(event.target.value)
              }
            />
          </Field>
          <Field label={t('finance.refundReason')} required hint={t('common.required')}>
            <textarea
              className="textarea"
              value={refundReason}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setRefundReason(event.target.value)
              }
            />
          </Field>
        </div>
      </Modal>

      {/* Ödeme iptal modalı */}
      <Modal
        open={cancelTarget !== null}
        onClose={() => setCancelTarget(null)}
        title={`${t('common.cancel')} · ${cancelTarget?.receipt_number ?? ''}`}
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setCancelTarget(null)}
              disabled={cancelPayment.isPending}
            >
              {t('common.close')}
            </button>
            <button
              type="button"
              className="btn-danger"
              disabled={cancelReason.trim().length < 3 || cancelPayment.isPending}
              onClick={() => cancelPayment.mutate()}
            >
              {t('common.confirm')}
            </button>
          </>
        }
      >
        <Field label={t('lesson.cancelReason')} required>
          <textarea
            className="textarea"
            value={cancelReason}
            onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
              setCancelReason(event.target.value)
            }
          />
        </Field>
      </Modal>

      {/* Yeni fatura modalı */}
      <Modal
        open={invoiceModalOpen}
        onClose={() => setInvoiceModalOpen(false)}
        title={t('finance.newInvoice')}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setInvoiceModalOpen(false)}
              disabled={createInvoice.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={!invoiceFormValid || createInvoice.isPending}
              onClick={() => createInvoice.mutate()}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('student.singular')} className="sm:col-span-2">
            <StudentPicker
              value={invoiceForm.student}
              onChange={(student) => setInvoiceForm((current) => ({ ...current, student }))}
            />
          </Field>
          <Field label={t('finance.issueDate')} required>
            <input
              type="date"
              className="input"
              value={invoiceForm.issueDate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setInvoiceForm((current) => ({ ...current, issueDate: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.dueDate')} required>
            <input
              type="date"
              className="input"
              value={invoiceForm.dueDate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setInvoiceForm((current) => ({ ...current, dueDate: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.subtotal')} required>
            <input
              type="number"
              min="0"
              step="0.01"
              className="input"
              value={invoiceForm.subtotal}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setInvoiceForm((current) => ({ ...current, subtotal: event.target.value }))
              }
            />
          </Field>
          <Field label={t('membership.discount')}>
            <input
              type="number"
              min="0"
              step="0.01"
              className="input"
              value={invoiceForm.discountAmount}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setInvoiceForm((current) => ({ ...current, discountAmount: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.tax')}>
            <input
              type="number"
              min="0"
              step="0.01"
              className="input"
              value={invoiceForm.taxAmount}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setInvoiceForm((current) => ({ ...current, taxAmount: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.totalAmount')} className="sm:col-span-1">
            <input
              className="input"
              readOnly
              value={formatCurrency(
                toAmount(invoiceForm.subtotal) -
                  toAmount(invoiceForm.discountAmount) +
                  toAmount(invoiceForm.taxAmount),
              )}
            />
          </Field>
          <Field label={t('common.description')} className="sm:col-span-2">
            <textarea
              className="textarea"
              value={invoiceForm.description}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setInvoiceForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </Field>
        </div>
      </Modal>

      {/* Gider modalı */}
      <Modal
        open={expenseModalOpen}
        onClose={() => setExpenseModalOpen(false)}
        title={expenseForm.id ? t('common.edit') : t('finance.newExpense')}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setExpenseModalOpen(false)}
              disabled={saveExpense.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={!expenseFormValid || saveExpense.isPending}
              onClick={() => saveExpense.mutate()}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('common.name')} required className="sm:col-span-2">
            <input
              className="input"
              value={expenseForm.title}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setExpenseForm((current) => ({ ...current, title: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.expenseByCategory')} required>
            <select
              className="select"
              value={expenseForm.category}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setExpenseForm((current) => ({ ...current, category: event.target.value }))
              }
            >
              {EXPENSE_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`finance.categories.${category}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('finance.amount')} required>
            <input
              type="number"
              min="0"
              step="0.01"
              className="input"
              value={expenseForm.amount}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setExpenseForm((current) => ({ ...current, amount: event.target.value }))
              }
            />
          </Field>
          <Field label={t('common.date')} required>
            <input
              type="date"
              className="input"
              value={expenseForm.expenseDate}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setExpenseForm((current) => ({ ...current, expenseDate: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.method')} required>
            <select
              className="select"
              value={expenseForm.method}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                setExpenseForm((current) => ({
                  ...current,
                  method: event.target.value as PaymentMethod,
                }))
              }
            >
              {PAYMENT_METHODS.map((method) => (
                <option key={method} value={method}>
                  {t(`finance.methods.${method}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('finance.vendor')}>
            <input
              className="input"
              value={expenseForm.vendor}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setExpenseForm((current) => ({ ...current, vendor: event.target.value }))
              }
            />
          </Field>
          <Field label={t('finance.reference')}>
            <input
              className="input"
              value={expenseForm.invoiceReference}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setExpenseForm((current) => ({ ...current, invoiceReference: event.target.value }))
              }
            />
          </Field>
          <Field label={t('common.description')} className="sm:col-span-2">
            <textarea
              className="textarea"
              value={expenseForm.description}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setExpenseForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </Field>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300 sm:col-span-2">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600"
              checked={expenseForm.isRecurring}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setExpenseForm((current) => ({ ...current, isRecurring: event.target.checked }))
              }
            />
            {t('finance.isRecurring')}
          </label>
        </div>
      </Modal>

      <ConfirmDialog
        open={expenseToDelete !== null}
        onClose={() => setExpenseToDelete(null)}
        onConfirm={() => deleteExpense.mutate()}
        title={t('common.delete')}
        message={`${expenseToDelete?.title ?? ''} · ${formatCurrency(expenseToDelete?.amount ?? 0)}`}
        confirmLabel={t('common.delete')}
        loading={deleteExpense.isPending}
      />

      {/* İndirim modalı */}
      <Modal
        open={discountModalOpen}
        onClose={() => setDiscountModalOpen(false)}
        title={t('finance.discounts')}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setDiscountModalOpen(false)}
              disabled={createDiscount.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={!discountFormValid || createDiscount.isPending}
              onClick={() => createDiscount.mutate()}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('finance.reference')} required>
            <input
              className="input font-mono uppercase"
              value={discountForm.code}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setDiscountForm((current) => ({
                  ...current,
                  code: event.target.value.toUpperCase(),
                }))
              }
            />
          </Field>
          <Field label={t('common.name')} required>
            <input
              className="input"
              value={discountForm.name}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setDiscountForm((current) => ({ ...current, name: event.target.value }))
              }
            />
          </Field>
          <Field
            label={`${t('membership.discount')} %`}
            hint={t('common.optional')}
          >
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              className="input"
              value={discountForm.percentage}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setDiscountForm((current) => ({
                  ...current,
                  percentage: event.target.value,
                  fixedAmount: event.target.value ? '' : current.fixedAmount,
                }))
              }
            />
          </Field>
          <Field label={t('finance.amount')} hint={t('common.optional')}>
            <input
              type="number"
              min="0"
              step="0.01"
              className="input"
              value={discountForm.fixedAmount}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setDiscountForm((current) => ({
                  ...current,
                  fixedAmount: event.target.value,
                  percentage: event.target.value ? '' : current.percentage,
                }))
              }
            />
          </Field>
          <Field label={t('membership.startDate')} required>
            <input
              type="date"
              className="input"
              value={discountForm.validFrom}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setDiscountForm((current) => ({ ...current, validFrom: event.target.value }))
              }
            />
          </Field>
          <Field label={t('membership.endDate')} required>
            <input
              type="date"
              className="input"
              value={discountForm.validUntil}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setDiscountForm((current) => ({ ...current, validUntil: event.target.value }))
              }
            />
          </Field>
          <Field label={t('pool.capacity')} hint={t('common.optional')}>
            <input
              type="number"
              min="1"
              step="1"
              className="input"
              value={discountForm.maxUses}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setDiscountForm((current) => ({ ...current, maxUses: event.target.value }))
              }
            />
          </Field>
          <div className="flex items-end pb-2">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
                checked={discountForm.isActive}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setDiscountForm((current) => ({ ...current, isActive: event.target.checked }))
                }
              />
              {t('common.active')}
            </label>
          </div>
          <Field label={t('common.description')} className="sm:col-span-2">
            <textarea
              className="textarea"
              value={discountForm.description}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                setDiscountForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </Field>
        </div>
      </Modal>
    </>
  )
}
