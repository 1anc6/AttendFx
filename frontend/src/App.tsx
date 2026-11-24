import { Navigate, Route, Routes } from 'react-router'
import { AppLayout } from '@/components/app-layout'
import { ComingSoonPage, NotFoundPage } from '@/pages/coming-soon'
import { ConnectPage } from '@/pages/connect'
import { KeysPage } from '@/pages/keys'
import { SignInPage } from '@/pages/sign-in'

export default function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/keys" replace />} />
        <Route path="/keys" element={<KeysPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/account" element={<ComingSoonPage title="Account" />} />
      </Route>
      <Route path="/admin" element={<AppLayout adminOnly />}>
        <Route index element={<Navigate to="/admin/overview" replace />} />
        <Route path="overview" element={<ComingSoonPage title="Overview" />} />
        <Route path="people" element={<ComingSoonPage title="People" />} />
        <Route path="activity" element={<ComingSoonPage title="Activity" />} />
        <Route path="usage" element={<ComingSoonPage title="Usage" />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
