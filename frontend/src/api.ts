const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

const TOKEN_KEY = 'resumepilot_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const isForm = options.body instanceof FormData
  if (!isForm && options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (resp.status === 204) return undefined as T

  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    const detail = (data as { detail?: string }).detail ?? `请求失败（${resp.status}）`
    throw new Error(detail)
  }
  return data as T
}

export const api = {
  register: (email: string, password: string) =>
    request<{ id: number; email: string; created_at: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) => {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    return request<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      body: form.toString(),
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },

  me: () => request<{ id: number; email: string; created_at: string }>('/api/auth/me'),

  uploadResume: (file: File) => {
    const form = new FormData()
    form.set('file', file)
    return request<{ id: number; filename: string; content_text: string; created_at: string }>(
      '/api/resumes/upload',
      { method: 'POST', body: form },
    )
  },

  analyze: (resumeId: number, jobDescription: string) =>
    request<import('./types').Analysis>('/api/analyze', {
      method: 'POST',
      body: JSON.stringify({ resume_id: resumeId, job_description: jobDescription }),
    }),

  analyses: () => request<import('./types').Analysis[]>('/api/analyses'),

  analysis: (id: number) => request<import('./types').Analysis>(`/api/analyses/${id}`),
}

/** SSE 流式对话：读取 /api/chat 事件流，逐 token 回调 */
export async function chatStream(
  resumeId: number,
  question: string,
  onToken: (token: string) => void,
): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ resume_id: resumeId, question }),
  })
  if (!resp.ok || !resp.body) {
    const data = await resp.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? `请求失败（${resp.status}）`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const event of events) {
      const line = event.trim()
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      if (payload === '[DONE]') return
      try {
        const token = (JSON.parse(payload) as { token?: string }).token
        if (token) onToken(token)
      } catch {
        // 忽略不完整的 JSON 帧
      }
    }
  }
}
