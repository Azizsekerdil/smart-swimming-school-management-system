/** Öğrenci listesi, filtreleme ve kayıt yönetimi / Student list screen. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Trash2, UserPlus, Users, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
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
  Modal,
  PageHeader,
  Pagination,
  Spinner,
  StatCard,
  StatusBadge,
  TableSkeleton,
  TableWrapper,
  type BadgeTone,
} from '@/components/ui'
import { del, get, patch, post } from '@/lib/api'
import { formatDate, formatNumber } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type {
  Gender,
  Group,
  Instructor,
  Message,
  Page,
  Student,
  StudentStatus,
  SwimLevel,
} from '@/lib/types'

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------
const LEVELS: SwimLevel[] = [
  'beginner',
  'elementary',
  'intermediate',
  'advanced',
  'competitive',
  'elite',
]
const STATUSES: StudentStatus[] = ['active', 'passive', 'trial', 'frozen', 'left']
const GENDERS: Gender[] = ['female', 'male', 'unspecified']

const LEVEL_TONES: Record<SwimLevel, BadgeTone> = {
  beginner: 'neutral',
  elementary: 'neutral',
  intermediate: 'info',
  advanced: 'info',
  competitive: 'success',
  elite: 'warning',
}

/** /students/stats/overview yanıtı */
interface StudentStatsOverview {
  total: number
  by_status: Record<string, number>
  by_level: Record<string, number>
  new_this_month: number
  active: number
}

/** Form alanları metin olarak tutulur, gönderimde dönüştürülür */
interface StudentFormState {
  first_name: string
  last_name: string
  birth_date: string
  gender: Gender
  phone: string
  email: string
  address: string
  swim_level: SwimLevel
  status: StudentStatus
  group_id: string
  primary_instructor_id: string
  emergency_contact_name: string
  emergency_contact_phone: string
  goals: string
  notes: string
  health_notes: string
  special_needs: string
  consent_given: boolean
}

const EMPTY_FORM: StudentFormState = {
  first_name: '',
  last_name: '',
  birth_date: '',
  gender: 'unspecified',
  phone: '',
  email: '',
  address: '',
  swim_level: 'beginner',
  status: 'active',
  group_id: '',
  primary_instructor_id: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  goals: '',
  notes: '',
  health_notes: '',
  special_needs: '',
  consent_given: false,
}

/** Boş metinleri null'a çevirir (backend null bekler) */
function textOrNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function idOrNull(value: string): number | null {
  return value === '' ? null : Number(value)
}

function toFormState(student: Student): StudentFormState {
  return {
    first_name: student.first_name,
    last_name: student.last_name,
    birth_date: student.birth_date ?? '',
    gender: student.gender,
    phone: student.phone ?? '',
    email: student.email ?? '',
    address: student.address ?? '',
    swim_level: student.swim_level,
    status: student.status,
    group_id: student.group_id === null || student.group_id === undefined ? '' : String(student.group_id),
    primary_instructor_id:
      student.primary_instructor_id === null || student.primary_instructor_id === undefined
        ? ''
        : String(student.primary_instructor_id),
    emergency_contact_name: student.emergency_contact_name ?? '',
    emergency_contact_phone: student.emergency_contact_phone ?? '',
    goals: student.goals ?? '',
    notes: student.notes ?? '',
    health_notes: student.health_notes ?? '',
    special_needs: student.special_needs ?? '',
    consent_given: student.consent_given,
  }
}

// ---------------------------------------------------------------------------
export default function StudentsPage() {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)
  const queryClient = useQueryClient()

  // --- Filtre durumu ---
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const [level, setLevel] = useState('')
  const [groupId, setGroupId] = useState('')
  const [instructorId, setInstructorId] = useState('')
  const [minAge, setMinAge] = useState('')
  const [maxAge, setMaxAge] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  // --- Modal / form durumu ---
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Student | null>(null)
  const [form, setForm] = useState<StudentFormState>(EMPTY_FORM)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [deleteTarget, setDeleteTarget] = useState<Student | null>(null)

  const canWrite = can('student:write')
  const canDelete = can('student:delete')
  const canSensitive = can('student:read_sensitive')

  // Arama kutusu 300 ms gecikmeyle sorguya yansır
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(searchInput.trim())
      setPage(1)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const filters = useMemo(
    () => ({
      q: query || undefined,
      status: status || undefined,
      swim_level: level || undefined,
      group_id: groupId ? Number(groupId) : undefined,
      instructor_id: instructorId ? Number(instructorId) : undefined,
      min_age: minAge ? Number(minAge) : undefined,
      max_age: maxAge ? Number(maxAge) : undefined,
    }),
    [query, status, level, groupId, instructorId, minAge, maxAge],
  )

  const hasFilters =
    query !== '' ||
    status !== '' ||
    level !== '' ||
    groupId !== '' ||
    instructorId !== '' ||
    minAge !== '' ||
    maxAge !== ''

  // --- Veri çekme ---
  const studentsQuery = useQuery({
    queryKey: ['students', page, pageSize, filters],
    queryFn: () =>
      get<Page<Student>>('/students', {
        page,
        page_size: pageSize,
        sort_by: 'last_name',
        sort_dir: 'asc',
        ...filters,
      }),
  })

  const statsQuery = useQuery({
    queryKey: ['students', 'stats'],
    queryFn: () => get<StudentStatsOverview>('/students/stats/overview'),
  })

  const groupsQuery = useQuery({
    queryKey: ['groups'],
    queryFn: () => get<Group[]>('/groups'),
    staleTime: 5 * 60_000,
  })

  const instructorsQuery = useQuery({
    queryKey: ['instructors', 'options'],
    queryFn: () => get<Page<Instructor>>('/instructors', { page: 1, page_size: 200, is_active: true }),
    staleTime: 5 * 60_000,
  })

  const groups = groupsQuery.data ?? []
  const instructors = instructorsQuery.data?.items ?? []

  // --- Mutasyonlar ---
  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        birth_date: textOrNull(form.birth_date),
        gender: form.gender,
        phone: textOrNull(form.phone),
        email: textOrNull(form.email),
        address: textOrNull(form.address),
        swim_level: form.swim_level,
        status: form.status,
        group_id: idOrNull(form.group_id),
        primary_instructor_id: idOrNull(form.primary_instructor_id),
        emergency_contact_name: textOrNull(form.emergency_contact_name),
        emergency_contact_phone: textOrNull(form.emergency_contact_phone),
        goals: textOrNull(form.goals),
        notes: textOrNull(form.notes),
        consent_given: form.consent_given,
      }
      // Hassas alanlar yalnızca yetkili kullanıcı tarafından gönderilir
      if (canSensitive) {
        payload.health_notes = textOrNull(form.health_notes)
        payload.special_needs = textOrNull(form.special_needs)
      }
      return editing
        ? patch<Student>(`/students/${editing.id}`, payload)
        : post<Student>('/students', payload)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students'] })
      toastSuccess(t('common.success'))
      setFormOpen(false)
      setEditing(null)
      setForm(EMPTY_FORM)
      setErrors({})
    },
    onError: (error: unknown) => toastError(error, t('errors.generic')),
  })

  const deleteMutation = useMutation({
    mutationFn: (studentId: number) => del<Message>(`/students/${studentId}`, { hard: false }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students'] })
      toastSuccess(t('common.success'))
      setDeleteTarget(null)
    },
    onError: (error: unknown) => toastError(error, t('errors.generic')),
  })

  // --- Yardımcılar ---
  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setErrors({})
    setFormOpen(true)
  }

  function openEdit(student: Student) {
    setEditing(student)
    setForm(toFormState(student))
    setErrors({})
    setFormOpen(true)
  }

  function clearFilters() {
    setSearchInput('')
    setStatus('')
    setLevel('')
    setGroupId('')
    setInstructorId('')
    setMinAge('')
    setMaxAge('')
    setPage(1)
  }

  function updateField<K extends keyof StudentFormState>(key: K, value: StudentFormState[K]) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors: Record<string, string> = {}
    if (!form.first_name.trim()) nextErrors.first_name = t('common.required')
    if (!form.last_name.trim()) nextErrors.last_name = t('common.required')
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    saveMutation.mutate()
  }

  const stats = statsQuery.data
  const items = studentsQuery.data?.items ?? []
  const total = studentsQuery.data?.total ?? 0

  return (
    <>
      <PageHeader
        title={t('student.title')}
        subtitle={t('common.total') + ': ' + formatNumber(stats?.total ?? total)}
        icon={<Users className="h-5 w-5" />}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={openCreate}>
              <Plus className="h-4 w-4" />
              {t('student.new')}
            </button>
          )
        }
      />

      {/* Özet sayaçlar */}
      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={t('common.total')}
          value={formatNumber(stats?.total ?? 0)}
          icon={<Users className="h-5 w-5" />}
          tone="brand"
        />
        <StatCard
          label={t('common.active')}
          value={formatNumber(stats?.active ?? 0)}
          hint={t('studentStatus.passive') + ': ' + formatNumber(stats?.by_status.passive ?? 0)}
          icon={<Users className="h-5 w-5" />}
          tone="success"
        />
        <StatCard
          label={t('dashboard.newRegistrations')}
          value={formatNumber(stats?.new_this_month ?? 0)}
          hint={t('common.thisMonth')}
          icon={<UserPlus className="h-5 w-5" />}
          tone="neutral"
        />
        <StatCard
          label={t('studentStatus.trial')}
          value={formatNumber(stats?.by_status.trial ?? 0)}
          hint={t('studentStatus.frozen') + ': ' + formatNumber(stats?.by_status.frozen ?? 0)}
          icon={<Users className="h-5 w-5" />}
          tone="warning"
        />
      </div>

      {/* Filtre çubuğu */}
      <Card
        title={t('common.filters')}
        className="mb-4"
        actions={
          hasFilters && (
            <button type="button" className="btn-ghost btn-sm" onClick={clearFilters}>
              <X className="h-3.5 w-3.5" />
              {t('common.clearFilters')}
            </button>
          )
        }
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <Field label={t('common.search')} className="xl:col-span-2">
            <input
              type="search"
              className="input"
              value={searchInput}
              placeholder={t('common.searchPlaceholder')}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setSearchInput(event.target.value)
              }
            />
          </Field>

          <Field label={t('common.status')}>
            <select
              className="select"
              value={status}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                setStatus(event.target.value)
                setPage(1)
              }}
            >
              <option value="">{t('common.all')}</option>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {t(`studentStatus.${value}`)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('student.swimLevel')}>
            <select
              className="select"
              value={level}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                setLevel(event.target.value)
                setPage(1)
              }}
            >
              <option value="">{t('common.all')}</option>
              {LEVELS.map((value) => (
                <option key={value} value={value}>
                  {t(`swimLevel.${value}`)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('student.group')}>
            <select
              className="select"
              value={groupId}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                setGroupId(event.target.value)
                setPage(1)
              }}
            >
              <option value="">{t('common.all')}</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('student.instructor')}>
            <select
              className="select"
              value={instructorId}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) => {
                setInstructorId(event.target.value)
                setPage(1)
              }}
            >
              <option value="">{t('common.all')}</option>
              {instructors.map((instructor) => (
                <option key={instructor.id} value={instructor.id}>
                  {instructor.full_name}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('student.age')} className="lg:col-span-2 xl:col-span-2">
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={120}
                className="input"
                value={minAge}
                aria-label={t('student.age')}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                  setMinAge(event.target.value)
                  setPage(1)
                }}
              />
              <span className="text-slate-400">–</span>
              <input
                type="number"
                min={0}
                max={120}
                className="input"
                value={maxAge}
                aria-label={t('student.age')}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                  setMaxAge(event.target.value)
                  setPage(1)
                }}
              />
            </div>
          </Field>
        </div>
      </Card>

      {/* Liste */}
      <Card bodyClassName="p-0">
        {studentsQuery.isLoading ? (
          <TableSkeleton rows={8} cols={7} />
        ) : studentsQuery.error ? (
          <ErrorState error={studentsQuery.error} onRetry={() => void studentsQuery.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            title={hasFilters ? t('common.noResults') : t('common.noData')}
            icon={<Users className="h-6 w-6" />}
            action={
              hasFilters ? (
                <button type="button" className="btn-secondary btn-sm" onClick={clearFilters}>
                  {t('common.clearFilters')}
                </button>
              ) : canWrite ? (
                <button type="button" className="btn-primary btn-sm" onClick={openCreate}>
                  <Plus className="h-4 w-4" />
                  {t('student.new')}
                </button>
              ) : undefined
            }
          />
        ) : (
          <>
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('student.number')}</th>
                  <th>{t('student.fullName')}</th>
                  <th className="hidden sm:table-cell">{t('student.age')}</th>
                  <th>{t('student.swimLevel')}</th>
                  <th className="hidden lg:table-cell">{t('student.group')}</th>
                  <th className="hidden xl:table-cell">{t('student.instructor')}</th>
                  <th>{t('common.status')}</th>
                  <th className="hidden md:table-cell">{t('student.registrationDate')}</th>
                  <th className="text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((student) => (
                  <tr key={student.id}>
                    <td className="whitespace-nowrap font-mono text-xs text-slate-500 dark:text-slate-400">
                      {student.student_number}
                    </td>
                    <td>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to={`/students/${student.id}`}
                          className="font-medium text-slate-900 hover:text-brand-600 dark:text-slate-100 dark:hover:text-brand-400"
                        >
                          {student.full_name}
                        </Link>
                        {student.is_demo && <DemoBadge />}
                      </div>
                      {student.phone && (
                        <p className="text-xs text-slate-500 dark:text-slate-400">{student.phone}</p>
                      )}
                    </td>
                    <td className="hidden whitespace-nowrap sm:table-cell">
                      {student.age !== null && student.age !== undefined ? student.age : '—'}
                    </td>
                    <td>
                      <Badge tone={LEVEL_TONES[student.swim_level]}>
                        {t(`swimLevel.${student.swim_level}`)}
                      </Badge>
                    </td>
                    <td className="hidden lg:table-cell text-xs text-slate-500 dark:text-slate-400">
                      {student.group?.name ?? '—'}
                    </td>
                    <td className="hidden xl:table-cell text-xs text-slate-500 dark:text-slate-400">
                      {student.primary_instructor?.full_name ?? '—'}
                    </td>
                    <td>
                      <StatusBadge
                        status={student.status}
                        label={t(`studentStatus.${student.status}`)}
                      />
                    </td>
                    <td className="hidden whitespace-nowrap md:table-cell text-xs text-slate-500 dark:text-slate-400">
                      {formatDate(student.registration_date)}
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-1">
                        {canWrite && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm"
                            onClick={() => openEdit(student)}
                            title={t('common.edit')}
                            aria-label={t('common.edit')}
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        )}
                        {canDelete && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            onClick={() => setDeleteTarget(student)}
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
              total={total}
              onPageChange={setPage}
              onPageSizeChange={(size) => {
                setPageSize(size)
                setPage(1)
              }}
            />
          </>
        )}
      </Card>

      {/* Oluşturma / düzenleme formu */}
      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? t('student.edit') : t('student.new')}
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
              form="student-form"
              className="btn-primary"
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending && <Spinner />}
              {t('common.save')}
            </button>
          </>
        }
      >
        <form id="student-form" onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-2">
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

          <Field label={t('student.birthDate')}>
            <input
              type="date"
              className="input"
              value={form.birth_date}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('birth_date', event.target.value)
              }
            />
          </Field>
          <Field label={t('student.gender')}>
            <select
              className="select"
              value={form.gender}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                updateField('gender', event.target.value as Gender)
              }
            >
              {GENDERS.map((value) => (
                <option key={value} value={value}>
                  {t(`gender.${value}`)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('common.phone')}>
            <input
              type="tel"
              className="input"
              value={form.phone}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('phone', event.target.value)
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

          <Field label={t('student.swimLevel')}>
            <select
              className="select"
              value={form.swim_level}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                updateField('swim_level', event.target.value as SwimLevel)
              }
            >
              {LEVELS.map((value) => (
                <option key={value} value={value}>
                  {t(`swimLevel.${value}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('common.status')}>
            <select
              className="select"
              value={form.status}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                updateField('status', event.target.value as StudentStatus)
              }
            >
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {t(`studentStatus.${value}`)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('student.group')}>
            <select
              className="select"
              value={form.group_id}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                updateField('group_id', event.target.value)
              }
            >
              <option value="">{t('common.none')}</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('student.instructor')}>
            <select
              className="select"
              value={form.primary_instructor_id}
              onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                updateField('primary_instructor_id', event.target.value)
              }
            >
              <option value="">{t('common.none')}</option>
              {instructors.map((instructor) => (
                <option key={instructor.id} value={instructor.id}>
                  {instructor.full_name}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('student.emergencyContact')}>
            <input
              className="input"
              value={form.emergency_contact_name}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('emergency_contact_name', event.target.value)
              }
            />
          </Field>
          <Field label={t('student.emergencyPhone')}>
            <input
              type="tel"
              className="input"
              value={form.emergency_contact_phone}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                updateField('emergency_contact_phone', event.target.value)
              }
            />
          </Field>

          <Field label={t('student.goals')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={2}
              value={form.goals}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                updateField('goals', event.target.value)
              }
            />
          </Field>
          <Field label={t('common.notes')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={2}
              value={form.notes}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                updateField('notes', event.target.value)
              }
            />
          </Field>

          {/* Hassas alanlar yalnızca student:read_sensitive iznine açıktır */}
          {canSensitive && (
            <>
              <Field label={t('student.healthNotes')} className="sm:col-span-2">
                <textarea
                  className="textarea"
                  rows={2}
                  value={form.health_notes}
                  onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                    updateField('health_notes', event.target.value)
                  }
                />
              </Field>
              <Field label={t('student.specialNeeds')} className="sm:col-span-2">
                <textarea
                  className="textarea"
                  rows={2}
                  value={form.special_needs}
                  onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                    updateField('special_needs', event.target.value)
                  }
                />
              </Field>
            </>
          )}

          <div className="sm:col-span-2">
            <label className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 dark:border-slate-600 dark:bg-surface-dark"
                checked={form.consent_given}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  updateField('consent_given', event.target.checked)
                }
              />
              <span>
                <span className="font-medium">{t('student.consent')}</span>
                <span className="block text-xs text-slate-500 dark:text-slate-400">
                  {t('student.consentGiven')}
                </span>
              </span>
            </label>
          </div>
        </form>
      </Modal>

      {/* Silme onayı */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id)
        }}
        title={t('common.delete')}
        confirmLabel={t('common.delete')}
        loading={deleteMutation.isPending}
        message={
          <>
            <p className="font-medium text-slate-800 dark:text-slate-100">
              {deleteTarget?.full_name} · {deleteTarget?.student_number}
            </p>
            <p className="mt-1">
              {t('common.status')}: {t('studentStatus.passive')}
            </p>
          </>
        }
      />
    </>
  )
}
