import { useQuery } from '@tanstack/react-query'
import { CalendarDays } from 'lucide-react'
import { useState } from 'react'
import {
  BarChart,
  DashboardSkeleton,
  LoadError,
  PageHeader,
  StatCard,
} from '@/components/dashboard'
import { Meter } from '@/components/meter'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { num, pct, share } from '@/lib/dashboard'
import { api, type BelowMinimum, type Overview } from '@/lib/api'

/** Plain calendar dates ("2026-08-03") have no time zone: format them as written. */
const dayFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' })
const day = (iso: string) => dayFmt.format(new Date(`${iso}T00:00:00Z`))

const FIRST_ROWS = 8

export function OverviewPage() {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: api.overview,
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Overview" description="Attendance across all courses this term.">
        {data?.term && (
          <span className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs text-muted-foreground">
            <CalendarDays className="size-3.5" />
            {data.term.name} · {day(data.term.starts_on)} to {day(data.term.ends_on)}
          </span>
        )}
      </PageHeader>

      {isPending && <DashboardSkeleton />}
      {isError && <LoadError message={error.message} onRetry={() => refetch()} />}
      {data && <OverviewBody data={data} />}
    </div>
  )
}

function OverviewBody({ data }: { data: Overview }) {
  const { people, assistant, attendance: att } = data
  const minimum = att?.minimum_percent ?? 75

  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Students"
          value={num(people.student)}
          hint={`${att ? `${num(att.courses)} courses · ` : ''}${num(people.teacher)} teachers`}
        />
        <StatCard
          label="Attendance this term"
          value={pct(att?.overall_percent)}
          hint="Present or late, of sessions counted"
        />
        <StatCard
          label={`Below ${minimum}%`}
          value={att ? num(att.students_below_minimum) : '–'}
          tone={att?.students_below_minimum ? 'bad' : undefined}
          hint={
            att
              ? `student${att.students_below_minimum === 1 ? '' : 's'}, in ${num(att.below_minimum.length)} enrolment${att.below_minimum.length === 1 ? '' : 's'}`
              : undefined
          }
        />
        <StatCard
          label={`Assistant calls, ${assistant.days} days`}
          value={num(assistant.calls)}
          tone={assistant.problems ? 'warn' : undefined}
          hint={`${num(assistant.people)} ${assistant.people === 1 ? 'person' : 'people'} · ${num(assistant.problems)} problem${assistant.problems === 1 ? '' : 's'} · ${num(assistant.active_keys)} active keys`}
        />
      </div>

      {att ? (
        <>
          <div className="grid gap-3 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle>Attendance by fortnight</CardTitle>
                <CardDescription>Share of marked sessions attended, present or late.</CardDescription>
              </CardHeader>
              <CardContent>
                <BarChart
                  summary={`Attendance by fortnight: ${att.fortnights
                    .map((f) => `${day(f.starts_on)} ${pct(f.attended_percent)}`)
                    .join(', ')}`}
                  series={[{ key: 'percent', label: 'Attended', className: 'bg-chart-1' }]}
                  data={att.fortnights.map((f) => ({
                    label: `From ${day(f.starts_on)}`,
                    tick: day(f.starts_on),
                    values: { percent: f.attended_percent },
                  }))}
                  format={(v) => pct(v)}
                  max={100}
                  guides={[
                    { value: 100, label: '100%' },
                    { value: 50, label: '50%' },
                    { value: minimum, label: `${minimum}%`, tone: 'bad' },
                  ]}
                />
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Enrolments by attendance</CardTitle>
                <CardDescription>Each student in each course, counted once.</CardDescription>
              </CardHeader>
              <CardContent>
                <Funnel att={att} />
              </CardContent>
            </Card>
          </div>

          <BelowMinimumCard rows={att.below_minimum} minimum={minimum} />

          <p className="text-xs text-muted-foreground">
            Rule: {att.how_percent_is_calculated} · Times in India time
          </p>
        </>
      ) : (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No term is running today, so there is no attendance to show.
          </CardContent>
        </Card>
      )}
    </>
  )
}

function Funnel({ att }: { att: NonNullable<Overview['attendance']> }) {
  const { funnel } = att
  const steps = [
    { label: 'Enrolled', value: funnel.enrolled },
    { label: 'Attended any session', value: funnel.attended_any },
    { label: `${att.minimum_percent}% or more`, value: funnel.at_or_above_minimum },
    { label: `${att.high_percent}% or more`, value: funnel.at_or_above_high },
  ]
  return (
    <ol className="grid gap-4">
      {steps.map((s) => {
        const part = share(s.value, funnel.enrolled)
        return (
          <li key={s.label} className="grid gap-1.5">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span>{s.label}</span>
              <span className="flex items-baseline gap-2 tabular-nums">
                <span className="font-semibold">{num(s.value)}</span>
                <span className="w-12 rounded-full bg-muted px-1.5 text-center text-xs text-muted-foreground">
                  {pct(part, 0)}
                </span>
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-track" aria-hidden="true">
              <div className="h-full rounded-full bg-chart-1" style={{ width: `${part ?? 0}%` }} />
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function RiskBadge({ risk }: { risk: BelowMinimum['risk'] }) {
  return risk === 'at_risk' ? <Badge variant="bad">At risk</Badge> : <Badge variant="warn">Watch</Badge>
}

function AttendanceMeter({ row }: { row: BelowMinimum }) {
  return (
    <Meter
      label={pct(row.attended_percent)}
      hint={`${row.attended} of ${row.counted_sessions} sessions`}
      value={row.attended_percent / 100}
      tone={row.risk === 'at_risk' ? 'bad' : 'warn'}
    />
  )
}

function BelowMinimumCard({ rows, minimum }: { rows: BelowMinimum[]; minimum: number }) {
  const [all, setAll] = useState(false)
  const shown = all ? rows : rows.slice(0, FIRST_ROWS)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Students below {minimum}%</CardTitle>
        <CardDescription>
          Lowest first. At risk means more than 10 points under the rule.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {rows.length === 0 ? (
          <p className="py-6 text-center text-muted-foreground">
            Everyone is at or above {minimum}% so far.
          </p>
        ) : (
          <>
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow className="border-0 bg-muted hover:bg-muted [&>th:first-child]:rounded-l-lg [&>th:last-child]:rounded-r-lg">
                    <TableHead>Student</TableHead>
                    <TableHead>Course</TableHead>
                    <TableHead>Teacher</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-56">Attendance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {shown.map((r) => (
                    <TableRow key={`${r.student_id}-${r.course_code}`}>
                      <TableCell className="py-3 font-semibold">{r.student_name}</TableCell>
                      <TableCell>
                        <div className="font-medium">{r.course_code}</div>
                        <div className="text-xs text-muted-foreground">{r.course_title}</div>
                      </TableCell>
                      <TableCell>{r.teacher_name ?? '–'}</TableCell>
                      <TableCell>
                        <RiskBadge risk={r.risk} />
                      </TableCell>
                      <TableCell>
                        <AttendanceMeter row={r} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <ul className="grid gap-3 md:hidden">
              {shown.map((r) => (
                <li key={`${r.student_id}-${r.course_code}`} className="grid gap-2 rounded-lg border p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate font-semibold">{r.student_name}</div>
                      <div className="truncate text-xs text-muted-foreground">
                        {r.course_code} · {r.course_title}
                        {r.teacher_name && ` · ${r.teacher_name}`}
                      </div>
                    </div>
                    <RiskBadge risk={r.risk} />
                  </div>
                  <AttendanceMeter row={r} />
                </li>
              ))}
            </ul>

            {rows.length > FIRST_ROWS && (
              <Button variant="outline" size="sm" className="justify-self-start" onClick={() => setAll((a) => !a)}>
                {all ? `Show the first ${FIRST_ROWS}` : `Show all ${rows.length}`}
              </Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
