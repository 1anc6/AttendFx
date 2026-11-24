import { Navigate, Outlet, useLocation } from 'react-router'
import { AppSidebar } from '@/components/app-sidebar'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import { useSession } from '@/lib/session'

const TITLES: Record<string, string> = {
  '/connect': 'Connect assistant',
  '/keys': 'Your access keys',
  '/account': 'Account',
  '/admin/overview': 'Overview',
  '/admin/people': 'People',
  '/admin/activity': 'Activity',
  '/admin/usage': 'Usage',
}

/** Signed-in shell. Sends signed-out visitors to /sign-in and brings them back afterwards. */
export function AppLayout({ adminOnly = false }: { adminOnly?: boolean }) {
  const { data: me, isPending, isError, refetch } = useSession()
  const location = useLocation()

  if (isPending) {
    return (
      <div className="flex min-h-svh gap-2 bg-sidebar p-2">
        <Skeleton className="hidden w-60 md:block" />
        <Skeleton className="flex-1 rounded-xl" />
      </div>
    )
  }
  if (isError) {
    return (
      <div className="grid min-h-svh place-items-center p-6 text-center">
        <div>
          <p className="font-medium">AttendFX could not load.</p>
          <button className="mt-2 text-sm underline" onClick={() => refetch()}>
            Try again
          </button>
        </div>
      </div>
    )
  }
  if (!me) {
    const next = encodeURIComponent(location.pathname)
    return <Navigate to={`/sign-in?next=${next}`} replace />
  }
  // A temporary password unlocks nothing but choosing a real one.
  if (me.must_change_password && location.pathname !== '/account') {
    return <Navigate to="/account" replace />
  }
  if (adminOnly && me.user.role !== 'admin') return <Navigate to="/keys" replace />

  return (
    <SidebarProvider>
      <AppSidebar user={me.user} />
      <SidebarInset>
        <header className="flex h-12 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
          <span className="text-sm text-muted-foreground">
            {TITLES[location.pathname] ?? 'AttendFX'}
          </span>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
