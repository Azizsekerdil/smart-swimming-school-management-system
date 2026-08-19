/** Ayarlar sayfası / Settings page: profil, kurum, yapay zekâ, geliştirici, yedekleme, kullanıcılar, denetim, hakkında. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Archive,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  FolderOpen,
  HardDrive,
  Info,
  KeyRound,
  Plus,
  RefreshCw,
  RotateCcw,
  ScrollText,
  Settings as SettingsIcon,
  ShieldCheck,
  Sparkles,
  Terminal,
  Trash2,
  User as UserIcon,
  Users as UsersIcon,
} from 'lucide-react'
import { Fragment, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'

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
import { del, get, patch, post, put } from '@/lib/api'
import { formatDateTime, formatFileSize, formatNumber, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { toastError, toastSuccess, useAuth, useUI, type Theme } from '@/lib/store'
import type {
  AboutInfo,
  AIControlCenter,
  AppSetting,
  AuditLog,
  BackupRecord,
  BackupStatusInfo,
  BackupVerifyResult,
  HealthReport,
  Message,
  Page,
  RestorePreview,
  User,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Yerel tipler (backend şemalarının karşılığı)
// ---------------------------------------------------------------------------
type TabId =
  | 'profile'
  | 'general'
  | 'ai'
  | 'developer'
  | 'backup'
  | 'users'
  | 'audit'
  | 'about'

interface OrganizationValue {
  name: string
  logo_url: string | null
  phone: string
  email: string
  address: string
  website: string
  tax_office: string
  tax_number: string
  currency: string
  language: string
  timezone: string
  date_format: string
}

interface DeveloperValue {
  ai_developer_enabled: boolean
  allow_apply: boolean
  allow_shell: boolean
  auto_test: boolean
  patch_policy: string
}

interface BackupSettingsValue {
  schedule_enabled: boolean
  schedule_cron: string
  retention_daily: number
  retention_weekly: number
  retention_monthly: number
  backup_dir: string
}

interface BackupLocationInfo {
  path: string
  exists: boolean
  file_count: number
  total_size_mb: number
  recent_files: string[]
}

interface RestoreStep {
  step: string
  status: string
  detail?: string
}

interface RestoreResultInfo {
  success: boolean
  backup_id: string
  safety_backup_id?: string | null
  message: string
  steps: RestoreStep[]
  rolled_back: boolean
}

interface RestoreHistoryRow {
  id: number
  backup_id: string
  safety_backup_id?: string | null
  status: string
  message?: string | null
  started_at: string
  finished_at?: string | null
}

interface RoleCatalogEntry {
  code: string
  label: string
}

interface RoleCatalog {
  groups: Record<string, RoleCatalogEntry[]>
}

interface I18nValidation {
  total_keys: number
  missing: Record<string, string[]>
  is_complete: boolean
}

const EMPTY_ORGANIZATION: OrganizationValue = {
  name: '',
  logo_url: null,
  phone: '',
  email: '',
  address: '',
  website: '',
  tax_office: '',
  tax_number: '',
  currency: 'TRY',
  language: 'tr',
  timezone: 'Europe/Istanbul',
  date_format: 'DD.MM.YYYY',
}

const EMPTY_DEVELOPER: DeveloperValue = {
  ai_developer_enabled: false,
  allow_apply: false,
  allow_shell: false,
  auto_test: true,
  patch_policy: 'review_required',
}

const CURRENCIES = ['TRY', 'EUR', 'USD', 'GBP']
const TIMEZONES = ['Europe/Istanbul', 'Europe/London', 'Europe/Berlin', 'UTC']
const DATE_FORMATS = ['DD.MM.YYYY', 'YYYY-MM-DD', 'MM/DD/YYYY']
const LANGUAGE_OPTIONS: Array<{ code: Language; label: string }> = [
  { code: 'tr', label: 'Türkçe' },
  { code: 'en', label: 'English' },
]
const THEME_OPTIONS: Theme[] = ['light', 'dark', 'system']
const PATCH_POLICIES: Array<{ value: string; labelKey: string }> = [
  { value: 'review_required', labelKey: 'aiDeveloper.requiresConfirmation' },
  { value: 'auto_apply_safe', labelKey: 'aiDeveloper.applyPatch' },
]
const BACKUP_TYPES = ['manual', 'full', 'incremental', 'pre_update', 'pre_migration']
const AUDIT_ACTIONS = [
  'create',
  'update',
  'delete',
  'soft_delete',
  'login',
  'logout',
  'export',
  'restore',
  'cancel',
]
const DAY_OPTIONS = [7, 30, 90, 365]
const HEALTH_DOT: Record<string, string> = {
  ok: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  down: 'bg-rose-500',
  disabled: 'bg-slate-400',
}

// ---------------------------------------------------------------------------
// Küçük yardımcı bileşenler
// ---------------------------------------------------------------------------
function InfoRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-2 last:border-0 dark:border-slate-800">
      <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">{label}</span>
      <span className="min-w-0 break-words text-right text-sm font-medium text-slate-800 dark:text-slate-100">
        {value}
      </span>
    </div>
  )
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  label: string
  hint?: string
  checked: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <span className="min-w-0">
        <span className="block text-sm font-medium text-slate-800 dark:text-slate-100">{label}</span>
        {hint && (
          <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">{hint}</span>
        )}
      </span>
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 shrink-0 accent-brand-500"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  )
}

/** Kopyalanabilir yol kutusu (yedek klasörü vb.) */
function CopyBox({ value }: { value: string }) {
  const { t } = useTranslation()

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value)
      toastSuccess(t('common.copied'))
    } catch (error) {
      toastError(error)
    }
  }

  return (
    <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
      <code className="min-w-0 flex-1 break-all text-xs text-slate-700 dark:text-slate-200">
        {value}
      </code>
      <button
        type="button"
        className="btn-ghost btn-sm shrink-0"
        onClick={() => void handleCopy()}
        title={t('common.copy')}
        aria-label={t('common.copy')}
      >
        <Copy className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function ResultBadge({ result }: { result: string }) {
  const passed = result.toUpperCase() === 'PASS' || result === 'success'
  const skipped = result.toUpperCase() === 'SKIPPED' || result === 'skipped'
  return (
    <Badge tone={passed ? 'success' : skipped ? 'neutral' : 'danger'}>{result.toUpperCase()}</Badge>
  )
}

// ---------------------------------------------------------------------------
// Ana sayfa
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const [searchParams, setSearchParams] = useSearchParams()

  // Sekmeleri yetkilere göre süz
  const tabs = useMemo(() => {
    const definitions: Array<{ id: TabId; label: string; icon: ReactNode; visible: boolean }> = [
      {
        id: 'profile',
        label: t('settings.tabs.profile'),
        icon: <UserIcon className="h-4 w-4" />,
        visible: true,
      },
      {
        id: 'general',
        label: t('settings.tabs.general'),
        icon: <Building2 className="h-4 w-4" />,
        visible: can('settings:read'),
      },
      {
        id: 'ai',
        label: t('settings.tabs.ai'),
        icon: <Sparkles className="h-4 w-4" />,
        visible: can('ai:use'),
      },
      {
        id: 'developer',
        label: t('settings.tabs.developer'),
        icon: <Terminal className="h-4 w-4" />,
        visible: can('ai:developer'),
      },
      {
        id: 'backup',
        label: t('settings.tabs.backup'),
        icon: <HardDrive className="h-4 w-4" />,
        visible: can('backup:read'),
      },
      {
        id: 'users',
        label: t('settings.tabs.users'),
        icon: <UsersIcon className="h-4 w-4" />,
        visible: can('user:read'),
      },
      {
        id: 'audit',
        label: t('settings.tabs.audit'),
        icon: <ScrollText className="h-4 w-4" />,
        visible: can('audit:read'),
      },
      {
        id: 'about',
        label: t('settings.tabs.about'),
        icon: <Info className="h-4 w-4" />,
        visible: true,
      },
    ]
    return definitions
      .filter((tab) => tab.visible)
      .map(({ id, label, icon }) => ({ id, label, icon }))
  }, [can, t])

  const requested = searchParams.get('tab') ?? ''
  const active = (tabs.some((tab) => tab.id === requested) ? requested : tabs[0].id) as TabId

  function handleTabChange(id: string) {
    const next = new URLSearchParams(searchParams)
    next.set('tab', id)
    setSearchParams(next, { replace: true })
  }

  return (
    <>
      <PageHeader
        title={t('settings.title')}
        subtitle={t('app.fullName')}
        icon={<SettingsIcon className="h-5 w-5" />}
      />

      <Tabs tabs={tabs} active={active} onChange={handleTabChange} />

      {active === 'profile' && <ProfileTab />}
      {active === 'general' && <GeneralTab />}
      {active === 'ai' && <AITab />}
      {active === 'developer' && <DeveloperTab />}
      {active === 'backup' && <BackupTab />}
      {active === 'users' && <UsersTab />}
      {active === 'audit' && <AuditTab />}
      {active === 'about' && <AboutTab />}
    </>
  )
}

// ---------------------------------------------------------------------------
// Profil
// ---------------------------------------------------------------------------
function ProfileTab() {
  const { t } = useTranslation()
  const user = useAuth((state) => state.user)
  const setUser = useAuth((state) => state.setUser)
  const theme = useUI((state) => state.theme)
  const setTheme = useUI((state) => state.setTheme)
  const language = useUI((state) => state.language)
  const changeLanguage = useUI((state) => state.changeLanguage)

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [mismatch, setMismatch] = useState(false)

  const trainingMutation = useMutation({
    mutationFn: (enabled: boolean) => post<Message>(`/training/mode/${enabled}`),
    onSuccess: (_result, enabled) => {
      if (user) setUser({ ...user, training_mode: enabled })
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const passwordMutation = useMutation({
    mutationFn: () =>
      post<Message>('/auth/change-password', { current_password: current, new_password: next }),
    onSuccess: () => {
      setCurrent('')
      setNext('')
      setRepeat('')
      setMismatch(false)
      toastSuccess(t('auth.passwordChanged'))
    },
    onError: (error) => toastError(error),
  })

  if (!user) return <LoadingState />

  function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (next !== repeat) {
      setMismatch(true)
      return
    }
    setMismatch(false)
    passwordMutation.mutate()
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={t('auth.myAccount')}>
        <div className="space-y-0.5">
          <InfoRow label={t('users.fullName')} value={user.full_name} />
          <InfoRow
            label={t('common.email')}
            value={<span className="text-slate-500 dark:text-slate-400">{user.email}</span>}
          />
          <InfoRow
            label={t('auth.roles')}
            value={
              user.roles.length === 0 ? (
                <span className="text-slate-400">{t('common.none')}</span>
              ) : (
                <span className="flex flex-wrap justify-end gap-1">
                  {user.roles.map((role) => (
                    <Badge key={role.id} tone="info">
                      {role.name_tr}
                    </Badge>
                  ))}
                </span>
              )
            }
          />
          <InfoRow
            label={t('auth.permissions')}
            value={
              user.is_superuser ? (
                <Badge tone="success">{t('users.isSuperuser')}</Badge>
              ) : (
                formatNumber(user.permissions.length)
              )
            }
          />
          <InfoRow
            label={t('auth.lastLogin')}
            value={user.last_login_at ? formatDateTime(user.last_login_at) : '—'}
          />
        </div>
      </Card>

      <Card title={t('settings.tabs.general')}>
        <div className="space-y-4">
          <Field label={t('settings.language')}>
            <select
              className="select"
              value={language}
              onChange={(event) => changeLanguage(event.target.value as Language)}
            >
              {LANGUAGE_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('settings.theme')}>
            <select
              className="select"
              value={theme}
              onChange={(event) => setTheme(event.target.value as Theme)}
            >
              {THEME_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {t(`settings.themes.${option}`)}
                </option>
              ))}
            </select>
          </Field>

          <ToggleRow
            label={t('settings.trainingMode')}
            hint={t('settings.trainingModeHint')}
            checked={user.training_mode}
            disabled={trainingMutation.isPending}
            onChange={(value) => trainingMutation.mutate(value)}
          />
        </div>
      </Card>

      <Card title={t('auth.changePassword')} className="lg:col-span-2">
        <form className="grid gap-4 sm:grid-cols-3" onSubmit={handlePasswordSubmit}>
          <Field label={t('auth.currentPassword')} required>
            <input
              type="password"
              className="input"
              autoComplete="current-password"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              required
            />
          </Field>
          <Field label={t('auth.newPassword')} required>
            <input
              type="password"
              className="input"
              autoComplete="new-password"
              minLength={8}
              value={next}
              onChange={(event) => setNext(event.target.value)}
              required
            />
          </Field>
          <Field
            label={t('auth.confirmPassword')}
            required
            error={mismatch ? t('auth.passwordMismatch') : undefined}
          >
            <input
              type="password"
              className="input"
              autoComplete="new-password"
              minLength={8}
              value={repeat}
              onChange={(event) => {
                setRepeat(event.target.value)
                if (mismatch) setMismatch(false)
              }}
              required
            />
          </Field>
          <div className="sm:col-span-3">
            <button type="submit" className="btn-primary" disabled={passwordMutation.isPending}>
              <KeyRound className="h-4 w-4" />
              {t('auth.changePassword')}
            </button>
          </div>
        </form>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Genel (kurum bilgileri)
// ---------------------------------------------------------------------------
function GeneralTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const can = useAuth((state) => state.can)
  const writable = can('settings:write')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['setting', 'organization'],
    queryFn: () => get<AppSetting>('/settings/organization'),
  })

  const [form, setForm] = useState<OrganizationValue>(EMPTY_ORGANIZATION)

  useEffect(() => {
    if (data && data.value && typeof data.value === 'object') {
      setForm({ ...EMPTY_ORGANIZATION, ...(data.value as Partial<OrganizationValue>) })
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: (value: OrganizationValue) =>
      put<AppSetting>('/settings', { key: 'organization', value, category: 'general' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['setting', 'organization'] })
      toastSuccess(t('common.success'))
    },
    onError: (saveError) => toastError(saveError),
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error} onRetry={refetch} />

  function update<K extends keyof OrganizationValue>(key: K, value: OrganizationValue[K]) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    saveMutation.mutate(form)
  }

  return (
    <form onSubmit={handleSubmit}>
      <Card
        title={t('settings.tabs.organization')}
        footer={
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {data?.updated_at ? `${t('settings.lastUpdated')}: ${formatDateTime(data.updated_at)}` : ''}
            </p>
            <button type="submit" className="btn-primary" disabled={!writable || saveMutation.isPending}>
              {t('common.save')}
            </button>
          </div>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('settings.organizationName')} required className="sm:col-span-2">
            <input
              className="input"
              value={form.name}
              disabled={!writable}
              onChange={(event) => update('name', event.target.value)}
              required
            />
          </Field>
          <Field label={t('common.phone')}>
            <input
              className="input"
              value={form.phone}
              disabled={!writable}
              onChange={(event) => update('phone', event.target.value)}
            />
          </Field>
          <Field label={t('common.email')}>
            <input
              type="email"
              className="input"
              value={form.email}
              disabled={!writable}
              onChange={(event) => update('email', event.target.value)}
            />
          </Field>
          <Field label={t('common.address')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={2}
              value={form.address}
              disabled={!writable}
              onChange={(event) => update('address', event.target.value)}
            />
          </Field>
          <Field label={t('settings.website')}>
            <input
              className="input"
              value={form.website}
              disabled={!writable}
              onChange={(event) => update('website', event.target.value)}
            />
          </Field>
          <Field label={t('settings.taxOffice')}>
            <input
              className="input"
              value={form.tax_office}
              disabled={!writable}
              onChange={(event) => update('tax_office', event.target.value)}
            />
          </Field>
          <Field label={t('settings.taxNumber')}>
            <input
              className="input"
              value={form.tax_number}
              disabled={!writable}
              onChange={(event) => update('tax_number', event.target.value)}
            />
          </Field>
          <Field label={t('settings.currency')}>
            <select
              className="select"
              value={form.currency}
              disabled={!writable}
              onChange={(event) => update('currency', event.target.value)}
            >
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('settings.language')}>
            <select
              className="select"
              value={form.language}
              disabled={!writable}
              onChange={(event) => update('language', event.target.value)}
            >
              {LANGUAGE_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('settings.timezone')}>
            <select
              className="select"
              value={form.timezone}
              disabled={!writable}
              onChange={(event) => update('timezone', event.target.value)}
            >
              {TIMEZONES.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('settings.dateFormat')}>
            <select
              className="select"
              value={form.date_format}
              disabled={!writable}
              onChange={(event) => update('date_format', event.target.value)}
            >
              {DATE_FORMATS.map((format) => (
                <option key={format} value={format}>
                  {format}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {!writable && (
          <div className="mt-4">
            <Alert tone="info">{t('errors.forbiddenHint')}</Alert>
          </div>
        )}
      </Card>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Yapay zekâ özeti
// ---------------------------------------------------------------------------
function AITab() {
  const { t, i18n } = useTranslation()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['ai', 'control-center', 'settings-summary'],
    queryFn: () => get<AIControlCenter>('/ai/control-center'),
  })

  return (
    <div className="space-y-4">
      <Card title={t('ai.controlCenter')}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-600 dark:text-slate-300">{t('ai.subtitle')}</p>
          <Link to="/ai" className="btn-primary shrink-0">
            <ExternalLink className="h-4 w-4" />
            {t('ai.title')}
          </Link>
        </div>
        <div className="mt-3">
          <Alert tone="info">{t('ai.systemWorksWithoutAi')}</Alert>
        </div>
      </Card>

      {isLoading && <LoadingState />}
      {error && <ErrorState error={error} onRetry={refetch} />}

      {data && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label={t('ai.mode')}
              value={t(`ai.modes.${data.mode}`, data.mode)}
              hint={`${t('ai.fallbackChain')}: ${data.fallback_chain.join(' → ') || '—'}`}
              icon={<Sparkles className="h-5 w-5" />}
              tone="brand"
            />
            <StatCard
              label={t('ai.providers')}
              value={`${data.providers.filter((provider) => provider.available).length}/${data.providers.length}`}
              hint={t('ai.available')}
              icon={<CheckCircle2 className="h-5 w-5" />}
              tone={data.providers.some((provider) => provider.available) ? 'success' : 'warning'}
            />
            <StatCard
              label={t('ai.todayUsage')}
              value={formatNumber(data.usage_today.total_tokens)}
              hint={`${t('ai.totalUsage')}: ${formatNumber(data.usage_total.total_tokens)}`}
              icon={<Archive className="h-5 w-5" />}
            />
            <StatCard
              label={t('ai.errors24h')}
              value={formatNumber(data.error_count_24h)}
              icon={<Info className="h-5 w-5" />}
              tone={data.error_count_24h > 0 ? 'danger' : 'neutral'}
            />
          </div>

          <Card title={t('ai.providers')} bodyClassName="p-0">
            {data.providers.length === 0 ? (
              <EmptyState title={t('common.noData')} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('ai.provider')}</th>
                    <th>{t('ai.status')}</th>
                    <th className="hidden md:table-cell">{t('ai.model')}</th>
                    <th className="hidden lg:table-cell">{t('ai.latency')}</th>
                    <th className="hidden lg:table-cell">{t('ai.apiKey')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.providers.map((provider) => (
                    <tr key={provider.provider}>
                      <td>
                        <span className="font-medium text-slate-800 dark:text-slate-100">
                          {provider.display_name}
                        </span>
                        <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                          {provider.is_local
                            ? t('ai.localPrivacy')
                            : (i18n.language === 'tr'
                              ? provider.privacy_note_tr
                              : provider.privacy_note_en) ?? t('ai.cloudPrivacy')}
                        </span>
                      </td>
                      <td>
                        <Badge
                          tone={
                            !provider.enabled ? 'neutral' : provider.available ? 'success' : 'danger'
                          }
                        >
                          {!provider.enabled
                            ? t('ai.disabled')
                            : provider.available
                              ? t('ai.available')
                              : t('ai.unavailable')}
                        </Badge>
                      </td>
                      <td className="hidden md:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {provider.model ?? '—'}
                      </td>
                      <td className="hidden lg:table-cell text-xs text-slate-500 dark:text-slate-400">
                        {provider.latency_ms !== null && provider.latency_ms !== undefined
                          ? `${formatNumber(provider.latency_ms)} ms`
                          : '—'}
                      </td>
                      <td className="hidden lg:table-cell text-xs">
                        {provider.api_key_set ? (
                          <span className="text-emerald-600 dark:text-emerald-400">
                            {t('ai.apiKeySet')}
                          </span>
                        ) : (
                          <span className="text-slate-400">{t('ai.apiKeyNotSet')}</span>
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
    </div>
  )
}

// ---------------------------------------------------------------------------
// Geliştirici
// ---------------------------------------------------------------------------
function DeveloperTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const can = useAuth((state) => state.can)
  const writable = can('settings:write')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['setting', 'developer'],
    queryFn: () => get<AppSetting>('/settings/developer'),
  })

  const [form, setForm] = useState<DeveloperValue>(EMPTY_DEVELOPER)

  useEffect(() => {
    if (data && data.value && typeof data.value === 'object') {
      setForm({ ...EMPTY_DEVELOPER, ...(data.value as Partial<DeveloperValue>) })
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: (value: DeveloperValue) =>
      put<AppSetting>('/settings', { key: 'developer', value, category: 'developer' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['setting', 'developer'] })
      toastSuccess(t('common.success'))
    },
    onError: (saveError) => toastError(saveError),
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error} onRetry={refetch} />

  function update<K extends keyof DeveloperValue>(key: K, value: DeveloperValue[K]) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  return (
    <div className="space-y-4">
      <Card
        title={t('settings.developerSettings')}
        footer={
          <div className="flex justify-end">
            <button
              type="button"
              className="btn-primary"
              disabled={!writable || saveMutation.isPending}
              onClick={() => saveMutation.mutate(form)}
            >
              {t('common.save')}
            </button>
          </div>
        }
      >
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          {t('aiDeveloper.policySubtitle')}
        </p>

        <div className="space-y-3">
          <ToggleRow
            label={t('settings.aiDeveloperEnabled')}
            checked={form.ai_developer_enabled}
            disabled={!writable}
            onChange={(value) => update('ai_developer_enabled', value)}
          />
          <ToggleRow
            label={t('settings.autoTest')}
            checked={form.auto_test}
            disabled={!writable}
            onChange={(value) => update('auto_test', value)}
          />

          <div className="rounded-lg border border-amber-300 bg-amber-50/60 p-3 dark:border-amber-800 dark:bg-amber-900/10">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
              {t('settings.dangerZone')}
            </p>
            <div className="space-y-3">
              <ToggleRow
                label={t('settings.allowApply')}
                hint={t('aiDeveloper.applyConfirm')}
                checked={form.allow_apply}
                disabled={!writable}
                onChange={(value) => update('allow_apply', value)}
              />
              {form.allow_apply && (
                <Alert tone="warning" title={t('settings.allowApply')}>
                  {t('aiDeveloper.applyConfirm')}
                </Alert>
              )}
              <ToggleRow
                label={t('settings.allowShell')}
                hint={t('aiDeveloper.blockedOperations')}
                checked={form.allow_shell}
                disabled={!writable}
                onChange={(value) => update('allow_shell', value)}
              />
              {form.allow_shell && (
                <Alert tone="warning" title={t('settings.allowShell')}>
                  {t('caio.cannotModify')}
                </Alert>
              )}
            </div>
          </div>

          <Field label={t('settings.patchPolicy')}>
            <select
              className="select"
              value={form.patch_policy}
              disabled={!writable}
              onChange={(event) => update('patch_policy', event.target.value)}
            >
              {PATCH_POLICIES.map((policy) => (
                <option key={policy.value} value={policy.value}>
                  {t(policy.labelKey)} ({policy.value})
                </option>
              ))}
            </select>
          </Field>
        </div>

        {!writable && (
          <div className="mt-4">
            <Alert tone="info">{t('errors.forbiddenHint')}</Alert>
          </div>
        )}
      </Card>

      <Card title={t('aiDeveloper.title')}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-600 dark:text-slate-300">{t('aiDeveloper.subtitle')}</p>
          <Link to="/ai-developer" className="btn-secondary shrink-0">
            <ExternalLink className="h-4 w-4" />
            {t('aiDeveloper.title')}
          </Link>
        </div>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Yedekleme
// ---------------------------------------------------------------------------
function BackupTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const can = useAuth((state) => state.can)
  const canCreate = can('backup:create')
  const canRestore = can('backup:restore')

  const [createOpen, setCreateOpen] = useState(false)
  const [cleanupOpen, setCleanupOpen] = useState(false)
  const [folderOpen, setFolderOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<BackupRecord | null>(null)
  const [verifyResult, setVerifyResult] = useState<BackupVerifyResult | null>(null)
  const [restoreTarget, setRestoreTarget] = useState<string | null>(null)
  const [restoreConfirmed, setRestoreConfirmed] = useState(false)
  const [safetyBackup, setSafetyBackup] = useState(true)
  const [restoreResult, setRestoreResult] = useState<RestoreResultInfo | null>(null)
  const [createForm, setCreateForm] = useState({
    backup_type: 'manual',
    note: '',
    include_uploads: true,
    include_logs: false,
    protect: false,
  })

  const statusQuery = useQuery({
    queryKey: ['backup', 'status'],
    queryFn: () => get<BackupStatusInfo>('/backup/status'),
  })
  const listQuery = useQuery({
    queryKey: ['backup', 'list'],
    queryFn: () => get<BackupRecord[]>('/backup', { limit: 100 }),
  })
  const settingsQuery = useQuery({
    queryKey: ['backup', 'settings'],
    queryFn: () => get<BackupSettingsValue>('/backup/settings/current'),
  })
  const historyQuery = useQuery({
    queryKey: ['backup', 'restore-history'],
    queryFn: () => get<RestoreHistoryRow[]>('/backup/restores/history', { limit: 50 }),
  })
  const locationQuery = useQuery({
    queryKey: ['backup', 'location'],
    queryFn: () => get<BackupLocationInfo>('/backup/location/open'),
    enabled: folderOpen,
  })
  const previewQuery = useQuery({
    queryKey: ['backup', 'restore-preview', restoreTarget],
    queryFn: () => get<RestorePreview>(`/backup/${restoreTarget}/restore-preview`),
    enabled: restoreTarget !== null,
  })

  function refreshBackups() {
    void queryClient.invalidateQueries({ queryKey: ['backup'] })
  }

  const createMutation = useMutation({
    mutationFn: () => post<BackupRecord>('/backup', createForm),
    onSuccess: () => {
      setCreateOpen(false)
      refreshBackups()
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const cleanupMutation = useMutation({
    mutationFn: () => post<Message>('/backup/cleanup'),
    onSuccess: (result) => {
      setCleanupOpen(false)
      refreshBackups()
      toastSuccess(result.message)
    },
    onError: (error) => toastError(error),
  })

  const verifyMutation = useMutation({
    mutationFn: (backupId: string) => post<BackupVerifyResult>(`/backup/${backupId}/verify`),
    onSuccess: (result) => {
      setVerifyResult(result)
      refreshBackups()
    },
    onError: (error) => toastError(error),
  })

  const protectMutation = useMutation({
    mutationFn: (payload: { backupId: string; protect: boolean }) =>
      post<BackupRecord>(`/backup/${payload.backupId}/protect`, undefined, {
        protect: payload.protect,
      }),
    onSuccess: () => {
      refreshBackups()
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const deleteMutation = useMutation({
    mutationFn: (backupId: string) => del<Message>(`/backup/${backupId}`),
    onSuccess: (result) => {
      setDeleteTarget(null)
      refreshBackups()
      toastSuccess(result.message)
    },
    onError: (error) => toastError(error),
  })

  const restoreMutation = useMutation({
    mutationFn: (backupId: string) =>
      post<RestoreResultInfo>('/backup/restore', {
        backup_id: backupId,
        confirm: true,
        create_safety_backup: safetyBackup,
      }),
    onSuccess: (result) => {
      setRestoreTarget(null)
      setRestoreConfirmed(false)
      setRestoreResult(result)
      void queryClient.invalidateQueries()
    },
    onError: (error) => toastError(error),
  })

  const status = statusQuery.data
  const preview = previewQuery.data
  const countKeys = useMemo(() => {
    if (!preview) return [] as string[]
    return Array.from(
      new Set([...Object.keys(preview.current_counts), ...Object.keys(preview.backup_counts)]),
    ).sort()
  }, [preview])

  return (
    <div className="space-y-4">
      {/* Üst bilgi ve işlemler */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500 dark:text-slate-400">{t('backup.subtitle')}</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary btn-sm" onClick={refreshBackups}>
            <RefreshCw className="h-4 w-4" />
            {t('common.refresh')}
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => setFolderOpen(true)}
          >
            <FolderOpen className="h-4 w-4" />
            {t('backup.openFolder')}
          </button>
          {canCreate && (
            <>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => setCleanupOpen(true)}
              >
                <Trash2 className="h-4 w-4" />
                {t('backup.cleanup')}
              </button>
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={() => setCreateOpen(true)}
              >
                <Archive className="h-4 w-4" />
                {t('backup.backupNow')}
              </button>
            </>
          )}
        </div>
      </div>

      <Alert tone="info" title={t('backup.note')}>
        {t('backup.secretsExcluded')}
      </Alert>

      {statusQuery.isLoading && <LoadingState />}
      {statusQuery.error && (
        <ErrorState error={statusQuery.error} onRetry={statusQuery.refetch} />
      )}

      {status && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              label={t('backup.lastBackup')}
              value={status.last_backup_at ? formatRelative(status.last_backup_at) : '—'}
              hint={status.last_backup_at ? formatDateTime(status.last_backup_at) : undefined}
              icon={<Archive className="h-5 w-5" />}
              tone={status.last_backup_at ? 'brand' : 'warning'}
            />
            <StatCard
              label={t('backup.lastSuccessful')}
              value={
                status.last_successful_backup_at
                  ? formatRelative(status.last_successful_backup_at)
                  : '—'
              }
              hint={
                status.last_successful_backup_at
                  ? formatDateTime(status.last_successful_backup_at)
                  : undefined
              }
              icon={<CheckCircle2 className="h-5 w-5" />}
              tone={status.last_successful_backup_at ? 'success' : 'danger'}
            />
            <StatCard
              label={t('backup.backupSize')}
              value={
                status.last_backup_size_mb !== null && status.last_backup_size_mb !== undefined
                  ? formatFileSize(status.last_backup_size_mb * 1024 * 1024)
                  : '—'
              }
              hint={`${t('common.total')}: ${formatFileSize(status.total_size_mb * 1024 * 1024)}`}
              icon={<HardDrive className="h-5 w-5" />}
            />
            <StatCard
              label={t('backup.totalBackups')}
              value={formatNumber(status.total_backup_count)}
              hint={t('backup.backupStatus')}
              icon={<Archive className="h-5 w-5" />}
            />
            <StatCard
              label={t('backup.protected')}
              value={formatNumber(status.protected_count)}
              hint={t('backup.protectedHint')}
              icon={<ShieldCheck className="h-5 w-5" />}
              tone={status.protected_count > 0 ? 'success' : 'neutral'}
            />
            <StatCard
              label={t('backup.nextBackup')}
              value={status.next_backup_at ? formatDateTime(status.next_backup_at) : '—'}
              hint={status.schedule_cron ?? undefined}
              icon={<RefreshCw className="h-5 w-5" />}
              tone={status.schedule_enabled ? 'brand' : 'neutral'}
            />
          </div>

          <Card title={t('backup.backupLocation')}>
            <CopyBox value={status.backup_location} />
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span>{t('backup.backupStatus')}:</span>
              <StatusBadge
                status={status.status}
                label={t(`backup.statuses.${status.status}`, status.status)}
              />
            </div>
          </Card>
        </>
      )}

      {/* Yedekleme ayarları */}
      <Card title={t('backup.settings')}>
        {settingsQuery.isLoading ? (
          <LoadingState />
        ) : settingsQuery.error ? (
          <ErrorState error={settingsQuery.error} onRetry={settingsQuery.refetch} />
        ) : settingsQuery.data ? (
          <div className="grid gap-x-6 sm:grid-cols-2">
            <InfoRow
              label={t('backup.scheduleEnabled')}
              value={
                <Badge tone={settingsQuery.data.schedule_enabled ? 'success' : 'neutral'}>
                  {settingsQuery.data.schedule_enabled ? t('common.active') : t('common.passive')}
                </Badge>
              }
            />
            <InfoRow
              label={t('backup.scheduleCron')}
              value={<code className="text-xs">{settingsQuery.data.schedule_cron}</code>}
            />
            <InfoRow
              label={t('backup.retentionDaily')}
              value={formatNumber(settingsQuery.data.retention_daily)}
            />
            <InfoRow
              label={t('backup.retentionWeekly')}
              value={formatNumber(settingsQuery.data.retention_weekly)}
            />
            <InfoRow
              label={t('backup.retentionMonthly')}
              value={formatNumber(settingsQuery.data.retention_monthly)}
            />
            <InfoRow
              label={t('backup.backupLocation')}
              value={<code className="text-xs break-all">{settingsQuery.data.backup_dir}</code>}
            />
          </div>
        ) : null}
      </Card>

      {/* Yedek listesi */}
      <Card title={t('backup.title')} bodyClassName="p-0">
        {listQuery.isLoading ? (
          <LoadingState />
        ) : listQuery.error ? (
          <ErrorState error={listQuery.error} onRetry={listQuery.refetch} />
        ) : !listQuery.data || listQuery.data.length === 0 ? (
          <EmptyState
            title={t('common.noData')}
            description={t('backup.subtitle')}
            icon={<Archive className="h-6 w-6" />}
          />
        ) : (
          <TableWrapper>
            <thead>
              <tr>
                <th>{t('backup.title')}</th>
                <th>{t('lesson.type')}</th>
                <th>{t('common.status')}</th>
                <th>{t('backup.backupSize')}</th>
                <th className="hidden lg:table-cell">{t('common.date')}</th>
                <th className="hidden xl:table-cell">{t('backup.integrityCheck')}</th>
                <th className="text-right">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {listQuery.data.map((record) => (
                <tr key={record.id}>
                  <td>
                    <span className="font-mono text-xs text-slate-800 dark:text-slate-100">
                      {record.backup_id}
                    </span>
                    {record.is_protected && (
                      <span className="ml-2 inline-flex align-middle">
                        <Badge tone="success">{t('backup.protected')}</Badge>
                      </span>
                    )}
                    <span className="mt-0.5 block truncate text-xs text-slate-500 dark:text-slate-400">
                      {record.file_name}
                    </span>
                  </td>
                  <td className="whitespace-nowrap text-xs">
                    {t(`backup.types.${record.backup_type}`, record.backup_type)}
                  </td>
                  <td>
                    <StatusBadge
                      status={record.status}
                      label={t(`backup.statuses.${record.status}`, record.status)}
                    />
                  </td>
                  <td className="whitespace-nowrap text-sm">{formatFileSize(record.size_bytes)}</td>
                  <td className="hidden lg:table-cell whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                    {formatDateTime(record.created_at)}
                  </td>
                  <td className="hidden xl:table-cell max-w-[220px] text-xs text-slate-500 dark:text-slate-400">
                    {record.verification_message ?? record.error_message ?? '—'}
                    {record.verified_at && (
                      <span className="mt-0.5 block text-[11px] text-slate-400">
                        {formatDateTime(record.verified_at)}
                      </span>
                    )}
                  </td>
                  <td>
                    <div className="flex flex-wrap items-center justify-end gap-1">
                      <button
                        type="button"
                        className="btn-ghost btn-sm"
                        disabled={verifyMutation.isPending}
                        onClick={() => verifyMutation.mutate(record.backup_id)}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        {t('backup.verify')}
                      </button>
                      {canRestore && (
                        <button
                          type="button"
                          className="btn-ghost btn-sm"
                          onClick={() => {
                            setRestoreConfirmed(false)
                            setSafetyBackup(true)
                            setRestoreTarget(record.backup_id)
                          }}
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          {t('backup.restore')}
                        </button>
                      )}
                      {canCreate && (
                        <>
                          <button
                            type="button"
                            className="btn-ghost btn-sm"
                            disabled={protectMutation.isPending}
                            onClick={() =>
                              protectMutation.mutate({
                                backupId: record.backup_id,
                                protect: !record.is_protected,
                              })
                            }
                          >
                            <ShieldCheck className="h-3.5 w-3.5" />
                            {record.is_protected ? t('backup.unprotect') : t('backup.protect')}
                          </button>
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 disabled:opacity-40 dark:text-rose-400"
                            disabled={record.is_protected}
                            title={record.is_protected ? t('backup.protectedHint') : t('common.delete')}
                            onClick={() => setDeleteTarget(record)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </TableWrapper>
        )}
      </Card>

      {/* Geri yükleme geçmişi */}
      <Card title={t('backup.restoreHistory')} bodyClassName="p-0">
        {historyQuery.isLoading ? (
          <LoadingState />
        ) : historyQuery.error ? (
          <ErrorState error={historyQuery.error} onRetry={historyQuery.refetch} />
        ) : !historyQuery.data || historyQuery.data.length === 0 ? (
          <EmptyState title={t('common.noData')} icon={<RotateCcw className="h-6 w-6" />} />
        ) : (
          <TableWrapper>
            <thead>
              <tr>
                <th>{t('backup.title')}</th>
                <th>{t('common.status')}</th>
                <th className="hidden md:table-cell">{t('backup.safetyBackup')}</th>
                <th>{t('common.details')}</th>
                <th className="hidden lg:table-cell">{t('common.date')}</th>
              </tr>
            </thead>
            <tbody>
              {historyQuery.data.map((row) => (
                <tr key={row.id}>
                  <td className="font-mono text-xs">{row.backup_id}</td>
                  <td>
                    <StatusBadge
                      status={row.status}
                      label={t(`backup.statuses.${row.status}`, row.status)}
                    />
                  </td>
                  <td className="hidden md:table-cell font-mono text-xs text-slate-500 dark:text-slate-400">
                    {row.safety_backup_id ?? '—'}
                  </td>
                  <td className="max-w-[280px] text-xs text-slate-600 dark:text-slate-300">
                    {row.message ?? '—'}
                  </td>
                  <td className="hidden lg:table-cell whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                    {formatDateTime(row.started_at)}
                    {row.finished_at && (
                      <span className="mt-0.5 block text-[11px] text-slate-400">
                        {formatDateTime(row.finished_at)}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableWrapper>
        )}
      </Card>

      {/* Yeni yedek modalı */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title={t('backup.backupNow')}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setCreateOpen(false)}>
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? t('backup.creating') : t('backup.backupNow')}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label={t('lesson.type')} required>
            <select
              className="select"
              value={createForm.backup_type}
              onChange={(event) =>
                setCreateForm((previous) => ({ ...previous, backup_type: event.target.value }))
              }
            >
              {BACKUP_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`backup.types.${type}`, type)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('backup.note')}>
            <textarea
              className="textarea"
              rows={2}
              value={createForm.note}
              onChange={(event) =>
                setCreateForm((previous) => ({ ...previous, note: event.target.value }))
              }
            />
          </Field>
          <ToggleRow
            label={t('backup.includeUploads')}
            checked={createForm.include_uploads}
            onChange={(value) =>
              setCreateForm((previous) => ({ ...previous, include_uploads: value }))
            }
          />
          <ToggleRow
            label={t('backup.includeLogs')}
            checked={createForm.include_logs}
            onChange={(value) => setCreateForm((previous) => ({ ...previous, include_logs: value }))}
          />
          <ToggleRow
            label={t('backup.protect')}
            hint={t('backup.protectedHint')}
            checked={createForm.protect}
            onChange={(value) => setCreateForm((previous) => ({ ...previous, protect: value }))}
          />
          <Alert tone="info">{t('backup.secretsExcluded')}</Alert>
        </div>
      </Modal>

      {/* Temizleme onayı */}
      <ConfirmDialog
        open={cleanupOpen}
        onClose={() => setCleanupOpen(false)}
        onConfirm={() => cleanupMutation.mutate()}
        title={t('backup.cleanup')}
        message={t('backup.protectedHint')}
        confirmLabel={t('backup.cleanup')}
        loading={cleanupMutation.isPending}
      />

      {/* Silme onayı */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.backup_id)
        }}
        title={t('common.delete')}
        message={deleteTarget?.file_name ?? ''}
        confirmLabel={t('common.delete')}
        loading={deleteMutation.isPending}
      />

      {/* Klasör bilgisi */}
      <Modal
        open={folderOpen}
        onClose={() => setFolderOpen(false)}
        title={t('backup.openFolder')}
      >
        {locationQuery.isLoading ? (
          <LoadingState />
        ) : locationQuery.error ? (
          <ErrorState error={locationQuery.error} onRetry={locationQuery.refetch} />
        ) : locationQuery.data ? (
          <div className="space-y-4">
            <CopyBox value={locationQuery.data.path} />
            <div>
              <InfoRow
                label={t('common.status')}
                value={
                  <Badge tone={locationQuery.data.exists ? 'success' : 'danger'}>
                    {locationQuery.data.exists ? t('common.active') : t('common.none')}
                  </Badge>
                }
              />
              <InfoRow
                label={t('backup.totalBackups')}
                value={formatNumber(locationQuery.data.file_count)}
              />
              <InfoRow
                label={t('common.total')}
                value={formatFileSize(locationQuery.data.total_size_mb * 1024 * 1024)}
              />
            </div>
            {locationQuery.data.recent_files.length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {t('common.details')}
                </p>
                <ul className="space-y-1">
                  {locationQuery.data.recent_files.map((name) => (
                    <li
                      key={name}
                      className="truncate rounded bg-slate-50 px-2 py-1 font-mono text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-300"
                    >
                      {name}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}
      </Modal>

      {/* Doğrulama sonucu */}
      <Modal
        open={verifyResult !== null}
        onClose={() => setVerifyResult(null)}
        title={t('backup.integrityCheck')}
      >
        {verifyResult && (
          <div className="space-y-4">
            <Alert
              tone={verifyResult.is_valid ? 'success' : 'danger'}
              title={verifyResult.backup_id}
            >
              {verifyResult.message}
            </Alert>
            {verifyResult.checks.length === 0 ? (
              <EmptyState title={t('common.noData')} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('backup.checks')}</th>
                    <th>{t('common.status')}</th>
                    <th>{t('common.details')}</th>
                  </tr>
                </thead>
                <tbody>
                  {verifyResult.checks.map((check) => (
                    <tr key={check.check}>
                      <td className="font-mono text-xs">{check.check}</td>
                      <td>
                        <ResultBadge result={check.result} />
                      </td>
                      <td className="max-w-[260px] break-words text-xs text-slate-500 dark:text-slate-400">
                        {check.detail ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </div>
        )}
      </Modal>

      {/* Geri yükleme önizlemesi */}
      <Modal
        open={restoreTarget !== null}
        onClose={() => {
          setRestoreTarget(null)
          setRestoreConfirmed(false)
        }}
        title={t('backup.restorePreview')}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setRestoreTarget(null)
                setRestoreConfirmed(false)
              }}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-danger"
              disabled={!restoreConfirmed || restoreMutation.isPending || !preview}
              onClick={() => {
                if (restoreTarget) restoreMutation.mutate(restoreTarget)
              }}
            >
              <RotateCcw className="h-4 w-4" />
              {restoreMutation.isPending ? t('backup.restoring') : t('backup.restore')}
            </button>
          </>
        }
      >
        {previewQuery.isLoading ? (
          <LoadingState />
        ) : previewQuery.error ? (
          <ErrorState error={previewQuery.error} onRetry={previewQuery.refetch} />
        ) : preview ? (
          <div className="space-y-4">
            <Alert tone="danger" title={t('backup.restoreWarning')}>
              {preview.backup_id} · {formatDateTime(preview.backup_created_at)}
            </Alert>

            <div className="grid gap-x-6 sm:grid-cols-2">
              <InfoRow
                label={t('settings.version')}
                value={preview.backup_app_version ?? '—'}
              />
              <InfoRow
                label={t('settings.databaseVersion')}
                value={
                  <span className="flex items-center justify-end gap-2">
                    <code className="text-xs">{preview.backup_db_revision ?? '—'}</code>
                    <Badge tone={preview.revision_compatible ? 'success' : 'danger'}>
                      {preview.current_db_revision ?? '—'}
                    </Badge>
                  </span>
                }
              />
              <InfoRow
                label={t('backup.integrityCheck')}
                value={
                  <Badge tone={preview.integrity_ok ? 'success' : 'danger'}>
                    {preview.integrity_ok
                      ? t('backup.statuses.verified')
                      : t('backup.statuses.corrupted')}
                  </Badge>
                }
              />
            </div>

            {preview.warnings.length > 0 && (
              <div className="rounded-lg border border-rose-300 bg-rose-50 p-3 dark:border-rose-800 dark:bg-rose-900/20">
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-rose-700 dark:text-rose-300">
                  {t('common.warning')}
                </p>
                <ul className="list-disc space-y-1 pl-5 text-sm text-rose-700 dark:text-rose-300">
                  {preview.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {countKeys.length === 0 ? (
              <EmptyState title={t('common.noData')} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('audit.entity')}</th>
                    <th className="text-right">{t('backup.currentCounts')}</th>
                    <th className="text-right">{t('backup.backupCounts')}</th>
                    <th className="text-right">{t('backup.differences')}</th>
                  </tr>
                </thead>
                <tbody>
                  {countKeys.map((key) => {
                    const currentCount = preview.current_counts[key] ?? 0
                    const backupCount = preview.backup_counts[key] ?? 0
                    const difference = preview.differences[key] ?? backupCount - currentCount
                    return (
                      <tr key={key}>
                        <td className="font-mono text-xs">{key}</td>
                        <td className="text-right text-sm">{formatNumber(currentCount)}</td>
                        <td className="text-right text-sm">{formatNumber(backupCount)}</td>
                        <td
                          className={
                            difference < 0
                              ? 'text-right text-sm font-medium text-rose-600 dark:text-rose-400'
                              : difference > 0
                                ? 'text-right text-sm font-medium text-emerald-600 dark:text-emerald-400'
                                : 'text-right text-sm text-slate-500'
                          }
                        >
                          {difference > 0 ? '+' : ''}
                          {formatNumber(difference)}
                          {difference < 0 && (
                            <span className="ml-1 text-[11px] uppercase">
                              {t('backup.willBeLost')}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </TableWrapper>
            )}

            <ToggleRow
              label={t('backup.safetyBackup')}
              hint={t('backup.safetyBackupHint')}
              checked={safetyBackup}
              onChange={setSafetyBackup}
            />

            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-rose-300 bg-rose-50 p-3 dark:border-rose-800 dark:bg-rose-900/20">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 shrink-0 accent-rose-500"
                checked={restoreConfirmed}
                onChange={(event) => setRestoreConfirmed(event.target.checked)}
              />
              <span className="text-sm text-rose-800 dark:text-rose-200">
                {t('backup.restoreWarning')}
              </span>
            </label>
          </div>
        ) : null}
      </Modal>

      {/* Geri yükleme sonucu */}
      <Modal
        open={restoreResult !== null}
        onClose={() => setRestoreResult(null)}
        title={t('backup.restoreSteps')}
      >
        {restoreResult && (
          <div className="space-y-4">
            <Alert
              tone={restoreResult.success ? 'success' : 'danger'}
              title={restoreResult.backup_id}
            >
              {restoreResult.message}
            </Alert>
            {restoreResult.rolled_back && (
              <Alert tone="warning">{t('backup.rolledBack')}</Alert>
            )}
            {restoreResult.safety_backup_id && (
              <InfoRow
                label={t('backup.safetyBackup')}
                value={<code className="text-xs">{restoreResult.safety_backup_id}</code>}
              />
            )}
            {restoreResult.steps.length === 0 ? (
              <EmptyState title={t('common.noData')} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('aiDeveloper.steps')}</th>
                    <th>{t('common.status')}</th>
                    <th>{t('common.details')}</th>
                  </tr>
                </thead>
                <tbody>
                  {restoreResult.steps.map((step, index) => (
                    <tr key={`${step.step}-${index}`}>
                      <td className="font-mono text-xs">{step.step}</td>
                      <td>
                        <ResultBadge result={step.status} />
                      </td>
                      <td className="max-w-[260px] break-words text-xs text-slate-500 dark:text-slate-400">
                        {step.detail ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Kullanıcılar
// ---------------------------------------------------------------------------
interface UserFormState {
  full_name: string
  email: string
  password: string
  phone: string
  language: string
  is_active: boolean
  must_change_password: boolean
  role_codes: string[]
}

const EMPTY_USER_FORM: UserFormState = {
  full_name: '',
  email: '',
  password: '',
  phone: '',
  language: 'tr',
  is_active: true,
  must_change_password: true,
  role_codes: [],
}

function RoleSelector({
  groups,
  selected,
  onChange,
}: {
  groups: Record<string, RoleCatalogEntry[]>
  selected: string[]
  onChange: (codes: string[]) => void
}) {
  const { t } = useTranslation()

  function toggle(code: string) {
    onChange(selected.includes(code) ? selected.filter((item) => item !== code) : [...selected, code])
  }

  return (
    <div className="space-y-3">
      {Object.entries(groups).map(([group, roles]) => (
        <div key={group}>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t(`users.roleGroups.${group}`, group)}
          </p>
          <div className="grid gap-1.5 sm:grid-cols-2">
            {roles.map((role) => (
              <label
                key={role.code}
                className="flex cursor-pointer items-center gap-2 rounded-md border border-slate-200 px-2.5 py-1.5 dark:border-slate-700"
              >
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 shrink-0 accent-brand-500"
                  checked={selected.includes(role.code)}
                  onChange={() => toggle(role.code)}
                />
                <span className="truncate text-sm text-slate-700 dark:text-slate-200">
                  {role.label}
                </span>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function UsersTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const can = useAuth((state) => state.can)
  const canWrite = can('user:write')
  const canDelete = can('user:delete')

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [query, setQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState('')

  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<User | null>(null)
  const [resetTarget, setResetTarget] = useState<User | null>(null)
  const [deactivateTarget, setDeactivateTarget] = useState<User | null>(null)
  const [form, setForm] = useState<UserFormState>(EMPTY_USER_FORM)
  const [resetForm, setResetForm] = useState({ new_password: '', must_change_password: true })

  const catalogQuery = useQuery({
    queryKey: ['users', 'roles-catalog'],
    queryFn: () => get<RoleCatalog>('/users/roles/catalog'),
    staleTime: 10 * 60_000,
  })

  const usersQuery = useQuery({
    queryKey: ['users', page, pageSize, query, roleFilter, activeFilter],
    queryFn: () =>
      get<Page<User>>('/users', {
        page,
        page_size: pageSize,
        q: query || undefined,
        role: roleFilter || undefined,
        is_active: activeFilter === '' ? undefined : activeFilter === 'true',
      }),
  })

  function refreshUsers() {
    void queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  const createMutation = useMutation({
    mutationFn: () =>
      post<User>('/users', {
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        phone: form.phone || null,
        language: form.language,
        role_codes: form.role_codes,
        is_active: form.is_active,
        must_change_password: form.must_change_password,
      }),
    onSuccess: () => {
      setCreateOpen(false)
      setForm(EMPTY_USER_FORM)
      refreshUsers()
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const editMutation = useMutation({
    mutationFn: (payload: { userId: number; body: Record<string, unknown> }) =>
      patch<User>(`/users/${payload.userId}`, payload.body),
    onSuccess: () => {
      setEditTarget(null)
      refreshUsers()
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const deactivateMutation = useMutation({
    mutationFn: (userId: number) => del<Message>(`/users/${userId}`),
    onSuccess: (result) => {
      setDeactivateTarget(null)
      refreshUsers()
      toastSuccess(result.message)
    },
    onError: (error) => toastError(error),
  })

  const resetMutation = useMutation({
    mutationFn: (userId: number) =>
      post<Message>('/users/reset-password', {
        user_id: userId,
        new_password: resetForm.new_password,
        must_change_password: resetForm.must_change_password,
      }),
    onSuccess: (result) => {
      setResetTarget(null)
      setResetForm({ new_password: '', must_change_password: true })
      toastSuccess(result.message)
    },
    onError: (error) => toastError(error),
  })

  const roleOptions = useMemo(() => {
    if (!catalogQuery.data) return [] as RoleCatalogEntry[]
    return Object.values(catalogQuery.data.groups).flat()
  }, [catalogQuery.data])

  function openEdit(user: User) {
    setForm({
      full_name: user.full_name,
      email: user.email,
      password: '',
      phone: user.phone ?? '',
      language: user.language,
      is_active: user.is_active,
      must_change_password: user.must_change_password,
      role_codes: user.roles.map((role) => role.code),
    })
    setEditTarget(user)
  }

  return (
    <div className="space-y-4">
      <Card
        title={t('users.title')}
        actions={
          canWrite ? (
            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={() => {
                setForm(EMPTY_USER_FORM)
                setCreateOpen(true)
              }}
            >
              <Plus className="h-4 w-4" />
              {t('users.new')}
            </button>
          ) : undefined
        }
        bodyClassName="p-0"
      >
        <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-4 dark:border-slate-700">
          <Field label={t('common.search')}>
            <input
              className="input"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setPage(1)
              }}
            />
          </Field>
          <Field label={t('users.roles')}>
            <select
              className="select"
              value={roleFilter}
              onChange={(event) => {
                setRoleFilter(event.target.value)
                setPage(1)
              }}
            >
              <option value="">{t('common.all')}</option>
              {roleOptions.map((role) => (
                <option key={role.code} value={role.code}>
                  {role.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('common.status')}>
            <select
              className="select"
              value={activeFilter}
              onChange={(event) => {
                setActiveFilter(event.target.value)
                setPage(1)
              }}
            >
              <option value="">{t('common.all')}</option>
              <option value="true">{t('common.active')}</option>
              <option value="false">{t('common.passive')}</option>
            </select>
          </Field>
          <div className="flex items-end">
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                setQuery('')
                setRoleFilter('')
                setActiveFilter('')
                setPage(1)
              }}
            >
              {t('common.clearFilters')}
            </button>
          </div>
        </div>

        {usersQuery.isLoading ? (
          <LoadingState />
        ) : usersQuery.error ? (
          <ErrorState error={usersQuery.error} onRetry={usersQuery.refetch} />
        ) : !usersQuery.data || usersQuery.data.items.length === 0 ? (
          <EmptyState title={t('common.noResults')} icon={<UsersIcon className="h-6 w-6" />} />
        ) : (
          <>
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('users.fullName')}</th>
                  <th>{t('common.email')}</th>
                  <th className="hidden md:table-cell">{t('users.roles')}</th>
                  <th>{t('users.isActive')}</th>
                  <th className="hidden lg:table-cell">{t('auth.lastLogin')}</th>
                  <th className="text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {usersQuery.data.items.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <span className="font-medium text-slate-800 dark:text-slate-100">
                        {user.full_name}
                      </span>
                      {user.is_superuser && (
                        <span className="ml-2 inline-flex align-middle">
                          <Badge tone="warning">{t('users.isSuperuser')}</Badge>
                        </span>
                      )}
                    </td>
                    <td className="text-xs text-slate-500 dark:text-slate-400">{user.email}</td>
                    <td className="hidden md:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {user.roles.length === 0 ? (
                          <span className="text-xs text-slate-400">{t('common.none')}</span>
                        ) : (
                          user.roles.map((role) => (
                            <Badge key={role.id} tone="info">
                              {role.name_tr}
                            </Badge>
                          ))
                        )}
                      </div>
                    </td>
                    <td>
                      <Badge tone={user.is_active ? 'success' : 'neutral'}>
                        {user.is_active ? t('common.active') : t('common.passive')}
                      </Badge>
                    </td>
                    <td className="hidden lg:table-cell whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                      {user.last_login_at ? formatDateTime(user.last_login_at) : '—'}
                    </td>
                    <td>
                      <div className="flex flex-wrap items-center justify-end gap-1">
                        {canWrite && (
                          <>
                            <button
                              type="button"
                              className="btn-ghost btn-sm"
                              onClick={() => openEdit(user)}
                            >
                              {t('common.edit')}
                            </button>
                            <button
                              type="button"
                              className="btn-ghost btn-sm"
                              onClick={() => {
                                setResetForm({ new_password: '', must_change_password: true })
                                setResetTarget(user)
                              }}
                            >
                              <KeyRound className="h-3.5 w-3.5" />
                              {t('users.resetPassword')}
                            </button>
                          </>
                        )}
                        {canDelete && user.is_active && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            onClick={() => setDeactivateTarget(user)}
                          >
                            {t('users.deactivate')}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={usersQuery.data.total}
              onPageChange={setPage}
              onPageSizeChange={(size) => {
                setPageSize(size)
                setPage(1)
              }}
            />
          </>
        )}
      </Card>

      {/* Yeni / düzenle modalı */}
      <Modal
        open={createOpen || editTarget !== null}
        onClose={() => {
          setCreateOpen(false)
          setEditTarget(null)
        }}
        title={editTarget ? t('common.edit') : t('users.new')}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setCreateOpen(false)
                setEditTarget(null)
              }}
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={
                createMutation.isPending ||
                editMutation.isPending ||
                form.full_name.trim().length < 2 ||
                (!editTarget && (form.email.trim() === '' || form.password.length < 8))
              }
              onClick={() => {
                if (editTarget) {
                  editMutation.mutate({
                    userId: editTarget.id,
                    body: {
                      full_name: form.full_name,
                      phone: form.phone || null,
                      language: form.language,
                      is_active: form.is_active,
                      role_codes: form.role_codes,
                    },
                  })
                } else {
                  createMutation.mutate()
                }
              }}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('users.fullName')} required>
              <input
                className="input"
                value={form.full_name}
                onChange={(event) =>
                  setForm((previous) => ({ ...previous, full_name: event.target.value }))
                }
              />
            </Field>
            <Field label={t('common.email')} required>
              <input
                type="email"
                className="input"
                value={form.email}
                disabled={editTarget !== null}
                onChange={(event) =>
                  setForm((previous) => ({ ...previous, email: event.target.value }))
                }
              />
            </Field>
            {!editTarget && (
              <Field label={t('auth.password')} required hint={t('common.required')}>
                <input
                  type="password"
                  className="input"
                  minLength={8}
                  value={form.password}
                  onChange={(event) =>
                    setForm((previous) => ({ ...previous, password: event.target.value }))
                  }
                />
              </Field>
            )}
            <Field label={t('common.phone')}>
              <input
                className="input"
                value={form.phone}
                onChange={(event) =>
                  setForm((previous) => ({ ...previous, phone: event.target.value }))
                }
              />
            </Field>
            <Field label={t('settings.language')}>
              <select
                className="select"
                value={form.language}
                onChange={(event) =>
                  setForm((previous) => ({ ...previous, language: event.target.value }))
                }
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <ToggleRow
            label={t('users.isActive')}
            checked={form.is_active}
            onChange={(value) => setForm((previous) => ({ ...previous, is_active: value }))}
          />
          {!editTarget && (
            <ToggleRow
              label={t('users.mustChangePassword')}
              checked={form.must_change_password}
              onChange={(value) =>
                setForm((previous) => ({ ...previous, must_change_password: value }))
              }
            />
          )}

          <div>
            <p className="label">{t('users.roles')}</p>
            {catalogQuery.isLoading ? (
              <LoadingState />
            ) : catalogQuery.data ? (
              <RoleSelector
                groups={catalogQuery.data.groups}
                selected={form.role_codes}
                onChange={(codes) => setForm((previous) => ({ ...previous, role_codes: codes }))}
              />
            ) : (
              <EmptyState title={t('common.noData')} />
            )}
          </div>
        </div>
      </Modal>

      {/* Parola sıfırlama */}
      <Modal
        open={resetTarget !== null}
        onClose={() => setResetTarget(null)}
        title={t('users.resetPassword')}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setResetTarget(null)}>
              {t('common.cancel')}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={resetMutation.isPending || resetForm.new_password.length < 8}
              onClick={() => {
                if (resetTarget) resetMutation.mutate(resetTarget.id)
              }}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <InfoRow label={t('users.fullName')} value={resetTarget?.full_name ?? ''} />
          <Field label={t('auth.newPassword')} required>
            <input
              type="password"
              className="input"
              minLength={8}
              value={resetForm.new_password}
              onChange={(event) =>
                setResetForm((previous) => ({ ...previous, new_password: event.target.value }))
              }
            />
          </Field>
          <ToggleRow
            label={t('users.mustChangePassword')}
            checked={resetForm.must_change_password}
            onChange={(value) =>
              setResetForm((previous) => ({ ...previous, must_change_password: value }))
            }
          />
        </div>
      </Modal>

      <ConfirmDialog
        open={deactivateTarget !== null}
        onClose={() => setDeactivateTarget(null)}
        onConfirm={() => {
          if (deactivateTarget) deactivateMutation.mutate(deactivateTarget.id)
        }}
        title={t('users.deactivate')}
        message={deactivateTarget?.email ?? ''}
        confirmLabel={t('users.deactivate')}
        loading={deactivateMutation.isPending}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Denetim kaydı
// ---------------------------------------------------------------------------
function AuditTab() {
  const { t } = useTranslation()

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [userId, setUserId] = useState('')
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [days, setDays] = useState(30)
  const [expanded, setExpanded] = useState<number | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['audit', page, pageSize, userId, action, entityType, days],
    queryFn: () =>
      get<Page<AuditLog>>('/audit', {
        page,
        page_size: pageSize,
        user_id: userId ? Number(userId) : undefined,
        action: action || undefined,
        entity_type: entityType || undefined,
        days,
      }),
  })

  return (
    <Card title={t('audit.title')} bodyClassName="p-0">
      <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-5 dark:border-slate-700">
        <Field label={t('audit.user')}>
          <input
            type="number"
            min={1}
            className="input"
            value={userId}
            onChange={(event) => {
              setUserId(event.target.value)
              setPage(1)
            }}
          />
        </Field>
        <Field label={t('audit.action')}>
          <select
            className="select"
            value={action}
            onChange={(event) => {
              setAction(event.target.value)
              setPage(1)
            }}
          >
            <option value="">{t('common.all')}</option>
            {AUDIT_ACTIONS.map((code) => (
              <option key={code} value={code}>
                {t(`audit.actions.${code}`, code)}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('audit.entity')}>
          <input
            className="input"
            value={entityType}
            onChange={(event) => {
              setEntityType(event.target.value)
              setPage(1)
            }}
          />
        </Field>
        <Field label={t('membership.durationDays')}>
          <select
            className="select"
            value={days}
            onChange={(event) => {
              setDays(Number(event.target.value))
              setPage(1)
            }}
          >
            {DAY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>
        <div className="flex items-end">
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => {
              setUserId('')
              setAction('')
              setEntityType('')
              setDays(30)
              setPage(1)
            }}
          >
            {t('common.clearFilters')}
          </button>
        </div>
      </div>

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState title={t('common.noResults')} icon={<ScrollText className="h-6 w-6" />} />
      ) : (
        <>
          <TableWrapper>
            <thead>
              <tr>
                <th className="w-8" aria-label={t('common.details')} />
                <th>{t('audit.occurredAt')}</th>
                <th>{t('audit.user')}</th>
                <th>{t('audit.action')}</th>
                <th className="hidden md:table-cell">{t('audit.entity')}</th>
                <th className="hidden lg:table-cell">{t('audit.summary')}</th>
                <th className="hidden xl:table-cell">{t('audit.ipAddress')}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => {
                const hasChanges = Object.keys(row.changes ?? {}).length > 0
                const isOpen = expanded === row.id
                return (
                  <Fragment key={row.id}>
                    <tr>
                      <td>
                        {hasChanges && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm"
                            aria-label={t('audit.changes')}
                            title={t('audit.changes')}
                            onClick={() => setExpanded(isOpen ? null : row.id)}
                          >
                            {isOpen ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                        )}
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {formatDateTime(row.occurred_at)}
                      </td>
                      <td className="text-xs text-slate-600 dark:text-slate-300">
                        {row.user_email ?? '—'}
                      </td>
                      <td>
                        <Badge tone={row.action === 'delete' ? 'danger' : 'neutral'}>
                          {t(`audit.actions.${row.action}`, row.action)}
                        </Badge>
                      </td>
                      <td className="hidden md:table-cell text-xs">
                        <span className="font-mono text-slate-600 dark:text-slate-300">
                          {row.entity_type}
                        </span>
                        {row.entity_id && (
                          <span className="ml-1 text-slate-400">#{row.entity_id}</span>
                        )}
                      </td>
                      <td className="hidden lg:table-cell max-w-[280px] text-xs text-slate-600 dark:text-slate-300">
                        {row.summary ?? '—'}
                      </td>
                      <td className="hidden xl:table-cell text-xs text-slate-400">
                        {row.ip_address ?? '—'}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={7} className="bg-slate-50 dark:bg-slate-800/50">
                          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {t('audit.changes')}
                          </p>
                          <pre className="max-h-72 overflow-auto rounded-lg bg-white p-3 text-xs leading-relaxed text-slate-700 dark:bg-surface-dark dark:text-slate-200">
                            {JSON.stringify(row.changes, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </TableWrapper>
          <Pagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size)
              setPage(1)
            }}
          />
        </>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Hakkında
// ---------------------------------------------------------------------------
function AboutTab() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)

  const aboutQuery = useQuery({
    queryKey: ['about'],
    queryFn: () => get<AboutInfo>('/about'),
  })
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: () => get<HealthReport>('/health'),
    refetchInterval: 60_000,
  })
  const i18nQuery = useQuery({
    queryKey: ['i18n', 'validate'],
    queryFn: () => get<I18nValidation>('/i18n/validate'),
    enabled: can('settings:read'),
  })

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={t('settings.tabs.about')}>
        {aboutQuery.isLoading ? (
          <LoadingState />
        ) : aboutQuery.error ? (
          <ErrorState error={aboutQuery.error} onRetry={aboutQuery.refetch} />
        ) : aboutQuery.data ? (
          <div>
            <InfoRow label={t('app.name')} value={aboutQuery.data.app_name} />
            <InfoRow label={t('settings.version')} value={aboutQuery.data.version} />
            <InfoRow
              label={t('settings.build')}
              value={<code className="text-xs">{aboutQuery.data.build}</code>}
            />
            <InfoRow
              label={t('settings.gitCommit')}
              value={<code className="text-xs">{aboutQuery.data.git_commit ?? '—'}</code>}
            />
            <InfoRow
              label={t('settings.databaseVersion')}
              value={<code className="text-xs">{aboutQuery.data.database_revision ?? '—'}</code>}
            />
            <InfoRow label={t('settings.databaseEngine')} value={aboutQuery.data.database_engine} />
            <InfoRow label="Python" value={aboutQuery.data.python_version} />
            <InfoRow label={t('settings.platform')} value={aboutQuery.data.platform} />
            <InfoRow label={t('settings.license')} value={aboutQuery.data.license} />
            <InfoRow
              label={t('settings.lastUpdated')}
              value={
                aboutQuery.data.last_updated ? formatDateTime(aboutQuery.data.last_updated) : '—'
              }
            />
          </div>
        ) : null}
      </Card>

      <Card title={t('system.health')}>
        {healthQuery.isLoading ? (
          <LoadingState />
        ) : healthQuery.error ? (
          <ErrorState error={healthQuery.error} onRetry={healthQuery.refetch} />
        ) : healthQuery.data ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full ${HEALTH_DOT[healthQuery.data.status] ?? 'bg-slate-400'}`}
              />
              <span className="text-sm font-medium text-slate-800 dark:text-slate-100">
                {t(`system.statuses.${healthQuery.data.status}`, healthQuery.data.status)}
              </span>
              <span className="ml-auto text-xs text-slate-400">
                {formatDateTime(healthQuery.data.checked_at)}
              </span>
            </div>
            <ul className="space-y-1.5">
              {healthQuery.data.components.map((component) => (
                <li
                  key={component.name}
                  className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700"
                >
                  <span
                    className={`h-2.5 w-2.5 shrink-0 rounded-full ${HEALTH_DOT[component.status] ?? 'bg-slate-400'}`}
                  />
                  <span className="min-w-0 flex-1 truncate text-sm text-slate-700 dark:text-slate-200">
                    {component.name}
                  </span>
                  {component.latency_ms !== null && component.latency_ms !== undefined && (
                    <span className="shrink-0 text-xs text-slate-400">
                      {formatNumber(component.latency_ms)} ms
                    </span>
                  )}
                  <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                    {component.detail ?? t(`system.statuses.${component.status}`, component.status)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Card>

      {can('settings:read') && (
        <Card title={t('settings.language')} className="lg:col-span-2">
          {i18nQuery.isLoading ? (
            <LoadingState />
          ) : i18nQuery.error ? (
            <ErrorState error={i18nQuery.error} onRetry={i18nQuery.refetch} />
          ) : i18nQuery.data ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <Badge tone={i18nQuery.data.is_complete ? 'success' : 'warning'}>
                  {i18nQuery.data.is_complete ? t('common.success') : t('common.warning')}
                </Badge>
                <span className="text-sm text-slate-600 dark:text-slate-300">
                  {formatNumber(i18nQuery.data.total_keys)}
                </span>
              </div>
              {Object.entries(i18nQuery.data.missing).map(([lang, keys]) => (
                <div key={lang}>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    {lang} · {formatNumber(keys.length)}
                  </p>
                  {keys.length === 0 ? (
                    <p className="text-xs text-emerald-600 dark:text-emerald-400">
                      {t('common.success')}
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {keys.map((key) => (
                        <code
                          key={key}
                          className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] text-amber-800 dark:bg-amber-900/30 dark:text-amber-200"
                        >
                          {key}
                        </code>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : null}
        </Card>
      )}
    </div>
  )
}
