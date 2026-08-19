/** AI Developer Console - güvenli, onaya dayalı kod geliştirme ekranı. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  FileCode,
  FolderTree,
  History,
  Layers,
  MinusCircle,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Terminal,
  Wand2,
  XCircle,
} from 'lucide-react'
import { useMemo, useState, type ChangeEvent } from 'react'
import { useTranslation } from 'react-i18next'

import {
  Alert,
  Badge,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  PageHeader,
  Pagination,
  Spinner,
  StatCard,
  TableWrapper,
  Tabs,
} from '@/components/ui'
import { get, post } from '@/lib/api'
import { formatDateTime, formatFileSize, formatNumber, formatRelative } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  AIControlCenter,
  AgentStep,
  CommandPolicyInfo,
  DeveloperPlanResponse,
  FileChange,
  Message,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Yalnızca bu ekranda kullanılan yardımcı tipler (uç noktalar sözlük döndürür)
// ---------------------------------------------------------------------------
interface TestRunResult {
  success: boolean
  return_code: number
  passed: number
  failed: number
  duration_ms: number
  output: string
  command?: string
}

interface PatchListItem {
  patch_id: string
  instruction: string
  created_at: string
  file_count: number
  files: string[]
}

interface CheckpointItem {
  checkpoint_id: string
  created_at: string
  label: string
  file_count: number
}

interface FileListResponse {
  pattern: string
  count: number
  files: string[]
}

interface FileContentResponse {
  path: string
  size: number
  lines: number
  content: string
}

interface CodeSearchHit {
  path: string
  line: number
  text: string
}

interface CodeSearchResponse {
  query: string
  count: number
  hits: CodeSearchHit[]
}

interface PatchApplyResultDto {
  success: boolean
  patch_id: string
  checkpoint_id?: string | null
  applied_files: string[]
  test_result?: Record<string, unknown> | null
  rolled_back: boolean
  message: string
}

const FALLBACK_PROVIDERS = ['local', 'nvidia', 'openai_compat']
const FILE_PATTERNS = ['*.py', '*.ts', '*.tsx', '*.json', '*.md', '*.css']

/** Sunucudan gelen sözlüğü test sonucuna dönüştürür (tip güvenli daraltma). */
function toTestResult(value: unknown): TestRunResult | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const record = value as Record<string, unknown>
  if (typeof record.passed !== 'number' && typeof record.output !== 'string') return null
  return {
    success: record.success === true,
    return_code: typeof record.return_code === 'number' ? record.return_code : 0,
    passed: typeof record.passed === 'number' ? record.passed : 0,
    failed: typeof record.failed === 'number' ? record.failed : 0,
    duration_ms: typeof record.duration_ms === 'number' ? record.duration_ms : 0,
    output: typeof record.output === 'string' ? record.output : '',
    command: typeof record.command === 'string' ? record.command : undefined,
  }
}

// ---------------------------------------------------------------------------
// Ajan adım ikonu
// ---------------------------------------------------------------------------
function StepIcon({ status }: { status: AgentStep['status'] }) {
  if (status === 'success') return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
  if (status === 'failed') return <XCircle className="h-4 w-4 text-rose-500" />
  if (status === 'running') return <Spinner className="h-4 w-4 text-brand-500" />
  if (status === 'skipped') return <MinusCircle className="h-4 w-4 text-slate-400" />
  return <Circle className="h-4 w-4 text-slate-300 dark:text-slate-600" />
}

// ---------------------------------------------------------------------------
// Satır satır renklendirilmiş diff görünümü
// ---------------------------------------------------------------------------
function DiffView({ diff }: { diff: string }) {
  const lines = diff.replace(/\n$/, '').split('\n')
  return (
    <div className="max-h-[26rem] overflow-auto rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900">
      <div className="min-w-full py-1 font-mono text-[11px] leading-5">
        {lines.map((line, index) => {
          let tone = 'text-slate-600 dark:text-slate-300'
          if (line.startsWith('+++') || line.startsWith('---')) {
            tone = 'text-slate-400 dark:text-slate-500'
          } else if (line.startsWith('@@')) {
            tone = 'bg-brand-100 text-brand-800 dark:bg-brand-900/40 dark:text-brand-200'
          } else if (line.startsWith('+')) {
            tone = 'bg-emerald-100/70 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
          } else if (line.startsWith('-')) {
            tone = 'bg-rose-100/70 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300'
          }
          return (
            <div key={index} className={`flex gap-3 px-3 ${tone}`}>
              <span className="w-8 shrink-0 select-none text-right text-slate-400 dark:text-slate-600">
                {index + 1}
              </span>
              <span className="whitespace-pre">{line === '' ? ' ' : line}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Test sonucu kartı
// ---------------------------------------------------------------------------
function TestResultCard({ result }: { result: TestRunResult }) {
  const { t } = useTranslation()
  return (
    <Card
      title={t('aiDeveloper.testResults')}
      actions={
        <Badge tone={result.success ? 'success' : 'danger'}>
          {result.success ? t('common.success') : t('common.error')}
        </Badge>
      }
    >
      <div className="mb-3 grid gap-3 sm:grid-cols-3">
        <StatCard
          label={t('aiDeveloper.testsPassed', { count: result.passed })}
          value={formatNumber(result.passed)}
          icon={<CheckCircle2 className="h-5 w-5" />}
          tone="success"
        />
        <StatCard
          label={t('aiDeveloper.testsFailed', { count: result.failed })}
          value={formatNumber(result.failed)}
          icon={<XCircle className="h-5 w-5" />}
          tone={result.failed > 0 ? 'danger' : 'neutral'}
        />
        <StatCard
          label={t('ai.latency')}
          value={`${formatNumber(result.duration_ms)} ms`}
          hint={result.command}
          icon={<Play className="h-5 w-5" />}
          tone="neutral"
        />
      </div>
      {result.output ? (
        <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-[11px] leading-5 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
          {result.output}
        </pre>
      ) : (
        <EmptyState title={t('common.noData')} />
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Politika etiket listesi
// ---------------------------------------------------------------------------
function ChipList({ items, tone }: { items: string[]; tone: 'neutral' | 'danger' | 'warning' }) {
  const { t } = useTranslation()
  if (items.length === 0) {
    return <p className="text-xs text-slate-400">{t('common.none')}</p>
  }
  const styles = {
    neutral: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
    danger: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
    warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className={`rounded px-1.5 py-0.5 font-mono text-[11px] ${styles[tone]}`}
        >
          {item}
        </span>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dosya değişikliği kartı (genişletilebilir)
// ---------------------------------------------------------------------------
function ChangeCard({ change }: { change: FileChange }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(true)
  const actionTone =
    change.action === 'create' ? 'success' : change.action === 'delete' ? 'danger' : 'info'

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
      >
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
        )}
        <FileCode className="h-4 w-4 shrink-0 text-brand-500" />
        <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-700 dark:text-slate-200">
          {change.path}
        </span>
        <Badge tone={actionTone}>{change.action}</Badge>
        <span className="hidden shrink-0 text-xs text-emerald-600 dark:text-emerald-400 sm:inline">
          +{formatNumber(change.lines_added)}
        </span>
        <span className="hidden shrink-0 text-xs text-rose-600 dark:text-rose-400 sm:inline">
          −{formatNumber(change.lines_removed)}
        </span>
      </button>
      {open && (
        <div className="border-t border-slate-200 p-3 dark:border-slate-700">
          <div className="mb-2 flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
            <span>{t('aiDeveloper.linesAdded', { count: change.lines_added })}</span>
            <span>{t('aiDeveloper.linesRemoved', { count: change.lines_removed })}</span>
            {change.original_size !== null && change.original_size !== undefined && (
              <span className="font-mono">{formatFileSize(change.original_size)}</span>
            )}
            {change.new_size !== null && change.new_size !== undefined && (
              <span className="font-mono">→ {formatFileSize(change.new_size)}</span>
            )}
          </div>
          {change.diff ? (
            <DiffView diff={change.diff} />
          ) : (
            <EmptyState title={t('aiDeveloper.noChanges')} />
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Ana sayfa
// ---------------------------------------------------------------------------
export default function AIDeveloperPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  // Form durumu
  const [instruction, setInstruction] = useState('')
  const [provider, setProvider] = useState('auto')
  const [maxFiles, setMaxFiles] = useState(8)
  const [autoTest, setAutoTest] = useState(true)

  // Sonuçlar
  const [planResult, setPlanResult] = useState<DeveloperPlanResponse | null>(null)
  const [applyResult, setApplyResult] = useState<PatchApplyResultDto | null>(null)
  const [testResult, setTestResult] = useState<TestRunResult | null>(null)

  // Onay iletişim kutuları
  const [pendingPatch, setPendingPatch] = useState<string | null>(null)
  const [pendingCheckpoint, setPendingCheckpoint] = useState<string | null>(null)

  // Politika paneli
  const [policyOpen, setPolicyOpen] = useState(false)

  // Alt sekmeler
  const [tab, setTab] = useState('patches')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  // Dosya gezgini / arama
  const [filePattern, setFilePattern] = useState('*.py')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [searchInput, setSearchInput] = useState('')
  const [searchPattern, setSearchPattern] = useState('*.py')
  const [searchQuery, setSearchQuery] = useState('')

  const allowed = can('ai:developer')

  // ---- Sorgular ----------------------------------------------------------
  const policyQuery = useQuery({
    queryKey: ['ai-developer', 'policy'],
    queryFn: () => get<CommandPolicyInfo>('/ai/developer/policy'),
    enabled: allowed,
  })

  const controlQuery = useQuery({
    queryKey: ['ai-control-center'],
    queryFn: () => get<AIControlCenter>('/ai/control-center'),
    enabled: allowed,
    retry: false,
  })

  const patchesQuery = useQuery({
    queryKey: ['ai-developer', 'patches'],
    queryFn: () => get<PatchListItem[]>('/ai/developer/patches', { limit: 100 }),
    enabled: allowed && tab === 'patches',
  })

  const checkpointsQuery = useQuery({
    queryKey: ['ai-developer', 'checkpoints'],
    queryFn: () => get<CheckpointItem[]>('/ai/developer/checkpoints', { limit: 100 }),
    enabled: allowed && tab === 'checkpoints',
  })

  const filesQuery = useQuery({
    queryKey: ['ai-developer', 'files', filePattern],
    queryFn: () => get<FileListResponse>('/ai/developer/files', { pattern: filePattern }),
    enabled: allowed && tab === 'files',
  })

  const fileQuery = useQuery({
    queryKey: ['ai-developer', 'file', selectedFile],
    queryFn: () => get<FileContentResponse>('/ai/developer/file', { path: selectedFile }),
    enabled: allowed && selectedFile !== null,
  })

  const searchQueryResult = useQuery({
    queryKey: ['ai-developer', 'search', searchQuery, searchPattern],
    queryFn: () =>
      get<CodeSearchResponse>('/ai/developer/search', { q: searchQuery, pattern: searchPattern }),
    enabled: allowed && tab === 'search' && searchQuery.length >= 2,
  })

  // ---- Mutasyonlar -------------------------------------------------------
  const planMutation = useMutation({
    mutationFn: () =>
      post<DeveloperPlanResponse>('/ai/developer/plan', {
        instruction: instruction.trim(),
        provider,
        auto_test: autoTest,
        max_files: maxFiles,
      }),
    onSuccess: (data) => {
      setPlanResult(data)
      setApplyResult(null)
      setTestResult(toTestResult(data.test_result))
      queryClient.invalidateQueries({ queryKey: ['ai-developer', 'patches'] })
      toastSuccess(t('common.success'), t('aiDeveloper.changes'))
    },
    onError: (error) => toastError(error),
  })

  const applyMutation = useMutation({
    mutationFn: (patchId: string) =>
      post<PatchApplyResultDto>('/ai/developer/apply', {
        patch_id: patchId,
        confirm: true,
        run_tests_after: true,
      }),
    onSuccess: (data) => {
      setApplyResult(data)
      setPendingPatch(null)
      const parsed = toTestResult(data.test_result)
      if (parsed) setTestResult(parsed)
      queryClient.invalidateQueries({ queryKey: ['ai-developer'] })
      if (data.success) {
        toastSuccess(t('common.success'), data.message)
      } else {
        toastError(new Error(data.message), data.message)
      }
    },
    onError: (error) => {
      setPendingPatch(null)
      toastError(error)
    },
  })

  const rollbackMutation = useMutation({
    mutationFn: (checkpointId: string) =>
      post<Message>('/ai/developer/rollback', { checkpoint_id: checkpointId, confirm: true }),
    onSuccess: (data) => {
      setPendingCheckpoint(null)
      queryClient.invalidateQueries({ queryKey: ['ai-developer'] })
      toastSuccess(t('common.success'), data.message)
    },
    onError: (error) => {
      setPendingCheckpoint(null)
      toastError(error)
    },
  })

  const testMutation = useMutation({
    mutationFn: () =>
      post<Record<string, unknown>>('/ai/developer/run-tests', undefined, {
        target: 'backend/tests',
      }),
    onSuccess: (data) => {
      const parsed = toTestResult(data)
      setTestResult(parsed)
      if (parsed) {
        toastSuccess(
          parsed.success ? t('common.success') : t('common.warning'),
          `${t('aiDeveloper.testsPassed', { count: parsed.passed })} · ${t('aiDeveloper.testsFailed', { count: parsed.failed })}`,
        )
      }
    },
    onError: (error) => toastError(error),
  })

  // ---- Türetilmiş veriler -------------------------------------------------
  const providerOptions = useMemo(() => {
    const options = [{ value: 'auto', label: t('ai.modes.automatic') }]
    const providers = controlQuery.data?.providers
    if (providers && providers.length > 0) {
      for (const item of providers) {
        options.push({ value: item.provider, label: item.display_name })
      }
    } else {
      for (const name of FALLBACK_PROVIDERS) options.push({ value: name, label: name })
    }
    return options
  }, [controlQuery.data, t])

  const policy = policyQuery.data

  function changeTab(id: string) {
    setTab(id)
    setPage(1)
  }

  function paginate<T>(rows: T[]): T[] {
    const start = (page - 1) * pageSize
    return rows.slice(start, start + pageSize)
  }

  if (!allowed) {
    return (
      <>
        <PageHeader title={t('aiDeveloper.title')} icon={<Terminal className="h-5 w-5" />} />
        <Alert tone="danger" title={t('errors.forbidden')}>
          {t('errors.forbiddenHint')}
        </Alert>
      </>
    )
  }

  const patches = patchesQuery.data ?? []
  const checkpoints = checkpointsQuery.data ?? []
  const files = filesQuery.data?.files ?? []
  const hits = searchQueryResult.data?.hits ?? []

  return (
    <>
      <PageHeader
        title={t('aiDeveloper.title')}
        subtitle={t('aiDeveloper.subtitle')}
        icon={<Terminal className="h-5 w-5" />}
        actions={
          <button
            type="button"
            className="btn-secondary"
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
          >
            {testMutation.isPending ? <Spinner /> : <Play className="h-4 w-4" />}
            {t('aiDeveloper.runTests')}
          </button>
        }
      />

      {/* ---------------------------------------------------------------- */}
      {/* Güvenlik politikası - her zaman görünür                           */}
      {/* ---------------------------------------------------------------- */}
      <section className="card mb-4">
        <div className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-brand-50 p-2 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {t('aiDeveloper.policy')}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('aiDeveloper.policySubtitle')}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {policyQuery.isLoading && <Spinner />}
            {policy && (
              <>
                <Badge tone={policy.shell_enabled ? 'warning' : 'neutral'}>
                  {t('aiDeveloper.shellEnabled')}:{' '}
                  {policy.shell_enabled ? t('common.active') : t('ai.disabled')}
                </Badge>
                <Badge tone={policy.apply_enabled ? 'success' : 'neutral'}>
                  {t('aiDeveloper.applyEnabled')}:{' '}
                  {policy.apply_enabled ? t('common.active') : t('ai.disabled')}
                </Badge>
              </>
            )}
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => setPolicyOpen((value) => !value)}
              aria-expanded={policyOpen}
            >
              {policyOpen ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              {policyOpen ? t('common.showLess') : t('common.showMore')}
            </button>
          </div>
        </div>

        {policyQuery.error && (
          <div className="border-t border-slate-200 px-5 py-3 dark:border-slate-700">
            <ErrorState error={policyQuery.error} onRetry={() => policyQuery.refetch()} />
          </div>
        )}

        {policyOpen && policy && (
          <div className="grid gap-4 border-t border-slate-200 px-5 py-4 dark:border-slate-700 lg:grid-cols-2">
            <div className="space-y-3">
              <div>
                <p className="label">{t('settings.tabs.developer')}</p>
                <p className="break-all rounded-lg bg-slate-50 px-2 py-1.5 font-mono text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-200">
                  {policy.project_root}
                </p>
              </div>
              <div>
                <p className="label">{t('aiDeveloper.writeScope')}</p>
                <p className="break-all rounded-lg bg-slate-50 px-2 py-1.5 font-mono text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-200">
                  {policy.write_scope}
                </p>
              </div>
              <div>
                <p className="label">{t('aiDeveloper.allowedCommands')}</p>
                <ChipList items={policy.allowed_commands} tone="neutral" />
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <p className="label text-rose-600 dark:text-rose-400">
                  {t('aiDeveloper.blockedOperations')}
                </p>
                <ChipList items={policy.blocked_patterns} tone="danger" />
              </div>
              <div>
                <p className="label">{t('aiDeveloper.requiresConfirmation')}</p>
                <ChipList items={policy.requires_confirmation} tone="warning" />
              </div>
            </div>
          </div>
        )}
      </section>

      {policy && !policy.apply_enabled && (
        <div className="mb-4">
          <Alert tone="warning">{t('aiDeveloper.applyDisabled')}</Alert>
        </div>
      )}

      {/* Yama uygulama sonucu - geri alındıysa uyarı gösterilir */}
      {applyResult && (
        <div className="mb-4">
          <Alert
            tone={applyResult.rolled_back ? 'warning' : applyResult.success ? 'success' : 'danger'}
            title={applyResult.message}
          >
            <div className="space-y-1">
              {applyResult.rolled_back && (
                <p className="font-medium">{t('backup.rolledBack')}</p>
              )}
              {applyResult.applied_files.length > 0 && (
                <p className="break-all font-mono">{applyResult.applied_files.join(', ')}</p>
              )}
              {applyResult.checkpoint_id && (
                <p className="break-all font-mono">
                  {t('aiDeveloper.checkpoints')}: {applyResult.checkpoint_id}
                </p>
              )}
            </div>
          </Alert>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Talimat formu                                                     */}
      {/* ---------------------------------------------------------------- */}
      <Card title={t('aiDeveloper.instruction')} className="mb-4">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (instruction.trim().length < 3) return
            planMutation.mutate()
          }}
        >
          <Field label={t('aiDeveloper.instruction')} required>
            <textarea
              className="textarea"
              rows={4}
              value={instruction}
              onChange={(event: ChangeEvent<HTMLTextAreaElement>) =>
                setInstruction(event.target.value)
              }
              placeholder={t('aiDeveloper.instructionPlaceholder')}
              maxLength={8000}
            />
          </Field>

          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <Field label={t('ai.provider')}>
              <select
                className="select"
                value={provider}
                onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                  setProvider(event.target.value)
                }
              >
                {providerOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('aiDeveloper.changes')} hint={t('common.total')}>
              <input
                type="number"
                className="input"
                min={1}
                max={40}
                value={maxFiles}
                onChange={(event: ChangeEvent<HTMLInputElement>) =>
                  setMaxFiles(Math.min(40, Math.max(1, Number(event.target.value) || 1)))
                }
              />
            </Field>
            <Field label={t('settings.autoTest')}>
              <label className="flex h-9 items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-brand-600"
                  checked={autoTest}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    setAutoTest(event.target.checked)
                  }
                />
                {t('settings.autoTest')}
              </label>
            </Field>
          </div>

          <div className="mt-4 flex items-center gap-2">
            <button
              type="submit"
              className="btn-primary"
              disabled={planMutation.isPending || instruction.trim().length < 3}
            >
              {planMutation.isPending ? <Spinner /> : <Wand2 className="h-4 w-4" />}
              {planMutation.isPending ? t('aiDeveloper.planning') : t('aiDeveloper.plan')}
            </button>
            {planResult && (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => {
                  setPlanResult(null)
                  setApplyResult(null)
                }}
              >
                {t('common.clearFilters')}
              </button>
            )}
          </div>
        </form>
      </Card>

      {planMutation.isPending && <LoadingState label={t('aiDeveloper.planning')} />}

      {/* ---------------------------------------------------------------- */}
      {/* Plan sonucu                                                       */}
      {/* ---------------------------------------------------------------- */}
      {planResult && (
        <div className="mb-4 space-y-4">
          {planResult.warnings.length > 0 && (
            <Alert tone="warning" title={t('aiDeveloper.warnings')}>
              <ul className="list-inside list-disc space-y-1">
                {planResult.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </Alert>
          )}

          <div className="grid gap-4 lg:grid-cols-3">
            {/* Ajan adımları */}
            <Card title={t('aiDeveloper.steps')}>
              {planResult.steps.length === 0 ? (
                <EmptyState title={t('common.noData')} />
              ) : (
                <ol className="space-y-3">
                  {planResult.steps.map((step, index) => (
                    <li key={`${step.step}-${index}`} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <StepIcon status={step.status} />
                        {index < planResult.steps.length - 1 && (
                          <span className="mt-1 h-full w-px flex-1 bg-slate-200 dark:bg-slate-700" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1 pb-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs font-semibold text-slate-700 dark:text-slate-200">
                            {step.step}
                          </span>
                          {step.duration_ms !== null && step.duration_ms !== undefined && (
                            <span className="shrink-0 text-[11px] text-slate-400">
                              {formatNumber(step.duration_ms)} ms
                            </span>
                          )}
                        </div>
                        {step.detail && (
                          <p className="mt-0.5 break-words text-xs text-slate-500 dark:text-slate-400">
                            {step.detail}
                          </p>
                        )}
                        {step.output && (
                          <pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono text-[10px] text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                            {step.output}
                          </pre>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </Card>

            {/* Analiz ve plan */}
            <Card
              title={t('aiDeveloper.analysis')}
              className="lg:col-span-2"
              actions={
                <div className="flex flex-wrap items-center gap-2">
                  {planResult.provider && (
                    <Badge tone="info">
                      {planResult.provider}
                      {planResult.model ? ` · ${planResult.model}` : ''}
                    </Badge>
                  )}
                  {planResult.requires_approval && (
                    <Badge tone="warning">{t('aiDeveloper.requiresConfirmation')}</Badge>
                  )}
                </div>
              }
            >
              {planResult.analysis ? (
                <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200">
                  {planResult.analysis}
                </p>
              ) : (
                <p className="text-sm text-slate-400">{t('common.noData')}</p>
              )}

              <h3 className="mb-2 mt-4 text-sm font-semibold text-slate-900 dark:text-slate-100">
                {t('aiDeveloper.planSteps')}
              </h3>
              {planResult.plan.length === 0 ? (
                <p className="text-sm text-slate-400">{t('common.noData')}</p>
              ) : (
                <ol className="list-inside list-decimal space-y-1.5 text-sm text-slate-700 dark:text-slate-200">
                  {planResult.plan.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ol>
              )}
            </Card>
          </div>

          {/* Dosya değişiklikleri */}
          <Card
            title={t('aiDeveloper.changes')}
            actions={
              planResult.patch_id && planResult.apply_allowed && policy?.apply_enabled ? (
                <button
                  type="button"
                  className="btn-primary btn-sm"
                  onClick={() => setPendingPatch(planResult.patch_id ?? null)}
                  disabled={applyMutation.isPending}
                >
                  {applyMutation.isPending ? <Spinner /> : <CheckCircle2 className="h-4 w-4" />}
                  {applyMutation.isPending
                    ? t('aiDeveloper.applying')
                    : t('aiDeveloper.applyPatch')}
                </button>
              ) : undefined
            }
          >
            {planResult.changes.length === 0 ? (
              <EmptyState title={t('aiDeveloper.noChanges')} icon={<FileCode className="h-6 w-6" />} />
            ) : (
              <div className="space-y-2">
                {planResult.changes.map((change) => (
                  <ChangeCard key={change.path} change={change} />
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {testResult && (
        <div className="mb-4">
          <TestResultCard result={testResult} />
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Alt sekmeler                                                      */}
      {/* ---------------------------------------------------------------- */}
      <Tabs
        active={tab}
        onChange={changeTab}
        tabs={[
          { id: 'patches', label: t('aiDeveloper.patches'), icon: <Layers className="h-4 w-4" /> },
          {
            id: 'checkpoints',
            label: t('aiDeveloper.checkpoints'),
            icon: <History className="h-4 w-4" />,
          },
          {
            id: 'files',
            label: t('aiDeveloper.fileExplorer'),
            icon: <FolderTree className="h-4 w-4" />,
          },
          {
            id: 'search',
            label: t('aiDeveloper.searchCode'),
            icon: <Search className="h-4 w-4" />,
          },
        ]}
      />

      {/* Yamalar */}
      {tab === 'patches' && (
        <Card title={t('aiDeveloper.patches')} bodyClassName="p-0">
          {patchesQuery.isLoading ? (
            <LoadingState />
          ) : patchesQuery.error ? (
            <ErrorState error={patchesQuery.error} onRetry={() => patchesQuery.refetch()} />
          ) : patches.length === 0 ? (
            <EmptyState title={t('common.noData')} icon={<Layers className="h-6 w-6" />} />
          ) : (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('common.date')}</th>
                    <th>{t('aiDeveloper.instruction')}</th>
                    <th>{t('aiDeveloper.changes')}</th>
                    <th className="text-right">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {paginate(patches).map((item) => (
                    <tr key={item.patch_id}>
                      <td className="whitespace-nowrap">
                        <p className="text-sm">{formatDateTime(item.created_at)}</p>
                        <p className="font-mono text-[11px] text-slate-400">{item.patch_id}</p>
                      </td>
                      <td className="max-w-md">
                        <p className="truncate text-sm text-slate-700 dark:text-slate-200">
                          {item.instruction}
                        </p>
                      </td>
                      <td>
                        <p className="text-sm">{formatNumber(item.file_count)}</p>
                        <p className="truncate font-mono text-[11px] text-slate-400">
                          {item.files.join(', ')}
                        </p>
                      </td>
                      <td className="text-right">
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => setPendingPatch(item.patch_id)}
                          disabled={!policy?.apply_enabled || applyMutation.isPending}
                          title={t('aiDeveloper.applyPatch')}
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          {t('aiDeveloper.applyPatch')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={patches.length}
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

      {/* Geri alma noktaları */}
      {tab === 'checkpoints' && (
        <Card title={t('aiDeveloper.checkpoints')} bodyClassName="p-0">
          {checkpointsQuery.isLoading ? (
            <LoadingState />
          ) : checkpointsQuery.error ? (
            <ErrorState error={checkpointsQuery.error} onRetry={() => checkpointsQuery.refetch()} />
          ) : checkpoints.length === 0 ? (
            <EmptyState title={t('common.noData')} icon={<History className="h-6 w-6" />} />
          ) : (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('common.date')}</th>
                    <th>{t('common.description')}</th>
                    <th>{t('common.total')}</th>
                    <th className="text-right">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {paginate(checkpoints).map((item) => (
                    <tr key={item.checkpoint_id}>
                      <td className="whitespace-nowrap">
                        <p className="text-sm">{formatDateTime(item.created_at)}</p>
                        <p className="text-[11px] text-slate-400">
                          {formatRelative(item.created_at)}
                        </p>
                      </td>
                      <td className="max-w-md">
                        <p className="truncate text-sm text-slate-700 dark:text-slate-200">
                          {item.label || '—'}
                        </p>
                        <p className="font-mono text-[11px] text-slate-400">{item.checkpoint_id}</p>
                      </td>
                      <td>{formatNumber(item.file_count)}</td>
                      <td className="text-right">
                        <button
                          type="button"
                          className="btn-danger btn-sm"
                          onClick={() => setPendingCheckpoint(item.checkpoint_id)}
                          disabled={rollbackMutation.isPending}
                          title={t('aiDeveloper.rollback')}
                        >
                          <RotateCcw className="h-4 w-4" />
                          {t('aiDeveloper.rollback')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={checkpoints.length}
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

      {/* Dosya gezgini */}
      {tab === 'files' && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            title={t('aiDeveloper.fileExplorer')}
            actions={
              <select
                className="select w-auto py-1 text-xs"
                value={filePattern}
                onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                  setFilePattern(event.target.value)
                  setPage(1)
                }}
                aria-label={t('common.filter')}
              >
                {FILE_PATTERNS.map((pattern) => (
                  <option key={pattern} value={pattern}>
                    {pattern}
                  </option>
                ))}
              </select>
            }
            bodyClassName="p-0"
          >
            {filesQuery.isLoading ? (
              <LoadingState />
            ) : filesQuery.error ? (
              <ErrorState error={filesQuery.error} onRetry={() => filesQuery.refetch()} />
            ) : files.length === 0 ? (
              <EmptyState title={t('common.noResults')} icon={<FolderTree className="h-6 w-6" />} />
            ) : (
              <>
                <ul className="max-h-[520px] overflow-y-auto py-1">
                  {paginate(files).map((path) => (
                    <li key={path}>
                      <button
                        type="button"
                        onClick={() => setSelectedFile(path)}
                        className={`flex w-full items-center gap-2 px-4 py-1.5 text-left font-mono text-[11px] transition-colors ${
                          selectedFile === path
                            ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                            : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-700/50'
                        }`}
                      >
                        <FileCode className="h-3.5 w-3.5 shrink-0" />
                        <span className="truncate">{path}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={files.length}
                  onPageChange={setPage}
                  onPageSizeChange={(size) => {
                    setPageSize(size)
                    setPage(1)
                  }}
                />
              </>
            )}
          </Card>

          <Card
            title={selectedFile ?? t('aiDeveloper.fileExplorer')}
            className="lg:col-span-2"
            actions={
              fileQuery.data ? (
                <div className="flex items-center gap-2">
                  <Badge tone="neutral">{formatFileSize(fileQuery.data.size)}</Badge>
                  <Badge tone="info">{formatNumber(fileQuery.data.lines)}</Badge>
                </div>
              ) : undefined
            }
          >
            {!selectedFile ? (
              <EmptyState
                title={t('common.noData')}
                description={t('aiDeveloper.fileExplorer')}
                icon={<FileCode className="h-6 w-6" />}
              />
            ) : fileQuery.isLoading ? (
              <LoadingState />
            ) : fileQuery.error ? (
              <ErrorState error={fileQuery.error} onRetry={() => fileQuery.refetch()} />
            ) : fileQuery.data ? (
              <div className="max-h-[540px] overflow-auto rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900">
                <div className="py-2 font-mono text-[11px] leading-5">
                  {fileQuery.data.content.split('\n').map((line, index) => (
                    <div key={index} className="flex gap-3 px-3">
                      <span className="w-10 shrink-0 select-none text-right text-slate-400 dark:text-slate-600">
                        {index + 1}
                      </span>
                      <span className="whitespace-pre text-slate-700 dark:text-slate-200">
                        {line === '' ? ' ' : line}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </Card>
        </div>
      )}

      {/* Kod arama */}
      {tab === 'search' && (
        <Card title={t('aiDeveloper.searchCode')} bodyClassName="p-0">
          <form
            className="flex flex-col gap-2 border-b border-slate-200 p-4 dark:border-slate-700 sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault()
              setSearchQuery(searchInput.trim())
              setPage(1)
            }}
          >
            <input
              className="input flex-1"
              value={searchInput}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setSearchInput(event.target.value)
              }
              placeholder={t('common.search')}
              minLength={2}
            />
            <select
              className="select sm:w-32"
              value={searchPattern}
              onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                setSearchPattern(event.target.value)
              }
              aria-label={t('common.filter')}
            >
              {FILE_PATTERNS.map((pattern) => (
                <option key={pattern} value={pattern}>
                  {pattern}
                </option>
              ))}
            </select>
            <button
              type="submit"
              className="btn-primary sm:w-auto"
              disabled={searchInput.trim().length < 2}
            >
              <Search className="h-4 w-4" />
              {t('common.search')}
            </button>
          </form>

          {searchQuery.length < 2 ? (
            <EmptyState title={t('common.search')} icon={<Search className="h-6 w-6" />} />
          ) : searchQueryResult.isLoading ? (
            <LoadingState />
          ) : searchQueryResult.error ? (
            <ErrorState
              error={searchQueryResult.error}
              onRetry={() => searchQueryResult.refetch()}
            />
          ) : hits.length === 0 ? (
            <EmptyState title={t('common.noResults')} icon={<Search className="h-6 w-6" />} />
          ) : (
            <>
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('common.name')}</th>
                    <th>{t('common.details')}</th>
                    <th className="text-right">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {paginate(hits).map((hit, index) => (
                    <tr key={`${hit.path}-${hit.line}-${index}`}>
                      <td className="whitespace-nowrap font-mono text-[11px]">
                        {hit.path}
                        <span className="ml-1 text-slate-400">:{hit.line}</span>
                      </td>
                      <td>
                        <code className="block max-w-xl truncate rounded bg-slate-50 px-2 py-1 font-mono text-[11px] text-slate-700 dark:bg-slate-900 dark:text-slate-200">
                          {hit.text}
                        </code>
                      </td>
                      <td className="text-right">
                        <button
                          type="button"
                          className="btn-ghost btn-sm"
                          onClick={() => {
                            setSelectedFile(hit.path)
                            changeTab('files')
                          }}
                          title={t('common.details')}
                        >
                          <FileCode className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={hits.length}
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

      {/* Onay iletişim kutuları */}
      <ConfirmDialog
        open={pendingPatch !== null}
        onClose={() => setPendingPatch(null)}
        onConfirm={() => {
          if (pendingPatch) applyMutation.mutate(pendingPatch)
        }}
        title={t('aiDeveloper.applyPatch')}
        message={t('aiDeveloper.applyConfirm')}
        confirmLabel={t('aiDeveloper.applyPatch')}
        tone="primary"
        loading={applyMutation.isPending}
      />
      <ConfirmDialog
        open={pendingCheckpoint !== null}
        onClose={() => setPendingCheckpoint(null)}
        onConfirm={() => {
          if (pendingCheckpoint) rollbackMutation.mutate(pendingCheckpoint)
        }}
        title={t('aiDeveloper.rollback')}
        message={t('aiDeveloper.rollbackConfirm')}
        confirmLabel={t('aiDeveloper.rollback')}
        loading={rollbackMutation.isPending}
      />
    </>
  )
}
