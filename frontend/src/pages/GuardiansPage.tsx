/** Veli yönetimi ve veli portalı / Guardian management and parent portal. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CalendarDays,
  ClipboardCheck,
  CreditCard,
  Eye,
  Pencil,
  Plus,
  Search,
  Trash2,
  Users,
  Wallet,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import {
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
  StatusBadge,
  TableWrapper,
} from '@/components/ui'
import { del, get, patch, post } from '@/lib/api'
import { formatCurrency, formatDate, formatNumber, formatTimeRange, initials } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type { Guardian, Message, Page, StudentBrief } from '@/lib/types'

// ---------------------------------------------------------------------------
// Veli portalı yanıt tipleri (GET /guardians/portal/my-children)
// ---------------------------------------------------------------------------
interface PortalLesson {
  id: number
  title: string
  start_at: string
  end_at: string
  pool?: string | null
  lane?: string | null
  instructor?: string | null
  status: string
}

interface PortalAttendance {
  lesson_title?: string | null
  date?: string | null
  status: string
}

interface PortalMembership {
  package_name?: string | null
  remaining_credits?: number | null
  end_date?: string | null
  days_remaining?: number | null
  status?: string | null
}

interface PortalChild {
  student: StudentBrief
  upcoming_lessons: PortalLesson[]
  recent_attendance: PortalAttendance[]
  membership?: PortalMembership | null
  outstanding_balance: number
  notes?: string | null
}

interface GuardianPortal {
  guardian: string
  children: PortalChild[]
}

// ---------------------------------------------------------------------------
// Form yardımcıları
// ---------------------------------------------------------------------------
const RELATIONSHIPS = ['mother', 'father', 'parent', 'grandparent', 'sibling', 'other']

interface GuardianForm {
  first_name: string
  last_name: string
  relationship_type: string
  phone: string
  secondary_phone: string
  email: string
  occupation: string
  address: string
  notes: string
}

const EMPTY_FORM: GuardianForm = {
  first_name: '',
  last_name: '',
  relationship_type: 'mother',
  phone: '',
  secondary_phone: '',
  email: '',
  occupation: '',
  address: '',
  notes: '',
}

/** Boş metinleri null'a çevirerek backend'e uygun gövde üretir */
function toPayload(form: GuardianForm) {
  const clean = (value: string): string | null => (value.trim() ? value.trim() : null)
  return {
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    relationship_type: form.relationship_type,
    phone: form.phone.trim(),
    secondary_phone: clean(form.secondary_phone),
    email: clean(form.email),
    occupation: clean(form.occupation),
    address: clean(form.address),
    notes: clean(form.notes),
  }
}

// ---------------------------------------------------------------------------
// Veli portalı: oturum açan velinin çocuk kartları
// ---------------------------------------------------------------------------
function ChildCard({ child }: { child: PortalChild }) {
  const { t } = useTranslation()
  const membership = child.membership ?? null
  const hasDebt = child.outstanding_balance > 0

  return (
    <Card
      className="h-full"
      title={
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
            {initials(child.student.full_name)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
              {child.student.full_name}
            </p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">
              {child.student.student_number} · {t(`swimLevel.${child.student.swim_level}`, child.student.swim_level)}
            </p>
          </div>
        </div>
      }
      actions={
        <StatusBadge
          status={child.student.status}
          label={t(`studentStatus.${child.student.status}`, child.student.status)}
        />
      }
    >
      {/* Üyelik ve bakiye özeti */}
      <div className="mb-4 grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
          <p className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
            <CreditCard className="h-3.5 w-3.5" />
            {t('student.activeMembership')}
          </p>
          {membership ? (
            <div className="mt-1.5 space-y-0.5 text-sm text-slate-800 dark:text-slate-200">
              <p className="truncate font-medium">{membership.package_name ?? '—'}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('membership.remainingCredits')}:{' '}
                {membership.remaining_credits === null || membership.remaining_credits === undefined
                  ? t('membership.unlimited')
                  : formatNumber(membership.remaining_credits)}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('membership.endDate')}: {formatDate(membership.end_date)}
                {membership.days_remaining !== null && membership.days_remaining !== undefined
                  ? ` · ${t('membership.daysRemaining')}: ${formatNumber(membership.days_remaining)}`
                  : ''}
              </p>
              {membership.status && (
                <StatusBadge
                  status={membership.status}
                  label={t(`membership.statuses.${membership.status}`, membership.status)}
                />
              )}
            </div>
          ) : (
            <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">
              {t('student.noMembership')}
            </p>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
          <p className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
            <Wallet className="h-3.5 w-3.5" />
            {t('student.outstandingBalance')}
          </p>
          <p
            className={
              hasDebt
                ? 'mt-1.5 text-xl font-semibold text-rose-600 dark:text-rose-400'
                : 'mt-1.5 text-xl font-semibold text-emerald-600 dark:text-emerald-400'
            }
          >
            {formatCurrency(child.outstanding_balance)}
          </p>
          {child.notes && (
            <p className="mt-1.5 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
              {child.notes}
            </p>
          )}
        </div>
      </div>

      {/* Yaklaşan dersler */}
      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        <CalendarDays className="h-3.5 w-3.5" />
        {t('guardian.upcomingLessons')}
      </p>
      {child.upcoming_lessons.length === 0 ? (
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">{t('calendar.noEvents')}</p>
      ) : (
        <ul className="mb-4 space-y-1.5">
          {child.upcoming_lessons.slice(0, 5).map((lesson) => (
            <li
              key={lesson.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/60"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-800 dark:text-slate-200">{lesson.title}</p>
                <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                  {formatDate(lesson.start_at)} · {formatTimeRange(lesson.start_at, lesson.end_at)}
                  {lesson.pool ? ` · ${lesson.pool}` : ''}
                  {lesson.lane ? ` · ${lesson.lane}` : ''}
                  {lesson.instructor ? ` · ${lesson.instructor}` : ''}
                </p>
              </div>
              <StatusBadge
                status={lesson.status}
                label={t(`lesson.statuses.${lesson.status}`, lesson.status)}
              />
            </li>
          ))}
        </ul>
      )}

      {/* Son yoklamalar */}
      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        <ClipboardCheck className="h-3.5 w-3.5" />
        {t('guardian.recentAttendance')}
      </p>
      {child.recent_attendance.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
      ) : (
        <ul className="space-y-1">
          {child.recent_attendance.slice(0, 6).map((record, index) => (
            <li
              key={`${record.date ?? 'x'}-${index}`}
              className="flex items-center justify-between gap-2 text-sm"
            >
              <span className="min-w-0 truncate text-slate-700 dark:text-slate-300">
                {record.lesson_title ?? '—'}
                <span className="ml-2 text-xs text-slate-400">{formatDate(record.date)}</span>
              </span>
              <StatusBadge
                status={record.status}
                label={t(`attendance.statuses.${record.status}`, record.status)}
              />
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Sayfa
// ---------------------------------------------------------------------------
export default function GuardiansPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const can = useAuth((state) => state.can)
  const hasRole = useAuth((state) => state.hasRole)
  const isParent = hasRole('parent')

  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Guardian | null>(null)
  const [form, setForm] = useState<GuardianForm>(EMPTY_FORM)
  const [errors, setErrors] = useState<Partial<Record<keyof GuardianForm, string>>>({})
  const [detailId, setDetailId] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Guardian | null>(null)

  // Arama kutusunu geciktirerek gereksiz istekleri engelle
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const listQuery = useQuery({
    queryKey: ['guardians', query, page, pageSize],
    queryFn: () =>
      get<Page<Guardian>>('/guardians', {
        q: query || undefined,
        page,
        page_size: pageSize,
      }),
  })

  const detailQuery = useQuery({
    queryKey: ['guardian', detailId],
    queryFn: () => get<Guardian>(`/guardians/${detailId}`),
    enabled: detailId !== null,
  })

  const portalQuery = useQuery({
    queryKey: ['guardian-portal'],
    queryFn: () => get<GuardianPortal>('/guardians/portal/my-children'),
    enabled: isParent,
  })

  const saveMutation = useMutation({
    mutationFn: (payload: ReturnType<typeof toPayload>) =>
      editing
        ? patch<Guardian>(`/guardians/${editing.id}`, payload)
        : post<Guardian>('/guardians', { ...payload, student_ids: [] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['guardians'] })
      queryClient.invalidateQueries({ queryKey: ['guardian'] })
      toastSuccess(t('common.success'))
      setFormOpen(false)
      setEditing(null)
      setForm(EMPTY_FORM)
    },
    onError: (error: unknown) => toastError(error),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => del<Message>(`/guardians/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['guardians'] })
      toastSuccess(t('common.success'))
      setDeleteTarget(null)
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

  function openEdit(guardian: Guardian) {
    setEditing(guardian)
    setForm({
      first_name: guardian.first_name,
      last_name: guardian.last_name,
      relationship_type: guardian.relationship_type || 'mother',
      phone: guardian.phone,
      secondary_phone: guardian.secondary_phone ?? '',
      email: guardian.email ?? '',
      occupation: guardian.occupation ?? '',
      address: guardian.address ?? '',
      notes: guardian.notes ?? '',
    })
    setErrors({})
    setFormOpen(true)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors: Partial<Record<keyof GuardianForm, string>> = {}
    if (!form.first_name.trim()) nextErrors.first_name = t('common.required')
    if (!form.last_name.trim()) nextErrors.last_name = t('common.required')
    if (form.phone.trim().length < 5) nextErrors.phone = t('common.required')
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    saveMutation.mutate(toPayload(form))
  }

  function updateField(key: keyof GuardianForm, value: string) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  const guardians = listQuery.data?.items ?? []
  const detail = detailQuery.data ?? null

  return (
    <>
      <PageHeader
        title={t('guardian.title')}
        icon={<Users className="h-5 w-5" />}
        actions={
          can('guardian:write') && (
            <button type="button" className="btn-primary" onClick={openCreate}>
              <Plus className="h-4 w-4" />
              {t('guardian.new')}
            </button>
          )
        }
      />

      {/* Veli portalı — yalnızca 'parent' rolündeki kullanıcılar için */}
      {isParent && (
        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-slate-100">
            <ClipboardCheck className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            {t('guardian.portal')}
            {portalQuery.data?.guardian && (
              <span className="text-sm font-normal text-slate-500 dark:text-slate-400">
                · {portalQuery.data.guardian}
              </span>
            )}
          </h2>

          {portalQuery.isLoading ? (
            <LoadingState />
          ) : portalQuery.error ? (
            <Card>
              <ErrorState error={portalQuery.error} onRetry={portalQuery.refetch} />
            </Card>
          ) : (portalQuery.data?.children.length ?? 0) === 0 ? (
            <Card>
              <EmptyState title={t('guardian.myChildren')} icon={<Users className="h-6 w-6" />} />
            </Card>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {portalQuery.data?.children.map((child) => (
                <ChildCard key={child.student.id} child={child} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* Veli listesi */}
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
          {searchInput && (
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => setSearchInput('')}
            >
              {t('common.clearFilters')}
            </button>
          )}
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {t('common.total')}: {formatNumber(listQuery.data?.total ?? 0)}
          </span>
        </div>

        {listQuery.isLoading ? (
          <LoadingState />
        ) : listQuery.error ? (
          <ErrorState error={listQuery.error} onRetry={listQuery.refetch} />
        ) : guardians.length === 0 ? (
          <EmptyState
            title={t('common.noResults')}
            icon={<Users className="h-6 w-6" />}
            action={
              can('guardian:write') ? (
                <button type="button" className="btn-secondary btn-sm" onClick={openCreate}>
                  <Plus className="h-4 w-4" />
                  {t('guardian.new')}
                </button>
              ) : undefined
            }
          />
        ) : (
          <>
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('student.fullName')}</th>
                  <th>{t('guardian.relationship')}</th>
                  <th>{t('common.phone')}</th>
                  <th className="hidden md:table-cell">{t('common.email')}</th>
                  <th>{t('guardian.children')}</th>
                  <th className="text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {guardians.map((guardian) => (
                  <tr key={guardian.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                          {initials(guardian.full_name)}
                        </span>
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {guardian.full_name}
                        </span>
                        {guardian.is_demo && <DemoBadge />}
                      </div>
                    </td>
                    <td>
                      <Badge tone="neutral">
                        {t(`guardian.relationships.${guardian.relationship_type}`, guardian.relationship_type)}
                      </Badge>
                    </td>
                    <td className="whitespace-nowrap">{guardian.phone}</td>
                    <td className="hidden md:table-cell text-xs text-slate-500 dark:text-slate-400">
                      {guardian.email ?? '—'}
                    </td>
                    <td>
                      <div className="flex flex-col gap-1">
                        <Badge tone="info">
                          {t('guardian.childCount', { count: guardian.students.length })}
                        </Badge>
                        {guardian.students.length > 0 && (
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {guardian.students.map((student) => student.full_name).join(', ')}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          className="btn-ghost btn-sm"
                          onClick={() => setDetailId(guardian.id)}
                          title={t('common.details')}
                          aria-label={t('common.details')}
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        {can('guardian:write') && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm"
                            onClick={() => openEdit(guardian)}
                            title={t('common.edit')}
                            aria-label={t('common.edit')}
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        )}
                        {can('guardian:delete') && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            onClick={() => setDeleteTarget(guardian)}
                            title={t('common.delete')}
                            aria-label={t('common.delete')}
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

      {/* Yeni / düzenle formu */}
      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `${t('common.edit')} — ${editing.full_name}` : t('guardian.new')}
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
              form="guardian-form"
              className="btn-primary"
              disabled={saveMutation.isPending}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <form id="guardian-form" onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
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
          <Field label={t('guardian.relationship')} required>
            <select
              className="select"
              value={form.relationship_type}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                updateField('relationship_type', event.target.value)
              }
            >
              {RELATIONSHIPS.map((code) => (
                <option key={code} value={code}>
                  {t(`guardian.relationships.${code}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('common.phone')} required error={errors.phone}>
            <input
              className="input"
              value={form.phone}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('phone', event.target.value)
              }
            />
          </Field>
          <Field label={t('guardian.secondaryPhone')}>
            <input
              className="input"
              value={form.secondary_phone}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('secondary_phone', event.target.value)
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
          <Field label={t('guardian.occupation')}>
            <input
              className="input"
              value={form.occupation}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('occupation', event.target.value)
              }
            />
          </Field>
          <Field label={t('common.address')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={2}
              value={form.address}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                updateField('address', event.target.value)
              }
            />
          </Field>
          <Field label={t('common.notes')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={3}
              value={form.notes}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                updateField('notes', event.target.value)
              }
            />
          </Field>
        </form>
      </Modal>

      {/* Detay modalı */}
      <Modal
        open={detailId !== null}
        onClose={() => setDetailId(null)}
        title={detail ? detail.full_name : t('guardian.singular')}
        size="lg"
        footer={
          detail && can('guardian:write') ? (
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
          ) : undefined
        }
      >
        {detailQuery.isLoading ? (
          <LoadingState />
        ) : detailQuery.error ? (
          <ErrorState error={detailQuery.error} onRetry={detailQuery.refetch} />
        ) : detail ? (
          <div className="space-y-5">
            <dl className="grid gap-3 sm:grid-cols-2">
              {[
                { label: t('guardian.relationship'), value: t(`guardian.relationships.${detail.relationship_type}`, detail.relationship_type) },
                { label: t('common.phone'), value: detail.phone },
                { label: t('guardian.secondaryPhone'), value: detail.secondary_phone ?? '—' },
                { label: t('common.email'), value: detail.email ?? '—' },
                { label: t('guardian.occupation'), value: detail.occupation ?? '—' },
                { label: t('common.address'), value: detail.address ?? '—' },
              ].map((row) => (
                <div key={row.label} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">{row.label}</dt>
                  <dd className="mt-0.5 break-words text-sm text-slate-800 dark:text-slate-200">
                    {row.value}
                  </dd>
                </div>
              ))}
            </dl>

            {detail.notes && (
              <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                <p className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {t('common.notes')}
                </p>
                {detail.notes}
              </div>
            )}

            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                {t('guardian.children')}
              </h3>
              {detail.students.length === 0 ? (
                <EmptyState title={t('common.noData')} icon={<Users className="h-6 w-6" />} />
              ) : (
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('student.number')}</th>
                      <th>{t('student.fullName')}</th>
                      <th>{t('student.swimLevel')}</th>
                      <th>{t('student.age')}</th>
                      <th>{t('common.status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.students.map((student) => (
                      <tr key={student.id}>
                        <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                          {student.student_number}
                        </td>
                        <td>
                          <Link
                            to={`/students/${student.id}`}
                            className="font-medium text-brand-600 hover:underline dark:text-brand-400"
                            onClick={() => setDetailId(null)}
                          >
                            {student.full_name}
                          </Link>
                        </td>
                        <td className="text-xs text-slate-500 dark:text-slate-400">
                          {t(`swimLevel.${student.swim_level}`, student.swim_level)}
                        </td>
                        <td>{student.age !== null && student.age !== undefined ? formatNumber(student.age) : '—'}</td>
                        <td>
                          <StatusBadge
                            status={student.status}
                            label={t(`studentStatus.${student.status}`, student.status)}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableWrapper>
              )}
            </div>
          </div>
        ) : (
          <EmptyState title={t('common.noData')} />
        )}
      </Modal>

      {/* Silme onayı */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        title={t('common.delete')}
        message={`${t('guardian.singular')}: ${deleteTarget?.full_name ?? ''}`}
        confirmLabel={t('common.delete')}
        loading={deleteMutation.isPending}
      />
    </>
  )
}
