import { CircleAlert, Eye, EyeOff, Loader2, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { LogoMark } from '@/components/logo'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { homeFor } from '@/lib/home'
import { useSession, useSignIn } from '@/lib/session'

/** Only same-site paths, so ?next= cannot bounce people to another site. Null means "go to
 * the person's own start page", which depends on who signs in. */
function safeNext(raw: string | null): string | null {
  return raw && raw.startsWith('/') && !raw.startsWith('//') ? raw : null
}

/** Loose on purpose: the server decides. This only catches typos like a missing "@". */
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

type FieldErrors = { email?: string; password?: string }

export function SignInPage() {
  const { data: me } = useSession()
  const signIn = useSignIn()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [capsLock, setCapsLock] = useState(false)
  const [errors, setErrors] = useState<FieldErrors>({})
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    document.title = 'Sign in · AttendFX'
  }, [])

  if (me) return <Navigate to={next ?? homeFor(me.user.role)} replace />

  function submit(e: FormEvent) {
    e.preventDefault()
    const found: FieldErrors = {}
    const trimmed = email.trim()
    if (!trimmed) found.email = 'Enter your email.'
    else if (!EMAIL.test(trimmed)) found.email = 'That email looks incomplete. Check it and try again.'
    if (!password) found.password = 'Enter your password.'
    setErrors(found)
    if (found.email) return emailRef.current?.focus()
    if (found.password) return passwordRef.current?.focus()

    signIn.mutate(
      { email: trimmed, password },
      {
        onSuccess: (signedIn) => navigate(next ?? homeFor(signedIn.user.role), { replace: true }),
        // Keep the email, clear the password and put the cursor back where the retry starts.
        onError: () => {
          setPassword('')
          requestAnimationFrame(() => passwordRef.current?.focus())
        },
      },
    )
  }

  function editEmail(value: string) {
    setEmail(value)
    if (errors.email) setErrors((e) => ({ ...e, email: undefined }))
    if (signIn.isError) signIn.reset()
  }

  function editPassword(value: string) {
    setPassword(value)
    if (errors.password) setErrors((e) => ({ ...e, password: undefined }))
    if (signIn.isError) signIn.reset()
  }

  function watchCapsLock(e: KeyboardEvent<HTMLInputElement>) {
    setCapsLock(e.getModifierState('CapsLock'))
  }

  return (
    <div className="grid min-h-svh place-items-center bg-sidebar p-4">
      <main className="w-full max-w-[400px]">
        <div className="mb-8 grid justify-items-center gap-2 text-center">
          <div className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <LogoMark />
            AttendFX
          </div>
          <p className="text-sm text-balance text-muted-foreground">
            Your courses and attendance, for you and your AI assistant.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              <h1>Sign in</h1>
            </CardTitle>
            <CardDescription>Use the account your college set up for you.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="grid gap-4" noValidate>
              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  ref={emailRef}
                  id="email"
                  type="email"
                  inputMode="email"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  autoFocus
                  placeholder="you@college.edu"
                  className="h-10 dark:bg-input/50"
                  value={email}
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  onChange={(e) => editEmail(e.target.value)}
                />
                {errors.email && (
                  <p id="email-error" className="text-xs text-destructive">
                    {errors.email}
                  </p>
                )}
              </div>

              <div className="grid gap-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    ref={passwordRef}
                    id="password"
                    type={show ? 'text' : 'password'}
                    autoComplete="current-password"
                    className="h-10 pr-10 dark:bg-input/50"
                    value={password}
                    aria-invalid={!!errors.password}
                    aria-describedby={
                      [errors.password && 'password-error', capsLock && 'caps-lock']
                        .filter(Boolean)
                        .join(' ') || undefined
                    }
                    onChange={(e) => editPassword(e.target.value)}
                    onKeyDown={watchCapsLock}
                    onKeyUp={watchCapsLock}
                    onBlur={() => setCapsLock(false)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    className="absolute top-1/2 right-1.5 -translate-y-1/2 text-muted-foreground"
                    aria-label={show ? 'Hide password' : 'Show password'}
                    aria-pressed={show}
                    onClick={() => setShow((s) => !s)}
                  >
                    {show ? <EyeOff /> : <Eye />}
                  </Button>
                </div>
                {errors.password && (
                  <p id="password-error" className="text-xs text-destructive">
                    {errors.password}
                  </p>
                )}
                {capsLock && (
                  <p id="caps-lock" className="flex items-center gap-1.5 text-xs text-warn">
                    <TriangleAlert className="size-3.5" />
                    Caps Lock is on.
                  </p>
                )}
              </div>

              {/* Under the fields, so a failed attempt never moves what you are typing in. */}
              {signIn.isError && (
                <Alert variant="destructive" role="alert">
                  <CircleAlert />
                  <AlertDescription>{signIn.error.message}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" size="lg" className="h-10" disabled={signIn.isPending}>
                {signIn.isPending && <Loader2 className="animate-spin" />}
                {signIn.isPending ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Forgot your password? Ask your college admin to reset it.
        </p>
      </main>
    </div>
  )
}
