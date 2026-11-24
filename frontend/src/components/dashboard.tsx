/** Shared pieces for the admin dashboards: stat tiles, a bar chart that also reads as a table,
 * plain-English labels for audit actions and outcomes, and a pager. */

import { BarChart3, ChevronLeft, ChevronRight, CircleAlert, Table2 } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { num } from '@/lib/dashboard'
import { cn } from '@/lib/utils'

/* ---------- Layout ---------- */

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="text-muted-foreground">{description}</p>
      </div>
      {children}
    </header>
  )
}

export function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'bad' | 'warn'
}) {
  return (
    <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <p className="mb-1.5 text-sm text-muted-foreground">{label}</p>
      <div
        className={cn(
          'text-2xl font-semibold tracking-tight tabular-nums',
          tone === 'bad' && 'text-bad',
          tone === 'warn' && 'text-warn',
        )}
      >
        {value}
      </div>
      {hint && <p className="mt-1 text-xs text-pretty text-muted-foreground">{hint}</p>}
    </div>
  )
}

/* ---------- Bar chart with a table view ---------- */

export interface Series {
  key: string
  label: string
  /** A Tailwind background class. Monochrome on purpose: colour is for status only. */
  className: string
}

export interface BarDatum {
  label: string
  /** Shown under the bars; defaults to `label`. Use '' to leave a gap on busy axes. */
  tick?: string
  values: Record<string, number | null>
}

/**
 * Grouped (or stacked) bars. Every chart has a table view with the same numbers, for screen
 * readers and for anyone who would rather read than eyeball. `format` renders a value.
 */
export function BarChart({
  data,
  series,
  summary,
  format = (v) => num(v),
  max,
  stacked = false,
  height = 176,
}: {
  data: BarDatum[]
  series: Series[]
  summary: string
  format?: (v: number) => string
  max?: number
  stacked?: boolean
  height?: number
}) {
  const [asTable, setAsTable] = useState(false)
  const id = useId()
  const top =
    max ??
    Math.max(
      1,
      ...data.map((d) =>
        stacked
          ? series.reduce((sum, s) => sum + (d.values[s.key] ?? 0), 0)
          : Math.max(...series.map((s) => d.values[s.key] ?? 0)),
      ),
    )

  // On phones, more than six labels collide: keep every other one, counting back from the last.
  const labelled = data.flatMap((d, i) => ((d.tick ?? d.label) ? [i] : []))
  const crowded = new Set(
    labelled.length > 6 ? labelled.filter((_, n) => (labelled.length - 1 - n) % 2 === 1) : [],
  )

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {series.length > 1 ? (
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-hidden={!asTable}>
            {series.map((s) => (
              <li key={s.key} className="inline-flex items-center gap-1.5">
                <i className={cn('size-2 rounded-[2px]', s.className)} />
                {s.label}
              </li>
            ))}
          </ul>
        ) : (
          <span />
        )}
        <Button
          variant="ghost"
          size="xs"
          aria-pressed={asTable}
          aria-controls={id}
          onClick={() => setAsTable((t) => !t)}
        >
          {asTable ? <BarChart3 /> : <Table2 />}
          {asTable ? 'Show chart' : 'Show table'}
        </Button>
      </div>

      <div id={id}>
        {asTable ? (
          <div className="max-h-72 overflow-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  {series.map((s) => (
                    <TableHead key={s.key} className="text-right">
                      {s.label}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((d) => (
                  <TableRow key={d.label}>
                    <TableCell>{d.label}</TableCell>
                    {series.map((s) => {
                      const v = d.values[s.key]
                      return (
                        <TableCell key={s.key} className="text-right tabular-nums">
                          {v === null || v === undefined ? '–' : format(v)}
                        </TableCell>
                      )
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <figure role="img" aria-label={summary} className="m-0">
            <div
              className="grid items-end gap-[3px] border-b border-border sm:gap-1.5"
              style={{ height, gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}
            >
              {data.map((d) => (
                <div
                  key={d.label}
                  className={cn(
                    'flex h-full justify-center',
                    stacked ? 'flex-col-reverse items-stretch' : 'items-end gap-[3px]',
                  )}
                  title={`${d.label}: ${series
                    .map((s) => `${s.label} ${d.values[s.key] == null ? '–' : format(d.values[s.key]!)}`)
                    .join(', ')}`}
                >
                  {series.map((s) => {
                    const v = d.values[s.key] ?? 0
                    const h = `${Math.max(0, Math.min(1, v / top)) * 100}%`
                    return (
                      <i
                        key={s.key}
                        className={cn(
                          'block',
                          stacked ? 'w-full max-w-6 self-center first:rounded-b-[2px] last:rounded-t-[2px]' : 'w-full max-w-3 rounded-t-[2px]',
                          s.className,
                        )}
                        style={{ height: h, minHeight: v > 0 ? 2 : 0 }}
                      />
                    )
                  })}
                </div>
              ))}
            </div>
            <div
              aria-hidden="true"
              className="mt-2 grid gap-[3px] text-center text-[11px] text-muted-foreground sm:gap-1.5"
              style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}
            >
              {data.map((d, i) => (
                <span
                  key={d.label}
                  className={cn(
                    'flex justify-center overflow-visible whitespace-nowrap',
                    crowded.has(i) && 'max-sm:invisible',
                  )}
                >
                  {d.tick ?? d.label}
                </span>
              ))}
            </div>
          </figure>
        )}
      </div>
    </div>
  )
}

/* ---------- Audit labels ---------- */

const STATUSES: Record<string, { label: string; tone: 'ok' | 'muted' | 'warn' | 'bad' }> = {
  ok: { label: 'OK', tone: 'ok' },
  no_records: { label: 'No records', tone: 'muted' },
  unchanged: { label: 'No change', tone: 'muted' },
  already_revoked: { label: 'Already revoked', tone: 'muted' },
  not_locked: { label: 'Was not locked', tone: 'muted' },
  invalid: { label: 'Invalid', tone: 'warn' },
  not_found: { label: 'Not found', tone: 'warn' },
  exists: { label: 'Already exists', tone: 'warn' },
  rejected: { label: 'Rejected', tone: 'warn' },
  limit: { label: 'Key limit', tone: 'warn' },
  disabled: { label: 'Account off', tone: 'warn' },
  denied: { label: 'Denied', tone: 'bad' },
  locked: { label: 'Locked out', tone: 'bad' },
  error: { label: 'Error', tone: 'bad' },
}

export function OutcomeBadge({ status }: { status: string }) {
  const s = STATUSES[status] ?? { label: status, tone: 'warn' as const }
  return <Badge variant={s.tone}>{s.label}</Badge>
}

/* ---------- Loading and errors ---------- */

export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Alert variant="destructive">
      <CircleAlert />
      <AlertDescription>
        {message}{' '}
        <button className="underline" onClick={onRetry}>
          Try again
        </button>
      </AlertDescription>
    </Alert>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="grid gap-3" aria-busy="true" aria-label="Loading">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-72 rounded-xl" />
    </div>
  )
}

/* ---------- Paging ---------- */

export function Pager({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number
  pageSize: number
  total: number
  onPage: (p: number) => void
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
      <span aria-live="polite">
        {num(from)}–{num(to)} of {num(total)}
      </span>
      {pages > 1 && (
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            <ChevronLeft />
            Newer
          </Button>
          <span className="px-2">
            Page {page} of {pages}
          </span>
          <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            Older
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  )
}
