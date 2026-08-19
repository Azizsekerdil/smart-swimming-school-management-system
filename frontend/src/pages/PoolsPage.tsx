/** Havuz, kulvar, bakım, su kalitesi ve tatil yönetimi / Pool & facility management. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CalendarOff,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Droplets,
  Pencil,
  Plus,
  Trash2,
  Waves,
  Wrench,
} from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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
  DemoBadge,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  ProgressBar,
  StatusBadge,
  TableWrapper,
  Tabs,
} from '@/components/ui'
import { del, get, patch, post } from '@/lib/api'
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatDecimal,
  formatNumber,
  formatPercent,
  toISODate,
  toISODateTime,
} from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type { Lane, Maintenance, Pool, PoolSummary, WaterQualityLog } from '@/lib/types'

/** Tatil kaydı (backend: HolidayOut) */
interface Holiday {
  id: number
  date: string
  name: string
  is_closed: boolean
}

const CURRENT_YEAR = new Date().getFullYear()
const YEAR_OPTIONS = [CURRENT_YEAR - 1, CURRENT_YEAR, CURRENT_YEAR + 1]

/** Bakım türleri — etiketler mevcut gider kategorisi anahtarlarından gelir */
const MAINTENANCE_TYPES = ['maintenance', 'chemicals', 'equipment', 'other'] as const

// Backend'deki su kalitesi kabul aralıkları (backend/app/api/v1/pools.py)
const PH_RANGE: [number, number] = [6.8, 7.6]
const CHLORINE_RANGE: [number, number] = [0.5, 3.0]
const TURBIDITY_MAX = 0.5

// ---------------------------------------------------------------------------
// Form durumları
// ---------------------------------------------------------------------------
interface PoolFormState {
  name: string
  location: string
  length_m: string
  width_m: string
  depth_min_m: string
  depth_max_m: string
  lane_count: string
  capacity: string
  course_type: 'short' | 'long'
  opening_time: string
  closing_time: string
  status: 'operational' | 'maintenance' | 'closed'
  water_temperature_c: string
  air_temperature_c: string
  is_indoor: boolean
  is_heated: boolean
  notes: string
  auto_create_lanes: boolean
}

const EMPTY_POOL_FORM: PoolFormState = {
  name: '',
  location: '',
  length_m: '25',
  width_m: '',
  depth_min_m: '',
  depth_max_m: '',
  lane_count: '6',
  capacity: '60',
  course_type: 'short',
  opening_time: '07:00',
  closing_time: '22:00',
  status: 'operational',
  water_temperature_c: '',
  air_temperature_c: '',
  is_indoor: true,
  is_heated: true,
  notes: '',
  auto_create_lanes: true,
}

interface LaneFormState {
  lane_number: string
  name: string
  purpose: string
  max_swimmers: string
  is_active: boolean
}

const EMPTY_LANE_FORM: LaneFormState = {
  lane_number: '1',
  name: '',
  purpose: '',
  max_swimmers: '8',
  is_active: true,
}

interface MaintenanceFormState {
  start_at: string
  end_at: string
  maintenance_type: string
  description: string
  cost: string
}

interface WaterFormState {
  measured_at: string
  ph: string
  chlorine_ppm: string
  temperature_c: string
  turbidity_ntu: string
}

interface HolidayFormState {
  date: string
  name: string
  is_closed: boolean
}

// ---------------------------------------------------------------------------
// Yardımcılar
// ---------------------------------------------------------------------------
/** Boş metni null yapar, aksi halde sayıya çevirir */
function numberOrNull(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}

/** Boş metni null yapar */
function textOrNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

/** "07:00:00" -> "07:00" (input type="time" için) */
function toInputTime(value: string | null | undefined): string {
  return (value ?? '').slice(0, 5)
}

/** "HH:MM" -> dakika */
function minutesOfTime(value: string): number {
  const [hours, minutes] = value.split(':')
  return Number(hours) * 60 + Number(minutes ?? 0)
}

function poolToForm(pool: Pool): PoolFormState {
  return {
    name: pool.name,
    location: pool.location ?? '',
    length_m: String(pool.length_m),
    width_m: pool.width_m === null || pool.width_m === undefined ? '' : String(pool.width_m),
    depth_min_m:
      pool.depth_min_m === null || pool.depth_min_m === undefined ? '' : String(pool.depth_min_m),
    depth_max_m:
      pool.depth_max_m === null || pool.depth_max_m === undefined ? '' : String(pool.depth_max_m),
    lane_count: String(pool.lane_count),
    capacity: String(pool.capacity),
    course_type: pool.course_type,
    opening_time: toInputTime(pool.opening_time),
    closing_time: toInputTime(pool.closing_time),
    status: pool.status,
    water_temperature_c:
      pool.water_temperature_c === null || pool.water_temperature_c === undefined
        ? ''
        : String(pool.water_temperature_c),
    air_temperature_c:
      pool.air_temperature_c === null || pool.air_temperature_c === undefined
        ? ''
        : String(pool.air_temperature_c),
    is_indoor: pool.is_indoor,
    is_heated: pool.is_heated,
    notes: pool.notes ?? '',
    auto_create_lanes: false,
  }
}

function defaultMaintenanceForm(): MaintenanceFormState {
  const now = new Date()
  const later = new Date(now.getTime() + 2 * 60 * 60 * 1000)
  return {
    start_at: toISODateTime(now),
    end_at: toISODateTime(later),
    maintenance_type: 'maintenance',
    description: '',
    cost: '',
  }
}

function defaultWaterForm(): WaterFormState {
  return {
    measured_at: toISODateTime(new Date()),
    ph: '',
    chlorine_ppm: '',
    temperature_c: '',
    turbidity_ntu: '',
  }
}

// ---------------------------------------------------------------------------
// Havuz özet kartı
// ---------------------------------------------------------------------------
function PoolSummaryCard({ summary }: { summary: PoolSummary }) {
  const { t } = useTranslation()
  const tone =
    summary.occupancy_rate >= 85 ? 'danger' : summary.occupancy_rate >= 55 ? 'success' : 'brand'

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
          {summary.name}
        </p>
        <StatusBadge status={summary.status} label={t(`pool.status.${summary.status}`, summary.status)} />
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          {formatPercent(summary.occupancy_rate)}
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {t('dashboard.poolOccupancy')}
        </span>
      </div>
      <div className="mt-2">
        <ProgressBar value={summary.occupancy_rate} tone={tone} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <dt className="text-slate-500 dark:text-slate-400">{t('dashboard.lessonsToday')}</dt>
          <dd className="font-medium text-slate-800 dark:text-slate-200">
            {formatNumber(summary.today_lesson_count)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">{t('pool.laneCount')}</dt>
          <dd className="font-medium text-slate-800 dark:text-slate-200">
            {formatNumber(summary.active_lane_count)} / {formatNumber(summary.lane_count)}
          </dd>
        </div>
      </dl>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Genişletilebilir havuz kartı
// ---------------------------------------------------------------------------
function PoolCard({
  pool,
  expanded,
  onToggle,
  onEdit,
  onDelete,
  onAddLane,
  onEditLane,
  onDeleteLane,
  canWrite,
  canDelete,
}: {
  pool: Pool
  expanded: boolean
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
  onAddLane: () => void
  onEditLane: (lane: Lane) => void
  onDeleteLane: (lane: Lane) => void
  canWrite: boolean
  canDelete: boolean
}) {
  const { t } = useTranslation()
  const lanes = [...pool.lanes].sort((a, b) => a.lane_number - b.lane_number)

  return (
    <section className="card">
      <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-700">
        <button
          type="button"
          onClick={onToggle}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          aria-expanded={expanded}
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
          )}
          <span className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
            {pool.name}
          </span>
          {pool.code && <span className="badge-neutral shrink-0">{pool.code}</span>}
          {pool.is_demo && <DemoBadge />}
        </button>
        <StatusBadge status={pool.status} label={t(`pool.status.${pool.status}`, pool.status)} />
        <span className="text-xs text-slate-500 dark:text-slate-400">{pool.operating_hours}</span>
        {canWrite && (
          <button type="button" className="btn-ghost btn-sm" onClick={onEdit} title={t('common.edit')}>
            <Pencil className="h-4 w-4" />
          </button>
        )}
        {canDelete && (
          <button
            type="button"
            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
            onClick={onDelete}
            title={t('common.delete')}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </header>

      {expanded && (
        <div className="card-body space-y-4">
          <dl className="grid gap-3 text-xs sm:grid-cols-3 lg:grid-cols-4">
            <div>
              <dt className="text-slate-500 dark:text-slate-400">{t('pool.location')}</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {pool.location ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">{t('pool.length')}</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {formatDecimal(pool.length_m, 1)}
                {pool.width_m ? ` × ${formatDecimal(pool.width_m, 1)}` : ''}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">
                {t('pool.depthMin')} / {t('pool.depthMax')}
              </dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {pool.depth_min_m !== null && pool.depth_min_m !== undefined
                  ? formatDecimal(pool.depth_min_m, 2)
                  : '—'}{' '}
                /{' '}
                {pool.depth_max_m !== null && pool.depth_max_m !== undefined
                  ? formatDecimal(pool.depth_max_m, 2)
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">{t('pool.laneCount')}</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {formatNumber(pool.lane_count)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">{t('pool.capacity')}</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {formatNumber(pool.capacity)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">{t('pool.operatingHours')}</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {pool.operating_hours}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">{t('pool.waterTemp')}</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {pool.water_temperature_c !== null && pool.water_temperature_c !== undefined
                  ? `${formatDecimal(pool.water_temperature_c, 1)} °C`
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">{t('pool.airTemp')}</dt>
              <dd className="font-medium text-slate-800 dark:text-slate-200">
                {pool.air_temperature_c !== null && pool.air_temperature_c !== undefined
                  ? `${formatDecimal(pool.air_temperature_c, 1)} °C`
                  : '—'}
              </dd>
            </div>
          </dl>

          <div className="flex flex-wrap gap-2">
            <Badge tone="info">
              {pool.course_type === 'short' ? t('pool.shortCourse') : t('pool.longCourse')}
            </Badge>
            {pool.is_indoor && <Badge tone="neutral">{t('pool.isIndoor')}</Badge>}
            {pool.is_heated && <Badge tone="neutral">{t('pool.isHeated')}</Badge>}
          </div>

          {pool.notes && (
            <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
              {pool.notes}
            </p>
          )}

          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              {t('lane.title')}
            </h3>
            {canWrite && (
              <button type="button" className="btn-secondary btn-sm" onClick={onAddLane}>
                <Plus className="h-4 w-4" />
                {t('common.add')}
              </button>
            )}
          </div>

          {lanes.length === 0 ? (
            <EmptyState title={t('common.noData')} icon={<Waves className="h-6 w-6" />} />
          ) : (
            <TableWrapper>
              <thead>
                <tr>
                  <th>{t('lane.number')}</th>
                  <th>{t('common.name')}</th>
                  <th className="hidden sm:table-cell">{t('lane.purpose')}</th>
                  <th>{t('lane.maxSwimmers')}</th>
                  <th>{t('common.status')}</th>
                  {(canWrite || canDelete) && <th className="text-right">{t('common.actions')}</th>}
                </tr>
              </thead>
              <tbody>
                {lanes.map((lane) => (
                  <tr key={lane.id}>
                    <td className="font-medium">{lane.lane_number}</td>
                    <td>{lane.display_name}</td>
                    <td className="hidden text-xs text-slate-500 sm:table-cell dark:text-slate-400">
                      {lane.purpose ?? '—'}
                    </td>
                    <td>{formatNumber(lane.max_swimmers)}</td>
                    <td>
                      <Badge tone={lane.is_active ? 'success' : 'neutral'}>
                        {lane.is_active ? t('common.active') : t('common.passive')}
                      </Badge>
                    </td>
                    {(canWrite || canDelete) && (
                      <td className="text-right whitespace-nowrap">
                        {canWrite && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm"
                            onClick={() => onEditLane(lane)}
                            title={t('common.edit')}
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        )}
                        {canDelete && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            onClick={() => onDeleteLane(lane)}
                            title={t('common.delete')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          )}
        </div>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Sayfa
// ---------------------------------------------------------------------------
export default function PoolsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const can = useAuth((state) => state.can)

  const canWrite = can('pool:write')
  const canDelete = can('pool:delete')
  const canMaintain = can('pool:maintenance')
  const canSchedule = can('lesson:schedule')

  const [tab, setTab] = useState('pools')
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [selectedPoolId, setSelectedPoolId] = useState<number | null>(null)
  const [year, setYear] = useState(CURRENT_YEAR)

  // Havuz formu
  const [poolModalOpen, setPoolModalOpen] = useState(false)
  const [editingPool, setEditingPool] = useState<Pool | null>(null)
  const [poolForm, setPoolForm] = useState<PoolFormState>(EMPTY_POOL_FORM)
  const [poolToDelete, setPoolToDelete] = useState<Pool | null>(null)

  // Kulvar formu
  const [laneModal, setLaneModal] = useState<{ poolId: number; lane: Lane | null } | null>(null)
  const [laneForm, setLaneForm] = useState<LaneFormState>(EMPTY_LANE_FORM)
  const [laneToDelete, setLaneToDelete] = useState<Lane | null>(null)

  // Bakım / su kalitesi / tatil formları
  const [maintenanceForm, setMaintenanceForm] = useState<MaintenanceFormState>(defaultMaintenanceForm)
  const [waterForm, setWaterForm] = useState<WaterFormState>(defaultWaterForm)
  const [holidayForm, setHolidayForm] = useState<HolidayFormState>({
    date: toISODate(new Date()),
    name: '',
    is_closed: true,
  })
  const [holidayToDelete, setHolidayToDelete] = useState<Holiday | null>(null)

  // --- Sorgular ---
  const poolsQuery = useQuery({
    queryKey: ['pools', 'list'],
    queryFn: () => get<Pool[]>('/pools'),
  })

  const summaryQuery = useQuery({
    queryKey: ['pools', 'summary'],
    queryFn: () => get<PoolSummary[]>('/pools/summary'),
  })

  const pools = useMemo(() => poolsQuery.data ?? [], [poolsQuery.data])
  const activePoolId = selectedPoolId ?? pools[0]?.id ?? null

  const maintenanceQuery = useQuery({
    queryKey: ['pool-maintenance', activePoolId],
    queryFn: () => get<Maintenance[]>(`/pools/${activePoolId}/maintenance`),
    enabled: tab === 'maintenance' && activePoolId !== null,
  })

  const waterQuery = useQuery({
    queryKey: ['pool-water', activePoolId],
    queryFn: () => get<WaterQualityLog[]>(`/pools/${activePoolId}/water-quality`, { limit: 50 }),
    enabled: tab === 'water' && activePoolId !== null,
  })

  const holidaysQuery = useQuery({
    queryKey: ['holidays', year],
    queryFn: () => get<Holiday[]>('/pools/calendar/holidays', { year }),
    enabled: tab === 'holidays',
  })

  // --- Mutasyonlar ---
  function invalidatePools() {
    queryClient.invalidateQueries({ queryKey: ['pools'] })
  }

  const savePool = useMutation({
    mutationFn: (form: PoolFormState) => {
      const body = {
        name: form.name.trim(),
        location: textOrNull(form.location),
        length_m: numberOrNull(form.length_m) ?? 25,
        width_m: numberOrNull(form.width_m),
        depth_min_m: numberOrNull(form.depth_min_m),
        depth_max_m: numberOrNull(form.depth_max_m),
        lane_count: numberOrNull(form.lane_count) ?? 6,
        capacity: numberOrNull(form.capacity) ?? 60,
        course_type: form.course_type,
        opening_time: form.opening_time,
        closing_time: form.closing_time,
        status: form.status,
        water_temperature_c: numberOrNull(form.water_temperature_c),
        air_temperature_c: numberOrNull(form.air_temperature_c),
        is_indoor: form.is_indoor,
        is_heated: form.is_heated,
        notes: textOrNull(form.notes),
      }
      if (editingPool) return patch<Pool>(`/pools/${editingPool.id}`, body)
      return post<Pool>('/pools', { ...body, auto_create_lanes: form.auto_create_lanes })
    },
    onSuccess: () => {
      invalidatePools()
      toastSuccess(t('common.success'))
      setPoolModalOpen(false)
      setEditingPool(null)
    },
    onError: (error) => toastError(error),
  })

  const deletePool = useMutation({
    mutationFn: (pool: Pool) => del<{ message: string }>(`/pools/${pool.id}`),
    onSuccess: () => {
      invalidatePools()
      toastSuccess(t('common.success'))
      setPoolToDelete(null)
    },
    onError: (error) => toastError(error),
  })

  const saveLane = useMutation({
    mutationFn: (payload: { poolId: number; lane: Lane | null; form: LaneFormState }) => {
      const body = {
        lane_number: numberOrNull(payload.form.lane_number) ?? 1,
        name: textOrNull(payload.form.name),
        purpose: textOrNull(payload.form.purpose),
        max_swimmers: numberOrNull(payload.form.max_swimmers) ?? 8,
        is_active: payload.form.is_active,
      }
      if (payload.lane) return patch<Lane>(`/pools/lanes/${payload.lane.id}`, body)
      return post<Lane>('/pools/lanes', { ...body, pool_id: payload.poolId })
    },
    onSuccess: () => {
      invalidatePools()
      toastSuccess(t('common.success'))
      setLaneModal(null)
    },
    onError: (error) => toastError(error),
  })

  const deleteLane = useMutation({
    mutationFn: (lane: Lane) => del<{ message: string }>(`/pools/lanes/${lane.id}`),
    onSuccess: () => {
      invalidatePools()
      toastSuccess(t('common.success'))
      setLaneToDelete(null)
    },
    onError: (error) => toastError(error),
  })

  const createMaintenance = useMutation({
    mutationFn: (form: MaintenanceFormState) =>
      post<Maintenance>('/pools/maintenance', {
        pool_id: activePoolId,
        start_at: form.start_at,
        end_at: form.end_at,
        maintenance_type: form.maintenance_type,
        description: textOrNull(form.description),
        cost: numberOrNull(form.cost),
        is_completed: false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pool-maintenance'] })
      invalidatePools()
      toastSuccess(t('common.success'))
      setMaintenanceForm(defaultMaintenanceForm())
    },
    onError: (error) => toastError(error),
  })

  const completeMaintenance = useMutation({
    mutationFn: (row: Maintenance) =>
      patch<Maintenance>(`/pools/maintenance/${row.id}?is_completed=${!row.is_completed}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pool-maintenance'] })
      toastSuccess(t('common.success'))
    },
    onError: (error) => toastError(error),
  })

  const createWaterLog = useMutation({
    mutationFn: (form: WaterFormState) =>
      post<WaterQualityLog>('/pools/water-quality', {
        pool_id: activePoolId,
        measured_at: form.measured_at,
        ph: numberOrNull(form.ph),
        chlorine_ppm: numberOrNull(form.chlorine_ppm),
        temperature_c: numberOrNull(form.temperature_c),
        turbidity_ntu: numberOrNull(form.turbidity_ntu),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pool-water'] })
      toastSuccess(t('common.success'))
      setWaterForm(defaultWaterForm())
    },
    onError: (error) => toastError(error),
  })

  const createHoliday = useMutation({
    mutationFn: (form: HolidayFormState) =>
      post<Holiday>('/pools/calendar/holidays', {
        date: form.date,
        name: form.name.trim(),
        is_closed: form.is_closed,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holidays'] })
      toastSuccess(t('common.success'))
      setHolidayForm({ date: toISODate(new Date()), name: '', is_closed: true })
    },
    onError: (error) => toastError(error),
  })

  const deleteHoliday = useMutation({
    mutationFn: (holiday: Holiday) =>
      del<{ message: string }>(`/pools/calendar/holidays/${holiday.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holidays'] })
      toastSuccess(t('common.success'))
      setHolidayToDelete(null)
    },
    onError: (error) => toastError(error),
  })

  // --- Su kalitesi grafiği ---
  const waterChartData = useMemo(() => {
    const rows = waterQuery.data ?? []
    return [...rows]
      .reverse()
      .map((row) => ({
        label: formatDate(row.measured_at),
        ph: row.ph,
        chlorine: row.chlorine_ppm,
      }))
  }, [waterQuery.data])

  // --- Form açma yardımcıları ---
  function openNewPool() {
    setEditingPool(null)
    setPoolForm(EMPTY_POOL_FORM)
    setPoolModalOpen(true)
  }

  function openEditPool(pool: Pool) {
    setEditingPool(pool)
    setPoolForm(poolToForm(pool))
    setPoolModalOpen(true)
  }

  function openNewLane(pool: Pool) {
    const nextNumber = pool.lanes.reduce((max, lane) => Math.max(max, lane.lane_number), 0) + 1
    setLaneForm({ ...EMPTY_LANE_FORM, lane_number: String(Math.min(20, nextNumber)) })
    setLaneModal({ poolId: pool.id, lane: null })
  }

  function openEditLane(pool: Pool, lane: Lane) {
    setLaneForm({
      lane_number: String(lane.lane_number),
      name: lane.name ?? '',
      purpose: lane.purpose ?? '',
      max_swimmers: String(lane.max_swimmers),
      is_active: lane.is_active,
    })
    setLaneModal({ poolId: pool.id, lane })
  }

  function updatePoolForm<K extends keyof PoolFormState>(key: K, value: PoolFormState[K]) {
    setPoolForm((prev) => ({ ...prev, [key]: value }))
  }

  const poolFormValid =
    poolForm.name.trim().length > 0 &&
    (numberOrNull(poolForm.length_m) ?? 0) > 0 &&
    minutesOfTime(poolForm.closing_time) > minutesOfTime(poolForm.opening_time)

  const laneFormValid = (numberOrNull(laneForm.lane_number) ?? 0) >= 1
  const maintenanceValid = maintenanceForm.end_at > maintenanceForm.start_at
  const waterValid =
    !!waterForm.measured_at &&
    [waterForm.ph, waterForm.chlorine_ppm, waterForm.temperature_c, waterForm.turbidity_ntu].some(
      (value) => numberOrNull(value) !== null,
    )
  const holidayValid = holidayForm.name.trim().length > 0 && !!holidayForm.date

  if (poolsQuery.isLoading) return <LoadingState />
  if (poolsQuery.error) return <ErrorState error={poolsQuery.error} onRetry={poolsQuery.refetch} />

  const activePool = pools.find((pool) => pool.id === activePoolId) ?? null

  return (
    <>
      <PageHeader
        title={t('pool.title')}
        subtitle={t('nav.sections.operations')}
        icon={<Waves className="h-5 w-5" />}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={openNewPool}>
              <Plus className="h-4 w-4" />
              {t('pool.new')}
            </button>
          )
        }
      />

      {/* Havuz doluluk özeti */}
      {summaryQuery.data && summaryQuery.data.length > 0 && (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {summaryQuery.data.map((summary) => (
            <PoolSummaryCard key={summary.id} summary={summary} />
          ))}
        </div>
      )}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: 'pools', label: t('pool.title'), icon: <Waves className="h-4 w-4" />, badge: pools.length },
          { id: 'maintenance', label: t('pool.maintenance'), icon: <Wrench className="h-4 w-4" /> },
          { id: 'water', label: t('pool.waterQuality'), icon: <Droplets className="h-4 w-4" /> },
          {
            id: 'holidays',
            label: t('lesson.conflict.holiday'),
            icon: <CalendarOff className="h-4 w-4" />,
          },
        ]}
      />

      {/* Bakım ve su kalitesi sekmeleri için havuz seçici */}
      {(tab === 'maintenance' || tab === 'water') && pools.length > 0 && (
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <Field label={t('pool.singular')} className="w-full max-w-xs">
            <select
              className="select"
              value={activePoolId ?? ''}
              onChange={(event) => setSelectedPoolId(Number(event.target.value))}
            >
              {pools.map((pool) => (
                <option key={pool.id} value={pool.id}>
                  {pool.name}
                </option>
              ))}
            </select>
          </Field>
          {activePool && (
            <p className="pb-2 text-xs text-slate-500 dark:text-slate-400">
              {t('pool.operatingHours')}: {activePool.operating_hours} ·{' '}
              {t('pool.laneCount')}: {formatNumber(activePool.lane_count)}
            </p>
          )}
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Havuzlar                                                          */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'pools' && (
        <div className="space-y-3">
          {pools.length === 0 ? (
            <Card>
              <EmptyState
                title={t('common.noData')}
                icon={<Waves className="h-6 w-6" />}
                action={
                  canWrite ? (
                    <button type="button" className="btn-primary btn-sm" onClick={openNewPool}>
                      <Plus className="h-4 w-4" />
                      {t('pool.new')}
                    </button>
                  ) : undefined
                }
              />
            </Card>
          ) : (
            pools.map((pool) => (
              <PoolCard
                key={pool.id}
                pool={pool}
                expanded={expandedId === pool.id}
                onToggle={() => setExpandedId(expandedId === pool.id ? null : pool.id)}
                onEdit={() => openEditPool(pool)}
                onDelete={() => setPoolToDelete(pool)}
                onAddLane={() => openNewLane(pool)}
                onEditLane={(lane) => openEditLane(pool, lane)}
                onDeleteLane={(lane) => setLaneToDelete(lane)}
                canWrite={canWrite}
                canDelete={canDelete}
              />
            ))
          )}
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Bakım                                                             */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'maintenance' && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card title={t('pool.maintenance')} className="lg:col-span-2" bodyClassName="p-0">
            {activePoolId === null ? (
              <EmptyState title={t('common.noData')} icon={<Waves className="h-6 w-6" />} />
            ) : maintenanceQuery.isLoading ? (
              <LoadingState />
            ) : maintenanceQuery.error ? (
              <ErrorState error={maintenanceQuery.error} onRetry={maintenanceQuery.refetch} />
            ) : (maintenanceQuery.data ?? []).length === 0 ? (
              <EmptyState title={t('common.noData')} icon={<Wrench className="h-6 w-6" />} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('lesson.start')}</th>
                    <th>{t('lesson.end')}</th>
                    <th>{t('pool.maintenanceType')}</th>
                    <th className="hidden md:table-cell">{t('common.description')}</th>
                    <th>{t('finance.amount')}</th>
                    <th>{t('common.status')}</th>
                    {canMaintain && <th className="text-right">{t('common.actions')}</th>}
                  </tr>
                </thead>
                <tbody>
                  {(maintenanceQuery.data ?? []).map((row) => (
                    <tr key={row.id}>
                      <td className="whitespace-nowrap">{formatDateTime(row.start_at)}</td>
                      <td className="whitespace-nowrap">{formatDateTime(row.end_at)}</td>
                      <td>{t(`finance.categories.${row.maintenance_type}`, row.maintenance_type)}</td>
                      <td className="hidden max-w-xs truncate text-xs text-slate-500 md:table-cell dark:text-slate-400">
                        {row.description ?? '—'}
                      </td>
                      <td className="whitespace-nowrap">
                        {row.cost !== null && row.cost !== undefined ? formatCurrency(row.cost) : '—'}
                      </td>
                      <td>
                        <Badge tone={row.is_completed ? 'success' : 'warning'}>
                          {row.is_completed
                            ? t('lesson.statuses.completed')
                            : t('finance.statuses.pending')}
                        </Badge>
                      </td>
                      {canMaintain && (
                        <td className="text-right whitespace-nowrap">
                          <button
                            type="button"
                            className="btn-ghost btn-sm"
                            onClick={() => completeMaintenance.mutate(row)}
                            disabled={completeMaintenance.isPending}
                            title={t('training.markComplete')}
                          >
                            <CheckCircle2
                              className={
                                row.is_completed
                                  ? 'h-4 w-4 text-emerald-600 dark:text-emerald-400'
                                  : 'h-4 w-4 text-slate-400'
                              }
                            />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </Card>

          {canMaintain && activePoolId !== null && (
            <Card title={t('pool.newMaintenance')}>
              <form
                className="space-y-3"
                onSubmit={(event: FormEvent) => {
                  event.preventDefault()
                  createMaintenance.mutate(maintenanceForm)
                }}
              >
                <Field label={t('lesson.start')} required>
                  <input
                    className="input"
                    type="datetime-local"
                    required
                    value={maintenanceForm.start_at}
                    onChange={(event) =>
                      setMaintenanceForm((prev) => ({ ...prev, start_at: event.target.value }))
                    }
                  />
                </Field>
                <Field label={t('lesson.end')} required>
                  <input
                    className="input"
                    type="datetime-local"
                    required
                    value={maintenanceForm.end_at}
                    onChange={(event) =>
                      setMaintenanceForm((prev) => ({ ...prev, end_at: event.target.value }))
                    }
                  />
                </Field>
                <Field label={t('pool.maintenanceType')}>
                  <select
                    className="select"
                    value={maintenanceForm.maintenance_type}
                    onChange={(event) =>
                      setMaintenanceForm((prev) => ({
                        ...prev,
                        maintenance_type: event.target.value,
                      }))
                    }
                  >
                    {MAINTENANCE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {t(`finance.categories.${type}`)}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t('common.description')}>
                  <textarea
                    className="textarea"
                    rows={3}
                    value={maintenanceForm.description}
                    onChange={(event) =>
                      setMaintenanceForm((prev) => ({ ...prev, description: event.target.value }))
                    }
                  />
                </Field>
                <Field label={t('finance.amount')}>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    step="0.01"
                    value={maintenanceForm.cost}
                    onChange={(event) =>
                      setMaintenanceForm((prev) => ({ ...prev, cost: event.target.value }))
                    }
                  />
                </Field>
                <button
                  type="submit"
                  className="btn-primary w-full"
                  disabled={!maintenanceValid || createMaintenance.isPending}
                >
                  <Plus className="h-4 w-4" />
                  {t('common.save')}
                </button>
              </form>
            </Card>
          )}
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Su kalitesi                                                       */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'water' && (
        <div className="space-y-4">
          <Alert tone="info" title={t('pool.withinLimits')}>
            {t('pool.ph')} {formatDecimal(PH_RANGE[0], 1)}–{formatDecimal(PH_RANGE[1], 1)} ·{' '}
            {t('pool.chlorine')} {formatDecimal(CHLORINE_RANGE[0], 1)}–
            {formatDecimal(CHLORINE_RANGE[1], 1)} · {t('pool.turbidity')} ≤{' '}
            {formatDecimal(TURBIDITY_MAX, 1)}
          </Alert>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card title={t('pool.waterQuality')} className="lg:col-span-2" bodyClassName="p-0">
              {activePoolId === null ? (
                <EmptyState title={t('common.noData')} icon={<Waves className="h-6 w-6" />} />
              ) : waterQuery.isLoading ? (
                <LoadingState />
              ) : waterQuery.error ? (
                <ErrorState error={waterQuery.error} onRetry={waterQuery.refetch} />
              ) : (waterQuery.data ?? []).length === 0 ? (
                <EmptyState title={t('common.noData')} icon={<Droplets className="h-6 w-6" />} />
              ) : (
                <TableWrapper>
                  <thead>
                    <tr>
                      <th>{t('performance.recordedDate')}</th>
                      <th>{t('pool.ph')}</th>
                      <th>{t('pool.chlorine')}</th>
                      <th className="hidden sm:table-cell">{t('pool.waterTemp')}</th>
                      <th className="hidden sm:table-cell">{t('pool.turbidity')}</th>
                      <th className="hidden md:table-cell">{t('pool.measuredBy')}</th>
                      <th>{t('common.status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(waterQuery.data ?? []).map((row) => (
                      <tr
                        key={row.id}
                        className={
                          row.is_within_limits
                            ? undefined
                            : 'bg-rose-50 text-rose-900 dark:bg-rose-900/20 dark:text-rose-200'
                        }
                      >
                        <td className="whitespace-nowrap">{formatDateTime(row.measured_at)}</td>
                        <td>{row.ph !== null && row.ph !== undefined ? formatDecimal(row.ph, 2) : '—'}</td>
                        <td>
                          {row.chlorine_ppm !== null && row.chlorine_ppm !== undefined
                            ? formatDecimal(row.chlorine_ppm, 2)
                            : '—'}
                        </td>
                        <td className="hidden sm:table-cell">
                          {row.temperature_c !== null && row.temperature_c !== undefined
                            ? `${formatDecimal(row.temperature_c, 1)} °C`
                            : '—'}
                        </td>
                        <td className="hidden sm:table-cell">
                          {row.turbidity_ntu !== null && row.turbidity_ntu !== undefined
                            ? formatDecimal(row.turbidity_ntu, 2)
                            : '—'}
                        </td>
                        <td className="hidden text-xs md:table-cell">{row.measured_by ?? '—'}</td>
                        <td>
                          <Badge tone={row.is_within_limits ? 'success' : 'danger'}>
                            {row.is_within_limits ? t('pool.withinLimits') : t('pool.outOfLimits')}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableWrapper>
              )}
            </Card>

            {canMaintain && activePoolId !== null && (
              <Card title={t('common.new')}>
                <form
                  className="space-y-3"
                  onSubmit={(event: FormEvent) => {
                    event.preventDefault()
                    createWaterLog.mutate(waterForm)
                  }}
                >
                  <Field label={t('performance.recordedDate')} required>
                    <input
                      className="input"
                      type="datetime-local"
                      required
                      value={waterForm.measured_at}
                      onChange={(event) =>
                        setWaterForm((prev) => ({ ...prev, measured_at: event.target.value }))
                      }
                    />
                  </Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label={t('pool.ph')}>
                      <input
                        className="input"
                        type="number"
                        min="0"
                        max="14"
                        step="0.01"
                        value={waterForm.ph}
                        onChange={(event) =>
                          setWaterForm((prev) => ({ ...prev, ph: event.target.value }))
                        }
                      />
                    </Field>
                    <Field label={t('pool.chlorine')}>
                      <input
                        className="input"
                        type="number"
                        min="0"
                        step="0.01"
                        value={waterForm.chlorine_ppm}
                        onChange={(event) =>
                          setWaterForm((prev) => ({ ...prev, chlorine_ppm: event.target.value }))
                        }
                      />
                    </Field>
                    <Field label={t('pool.waterTemp')}>
                      <input
                        className="input"
                        type="number"
                        step="0.1"
                        value={waterForm.temperature_c}
                        onChange={(event) =>
                          setWaterForm((prev) => ({ ...prev, temperature_c: event.target.value }))
                        }
                      />
                    </Field>
                    <Field label={t('pool.turbidity')}>
                      <input
                        className="input"
                        type="number"
                        min="0"
                        step="0.01"
                        value={waterForm.turbidity_ntu}
                        onChange={(event) =>
                          setWaterForm((prev) => ({ ...prev, turbidity_ntu: event.target.value }))
                        }
                      />
                    </Field>
                  </div>
                  <button
                    type="submit"
                    className="btn-primary w-full"
                    disabled={!waterValid || createWaterLog.isPending}
                  >
                    <Plus className="h-4 w-4" />
                    {t('common.save')}
                  </button>
                </form>
              </Card>
            )}
          </div>

          {waterChartData.length > 1 && (
            <Card title={`${t('pool.ph')} / ${t('pool.chlorine')}`}>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={waterChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} width={40} />
                  <Tooltip
                    formatter={(value: number) => formatDecimal(value, 2)}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="ph"
                    name={t('pool.ph')}
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="chlorine"
                    name={t('pool.chlorine')}
                    stroke="#f59e0b"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Tatiller                                                          */}
      {/* ---------------------------------------------------------------- */}
      {tab === 'holidays' && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            title={t('lesson.conflict.holiday')}
            className="lg:col-span-2"
            bodyClassName="p-0"
            actions={
              <select
                className="select w-auto py-1 text-xs"
                value={year}
                onChange={(event) => setYear(Number(event.target.value))}
                aria-label={t('common.date')}
              >
                {YEAR_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            }
          >
            {holidaysQuery.isLoading ? (
              <LoadingState />
            ) : holidaysQuery.error ? (
              <ErrorState error={holidaysQuery.error} onRetry={holidaysQuery.refetch} />
            ) : (holidaysQuery.data ?? []).length === 0 ? (
              <EmptyState title={t('common.noData')} icon={<CalendarOff className="h-6 w-6" />} />
            ) : (
              <TableWrapper>
                <thead>
                  <tr>
                    <th>{t('common.date')}</th>
                    <th>{t('common.name')}</th>
                    <th>{t('common.status')}</th>
                    {canSchedule && <th className="text-right">{t('common.actions')}</th>}
                  </tr>
                </thead>
                <tbody>
                  {(holidaysQuery.data ?? []).map((holiday) => (
                    <tr key={holiday.id}>
                      <td className="whitespace-nowrap font-medium">{formatDate(holiday.date)}</td>
                      <td>{holiday.name}</td>
                      <td>
                        <Badge tone={holiday.is_closed ? 'danger' : 'neutral'}>
                          {holiday.is_closed
                            ? t('pool.status.closed')
                            : t('pool.status.operational')}
                        </Badge>
                      </td>
                      {canSchedule && (
                        <td className="text-right">
                          <button
                            type="button"
                            className="btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            onClick={() => setHolidayToDelete(holiday)}
                            title={t('common.delete')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </TableWrapper>
            )}
          </Card>

          {canSchedule && (
            <Card title={t('common.new')}>
              <form
                className="space-y-3"
                onSubmit={(event: FormEvent) => {
                  event.preventDefault()
                  createHoliday.mutate(holidayForm)
                }}
              >
                <Field label={t('common.date')} required>
                  <input
                    className="input"
                    type="date"
                    required
                    value={holidayForm.date}
                    onChange={(event) =>
                      setHolidayForm((prev) => ({ ...prev, date: event.target.value }))
                    }
                  />
                </Field>
                <Field label={t('common.name')} required>
                  <input
                    className="input"
                    required
                    maxLength={160}
                    value={holidayForm.name}
                    onChange={(event) =>
                      setHolidayForm((prev) => ({ ...prev, name: event.target.value }))
                    }
                  />
                </Field>
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 dark:border-slate-600"
                    checked={holidayForm.is_closed}
                    onChange={(event) =>
                      setHolidayForm((prev) => ({ ...prev, is_closed: event.target.checked }))
                    }
                  />
                  {t('pool.status.closed')}
                </label>
                <button
                  type="submit"
                  className="btn-primary w-full"
                  disabled={!holidayValid || createHoliday.isPending}
                >
                  <Plus className="h-4 w-4" />
                  {t('common.save')}
                </button>
              </form>
            </Card>
          )}
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Havuz formu                                                       */}
      {/* ---------------------------------------------------------------- */}
      <Modal
        open={poolModalOpen}
        onClose={() => setPoolModalOpen(false)}
        title={editingPool ? `${t('common.edit')} · ${editingPool.name}` : t('pool.new')}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setPoolModalOpen(false)}
              disabled={savePool.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              form="pool-form"
              className="btn-primary"
              disabled={!poolFormValid || savePool.isPending}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <form
          id="pool-form"
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={(event: FormEvent) => {
            event.preventDefault()
            if (!poolFormValid) return
            savePool.mutate(poolForm)
          }}
        >
          <Field label={t('common.name')} required className="sm:col-span-2">
            <input
              className="input"
              required
              maxLength={120}
              value={poolForm.name}
              onChange={(event) => updatePoolForm('name', event.target.value)}
            />
          </Field>
          <Field label={t('pool.location')}>
            <input
              className="input"
              maxLength={200}
              value={poolForm.location}
              onChange={(event) => updatePoolForm('location', event.target.value)}
            />
          </Field>
          <Field label={t('common.status')}>
            <select
              className="select"
              value={poolForm.status}
              onChange={(event) =>
                updatePoolForm('status', event.target.value as PoolFormState['status'])
              }
            >
              <option value="operational">{t('pool.status.operational')}</option>
              <option value="maintenance">{t('pool.status.maintenance')}</option>
              <option value="closed">{t('pool.status.closed')}</option>
            </select>
          </Field>
          <Field label={t('pool.length')} required>
            <input
              className="input"
              type="number"
              min="1"
              max="100"
              step="0.5"
              required
              value={poolForm.length_m}
              onChange={(event) => updatePoolForm('length_m', event.target.value)}
            />
          </Field>
          <Field label={t('pool.width')}>
            <input
              className="input"
              type="number"
              min="0"
              step="0.5"
              value={poolForm.width_m}
              onChange={(event) => updatePoolForm('width_m', event.target.value)}
            />
          </Field>
          <Field label={t('pool.depthMin')}>
            <input
              className="input"
              type="number"
              min="0"
              step="0.1"
              value={poolForm.depth_min_m}
              onChange={(event) => updatePoolForm('depth_min_m', event.target.value)}
            />
          </Field>
          <Field label={t('pool.depthMax')}>
            <input
              className="input"
              type="number"
              min="0"
              step="0.1"
              value={poolForm.depth_max_m}
              onChange={(event) => updatePoolForm('depth_max_m', event.target.value)}
            />
          </Field>
          <Field label={t('pool.laneCount')} required>
            <input
              className="input"
              type="number"
              min="1"
              max="20"
              required
              value={poolForm.lane_count}
              onChange={(event) => updatePoolForm('lane_count', event.target.value)}
            />
          </Field>
          <Field label={t('pool.capacity')} required>
            <input
              className="input"
              type="number"
              min="1"
              required
              value={poolForm.capacity}
              onChange={(event) => updatePoolForm('capacity', event.target.value)}
            />
          </Field>
          <Field label={t('pool.courseType')}>
            <select
              className="select"
              value={poolForm.course_type}
              onChange={(event) =>
                updatePoolForm('course_type', event.target.value as PoolFormState['course_type'])
              }
            >
              <option value="short">{t('pool.shortCourse')}</option>
              <option value="long">{t('pool.longCourse')}</option>
            </select>
          </Field>
          <Field label={t('pool.openingTime')} required>
            <input
              className="input"
              type="time"
              required
              value={poolForm.opening_time}
              onChange={(event) => updatePoolForm('opening_time', event.target.value)}
            />
          </Field>
          <Field label={t('pool.closingTime')} required>
            <input
              className="input"
              type="time"
              required
              value={poolForm.closing_time}
              onChange={(event) => updatePoolForm('closing_time', event.target.value)}
            />
          </Field>
          <Field label={t('pool.waterTemp')}>
            <input
              className="input"
              type="number"
              step="0.1"
              value={poolForm.water_temperature_c}
              onChange={(event) => updatePoolForm('water_temperature_c', event.target.value)}
            />
          </Field>
          <Field label={t('pool.airTemp')}>
            <input
              className="input"
              type="number"
              step="0.1"
              value={poolForm.air_temperature_c}
              onChange={(event) => updatePoolForm('air_temperature_c', event.target.value)}
            />
          </Field>
          <Field label={t('common.notes')} className="sm:col-span-2">
            <textarea
              className="textarea"
              rows={2}
              value={poolForm.notes}
              onChange={(event) => updatePoolForm('notes', event.target.value)}
            />
          </Field>
          <div className="flex flex-wrap gap-4 sm:col-span-2">
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 dark:border-slate-600"
                checked={poolForm.is_indoor}
                onChange={(event) => updatePoolForm('is_indoor', event.target.checked)}
              />
              {t('pool.isIndoor')}
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 dark:border-slate-600"
                checked={poolForm.is_heated}
                onChange={(event) => updatePoolForm('is_heated', event.target.checked)}
              />
              {t('pool.isHeated')}
            </label>
            {!editingPool && (
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 dark:border-slate-600"
                  checked={poolForm.auto_create_lanes}
                  onChange={(event) => updatePoolForm('auto_create_lanes', event.target.checked)}
                />
                {t('pool.autoCreateLanes')}
              </label>
            )}
          </div>
        </form>
      </Modal>

      {/* ---------------------------------------------------------------- */}
      {/* Kulvar formu                                                      */}
      {/* ---------------------------------------------------------------- */}
      <Modal
        open={laneModal !== null}
        onClose={() => setLaneModal(null)}
        title={laneModal?.lane ? `${t('common.edit')} · ${laneModal.lane.display_name}` : t('lane.singular')}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setLaneModal(null)}
              disabled={saveLane.isPending}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              form="lane-form"
              className="btn-primary"
              disabled={!laneFormValid || saveLane.isPending}
            >
              {t('common.save')}
            </button>
          </>
        }
      >
        <form
          id="lane-form"
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={(event: FormEvent) => {
            event.preventDefault()
            if (!laneModal || !laneFormValid) return
            saveLane.mutate({ poolId: laneModal.poolId, lane: laneModal.lane, form: laneForm })
          }}
        >
          <Field label={t('lane.number')} required>
            <input
              className="input"
              type="number"
              min="1"
              max="20"
              required
              value={laneForm.lane_number}
              onChange={(event) =>
                setLaneForm((prev) => ({ ...prev, lane_number: event.target.value }))
              }
            />
          </Field>
          <Field label={t('lane.maxSwimmers')} required>
            <input
              className="input"
              type="number"
              min="1"
              max="30"
              required
              value={laneForm.max_swimmers}
              onChange={(event) =>
                setLaneForm((prev) => ({ ...prev, max_swimmers: event.target.value }))
              }
            />
          </Field>
          <Field label={t('common.name')}>
            <input
              className="input"
              maxLength={80}
              value={laneForm.name}
              onChange={(event) => setLaneForm((prev) => ({ ...prev, name: event.target.value }))}
            />
          </Field>
          <Field label={t('lane.purpose')}>
            <input
              className="input"
              maxLength={80}
              value={laneForm.purpose}
              onChange={(event) => setLaneForm((prev) => ({ ...prev, purpose: event.target.value }))}
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2 dark:text-slate-300">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 dark:border-slate-600"
              checked={laneForm.is_active}
              onChange={(event) =>
                setLaneForm((prev) => ({ ...prev, is_active: event.target.checked }))
              }
            />
            {t('common.active')}
          </label>
        </form>
      </Modal>

      {/* Silme onayları */}
      <ConfirmDialog
        open={poolToDelete !== null}
        onClose={() => setPoolToDelete(null)}
        onConfirm={() => poolToDelete && deletePool.mutate(poolToDelete)}
        title={t('common.delete')}
        message={`${t('pool.singular')}: ${poolToDelete?.name ?? ''}`}
        confirmLabel={t('common.delete')}
        loading={deletePool.isPending}
      />
      <ConfirmDialog
        open={laneToDelete !== null}
        onClose={() => setLaneToDelete(null)}
        onConfirm={() => laneToDelete && deleteLane.mutate(laneToDelete)}
        title={t('common.delete')}
        message={`${t('lane.singular')}: ${laneToDelete?.display_name ?? ''}`}
        confirmLabel={t('common.delete')}
        loading={deleteLane.isPending}
      />
      <ConfirmDialog
        open={holidayToDelete !== null}
        onClose={() => setHolidayToDelete(null)}
        onConfirm={() => holidayToDelete && deleteHoliday.mutate(holidayToDelete)}
        title={t('common.delete')}
        message={`${formatDate(holidayToDelete?.date)} · ${holidayToDelete?.name ?? ''}`}
        confirmLabel={t('common.delete')}
        loading={deleteHoliday.isPending}
      />
    </>
  )
}
