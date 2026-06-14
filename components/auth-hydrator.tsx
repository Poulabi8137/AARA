'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/store'

const TOKEN_KEY = 'authToken'

export function AuthHydrator() {
  const hydrate = useAuthStore((state) => state.hydrate)
  const logout = useAuthStore((state) => state.logout)

  useEffect(() => {
    hydrate()
  }, [hydrate])

  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === TOKEN_KEY) {
        if (e.newValue === null) {
          logout()
        } else {
          hydrate()
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [hydrate, logout])

  return null
}
