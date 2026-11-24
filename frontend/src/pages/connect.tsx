import { Check, Copy, KeyRound } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

function CopyBlock({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Could not copy. Select the text and copy it by hand.')
    }
  }
  return (
    <div className="relative">
      <pre className="overflow-x-auto rounded-lg border bg-muted p-3 pr-12 font-mono text-[13px] leading-relaxed">
        {text}
      </pre>
      <Button
        variant="ghost"
        size="icon-sm"
        className="absolute top-2 right-2"
        onClick={copy}
        aria-label={copied ? 'Copied' : `Copy ${label}`}
      >
        {copied ? <Check /> : <Copy />}
      </Button>
    </div>
  )
}

export function ConnectPage() {
  const url = `${window.location.origin}/mcp`
  const claudeCode = `claude mcp add --transport http attendfx ${url} \\\n  --header "Authorization: Bearer YOUR_KEY"`
  const generic = JSON.stringify(
    { mcpServers: { attendfx: { url, headers: { Authorization: 'Bearer YOUR_KEY' } } } },
    null,
    2,
  )
  const desktop = JSON.stringify(
    {
      mcpServers: {
        attendfx: {
          command: 'npx',
          args: ['-y', 'mcp-remote', url, '--header', 'Authorization:${AFX_AUTH}'],
          env: { AFX_AUTH: 'Bearer YOUR_KEY' },
        },
      },
    },
    null,
    2,
  )

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Connect your assistant</h1>
        <p className="text-muted-foreground">
          Add AttendFX as an MCP server, using one of your access keys. Replace YOUR_KEY with it.
        </p>
      </header>

      <Card size="sm">
        <CardContent className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">Server address</p>
            <p className="truncate font-mono text-sm">{url}</p>
          </div>
          <Button variant="outline" asChild>
            <Link to="/keys">
              <KeyRound />
              Get a key
            </Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Claude Code</CardTitle>
          <CardDescription>Run this once in a terminal.</CardDescription>
        </CardHeader>
        <CardContent>
          <CopyBlock label="Claude Code command" text={claudeCode} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Claude Desktop</CardTitle>
          <CardDescription>
            Add this to claude_desktop_config.json, then restart Claude. Needs Node.js.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CopyBlock label="Claude Desktop config" text={desktop} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Other MCP clients</CardTitle>
          <CardDescription>
            Any client that supports Streamable HTTP with custom headers, such as Cursor or VS
            Code.
          </CardDescription>
          <CardAction />
        </CardHeader>
        <CardContent>
          <CopyBlock label="MCP config" text={generic} />
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">
        Then ask something like “What is my attendance in each course?” Your assistant sees
        only what you can see in AttendFX.
      </p>
    </div>
  )
}
