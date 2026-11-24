import { Navigate, Route, Routes } from 'react-router'
import { AppLayout } from '@/components/app-layout'
import { AccountPage } from '@/pages/account'
import { NotFoundPage } from '@/pages/coming-soon'
import { ActivityPage } from '@/pages/activity'
import { ConnectPage } from '@/pages/connect'
import { KeysPage } from '@/pages/keys'
import { OverviewPage } from '@/pages/overview'
import { PeoplePage } from '@/pages/people'
import { SignInPage } from '@/pages/sign-in'
import { UsagePage } from '@/pages/usage'

export default function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/keys" replace />} />
        <Route path="/keys" element={<KeysPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/account" element={<AccountPage />} />
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
