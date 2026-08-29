import { useEffect, useState } from 'react'
import { getCurrentUser, loginUser, logoutUser, registerUser } from '../services/authService'
import { AuthContext } from './authContext'
const TOKEN_KEY = 'kisan_direct_access_token'

function readToken() {
  return window.localStorage.getItem(TOKEN_KEY)
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(readToken)
  const [user, setUser] = useState(null)
  const [isCheckingSession, setIsCheckingSession] = useState(Boolean(token))

  useEffect(() => {
    if (!token) return

    getCurrentUser(token)
      .then(setUser)
      .catch(() => {
        window.localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
      })
      .finally(() => setIsCheckingSession(false))
  }, [token])

  async function signIn(credentials) {
    const result = await loginUser(credentials)
    window.localStorage.setItem(TOKEN_KEY, result.access_token)
    setToken(result.access_token)
    setUser(await getCurrentUser(result.access_token))
  }

  async function signUp(details) {
    const result = await registerUser(details)
    window.localStorage.setItem(TOKEN_KEY, result.access_token)
    setToken(result.access_token)
    setUser(result.user)
  }

  async function signOut() {
    if (token) {
      try {
        await logoutUser(token)
      } finally {
        window.localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
      }
    }
  }

  return (
    <AuthContext.Provider value={{ token, user, isCheckingSession, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

