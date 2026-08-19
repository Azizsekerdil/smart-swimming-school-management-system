/** CAIO — Chief AI Officer: sistem gözlemi, bulgular ve öneriler. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  Archive,
  Brain,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Database,
  FileText,
  ListChecks,
  Play,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { useMemo, useState, type ChangeEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  AIPanel,
  Alert,
  Badge,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Pagination,
  Spinner,
  StatCard,
  TableWrapper,
  type BadgeTone,
} from '@/components/ui'
import { get, patch, post } from '@/lib/api'
import { formatDateTime, formatNumber, formatPercent, formatRelative } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type { CAIOFinding, CAIOReport, Page } from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------
const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info']

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f43f5e',
  high: '#f59e0b',
  medium: '#6366f1',
  low: '#0ea5e9',
  info: '#94a3b8',
}

const SEVERITY_TONES: Record<string, BadgeTone> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'info',
  info: 'neutral',
}

const CATEGORY_LIST = [
  'security',
  'backup',
  'testing',
  'technical_debt',
  'reliability',
  'data_quality',
  'compliance',
  'operations',
  'ai_quality',
  'cost',
  'ai_suggestion',
]

const CATEGORY_COLORS = [
  '#0ea5e9',
  '#38bdf8',
  '#6366f1',
  '#8b5cf6',
  '#f59e0b',
  '#10b981',
  '#f43f5e',
  '#d946ef',
]

const FINDING_STATUSES = ['open', 'acknowledged', 'in_progress', 'resolved', 'dismissed']

/** Gözlem bölümleri: her biri gerçek ölçüm verisidir, AI yorumu değildir. */
const OBSERVATION_SECTIONS: Array<{ key: string; titleKey: string }> = [
  { key: 'logs', titleKey: 'caio.categories.reliability' },
  { key: 'ai_usage', titleKey: 'caio.categories.ai_quality' },
  { key: 'code_quality', titleKey: 'caio.categories.technical_debt' },
  { key: 'database', titleKey: 'system.database' },
  { key: 'security', titleKey: 'caio.categories.security' },
  { key: 'backups', titleKey: 'caio.categories.backup' },
]

interface CAIOSummaryResponse {
  open_findings: number
  by_severity: Record<string, number>
  by_category: Record<string, number>
  critical_count: number
  high_count: number
  last_run_at: string | null
  top_findings: Array<{
    id: number
    severity: string
    category: string
    title: string
    recommendation: string | null
  }>
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function severityRank(severity: string): number {
  const index = SEVERITY_ORDER.indexOf(severity)
  return index === -1 ? SEVERITY_ORDER.length : index
}

// ---------------------------------------------------------------------------
// Gözlem değeri gösterimi
// ---------------------------------------------------------------------------
function ScalarValue({ value }: { value: unknown }) {
  const { t } = useTranslation()
  if (value === null || value === undefined || value === '') {
    return <span className="text-slate-400">—</span>
  }
  if (typeof value === 'boolean') {
    return (
      <Badge tone={value ? 'success' : 'neutral'}>{value ? t('common.yes') : t('common.no')}</Badge>
    )
  }
  if (typeof value === 'number') {
    return (
      <span className="font-medium text-slate-900 dark:text-slate-100">
        {formatNumber(value, Number.isInteger(value) ? 0 : 2)}
      </span>
    )
  }
  return <span className="break-words text-slate-700 dark:text-slate-200">{String(value)}</span>
}

function ComplexValue({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <p className="text-xs text-slate-400">—</p>
    const objectRows = value.filter(isRecord)
    if (objectRows.length === 0) {
      return (
        <div className="flex flex-wrap gap-1.5">
          {value.map((item, index) => (
            <span
              key={index}
              className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700 dark:bg-slate-700 dark:text-slate-200"
            >
              {String(item)}
            </span>
          ))}
        </div>
      )
    }
    const columns = Array.from(new Set(objectRows.flatMap((row) => Object.keys(row))))
    return (
      <div className="rounded-lg border border-slate-200 dark:border-slate-700">
        <TableWrapper>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} className="font-mono text-[11px]">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {objectRows.slice(0, 10).map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td key={column} className="max-w-xs truncate text-xs">
                    <ScalarValue value={row[column]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </TableWrapper>
      </div>
    )
  }

  if (isRecord(value)) {
    return (
      <dl className="grid gap-x-4 gap-y-1.5 sm:grid-cols-2">
        {Object.entries(value).map(([key, entry]) => (
          <div key={key} className="flex items-baseline justify-between gap-3">
            <dt className="font-mono text-[11px] text-slate-500 dark:text-slate-400">{key}</dt>
            <dd className="text-right text-sm">
              {isRecord(entry) || Array.isArray(entry) ? (
                <ComplexValue value={entry} />
              ) : (
                <ScalarValue value={entry} />
              )}
            </dd>
          </div>
        ))}
      </dl>
    )
  }

  return <ScalarValue value={value} />
}

/** Ölçülen sistem verisi kartı (AI yorumu DEĞİL). */
function ObservationCard({
  title,
  icon,
  data,
}: {
  title: string
  icon: ReactNode
  data: Record<string, unknown>
}) {
  const { t } = useTranslation()
  const entries = Object.entries(data)
  const scalars = entries.filter(([, value]) => !isRecord(value) && !Array.isArray(value))
  const complex = entries.filter(([, value]) => isRecord(value) || Array.isArray(value))

  return (
    <Card
      title={
        <h2 className="card-title flex items-center gap-2">
          <span className="text-brand-500">{icon}</span>
          {title}
        </h2>
      }
    >
      {scalars.length > 0 && (
        <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
          {scalars.map(([key, value]) => (
            <div
              key={key}
              className="flex items-baseline justify-between gap-3 border-b border-dashed border-slate-100 pb-1 dark:border-slate-700/70"
            >
              <dt className="font-mono text-[11px] text-slate-500 dark:text-slate-400">{key}</dt>
              <dd className="text-right text-sm">
                <ScalarValue value={value} />
              </dd>
            </div>
          ))}
        </dl>
      )}
      {complex.map(([key, value]) => (
        <div key={key} className="mt-4">
          <p className="mb-1.5 font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400">
            {key}
          </p>
          <ComplexValue value={value} />
        </div>
      ))}
      {entries.length === 0 && <EmptyState title={t('common.noData')} />}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Önem dağılımı çubukları
// ---------------------------------------------------------------------------
function SeverityBars({ bySeverity }: { bySeverity: Record<string, number> }) {
  const { t } = useTranslation()
  const extras = Object.keys(bySeverity).filter((key) => !SEVERITY_ORDER.includes(key))
  const keys = [...SEVERITY_ORDER, ...extras].filter((key) => (bySeverity[key] ?? 0) > 0)
  const total = keys.reduce((sum, key) => sum + (bySeverity[key] ?? 0), 0)

  if (total === 0) return <EmptyState title={t('caio.noFindings')} />

  return (
    <div className="space-y-2.5">
      {keys.map((key) => {
        const count = bySeverity[key] ?? 0
        const percent = (count / total) * 100
        return (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between gap-2 text-xs">
              <span className="font-medium text-slate-600 dark:text-slate-300">
                {t(`caio.severity.${key}`, key)}
              </span>
              <span className="text-slate-500 dark:text-slate-400">
                {formatNumber(count)} · {formatPercent(percent)}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${percent}%`, backgroundColor: SEVERITY_COLORS[key] ?? '#94a3b8' }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Bulgu kartı
// ---------------------------------------------------------------------------
function FindingCard({
  finding,
  onChangeStatus,
  pending,
}: {
  finding: CAIOFinding
  onChangeStatus: (id: number, status: string) => void
  pending: boolean
}) {
  const { t } = useTranslation()
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const hasEvidence = Object.keys(finding.evidence ?? {}).length > 0

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap items-center gap-2">
            <Badge tone={SEVERITY_TONES[finding.severity] ?? 'neutral'}>
              {t(`caio.severity.${finding.severity}`, finding.severity)}
            </Badge>
            <Badge tone="neutral">
              {t(`caio.categories.${finding.category}`, finding.category)}
            </Badge>
            {finding.is_ai_generated && (
              <span className="badge bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
                {finding.ai_provider ? `AI · ${finding.ai_provider}` : 'AI'}
              </span>
            )}
            <span className="text-[11px] text-slate-400">{formatDateTime(finding.created_at)}</span>
          </div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {finding.title}
          </h3>
          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">
            {finding.description}
          </p>
        </div>

        <select
          className="select w-auto py-1 text-xs"
          value={finding.status}
          onChange={(event: ChangeEvent<HTMLSelectElement>) =>
            onChangeStatus(finding.id, event.target.value)
          }
          disabled={pending}
          aria-label={t('common.status')}
        >
          {FINDING_STATUSES.map((status) => (
            <option key={status} value={status}>
              {t(`caio.statuses.${status}`, status)}
            </option>
          ))}
        </select>
      </div>

      {finding.recommendation && (
        <div className="mt-3 rounded-lg border-l-4 border-brand-400 bg-brand-50 px-3 py-2 dark:border-brand-600 dark:bg-brand-900/20">
          <p className="text-xs font-semibold text-brand-800 dark:text-brand-300">
            {t('caio.recommendation')}
          </p>
          <p className="mt-0.5 whitespace-pre-wrap text-sm text-brand-900 dark:text-brand-100">
            {finding.recommendation}
          </p>
        </div>
      )}

      {hasEvidence && (
        <div className="mt-3">
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => setEvidenceOpen((value) => !value)}
            aria-expanded={evidenceOpen}
          >
            {evidenceOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            {t('caio.evidence')}
          </button>
          {evidenceOpen && (
            <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-2.5 font-mono text-[11px] leading-5 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
              {JSON.stringify(finding.evidence, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Ana sayfa
// ---------------------------------------------------------------------------
export default function CAIOPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const [includeAi, setIncludeAi] = useState(true)
  const [report, setReport] = useState<CAIOReport | null>(null)

  const [statusFilter, setStatusFilter] = useState('open')
  const [severityFilter, setSeverityFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const allowed = can('ai:caio')

  const summaryQuery = useQuery({
    queryKey: ['caio', 'summary'],
    queryFn: () => get<CAIOSummaryResponse>('/ai/caio/summary'),
    enabled: allowed,
  })

  const observeQuery = useQuery({
    queryKey: ['caio', 'observe'],
    queryFn: () => get<Record<string, unknown>>('/ai/caio/observe'),
    enabled: allowed,
    staleTime: 60_000,
  })

  const findingsQuery = useQuery({
    queryKey: ['caio', 'findings', statusFilter, severityFilter, categoryFilter, page, pageSize],
    queryFn: () =>
      get<Page<CAIOFinding>>('/ai/caio/findings', {
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        category: categoryFilter || undefined,
        page,
        page_size: pageSize,
      }),
    enabled: allowed,
  })

  const runMutation = useMutation({
    mutationFn: () =>
      post<CAIOReport>('/ai/caio/run', {
        include_ai: includeAi,
        categories: [],
        provider: 'auto',
      }),
    onSuccess: (data) => {
      setReport(data)
      queryClient.invalidateQueries({ queryKey: ['caio'] })
      toastSuccess(
        t('common.success'),
        `${formatNumber(data.findings.length)} · ${t('caio.findings')}`,
      )
    },
    onError: (error) => toastError(error),
  })

  const statusMutation = useMutation({
    mutationFn: (payload: { id: number; status: string }) =>
      patch<CAIOFinding>(`/ai/caio/findings/${payload.id}`, { status: payload.status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['caio'] })
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const summary = summaryQuery.data

  const observations: Record<string, unknown> = useMemo(() => {
    if (report) return report.observations as Record<string, unknown>
    return observeQuery.data ?? {}
  }, [report, observeQuery.data])

  const categoryChartData = useMemo(() => {
    const source = summary?.by_category ?? {}
    return Object.entries(source)
      .map(([key, value]) => ({ name: t(`caio.categories.${key}`, key), value }))
      .sort((a, b) => b.value - a.value)
  }, [summary, t])

  const findings = useMemo(() => {
    const items = findingsQuery.data?.items ?? []
    return [...items].sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
  }, [findingsQuery.data])

  function resetPage() {
    setPage(1)
  }

  if (!allowed) {
    return (
      <>
        <PageHeader title={t('caio.fullTitle')} icon={<Brain className="h-5 w-5" />} />
        <Alert tone="danger" title={t('errors.forbidden')}>
          {t('errors.forbiddenHint')}
        </Alert>
      </>
    )
  }

  const sectionIcons: Record<string, ReactNode> = {
    logs: <FileText className="h-4 w-4" />,
    ai_usage: <Sparkles className="h-4 w-4" />,
    code_quality: <Code2 className="h-4 w-4" />,
    database: <Database className="h-4 w-4" />,
    security: <ShieldAlert className="h-4 w-4" />,
    backups: <Archive className="h-4 w-4" />,
  }

  const totalFindings = findingsQuery.data?.total ?? 0

  return (
    <>
      <PageHeader
        title={t('caio.fullTitle')}
        subtitle={t('caio.subtitle')}
        icon={<Brain className="h-5 w-5" />}
        actions={
          <>
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
                checked={includeAi}
                onChange={(event: ChangeEvent<HTMLInputElement>) =>
                  setIncludeAi(event.target.checked)
                }
              />
              {t('caio.includeAi')}
            </label>
            <button
              type="button"
              className="btn-primary"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
            >
              {runMutation.isPending ? <Spinner /> : <Play className="h-4 w-4" />}
              {runMutation.isPending ? t('caio.running') : t('caio.run')}
            </button>
          </>
        }
      />

      {/* Rolün sınırları - her zaman görünür */}
      <div className="mb-5">
        <Alert tone="info" title={t('caio.cannotModify')}>
          <span className="font-mono">{t('caio.workflow')}</span>
        </Alert>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Özet                                                              */}
      {/* ---------------------------------------------------------------- */}
      {summaryQuery.isLoading ? (
        <LoadingState />
      ) : summaryQuery.error ? (
        <ErrorState error={summaryQuery.error} onRetry={() => summaryQuery.refetch()} />
      ) : summary ? (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label={t('caio.openFindings')}
              value={formatNumber(summary.open_findings)}
              icon={<ListChecks className="h-5 w-5" />}
              tone={summary.open_findings > 0 ? 'warning' : 'success'}
            />
            <StatCard
              label={t('caio.severity.critical')}
              value={formatNumber(summary.critical_count)}
              icon={<ShieldAlert className="h-5 w-5" />}
              tone={summary.critical_count > 0 ? 'danger' : 'success'}
            />
            <StatCard
              label={t('caio.severity.high')}
              value={formatNumber(summary.high_count)}
              icon={<AlertTriangle className="h-5 w-5" />}
              tone={summary.high_count > 0 ? 'warning' : 'success'}
            />
            <StatCard
              label={t('settings.lastUpdated')}
              value={summary.last_run_at ? formatRelative(summary.last_run_at) : '—'}
              hint={summary.last_run_at ? formatDateTime(summary.last_run_at) : undefined}
              icon={<Clock className="h-5 w-5" />}
              tone="neutral"
            />
          </div>

          <div className="mb-4 grid gap-4 lg:grid-cols-2">
            <Card title={t('caio.findings')}>
              <SeverityBars bySeverity={summary.by_severity} />
            </Card>
            <Card title={`${t('caio.findings')} · ${t('statistics.distribution')}`}>
              {categoryChartData.length === 0 ? (
                <EmptyState title={t('caio.noFindings')} />
              ) : (
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(180, categoryChartData.length * 30)}
                >
                  <BarChart
                    data={categoryChartData}
                    layout="vertical"
                    margin={{ top: 4, right: 16, bottom: 4, left: 4 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                    <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals={false} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 10 }}
                      width={110}
                      interval={0}
                    />
                    <Tooltip
                      formatter={(value: number) => [formatNumber(value), t('caio.findings')]}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {categoryChartData.map((_, index) => (
                        <Cell key={index} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
        </>
      ) : null}

      {/* ---------------------------------------------------------------- */}
      {/* Rapor - AI yorumu                                                 */}
      {/* ---------------------------------------------------------------- */}
      {runMutation.isPending && <LoadingState label={t('caio.running')} />}

      {report && (
        <div className="mb-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <Badge tone="info">{formatDateTime(report.run_at)}</Badge>
            <Badge tone="neutral">{formatNumber(report.duration_ms)} ms</Badge>
            <Badge tone={report.findings.length > 0 ? 'warning' : 'success'}>
              {t('caio.findings')}: {formatNumber(report.findings.length)}
            </Badge>
          </div>

          {report.ai_available && report.ai_summary ? (
            <AIPanel title={t('caio.aiSummary')} provider={report.provider}>
              <p className="whitespace-pre-wrap">{report.ai_summary}</p>
              {report.ai_proposals.length > 0 && (
                <>
                  <p className="mb-1 mt-3 text-sm font-semibold text-violet-900 dark:text-violet-200">
                    {t('caio.aiProposals')}
                  </p>
                  <ul className="list-inside list-disc space-y-1">
                    {report.ai_proposals.map((proposal, index) => (
                      <li key={index}>{proposal}</li>
                    ))}
                  </ul>
                </>
              )}
            </AIPanel>
          ) : (
            <Alert tone="warning">{t('ai.notAvailable')}</Alert>
          )}
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Gözlemler - GERÇEK ÖLÇÜM (AI yorumu değil)                        */}
      {/* ---------------------------------------------------------------- */}
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {t('caio.observations')}
      </h2>

      {observeQuery.isLoading && !report ? (
        <LoadingState />
      ) : observeQuery.error && !report ? (
        <ErrorState error={observeQuery.error} onRetry={() => observeQuery.refetch()} />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {['observed_at', 'app_version', 'environment'].map((key) => {
              const value = observations[key]
              if (value === undefined || value === null) return null
              return (
                <Badge key={key} tone="neutral">
                  <span className="font-mono">
                    {key}: {key === 'observed_at' ? formatDateTime(String(value)) : String(value)}
                  </span>
                </Badge>
              )
            })}
          </div>

          <div className="mb-6 grid gap-4 lg:grid-cols-2">
            {OBSERVATION_SECTIONS.map((section) => {
              const data = observations[section.key]
              if (!isRecord(data)) return null
              return (
                <ObservationCard
                  key={section.key}
                  title={t(section.titleKey)}
                  icon={sectionIcons[section.key]}
                  data={data}
                />
              )
            })}
          </div>
        </>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Bulgular                                                          */}
      {/* ---------------------------------------------------------------- */}
      <Card
        title={t('caio.findings')}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="select w-auto py-1 text-xs"
              value={statusFilter}
              onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                setStatusFilter(event.target.value)
                resetPage()
              }}
              aria-label={t('common.status')}
            >
              <option value="">{t('common.all')}</option>
              {FINDING_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {t(`caio.statuses.${status}`, status)}
                </option>
              ))}
            </select>
            <select
              className="select w-auto py-1 text-xs"
              value={severityFilter}
              onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                setSeverityFilter(event.target.value)
                resetPage()
              }}
              aria-label={t('common.filter')}
            >
              <option value="">{t('common.all')}</option>
              {SEVERITY_ORDER.map((severity) => (
                <option key={severity} value={severity}>
                  {t(`caio.severity.${severity}`, severity)}
                </option>
              ))}
            </select>
            <select
              className="select w-auto py-1 text-xs"
              value={categoryFilter}
              onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                setCategoryFilter(event.target.value)
                resetPage()
              }}
              aria-label={t('common.filters')}
            >
              <option value="">{t('common.all')}</option>
              {CATEGORY_LIST.map((category) => (
                <option key={category} value={category}>
                  {t(`caio.categories.${category}`, category)}
                </option>
              ))}
            </select>
            {(statusFilter !== 'open' || severityFilter || categoryFilter) && (
              <button
                type="button"
                className="btn-ghost btn-sm"
                onClick={() => {
                  setStatusFilter('open')
                  setSeverityFilter('')
                  setCategoryFilter('')
                  resetPage()
                }}
              >
                {t('common.clearFilters')}
              </button>
            )}
          </div>
        }
        bodyClassName="p-0"
      >
        {findingsQuery.isLoading ? (
          <LoadingState />
        ) : findingsQuery.error ? (
          <ErrorState error={findingsQuery.error} onRetry={() => findingsQuery.refetch()} />
        ) : findings.length === 0 ? (
          <EmptyState title={t('caio.noFindings')} icon={<ListChecks className="h-6 w-6" />} />
        ) : (
          <>
            <div className="space-y-3 p-4">
              {findings.map((finding) => (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  pending={statusMutation.isPending}
                  onChangeStatus={(id, status) => statusMutation.mutate({ id, status })}
                />
              ))}
            </div>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={totalFindings}
              onPageChange={setPage}
              onPageSizeChange={(size) => {
                setPageSize(size)
                resetPage()
              }}
            />
          </>
        )}
      </Card>
    </>
  )
}
