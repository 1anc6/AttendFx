import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  Check,
  CircleAlert,
  Copy,
  KeyRound,
  Loader2,
  Plus,
  TriangleAlert,
} from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { Meter, Segments } from '@/components/meter'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { api, type AccessKey, type IssuedKey, type KeyList } from '@/lib/api'
import { daysUntil, expiryTone, formatDate, timeAgo } from '@/lib/format'

const KEYS = ['keys'] as const
const EXPIRY_CHOICES = [7, 30, 90, 180, 365]

export function KeysPage() {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: KEYS,
    queryFn: api.keys,
  })
  const [issued, setIssued] = useState<IssuedKey | null>(null)
  const [creating, setCreating] = useState(false)
  const [revoking, setRevoking] = useState<AccessKey | null>(null)

  const atLimit = data ? data.active >= data.max_active : false

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your access keys</h1>
          <p className="text-muted-foreground">
            Each key lets one assistant read what you can see. Nothing more.
          </p>
        </div>
        <Button onClick={() => setCreating(true)} disabled={!data || atLimit}>
          <Plus />
          New key
        </Button>
      </header>

      {isPending && <KeysSkeleton />}

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
          <Stats data={data} />
          {issued && <OneTimeKey issued={issued} onDone={() => setIssued(null)} />}
          {atLimit && (
            <Alert>
              <TriangleAlert />
              <AlertDescription>
                You have {data.max_active} active keys, the most allowed. Revoke one you no
                longer use to make a new one.
              </AlertDescription>
            </Alert>
          )}
          {data.keys.length === 0 && !issued ? (
            <EmptyState onCreate={() => setCreating(true)} />
          ) : (
            <KeysCard keys={data.keys} onRevoke={setRevoking} />
          )}
        </>
      )}

      {data && (
        <NewKeyDialog
          open={creating}
          onOpenChange={setCreating}
          maxDays={data.max_days}
          onCreated={(k) => {
            setIssued(k)
            setCreating(false)
          }}
        />
      )}
      <RevokeDialog
        target={revoking}
        onClose={() => setRevoking(null)}
        onRevoked={(k) => {
          if (issued?.id === k.id) setIssued(null)
        }}
      />
    </div>
  )
}

function Stats({ data }: { data: KeyList }) {
  const active = data.keys.filter((k) => k.status === 'active')
  const soonest = active
    .filter((k) => k.expires_at)
    .sort((a, b) => a.expires_at!.localeCompare(b.expires_at!))[0]
  const lastUsed = data.keys
    .filter((k) => k.last_used_at)
    .sort((a, b) => b.last_used_at!.localeCompare(a.last_used_at!))[0]
  const days = soonest?.expires_at ? daysUntil(soonest.expires_at) : null
  const tone = days === null ? null : expiryTone(days)

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <StatCard label="Active keys" className="col-span-2 sm:col-span-1">
        <div className="text-2xl font-semibold tracking-tight">
          {data.active} <span className="text-sm font-medium text-muted-foreground">/ {data.max_active}</span>
        </div>
        <div className="mt-3">
          <Segments used={data.active} total={data.max_active} />
        </div>
      </StatCard>
      <StatCard label="Next expiry">
        {soonest?.expires_at ? (
          <>
            <div className="text-2xl font-semibold tracking-tight">{formatDate(soonest.expires_at)}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {soonest.name} ·{' '}
              <span className={tone === 'ok' ? '' : tone === 'warn' ? 'text-warn' : 'text-bad'}>
                {days === 1 ? '1 day left' : `${days} days left`}
              </span>
            </p>
          </>
        ) : (
          <div className="text-2xl font-semibold tracking-tight text-muted-foreground">None</div>
        )}
      </StatCard>
      <StatCard label="Last used">
        {lastUsed?.last_used_at ? (
          <>
            <div className="text-2xl font-semibold tracking-tight">{timeAgo(lastUsed.last_used_at)}</div>
            <p className="mt-1 text-xs text-muted-foreground">by {lastUsed.name}</p>
          </>
        ) : (
          <>
            <div className="text-2xl font-semibold tracking-tight text-muted-foreground">Never</div>
            <p className="mt-1 text-xs text-muted-foreground">No assistant has used a key yet</p>
          </>
        )}
      </StatCard>
    </div>
  )
}

function StatCard({
  label,
  children,
  className,
}: {
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <Card size="sm" className={className}>
      <CardContent>
        <p className="mb-1.5 text-sm text-muted-foreground">{label}</p>
        {children}
      </CardContent>
    </Card>
  )
}

function OneTimeKey({ issued, onDone }: { issued: IssuedKey; onDone: () => void }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(issued.key)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Could not copy. Select the key and copy it by hand.')
    }
  }

  return (
    <Card className="ring-warn-bar/50" role="status">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          New key · <span className="text-foreground">{issued.name}</span>
        </CardTitle>
        <CardAction>
          <Link
            to="/connect"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            Connect your assistant <ArrowRight className="size-3.5" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="grid gap-3">
        <p className="flex items-center gap-2 text-sm">
          <TriangleAlert className="size-4 text-warn" />
          <span>
            <strong className="font-semibold">Copy it now.</strong> You won't see this key again.
          </span>
        </p>
        <div className="flex flex-wrap gap-2">
          <code className="min-w-0 flex-1 basis-80 rounded-lg border bg-muted px-3 py-2 font-mono text-[13px] break-all">
            {issued.key}
          </code>
          <Button variant="outline" onClick={copy} aria-live="polite">
            {copied ? <Check /> : <Copy />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>
            Expires {formatDate(issued.expires_at)}. Treat it like a password.
          </span>
          <Button variant="ghost" size="sm" onClick={onDone}>
            I've saved it
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function statusBadge(k: AccessKey) {
  if (k.status === 'active') return <Badge variant="ok">Active</Badge>
  if (k.status === 'expired') return <Badge variant="warn">Expired</Badge>
  return <Badge variant="muted">Revoked</Badge>
}

function ExpiryCell({ k }: { k: AccessKey }) {
  if (k.status === 'revoked' && k.revoked_at)
    return <span className="text-muted-foreground">Revoked {formatDate(k.revoked_at)}</span>
  if (!k.expires_at) return <span className="text-muted-foreground">Never</span>
  if (k.status === 'expired')
    return <span className="text-muted-foreground">Expired {formatDate(k.expires_at)}</span>
  const left = daysUntil(k.expires_at)
  const total = Math.max(1, daysUntil(k.expires_at, new Date(k.created_at).getTime()))
  return (
    <Meter
      label={formatDate(k.expires_at)}
      hint={`${left}d left`}
      value={left / total}
      tone={expiryTone(left)}
    />
  )
}

function KeysCard({ keys, onRevoke }: { keys: AccessKey[]; onRevoke: (k: AccessKey) => void }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">Keys</CardTitle>
        <CardDescription className="sr-only">Your access keys and when they expire</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Table on wider screens */}
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow className="border-0 bg-muted hover:bg-muted [&>th:first-child]:rounded-l-lg [&>th:last-child]:rounded-r-lg">
                <TableHead>Key</TableHead>
                <TableHead>Prefix</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last used</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((k) => (
                <TableRow key={k.id} className={k.status === 'active' ? '' : 'text-muted-foreground'}>
                  <TableCell className="py-3">
                    <div className="font-semibold text-foreground">{k.name}</div>
                    <div className="text-xs text-muted-foreground">Created {formatDate(k.created_at)}</div>
                  </TableCell>
                  <TableCell className="font-mono text-[13px]">afx_{k.prefix}</TableCell>
                  <TableCell>{statusBadge(k)}</TableCell>
                  <TableCell>{k.last_used_at ? timeAgo(k.last_used_at) : 'Never'}</TableCell>
                  <TableCell>
                    <ExpiryCell k={k} />
                  </TableCell>
                  <TableCell className="text-right">
                    {k.status === 'active' && (
                      <Button variant="secondary" size="sm" onClick={() => onRevoke(k)}>
                        Revoke<span className="sr-only"> {k.name}</span>
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Cards on phones */}
        <ul className="grid gap-3 md:hidden">
          {keys.map((k) => (
            <li key={k.id} className="grid gap-3 rounded-lg border p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-semibold">{k.name}</div>
                  <div className="font-mono text-xs text-muted-foreground">afx_{k.prefix}</div>
                </div>
                {statusBadge(k)}
              </div>
              <div className="grid gap-1 text-xs text-muted-foreground">
                <span>Last used {k.last_used_at ? timeAgo(k.last_used_at) : 'never'}</span>
                <ExpiryCell k={k} />
              </div>
              {k.status === 'active' && (
                <Button variant="secondary" size="sm" className="justify-self-start" onClick={() => onRevoke(k)}>
                  Revoke<span className="sr-only"> {k.name}</span>
                </Button>
              )}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-muted-foreground">
          Keys expire after at most a year · Times in India time
        </p>
      </CardContent>
    </Card>
  )
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card>
      <CardContent className="grid justify-items-center gap-3 py-10 text-center">
        <span className="grid size-10 place-items-center rounded-full bg-muted">
          <KeyRound className="size-5 text-muted-foreground" />
        </span>
        <div>
          <p className="font-medium">No keys yet</p>
          <p className="mx-auto max-w-sm text-sm text-muted-foreground">
            Make a key, then paste it into your assistant. It can read only what you can see
            in AttendFX.
          </p>
        </div>
        <Button onClick={onCreate}>
          <Plus />
          New key
        </Button>
      </CardContent>
    </Card>
  )
}

function NewKeyDialog({
  open,
  onOpenChange,
  maxDays,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  maxDays: number
  onCreated: (k: IssuedKey) => void
}) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [days, setDays] = useState('90')
  const create = useMutation({
    mutationFn: () => api.createKey(name.trim(), Number(days)),
    onSuccess: (k) => {
      qc.invalidateQueries({ queryKey: KEYS })
      setName('')
      setDays('90')
      onCreated(k)
    },
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) create.reset()
        onOpenChange(o)
      }}
    >
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>New access key</DialogTitle>
            <DialogDescription>
              Name it after the device or app that will use it, so you know which to revoke.
            </DialogDescription>
          </DialogHeader>
          {create.isError && (
            <Alert variant="destructive" role="alert">
              <CircleAlert />
              <AlertDescription>{create.error.message}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-2">
            <Label htmlFor="key-name">Name</Label>
            <Input
              id="key-name"
              placeholder="laptop, phone, Claude Desktop…"
              maxLength={60}
              required
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="key-days">Expires after</Label>
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger id="key-days" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EXPIRY_CHOICES.filter((d) => d <= maxDays).map((d) => (
                  <SelectItem key={d} value={String(d)}>
                    {d === 365 ? '1 year' : `${d} days`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={create.isPending || !name.trim()}>
              {create.isPending && <Loader2 className="animate-spin" />}
              Create key
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function RevokeDialog({
  target,
  onClose,
  onRevoked,
}: {
  target: AccessKey | null
  onClose: () => void
  onRevoked: (k: AccessKey) => void
}) {
  const qc = useQueryClient()
  const revoke = useMutation({
    mutationFn: (k: AccessKey) => api.revokeKey(k.id),
    onSuccess: (_, k) => {
      qc.invalidateQueries({ queryKey: KEYS })
      toast.success(`Revoked ${k.name}`)
      onRevoked(k)
      onClose()
    },
  })

  return (
    <Dialog
      open={target !== null}
      onOpenChange={(o) => {
        if (!o) {
          revoke.reset()
          onClose()
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Revoke {target?.name}?</DialogTitle>
          <DialogDescription>
            Any assistant using <span className="font-mono">afx_{target?.prefix}</span> stops
            working on its next request. You can't undo this, but you can make a new key.
          </DialogDescription>
        </DialogHeader>
        {revoke.isError && (
          <Alert variant="destructive" role="alert">
            <CircleAlert />
            <AlertDescription>{revoke.error.message}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            disabled={revoke.isPending}
            onClick={() => target && revoke.mutate(target)}
          >
            {revoke.isPending && <Loader2 className="animate-spin" />}
            Revoke key
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function KeysSkeleton() {
  return (
    <div className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}
