/** Number formatting and plain-English audit labels for the admin dashboards. */

const nf = new Intl.NumberFormat('en-IN')

export function num(n: number): string {
  return nf.format(n)
}

export function pct(n: number | null | undefined, digits = 1): string {
  return n === null || n === undefined ? '–' : `${n.toFixed(digits).replace(/\.0$/, '')}%`
}

export function share(part: number, whole: number): number | null {
  return whole ? (100 * part) / whole : null
}

/* ---------- Audit labels ---------- */

const ACTIONS: Record<string, string> = {
  search_courses: 'Searched courses',
  course_details: 'Looked up a course',
  my_attendance: 'Attendance lookup',
  attendance_rule: 'Attendance rule',
  course_attendance_summary: 'Course attendance summary',
  low_attendance_list: 'Low attendance list',
  'resource:course_list_guide': 'Read the course list',
  'resource:term_calendar': 'Read the term calendar',
  'web.sign_in': 'Signed in',
  'web.sign_out': 'Signed out',
  'key.create': 'Created an access key',
  'key.revoke': 'Revoked an access key',
  'account.password_change': 'Changed password',
  'person.create': 'Added a person',
  'person.import': 'Imported people',
  'person.reset_password': 'Reset a password',
  'person.unlock': 'Unlocked an account',
  'person.disable': 'Turned an account off',
  'person.enable': 'Turned an account on',
}

export function actionLabel(action: string): string {
  return ACTIONS[action] ?? action
}

export const SURFACE_LABEL: Record<string, string> = {
  mcp: 'Assistant',
  api: 'Web',
  cli: 'Operator',
}
