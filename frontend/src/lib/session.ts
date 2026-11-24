import { QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, rememberCsrf, type Me } from '@/lib/api'

export const ME = ['me'] as const

/** Any 401 from the API means the session is gone: forget it, the guard sends you to sign in. */
export function createQueryClient() {
  const client: QueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
        refetchOnWindowFocus: true,
      },
    },
  })
  const onError = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401) {
      rememberCsrf(null)
      client.setQueryData(ME, null)
    }
  }
  client.getQueryCache().config.onError = onError
  client.getMutationCache().config.onError = onError
  return client
}

/** The signed-in person, or null when signed out. */
export function useSession() {
  return useQuery({
    queryKey: ME,
    queryFn: async (): Promise<Me | null> => {
      try {
        const me = await api.me()
        rememberCsrf(me.csrf_token)
        return me
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          rememberCsrf(null)
          return null
        }
        throw e
      }
    },
    staleTime: 60_000,
  })
}

export function useSignIn() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.signIn(email, password),
    onSuccess: (me) => {
      rememberCsrf(me.csrf_token)
      qc.setQueryData(ME, me)
    },
  })
}

/** Change your own password. The server ends your other sessions and returns a fresh `me`. */
export function useChangePassword() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ current, next }: { current: string; next: string }) =>
      api.changePassword(current, next),
    onSuccess: (me) => {
      rememberCsrf(me.csrf_token)
      qc.setQueryData(ME, me)
    },
  })
}

export function useSignOut() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.signOut(),
    onSettled: () => {
      rememberCsrf(null)
      // Null the session in place so the layout guard sees it and goes to sign-in; clear()
      // would drop the query the guard is watching and leave the page up.
      qc.setQueryData(ME, null)
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== ME[0] })
    },
  })
}
