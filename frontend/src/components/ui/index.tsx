/** Paylaşılan arayüz bileşenleri / Shared UI primitives. */
import clsx from 'clsx'
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Info,
  Loader2,
  Search,
  X,
} from 'lucide-react'
import {
  Fragment,
  useEffect,
  useRef,
  type ReactNode,
} from 'react'
import { useTranslation } from 'react-i18next'

import { useToast } from '@/lib/store'

// ---------------------------------------------------------------------------
// Sayfa başlığı
// ---------------------------------------------------------------------------
export function PageHeader({
  title,
  subtitle,
  actions,
  icon,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        {icon && (
          <div className="mt-0.5 rounded-lg bg-brand-50 p-2 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
            {icon}
          </div>
        )}
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
          {subtitle && (
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Kart
// ---------------------------------------------------------------------------
export function Card({
  title,
  actions,
  children,
  className,
  bodyClassName,
  footer,
}: {
  title?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
  footer?: ReactNode
}) {
  return (
    <section className={clsx('card', className)}>
      {(title || actions) && (
        <header className="card-header">
          {typeof title === 'string' ? <h2 className="card-title">{title}</h2> : title}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={clsx('card-body', bodyClassName)}>{children}</div>
      {footer && (
        <footer className="border-t border-slate-200 px-5 py-3 dark:border-slate-700">
          {footer}
        </footer>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// İstatistik kartı
// ---------------------------------------------------------------------------
export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = 'neutral',
  trend,
  onClick,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'brand'
  trend?: { value: number; label?: string }
  onClick?: () => void
}) {
  const tones = {
    neutral: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    success: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400',
    warning: 'bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-400',
    danger: 'bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400',
    brand: 'bg-brand-100 text-brand-600 dark:bg-brand-900/40 dark:text-brand-400',
  }
  const Wrapper = onClick ? 'button' : 'div'

  return (
    <Wrapper
      onClick={onClick}
      className={clsx(
        'card card-hover w-full p-4 text-left',
        onClick && 'cursor-pointer hover:border-brand-300 dark:hover:border-brand-700',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
          <p className="mt-1.5 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            {value}
          </p>
          {hint && <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
          {trend && (
            <p
              className={clsx(
                'mt-1 text-xs font-medium',
                trend.value > 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : trend.value < 0
                    ? 'text-rose-600 dark:text-rose-400'
                    : 'text-slate-500',
              )}
            >
              {trend.value > 0 ? '▲' : trend.value < 0 ? '▼' : '■'} {Math.abs(trend.value).toFixed(1)}%
              {trend.label && <span className="ml-1 text-slate-400">{trend.label}</span>}
            </p>
          )}
        </div>
        {icon && <div className={clsx('shrink-0 rounded-lg p-2', tones[tone])}>{icon}</div>}
      </div>
    </Wrapper>
  )
}

// ---------------------------------------------------------------------------
// Durum göstergeleri
// ---------------------------------------------------------------------------
export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx('h-4 w-4 animate-spin', className)} />
}

export function LoadingState({ label }: { label?: string }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-slate-500 dark:text-slate-400">
      <Spinner className="h-6 w-6" />
      <p className="text-sm">{label ?? t('common.loading')}</p>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  icon,
  action,
}: {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <div className="rounded-full bg-slate-100 p-3 text-slate-400 dark:bg-slate-700 dark:text-slate-500">
        {icon ?? <Search className="h-6 w-6" />}
      </div>
      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{title}</p>
        {description && (
          <p className="mt-1 max-w-md text-xs text-slate-500 dark:text-slate-400">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation()
  const message = error instanceof Error ? error.message : t('errors.generic')
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
      <AlertCircle className="h-8 w-8 text-rose-500" />
      <p className="max-w-md text-sm text-slate-700 dark:text-slate-300">{message}</p>
      {onRetry && (
        <button type="button" className="btn-secondary btn-sm" onClick={onRetry}>
          {t('common.retry')}
        </button>
      )}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('skeleton', className)} />
}

export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-3">
          {Array.from({ length: cols }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-8 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Rozet
// ---------------------------------------------------------------------------
export type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info'

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode
  tone?: BadgeTone
  className?: string
}) {
  return <span className={clsx(`badge-${tone}`, className)}>{children}</span>
}

const STATUS_TONES: Record<string, BadgeTone> = {
  active: 'success', paid: 'success', completed: 'success', present: 'success',
  verified: 'success', operational: 'success', ok: 'success', good: 'success',
  passive: 'neutral', pending: 'neutral', scheduled: 'info', not_started: 'neutral',
  trial: 'info', in_progress: 'info', partial: 'warning', late: 'warning',
  excused: 'warning', frozen: 'warning', warning: 'warning', maintenance: 'warning',
  expired: 'danger', overdue: 'danger', cancelled: 'danger', absent: 'danger',
  failed: 'danger', corrupted: 'danger', left: 'danger', closed: 'danger',
  critical: 'danger', high: 'danger', medium: 'warning', low: 'info', bad: 'danger',
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return <Badge tone={STATUS_TONES[status] ?? 'neutral'}>{label ?? status}</Badge>
}

/** Demo verisi işareti - gerçek kayıtla karışmasını önler */
export function DemoBadge() {
  const { t } = useTranslation()
  return (
    <span
      title={t('common.demoTooltip')}
      className="badge bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
    >
      {t('common.demo')}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = 'md',
}: {
  open: boolean
  onClose: () => void
  title: ReactNode
  children: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
    xl: 'max-w-6xl',
    full: 'max-w-[95vw]',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 pt-[6vh]">
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        className={clsx(
          'relative w-full animate-slide-up rounded-xl bg-white shadow-panel dark:bg-surface-dark-alt',
          sizes[size],
        )}
      >
        <header className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4 dark:border-slate-700">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700"
            aria-label="Kapat"
          >
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <footer className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-3 dark:border-slate-700">
            {footer}
          </footer>
        )}
      </div>
    </div>
  )
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel,
  tone = 'danger',
  loading,
}: {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: ReactNode
  confirmLabel?: string
  tone?: 'danger' | 'primary'
  loading?: boolean
}) {
  const { t } = useTranslation()
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
            {t('common.cancel')}
          </button>
          <button
            type="button"
            className={tone === 'danger' ? 'btn-danger' : 'btn-primary'}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading && <Spinner />}
            {confirmLabel ?? t('common.confirm')}
          </button>
        </>
      }
    >
      <div className="flex gap-3">
        <AlertTriangle
          className={clsx('mt-0.5 h-5 w-5 shrink-0', tone === 'danger' ? 'text-rose-500' : 'text-brand-500')}
        />
        <div className="text-sm text-slate-600 dark:text-slate-300">{message}</div>
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Form alanları
// ---------------------------------------------------------------------------
export function Field({
  label,
  required,
  error,
  hint,
  children,
  className,
}: {
  label?: string
  required?: boolean
  error?: string
  hint?: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={className}>
      {label && (
        <label className="label">
          {label}
          {required && <span className="ml-0.5 text-rose-500">*</span>}
        </label>
      )}
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
      {error && <p className="field-error">{error}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sayfalama
// ---------------------------------------------------------------------------
export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (size: number) => void
}) {
  const { t } = useTranslation()
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  return (
    <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm dark:border-slate-700 sm:flex-row">
      <p className="text-slate-500 dark:text-slate-400">
        {from}–{to} / {total}
      </p>
      <div className="flex items-center gap-3">
        {onPageSizeChange && (
          <select
            className="select w-auto py-1 text-xs"
            value={pageSize}
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            aria-label={t('common.rowsPerPage')}
          >
            {[10, 25, 50, 100].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        )}
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            aria-label={t('common.previous')}
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="px-2 text-slate-600 dark:text-slate-300">
            {page} / {pages}
          </span>
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
            aria-label={t('common.next')}
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sekmeler
// ---------------------------------------------------------------------------
export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: string; label: string; icon?: ReactNode; badge?: number }>
  active: string
  onChange: (id: string) => void
}) {
  return (
    <div className="mb-5 flex gap-1 overflow-x-auto border-b border-slate-200 scrollbar-none dark:border-slate-700">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={clsx(
            'flex shrink-0 items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors',
            active === tab.id
              ? 'border-brand-500 text-brand-600 dark:text-brand-400'
              : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200',
          )}
        >
          {tab.icon}
          {tab.label}
          {tab.badge !== undefined && tab.badge > 0 && (
            <span className="rounded-full bg-slate-200 px-1.5 text-xs dark:bg-slate-600">
              {tab.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Bilgi kutuları
// ---------------------------------------------------------------------------
export function Alert({
  tone = 'info',
  title,
  children,
  icon,
}: {
  tone?: 'info' | 'success' | 'warning' | 'danger'
  title?: string
  children?: ReactNode
  icon?: ReactNode
}) {
  const styles = {
    info: 'border-brand-300 bg-brand-50 text-brand-900 dark:border-brand-800 dark:bg-brand-900/20 dark:text-brand-200',
    success:
      'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200',
    warning:
      'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200',
    danger:
      'border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-200',
  }
  const icons = {
    info: <Info className="h-4 w-4" />,
    success: <CheckCircle2 className="h-4 w-4" />,
    warning: <AlertTriangle className="h-4 w-4" />,
    danger: <AlertCircle className="h-4 w-4" />,
  }

  return (
    <div className={clsx('flex gap-3 rounded-lg border px-4 py-3 text-sm', styles[tone])}>
      <div className="mt-0.5 shrink-0">{icon ?? icons[tone]}</div>
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={clsx(title && 'mt-1', 'text-xs leading-relaxed')}>{children}</div>}
      </div>
    </div>
  )
}

/**
 * AI yorumu ile gerçek veriyi görsel olarak ayıran panel.
 * Kullanıcı hangi bilginin hesaplanmış, hangisinin model çıktısı olduğunu
 * her zaman ayırt edebilmelidir.
 */
export function DataPanel({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="data-panel">
      <div className="mb-2 flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        <h3 className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">{title}</h3>
      </div>
      <p className="mb-3 text-xs text-emerald-700 dark:text-emerald-300/80">{t('ai.realDataHint')}</p>
      <div className="text-sm text-slate-700 dark:text-slate-200">{children}</div>
    </div>
  )
}

export function AIPanel({
  title,
  children,
  provider,
  model,
}: {
  title: string
  children: ReactNode
  provider?: string | null
  model?: string | null
}) {
  const { t } = useTranslation()
  return (
    <div className="ai-panel">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-violet-600 dark:text-violet-400">✦</span>
        <h3 className="text-sm font-semibold text-violet-900 dark:text-violet-200">{title}</h3>
        {provider && (
          <span className="badge bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
            {provider}
            {model ? ` · ${model}` : ''}
          </span>
        )}
      </div>
      <div className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">{children}</div>
      <p className="ai-disclaimer mt-3">{t('ai.disclaimer')}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tostlar
// ---------------------------------------------------------------------------
export function ToastContainer() {
  const { toasts, dismiss } = useToast()
  const icons = {
    success: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
    error: <AlertCircle className="h-4 w-4 text-rose-500" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-500" />,
    info: <Info className="h-4 w-4 text-brand-500" />,
  }

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className="pointer-events-auto flex animate-slide-up items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-panel dark:border-slate-700 dark:bg-surface-dark-alt"
        >
          <div className="mt-0.5">{icons[toast.type]}</div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{toast.title}</p>
            {toast.description && (
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{toast.description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => dismiss(toast.id)}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
            aria-label="Kapat"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tablo sarmalayıcı
// ---------------------------------------------------------------------------
export function TableWrapper({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx('overflow-x-auto', className)}>
      <table className="table">{children}</table>
    </div>
  )
}

export function ProgressBar({
  value,
  tone = 'brand',
  showLabel,
}: {
  value: number
  tone?: 'brand' | 'success' | 'warning' | 'danger'
  showLabel?: boolean
}) {
  const clamped = Math.max(0, Math.min(100, value))
  const tones = {
    brand: 'bg-brand-500',
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    danger: 'bg-rose-500',
  }
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className={clsx('h-full rounded-full transition-all', tones[tone])} style={{ width: `${clamped}%` }} />
      </div>
      {showLabel && (
        <span className="w-10 shrink-0 text-right text-xs text-slate-500">{clamped.toFixed(0)}%</span>
      )}
    </div>
  )
}

export { Fragment }
