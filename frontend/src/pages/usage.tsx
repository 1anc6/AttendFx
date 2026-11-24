import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  BarChart,
  DashboardSkeleton,
  LoadError,
  PageHeader,
  StatCard,
} from '@/components/dashboard'
import { Meter } from '@/components/meter'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { actionLabel, num, pct, share } from '@/lib/dashboard'
import { api, type Usage, type UsageWindow } from '@/lib/api'
import { formatDateTime, timeAgo } from '@/lib/format'
import { cn } from '@/lib/utils'

const WINDOWS: UsageWindow[] = [7, 30, 90]
const ROLE = { student: 'Student', teacher: 'Teacher', admin: 'Admin' } as const

const dayFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' })
const day = (iso: string) => dayFmt.format(new Date(`${iso}T00:00:00Z`))

const ms = (v: number | null) => (v === null ? '–' : `${num(v)} ms`)

export function UsagePage() {
  const [days, setDays] = useState<UsageWindow>(30)
  const { data, isPending, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['admin', 'usage', days],
    queryFn: () => api.usage(days),
    placeholderData: keepPreviousData,
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Usage" description="How much the assistant is used, and how fast it answers.">
        <div
          role="group"
          aria-label="Period"
          className={cn('inline-flex rounded-lg border p-0.5', isFetching && 'opacity-70')}
        >
          {WINDOWS.map((w) => (
            <button
              key={w}
              type="button"
              aria-pressed={days === w}
              onClick={() => setDays(w)}
              className={cn(
                'rounded-md px-3 py-1 text-sm transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
                days === w ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {w} days
            </button>
          ))}
        </div>
      </PageHeader>

      {isPending && <DashboardSkeleton />}
      {isError && <LoadError message={error.message} onRetry={() => refetch()} />}
      {data && <UsageBody data={data} />}
    </div>
  )
}

function UsageBody({ data }: { data: Usage }) {
  const { totals } = data
  // Label every day on a week; on longer spans, about one tick a week so they stay readable.
  const every = data.days <= 7 ? 1 : 7
  const last = data.daily.length - 1

  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Assistant calls" value={num(totals.assistant_calls)} hint={`Last ${data.days} days`} />
        <StatCard label="People using it" value={num(totals.people)} hint="With at least one call" />
        <StatCard
          label="Problems"
          value={num(totals.problems)}
          tone={totals.problems ? 'warn' : undefined}
          hint={`${pct(share(totals.problems, totals.assistant_calls))} of assistant calls`}
        />
        <StatCard label="Web and operator events" value={num(totals.web_events)} hint="Sign-ins, keys, accounts" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Calls per day</CardTitle>
          <CardDescription>India time days. Updated {formatDateTime(data.generated_at)}.</CardDescription>
        </CardHeader>
        <CardContent>
          <BarChart
            stacked
            summary={`Calls per day over ${data.days} days: ${num(totals.assistant_calls)} assistant calls and ${num(totals.web_events)} web and operator events.`}
            series={[
              { key: 'assistant', label: 'Assistant', className: 'bg-chart-1' },
              { key: 'web', label: 'Web and operator', className: 'bg-chart-3' },
            ]}
            data={data.daily.map((d, i) => ({
              label: day(d.day),
              tick: (last - i) % every === 0 ? day(d.day) : '',
              values: { assistant: d.assistant, web: d.web },
            }))}
          />
        </CardContent>
      </Card>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>By tool</CardTitle>
            <CardDescription>Assistant calls. Took is the median and the slowest 5%.</CardDescription>
          </CardHeader>
          <CardContent>
            {data.tools.length === 0 ? (
              <Empty />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tool</TableHead>
                    <TableHead className="w-40">Calls</TableHead>
                    <TableHead className="text-right">Problems</TableHead>
                    <TableHead className="text-right">Took</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.tools.map((t) => (
                    <TableRow key={t.action}>
                      <TableCell className="font-medium">{actionLabel(t.action)}</TableCell>
                      <TableCell>
                        <Meter
                          className="min-w-28"
                          label={num(t.calls)}
                          hint={pct(share(t.calls, totals.assistant_calls), 0)}
                          value={t.calls / Math.max(1, totals.assistant_calls)}
                          tone="ok"
                        />
                      </TableCell>
                      <TableCell className={cn('text-right tabular-nums', t.problems > 0 && 'text-warn')}>
                        {num(t.problems)}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap tabular-nums">
                        {ms(t.median_ms)}
                        <div className="text-xs text-muted-foreground">{ms(t.p95_ms)}</div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Most active people</CardTitle>
            <CardDescription>The ten who called the assistant most.</CardDescription>
          </CardHeader>
          <CardContent>
            {data.people.length === 0 ? (
              <Empty />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Person</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead className="text-right">Calls</TableHead>
                    <TableHead className="text-right">Last call</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.people.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell>
                        <div className="font-semibold">{p.name}</div>
                        <div className="text-xs text-muted-foreground">{p.email}</div>
                      </TableCell>
                      <TableCell>{ROLE[p.role]}</TableCell>
                      <TableCell className="text-right tabular-nums">{num(p.calls)}</TableCell>
                      <TableCell className="text-right whitespace-nowrap" title={formatDateTime(p.last_call_at)}>
                        {timeAgo(p.last_call_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}

function Empty() {
  return <p className="py-6 text-center text-muted-foreground">No assistant calls in this period.</p>
}
