import { Check, Copy } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'

/** A secret shown once, in mono, with a Copy button. */
export function CopyField({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Could not copy. Select it and copy it by hand.')
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      <code
        aria-label={label}
        className="min-w-0 flex-1 basis-48 rounded-lg border bg-muted px-3 py-2 font-mono text-[13px] break-all"
      >
        {value}
      </code>
      <Button type="button" variant="outline" onClick={copy} aria-live="polite">
        {copied ? <Check /> : <Copy />}
        {copied ? 'Copied' : 'Copy'}
      </Button>
    </div>
  )
}
