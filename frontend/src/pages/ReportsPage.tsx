/** Rapor oluşturucu / Report builder. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  BookmarkPlus,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  Printer,
  Search,
  Trash2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  Alert,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  Spinner,
  TableWrapper,
} from '@/components/ui'
import { del, download, get, post } from '@/lib/api'
import { formatDateTime, formatDecimal, formatNumber } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  Group,
  Instructor,
  Message,
  Page,
  Pool,
  ReportDefinition,
  ReportPreview,
  Student,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Yerel tipler (backend şemalarıyla birebir)
// ---------------------------------------------------------------------------
type PeriodKey =
  | 'today'
  | 'week'
  | 'month'
  | 'quarter'
  | 'half_year'
  | 'year'
  | 'last_year'
  | 'custom'

type ReportFormat = 'pdf' | 'xlsx' | 'csv' | 'json'

interface ReportRequest {
  report_key: string
  format: ReportFormat
  period: PeriodKey
  date_from: string | null
  date_to: string | null
  pool_id: number | null
  instructor_id: number | null
  group_id: number | null
  student_id: number | null
  membership_status: string | null
  language: 'tr' | 'en'
  include_charts: boolean
}

interface ReportTemplate {
  id: number
  name: string
  report_key: string
  filters: Record<string, unknown>
  description?: string | null
  is_shared: boolean
  owner_user_id?: number | null
}

/** Filtre formunun ham (string) hâli - şablonlara olduğu gibi kaydedilir */
interface FilterState {
  period: PeriodKey
  date_from: string
  date_to: string
  pool_id: string
  instructor_id: string
  group_id: string
  student_id: string
  membership_status: string
}

const PERIODS: PeriodKey[] = [
  'today',
  'week',
  'month',
  'quarter',
  'half_year',
  'year',
  'last_year',
  'custom',
]

const MEMBERSHIP_STATUSES = ['active', 'expired', 'frozen', 'cancelled', 'pending']

/** Dışa aktarma biçimleri - JSON kullanıcıya sunulmaz */
const EXPORT_FORMATS: Array<{ format: ReportFormat; labelKey: string }> = [
  { format: 'pdf', labelKey: 'reports.exportPdf' },
  { format: 'xlsx', labelKey: 'reports.exportExcel' },
  { format: 'csv', labelKey: 'reports.exportCsv' },
]

const EMPTY_FILTERS: FilterState = {
  period: 'month',
  date_from: '',
  date_to: '',
  pool_id: '',
  instructor_id: '',
  group_id: '',
  student_id: '',
  membership_status: '',
}

/** Şablondan gelen bilinmeyen değeri güvenle metne çevirir */
function readString(source: Record<string, unknown>, key: string): string {
  const value = source[key]
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  return ''
}

/** Toplam/özet anahtarlarını okunur hâle getirir (veri anahtarı, arayüz metni değil) */
function humanizeKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

/** Tablo hücresi değerini biçimlendirir */
function renderValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? formatNumber(value) : formatDecimal(value)
  }
  if (typeof value === 'boolean') return value ? '✓' : '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function ReportsPage() {
  const { t, i18n } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  const language: 'tr' | 'en' = i18n.language.startsWith('en') ? 'en' : 'tr'

  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const [studentSearch, setStudentSearch] = useState('')
  const [templateOpen, setTemplateOpen] = useState(false)
  const [templateForm, setTemplateForm] = useState({ name: '', description: '', is_shared: false })
  const [templateError, setTemplateError] = useState('')
  const [templateToDelete, setTemplateToDelete] = useState<ReportTemplate | null>(null)

  // --- Rapor kataloğu -------------------------------------------------------
  const definitionsQuery = useQuery({
    queryKey: ['report-definitions'],
    queryFn: () => get<ReportDefinition[]>('/reports/definitions'),
  })

  const definitions = definitionsQuery.data
  const definition = useMemo(
    () => (definitions ?? []).find((item) => item.key === selectedKey) ?? null,
    [definitions, selectedKey],
  )
  const needs = useMemo(() => new Set(definition?.filters ?? []), [definition])

  const grouped = useMemo(() => {
    const map = new Map<string, ReportDefinition[]>()
    for (const item of definitions ?? []) {
      const list = map.get(item.category) ?? []
      list.push(item)
      map.set(item.category, list)
    }
    return Array.from(map.entries())
  }, [definitions])

  // --- Filtre kaynakları (yalnızca gerekli olduğunda yüklenir) --------------
  const poolsQuery = useQuery({
    queryKey: ['report-pools'],
    queryFn: () => get<Pool[]>('/pools'),
    enabled: needs.has('pool'),
  })
  const instructorsQuery = useQuery({
    queryKey: ['report-instructors'],
    queryFn: () => get<Page<Instructor>>('/instructors', { page_size: 200, is_active: true }),
    enabled: needs.has('instructor'),
  })
  const groupsQuery = useQuery({
    queryKey: ['report-groups'],
    queryFn: () => get<Group[]>('/groups'),
    enabled: needs.has('group'),
  })
  const studentsQuery = useQuery({
    queryKey: ['report-students', studentSearch],
    queryFn: () =>
      get<Page<Student>>('/students', {
        q: studentSearch.trim() || undefined,
        page_size: 50,
      }),
    enabled: needs.has('student'),
  })

  // --- Kayıtlı şablonlar ----------------------------------------------------
  const templatesQuery = useQuery({
    queryKey: ['report-templates'],
    queryFn: () => get<ReportTemplate[]>('/reports/templates'),
  })

  // --- İstek gövdesi --------------------------------------------------------
  function buildRequest(format: ReportFormat): ReportRequest {
    const usesPeriod = needs.has('period')
    const usesDate = needs.has('date')
    return {
      report_key: selectedKey ?? '',
      format,
      period: usesPeriod ? filters.period : 'month',
      date_from: filters.date_from || null,
      // Tek günlük raporlarda bitiş tarihi başlangıçla aynıdır
      date_to: usesDate ? filters.date_from || null : filters.date_to || null,
      pool_id: needs.has('pool') && filters.pool_id ? Number(filters.pool_id) : null,
      instructor_id:
        needs.has('instructor') && filters.instructor_id ? Number(filters.instructor_id) : null,
      group_id: needs.has('group') && filters.group_id ? Number(filters.group_id) : null,
      student_id: needs.has('student') && filters.student_id ? Number(filters.student_id) : null,
      membership_status:
        needs.has('status') && filters.membership_status ? filters.membership_status : null,
      language,
      include_charts: true,
    }
  }

  const previewMutation = useMutation({
    mutationFn: () => post<ReportPreview>('/reports/preview', buildRequest('json')),
    onError: (error) => toastError(error),
  })

  const exportMutation = useMutation({
    mutationFn: (format: ReportFormat) =>
      download('/reports/export', buildRequest(format), `${selectedKey ?? 'rapor'}.${format}`),
    onSuccess: () => toastSuccess(t('common.success')),
    onError: (error) => toastError(error),
  })

  const saveTemplateMutation = useMutation({
    mutationFn: () =>
      post<ReportTemplate>('/reports/templates', {
        name: templateForm.name.trim(),
        report_key: selectedKey ?? '',
        filters: { ...filters },
        description: templateForm.description.trim() || null,
        is_shared: templateForm.is_shared,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-templates'] })
      setTemplateOpen(false)
      setTemplateForm({ name: '', description: '', is_shared: false })
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const deleteTemplateMutation = useMutation({
    mutationFn: (id: number) => del<Message>(`/reports/templates/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-templates'] })
      setTemplateToDelete(null)
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  // --- Yardımcılar ----------------------------------------------------------
  function selectReport(key: string) {
    setSelectedKey(key)
    setFilters(EMPTY_FILTERS)
    setStudentSearch('')
    previewMutation.reset()
  }

  function applyTemplate(template: ReportTemplate) {
    const source = template.filters ?? {}
    const rawPeriod = readString(source, 'period') as PeriodKey
    setSelectedKey(template.report_key)
    setFilters({
      period: PERIODS.includes(rawPeriod) ? rawPeriod : 'month',
      date_from: readString(source, 'date_from'),
      date_to: readString(source, 'date_to'),
      pool_id: readString(source, 'pool_id'),
      instructor_id: readString(source, 'instructor_id'),
      group_id: readString(source, 'group_id'),
      student_id: readString(source, 'student_id'),
      membership_status: readString(source, 'membership_status'),
    })
    setStudentSearch('')
    previewMutation.reset()
  }

  function updateFilter<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  function submitTemplate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!templateForm.name.trim()) {
      setTemplateError(t('common.required'))
      return
    }
    setTemplateError('')
    saveTemplateMutation.mutate()
  }

  const preview = previewMutation.data ?? null
  const canExport = can('report:export')
  const exportFormats = EXPORT_FORMATS.filter(
    (item) => definition?.supported_formats.includes(item.format) ?? false,
  )

  // --- Yükleme / hata -------------------------------------------------------
  if (definitionsQuery.isLoading) return <LoadingState />
  if (definitionsQuery.error) {
    return <ErrorState error={definitionsQuery.error} onRetry={definitionsQuery.refetch} />
  }

  return (
    <>
      <PageHeader
        title={t('reports.title')}
        subtitle={t('reports.subtitle')}
        icon={<FileText className="h-5 w-5" />}
        actions={
          <div className="no-print flex flex-wrap items-center gap-2">
            {definition && canExport
              && exportFormats.map((item) => (
                <button
                  key={item.format}
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => exportMutation.mutate(item.format)}
                  disabled={exportMutation.isPending}
                >
                  {exportMutation.isPending && exportMutation.variables === item.format ? (
                    <Spinner />
                  ) : item.format === 'xlsx' ? (
                    <FileSpreadsheet className="h-4 w-4" />
                  ) : item.format === 'pdf' ? (
                    <FileText className="h-4 w-4" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  {t(item.labelKey)}
                </button>
              ))}
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => window.print()}
              disabled={!preview}
            >
              <Printer className="h-4 w-4" />
              {t('common.print')}
            </button>
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-12">
        {/* Sol panel: rapor kataloğu ve şablonlar */}
        <div className="no-print space-y-4 lg:col-span-4 xl:col-span-3">
          <Card title={t('reports.reportType')} bodyClassName="p-0">
            {grouped.length === 0 ? (
              <EmptyState title={t('common.noData')} icon={<FileText className="h-6 w-6" />} />
            ) : (
              <div className="max-h-[520px] overflow-y-auto p-3">
                {grouped.map(([category, items]) => (
                  <div key={category} className="mb-4 last:mb-0">
                    <p className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                      {t(`reports.categories.${category}`, category)}
                    </p>
                    <div className="space-y-1.5">
                      {items.map((item) => {
                        const isActive = item.key === selectedKey
                        return (
                          <button
                            key={item.key}
                            type="button"
                            onClick={() => selectReport(item.key)}
                            className={clsx(
                              'w-full rounded-lg border px-3 py-2 text-left transition-colors',
                              isActive
                                ? 'border-brand-400 bg-brand-50 dark:border-brand-600 dark:bg-brand-900/30'
                                : 'border-slate-200 bg-white hover:border-brand-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-surface-dark-alt dark:hover:border-brand-700 dark:hover:bg-slate-800',
                            )}
                          >
                            <p
                              className={clsx(
                                'text-sm font-medium',
                                isActive
                                  ? 'text-brand-700 dark:text-brand-300'
                                  : 'text-slate-800 dark:text-slate-100',
                              )}
                            >
                              {language === 'tr' ? item.title_tr : item.title_en}
                            </p>
                            <p className="mt-0.5 text-xs leading-snug text-slate-500 dark:text-slate-400">
                              {language === 'tr' ? item.description_tr : item.description_en}
                            </p>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card
            title={t('reports.templates')}
            actions={
              definition && (
                <button
                  type="button"
                  className="btn-ghost btn-sm"
                  onClick={() => {
                    setTemplateError('')
                    setTemplateOpen(true)
                  }}
                  title={t('reports.saveTemplate')}
                >
                  <BookmarkPlus className="h-4 w-4" />
                </button>
              )
            }
            bodyClassName="p-3"
          >
            {templatesQuery.isLoading ? (
              <LoadingState />
            ) : templatesQuery.error ? (
              <ErrorState error={templatesQuery.error} onRetry={templatesQuery.refetch} />
            ) : (templatesQuery.data ?? []).length === 0 ? (
              <EmptyState title={t('common.noData')} icon={<BookmarkPlus className="h-6 w-6" />} />
            ) : (
              <ul className="space-y-1.5">
                {(templatesQuery.data ?? []).map((template) => (
                  <li
                    key={template.id}
                    className="flex items-start gap-2 rounded-lg border border-slate-200 p-2 dark:border-slate-700"
                  >
                    <button
                      type="button"
                      onClick={() => applyTemplate(template)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                        {template.name}
                      </p>
                      {template.description && (
                        <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                          {template.description}
                        </p>
                      )}
                      <p className="mt-0.5 text-xs text-slate-400">
                        {template.is_shared ? t('reports.shareTemplate') : template.report_key}
                      </p>
                    </button>
                    <button
                      type="button"
                      className="btn-ghost btn-sm shrink-0 text-rose-600 dark:text-rose-400"
                      onClick={() => setTemplateToDelete(template)}
                      title={t('common.delete')}
                      aria-label={t('common.delete')}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        {/* Sağ panel: filtreler ve önizleme */}
        <div className="space-y-4 lg:col-span-8 xl:col-span-9">
          {!definition ? (
            <Card>
              <EmptyState
                title={t('reports.noPreview')}
                description={t('reports.builder')}
                icon={<Eye className="h-6 w-6" />}
              />
            </Card>
          ) : (
            <>
              <Card
                title={t('common.filters')}
                className="no-print"
                actions={
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    onClick={() => previewMutation.mutate()}
                    disabled={previewMutation.isPending}
                  >
                    {previewMutation.isPending ? <Spinner /> : <Eye className="h-4 w-4" />}
                    {t('reports.preview')}
                  </button>
                }
              >
                {needs.size === 0 ? (
                  <Alert tone="info" title={t('reports.noPreview')} />
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {needs.has('period') && (
                      <Field label={t('statistics.period')}>
                        <select
                          className="select"
                          value={filters.period}
                          onChange={(event) =>
                            updateFilter('period', event.target.value as PeriodKey)
                          }
                        >
                          {PERIODS.map((period) => (
                            <option key={period} value={period}>
                              {t(`statistics.periods.${period}`)}
                            </option>
                          ))}
                        </select>
                      </Field>
                    )}

                    {needs.has('period') && filters.period === 'custom' && (
                      <>
                        <Field label={t('membership.startDate')}>
                          <input
                            type="date"
                            className="input"
                            value={filters.date_from}
                            onChange={(event) => updateFilter('date_from', event.target.value)}
                          />
                        </Field>
                        <Field label={t('membership.endDate')}>
                          <input
                            type="date"
                            className="input"
                            value={filters.date_to}
                            onChange={(event) => updateFilter('date_to', event.target.value)}
                          />
                        </Field>
                      </>
                    )}

                    {needs.has('date') && (
                      <Field label={t('common.date')}>
                        <input
                          type="date"
                          className="input"
                          value={filters.date_from}
                          onChange={(event) => updateFilter('date_from', event.target.value)}
                        />
                      </Field>
                    )}

                    {needs.has('pool') && (
                      <Field label={t('pool.singular')}>
                        <select
                          className="select"
                          value={filters.pool_id}
                          onChange={(event) => updateFilter('pool_id', event.target.value)}
                          disabled={poolsQuery.isLoading}
                        >
                          <option value="">{t('common.all')}</option>
                          {(poolsQuery.data ?? []).map((pool) => (
                            <option key={pool.id} value={pool.id}>
                              {pool.name}
                            </option>
                          ))}
                        </select>
                      </Field>
                    )}

                    {needs.has('instructor') && (
                      <Field label={t('instructor.singular')}>
                        <select
                          className="select"
                          value={filters.instructor_id}
                          onChange={(event) => updateFilter('instructor_id', event.target.value)}
                          disabled={instructorsQuery.isLoading}
                        >
                          <option value="">{t('common.all')}</option>
                          {(instructorsQuery.data?.items ?? []).map((instructor) => (
                            <option key={instructor.id} value={instructor.id}>
                              {instructor.full_name}
                            </option>
                          ))}
                        </select>
                      </Field>
                    )}

                    {needs.has('group') && (
                      <Field label={t('student.group')}>
                        <select
                          className="select"
                          value={filters.group_id}
                          onChange={(event) => updateFilter('group_id', event.target.value)}
                          disabled={groupsQuery.isLoading}
                        >
                          <option value="">{t('common.all')}</option>
                          {(groupsQuery.data ?? []).map((group) => (
                            <option key={group.id} value={group.id}>
                              {group.name}
                            </option>
                          ))}
                        </select>
                      </Field>
                    )}

                    {needs.has('student') && (
                      <>
                        <Field label={t('common.search')}>
                          <div className="relative">
                            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                            <input
                              type="search"
                              className="input pl-9"
                              value={studentSearch}
                              placeholder={t('common.search')}
                              onChange={(event) => setStudentSearch(event.target.value)}
                            />
                          </div>
                        </Field>
                        <Field
                          label={t('student.singular')}
                          hint={
                            studentsQuery.isLoading
                              ? t('common.loading')
                              : t('reports.rowCount', {
                                  count: studentsQuery.data?.items.length ?? 0,
                                })
                          }
                        >
                          <select
                            className="select"
                            value={filters.student_id}
                            onChange={(event) => updateFilter('student_id', event.target.value)}
                          >
                            <option value="">{t('common.all')}</option>
                            {(studentsQuery.data?.items ?? []).map((student) => (
                              <option key={student.id} value={student.id}>
                                {student.full_name} · {student.student_number}
                              </option>
                            ))}
                          </select>
                        </Field>
                      </>
                    )}

                    {needs.has('status') && (
                      <Field label={`${t('membership.singular')} · ${t('common.status')}`}>
                        <select
                          className="select"
                          value={filters.membership_status}
                          onChange={(event) =>
                            updateFilter('membership_status', event.target.value)
                          }
                        >
                          <option value="">{t('common.all')}</option>
                          {MEMBERSHIP_STATUSES.map((status) => (
                            <option key={status} value={status}>
                              {t(`membership.statuses.${status}`)}
                            </option>
                          ))}
                        </select>
                      </Field>
                    )}
                  </div>
                )}
              </Card>

              {/* Önizleme */}
              <Card
                title={preview ? preview.title : t('reports.preview')}
                bodyClassName="p-0"
                actions={
                  preview && (
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {preview.period_label} · {formatDateTime(preview.generated_at)}
                    </span>
                  )
                }
              >
                {previewMutation.isPending ? (
                  <LoadingState />
                ) : previewMutation.error ? (
                  <ErrorState
                    error={previewMutation.error}
                    onRetry={() => previewMutation.mutate()}
                  />
                ) : !preview ? (
                  <EmptyState title={t('reports.noPreview')} icon={<Eye className="h-6 w-6" />} />
                ) : preview.rows.length === 0 ? (
                  <EmptyState title={t('common.noData')} />
                ) : (
                  <>
                    <div className="max-h-[520px] overflow-y-auto">
                      <TableWrapper>
                        <thead className="sticky top-0 bg-white dark:bg-surface-dark-alt">
                          <tr>
                            <th className="w-12 text-right">#</th>
                            {preview.columns.map((column) => (
                              <th key={column.key}>{column.label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {preview.rows.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                              <td className="text-right text-xs text-slate-400">{rowIndex + 1}</td>
                              {preview.columns.map((column) => (
                                <td key={column.key} className="whitespace-nowrap">
                                  {renderValue(row[column.key])}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </TableWrapper>
                    </div>

                    <div className="border-t border-slate-200 px-5 py-3 dark:border-slate-700">
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {t('reports.rowCount', { count: preview.row_count })}
                      </p>
                    </div>

                    {Object.keys(preview.totals).length > 0 && (
                      <div className="border-t border-slate-200 px-5 py-3 dark:border-slate-700">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          {t('common.total')}
                        </p>
                        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                          {Object.entries(preview.totals).map(([key, value]) => (
                            <div
                              key={key}
                              className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800"
                            >
                              <p className="text-xs text-slate-500 dark:text-slate-400">
                                {humanizeKey(key)}
                              </p>
                              <p className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
                                {renderValue(value)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {Object.keys(preview.summary).length > 0 && (
                      <div className="border-t border-slate-200 px-5 py-3 dark:border-slate-700">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          {t('audit.summary')}
                        </p>
                        <dl className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
                          {Object.entries(preview.summary).map(([key, value]) => (
                            <div key={key} className="flex items-baseline justify-between gap-3">
                              <dt className="text-xs text-slate-500 dark:text-slate-400">
                                {humanizeKey(key)}
                              </dt>
                              <dd className="truncate text-sm text-slate-800 dark:text-slate-200">
                                {renderValue(value)}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}
                  </>
                )}
              </Card>
            </>
          )}
        </div>
      </div>

      {/* Şablon kaydetme */}
      <Modal
        open={templateOpen}
        onClose={() => setTemplateOpen(false)}
        title={t('reports.saveTemplate')}
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setTemplateOpen(false)}
              disabled={saveTemplateMutation.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              form="report-template-form"
              className="btn-primary"
              disabled={saveTemplateMutation.isPending}
            >
              {saveTemplateMutation.isPending && <Spinner />}
              {t('common.save')}
            </button>
          </>
        }
      >
        <form id="report-template-form" onSubmit={submitTemplate} className="space-y-3">
          <Field label={t('reports.templateName')} required error={templateError}>
            <input
              className="input"
              value={templateForm.name}
              onChange={(event) =>
                setTemplateForm((current) => ({ ...current, name: event.target.value }))
              }
              autoFocus
            />
          </Field>
          <Field label={t('common.description')}>
            <textarea
              className="textarea"
              rows={3}
              value={templateForm.description}
              onChange={(event) =>
                setTemplateForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 dark:border-slate-600"
              checked={templateForm.is_shared}
              onChange={(event) =>
                setTemplateForm((current) => ({ ...current, is_shared: event.target.checked }))
              }
            />
            {t('reports.shareTemplate')}
          </label>
        </form>
      </Modal>

      <ConfirmDialog
        open={templateToDelete !== null}
        onClose={() => setTemplateToDelete(null)}
        onConfirm={() => {
          if (templateToDelete) deleteTemplateMutation.mutate(templateToDelete.id)
        }}
        title={t('common.delete')}
        message={templateToDelete?.name ?? ''}
        confirmLabel={t('common.delete')}
        loading={deleteTemplateMutation.isPending}
      />
    </>
  )
}
