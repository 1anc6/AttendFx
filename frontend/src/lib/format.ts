/** Dates are shown in India time, whatever the viewer's device clock says. */

const TZ = 'Asia/Kolkata'
const DAY = 86_400_000

const dateFmt = new Intl.DateTimeFormat('en-IN', {
  timeZone: TZ,
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})
const rtf = new Intl.RelativeTimeFormat('en-IN', { numeric: 'auto' })

const dateTimeFmt = new Intl.DateTimeFormat('en-IN', {
  timeZone: TZ,
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDate(iso: string): string {
  return dateFmt.format(new Date(iso))
}

export function formatDateTime(iso: string): string {
  return dateTimeFmt.format(new Date(iso))
}

export function daysUntil(iso: string, now = Date.now()): number {
  return Math.ceil((new Date(iso).getTime() - now) / DAY)
}

export function timeAgo(iso: string, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 60) return 'just now'
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute')
  if (abs < DAY / 1000) return rtf.format(Math.round(seconds / 3600), 'hour')
  if (abs < (30 * DAY) / 1000) return rtf.format(Math.round(seconds / 86400), 'day')
  return formatDate(iso)
}

export type Tone = 'ok' | 'warn' | 'bad'

/** Expiry colour: red inside a week, amber inside a month. */
export function expiryTone(daysLeft: number): Tone {
  if (daysLeft <= 7) return 'bad'
  if (daysLeft <= 30) return 'warn'
  return 'ok'
}
