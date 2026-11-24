/** Typed client for the AttendFX JSON API (/api). Same origin, cookie session, CSRF header. */

export type Role = 'student' | 'teacher' | 'admin'

export interface User {
  id: string
  name: string
  email: string
  role: Role
}

export interface Me {
  user: User
  /** Signed in with a temporary password: only Account works until it is replaced. */
  must_change_password: boolean
  csrf_token: string
  expires_at: string
}

export type PersonStatus = 'all' | 'active' | 'locked' | 'must_change' | 'disabled'

export interface Person extends User {
  created_at: string
  last_sign_in_at: string | null
  locked_until: string | null
  disabled_at: string | null
  must_change_password: boolean
  active_keys: number
}

export interface PeopleCounts {
  total: number
  student: number
  teacher: number
  admin: number
  locked: number
  must_change: number
  disabled: number
}

export interface PeoplePage {
  people: Person[]
  total: number
  page: number
  page_size: number
  counts: PeopleCounts
}

export interface PeopleQuery {
  q: string
  role: Role | 'all'
  status: PersonStatus
  page: number
}

/** A new or reset account. The temporary password is shown once and never stored readable. */
export interface IssuedPerson {
  id: string
  name: string
  email: string
  role: Role
  temporary_password: string
}

export interface ImportRow {
  line: number
  name: string
  email: string
  role: Role
}

export interface ImportResult {
  rows: ImportRow[]
  errors: { line: number; message: string }[]
  created: boolean
  people: IssuedPerson[]
}

export type KeyStatus = 'active' | 'expired' | 'revoked'

export interface AccessKey {
  id: string
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
  expires_at: string | null
  revoked_at: string | null
  status: KeyStatus
}

export interface KeyList {
  keys: AccessKey[]
  active: number
  max_active: number
  max_days: number
}

export interface IssuedKey {
  id: string
  key: string
  prefix: string
  name: string
  expires_at: string
}

/* ---------- Admin dashboards ---------- */

export interface BelowMinimum {
  student_id: string
  student_name: string
  course_code: string
  course_title: string
  teacher_name: string | null
  attended: number
  counted_sessions: number
  attended_percent: number
  risk: 'at_risk' | 'watch'
}

export interface Overview {
  term: { name: string; starts_on: string; ends_on: string } | null
  people: PeopleCounts
  assistant: { days: number; calls: number; people: number; problems: number; active_keys: number }
  attendance: {
    courses: number
    minimum_percent: number
    high_percent: number
    overall_percent: number | null
    funnel: {
      enrolled: number
      attended_any: number
      at_or_above_minimum: number
      at_or_above_high: number
    }
    fortnights: { starts_on: string; records: number; attended_percent: number | null }[]
    below_minimum: BelowMinimum[]
    students_below_minimum: number
    how_percent_is_calculated: string
  } | null
}

/* ---------- The student's own page ---------- */

export type MarkStatus = 'present' | 'absent' | 'late' | 'excused'

/** Room against the rule for the rest of the term. See backend/app/services/student.py. */
export type Room =
  | { kind: 'spare'; sessions: number }
  | { kind: 'need'; sessions: number }
  | { kind: 'cannot_reach' }
  | { kind: 'final' }
  | { kind: 'no_sessions' }

export interface MyCourse {
  course_code: string
  course_title: string
  teacher_name: string | null
  present: number
  absent: number
  late: number
  excused: number
  attended: number
  counted_sessions: number
  attended_percent: number | null
  remaining_sessions: number
  status: 'ok' | 'watch' | 'at_risk' | 'no_records'
  room: Room
}

export interface MyAttendance {
  term: { name: string; starts_on: string; ends_on: string } | null
  minimum_percent: number
  /** False when the college has not set a rule and the 75% default is shown as a guide. */
  rule_set: boolean
  overall: {
    present: number
    absent: number
    late: number
    excused: number
    attended: number
    counted_sessions: number
    attended_percent: number | null
  } | null
  courses: MyCourse[]
  recent: { starts_at: string; course_code: string; course_title: string; status: MarkStatus }[]
  fortnights: { starts_on: string; records: number; attended_percent: number | null }[]
  how_percent_is_calculated: string
}

export interface MyCourseSessions {
  course_code: string
  sessions: {
    starts_at: string
    ends_at: string
    status: MarkStatus | 'upcoming' | 'unmarked'
  }[]
}

export type Surface = 'mcp' | 'api' | 'cli'

export interface ActivityEvent {
  id: number
  ts: string
  surface: Surface
  action: string
  status: string
  ok: boolean
  latency_ms: number | null
  person: { id: string; name: string; email: string; role: Role } | null
  key_prefix: string | null
}

export interface ActivityQuery {
  q: string
  surface: Surface | 'all'
  outcome: 'all' | 'problems'
  page: number
}

export interface ActivityPage {
  events: ActivityEvent[]
  total: number
  page: number
  page_size: number
  retention_days: number
}

export type UsageWindow = 7 | 30 | 90

export interface Usage {
  days: UsageWindow
  generated_at: string
  totals: { assistant_calls: number; people: number; problems: number; web_events: number }
  daily: { day: string; assistant: number; web: number; problems: number }[]
  tools: {
    action: string
    calls: number
    problems: number
    median_ms: number | null
    p95_ms: number | null
  }[]
  people: {
    id: string
    name: string
    email: string
    role: Role
    calls: number
    last_call_at: string
  }[]
}

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let csrfToken: string | null = null

export function rememberCsrf(token: string | null) {
  csrfToken = token
}

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken

  let res: Response
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'Could not reach AttendFX. Check your connection and try again.')
  }
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : null
    throw new ApiError(res.status, detail ?? `Something went wrong (${res.status}).`)
  }
  return data as T
}

export const api = {
  me: () => request<Me>('GET', '/api/me'),
  signIn: (email: string, password: string) =>
    request<Me>('POST', '/api/auth/sign-in', { email, password }),
  signOut: () => request<void>('POST', '/api/auth/sign-out'),
  keys: () => request<KeyList>('GET', '/api/keys'),
  createKey: (name: string, days: number) =>
    request<IssuedKey>('POST', '/api/keys', { name, days }),
  revokeKey: (id: string) => request<{ status: string }>('POST', `/api/keys/${id}/revoke`),
  changePassword: (current_password: string, new_password: string) =>
    request<Me>('POST', '/api/account/password', { current_password, new_password }),

  people: ({ q, role, status, page }: PeopleQuery) => {
    const params = new URLSearchParams({ status, page: String(page) })
    if (q.trim()) params.set('q', q.trim())
    if (role !== 'all') params.set('role', role)
    return request<PeoplePage>('GET', `/api/people?${params}`)
  },
  createPerson: (name: string, email: string, role: Role) =>
    request<IssuedPerson>('POST', '/api/people', { name, email, role }),
  importPeople: (csv: string, dry_run: boolean) =>
    request<ImportResult>('POST', '/api/people/import', { csv, dry_run }),
  resetPassword: (id: string) =>
    request<{ id: string; temporary_password: string }>(
      'POST',
      `/api/people/${id}/reset-password`,
    ),
  unlockPerson: (id: string) =>
    request<{ id: string; unlocked: boolean }>('POST', `/api/people/${id}/unlock`),
  setDisabled: (id: string, disabled: boolean) =>
    request<{ id: string; disabled: boolean }>('POST', `/api/people/${id}/disabled`, {
      disabled,
    }),

  myAttendance: () => request<MyAttendance>('GET', '/api/me/attendance'),
  myCourse: (code: string) =>
    request<MyCourseSessions>('GET', `/api/me/attendance/${encodeURIComponent(code)}`),

  overview: () => request<Overview>('GET', '/api/admin/overview'),
  activity: ({ q, surface, outcome, page }: ActivityQuery) => {
    const params = new URLSearchParams({ outcome, page: String(page) })
    if (q.trim()) params.set('q', q.trim())
    if (surface !== 'all') params.set('surface', surface)
    return request<ActivityPage>('GET', `/api/admin/activity?${params}`)
  },
  usage: (days: UsageWindow) => request<Usage>('GET', `/api/admin/usage?days=${days}`),
}
