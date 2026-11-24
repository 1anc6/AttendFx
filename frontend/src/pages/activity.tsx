import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { History, Loader2, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  DashboardSkeleton,
  LoadError,
  OutcomeBadge,
  PageHeader,
  Pager,
} from '@/components/dashboard'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { SURFACE_LABEL, actionLabel } from '@/lib/dashboard'
import { api, type ActivityEvent, type ActivityQuery } from '@/lib/api'
import { formatDateTime, timeAgo } from '@/lib/format'

const START: ActivityQuery = { q: '', surface: 'all', outcome: 'all', page: 1 }

function who(e: ActivityEvent) {
  if (e.person) return { name: e.person.name, detail: e.person.email }
  return e.surface === 'cli'
    ? { name: 'Operator', detail: 'Command line' }
    : { name: 'Unknown', detail: 'No such account' }
}

function latency(ms: number | null) {
  if (ms === null) return '–'
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
}

export function ActivityPage() {
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState<ActivityQuery>(START)

  useEffect(() => {
    const t = setTimeout(() => setQuery((q) => (q.q === search ? q : { ...q, q: search, page: 1 })), 250)
    return () => clearTimeout(t)
  }, [search])

  const { data, isPending, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['admin', 'activity', query],
    queryFn: () => api.activity(query),
    placeholderData: keepPreviousData,
  })

  const filter = (patch: Partial<ActivityQuery>) => setQuery((q) => ({ ...q, ...patch, page: 1 }))
  const filtered = query.q !== '' || query.surface !== 'all' || query.outcome !== 'all'

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Activity"
        description={`Who used AttendFX, and how it went. Kept for ${data?.retention_days ?? 90} days. Questions and answers are never stored.`}
      />

      {isPending && <DashboardSkeleton />}
      {isError && <LoadError message={error.message} onRetry={() => refetch()} />}

      {data && (
        <Card>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative min-w-0 flex-1 basis-64">
                <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="search"
                  aria-label="Search by person or action"
                  placeholder="Search by name, email or action"
                  className="pl-8"
                  maxLength={100}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {isFetching && (
                  <Loader2 className="absolute top-1/2 right-2.5 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
                )}
              </div>
              <Select
                value={query.surface}
                onValueChange={(v) => filter({ surface: v as ActivityQuery['surface'] })}
              >
                <SelectTrigger aria-label="Where" className="flex-1 sm:w-40 sm:flex-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Everywhere</SelectItem>
                  <SelectItem value="mcp">Assistant</SelectItem>
                  <SelectItem value="api">Web app</SelectItem>
                  <SelectItem value="cli">Operator</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={query.outcome}
                onValueChange={(v) => filter({ outcome: v as ActivityQuery['outcome'] })}
              >
                <SelectTrigger aria-label="Outcome" className="flex-1 sm:w-40 sm:flex-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any outcome</SelectItem>
                  <SelectItem value="problems">Problems only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {data.events.length === 0 ? (
              <div className="grid justify-items-center gap-3 py-10 text-center">
                <span className="grid size-10 place-items-center rounded-full bg-muted">
                  <History className="size-5 text-muted-foreground" />
                </span>
                <p className="font-medium">{filtered ? 'Nothing matches' : 'No activity yet'}</p>
                {filtered && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSearch('')
                      setQuery(START)
                    }}
                  >
                    Clear search and filters
                  </Button>
                )}
              </div>
            ) : (
              <EventList events={data.events} />
            )}

            <Pager
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              onPage={(page) => setQuery((q) => ({ ...q, page }))}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function EventList({ events }: { events: ActivityEvent[] }) {
  return (
    <>
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow className="border-0 bg-muted hover:bg-muted [&>th:first-child]:rounded-l-lg [&>th:last-child]:rounded-r-lg">
              <TableHead>When</TableHead>
              <TableHead>Person</TableHead>
              <TableHead>What</TableHead>
              <TableHead>Outcome</TableHead>
              <TableHead className="text-right">Took</TableHead>
              <TableHead>Key</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.map((e) => {
              const p = who(e)
              return (
                <TableRow key={e.id}>
                  <TableCell className="whitespace-nowrap" title={formatDateTime(e.ts)}>
                    {timeAgo(e.ts)}
                  </TableCell>
                  <TableCell className="py-3">
                    <div className="font-semibold text-foreground">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.detail}</div>
                  </TableCell>
                  <TableCell>
                    <div>{actionLabel(e.action)}</div>
                    <div className="text-xs text-muted-foreground">{SURFACE_LABEL[e.surface]}</div>
                  </TableCell>
                  <TableCell>
                    <OutcomeBadge status={e.status} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{latency(e.latency_ms)}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {e.key_prefix ?? '–'}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <ul className="grid gap-3 md:hidden">
        {events.map((e) => {
          const p = who(e)
          return (
            <li key={e.id} className="grid gap-2 rounded-lg border p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate font-semibold">{actionLabel(e.action)}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {p.name} · {p.detail}
                  </div>
                </div>
                <OutcomeBadge status={e.status} />
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span title={formatDateTime(e.ts)}>{timeAgo(e.ts)}</span>
                <span>{SURFACE_LABEL[e.surface]}</span>
                <span>{latency(e.latency_ms)}</span>
                {e.key_prefix && <span className="font-mono">{e.key_prefix}</span>}
              </div>
            </li>
          )
        })}
      </ul>
    </>
  )
}
