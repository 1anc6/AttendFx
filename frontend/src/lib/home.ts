import type { Role } from '@/lib/api'

/** Where each role lands after signing in: students see their attendance, everyone else
 * starts at their access keys. */
export function homeFor(role: Role): string {
  return role === 'student' ? '/me' : '/keys'
}
