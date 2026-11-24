import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Download,
  FileUp,
  Loader2,
  LockOpen,
  MoreHorizontal,
  Power,
  RotateCcw,
  Search,
  TriangleAlert,
  UserPlus,
  Users,
} from 'lucide-react'
import { useEffect, useId, useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { CopyField } from '@/components/copy-field'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import {
  api,
  type ImportResult,
  type IssuedPerson,
  type PeopleCounts,
  type PeopleQuery,
  type Person,
  type PersonStatus,
  type Role,
} from '@/lib/api'
import { formatDate, timeAgo } from '@/lib/format'
import { useSession } from '@/lib/session'
import { cn } from '@/lib/utils'

const PEOPLE = ['people'] as const
const ROLE: Record<Role, string> = { student: 'Student', teacher: 'Teacher', admin: 'Admin' }
const STATUS_LABEL: Record<PersonStatus, string> = {
  all: 'Any status',
  active: 'Active',
  locked: 'Locked out',
  must_change: 'Temporary password',
  disabled: 'Turned off',
}

/** Which dialog is up. A new `n` per opening remounts it fresh, so nothing has to be reset
 * while it fades out (which would flash the empty form). */
type DialogState =
  | { kind: 'add' | 'import'; n: number }
  | { kind: 'reset' | 'disable'; person: Person; n: number }

export function PeoplePage() {
  const { data: me } = useSession()
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState<PeopleQuery>({ q: '', role: 'all', status: 'all', page: 1 })
  const [dialog, setDialog] = useState<DialogState | null>(null)
  const [open, setOpen] = useState(false)

  function show(next: { kind: 'add' | 'import' } | { kind: 'reset' | 'disable'; person: Person }) {
    setDialog((d) => ({ ...next, n: (d?.n ?? 0) + 1 }))
    setOpen(true)
  }

  // Search as you type, without a request per keystroke.
  useEffect(() => {
    const t = setTimeout(() => setQuery((q) => (q.q === search ? q : { ...q, q: search, page: 1 })), 250)
    return () => clearTimeout(t)
  }, [search])

  const { data, isPending, isError, error, refetch, isFetching } = useQuery({
    queryKey: [...PEOPLE, query],
    queryFn: () => api.people(query),
    placeholderData: keepPreviousData,
  })

  const filter = (patch: Partial<PeopleQuery>) => setQuery((q) => ({ ...q, ...patch, page: 1 }))

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">People</h1>
          <p className="text-muted-foreground">Everyone who can sign in to AttendFX.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => show({ kind: 'import' })}>
            <FileUp />
            Import CSV
          </Button>
          <Button onClick={() => show({ kind: 'add' })}>
            <UserPlus />
            Add person
          </Button>
        </div>
      </header>

      {isPending && <PeopleSkeleton />}

      {isError && (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertDescription>
            {error.message}{' '}
            <button className="underline" onClick={() => refetch()}>
              Try again
            </button>
          </AlertDescription>
        </Alert>
      )}

      {data && (
        <>
          <Stats counts={data.counts} status={query.status} onPick={(status) => filter({ status })} />
          <Card>
            <CardContent className="grid gap-4">
              <Toolbar
                search={search}
                onSearch={setSearch}
                query={query}
                onFilter={filter}
                busy={isFetching}
              />
              {data.people.length === 0 ? (
                <NoMatches
                  filtered={query.q !== '' || query.role !== 'all' || query.status !== 'all'}
                  onClear={() => {
                    setSearch('')
                    setQuery({ q: '', role: 'all', status: 'all', page: 1 })
                  }}
                />
              ) : (
                <PeopleList
                  people={data.people}
                  selfId={me?.user.id}
                  onReset={(person) => show({ kind: 'reset', person })}
                  onDisable={(person) => show({ kind: 'disable', person })}
                />
              )}
              <Pager
                page={data.page}
                pageSize={data.page_size}
                total={data.total}
                onPage={(page) => setQuery((q) => ({ ...q, page }))}
              />
            </CardContent>
          </Card>
        </>
      )}

      {dialog?.kind === 'add' && (
        <AddPersonDialog key={dialog.n} open={open} onOpenChange={setOpen} />
      )}
      {dialog?.kind === 'import' && (
        <ImportDialog key={dialog.n} open={open} onOpenChange={setOpen} />
      )}
      {dialog?.kind === 'reset' && (
        <ResetDialog key={dialog.n} open={open} onOpenChange={setOpen} person={dialog.person} />
      )}
      {dialog?.kind === 'disable' && (
        <DisableDialog key={dialog.n} open={open} onOpenChange={setOpen} person={dialog.person} />
      )}
    </div>
  )
}

/* ---------- Summary ---------- */

function Stats({
  counts,
  status,
  onPick,
}: {
  counts: PeopleCounts
  status: PersonStatus
  onPick: (s: PersonStatus) => void
}) {
  const tiles: { status: PersonStatus; label: string; value: number; hint: string; tone?: string }[] = [
    {
      status: 'all',
      label: 'Everyone',
      value: counts.total,
      hint: `${counts.student} students · ${counts.teacher} teachers · ${counts.admin} admin${counts.admin === 1 ? '' : 's'}`,
    },
    {
      status: 'locked',
      label: 'Locked out',
      value: counts.locked,
      hint: 'Too many wrong passwords',
      tone: counts.locked ? 'text-bad' : undefined,
    },
    {
      status: 'must_change',
      label: 'Temporary password',
      value: counts.must_change,
      hint: 'Not signed in to set their own yet',
      tone: counts.must_change ? 'text-warn' : undefined,
    },
    { status: 'disabled', label: 'Turned off', value: counts.disabled, hint: 'Cannot sign in or use keys' },
  ]
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((t) => {
        const active = status === t.status
        return (
          <button
            key={t.status}
            type="button"
            aria-pressed={active}
            onClick={() => onPick(active && t.status !== 'all' ? 'all' : t.status)}
            className={cn(
              'rounded-xl bg-card p-4 text-left ring-1 ring-foreground/10 transition-colors hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
              active && 'ring-foreground/40',
            )}
          >
            <p className="mb-1.5 text-sm text-muted-foreground">{t.label}</p>
            <div className={cn('text-2xl font-semibold tracking-tight', t.tone)}>{t.value}</div>
            <p className="mt-1 text-xs text-pretty text-muted-foreground">{t.hint}</p>
          </button>
        )
      })}
    </div>
  )
}

/* ---------- Search and filters ---------- */

function Toolbar({
  search,
  onSearch,
  query,
  onFilter,
  busy,
}: {
  search: string
  onSearch: (s: string) => void
  query: PeopleQuery
  onFilter: (patch: Partial<PeopleQuery>) => void
  busy: boolean
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative min-w-0 flex-1 basis-64">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          aria-label="Search by name or email"
          placeholder="Search by name or email"
          className="pl-8"
          maxLength={100}
          value={search}
          onChange={(e) => onSearch(e.target.value)}
        />
        {busy && (
          <Loader2 className="absolute top-1/2 right-2.5 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
        )}
      </div>
      <Select value={query.role} onValueChange={(role) => onFilter({ role: role as PeopleQuery['role'] })}>
        <SelectTrigger aria-label="Role" className="flex-1 sm:w-36 sm:flex-none">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Any role</SelectItem>
          <SelectItem value="student">Students</SelectItem>
          <SelectItem value="teacher">Teachers</SelectItem>
          <SelectItem value="admin">Admins</SelectItem>
        </SelectContent>
      </Select>
      <Select value={query.status} onValueChange={(status) => onFilter({ status: status as PersonStatus })}>
        <SelectTrigger aria-label="Status" className="flex-1 sm:w-48 sm:flex-none">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(Object.keys(STATUS_LABEL) as PersonStatus[]).map((s) => (
            <SelectItem key={s} value={s}>
              {STATUS_LABEL[s]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

/* ---------- The list ---------- */

function isLocked(p: Person) {
  return p.locked_until !== null && new Date(p.locked_until).getTime() > Date.now()
}

function StatusBadge({ p }: { p: Person }) {
  if (p.disabled_at) return <Badge variant="muted">Turned off</Badge>
  if (isLocked(p)) return <Badge variant="bad">Locked out</Badge>
  if (p.must_change_password) return <Badge variant="warn">Temporary password</Badge>
  return <Badge variant="ok">Active</Badge>
}

function RowActions({
  p,
  onReset,
  onDisable,
}: {
  p: Person
  onReset: (p: Person) => void
  onDisable: (p: Person) => void
}) {
  const qc = useQueryClient()
  const unlock = useMutation({
    mutationFn: () => api.unlockPerson(p.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PEOPLE })
      toast.success(`${p.name} can sign in again`)
    },
    onError: (e) => toast.error(e.message),
  })
  const enable = useMutation({
    mutationFn: () => api.setDisabled(p.id, false),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PEOPLE })
      toast.success(`Turned ${p.name}'s account back on`)
    },
    onError: (e) => toast.error(e.message),
  })

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Actions for ${p.name}`}>
          <MoreHorizontal />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {p.disabled_at ? (
          <DropdownMenuItem onSelect={() => enable.mutate()}>
            <Power />
            Turn account on
          </DropdownMenuItem>
        ) : (
          <>
            {isLocked(p) && (
              <DropdownMenuItem onSelect={() => unlock.mutate()}>
                <LockOpen />
                Unlock now
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onSelect={() => onReset(p)}>
              <RotateCcw />
              Reset password…
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={() => onDisable(p)}>
              <Power />
              Turn account off…
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function lastSeen(p: Person) {
  return p.last_sign_in_at ? timeAgo(p.last_sign_in_at) : 'Never'
}

function PeopleList({
  people,
  selfId,
  onReset,
  onDisable,
}: {
  people: Person[]
  selfId?: string
  onReset: (p: Person) => void
  onDisable: (p: Person) => void
}) {
  const actions = (p: Person) =>
    p.id === selfId ? (
      <span className="text-xs text-muted-foreground">You</span>
    ) : (
      <RowActions p={p} onReset={onReset} onDisable={onDisable} />
    )

  return (
    <>
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow className="border-0 bg-muted hover:bg-muted [&>th:first-child]:rounded-l-lg [&>th:last-child]:rounded-r-lg">
              <TableHead>Person</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last sign-in</TableHead>
              <TableHead className="text-right">Active keys</TableHead>
              <TableHead className="w-12 text-right">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {people.map((p) => (
              <TableRow key={p.id} className={p.disabled_at ? 'text-muted-foreground' : ''}>
                <TableCell className="py-3">
                  <div className={cn('font-semibold', !p.disabled_at && 'text-foreground')}>{p.name}</div>
                  <div className="text-xs text-muted-foreground">{p.email}</div>
                </TableCell>
                <TableCell>{ROLE[p.role]}</TableCell>
                <TableCell>
                  <StatusBadge p={p} />
                </TableCell>
                <TableCell title={p.last_sign_in_at ? formatDate(p.last_sign_in_at) : undefined}>
                  {lastSeen(p)}
                </TableCell>
                <TableCell className="text-right tabular-nums">{p.active_keys}</TableCell>
                <TableCell className="text-right">{actions(p)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ul className="grid gap-3 md:hidden">
        {people.map((p) => (
          <li key={p.id} className="grid gap-2 rounded-lg border p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate font-semibold">{p.name}</div>
                <div className="truncate text-xs text-muted-foreground">{p.email}</div>
              </div>
              {actions(p)}
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <StatusBadge p={p} />
              <span>{ROLE[p.role]}</span>
              <span>Signed in {lastSeen(p).toLowerCase()}</span>
              <span>
                {p.active_keys} key{p.active_keys === 1 ? '' : 's'}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}

function Pager({
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
        {from}–{to} of {total}
      </span>
      {pages > 1 && (
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            <ChevronLeft />
            Previous
          </Button>
          <span className="px-2">
            Page {page} of {pages}
          </span>
          <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            Next
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  )
}

function NoMatches({ filtered, onClear }: { filtered: boolean; onClear: () => void }) {
  return (
    <div className="grid justify-items-center gap-3 py-10 text-center">
      <span className="grid size-10 place-items-center rounded-full bg-muted">
        <Users className="size-5 text-muted-foreground" />
      </span>
      <p className="font-medium">{filtered ? 'Nobody matches' : 'No people yet'}</p>
      {filtered && (
        <Button variant="outline" size="sm" onClick={onClear}>
          Clear search and filters
        </Button>
      )}
    </div>
  )
}

/* ---------- Temporary passwords ---------- */

function HandOver({ name, password }: { name: string; password: string }) {
  return (
    <div className="grid gap-3 rounded-lg border border-warn-bar/50 p-3" role="status">
      <p className="flex items-start gap-2 text-sm">
        <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warn" />
        <span>
          <strong className="font-semibold">Copy it now.</strong> Give it to {name} privately. They
          choose their own password when they sign in, and you won't see this one again.
        </span>
      </p>
      <CopyField value={password} label={`Temporary password for ${name}`} />
    </div>
  )
}

/** Excel and Sheets run cells that start with = + - @ as formulas; quote and defuse them. */
function csvCell(value: string) {
  const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value
  return `"${safe.replace(/"/g, '""')}"`
}

function downloadAccounts(people: IssuedPerson[]) {
  const lines = [
    'name,email,role,temporary_password',
    ...people.map((p) => [p.name, p.email, p.role, p.temporary_password].map(csvCell).join(',')),
  ]
  const blob = new Blob([lines.join('\r\n') + '\r\n'], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `attendfx-new-accounts-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/* ---------- Add one person ---------- */

function AddPersonDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const qc = useQueryClient()
  const id = useId()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<Role>('student')
  const create = useMutation({
    mutationFn: () => api.createPerson(name.trim(), email.trim(), role),
    onSuccess: () => qc.invalidateQueries({ queryKey: PEOPLE }),
  })
  const close = () => onOpenChange(false)

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate()
  }

  const made = create.data

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        {made ? (
          <div className="grid gap-4">
            <DialogHeader>
              <DialogTitle>Account ready for {made.name}</DialogTitle>
              <DialogDescription>
                {made.email} · {ROLE[made.role]}
              </DialogDescription>
            </DialogHeader>
            <HandOver name={made.name} password={made.temporary_password} />
            <DialogFooter>
              <Button onClick={close}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={submit} className="grid gap-4">
            <DialogHeader>
              <DialogTitle>Add a person</DialogTitle>
              <DialogDescription>
                They get a temporary password to sign in with, then choose their own.
              </DialogDescription>
            </DialogHeader>
            {create.isError && (
              <Alert variant="destructive" role="alert">
                <CircleAlert />
                <AlertDescription>{create.error.message}</AlertDescription>
              </Alert>
            )}
            <div className="grid gap-2">
              <Label htmlFor={`${id}-name`}>Full name</Label>
              <Input
                id={`${id}-name`}
                required
                autoFocus
                maxLength={100}
                autoComplete="off"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor={`${id}-email`}>Email</Label>
              <Input
                id={`${id}-email`}
                type="email"
                required
                maxLength={254}
                autoComplete="off"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor={`${id}-role`}>Role</Label>
              <Select value={role} onValueChange={(r) => setRole(r as Role)}>
                <SelectTrigger id={`${id}-role`} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="student">Student</SelectItem>
                  <SelectItem value="teacher">Teacher</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
              {role === 'admin' && (
                <p className="text-xs text-warn">Admins can see everyone's attendance and manage accounts.</p>
              )}
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              </DialogClose>
              <Button type="submit" disabled={create.isPending || !name.trim() || !email.trim()}>
                {create.isPending && <Loader2 className="animate-spin" />}
                Create account
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}

/* ---------- Import a CSV ---------- */

const SAMPLE = 'name,email,role\nAsha Rao,asha.rao@college.edu,student\nDev Iyer,dev.iyer@college.edu,teacher'

function ImportDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const qc = useQueryClient()
  const id = useId()
  const [text, setText] = useState('')
  const [fileName, setFileName] = useState<string | null>(null)
  const [check, setCheck] = useState<ImportResult | null>(null)

  const run = useMutation({
    mutationFn: (dryRun: boolean) => api.importPeople(text, dryRun),
    onSuccess: (result) => {
      setCheck(result)
      if (result.created) qc.invalidateQueries({ queryKey: PEOPLE })
    },
  })

  async function pickFile(file: File | undefined) {
    if (!file) return
    if (file.size > 200_000) {
      toast.error('That file is too big. Import at most 200 people at a time.')
      return
    }
    setFileName(file.name)
    setText(await file.text())
    setCheck(null)
    run.reset()
  }

  const done = check?.created ? check : null
  const checked = check && !check.created ? check : null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        {done ? (
          <div className="grid gap-4">
            <DialogHeader>
              <DialogTitle>
                Created {done.people.length} account{done.people.length === 1 ? '' : 's'}
              </DialogTitle>
              <DialogDescription>
                Download the temporary passwords now and hand each one over privately. You
                won't see them again.
              </DialogDescription>
            </DialogHeader>
            <div className="max-h-72 overflow-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Person</TableHead>
                    <TableHead>Temporary password</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {done.people.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell>
                        <div className="font-medium">{p.name}</div>
                        <div className="text-xs text-muted-foreground">{p.email}</div>
                      </TableCell>
                      <TableCell className="font-mono text-[13px]">{p.temporary_password}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => downloadAccounts(done.people)}>
                <Download />
                Download CSV
              </Button>
              <Button onClick={() => onOpenChange(false)}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="grid min-w-0 gap-4">
            <DialogHeader>
              <DialogTitle>Import people from a CSV</DialogTitle>
              <DialogDescription>
                The first line names the columns: name, email and role (student, teacher or
                admin). Other columns are ignored. Up to 200 people at a time.
              </DialogDescription>
            </DialogHeader>

            {run.isError && (
              <Alert variant="destructive" role="alert">
                <CircleAlert />
                <AlertDescription>{run.error.message}</AlertDescription>
              </Alert>
            )}

            {!checked && (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    id={`${id}-file`}
                    type="file"
                    accept=".csv,text/csv"
                    className="sr-only"
                    onChange={(e) => pickFile(e.target.files?.[0])}
                  />
                  <Button variant="outline" asChild>
                    <label htmlFor={`${id}-file`} className="cursor-pointer">
                      <FileUp />
                      Choose file
                    </label>
                  </Button>
                  <span className="min-w-0 truncate text-sm text-muted-foreground">
                    {fileName ?? 'or paste below'}
                  </span>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor={`${id}-text`}>CSV</Label>
                  <Textarea
                    id={`${id}-text`}
                    className="h-40 font-mono text-[13px]"
                    placeholder={SAMPLE}
                    spellCheck={false}
                    value={text}
                    onChange={(e) => {
                      setText(e.target.value)
                      setFileName(null)
                    }}
                  />
                </div>
              </>
            )}

            {checked && <ImportCheck result={checked} />}

            <DialogFooter>
              {checked ? (
                <>
                  <Button variant="outline" onClick={() => setCheck(null)}>
                    Back
                  </Button>
                  <Button
                    disabled={checked.errors.length > 0 || checked.rows.length === 0 || run.isPending}
                    onClick={() => run.mutate(false)}
                  >
                    {run.isPending && <Loader2 className="animate-spin" />}
                    Create {checked.rows.length} account{checked.rows.length === 1 ? '' : 's'}
                  </Button>
                </>
              ) : (
                <>
                  <DialogClose asChild>
                    <Button variant="outline">Cancel</Button>
                  </DialogClose>
                  <Button disabled={!text.trim() || run.isPending} onClick={() => run.mutate(true)}>
                    {run.isPending && <Loader2 className="animate-spin" />}
                    Check file
                  </Button>
                </>
              )}
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function ImportCheck({ result }: { result: ImportResult }) {
  const { rows, errors } = result
  return (
    <div className="grid min-w-0 gap-3">
      {errors.length > 0 ? (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertDescription>
            Fix {errors.length === 1 ? 'this line' : `these ${errors.length} lines`} and check
            again. Nobody is created until the whole file is clean.
          </AlertDescription>
        </Alert>
      ) : (
        <p className="text-sm">
          Ready to create <strong className="font-semibold">{rows.length}</strong> account
          {rows.length === 1 ? '' : 's'}. Each gets a temporary password.
        </p>
      )}
      {errors.length > 0 && (
        <ul className="max-h-40 overflow-auto rounded-lg border text-sm">
          {errors.map((e) => (
            <li key={`${e.line}-${e.message}`} className="flex gap-3 border-b px-3 py-2 last:border-0">
              <span className="w-14 shrink-0 text-muted-foreground tabular-nums">Line {e.line}</span>
              <span>{e.message}</span>
            </li>
          ))}
        </ul>
      )}
      {rows.length > 0 && (
        <div className="max-h-56 overflow-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">Line</TableHead>
                <TableHead>Person</TableHead>
                <TableHead>Role</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.line}>
                  <TableCell className="text-muted-foreground tabular-nums">{r.line}</TableCell>
                  <TableCell>
                    <div className="font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground">{r.email}</div>
                  </TableCell>
                  <TableCell>{ROLE[r.role]}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

/* ---------- Reset and turn off ---------- */

interface PersonDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  person: Person
}

function ResetDialog({ open, onOpenChange, person }: PersonDialogProps) {
  const qc = useQueryClient()
  const reset = useMutation({
    mutationFn: () => api.resetPassword(person.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: PEOPLE }),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {reset.data ? `New password for ${person.name}` : `Reset ${person.name}'s password?`}
          </DialogTitle>
          <DialogDescription>
            {reset.data
              ? 'Their old password no longer works.'
              : 'They are signed out of the web app and get a temporary password. This also clears a lockout. Their access keys keep working.'}
          </DialogDescription>
        </DialogHeader>
        {reset.isError && (
          <Alert variant="destructive" role="alert">
            <CircleAlert />
            <AlertDescription>{reset.error.message}</AlertDescription>
          </Alert>
        )}
        {reset.data && <HandOver name={person.name} password={reset.data.temporary_password} />}
        <DialogFooter>
          {reset.data ? (
            <Button onClick={() => onOpenChange(false)}>Done</Button>
          ) : (
            <>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button disabled={reset.isPending} onClick={() => reset.mutate()}>
                {reset.isPending && <Loader2 className="animate-spin" />}
                Reset password
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DisableDialog({ open, onOpenChange, person }: PersonDialogProps) {
  const qc = useQueryClient()
  const disable = useMutation({
    mutationFn: () => api.setDisabled(person.id, true),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PEOPLE })
      toast.success(`Turned off ${person.name}'s account`)
      onOpenChange(false)
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Turn off {person.name}'s account?</DialogTitle>
          <DialogDescription>
            They are signed out now, can't sign in, and{' '}
            {person.active_keys > 0
              ? `their ${person.active_keys} access key${person.active_keys === 1 ? '' : 's'} stop working`
              : 'any access keys stop working'}
            . Nothing is deleted: turn it back on any time.
          </DialogDescription>
        </DialogHeader>
        {disable.isError && (
          <Alert variant="destructive" role="alert">
            <CircleAlert />
            <AlertDescription>{disable.error.message}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            disabled={disable.isPending}
            onClick={() => disable.mutate()}
          >
            {disable.isPending && <Loader2 className="animate-spin" />}
            Turn off
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PeopleSkeleton() {
  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-96 rounded-xl" />
    </div>
  )
}
