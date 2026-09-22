import { createContext, useContext, useEffect, useState } from 'react'
import api, { tokens } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [utilisateur, setUtilisateur] = useState(null)
  const [chargement, setChargement] = useState(true)

  useEffect(() => {
    if (!tokens.access) {
      setChargement(false)
      return
    }
    api.get('/auth/moi/')
      .then((res) => setUtilisateur(res.data))
      .catch(() => tokens.clear())
      .finally(() => setChargement(false))
  }, [])

  async function connecter(email, mot_de_passe) {
    const res = await api.post('/auth/login/', { email, mot_de_passe })
    tokens.set(res.data.access, res.data.refresh)
    setUtilisateur(res.data.utilisateur)
    return res.data.utilisateur
  }

  async function deconnecter() {
    tokens.clear()
    setUtilisateur(null)
  }

  return (
    <AuthContext.Provider value={{ utilisateur, chargement, connecter, deconnecter, setUtilisateur }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
