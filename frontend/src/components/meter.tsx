import type { Tone } from '@/lib/format'
import { cn } from '@/lib/utils'

const BAR: Record<Tone, string> = { ok: 'bg-ok-bar', warn: 'bg-warn-bar', bad: 'bg-bad-bar' }

/** Thin labelled progress bar, as in the reference's "Idle" column. */
export function Meter({
  label,
  hint,
  value,
  tone,
  mark,
  className,
}: {
  label: string
  hint?: string
  value: number // 0..1
  /** No tone draws the track only, for "nothing to measure yet". */
  tone: Tone | null
  /** A tick on the track, such as the attendance rule (0..1). */
  mark?: number
  className?: string
}) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100)
  return (
    <div className={cn('min-w-36', className)}>
      <div className="mb-1.5 flex items-baseline justify-between gap-3 text-xs">
        <span className="font-medium text-foreground">{label}</span>
        {hint && <span className="text-muted-foreground">{hint}</span>}
      </div>
      <div className="relative" aria-hidden="true">
        <div className="h-[3px] overflow-hidden rounded-full bg-track">
          {tone && (
            <div className={cn('h-full rounded-full', BAR[tone])} style={{ width: `${pct}%` }} />
          )}
        </div>
        {mark !== undefined && (
          <i
            className="absolute top-1/2 block h-2.5 w-px -translate-y-1/2 bg-foreground/50"
            style={{ left: `${Math.min(1, Math.max(0, mark)) * 100}%` }}
          />
        )}
      </div>
    </div>
  )
}

/** Row of small segments, filled up to `used` (e.g. 2 of 10 keys). */
export function Segments({ used, total }: { used: number; total: number }) {
  return (
    <div className="flex gap-[3px]" aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          className={cn('h-[5px] flex-1 rounded-[2px]', i < used ? 'bg-foreground' : 'bg-track')}
        />
      ))}
    </div>
  )
}
