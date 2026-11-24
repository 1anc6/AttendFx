import { useSyncExternalStore } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'afx-theme'
const listeners = new Set<() => void>()

function current(): Theme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

export function setTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    /* private window: the choice lasts for this page only */
  }
  listeners.forEach((l) => l())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** The active theme. public/theme-init.js sets it before first paint. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, current, () => 'light')
}
