/** AI Kontrol Merkezi / AI control center. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  Activity,
  Bot,
  ChevronRight,
  Cloud,
  Gauge,
  History,
  KeyRound,
  MessageSquare,
  Network,
  PlugZap,
  RefreshCw,
  Save,
  Send,
  Server,
  Settings2,
  Sparkles,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import {
  AIPanel,
  Alert,
  Badge,
  Card,
  DataPanel,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  Pagination,
  Spinner,
  StatCard,
  TableWrapper,
  Tabs,
} from '@/components/ui'
import { get, post, put } from '@/lib/api'
import { formatDateTime, formatDecimal, formatNumber, formatRelative } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  AIAnalysisResponse,
  AIControlCenter,
  AITask,
  ConnectionTestReport,
  Message,
  ModelInfo,
  Page,
  PromptTemplate,
  ProviderStatus,
  Student,
  TokenUsage,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Yalnızca bu ekranda kullanılan yardımcı tipler
// ---------------------------------------------------------------------------
interface ProviderHealthResult {
  provider: string
  available: boolean
  latency_ms?: number | null
  model_count?: number | null
  endpoint?: string | null
  error?: string | null
  checked_at: string
}

interface ChatApiResponse {
  content: string
  provider: string
  model: string
  usage: TokenUsage
  duration_ms: number
  fallback_used: boolean
  attempted_providers: string[]
  finish_reason?: string | null
}

interface ChatEntry {
  id: number
  role: 'user' | 'assistant'
  content: string
  provider?: string
  model?: string
  tokens?: number
  durationMs?: number
  fallbackUsed?: boolean
}

interface RoutingProviderHint {
  suggested_model?: string | null
  capability_source: string
  verified: boolean
}

interface RoutingTaskRow {
  task: string
  label: string
  keywords: string[]
  providers: Record<string, RoutingProviderHint>
}

interface RoutingTableResponse {
  tasks: RoutingTaskRow[]
  note_tr: string
  note_en: string
}

interface AIProviderConfigValue {
  enabled: boolean
  base_url?: string | null
  model?: string | null
  api_key_set: boolean
  api_key_masked: string
  timeout?: number | null
  max_tokens?: number | null
  temperature?: number | null
}

interface AIConfigResponse {
  local: AIProviderConfigValue
  nvidia: AIProviderConfigValue
  openai_compat: AIProviderConfigValue
  routing: {
    mode: string
    fallback_chain: string[]
    response_language: string
  }
}

interface ConfigFormState {
  mode: string
  fallback_chain: string[]
  response_language: string
  local_enabled: boolean
  local_base_url: string
  local_model: string
  local_timeout: number
  local_max_tokens: number
  local_temperature: number
  nvidia_enabled: boolean
  nvidia_base_url: string
  nvidia_model: string
}

// ---------------------------------------------------------------------------
// Sabitler — etiketler mevcut çeviri anahtarlarından türetilir
// ---------------------------------------------------------------------------
const ANALYSIS_SCOPES = [
  'student_performance',
  'declining_students',
  'training_suggestion',
  'weakest_stroke',
  'top_improvers',
  'competition_readiness',
  'attendance',
  'finance',
  'retention',
  'instructor_workload',
  'schedule_optimization',
  'free_lanes',
  'payment_risk',
  'general',
]

/** Öğrenci seçimi zorunlu olan kapsamlar */
const STUDENT_SCOPES = ['student_performance', 'training_suggestion', 'weakest_stroke', 'competition_readiness']

const SCOPE_LABEL_KEYS: Record<string, string[]> = {
  student_performance: ['student.singular', 'performance.title'],
  declining_students: ['performance.declining'],
  training_suggestion: ['performance.trainingPlan'],
  weakest_stroke: ['performance.weakestStroke'],
  top_improvers: ['performance.topImprovers'],
  competition_readiness: ['performance.readiness'],
  attendance: ['attendance.title'],
  finance: ['finance.title'],
  retention: ['statistics.retentionRate'],
  instructor_workload: ['instructor.singular', 'instructor.workload'],
  schedule_optimization: ['calendar.title'],
  free_lanes: ['lane.free', 'lane.title'],
  payment_risk: ['finance.outstanding'],
  general: ['common.all'],
}

/** Hazır soru kimliğinden analiz kapsamına eşleme */
const PROMPT_SCOPE_MAP: Record<string, string> = {
  instructor_balance: 'instructor_workload',
  retention_analysis: 'retention',
  attendance_analysis: 'attendance',
  weekly_report: 'general',
}

const TASK_KIND_KEYS: Record<string, string> = {
  analysis: 'ai.analysis',
  chat: 'ai.chat',
  developer: 'nav.aiDeveloper',
  caio: 'caio.title',
  report: 'nav.reports',
  health_check: 'system.health',
}

const TASK_STATUS_KEYS: Record<string, string> = {
  pending: 'membership.statuses.pending',
  running: 'training.inProgress',
  success: 'common.success',
  failed: 'backup.statuses.failed',
  cancelled: 'lesson.statuses.cancelled',
}

const TASK_STATUS_TONES: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  pending: 'neutral',
  running: 'info',
  success: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

const TASK_KINDS = ['analysis', 'chat', 'developer', 'caio', 'report', 'health_check']
const TASK_STATUSES = ['pending', 'running', 'success', 'failed', 'cancelled']

// ---------------------------------------------------------------------------
// Metrik gösterimi için saf yardımcılar
// ---------------------------------------------------------------------------
function isPrimitive(value: unknown): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Backend alan adını okunabilir başlığa çevirir (ör. total_students -> Total students) */
function humanizeKey(key: string): string {
  const text = key.replace(/[_.]/g, ' ').trim()
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : key
}

function primitiveText(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? '✓' : '✕'
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '—'
    return Number.isInteger(value) ? formatNumber(value) : formatDecimal(value, 2)
  }
  if (typeof value === 'string') return value.length > 0 ? value : '—'
  return '—'
}

function objectText(value: Record<string, unknown>): string {
  const parts = Object.entries(value)
    .filter(([, item]) => item === null || isPrimitive(item))
    .map(([key, item]) => `${humanizeKey(key)}: ${primitiveText(item)}`)
  return parts.length > 0 ? parts.join(' · ') : '—'
}

function cellText(value: unknown): string {
  if (Array.isArray(value)) {
    if (value.length === 0) return '—'
    if (value.every((item) => item === null || isPrimitive(item))) {
      return value.map((item) => primitiveText(item)).join(', ')
    }
    return value.map((item) => (isPlainObject(item) ? objectText(item) : primitiveText(item))).join(' | ')
  }
  if (isPlainObject(value)) return objectText(value)
  return primitiveText(value)
}

// ---------------------------------------------------------------------------
// Ana sayfa
// ---------------------------------------------------------------------------
export default function AICenterPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const [tab, setTab] = useState('control')

  const centerQuery = useQuery({
    queryKey: ['ai', 'control-center'],
    queryFn: () => get<AIControlCenter>('/ai/control-center'),
    refetchInterval: 90_000,
  })

  const providers = useMemo(() => centerQuery.data?.providers ?? [], [centerQuery.data])
  const canConfigure = can('ai:configure')

  const tabs = useMemo(() => {
    const items = [
      { id: 'control', label: t('ai.controlCenter'), icon: <Gauge className="h-4 w-4" /> },
      { id: 'analysis', label: t('ai.analysis'), icon: <Sparkles className="h-4 w-4" /> },
      { id: 'chat', label: t('ai.chat'), icon: <MessageSquare className="h-4 w-4" /> },
      { id: 'routing', label: t('ai.routing'), icon: <Network className="h-4 w-4" /> },
      { id: 'tasks', label: t('ai.taskHistory'), icon: <History className="h-4 w-4" /> },
    ]
    if (canConfigure) {
      items.push({ id: 'config', label: t('nav.settings'), icon: <Settings2 className="h-4 w-4" /> })
    }
    return items
  }, [t, canConfigure])

  return (
    <>
      <PageHeader
        title={t('ai.title')}
        subtitle={t('ai.subtitle')}
        icon={<Bot className="h-5 w-5" />}
        actions={
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => void centerQuery.refetch()}
            disabled={centerQuery.isFetching}
          >
            {centerQuery.isFetching ? <Spinner /> : <RefreshCw className="h-4 w-4" />}
            {t('common.refresh')}
          </button>
        }
      />

      <Tabs tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'control' && (
        <ControlCenterTab
          data={centerQuery.data}
          isLoading={centerQuery.isLoading}
          error={centerQuery.error}
          onRetry={() => void centerQuery.refetch()}
          canConfigure={canConfigure}
        />
      )}
      {tab === 'analysis' && <AnalysisTab providers={providers} />}
      {tab === 'chat' && <ChatTab providers={providers} />}
      {tab === 'routing' && <RoutingTab />}
      {tab === 'tasks' && <TaskHistoryTab providers={providers} />}
      {tab === 'config' && canConfigure && <ConfigTab />}
    </>
  )
}

// ---------------------------------------------------------------------------
// 1) Kontrol merkezi
// ---------------------------------------------------------------------------
function ControlCenterTab({
  data,
  isLoading,
  error,
  onRetry,
  canConfigure,
}: {
  data?: AIControlCenter
  isLoading: boolean
  error: unknown
  onRetry: () => void
  canConfigure: boolean
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [report, setReport] = useState<ConnectionTestReport | null>(null)
  const [busyProvider, setBusyProvider] = useState<string | null>(null)

  const healthMutation = useMutation({
    mutationFn: (provider: string) => post<ProviderHealthResult>(`/ai/providers/${provider}/health`),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ['ai', 'control-center'] })
      toastSuccess(
        result.available ? t('ai.available') : t('ai.unavailable'),
        result.error ?? (result.latency_ms != null ? `${formatNumber(result.latency_ms)} ms` : undefined),
      )
    },
    onError: (mutationError) => toastError(mutationError),
    onSettled: () => setBusyProvider(null),
  })

  const testMutation = useMutation({
    mutationFn: (provider: string) => post<ConnectionTestReport>(`/ai/providers/${provider}/test`),
    onSuccess: (result) => {
      setReport(result)
      void queryClient.invalidateQueries({ queryKey: ['ai', 'control-center'] })
    },
    onError: (mutationError) => toastError(mutationError),
    onSettled: () => setBusyProvider(null),
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error} onRetry={onRetry} />
  if (!data) return null

  const noProviderAvailable = data.providers.every((provider) => !provider.available)
  const totalTasks = Object.values(data.task_counts).reduce((sum, value) => sum + value, 0)

  return (
    <div className="space-y-4">
      {noProviderAvailable && <Alert tone="warning">{t('ai.systemWorksWithoutAi')}</Alert>}

      {/* Mod ve yedekleme zinciri */}
      <Card title={t('ai.mode')}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={data.mode === 'automatic' ? 'info' : 'success'}>
              {t(`ai.modes.${data.mode}`, data.mode)}
            </Badge>
            {data.local_only_mode && <Badge tone="success">{t('system.localAi')}</Badge>}
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {t('ai.responseLanguage')}:{' '}
              {data.response_language === 'auto'
                ? t('ai.languageAuto')
                : data.response_language === 'en'
                  ? 'English'
                  : 'Türkçe'}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              {t('ai.fallbackChain')}:
            </span>
            {data.fallback_chain.length === 0 ? (
              <span className="text-xs text-slate-400">{t('common.none')}</span>
            ) : (
              data.fallback_chain.map((name, index) => (
                <span key={`${name}-${index}`} className="flex items-center gap-1.5">
                  {index > 0 && <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                    {name}
                  </span>
                </span>
              ))
            )}
          </div>
        </div>
      </Card>

      {/* Sağlayıcı kartları */}
      <div className="grid gap-3 lg:grid-cols-2">
        {data.providers.map((provider) => (
          <ProviderCard
            key={provider.provider}
            provider={provider}
            canConfigure={canConfigure}
            busy={busyProvider === provider.provider}
            healthPending={healthMutation.isPending}
            testPending={testMutation.isPending}
            onHealth={() => {
              setBusyProvider(provider.provider)
              healthMutation.mutate(provider.provider)
            }}
            onTest={() => {
              setBusyProvider(provider.provider)
              testMutation.mutate(provider.provider)
            }}
          />
        ))}
      </div>

      {/* Token kullanımı ve sayaçlar */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={`${t('ai.tokenUsage')} · ${t('ai.todayUsage')}`}
          value={formatNumber(data.usage_today.total_tokens)}
          hint={`${formatNumber(data.usage_today.prompt_tokens)} + ${formatNumber(data.usage_today.completion_tokens)}`}
          icon={<Activity className="h-5 w-5" />}
          tone="brand"
        />
        <StatCard
          label={`${t('ai.tokenUsage')} · ${t('ai.totalUsage')}`}
          value={formatNumber(data.usage_total.total_tokens)}
          hint={`${formatNumber(data.usage_total.prompt_tokens)} + ${formatNumber(data.usage_total.completion_tokens)}`}
          icon={<Activity className="h-5 w-5" />}
          tone="neutral"
        />
        <StatCard
          label={t('ai.taskHistory')}
          value={formatNumber(totalTasks)}
          hint={t('common.total')}
          icon={<History className="h-5 w-5" />}
          tone="neutral"
        />
        <StatCard
          label={t('ai.errors24h')}
          value={formatNumber(data.error_count_24h)}
          icon={<PlugZap className="h-5 w-5" />}
          tone={data.error_count_24h > 0 ? 'danger' : 'success'}
        />
      </div>

      <Card title={t('ai.taskHistory')}>
        {totalTasks === 0 ? (
          <EmptyState title={t('common.noData')} icon={<History className="h-6 w-6" />} />
        ) : (
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.task_counts).map(([status, count]) => (
              <Badge key={status} tone={TASK_STATUS_TONES[status] ?? 'neutral'}>
                {t(TASK_STATUS_KEYS[status] ?? 'common.status', status)}: {formatNumber(count)}
              </Badge>
            ))}
          </div>
        )}
      </Card>

      <TestReportModal report={report} onClose={() => setReport(null)} />
    </div>
  )
}

function ProviderCard({
  provider,
  canConfigure,
  busy,
  healthPending,
  testPending,
  onHealth,
  onTest,
}: {
  provider: ProviderStatus
  canConfigure: boolean
  busy: boolean
  healthPending: boolean
  testPending: boolean
  onHealth: () => void
  onTest: () => void
}) {
  const { t, i18n } = useTranslation()

  const dotClass = !provider.enabled
    ? 'bg-slate-400'
    : provider.available
      ? 'bg-emerald-500'
      : 'bg-rose-500'

  const statusLabel = !provider.enabled
    ? t('ai.disabled')
    : provider.available
      ? t('ai.available')
      : t('ai.unavailable')

  const privacyNote =
    (i18n.language === 'tr' ? provider.privacy_note_tr : provider.privacy_note_en) ??
    (provider.is_local ? t('ai.localPrivacy') : t('ai.cloudPrivacy'))

  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          <span className={clsx('inline-block h-2.5 w-2.5 rounded-full', dotClass)} aria-hidden="true" />
          <h2 className="card-title">{provider.display_name}</h2>
          <Badge tone={!provider.enabled ? 'neutral' : provider.available ? 'success' : 'danger'}>
            {statusLabel}
          </Badge>
        </div>
      }
      actions={
        provider.is_local ? (
          <Server className="h-4 w-4 text-slate-400" aria-label={t('system.localAi')} />
        ) : (
          <Cloud className="h-4 w-4 text-slate-400" aria-label={t('system.cloudAi')} />
        )
      }
    >
      <dl className="grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
        <div className="min-w-0">
          <dt className="text-xs text-slate-500 dark:text-slate-400">{t('ai.endpoint')}</dt>
          <dd className="truncate font-mono text-xs text-slate-700 dark:text-slate-200" title={provider.endpoint ?? ''}>
            {provider.endpoint ?? '—'}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs text-slate-500 dark:text-slate-400">{t('ai.model')}</dt>
          <dd className="truncate text-slate-700 dark:text-slate-200" title={provider.model ?? ''}>
            {provider.model ?? '—'}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500 dark:text-slate-400">{t('ai.latency')}</dt>
          <dd className="text-slate-700 dark:text-slate-200">
            {provider.latency_ms != null ? `${formatNumber(provider.latency_ms)} ms` : '—'}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500 dark:text-slate-400">{t('ai.models')}</dt>
          <dd className="text-slate-700 dark:text-slate-200">
            {provider.model_count != null ? formatNumber(provider.model_count) : '—'}
          </dd>
        </div>
        <div className="min-w-0 sm:col-span-2">
          <dt className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <KeyRound className="h-3.5 w-3.5" />
            {t('ai.apiKey')}
          </dt>
          <dd className="flex flex-wrap items-center gap-2">
            {provider.api_key_set ? (
              <>
                <span className="font-mono text-xs text-slate-700 dark:text-slate-200">
                  {provider.api_key_masked || '••••'}
                </span>
                <Badge tone="success">{t('ai.apiKeySet')}</Badge>
              </>
            ) : (
              <Badge tone="neutral">{t('ai.apiKeyNotSet')}</Badge>
            )}
          </dd>
        </div>
        {provider.last_checked_at && (
          <div className="sm:col-span-2">
            <dt className="text-xs text-slate-500 dark:text-slate-400">{t('ai.lastTest')}</dt>
            <dd className="text-xs text-slate-600 dark:text-slate-300">
              {formatRelative(provider.last_checked_at)} · {formatDateTime(provider.last_checked_at)}
            </dd>
          </div>
        )}
      </dl>

      <p
        className={clsx(
          'mt-3 rounded-lg border px-3 py-2 text-xs',
          provider.is_local
            ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-200'
            : 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-900/20 dark:text-amber-200',
        )}
      >
        {privacyNote}
      </p>

      {provider.error_message && (
        <p className="mt-2 text-xs text-rose-600 dark:text-rose-400">{provider.error_message}</p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className="btn-secondary btn-sm" onClick={onHealth} disabled={busy && healthPending}>
          {busy && healthPending ? <Spinner /> : <Activity className="h-4 w-4" />}
          {t('system.health')}
        </button>
        {canConfigure && (
          <button type="button" className="btn-secondary btn-sm" onClick={onTest} disabled={busy && testPending}>
            {busy && testPending ? <Spinner /> : <PlugZap className="h-4 w-4" />}
            {busy && testPending ? t('ai.testing') : t('ai.testConnection')}
          </button>
        )}
      </div>
    </Card>
  )
}

function TestReportModal({ report, onClose }: { report: ConnectionTestReport | null; onClose: () => void }) {
  const { t } = useTranslation()
  if (!report) return null

  const tone = report.overall === 'PASS' ? 'success' : report.overall === 'FAIL' ? 'danger' : 'neutral'

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title={
        <span className="flex flex-wrap items-center gap-2">
          {t('ai.testResults')}
          <Badge tone="info">{report.provider}</Badge>
          <Badge tone={tone}>{report.overall}</Badge>
        </span>
      }
      footer={
        <button type="button" className="btn-secondary" onClick={onClose}>
          {t('common.close')}
        </button>
      }
    >
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        {t('ai.lastTest')}: {formatDateTime(report.checked_at)} · {t('ai.apiKeyNeverShown')}
      </p>
      <TableWrapper>
        <thead>
          <tr>
            <th>{t('common.name')}</th>
            <th>{t('common.status')}</th>
            <th>{t('common.details')}</th>
            <th>{t('lesson.duration')}</th>
          </tr>
        </thead>
        <tbody>
          {report.tests.map((test) => (
            <tr key={test.test_name}>
              <td className="font-medium">{t(`ai.tests.${test.test_name}`, test.test_name)}</td>
              <td>
                <Badge
                  tone={test.result === 'PASS' ? 'success' : test.result === 'FAIL' ? 'danger' : 'neutral'}
                >
                  {test.result}
                </Badge>
              </td>
              <td className="text-xs text-slate-600 dark:text-slate-300">{test.detail || '—'}</td>
              <td className="whitespace-nowrap text-xs">
                {test.duration_ms != null ? `${formatNumber(test.duration_ms)} ms` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </TableWrapper>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// 2) Analiz
// ---------------------------------------------------------------------------
function AnalysisTab({ providers }: { providers: ProviderStatus[] }) {
  const { t, i18n } = useTranslation()
  const can = useAuth((state) => state.can)

  const [scope, setScope] = useState('general')
  const [question, setQuestion] = useState('')
  const [studentId, setStudentId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [provider, setProvider] = useState('auto')
  const [result, setResult] = useState<AIAnalysisResponse | null>(null)

  const needsStudent = STUDENT_SCOPES.includes(scope)

  const scopeLabel = (value: string): string =>
    (SCOPE_LABEL_KEYS[value] ?? [value]).map((key) => t(key)).join(' · ')

  const studentsQuery = useQuery({
    queryKey: ['ai', 'analysis-students'],
    queryFn: () => get<Page<Student>>('/students', { page: 1, page_size: 200, status: 'active' }),
    enabled: needsStudent && can('student:read'),
    staleTime: 300_000,
  })

  const promptsQuery = useQuery({
    queryKey: ['ai', 'prompts'],
    queryFn: () => get<PromptTemplate[]>('/ai/prompts'),
    staleTime: 600_000,
  })

  const analysisMutation = useMutation({
    mutationFn: () =>
      post<AIAnalysisResponse>('/ai/analyze', {
        question: question.trim(),
        scope,
        student_id: needsStudent && studentId ? Number(studentId) : null,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        provider,
        language: i18n.language === 'en' ? 'en' : 'tr',
      }),
    onSuccess: (data) => setResult(data),
    onError: (error) => toastError(error),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    analysisMutation.mutate()
  }

  const canSubmit =
    question.trim().length >= 3 && (!needsStudent || studentId !== '') && !analysisMutation.isPending

  const analysisPrompts = (promptsQuery.data ?? []).filter((item) => item.category !== 'developer')

  return (
    <div className="space-y-4">
      <Card title={t('ai.analysis')}>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Field label={t('ai.analysis')}>
              <select className="select" value={scope} onChange={(event) => setScope(event.target.value)}>
                {ANALYSIS_SCOPES.map((item) => (
                  <option key={item} value={item}>
                    {scopeLabel(item)}
                  </option>
                ))}
              </select>
            </Field>

            {needsStudent && (
              <Field
                label={t('student.singular')}
                required
                hint={!can('student:read') ? t('errors.forbidden') : undefined}
              >
                <select
                  className="select"
                  value={studentId}
                  onChange={(event) => setStudentId(event.target.value)}
                  disabled={!can('student:read') || studentsQuery.isLoading}
                >
                  <option value="">{t('common.none')}</option>
                  {(studentsQuery.data?.items ?? []).map((student) => (
                    <option key={student.id} value={student.id}>
                      {student.full_name} ({student.student_number})
                    </option>
                  ))}
                </select>
              </Field>
            )}

            <Field label={t('membership.startDate')}>
              <input
                type="date"
                className="input"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
              />
            </Field>
            <Field label={t('membership.endDate')}>
              <input
                type="date"
                className="input"
                value={dateTo}
                onChange={(event) => setDateTo(event.target.value)}
              />
            </Field>
            <Field label={t('ai.provider')}>
              <select
                className="select"
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
              >
                <option value="auto">{t('ai.modes.automatic')}</option>
                {providers.map((item) => (
                  <option key={item.provider} value={item.provider}>
                    {item.display_name}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label={t('ai.askQuestion')} required>
            <textarea
              className="textarea"
              rows={3}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </Field>

          <div className="flex flex-wrap items-center gap-2">
            <button type="submit" className="btn-primary" disabled={!canSubmit}>
              {analysisMutation.isPending ? <Spinner /> : <Sparkles className="h-4 w-4" />}
              {analysisMutation.isPending ? t('ai.analyzing') : t('ai.ask')}
            </button>
            {result && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {formatNumber(result.data_points)} · {formatNumber(result.duration_ms)} ms
              </span>
            )}
          </div>
        </form>
      </Card>

      {/* Hazır sorular */}
      <Card title={t('ai.promptLibrary')}>
        {promptsQuery.isLoading ? (
          <LoadingState />
        ) : promptsQuery.error ? (
          <ErrorState error={promptsQuery.error} onRetry={() => void promptsQuery.refetch()} />
        ) : analysisPrompts.length === 0 ? (
          <EmptyState title={t('common.noData')} icon={<Sparkles className="h-6 w-6" />} />
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {analysisPrompts.map((item) => {
              const title = i18n.language === 'tr' ? item.title_tr : item.title_en
              const description = i18n.language === 'tr' ? item.description_tr : item.description_en
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setQuestion(i18n.language === 'tr' ? item.prompt_tr : item.prompt_en)
                    const mapped = PROMPT_SCOPE_MAP[item.id] ?? item.id
                    if (ANALYSIS_SCOPES.includes(mapped)) setScope(mapped)
                  }}
                  className="rounded-lg border border-slate-200 p-3 text-left transition-colors hover:border-brand-300 hover:bg-brand-50/50 dark:border-slate-700 dark:hover:border-brand-700 dark:hover:bg-brand-900/20"
                >
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{title}</p>
                  {description && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{description}</p>
                  )}
                  {item.requires_context.length > 0 && (
                    <span className="mt-2 inline-block text-[11px] text-amber-600 dark:text-amber-400">
                      {t('student.singular')}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </Card>

      {analysisMutation.isPending && <LoadingState label={t('ai.analyzing')} />}

      {result && !analysisMutation.isPending && <AnalysisResult result={result} />}
    </div>
  )
}

function AnalysisResult({ result }: { result: AIAnalysisResponse }) {
  const { t, i18n } = useTranslation()
  const summary = i18n.language === 'tr' ? result.metrics_summary_tr : result.metrics_summary_en
  const summaryLines = summary
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  return (
    <div className="space-y-4">
      {!result.data_sufficient && <Alert tone="info">{t('ai.insufficientData')}</Alert>}

      <DataPanel title={t('ai.realData')}>
        {summaryLines.length > 0 && (
          <ul className="mb-4 space-y-1">
            {summaryLines.map((line, index) => (
              <li key={index} className="flex gap-2 text-sm">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" aria-hidden="true" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        )}
        <MetricsView metrics={result.metrics} />
      </DataPanel>

      {result.ai_available ? (
        <AIPanel title={t('ai.aiInterpretation')} provider={result.provider} model={result.model}>
          {result.ai_interpretation ? (
            <p className="whitespace-pre-line">{result.ai_interpretation}</p>
          ) : (
            <p className="text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
          )}

          {result.ai_possible_causes.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-semibold text-violet-900 dark:text-violet-200">
                {t('ai.possibleCauses')}
              </p>
              <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm">
                {result.ai_possible_causes.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {result.ai_recommendations.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-semibold text-violet-900 dark:text-violet-200">
                {t('ai.recommendations')}
              </p>
              <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm">
                {result.ai_recommendations.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </AIPanel>
      ) : (
        <Alert tone="warning">{t('ai.notAvailable')}</Alert>
      )}
    </div>
  )
}

/** Hesaplanmış metrikleri kart ve tablolar olarak gösterir */
function MetricsView({ metrics }: { metrics: Record<string, unknown> }) {
  const { t } = useTranslation()
  const entries = Object.entries(metrics)

  if (entries.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
  }

  const scalars = entries.filter(([, value]) => value === null || isPrimitive(value))
  const objects = entries.filter(([, value]) => isPlainObject(value))
  const arrays = entries.filter(([, value]) => Array.isArray(value) && value.length > 0)

  return (
    <div className="space-y-4">
      {scalars.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {scalars.map(([key, value]) => (
            <div
              key={key}
              className="rounded-lg border border-emerald-200/70 bg-white/70 px-3 py-2 dark:border-emerald-900/50 dark:bg-slate-900/40"
            >
              <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {humanizeKey(key)}
              </p>
              <p className="mt-0.5 break-words text-sm font-semibold text-slate-900 dark:text-slate-100">
                {primitiveText(value)}
              </p>
            </div>
          ))}
        </div>
      )}

      {objects.map(([key, value]) => (
        <ObjectMetric key={key} name={key} value={value as Record<string, unknown>} />
      ))}

      {arrays.map(([key, value]) => (
        <ArrayMetric key={key} name={key} rows={value as unknown[]} />
      ))}
    </div>
  )
}

function ObjectMetric({ name, value }: { name: string; value: Record<string, unknown> }) {
  const rows = Object.entries(value)
  if (rows.length === 0) return null

  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
        {humanizeKey(name)}
      </p>
      <TableWrapper className="rounded-lg border border-emerald-200/70 dark:border-emerald-900/50">
        <tbody>
          {rows.map(([key, item]) => (
            <tr key={key}>
              <td className="w-1/2 text-xs text-slate-500 dark:text-slate-400">{humanizeKey(key)}</td>
              <td className="text-sm text-slate-800 dark:text-slate-100">{cellText(item)}</td>
            </tr>
          ))}
        </tbody>
      </TableWrapper>
    </div>
  )
}

function ArrayMetric({ name, rows }: { name: string; rows: unknown[] }) {
  const objectRows = rows.filter(isPlainObject)

  if (objectRows.length === 0) {
    return (
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
          {humanizeKey(name)}
        </p>
        <p className="text-sm text-slate-800 dark:text-slate-100">{cellText(rows)}</p>
      </div>
    )
  }

  const columns = Array.from(new Set(objectRows.flatMap((row) => Object.keys(row))))
  const visible = objectRows.slice(0, 25)

  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
        {humanizeKey(name)} ({formatNumber(objectRows.length)})
      </p>
      <TableWrapper className="rounded-lg border border-emerald-200/70 dark:border-emerald-900/50">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{humanizeKey(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visible.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column} className="whitespace-nowrap text-xs">
                  {cellText(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </TableWrapper>
    </div>
  )
}

// ---------------------------------------------------------------------------
// 3) Sohbet
// ---------------------------------------------------------------------------
function ChatTab({ providers }: { providers: ProviderStatus[] }) {
  const { t, i18n } = useTranslation()
  const [entries, setEntries] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const [provider, setProvider] = useState('auto')
  const bottomRef = useRef<HTMLDivElement>(null)
  const counterRef = useRef(0)

  const chatMutation = useMutation({
    mutationFn: (history: ChatEntry[]) =>
      post<ChatApiResponse>('/ai/chat', {
        messages: history.map((entry) => ({ role: entry.role, content: entry.content })),
        provider,
        language: i18n.language === 'en' ? 'en' : 'tr',
        json_mode: false,
      }),
    onSuccess: (response) => {
      counterRef.current += 1
      setEntries((current) => [
        ...current,
        {
          id: counterRef.current,
          role: 'assistant',
          content: response.content,
          provider: response.provider,
          model: response.model,
          tokens: response.usage.total_tokens,
          durationMs: response.duration_ms,
          fallbackUsed: response.fallback_used,
        },
      ])
    },
    onError: (error) => toastError(error),
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [entries.length, chatMutation.isPending])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = input.trim()
    if (text.length === 0 || chatMutation.isPending) return
    counterRef.current += 1
    const next: ChatEntry[] = [...entries, { id: counterRef.current, role: 'user', content: text }]
    setEntries(next)
    setInput('')
    chatMutation.mutate(next)
  }

  return (
    <Card
      title={t('ai.chat')}
      actions={
        <div className="flex items-center gap-2">
          <select
            className="select w-auto py-1 text-xs"
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
            aria-label={t('ai.provider')}
          >
            <option value="auto">{t('ai.modes.automatic')}</option>
            {providers.map((item) => (
              <option key={item.provider} value={item.provider}>
                {item.display_name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => setEntries([])}
            disabled={entries.length === 0}
          >
            {t('common.clearFilters')}
          </button>
        </div>
      }
    >
      <div className="mb-3 max-h-[52vh] min-h-[240px] space-y-3 overflow-y-auto pr-1">
        {entries.length === 0 && !chatMutation.isPending ? (
          <EmptyState
            title={t('ai.chat')}
            description={t('ai.systemWorksWithoutAi')}
            icon={<MessageSquare className="h-6 w-6" />}
          />
        ) : (
          entries.map((entry) => (
            <div
              key={entry.id}
              className={clsx('flex', entry.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              <div
                className={clsx(
                  'max-w-[85%] rounded-xl px-3 py-2 text-sm',
                  entry.role === 'user'
                    ? 'bg-brand-500 text-white'
                    : 'border border-violet-200 bg-violet-50 text-slate-800 dark:border-violet-900 dark:bg-violet-900/20 dark:text-slate-100',
                )}
              >
                <p className="whitespace-pre-line break-words">{entry.content}</p>
                {entry.role === 'assistant' && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {entry.provider && <Badge tone="info">{entry.provider}</Badge>}
                    {entry.model && <Badge tone="neutral">{entry.model}</Badge>}
                    {entry.tokens != null && (
                      <Badge tone="neutral">
                        {t('ai.tokenUsage')}: {formatNumber(entry.tokens)}
                      </Badge>
                    )}
                    {entry.durationMs != null && (
                      <Badge tone="neutral">{`${formatNumber(entry.durationMs)} ms`}</Badge>
                    )}
                    {entry.fallbackUsed && <Badge tone="warning">{t('ai.fallbackChain')}</Badge>}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {chatMutation.isPending && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-sm text-slate-600 dark:border-violet-900 dark:bg-violet-900/20 dark:text-slate-300">
              <Spinner />
              {t('ai.analyzing')}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <textarea
          className="textarea flex-1"
          rows={2}
          value={input}
          placeholder={t('ai.askQuestion')}
          onChange={(event) => setInput(event.target.value)}
          aria-label={t('ai.askQuestion')}
        />
        <button
          type="submit"
          className="btn-primary"
          disabled={input.trim().length === 0 || chatMutation.isPending}
        >
          {chatMutation.isPending ? <Spinner /> : <Send className="h-4 w-4" />}
          {t('ai.ask')}
        </button>
      </form>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// 4) Model yönlendirme
// ---------------------------------------------------------------------------
function RoutingTab() {
  const { t, i18n } = useTranslation()

  const routingQuery = useQuery({
    queryKey: ['ai', 'routing'],
    queryFn: () => get<RoutingTableResponse>('/ai/routing/tasks'),
  })

  const modelsQuery = useQuery({
    queryKey: ['ai', 'models', 'local'],
    queryFn: () => get<ModelInfo[]>('/ai/providers/local/models'),
    retry: false,
  })

  const providerColumns = useMemo(() => {
    const names = new Set<string>()
    for (const row of routingQuery.data?.tasks ?? []) {
      for (const name of Object.keys(row.providers)) names.add(name)
    }
    return Array.from(names)
  }, [routingQuery.data])

  return (
    <div className="space-y-4">
      <Card title={t('ai.routing')} bodyClassName="p-0">
        {routingQuery.isLoading ? (
          <LoadingState />
        ) : routingQuery.error ? (
          <ErrorState error={routingQuery.error} onRetry={() => void routingQuery.refetch()} />
        ) : !routingQuery.data || routingQuery.data.tasks.length === 0 ? (
          <EmptyState title={t('common.noData')} icon={<Network className="h-6 w-6" />} />
        ) : (
          <>
            <div className="px-5 pt-4">
              <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">{t('ai.routingSubtitle')}</p>
              <Alert tone="info">
                {i18n.language === 'tr' ? routingQuery.data.note_tr : routingQuery.data.note_en}
              </Alert>
            </div>
            <TableWrapper className="mt-3">
              <thead>
                <tr>
                  <th>{t('audit.action')}</th>
                  {providerColumns.map((name) => (
                    <th key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {routingQuery.data.tasks.map((row) => (
                  <tr key={row.task}>
                    <td className="align-top">
                      <p className="font-medium text-slate-800 dark:text-slate-100">{row.label}</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {row.keywords.map((keyword) => (
                          <span
                            key={keyword}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </td>
                    {providerColumns.map((name) => {
                      const hint = row.providers[name]
                      return (
                        <td key={name} className="align-top">
                          {hint ? (
                            <div className="space-y-1">
                              <p className="break-all text-xs text-slate-700 dark:text-slate-200">
                                {hint.suggested_model ?? '—'}
                              </p>
                              <Badge tone={hint.verified ? 'success' : 'neutral'}>
                                {hint.verified ? t('ai.capabilityVerified') : t('ai.capabilityHeuristic')}
                              </Badge>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          </>
        )}
      </Card>

      <Card
        title={`${t('ai.models')} · ${t('system.localAi')}`}
        bodyClassName="p-0"
        actions={
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => void modelsQuery.refetch()}
            disabled={modelsQuery.isFetching}
          >
            {modelsQuery.isFetching ? <Spinner /> : <RefreshCw className="h-4 w-4" />}
            {t('common.refresh')}
          </button>
        }
      >
        {modelsQuery.isLoading ? (
          <LoadingState />
        ) : modelsQuery.error ? (
          <ErrorState error={modelsQuery.error} onRetry={() => void modelsQuery.refetch()} />
        ) : !modelsQuery.data || modelsQuery.data.length === 0 ? (
          <EmptyState title={t('common.noData')} description={t('ai.unavailable')} icon={<Server className="h-6 w-6" />} />
        ) : (
          <TableWrapper>
            <thead>
              <tr>
                <th>{t('ai.model')}</th>
                <th>{t('instructor.specialties')}</th>
                <th>{t('common.status')}</th>
              </tr>
            </thead>
            <tbody>
              {modelsQuery.data.map((model) => (
                <tr key={model.id}>
                  <td>
                    <p className="break-all font-medium text-slate-800 dark:text-slate-100">{model.id}</p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      {model.owned_by ?? model.provider}
                      {model.context_length != null ? ` · ${formatNumber(model.context_length)} token` : ''}
                    </p>
                  </td>
                  <td>
                    {model.capabilities.length === 0 ? (
                      <span className="text-xs text-slate-400">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {model.capabilities.map((capability) => (
                          <span
                            key={capability}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                          >
                            {capability}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>
                    <Badge tone={model.capability_source === 'api' ? 'success' : 'neutral'}>
                      {model.capability_source === 'api'
                        ? t('ai.capabilityVerified')
                        : t('ai.capabilityHeuristic')}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </TableWrapper>
        )}
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// 5) Görev geçmişi
// ---------------------------------------------------------------------------
function TaskHistoryTab({ providers }: { providers: ProviderStatus[] }) {
  const { t } = useTranslation()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [kind, setKind] = useState('')
  const [status, setStatus] = useState('')
  const [provider, setProvider] = useState('')

  const tasksQuery = useQuery({
    queryKey: ['ai', 'tasks', page, pageSize, kind, status, provider],
    queryFn: () =>
      get<Page<AITask>>('/ai/tasks', {
        page,
        page_size: pageSize,
        kind: kind || undefined,
        status: status || undefined,
        provider: provider || undefined,
      }),
  })

  function resetAndSet(setter: (value: string) => void) {
    return (event: ChangeEvent<HTMLSelectElement>) => {
      setter(event.target.value)
      setPage(1)
    }
  }

  return (
    <Card
      title={t('ai.taskHistory')}
      bodyClassName="p-0"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="select w-auto py-1 text-xs"
            value={kind}
            onChange={resetAndSet(setKind)}
            aria-label={t('audit.action')}
          >
            <option value="">{t('common.all')}</option>
            {TASK_KINDS.map((item) => (
              <option key={item} value={item}>
                {t(TASK_KIND_KEYS[item] ?? 'common.all', item)}
              </option>
            ))}
          </select>
          <select
            className="select w-auto py-1 text-xs"
            value={status}
            onChange={resetAndSet(setStatus)}
            aria-label={t('common.status')}
          >
            <option value="">{t('common.all')}</option>
            {TASK_STATUSES.map((item) => (
              <option key={item} value={item}>
                {t(TASK_STATUS_KEYS[item] ?? 'common.status', item)}
              </option>
            ))}
          </select>
          <select
            className="select w-auto py-1 text-xs"
            value={provider}
            onChange={resetAndSet(setProvider)}
            aria-label={t('ai.provider')}
          >
            <option value="">{t('common.all')}</option>
            {providers.map((item) => (
              <option key={item.provider} value={item.provider}>
                {item.display_name}
              </option>
            ))}
          </select>
        </div>
      }
      footer={
        tasksQuery.data && tasksQuery.data.total > 0 ? (
          <Pagination
            page={page}
            pageSize={pageSize}
            total={tasksQuery.data.total}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size)
              setPage(1)
            }}
          />
        ) : undefined
      }
    >
      {tasksQuery.isLoading ? (
        <LoadingState />
      ) : tasksQuery.error ? (
        <ErrorState error={tasksQuery.error} onRetry={() => void tasksQuery.refetch()} />
      ) : !tasksQuery.data || tasksQuery.data.items.length === 0 ? (
        <EmptyState title={t('common.noData')} icon={<History className="h-6 w-6" />} />
      ) : (
        <TableWrapper>
          <thead>
            <tr>
              <th>{t('audit.action')}</th>
              <th>{t('common.status')}</th>
              <th className="hidden md:table-cell">{t('ai.provider')}</th>
              <th className="hidden lg:table-cell">{t('ai.model')}</th>
              <th>{t('ai.tokenUsage')}</th>
              <th>{t('lesson.duration')}</th>
              <th className="hidden sm:table-cell">{t('audit.occurredAt')}</th>
            </tr>
          </thead>
          <tbody>
            {tasksQuery.data.items.map((task) => (
              <tr key={task.id}>
                <td>
                  <p className="font-medium text-slate-800 dark:text-slate-100">
                    {t(TASK_KIND_KEYS[task.kind] ?? 'common.all', task.kind)}
                  </p>
                  <p className="max-w-[280px] truncate text-[11px] text-slate-500 dark:text-slate-400" title={task.title}>
                    {task.title}
                  </p>
                </td>
                <td>
                  <Badge tone={TASK_STATUS_TONES[task.status] ?? 'neutral'}>
                    {t(TASK_STATUS_KEYS[task.status] ?? 'common.status', task.status)}
                  </Badge>
                  {task.error_message && (
                    <p className="mt-1 max-w-[220px] truncate text-[11px] text-rose-600 dark:text-rose-400" title={task.error_message}>
                      {task.error_message}
                    </p>
                  )}
                </td>
                <td className="hidden whitespace-nowrap md:table-cell">
                  {task.provider ?? '—'}
                  {task.fallback_used && (
                    <span className="ml-1 text-[11px] text-amber-600 dark:text-amber-400">↩</span>
                  )}
                </td>
                <td className="hidden max-w-[200px] truncate lg:table-cell" title={task.model ?? ''}>
                  {task.model ?? '—'}
                </td>
                <td className="whitespace-nowrap">{formatNumber(task.total_tokens)}</td>
                <td className="whitespace-nowrap">{`${formatNumber(task.duration_ms)} ms`}</td>
                <td className="hidden whitespace-nowrap text-xs text-slate-500 dark:text-slate-400 sm:table-cell">
                  {formatDateTime(task.started_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </TableWrapper>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// 6) Yapılandırma
// ---------------------------------------------------------------------------
function ConfigTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<ConfigFormState | null>(null)
  const [apiKey, setApiKey] = useState('')

  const configQuery = useQuery({
    queryKey: ['ai', 'config'],
    queryFn: () => get<AIConfigResponse>('/ai/config'),
    refetchOnWindowFocus: false,
  })

  const configData = configQuery.data

  useEffect(() => {
    if (!configData) return
    setForm({
      mode: configData.routing.mode,
      fallback_chain: [...configData.routing.fallback_chain],
      response_language: configData.routing.response_language,
      local_enabled: configData.local.enabled,
      local_base_url: configData.local.base_url ?? '',
      local_model: configData.local.model && !configData.local.model.startsWith('(') ? configData.local.model : '',
      local_timeout: configData.local.timeout ?? 120,
      local_max_tokens: configData.local.max_tokens ?? 2048,
      local_temperature: configData.local.temperature ?? 0.3,
      nvidia_enabled: configData.nvidia.enabled,
      nvidia_base_url: configData.nvidia.base_url ?? '',
      nvidia_model: configData.nvidia.model ?? '',
    })
    setApiKey('')
  }, [configData])

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => put<Message>('/ai/config', payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['ai', 'config'] })
      void queryClient.invalidateQueries({ queryKey: ['ai', 'control-center'] })
      setApiKey('')
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  if (configQuery.isLoading) return <LoadingState />
  if (configQuery.error) {
    return <ErrorState error={configQuery.error} onRetry={() => void configQuery.refetch()} />
  }
  if (!configData || !form) return null

  const providerKeys = Object.keys(configData).filter((key) => key !== 'routing')
  const chainCandidates = providerKeys.filter((key) => !form.fallback_chain.includes(key))

  function update<K extends keyof ConfigFormState>(key: K, value: ConfigFormState[K]) {
    setForm((current) => (current ? { ...current, [key]: value } : current))
  }

  function moveChainItem(index: number, direction: -1 | 1) {
    setForm((current) => {
      if (!current) return current
      const chain = [...current.fallback_chain]
      const target = index + direction
      if (target < 0 || target >= chain.length) return current
      const [item] = chain.splice(index, 1)
      chain.splice(target, 0, item)
      return { ...current, fallback_chain: chain }
    })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form) return
    const payload: Record<string, unknown> = {
      mode: form.mode,
      fallback_chain: form.fallback_chain,
      response_language: form.response_language,
      local_enabled: form.local_enabled,
      local_timeout: form.local_timeout,
      local_max_tokens: form.local_max_tokens,
      local_temperature: form.local_temperature,
      nvidia_enabled: form.nvidia_enabled,
    }
    if (form.local_base_url.trim()) payload.local_base_url = form.local_base_url.trim()
    if (form.local_model.trim()) payload.local_model = form.local_model.trim()
    if (form.nvidia_base_url.trim()) payload.nvidia_base_url = form.nvidia_base_url.trim()
    if (form.nvidia_model.trim()) payload.nvidia_model = form.nvidia_model.trim()
    // Boş bırakılırsa mevcut anahtar korunur; anahtar hiçbir zaman geri okunmaz
    if (apiKey.trim()) payload.nvidia_api_key = apiKey.trim()
    saveMutation.mutate(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Card title={t('ai.mode')}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t('ai.mode')}>
            <select
              className="select"
              value={form.mode}
              onChange={(event) => update('mode', event.target.value)}
            >
              {['local', 'nvidia', 'automatic'].map((item) => (
                <option key={item} value={item}>
                  {t(`ai.modes.${item}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('ai.responseLanguage')}>
            <select
              className="select"
              value={form.response_language}
              onChange={(event) => update('response_language', event.target.value)}
            >
              <option value="auto">{t('ai.languageAuto')}</option>
              <option value="tr">Türkçe</option>
              <option value="en">English</option>
            </select>
          </Field>
        </div>

        <Field label={t('ai.fallbackChain')} className="mt-3">
          <div className="space-y-2">
            {form.fallback_chain.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('common.none')}</p>
            ) : (
              form.fallback_chain.map((name, index) => (
                <div
                  key={`${name}-${index}`}
                  className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 dark:border-slate-700"
                >
                  <span className="w-5 text-xs text-slate-400">{index + 1}</span>
                  <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">{name}</span>
                  <button
                    type="button"
                    className="btn-ghost btn-sm"
                    onClick={() => moveChainItem(index, -1)}
                    disabled={index === 0}
                    aria-label={t('common.previous')}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="btn-ghost btn-sm"
                    onClick={() => moveChainItem(index, 1)}
                    disabled={index === form.fallback_chain.length - 1}
                    aria-label={t('common.next')}
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                    onClick={() =>
                      update(
                        'fallback_chain',
                        form.fallback_chain.filter((_, position) => position !== index),
                      )
                    }
                    aria-label={t('common.delete')}
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
            {chainCandidates.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {chainCandidates.map((name) => (
                  <button
                    key={name}
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => update('fallback_chain', [...form.fallback_chain, name])}
                  >
                    + {name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </Field>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Yerel sağlayıcı */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <h2 className="card-title">{t('system.localAi')}</h2>
            </div>
          }
        >
          <label className="mb-3 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input
              type="checkbox"
              checked={form.local_enabled}
              onChange={(event) => update('local_enabled', event.target.checked)}
            />
            {t('common.active')}
          </label>

          <div className="grid gap-3">
            <Field label={t('ai.endpoint')}>
              <input
                type="text"
                className="input"
                value={form.local_base_url}
                onChange={(event) => update('local_base_url', event.target.value)}
              />
            </Field>
            {/* Boş bırakılırsa sağlayıcının ilk modeli otomatik seçilir */}
            <Field label={t('ai.model')} hint={t('common.optional')}>
              <input
                type="text"
                className="input"
                value={form.local_model}
                onChange={(event) => update('local_model', event.target.value)}
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label={t('ai.tests.timeout')}>
                <input
                  type="number"
                  min={5}
                  max={900}
                  className="input"
                  value={form.local_timeout}
                  onChange={(event) => update('local_timeout', Number(event.target.value))}
                />
              </Field>
              {/* Teknik parametre adları çeviriye tabi değildir (.env anahtarlarıyla birebir) */}
              <Field label="max_tokens">
                <input
                  type="number"
                  min={1}
                  max={32000}
                  className="input"
                  value={form.local_max_tokens}
                  onChange={(event) => update('local_max_tokens', Number(event.target.value))}
                />
              </Field>
              <Field label="temperature">
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  className="input"
                  value={form.local_temperature}
                  onChange={(event) => update('local_temperature', Number(event.target.value))}
                />
              </Field>
            </div>
          </div>

          <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800 dark:border-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-200">
            {t('ai.localPrivacy')}
          </p>
        </Card>

        {/* NVIDIA sağlayıcısı */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <Cloud className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <h2 className="card-title">{t('system.cloudAi')}</h2>
            </div>
          }
        >
          <label className="mb-3 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input
              type="checkbox"
              checked={form.nvidia_enabled}
              onChange={(event) => update('nvidia_enabled', event.target.checked)}
            />
            {t('common.active')}
          </label>

          <div className="grid gap-3">
            <Field label={t('ai.endpoint')}>
              <input
                type="text"
                className="input"
                value={form.nvidia_base_url}
                onChange={(event) => update('nvidia_base_url', event.target.value)}
              />
            </Field>
            <Field label={t('ai.model')}>
              <input
                type="text"
                className="input"
                value={form.nvidia_model}
                onChange={(event) => update('nvidia_model', event.target.value)}
              />
            </Field>
            <Field label={t('ai.apiKey')} hint={t('ai.apiKeyHint')}>
              <input
                type="password"
                className="input"
                value={apiKey}
                autoComplete="new-password"
                placeholder={configData.nvidia.api_key_masked || t('ai.apiKeyNotSet')}
                onChange={(event) => setApiKey(event.target.value)}
              />
            </Field>
            <div className="flex flex-wrap items-center gap-2">
              <KeyRound className="h-3.5 w-3.5 text-slate-400" />
              {configData.nvidia.api_key_set ? (
                <Badge tone="success">{t('ai.apiKeySet')}</Badge>
              ) : (
                <Badge tone="neutral">{t('ai.apiKeyNotSet')}</Badge>
              )}
              <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                {configData.nvidia.api_key_masked}
              </span>
            </div>
          </div>

          <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-900/20 dark:text-amber-200">
            {t('ai.cloudPrivacy')}
          </p>
        </Card>
      </div>

      <Alert tone="warning" title={t('ai.apiKey')}>
        {t('ai.apiKeyNeverShown')}
      </Alert>

      <div className="flex justify-end">
        <button type="submit" className="btn-primary" disabled={saveMutation.isPending}>
          {saveMutation.isPending ? <Spinner /> : <Save className="h-4 w-4" />}
          {t('common.save')}
        </button>
      </div>
    </form>
  )
}
