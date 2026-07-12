import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

function isBrowser(): boolean {
  return typeof window !== 'undefined'
}

export function safeGetItem(key: string): string | null {
  if (!isBrowser()) return null
  try { return localStorage.getItem(key) } catch { return null }
}

export function safeSetItem(key: string, value: string): void {
  if (!isBrowser()) return
  try { localStorage.setItem(key, value) } catch { return }
}

export function safeRemoveItem(key: string): void {
  if (!isBrowser()) return
  try { localStorage.removeItem(key) } catch { return }
}
