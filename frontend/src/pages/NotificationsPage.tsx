/** Bildirim merkezi / Notification centre. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  AlertCircle,
  AlertTriangle,
  Bell,
  BellRing,
  CheckCheck,
  CheckCircle2,
  ExternalLink,
  Info,
  Radar,
  Send,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  Pagination,
  Spinner,
  StatCard,
  Tabs,
} from '@/components/ui'
import { get, post } from '@/lib/api'
import { formatNumber, formatRelative } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type { Message, Notification, Page } from '@/lib/types'

// ---------------------------------------------------------------------------
// Yerel tipler ve sabitler
// ---------------------------------------------------------------------------
type Severity = Notification['severity']

interface NotificationCounts {
  total: number
  unread: number
  by_severity: Record<string, number>
}

interface RoleCatalog {
  groups: Record<string, Array<{ code: string; label: string }>>
}

const SEVERITIES: Severity[] = ['info', 'success', 'warning', 'error']

/** Bildirim türleri - backend NotificationType numaralandırması ile aynı sırada */
const NOTIFICATION_TYPES = [
  'membership_expiring',
  'payment_overdue',
  'lesson_cancelled',
  'instructor_leave',
  'pool_maintenance',
  'performance_drop',
  'competition_upcoming',
  'ai_report_ready',
  'backup_result',
  'system',
  'trial_lesson',
  'new_registration',
]

/** Sol kenarlık rengi (ayrı bir şerit olarak çizilir, koyu temada da okunur) */
const SEVERITY_ACCENT: Record<Severity, string> = {
  info: 'bg-brand-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  error: 'bg-rose-500',
}

const SEVERITY_ICON: Record<Severity, ReactNode> = {
  info: <Info className="h-4 w-4 text-brand-600 dark:text-brand-400" />,
  success: <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
  warning: <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />,
  error: <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400" />,
}

/** Önem seviyesi etiketleri için mevcut çeviri anahtarları */
const SEVERITY_LABEL_KEY: Record<Severity, string> = {
  info: 'common.info',
  success: 'common.success',
  warning: 'common.warning',
  error: 'common.error',
}

const SEVERITY_TONE: Record<Severity, 'neutral' | 'success' | 'warning' | 'danger' | 'brand'> = {
  info: 'brand',
  success: 'success',
  warning: 'warning',
  error: 'danger',
}

interface SendForm {
  title_tr: string
  title_en: string
  body_tr: string
  body_en: string
  notification_type: string
  severity: Severity
  role_codes: string[]
}

const EMPTY_SEND_FORM: SendForm = {
  title_tr: '',
  title_en: '',
  body_tr: '',
  body_en: '',
  notification_type: 'system',
  severity: 'info',
  role_codes: [],
}

export default function NotificationsPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<'all' | 'unread'>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [sendOpen, setSendOpen] = useState(false)
  const [sendForm, setSendForm] = useState<SendForm>(EMPTY_SEND_FORM)
  const [sendError, setSendError] = useState('')

  const canSend = can('notification:send')

  // --- Sayaçlar -------------------------------------------------------------
  const countsQuery = useQuery({
    queryKey: ['notification-counts'],
    queryFn: () => get<NotificationCounts>('/notifications/counts'),
    refetchInterval: 120_000,
  })

  // --- Liste ----------------------------------------------------------------
  const listQuery = useQuery({
    queryKey: ['notifications', tab, page, pageSize],
    queryFn: () =>
      get<Page<Notification>>('/notifications', {
        unread_only: tab === 'unread',
        page,
        page_size: pageSize,
      }),
  })

  // --- Rol kataloğu (yalnızca gönderme yetkisi varsa) -----------------------
  const rolesQuery = useQuery({
    queryKey: ['role-catalog'],
    queryFn: () => get<RoleCatalog>('/users/roles/catalog'),
    enabled: canSend && sendOpen,
  })

  function refreshAll() {
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
    queryClient.invalidateQueries({ queryKey: ['notification-counts'] })
  }

  const markReadMutation = useMutation({
    mutationFn: (id: number) => post<Message>(`/notifications/${id}/read`),
    onSuccess: () => refreshAll(),
    onError: (error) => toastError(error),
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => post<Message>('/notifications/read-all'),
    onSuccess: () => {
      refreshAll()
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const generateMutation = useMutation({
    mutationFn: () => post<Message>('/notifications/generate'),
    onSuccess: (message) => {
      refreshAll()
      // Sunucu üretilen bildirimleri tür bazında döner: { created: { tip: adet } }
      const created = message.data?.created
      const detail: string[] = []
      let total = 0
      if (created && typeof created === 'object') {
        for (const [key, value] of Object.entries(created as Record<string, unknown>)) {
          const count = typeof value === 'number' ? value : 0
          total += count
          if (count > 0) {
            detail.push(`${t(`notifications.types.${key}`, key)}: ${formatNumber(count)}`)
          }
        }
      }
      toastSuccess(
        `${t('notifications.generate')} · ${formatNumber(total)}`,
        detail.length > 0 ? detail.join(' · ') : t('notifications.noNotifications'),
      )
    },
    onError: (error) => toastError(error),
  })

  const sendMutation = useMutation({
    mutationFn: () =>
      post<Message>('/notifications', {
        role_codes: sendForm.role_codes,
        user_ids: [],
        notification_type: sendForm.notification_type,
        severity: sendForm.severity,
        title_tr: sendForm.title_tr.trim(),
        title_en: sendForm.title_en.trim() || null,
        body_tr: sendForm.body_tr.trim() || null,
        body_en: sendForm.body_en.trim() || null,
      }),
    onSuccess: (message) => {
      refreshAll()
      setSendOpen(false)
      setSendForm(EMPTY_SEND_FORM)
      const recipients = message.data?.recipients
      toastSuccess(
        t('common.success'),
        typeof recipients === 'number' ? formatNumber(recipients) : undefined,
      )
    },
    onError: (error) => toastError(error),
  })

  function submitSend(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!sendForm.title_tr.trim()) {
      setSendError(t('common.required'))
      return
    }
    setSendError('')
    sendMutation.mutate()
  }

  function toggleRole(code: string) {
    setSendForm((current) => ({
      ...current,
      role_codes: current.role_codes.includes(code)
        ? current.role_codes.filter((item) => item !== code)
        : [...current.role_codes, code],
    }))
  }

  function changeTab(id: string) {
    setTab(id === 'unread' ? 'unread' : 'all')
    setPage(1)
  }

  const counts = countsQuery.data
  const items = listQuery.data?.items ?? []

  return (
    <>
      <PageHeader
        title={t('notifications.title')}
        subtitle={t('nav.notifications')}
        icon={<Bell className="h-5 w-5" />}
        actions={
          <>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending || (counts?.unread ?? 0) === 0}
            >
              {markAllReadMutation.isPending ? <Spinner /> : <CheckCheck className="h-4 w-4" />}
              {t('notifications.markAllRead')}
            </button>
            {canSend && (
              <>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                >
                  {generateMutation.isPending ? <Spinner /> : <Radar className="h-4 w-4" />}
                  {t('notifications.generate')}
                </button>
                <button
                  type="button"
                  className="btn-primary btn-sm"
                  onClick={() => {
                    setSendError('')
                    setSendOpen(true)
                  }}
                >
                  <Send className="h-4 w-4" />
                  {t('common.new')} · {t('notifications.title')}
                </button>
              </>
            )}
          </>
        }
      />

      {/* Sayaçlar ve önem dağılımı */}
      {countsQuery.error ? (
        <div className="mb-6">
          <ErrorState error={countsQuery.error} onRetry={countsQuery.refetch} />
        </div>
      ) : (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatCard
            label={t('common.total')}
            value={formatNumber(counts?.total ?? 0)}
            icon={<Bell className="h-5 w-5" />}
            tone="neutral"
          />
          <StatCard
            label={t('notifications.unread')}
            value={formatNumber(counts?.unread ?? 0)}
            icon={<BellRing className="h-5 w-5" />}
            tone={(counts?.unread ?? 0) > 0 ? 'brand' : 'success'}
            onClick={() => changeTab('unread')}
          />
          {SEVERITIES.map((severity) => (
            <StatCard
              key={severity}
              label={t(SEVERITY_LABEL_KEY[severity])}
              value={formatNumber(counts?.by_severity[severity] ?? 0)}
              hint={t('notifications.unread')}
              icon={SEVERITY_ICON[severity]}
              tone={SEVERITY_TONE[severity]}
            />
          ))}
        </div>
      )}

      <Tabs
        tabs={[
          { id: 'all', label: t('common.all') },
          { id: 'unread', label: t('notifications.unread'), badge: counts?.unread ?? 0 },
        ]}
        active={tab}
        onChange={changeTab}
      />

      <Card bodyClassName="p-0">
        {listQuery.isLoading ? (
          <LoadingState />
        ) : listQuery.error ? (
          <ErrorState error={listQuery.error} onRetry={listQuery.refetch} />
        ) : items.length === 0 ? (
          <EmptyState
            title={t('notifications.noNotifications')}
            description={t('dashboard.noAlerts')}
            icon={<Bell className="h-6 w-6" />}
          />
        ) : (
          <>
            <ul className="space-y-2 p-3">
              {items.map((notification) => (
                <li
                  key={notification.id}
                  className={clsx(
                    'relative overflow-hidden rounded-lg border bg-white transition-colors dark:bg-surface-dark-alt',
                    notification.is_read
                      ? 'border-slate-200 dark:border-slate-700'
                      : 'border-brand-200 shadow-sm dark:border-brand-800',
                  )}
                >
                  <span
                    className={clsx(
                      'absolute inset-y-0 left-0 w-1',
                      SEVERITY_ACCENT[notification.severity],
                    )}
                    aria-hidden="true"
                  />
                  <div className="flex flex-col gap-3 py-3 pl-5 pr-3 sm:flex-row sm:items-start">
                    <div className="mt-0.5 shrink-0">{SEVERITY_ICON[notification.severity]}</div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p
                          className={clsx(
                            'text-sm',
                            notification.is_read
                              ? 'text-slate-700 dark:text-slate-300'
                              : 'font-semibold text-slate-900 dark:text-slate-100',
                          )}
                        >
                          {notification.title}
                        </p>
                        {!notification.is_read && (
                          <span className="h-2 w-2 shrink-0 rounded-full bg-brand-500" />
                        )}
                      </div>

                      {notification.body && (
                        <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                          {notification.body}
                        </p>
                      )}

                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Badge tone="neutral">
                          {t(
                            `notifications.types.${notification.notification_type}`,
                            notification.notification_type,
                          )}
                        </Badge>
                        <span className="text-xs text-slate-400 dark:text-slate-500">
                          {formatRelative(notification.created_at)}
                        </span>
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      {notification.link && (
                        <Link to={notification.link} className="btn-ghost btn-sm">
                          <ExternalLink className="h-4 w-4" />
                          {t('training.goToScreen')}
                        </Link>
                      )}
                      {!notification.is_read && (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => markReadMutation.mutate(notification.id)}
                          disabled={markReadMutation.isPending}
                          title={t('notifications.markRead')}
                        >
                          {markReadMutation.isPending
                            && markReadMutation.variables === notification.id ? (
                            <Spinner />
                          ) : (
                            <CheckCheck className="h-4 w-4" />
                          )}
                          <span className="hidden sm:inline">{t('notifications.markRead')}</span>
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>

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

      {/* Bildirim gönderme */}
      <Modal
        open={sendOpen}
        onClose={() => setSendOpen(false)}
        title={`${t('common.new')} · ${t('notifications.title')}`}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setSendOpen(false)}
              disabled={sendMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              form="notification-send-form"
              className="btn-primary"
              disabled={sendMutation.isPending}
            >
              {sendMutation.isPending ? <Spinner /> : <Send className="h-4 w-4" />}
              {t('common.save')}
            </button>
          </>
        }
      >
        <form id="notification-send-form" onSubmit={submitSend} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={`${t('common.name')} (TR)`} required error={sendError}>
              <input
                className="input"
                value={sendForm.title_tr}
                onChange={(event) =>
                  setSendForm((current) => ({ ...current, title_tr: event.target.value }))
                }
                autoFocus
              />
            </Field>
            <Field label={`${t('common.name')} (EN)`}>
              <input
                className="input"
                value={sendForm.title_en}
                onChange={(event) =>
                  setSendForm((current) => ({ ...current, title_en: event.target.value }))
                }
              />
            </Field>
            <Field label={`${t('common.description')} (TR)`}>
              <textarea
                className="textarea"
                rows={3}
                value={sendForm.body_tr}
                onChange={(event) =>
                  setSendForm((current) => ({ ...current, body_tr: event.target.value }))
                }
              />
            </Field>
            <Field label={`${t('common.description')} (EN)`}>
              <textarea
                className="textarea"
                rows={3}
                value={sendForm.body_en}
                onChange={(event) =>
                  setSendForm((current) => ({ ...current, body_en: event.target.value }))
                }
              />
            </Field>
            <Field label={t('audit.entity')}>
              <select
                className="select"
                value={sendForm.notification_type}
                onChange={(event) =>
                  setSendForm((current) => ({ ...current, notification_type: event.target.value }))
                }
              >
                {NOTIFICATION_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`notifications.types.${type}`, type)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('common.status')}>
              <select
                className="select"
                value={sendForm.severity}
                onChange={(event) =>
                  setSendForm((current) => ({
                    ...current,
                    severity: event.target.value as Severity,
                  }))
                }
              >
                {SEVERITIES.map((severity) => (
                  <option key={severity} value={severity}>
                    {t(SEVERITY_LABEL_KEY[severity])}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {/* Hedef roller - boş bırakılırsa bildirim herkese açık olarak üretilir */}
          <Field
            label={`${t('statistics.target')} · ${t('auth.roles')}`}
            hint={sendForm.role_codes.length === 0 ? t('common.all') : undefined}
          >
            {rolesQuery.isLoading ? (
              <LoadingState />
            ) : rolesQuery.error ? (
              <ErrorState error={rolesQuery.error} onRetry={rolesQuery.refetch} />
            ) : (
              <div className="space-y-3">
                {Object.entries(rolesQuery.data?.groups ?? {}).map(([groupKey, roles]) => (
                  <div key={groupKey}>
                    <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                      {t(`users.roleGroups.${groupKey}`, groupKey)}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {roles.map((role) => {
                        const selected = sendForm.role_codes.includes(role.code)
                        return (
                          <button
                            key={role.code}
                            type="button"
                            onClick={() => toggleRole(role.code)}
                            className={clsx(
                              'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                              selected
                                ? 'border-brand-500 bg-brand-500 text-white'
                                : 'border-slate-300 bg-white text-slate-600 hover:border-brand-400 dark:border-slate-600 dark:bg-surface-dark-alt dark:text-slate-300 dark:hover:border-brand-600',
                            )}
                            aria-pressed={selected}
                          >
                            {role.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Field>
        </form>
      </Modal>
    </>
  )
}
