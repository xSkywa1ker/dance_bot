import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import axios from 'axios'
import { apiClient } from '../api/client'

type AdminUser = {
  id: number
  email: string
  role: string
}

type AuthContextValue = {
  user: AdminUser | null
  token: string | null
  initializing: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  clearError: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const readStoredToken = () =>
  (typeof window !== 'undefined' ? window.localStorage.getItem('admin_token') : null)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(readStoredToken)
  const [user, setUser] = useState<AdminUser | null>(null)
  const [initializing, setInitializing] = useState(() => Boolean(readStoredToken()))
  const [error, setError] = useState<string | null>(null)

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('admin_token')
    }
    delete apiClient.defaults.headers.common.Authorization
    setToken(null)
    setUser(null)
  }, [])

  const clearError = useCallback(() => setError(null), [])

  const login = useCallback(
    async (email: string, password: string) => {
      clearError()
      const formData = new URLSearchParams()
      formData.set('username', email.trim())
      formData.set('password', password)
      try {
        const { data } = await apiClient.post('/auth/login', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })
        if (typeof window !== 'undefined') {
          window.localStorage.setItem('admin_token', data.access_token)
        }
        apiClient.defaults.headers.common.Authorization = `Bearer ${data.access_token}`
        setToken(data.access_token)
        setUser(data.user)
      } catch (loginError) {
        if (axios.isAxiosError(loginError)) {
          if (loginError.response?.status === 400) {
            setError('Неверный email или пароль. Проверьте данные и попробуйте снова.')
          } else {
            setError('Не удалось выполнить вход. Попробуйте ещё раз позже.')
          }
        } else {
          setError('Произошла непредвиденная ошибка. Повторите попытку позже.')
        }
        throw loginError
      }
    },
    [clearError]
  )

  useEffect(() => {
    let isMounted = true
    const verify = async () => {
      if (!token) {
        if (isMounted) {
          setInitializing(false)
        }
        return
      }
      if (isMounted) {
        setInitializing(true)
      }
      apiClient.defaults.headers.common.Authorization = `Bearer ${token}`
      try {
        const { data } = await apiClient.get<AdminUser>('/auth/me')
        if (isMounted) {
          setUser(data)
        }
      } catch (verifyError) {
        if (isMounted) {
          setError('Сессия истекла. Пожалуйста, войдите снова.')
          logout()
        }
      } finally {
        if (isMounted) {
          setInitializing(false)
        }
      }
    }

    verify()

    return () => {
      isMounted = false
    }
  }, [token, logout])

  useEffect(() => {
    const interceptor = apiClient.interceptors.response.use(
      (response) => response,
      (responseError) => {
        if (responseError.response?.status === 401) {
          setError('Сессия истекла. Пожалуйста, войдите снова.')
          logout()
        }
        return Promise.reject(responseError)
      }
    )

    return () => {
      apiClient.interceptors.response.eject(interceptor)
    }
  }, [logout])

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, initializing, error, login, logout, clearError }),
    [user, token, initializing, error, login, logout, clearError]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

