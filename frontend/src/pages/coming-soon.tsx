import { Hammer } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function ComingSoonPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <Card>
        <CardContent className="grid justify-items-center gap-2 py-12 text-center">
          <span className="grid size-10 place-items-center rounded-full bg-muted">
            <Hammer className="size-5 text-muted-foreground" />
          </span>
          <p className="font-medium">Not built yet</p>
          <p className="text-sm text-muted-foreground">This page is coming in a later update.</p>
        </CardContent>
      </Card>
    </div>
  )
}

export function NotFoundPage() {
  return (
    <div className="grid min-h-svh place-items-center p-6 text-center">
      <div>
        <p className="text-sm text-muted-foreground">404</p>
        <h1 className="text-xl font-semibold">Page not found</h1>
        <a href="/" className="mt-2 inline-block text-sm underline">
          Go to your start page
        </a>
      </div>
    </div>
  )
}
