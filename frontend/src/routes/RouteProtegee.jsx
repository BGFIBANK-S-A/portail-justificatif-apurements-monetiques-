import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function RouteProtegee({ children, roles }) {
  const { utilisateur, chargement } = useAuth()

  if (chargement) return null
  if (!utilisateur) return <Navigate to="/login" replace />
  if (roles && !roles.includes(utilisateur.role)) {
    return <Navigate to={utilisateur.role === 'client' ? '/dashboard' : '/admin/dashboard'} replace />
  }
  return children
}
