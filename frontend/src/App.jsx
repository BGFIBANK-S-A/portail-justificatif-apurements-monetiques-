import { Navigate, Route, Routes } from 'react-router-dom'
import Login from './pages/Login'
import Activer from './pages/Activer'
import MotDePasseOublie from './pages/MotDePasseOublie'
import Reinitialiser from './pages/Reinitialiser'
import RenvoyerActivation from './pages/RenvoyerActivation'
import Dashboard from './pages/client/Dashboard'
import DetailDossier from './pages/client/DetailDossier'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminDetailDossier from './pages/admin/AdminDetailDossier'
import AdminImport from './pages/admin/AdminImport'
import AdminArchive from './pages/admin/AdminArchive'
import AdminUtilisateurs from './pages/admin/AdminUtilisateurs'
import AdminSuspendus from './pages/admin/AdminSuspendus'
import Journal from './pages/admin/Journal'
import GestionCrc from './pages/admin/GestionCrc'
import RouteProtegee from './routes/RouteProtegee'
import { RESSOURCES_STAFF } from './routes/navConfig'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/activer/:token" element={<Activer />} />
      <Route path="/mot-de-passe-oublie" element={<MotDePasseOublie />} />
      <Route path="/reinitialiser/:token" element={<Reinitialiser />} />
      <Route path="/renvoyer-activation" element={<RenvoyerActivation />} />

      <Route path="/dashboard" element={<RouteProtegee roles={['client']}><Dashboard /></RouteProtegee>} />
      <Route path="/dossier/:id" element={<RouteProtegee roles={['client']}><DetailDossier /></RouteProtegee>} />

      <Route path="/admin/dashboard" element={<RouteProtegee roles={RESSOURCES_STAFF}><AdminDashboard /></RouteProtegee>} />
      <Route path="/admin/dossier/:id" element={<RouteProtegee roles={RESSOURCES_STAFF}><AdminDetailDossier /></RouteProtegee>} />
      <Route path="/admin/archive" element={<RouteProtegee roles={RESSOURCES_STAFF}><AdminArchive /></RouteProtegee>} />
      <Route path="/admin/suspendus" element={<RouteProtegee roles={RESSOURCES_STAFF}><AdminSuspendus /></RouteProtegee>} />
      <Route path="/admin/import" element={<RouteProtegee roles={['admin', 'superviseur']}><AdminImport /></RouteProtegee>} />
      <Route path="/admin/utilisateurs" element={<RouteProtegee roles={['admin']}><AdminUtilisateurs /></RouteProtegee>} />
      <Route path="/admin/journal" element={<RouteProtegee roles={['admin', 'superviseur']}><Journal /></RouteProtegee>} />
      <Route path="/admin/crcs" element={<RouteProtegee roles={['admin', 'superviseur']}><GestionCrc /></RouteProtegee>} />

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
