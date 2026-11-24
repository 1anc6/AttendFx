import { Check, CircleAlert, Eye, EyeOff, Loader2, TriangleAlert } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Role } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { useChangePassword, useSession } from '@/lib/session'
import { cn } from '@/lib/utils'

const MIN = 12
const ROLE: Record<Role, string> = { student: 'Student', teacher: 'Teacher', admin: 'Admin' }

export function AccountPage() {
  const { data: me } = useSession()
  if (!me) return null
  const forced = me.must_change_password

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Account</h1>
        <p className="text-muted-foreground">Your details and your password.</p>
      </header>

      {forced && (
        <Alert className="border-warn-bar/50">
          <TriangleAlert className="text-warn" />
          <AlertTitle>Choose your own password</AlertTitle>
          <AlertDescription>
            You signed in with a temporary password from an admin. Replace it to start using
            AttendFX.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">You</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-3 text-sm">
              <Row label="Name">{me.user.name}</Row>
              <Row label="Email">
                <span className="break-all">{me.user.email}</span>
              </Row>
              <Row label="Role">
                <Badge variant="muted">{ROLE[me.user.role]}</Badge>
              </Row>
              <Row label="Signed in until">{formatDateTime(me.expires_at)}</Row>
            </dl>
            <p className="mt-4 text-xs text-muted-foreground">
              To change your name or email, ask an admin.
            </p>
          </CardContent>
        </Card>

        <PasswordCard forced={forced} email={me.user.email} />
      </div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[8rem_minmax(0,1fr)] items-baseline gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  )
}

function PasswordCard({ forced, email }: { forced: boolean; email: string }) {
  const change = useChangePassword()
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)

  const longEnough = next.length >= MIN
  const matches = next.length > 0 && next === confirm
  const ready = current.length > 0 && longEnough && matches

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!ready) return
    change.mutate(
      { current, next },
      {
        onSuccess: () => {
          setCurrent('')
          setNext('')
          setConfirm('')
          if (forced) {
            toast.success('Password set. You can use AttendFX now.')
            navigate('/keys', { replace: true })
          } else {
            toast.success('Password changed. Your other devices were signed out.')
          }
        },
        onError: () => setCurrent(''),
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{forced ? 'Set your password' : 'Change password'}</CardTitle>
        <CardDescription>
          Use at least {MIN} characters. A few unrelated words are easy to remember and hard to
          guess.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4">
          {/* Lets password managers save the new password against the right account. */}
          <input type="email" autoComplete="username" value={email} readOnly hidden />
          {change.isError && (
            <Alert variant="destructive" role="alert">
              <CircleAlert />
              <AlertDescription>{change.error.message}</AlertDescription>
            </Alert>
          )}
          <PasswordField
            label={forced ? 'Temporary password' : 'Current password'}
            autoComplete="current-password"
            value={current}
            onChange={setCurrent}
            show={show}
            autoFocus
          />
          <PasswordField
            label="New password"
            autoComplete="new-password"
            value={next}
            onChange={setNext}
            show={show}
          />
          <PasswordField
            label="Type it again"
            autoComplete="new-password"
            value={confirm}
            onChange={setConfirm}
            show={show}
          />
          <ul className="grid gap-1 text-xs" aria-live="polite">
            <Requirement ok={longEnough}>
              {MIN}+ characters{next.length > 0 && !longEnough ? ` (${next.length} so far)` : ''}
            </Requirement>
            <Requirement ok={matches}>Both new passwords match</Requirement>
          </ul>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShow((s) => !s)}
              aria-pressed={show}
            >
              {show ? <EyeOff /> : <Eye />}
              {show ? 'Hide passwords' : 'Show passwords'}
            </Button>
            <Button type="submit" disabled={!ready || change.isPending}>
              {change.isPending && <Loader2 className="animate-spin" />}
              {forced ? 'Set password' : 'Change password'}
            </Button>
          </div>
          {!forced && (
            <p className="text-xs text-muted-foreground">
              Changing it signs you out everywhere else. Your access keys keep working.
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}

function PasswordField({
  label,
  value,
  onChange,
  show,
  autoComplete,
  autoFocus,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  show: boolean
  autoComplete: string
  autoFocus?: boolean
}) {
  const id = useId()
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={show ? 'text' : 'password'}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        spellCheck={false}
        maxLength={128}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

function Requirement({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <li className={cn('flex items-center gap-1.5', ok ? 'text-ok' : 'text-muted-foreground')}>
      <Check className={cn('size-3.5', !ok && 'opacity-40')} aria-hidden="true" />
      <span>
        {children}
        <span className="sr-only">{ok ? ' (done)' : ' (not yet)'}</span>
      </span>
    </li>
  )
}
