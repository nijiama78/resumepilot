import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, clearToken, getToken, setToken } from '../api'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(getToken())
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(email: string, password: string): Promise<void> {
    const res = await api.login(email, password)
    token.value = res.access_token
    setToken(res.access_token)
    await fetchMe()
  }

  async function register(email: string, password: string): Promise<void> {
    await api.register(email, password)
    await login(email, password)
  }

  async function fetchMe(): Promise<void> {
    if (!token.value) return
    try {
      user.value = await api.me()
    } catch {
      logout()
    }
  }

  function logout(): void {
    token.value = ''
    user.value = null
    clearToken()
  }

  return { token, user, isLoggedIn, login, register, fetchMe, logout }
})
