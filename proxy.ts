import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import crypto from 'crypto'

const PROTECTED_ROUTES = ['/dashboard', '/research', '/settings']
const AUTH_ROUTES = ['/auth/login', '/auth/signup']

interface JwtPayload {
  sub?: string
  exp?: number
  type?: string
}

function decodeBase64Url(str: string): Buffer {
  const base64 = str.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
  return Buffer.from(padded, 'base64')
}

function decodeBase64UrlToString(str: string): string {
  return decodeBase64Url(str).toString('utf8')
}

function decodeJWTPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const raw = decodeBase64UrlToString(parts[1])
    if (!raw) return null
    return JSON.parse(raw) as JwtPayload
  } catch {
    return null
  }
}

function isTokenExpired(payload: JwtPayload): boolean {
  if (!payload.exp) return true
  const now = Math.floor(Date.now() / 1000)
  return payload.exp < now
}

function verifySignature(token: string, secret: string): boolean {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return false

    const headerPayload = parts[0] + '.' + parts[1]
    const signatureBuffer = decodeBase64Url(parts[2])

    const expectedBuffer = crypto
      .createHmac('sha256', secret)
      .update(headerPayload, 'utf8')
      .digest()

    if (signatureBuffer.length !== expectedBuffer.length) return false
    return crypto.timingSafeEqual(signatureBuffer, expectedBuffer)
  } catch {
    return false
  }
}

let _warnedMissingSecret = false

function isValidToken(token: string | undefined): boolean {
  if (!token) return false

  const secret = process.env.JWT_SECRET
  if (!secret) {
    if (!_warnedMissingSecret) {
      _warnedMissingSecret = true
      console.error(
        '[proxy.ts] FATAL: JWT_SECRET environment variable is not set. ' +
        'All protected routes will redirect to login. ' +
        'Set JWT_SECRET to match backend SECRET_KEY for authentication to work.'
      )
    }
    return false
  }

  if (!verifySignature(token, secret)) return false

  const payload = decodeJWTPayload(token)
  if (!payload) return false
  if (!payload.sub) return false
  if (isTokenExpired(payload)) return false

  return true
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get('auth_token')?.value
  const isAuthenticated = isValidToken(token)

  const isProtected = PROTECTED_ROUTES.some((route) => pathname.startsWith(route))
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route))

  if (isProtected && !isAuthenticated) {
    const loginUrl = new URL('/auth/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  if (isAuthRoute && isAuthenticated) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/research/:path*', '/settings/:path*', '/auth/login', '/auth/signup'],
}
