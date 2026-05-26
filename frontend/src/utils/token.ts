const TOKEN_KEY = 'datanexus_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function isTokenExpired(): boolean {
  const token = getToken()
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const exp = payload.exp
    if (!exp) return true
    // 提前 60 秒判定过期，避免边界情况
    return Date.now() / 1000 > exp - 60
  } catch {
    return true
  }
}
