import {
  Activity,
  BarChart3,
  CalendarCheck,
  ChevronsUpDown,
  KeyRound,
  LayoutGrid,
  LogOut,
  Moon,
  Plug,
  Sun,
  UserRound,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { NavLink, useLocation } from 'react-router'
import { LogoMark } from '@/components/logo'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import type { User } from '@/lib/api'
import { homeFor } from '@/lib/home'
import { useSignOut } from '@/lib/session'
import { setTheme, useTheme } from '@/lib/theme'

interface Item {
  to: string
  label: string
  icon: LucideIcon
}

const YOU: Item[] = [
  { to: '/connect', label: 'Connect assistant', icon: Plug },
  { to: '/keys', label: 'Your access keys', icon: KeyRound },
  { to: '/account', label: 'Account', icon: UserRound },
]

const STUDENT_ONLY: Item[] = [{ to: '/me', label: 'Your attendance', icon: CalendarCheck }]

const ADMIN: Item[] = [
  { to: '/admin/overview', label: 'Overview', icon: LayoutGrid },
  { to: '/admin/people', label: 'People', icon: Users },
  { to: '/admin/activity', label: 'Activity', icon: Activity },
  { to: '/admin/usage', label: 'Usage', icon: BarChart3 },
]

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('')
}

const ROLE: Record<User['role'], string> = { student: 'Student', teacher: 'Teacher', admin: 'Admin' }

function NavGroup({ label, items }: { label: string; items: Item[] }) {
  const { pathname } = useLocation()
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{label}</SidebarGroupLabel>
      <SidebarMenu>
        {items.map(({ to, label: text, icon: Icon }) => (
          <SidebarMenuItem key={to}>
            <SidebarMenuButton asChild isActive={pathname === to} tooltip={text}>
              <NavLink to={to}>
                <Icon />
                <span>{text}</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  )
}

export function AppSidebar({ user }: { user: User }) {
  const theme = useTheme()
  const signOut = useSignOut()
  const next = theme === 'dark' ? 'light' : 'dark'

  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <NavLink to={homeFor(user.role)}>
                <LogoMark className="size-6!" />
                <span className="text-[15px] font-semibold tracking-tight">AttendFX</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <NavGroup label="You" items={user.role === 'student' ? [...STUDENT_ONLY, ...YOU] : YOU} />
        {user.role === 'admin' && <NavGroup label="Admin" items={ADMIN} />}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={() => setTheme(next)} tooltip={`Switch to ${next} mode`}>
              {theme === 'dark' ? <Sun /> : <Moon />}
              <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" tooltip={user.name}>
                  <span
                    aria-hidden="true"
                    className="grid size-8 shrink-0 place-items-center rounded-full bg-sidebar-accent text-xs font-semibold"
                  >
                    {initials(user.name)}
                  </span>
                  <span className="grid min-w-0 flex-1 text-left leading-tight">
                    <span className="truncate font-medium">{user.name}</span>
                    <span className="truncate text-xs text-muted-foreground">{ROLE[user.role]}</span>
                  </span>
                  <ChevronsUpDown className="ml-auto text-muted-foreground" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-60">
                <DropdownMenuLabel className="font-normal">
                  <div className="font-medium">{user.name}</div>
                  <div className="truncate text-xs text-muted-foreground">{user.email}</div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => signOut.mutate()}>
                  <LogOut />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
