import { Navigate, Route, Routes } from 'react-router'
import { AppLayout } from '@/components/app-layout'
import { homeFor } from '@/lib/home'
import { useSession } from '@/lib/session'
import { AccountPage } from '@/pages/account'
import { MyAttendancePage } from '@/pages/my-attendance'
import { NotFoundPage } from '@/pages/coming-soon'
import { ActivityPage } from '@/pages/activity'
import { ConnectPage } from '@/pages/connect'
import { KeysPage } from '@/pages/keys'
import { OverviewPage } from '@/pages/overview'
import { PeoplePage } from '@/pages/people'
import { SignInPage } from '@/pages/sign-in'
import { UsagePage } from '@/pages/usage'

/** "/" sends each person to their own start page. AppLayout has already checked the session. */
function HomeRedirect() {
  const { data: me } = useSession()
  return <Navigate to={me ? homeFor(me.user.role) : '/keys'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route element={<AppLayout />}>
        <Route index element={<HomeRedirect />} />
        <Route path="/keys" element={<KeysPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/account" element={<AccountPage />} />
      </Route>
      <Route element={<AppLayout studentOnly />}>
        <Route path="/me" element={<MyAttendancePage />} />
      </Route>
      <Route path="/admin" element={<AppLayout adminOnly />}>
        <Route index element={<Navigate to="/admin/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="people" element={<PeoplePage />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="usage" element={<UsagePage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
