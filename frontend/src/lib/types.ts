/**
 * Backend şemalarıyla eşleşen tip tanımları / Types mirroring backend schemas.
 * Kaynak: backend/app/schemas/*.py
 */

// ---------------------------------------------------------------------------
// Ortak
// ---------------------------------------------------------------------------
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Message {
  code: string
  message: string
  data?: Record<string, unknown>
}

export interface HealthComponent {
  name: string
  status: 'ok' | 'degraded' | 'down' | 'disabled'
  detail?: string | null
  latency_ms?: number | null
}

export interface HealthReport {
  status: string
  checked_at: string
  app_version: string
  components: HealthComponent[]
}

// ---------------------------------------------------------------------------
// Kimlik / kullanıcı
// ---------------------------------------------------------------------------
export interface RoleSummary {
  id: number
  code: string
  name_tr: string
  name_en: string
}

export interface Role extends RoleSummary {
  description?: string | null
  permissions: string[]
  is_system: boolean
}

export interface User {
  id: number
  email: string
  full_name: string
  phone?: string | null
  avatar_url?: string | null
  language: string
  theme: string
  is_active: boolean
  is_superuser: boolean
  must_change_password: boolean
  onboarding_completed: boolean
  training_mode: boolean
  last_login_at?: string | null
  roles: RoleSummary[]
  created_at?: string | null
}

export interface CurrentUser extends User {
  permissions: string[]
  student_id?: number | null
  guardian_id?: number | null
  instructor_id?: number | null
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// ---------------------------------------------------------------------------
// Kişiler
// ---------------------------------------------------------------------------
export type SwimLevel =
  | 'beginner'
  | 'elementary'
  | 'intermediate'
  | 'advanced'
  | 'competitive'
  | 'elite'
export type StudentStatus = 'active' | 'passive' | 'trial' | 'frozen' | 'left'
export type Gender = 'female' | 'male' | 'unspecified'

export interface GuardianBrief {
  id: number
  full_name: string
  phone: string
  relationship_type: string
  email?: string | null
}

export interface StudentBrief {
  id: number
  student_number: string
  first_name: string
  last_name: string
  full_name: string
  swim_level: string
  status: string
  age?: number | null
  photo_url?: string | null
}

export interface Group {
  id: number
  name: string
  description?: string | null
  level: SwimLevel
  min_age?: number | null
  max_age?: number | null
  color: string
  capacity: number
  is_active: boolean
  default_instructor_id?: number | null
  student_count: number
}

export interface InstructorBrief {
  id: number
  employee_number: string
  full_name: string
  title?: string | null
  photo_url?: string | null
}

export interface Student {
  id: number
  student_number: string
  first_name: string
  last_name: string
  full_name: string
  birth_date?: string | null
  age?: number | null
  gender: Gender
  phone?: string | null
  email?: string | null
  address?: string | null
  emergency_contact_name?: string | null
  emergency_contact_phone?: string | null
  swim_level: SwimLevel
  status: StudentStatus
  registration_date: string
  left_date?: string | null
  group_id?: number | null
  primary_instructor_id?: number | null
  goals?: string | null
  notes?: string | null
  health_notes?: string | null
  special_needs?: string | null
  consent_given: boolean
  photo_url?: string | null
  is_demo: boolean
  user_id?: number | null
  guardians: GuardianBrief[]
  group?: Group | null
  primary_instructor?: InstructorBrief | null
}

export interface StudentDetail extends Student {
  active_membership?: Record<string, unknown> | null
  attendance_rate?: number | null
  total_lessons: number
  outstanding_balance: number
  personal_best_count: number
}

export interface Guardian {
  id: number
  first_name: string
  last_name: string
  full_name: string
  relationship_type: string
  phone: string
  secondary_phone?: string | null
  email?: string | null
  address?: string | null
  occupation?: string | null
  notes?: string | null
  user_id?: number | null
  is_demo: boolean
  students: StudentBrief[]
}

export interface Certificate {
  id: number
  instructor_id: number
  name: string
  issuer?: string | null
  issued_date?: string | null
  expiry_date?: string | null
  document_url?: string | null
  is_expired: boolean
}

export interface Availability {
  id: number
  instructor_id: number
  weekday: number
  start_time: string
  end_time: string
}

export interface Leave {
  id: number
  instructor_id: number
  start_date: string
  end_date: string
  leave_type: string
  reason?: string | null
  approved: boolean
}

export interface Instructor {
  id: number
  employee_number: string
  first_name: string
  last_name: string
  full_name: string
  birth_date?: string | null
  gender: Gender
  phone?: string | null
  email?: string | null
  title?: string | null
  specialties: string[]
  hire_date?: string | null
  is_active: boolean
  max_weekly_hours: number
  hourly_rate?: number | null
  monthly_salary?: number | null
  bio?: string | null
  notes?: string | null
  photo_url?: string | null
  is_demo: boolean
  user_id?: number | null
  certificates: Certificate[]
  availabilities: Availability[]
}

export interface InstructorDetail extends Instructor {
  student_count: number
  weekly_lesson_count: number
  weekly_hours: number
  upcoming_lessons: number
  attendance_rate?: number | null
  leaves: Leave[]
}

export interface InstructorWorkload {
  instructor_id: number
  full_name: string
  lesson_count: number
  total_hours: number
  student_count: number
  occupancy_rate: number
  cancellation_rate: number
  private_ratio: number
}

// ---------------------------------------------------------------------------
// Tesis
// ---------------------------------------------------------------------------
export interface Lane {
  id: number
  pool_id: number
  lane_number: number
  name?: string | null
  display_name: string
  width_m?: number | null
  depth_m?: number | null
  max_swimmers: number
  is_active: boolean
  purpose?: string | null
  notes?: string | null
}

export interface Pool {
  id: number
  name: string
  code?: string | null
  location?: string | null
  length_m: number
  width_m?: number | null
  depth_min_m?: number | null
  depth_max_m?: number | null
  lane_count: number
  capacity: number
  course_type: 'short' | 'long'
  opening_time: string
  closing_time: string
  operating_hours: string
  status: 'operational' | 'maintenance' | 'closed'
  water_temperature_c?: number | null
  air_temperature_c?: number | null
  is_indoor: boolean
  is_heated: boolean
  notes?: string | null
  is_demo: boolean
  lanes: Lane[]
}

export interface PoolSummary {
  id: number
  name: string
  status: string
  lane_count: number
  active_lane_count: number
  today_lesson_count: number
  occupancy_rate: number
}

export interface LaneSlot {
  lane_id: number
  lane_number: number
  lane_name: string
  start_at: string
  end_at: string
  lesson_id?: number | null
  lesson_title?: string | null
  lesson_type?: string | null
  instructor_name?: string | null
  enrolled: number
  capacity: number
  color: string
  is_free: boolean
}

export interface LanePlan {
  pool_id: number
  pool_name: string
  date: string
  slots: LaneSlot[]
  free_lane_count: number
  used_lane_count: number
  occupancy_rate: number
}

export interface WaterQualityLog {
  id: number
  pool_id: number
  measured_at: string
  ph?: number | null
  chlorine_ppm?: number | null
  temperature_c?: number | null
  turbidity_ntu?: number | null
  measured_by?: string | null
  is_within_limits: boolean
  notes?: string | null
}

export interface Maintenance {
  id: number
  pool_id: number
  start_at: string
  end_at: string
  maintenance_type: string
  description?: string | null
  cost?: number | null
  performed_by?: string | null
  is_completed: boolean
}

// ---------------------------------------------------------------------------
// Dersler
// ---------------------------------------------------------------------------
export type LessonType =
  | 'group' | 'private' | 'kids' | 'baby' | 'adult' | 'beginner'
  | 'intermediate' | 'advanced' | 'competition_team' | 'adaptive'
  | 'conditioning' | 'trial' | 'makeup'

export type LessonStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | 'postponed'

export interface Enrollment {
  id: number
  lesson_id: number
  student_id: number
  student_name?: string | null
  student_number?: string | null
  status: 'enrolled' | 'waitlist' | 'cancelled'
  membership_id?: number | null
  credit_consumed: boolean
  notes?: string | null
}

export interface Lesson {
  id: number
  title: string
  lesson_type: LessonType
  status: LessonStatus
  start_at: string
  end_at: string
  pool_id: number
  lane_id?: number | null
  instructor_id?: number | null
  group_id?: number | null
  series_id?: number | null
  capacity: number
  price?: number | null
  color: string
  notes?: string | null
  cancellation_reason?: string | null
  duration_minutes: number
  enrolled_count: number
  occupancy_rate: number
  is_demo: boolean
  pool_name?: string | null
  lane_name?: string | null
  instructor_name?: string | null
  group_name?: string | null
}

export interface LessonDetail extends Lesson {
  enrollments: Enrollment[]
  attendance_recorded: boolean
}

export interface CalendarEvent {
  id: number
  title: string
  start: string
  end: string
  lesson_type: string
  status: string
  color: string
  pool_id: number
  pool_name: string
  lane_id?: number | null
  lane_name?: string | null
  instructor_id?: number | null
  instructor_name?: string | null
  group_name?: string | null
  enrolled_count: number
  capacity: number
}

export interface ConflictItem {
  kind: string
  message_key: string
  message: string
  lesson_id?: number | null
  lesson_title?: string | null
  entity_id?: number | null
  entity_name?: string | null
  start_at?: string | null
  end_at?: string | null
  severity: 'error' | 'warning'
}

export interface ConflictCheckResponse {
  has_conflict: boolean
  conflicts: ConflictItem[]
  warnings: ConflictItem[]
}

// ---------------------------------------------------------------------------
// Yoklama
// ---------------------------------------------------------------------------
export type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused' | 'cancelled' | 'makeup'

export interface AttendanceSheetRow {
  student_id: number
  student_number: string
  full_name: string
  photo_url?: string | null
  enrollment_status: string
  attendance_id?: number | null
  status?: AttendanceStatus | null
  late_minutes?: number | null
  notes?: string | null
  membership_remaining?: number | null
}

export interface AttendanceSheet {
  lesson_id: number
  lesson_title: string
  start_at: string
  end_at: string
  pool_name?: string | null
  lane_name?: string | null
  instructor_name?: string | null
  is_recorded: boolean
  rows: AttendanceSheetRow[]
}

export interface AttendanceRecord {
  id: number
  lesson_id: number
  student_id: number
  student_name?: string | null
  student_number?: string | null
  lesson_title?: string | null
  lesson_start?: string | null
  status: AttendanceStatus
  method: string
  checked_in_at?: string | null
  late_minutes?: number | null
  excuse_reason?: string | null
  notes?: string | null
  makeup_lesson_id?: number | null
}

// ---------------------------------------------------------------------------
// Üyelik / finans
// ---------------------------------------------------------------------------
export type MembershipStatus = 'active' | 'expired' | 'frozen' | 'cancelled' | 'pending'
export type PaymentMethod = 'cash' | 'card' | 'transfer' | 'online' | 'other'
export type PaymentStatus = 'paid' | 'pending' | 'partial' | 'overdue' | 'refunded' | 'cancelled'

export interface Package {
  id: number
  name: string
  name_en?: string | null
  package_type: string
  description?: string | null
  lesson_count?: number | null
  duration_days?: number | null
  price: number
  currency: string
  max_freeze_days: number
  is_active: boolean
  color: string
  active_membership_count: number
}

export interface MembershipFreeze {
  id: number
  membership_id: number
  start_date: string
  end_date: string
  reason?: string | null
  days: number
}

export interface Membership {
  id: number
  student_id: number
  student_name?: string | null
  student_number?: string | null
  package_id: number
  package_name?: string | null
  package_type?: string | null
  start_date: string
  end_date?: string | null
  status: MembershipStatus
  total_credits?: number | null
  used_credits: number
  remaining_credits?: number | null
  days_remaining?: number | null
  usage_rate: number
  price_paid: number
  discount_amount: number
  auto_renew: boolean
  is_expiring_soon: boolean
  notes?: string | null
  freezes: MembershipFreeze[]
}

export interface Payment {
  id: number
  receipt_number: string
  student_id?: number | null
  student_name?: string | null
  membership_id?: number | null
  invoice_id?: number | null
  amount: number
  currency: string
  method: PaymentMethod
  status: PaymentStatus
  payment_date: string
  reference?: string | null
  description?: string | null
  refunded_amount: number
  net_amount: number
  created_at?: string | null
}

export interface Invoice {
  id: number
  invoice_number: string
  student_id?: number | null
  student_name?: string | null
  membership_id?: number | null
  issue_date: string
  due_date: string
  subtotal: number
  discount_amount: number
  tax_amount: number
  total_amount: number
  paid_amount: number
  balance: number
  currency: string
  status: PaymentStatus
  is_overdue: boolean
  days_overdue: number
  description?: string | null
}

export interface Expense {
  id: number
  title: string
  category: string
  amount: number
  currency: string
  expense_date: string
  method: PaymentMethod
  vendor?: string | null
  invoice_reference?: string | null
  description?: string | null
  is_recurring: boolean
}

export interface FinanceSummary {
  period_start: string
  period_end: string
  currency: string
  total_income: number
  total_expense: number
  net_income: number
  outstanding_total: number
  overdue_total: number
  overdue_count: number
  collection_rate: number
  revenue_per_student: number
  active_student_count: number
  income_by_method: Record<string, number>
  expense_by_category: Record<string, number>
  income_by_package: Record<string, number>
  monthly_series: Array<{ label: string; income: number; expense: number; net: number }>
}

// ---------------------------------------------------------------------------
// Performans / yarışma
// ---------------------------------------------------------------------------
export type Stroke = 'freestyle' | 'backstroke' | 'breaststroke' | 'butterfly' | 'medley'

export interface PerformanceRecord {
  id: number
  student_id: number
  student_name?: string | null
  instructor_id?: number | null
  instructor_name?: string | null
  lesson_id?: number | null
  stroke: Stroke
  distance_m: number
  course_type: 'short' | 'long'
  time_seconds: number
  formatted_time: string
  splits: number[]
  stroke_rate?: number | null
  stroke_count?: number | null
  reaction_time?: number | null
  turn_time?: number | null
  recorded_date: string
  is_personal_best: boolean
  is_competition: boolean
  heart_rate_avg?: number | null
  perceived_effort?: number | null
  notes?: string | null
  event_name: string
  pace_per_100m?: number | null
  speed_ms?: number | null
}

export interface PerformanceTrendPoint {
  date: string
  time_seconds: number
  formatted_time: string
  is_personal_best: boolean
  moving_average?: number | null
}

export interface PerformanceEventAnalysis {
  stroke: string
  distance_m: number
  course_type: string
  record_count: number
  best_time: number
  worst_time: number
  mean_time: number
  median_time: number
  std_dev?: number | null
  percentile_25?: number | null
  percentile_75?: number | null
  first_time: number
  last_time: number
  improvement_seconds: number
  improvement_percent: number
  change_30d?: number | null
  change_90d?: number | null
  trend: 'improving' | 'stable' | 'declining'
  trend_slope?: number | null
  points: PerformanceTrendPoint[]
}

export interface StudentPerformanceSummary {
  student_id: number
  student_name: string
  total_records: number
  training_count: number
  competition_count: number
  personal_best_count: number
  first_record_date?: string | null
  last_record_date?: string | null
  events: PerformanceEventAnalysis[]
  strongest_stroke?: string | null
  weakest_stroke?: string | null
  overall_improvement_percent?: number | null
}

export interface PersonalBest {
  id: number
  student_id: number
  stroke: string
  distance_m: number
  course_type: string
  time_seconds: number
  formatted_time: string
  achieved_date: string
}

export interface TopImprover {
  student_id: number
  student_name: string
  stroke: string
  distance_m: number
  first_time: number
  last_time: number
  improvement_seconds: number
  improvement_percent: number
  record_count: number
}

export interface DecliningAthlete {
  student_id: number
  student_name: string
  stroke: string
  distance_m: number
  recent_mean: number
  baseline_mean: number
  decline_seconds: number
  decline_percent: number
  record_count: number
  last_record_date: string
}

export interface CompetitionEntry {
  id: number
  event_id: number
  student_id: number
  student_name?: string | null
  seed_time_seconds?: number | null
  heat_number?: number | null
  lane_number?: number | null
  result_time_seconds?: number | null
  formatted_result?: string | null
  rank?: number | null
  medal?: string | null
  is_personal_best: boolean
  is_club_record: boolean
  is_disqualified: boolean
  improvement_seconds?: number | null
  notes?: string | null
}

export interface CompetitionEvent {
  id: number
  competition_id: number
  stroke: string
  distance_m: number
  gender_category: string
  age_category?: string | null
  event_order: number
  scheduled_date?: string | null
  name: string
  entry_count: number
  entries: CompetitionEntry[]
}

export interface Competition {
  id: number
  name: string
  location?: string | null
  organizer?: string | null
  level: string
  course_type: string
  start_date: string
  end_date: string
  registration_deadline?: string | null
  description?: string | null
  is_completed: boolean
  event_count: number
  entry_count: number
  medal_count: number
  events: CompetitionEvent[]
}

export interface ClubRecord {
  id: number
  stroke: string
  distance_m: number
  course_type: string
  gender_category: string
  age_category: string
  student_id?: number | null
  holder_name: string
  time_seconds: number
  formatted_time: string
  achieved_date: string
  competition_name?: string | null
}

// ---------------------------------------------------------------------------
// İstatistik
// ---------------------------------------------------------------------------
export interface SeriesPoint {
  label: string
  value: number
  secondary?: number | null
  date?: string | null
}

export interface Distribution {
  label: string
  value: number
  percent: number
  color?: string | null
}

export interface ComparisonMetric {
  key: string
  label_tr: string
  label_en: string
  current: number
  previous?: number | null
  change_absolute?: number | null
  change_percent?: number | null
  unit: string
  direction: string
}

export interface DashboardAlert {
  key: string
  severity: string
  title_tr: string
  title_en: string
  count: number
  link?: string | null
}

export interface DashboardTodayLesson {
  id: number
  title: string
  start_at: string
  end_at: string
  pool_name?: string | null
  lane_name?: string | null
  instructor_name?: string | null
  enrolled_count: number
  capacity: number
  status: string
  attendance_recorded: boolean
}

export interface DashboardSummary {
  generated_at: string
  active_students: number
  total_students: number
  lessons_today: number
  lessons_completed_today: number
  active_instructors: number
  instructors_on_leave: number
  pool_occupancy_rate: number
  lanes_in_use: number
  lanes_free: number
  total_lanes: number
  due_today: number
  collected_today: number
  overdue_amount: number
  overdue_count: number
  monthly_revenue: number
  monthly_expense: number
  attendance_today_rate?: number | null
  attendance_pending_lessons: number
  upcoming_trials: number
  new_registrations_this_month: number
  expiring_memberships: number
  declining_athletes: number
  upcoming_competitions: number
  unread_notifications: number
  today_lessons: DashboardTodayLesson[]
  alerts: DashboardAlert[]
  revenue_trend: SeriesPoint[]
  attendance_trend: SeriesPoint[]
  level_distribution: Distribution[]
  pool_load: SeriesPoint[]
}

export interface StudentStatistics {
  period_start: string
  period_end: string
  total_students: number
  active_students: number
  passive_students: number
  trial_students: number
  new_registrations: number
  lost_students: number
  growth_rate: number
  retention_rate: number
  churn_rate: number
  average_membership_days: number
  attendance_rate: number
  age_distribution: Distribution[]
  level_distribution: Distribution[]
  group_distribution: Distribution[]
  gender_distribution: Distribution[]
  registration_trend: SeriesPoint[]
  comparisons: ComparisonMetric[]
}

export interface InstructorStatRow {
  instructor_id: number
  full_name: string
  student_count: number
  lesson_count: number
  total_hours: number
  occupancy_rate: number
  attendance_rate: number
  cancellation_rate: number
  private_lesson_count: number
  group_lesson_count: number
  private_ratio: number
  student_improvement_percent?: number | null
}

export interface InstructorStatistics {
  period_start: string
  period_end: string
  rows: InstructorStatRow[]
  total_hours: number
  average_students_per_instructor: number
  average_occupancy: number
  disclaimer_tr: string
  disclaimer_en: string
}

export interface HeatmapCell {
  weekday: number
  hour: number
  value: number
  lesson_count: number
}

export interface PoolStatistics {
  period_start: string
  period_end: string
  pool_usage: Distribution[]
  lane_usage: Distribution[]
  hourly_load: SeriesPoint[]
  daily_load: SeriesPoint[]
  weekly_load: SeriesPoint[]
  busiest_hour?: string | null
  quietest_hour?: string | null
  most_used_lane?: string | null
  overall_occupancy: number
  free_capacity_hours: number
  average_lanes_per_lesson: number
  heatmap: HeatmapCell[]
}

export interface AttendanceStatistics {
  period_start: string
  period_end: string
  overall_rate: number
  present_count: number
  absent_count: number
  late_count: number
  excused_count: number
  cancelled_count: number
  makeup_count: number
  no_show_rate: number
  late_rate: number
  excuse_rate: number
  makeup_rate: number
  by_group: Distribution[]
  by_instructor: Distribution[]
  lowest_students: Array<Record<string, unknown>>
  trend: SeriesPoint[]
}

export interface KpiValue {
  key: string
  label_tr: string
  label_en: string
  value: number
  unit: string
  target?: number | null
  achievement_percent?: number | null
  status: 'good' | 'warning' | 'bad' | 'neutral'
  previous_value?: number | null
  change_percent?: number | null
}

export interface KpiDashboard {
  period_start: string
  period_end: string
  kpis: KpiValue[]
}

export interface CorrelationResult {
  variable_a: string
  variable_b: string
  coefficient: number
  sample_size: number
  strength: string
  disclaimer_tr: string
  disclaimer_en: string
}

export interface CohortAnalysis {
  cohorts: Array<{ cohort: string; size: number; retention_by_month: number[] }>
  months: number
  note_tr: string
  note_en: string
}

// ---------------------------------------------------------------------------
// Raporlar
// ---------------------------------------------------------------------------
export interface ReportDefinition {
  key: string
  title_tr: string
  title_en: string
  description_tr: string
  description_en: string
  category: string
  supported_formats: string[]
  filters: string[]
  required_permission: string
}

export interface ReportPreview {
  report_key: string
  title: string
  generated_at: string
  period_label: string
  columns: Array<{ key: string; label: string }>
  rows: Array<Record<string, unknown>>
  totals: Record<string, unknown>
  summary: Record<string, unknown>
  row_count: number
}

// ---------------------------------------------------------------------------
// Sistem
// ---------------------------------------------------------------------------
export interface Notification {
  id: number
  notification_type: string
  severity: 'info' | 'success' | 'warning' | 'error'
  title: string
  body?: string | null
  link?: string | null
  entity_type?: string | null
  entity_id?: string | null
  is_read: boolean
  created_at: string
}

export interface AuditLog {
  id: number
  user_id?: number | null
  user_email?: string | null
  action: string
  entity_type: string
  entity_id?: string | null
  summary?: string | null
  changes: Record<string, unknown>
  ip_address?: string | null
  occurred_at: string
}

export interface AppSetting {
  id: number
  key: string
  value: unknown
  category: string
  description?: string | null
  updated_at?: string | null
}

export interface AboutInfo {
  app_name: string
  version: string
  build: string
  git_commit?: string | null
  database_revision?: string | null
  database_engine: string
  python_version: string
  platform: string
  last_updated?: string | null
  license: string
}

export interface BackupRecord {
  id: number
  backup_id: string
  backup_type: string
  status: string
  file_name: string
  size_bytes: number
  size_mb: number
  checksum_sha256?: string | null
  app_version?: string | null
  db_revision?: string | null
  record_counts: Record<string, number>
  is_protected: boolean
  verified_at?: string | null
  verification_message?: string | null
  error_message?: string | null
  created_at: string
}

export interface BackupStatusInfo {
  last_backup_at?: string | null
  last_successful_backup_at?: string | null
  last_backup_size_mb?: number | null
  backup_location: string
  total_backup_count: number
  total_size_mb: number
  protected_count: number
  schedule_enabled: boolean
  schedule_cron?: string | null
  next_backup_at?: string | null
  status: string
}

export interface BackupVerifyResult {
  backup_id: string
  is_valid: boolean
  checks: Array<{ check: string; result: string; detail?: string }>
  message: string
}

export interface RestorePreview {
  backup_id: string
  backup_created_at: string
  backup_app_version?: string | null
  backup_db_revision?: string | null
  current_db_revision?: string | null
  revision_compatible: boolean
  current_counts: Record<string, number>
  backup_counts: Record<string, number>
  differences: Record<string, number>
  warnings: string[]
  integrity_ok: boolean
}

export interface SearchHit {
  entity_type: string
  id: number
  title: string
  subtitle?: string | null
  route: string
  badge?: string | null
  score: number
}

export interface SearchResponse {
  query: string
  total: number
  groups: Record<string, SearchHit[]>
  took_ms: number
}

export interface PaletteCommand {
  id: string
  label: string
  route: string
  icon: string
}

// ---------------------------------------------------------------------------
// Eğitim merkezi
// ---------------------------------------------------------------------------
export interface TutorialStep {
  order: number
  title_tr: string
  title_en: string
  body_tr: string
  body_en: string
  target_route?: string | null
  action_hint_tr?: string | null
  action_hint_en?: string | null
}

export interface Tutorial {
  id: string
  title_tr: string
  title_en: string
  description_tr: string
  description_en: string
  category: string
  roles: string[]
  estimated_minutes: number
  steps: TutorialStep[]
  status: 'not_started' | 'in_progress' | 'completed'
  current_step: number
  total_steps: number
  progress_percent: number
}

export interface TrainingOverview {
  tracks: Array<{
    id: string
    title: string
    total: number
    completed: number
    percent: number
    recommended: boolean
    tutorials: Array<{ id: string; title: string; status: string; minutes: number }>
  }>
  total_tutorials: number
  completed: number
  in_progress: number
  overall_percent: number
}

export interface OnboardingState {
  completed: boolean
  current_step: number
  steps_done: string[]
  organization_configured: boolean
  has_pool: boolean
  has_instructor: boolean
  has_student: boolean
  ai_configured: boolean
  backup_configured: boolean
}

// ---------------------------------------------------------------------------
// Yapay zekâ
// ---------------------------------------------------------------------------
export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface ProviderStatus {
  provider: string
  display_name: string
  enabled: boolean
  available: boolean
  endpoint?: string | null
  model?: string | null
  api_key_set: boolean
  api_key_masked: string
  latency_ms?: number | null
  model_count?: number | null
  last_checked_at?: string | null
  error_message?: string | null
  is_local: boolean
  privacy_note_tr?: string | null
  privacy_note_en?: string | null
}

export interface AIControlCenter {
  mode: string
  fallback_chain: string[]
  response_language: string
  providers: ProviderStatus[]
  usage_today: TokenUsage
  usage_total: TokenUsage
  task_counts: Record<string, number>
  error_count_24h: number
  local_only_mode: boolean
}

export interface ModelInfo {
  id: string
  provider: string
  owned_by?: string | null
  capabilities: string[]
  capability_source: string
  context_length?: number | null
}

export interface ConnectionTestResult {
  provider: string
  test_name: string
  result: 'PASS' | 'FAIL' | 'SKIPPED'
  detail?: string | null
  duration_ms?: number | null
}

export interface ConnectionTestReport {
  provider: string
  overall: 'PASS' | 'FAIL' | 'SKIPPED'
  tests: ConnectionTestResult[]
  checked_at: string
}

export interface AIAnalysisResponse {
  question: string
  scope: string
  metrics: Record<string, unknown>
  metrics_summary_tr: string
  metrics_summary_en: string
  data_points: number
  data_sufficient: boolean
  ai_available: boolean
  ai_interpretation?: string | null
  ai_possible_causes: string[]
  ai_recommendations: string[]
  ai_disclaimer_tr: string
  ai_disclaimer_en: string
  provider?: string | null
  model?: string | null
  duration_ms: number
  task_id?: number | null
}

export interface AITask {
  id: number
  kind: string
  status: string
  title: string
  provider?: string | null
  model?: string | null
  prompt_preview?: string | null
  result_preview?: string | null
  error_message?: string | null
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  duration_ms: number
  fallback_used: boolean
  attempted_providers: string[]
  file_changes: Array<Record<string, unknown>>
  test_result: Record<string, unknown>
  user_id?: number | null
  started_at: string
  finished_at?: string | null
}

export interface PromptTemplate {
  id: string
  category: string
  title_tr: string
  title_en: string
  prompt_tr: string
  prompt_en: string
  description_tr?: string | null
  description_en?: string | null
  requires_context: string[]
  icon?: string | null
}

export interface AgentStep {
  step: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  detail?: string | null
  duration_ms?: number | null
  output?: string | null
}

export interface FileChange {
  path: string
  action: 'create' | 'modify' | 'delete'
  diff?: string | null
  original_size?: number | null
  new_size?: number | null
  lines_added: number
  lines_removed: number
}

export interface DeveloperPlanResponse {
  task_id: number
  instruction: string
  plan: string[]
  analysis?: string | null
  steps: AgentStep[]
  changes: FileChange[]
  patch_id?: string | null
  test_result?: Record<string, unknown> | null
  requires_approval: boolean
  apply_allowed: boolean
  warnings: string[]
  provider?: string | null
  model?: string | null
}

export interface CommandPolicyInfo {
  shell_enabled: boolean
  apply_enabled: boolean
  project_root: string
  allowed_commands: string[]
  blocked_patterns: string[]
  write_scope: string
  requires_confirmation: string[]
}

export interface CAIOFinding {
  id: number
  category: string
  severity: string
  title: string
  description: string
  recommendation?: string | null
  evidence: Record<string, unknown>
  source: string
  status: string
  is_ai_generated: boolean
  ai_provider?: string | null
  created_at: string
  resolved_at?: string | null
}

/** CAIO gözlem bloğu - iç içe ölçüm nesneleri (logs, ai_usage, security, ...) */
export type CAIOObservationValue =
  | string
  | number
  | boolean
  | null
  | CAIOObservationValue[]
  | { [key: string]: CAIOObservationValue }

export interface CAIOReport {
  run_at: string
  duration_ms: number
  observations: Record<string, CAIOObservationValue>
  findings: CAIOFinding[]
  findings_by_severity: Record<string, number>
  ai_available: boolean
  ai_summary?: string | null
  ai_proposals: string[]
  provider?: string | null
}
