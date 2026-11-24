import { useQuery } from '@tanstack/react-query'
import { CalendarDays, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { BarChart, DashboardSkeleton, LoadError, PageHeader, StatCard } from '@/components/dashboard'
import { Meter } from '@/components/meter'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api, type MyAttendance, type MyCourse, type MyCourseSessions } from '@/lib/api'
import { num, pct } from '@/lib/dashboard'
import { formatDateTime, type Tone } from '@/lib/format'
import { cn } from '@/lib/utils'

const dayFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' })
const day = (iso: string) => dayFmt.format(new Date(`${iso}T00:00:00Z`))

const sessionFmt = new Intl.DateTimeFormat('en-IN', {
  timeZone: 'Asia/Kolkata',
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

const STATUS_TONE: Record<MyCourse['status'], Tone | null> = {
  ok: 'ok',
  watch: 'warn',
  at_risk: 'bad',
  no_records: null,
}

function StatusBadge({ status }: { status: MyCourse['status'] }) {
  if (status === 'ok') return <Badge variant="ok">On track</Badge>
  if (status === 'watch') return <Badge variant="warn">Watch</Badge>
  if (status === 'at_risk') return <Badge variant="bad">At risk</Badge>
  return <Badge variant="muted">No marks yet</Badge>
}

const MARK: Record<MyCourseSessions['sessions'][number]['status'], { label: string; variant: 'ok' | 'warn' | 'bad' | 'muted' }> = {
  present: { label: 'Present', variant: 'ok' },
  late: { label: 'Late', variant: 'warn' },
  absent: { label: 'Absent', variant: 'bad' },
  excused: { label: 'Excused', variant: 'muted' },
  unmarked: { label: 'Not marked', variant: 'muted' },
  upcoming: { label: 'Upcoming', variant: 'muted' },
}

function MarkBadge({ status }: { status: keyof typeof MARK }) {
  const m = MARK[status]
  return <Badge variant={m.variant}>{m.label}</Badge>
}

/** Room against the rule, in plain words. Neutral on purpose: "to spare", not "you can miss". */
function roomText(c: MyCourse, minimum: number): { text: string; tone: Tone | null } {
  const r = c.room
  switch (r.kind) {
    case 'spare':
      return r.sessions === 0
        ? { text: 'No sessions to spare', tone: 'warn' }
        : { text: `${r.sessions} session${r.sessions === 1 ? '' : 's'} to spare`, tone: null }
    case 'need':
      return { text: `Attend the next ${r.sessions}`, tone: 'warn' }
    case 'cannot_reach':
      return { text: `Can't reach ${minimum}% this term`, tone: 'bad' }
    case 'final':
      return { text: 'No sessions left this term', tone: null }
    default:
      return { text: '–', tone: null }
  }
}

function RoomLeft({ course, minimum }: { course: MyCourse; minimum: number }) {
  const { text, tone } = roomText(course, minimum)
  return (
    <span className={cn('text-sm', tone === 'warn' && 'text-warn', tone === 'bad' && 'text-bad')}>
      {text}
    </span>
  )
}

function CourseMeter({ course, minimum }: { course: MyCourse; minimum: number }) {
  return (
    <Meter
      label={pct(course.attended_percent)}
      hint={`${course.attended} of ${course.counted_sessions}`}
      value={(course.attended_percent ?? 0) / 100}
      tone={STATUS_TONE[course.status]}
      mark={minimum / 100}
    />
  )
}

export function MyAttendancePage() {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['me', 'attendance'],
    queryFn: api.myAttendance,
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Your attendance" description={describe(data)}>
        {data?.term && (
          <span className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs text-muted-foreground">
            <CalendarDays className="size-3.5" />
            {data.term.name} · {day(data.term.starts_on)} to {day(data.term.ends_on)}
          </span>
        )}
      </PageHeader>

      {isPending && <DashboardSkeleton />}
      {isError && <LoadError message={error.message} onRetry={() => refetch()} />}
      {data && <Body data={data} />}
    </div>
  )
}

function describe(data: MyAttendance | undefined): string {
  if (!data) return 'How you are doing in each course this term.'
  if (!data.term) return 'No term is running right now.'
  const n = data.courses.length
  const courses = `${n} course${n === 1 ? '' : 's'}`
  return data.rule_set
    ? `Across your ${courses} this term. The rule is ${data.minimum_percent}% in each course.`
    : `Across your ${courses} this term. No rule is set yet, so ${data.minimum_percent}% is shown as a guide.`
}

function Body({ data }: { data: MyAttendance }) {
  const [open, setOpen] = useState<MyCourse | null>(null)
  const minimum = data.minimum_percent

  if (!data.term || data.courses.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-muted-foreground">
          {data.term
            ? 'You are not enrolled in any courses this term.'
            : 'There is no attendance to show until the next term starts.'}
        </CardContent>
      </Card>
    )
  }

  const below = data.courses.filter((c) => c.status === 'watch' || c.status === 'at_risk')
  const tightest = tightestCourse(data.courses)

  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <StatCard
          label="Overall"
          value={pct(data.overall?.attended_percent)}
          hint={
            data.overall
              ? `${num(data.overall.attended)} of ${num(data.overall.counted_sessions)} sessions, present or late`
              : undefined
          }
        />
        <StatCard
          label={`Below ${minimum}%`}
          value={num(below.length)}
          tone={below.length ? 'bad' : undefined}
          hint={
            below.length
              ? below.map((c) => c.course_code).join(', ')
              : `of ${num(data.courses.length)} courses`
          }
        />
        <div className="col-span-2 lg:col-span-1">
          <StatCard
            label="Needs most attention"
            value={tightest ? tightest.course_code : '–'}
            hint={tightest ? roomText(tightest, minimum).text : 'Every course is settled or not started'}
          />
        </div>
      </div>

      <CoursesCard courses={data.courses} minimum={minimum} onOpen={setOpen} />

      <div className="grid gap-3 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent sessions</CardTitle>
            <CardDescription>Your latest marks. Tell your teacher if one looks wrong.</CardDescription>
          </CardHeader>
          <CardContent>
            {data.recent.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">No sessions marked yet.</p>
            ) : (
              <ul className="grid">
                {data.recent.map((r) => (
                  <li
                    key={`${r.starts_at}-${r.course_code}`}
                    className="flex items-center justify-between gap-3 border-b py-2 last:border-0"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {r.course_code} <span className="font-normal text-muted-foreground">{r.course_title}</span>
                      </div>
                      <div className="text-xs text-muted-foreground tabular-nums">{formatDateTime(r.starts_at)}</div>
                    </div>
                    <MarkBadge status={r.status} />
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Attendance by fortnight</CardTitle>
            <CardDescription>Your share of marked sessions attended, present or late.</CardDescription>
          </CardHeader>
          <CardContent>
            <BarChart
              summary={`Your attendance by fortnight: ${data.fortnights
                .map((f) => `${day(f.starts_on)} ${pct(f.attended_percent)}`)
                .join(', ')}`}
              series={[{ key: 'percent', label: 'Attended', className: 'bg-chart-1' }]}
              data={data.fortnights.map((f) => ({
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
      </div>

      <p className="text-xs text-muted-foreground">
        Rule: {data.how_percent_is_calculated} · Sessions to spare assume no future excused
        sessions · Times in India time
      </p>

      <CourseSheet course={open} minimum={minimum} onClose={() => setOpen(null)} />
    </>
  )
}

/** The course that needs the most attention: one that can no longer reach the rule (lowest
 * attendance first), then the longest run needed, then the fewest sessions to spare. Courses
 * with nothing marked are left out. */
function tightestCourse(courses: MyCourse[]): MyCourse | null {
  const rank = (c: MyCourse): [number, number] => {
    const r = c.room
    const percent = c.attended_percent ?? 100
    if (r.kind === 'cannot_reach') return [0, percent]
    if (r.kind === 'need') return [1, -r.sessions]
    if (r.kind === 'spare') return [2, r.sessions]
    return [3, 0]
  }
  const before = (a: MyCourse, b: MyCourse) => {
    const [ra, rb] = [rank(a), rank(b)]
    return ra[0] !== rb[0] ? ra[0] < rb[0] : ra[1] < rb[1]
  }
  // Finished courses that made the rule need no attention.
  const measured = courses.filter((c) => c.status !== 'no_records' && c.room.kind !== 'final')
  if (!measured.length) return null
  return measured.reduce((best, c) => (before(c, best) ? c : best))
}

function CoursesCard({
  courses,
  minimum,
  onOpen,
}: {
  courses: MyCourse[]
  minimum: number
  onOpen: (c: MyCourse) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Your courses</CardTitle>
        <CardDescription>The tick on each bar marks {minimum}%. Open a course to see every session.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow className="border-0 bg-muted hover:bg-muted [&>th:first-child]:rounded-l-lg [&>th:last-child]:rounded-r-lg">
                <TableHead>Course</TableHead>
                <TableHead>Teacher</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-56">Attendance</TableHead>
                <TableHead>Room left</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Sessions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {courses.map((c) => (
                <TableRow key={c.course_code} className="cursor-pointer" onClick={() => onOpen(c)}>
                  <TableCell className="py-3">
                    <div className="font-semibold">{c.course_code}</div>
                    <div className="text-xs text-muted-foreground">{c.course_title}</div>
                  </TableCell>
                  <TableCell>{c.teacher_name ?? '–'}</TableCell>
                  <TableCell>
                    <StatusBadge status={c.status} />
                  </TableCell>
                  <TableCell>
                    <CourseMeter course={c} minimum={minimum} />
                  </TableCell>
                  <TableCell>
                    <RoomLeft course={c} minimum={minimum} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        onOpen(c)
                      }}
                    >
                      Sessions<span className="sr-only"> for {c.course_code}</span>
                      <ChevronRight />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <ul className="grid gap-3 md:hidden">
          {courses.map((c) => (
            <li key={c.course_code}>
              <button
                type="button"
                onClick={() => onOpen(c)}
                className="grid w-full gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                <span className="flex items-start justify-between gap-2">
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{c.course_code}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {c.course_title}
                      {c.teacher_name && ` · ${c.teacher_name}`}
                    </span>
                  </span>
                  <StatusBadge status={c.status} />
                </span>
                <CourseMeter course={c} minimum={minimum} />
                <span className="flex items-center justify-between">
                  <RoomLeft course={c} minimum={minimum} />
                  <ChevronRight className="size-4 text-muted-foreground" />
                </span>
              </button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

/** Coming up first (soonest first), then what has happened (newest first). */
function SessionList({ sessions }: { sessions: MyCourseSessions['sessions'] }) {
  const upcoming = sessions.filter((s) => s.status === 'upcoming')
  const past = sessions.filter((s) => s.status !== 'upcoming').reverse()
  const groups = [
    { title: 'Coming up', rows: upcoming },
    { title: 'So far', rows: past },
  ].filter((g) => g.rows.length)

  if (!groups.length) {
    return <p className="py-6 text-center text-sm text-muted-foreground">No sessions scheduled.</p>
  }
  return (
    <div className="grid gap-5">
      {groups.map((g) => (
        <section key={g.title} aria-label={g.title}>
          <h3 className="mb-1 text-xs font-medium text-muted-foreground">
            {g.title} · {g.rows.length}
          </h3>
          <ol className="grid">
            {g.rows.map((s) => (
              <li
                key={s.starts_at}
                className="flex items-center justify-between gap-3 border-b py-2 text-sm last:border-0"
              >
                <span className="tabular-nums">{sessionFmt.format(new Date(s.starts_at))}</span>
                <MarkBadge status={s.status} />
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  )
}

function CourseSheet({
  course,
  minimum,
  onClose,
}: {
  course: MyCourse | null
  minimum: number
  onClose: () => void
}) {
  const code = course?.course_code
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['me', 'attendance', code],
    queryFn: () => api.myCourse(code!),
    enabled: !!code,
  })

  return (
    <Sheet open={!!course} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        {course && (
          <>
            <SheetHeader className="border-b">
              <SheetTitle>
                {course.course_code} · {course.course_title}
              </SheetTitle>
              <SheetDescription>
                {course.teacher_name ? `${course.teacher_name} · ` : ''}
                {course.remaining_sessions} session{course.remaining_sessions === 1 ? '' : 's'} still to come
              </SheetDescription>
              <div className="mt-3 grid gap-3">
                <CourseMeter course={course} minimum={minimum} />
                <dl className="grid grid-cols-4 gap-2 text-center text-xs">
                  {(['present', 'late', 'absent', 'excused'] as const).map((s) => (
                    <div key={s} className="rounded-md bg-muted px-2 py-1.5">
                      <dt className="text-muted-foreground">{MARK[s].label}</dt>
                      <dd className="text-sm font-semibold tabular-nums">{num(course[s])}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </SheetHeader>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {isPending && (
                <div className="grid gap-2" aria-busy="true" aria-label="Loading sessions">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-9" />
                  ))}
                </div>
              )}
              {isError && <LoadError message={error.message} onRetry={() => refetch()} />}
              {data && <SessionList sessions={data.sessions} />}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
