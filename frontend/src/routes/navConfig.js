import { FiActivity, FiArchive, FiFolder, FiHome, FiUpload, FiUserCheck, FiUsers } from 'react-icons/fi'

export const RESSOURCES_STAFF = ['admin', 'superviseur', 'crc', 'acrc']

const LIENS_CLIENT = [{ to: '/dashboard', label: 'Mes dossiers', icon: FiFolder }]

const LIENS_STAFF = [
  { to: '/admin/dashboard', label: 'Tableau de bord', icon: FiHome },
  { to: '/admin/crcs', label: 'Gestion des CRC', icon: FiUsers, roles: ['admin', 'superviseur'] },
  { to: '/admin/archive', label: 'Archives', icon: FiArchive },
  { to: '/admin/suspendus', label: 'Clients suspendus', icon: FiUserCheck },
  { to: '/admin/utilisateurs', label: 'Utilisateurs', icon: FiUsers, roles: ['admin'] },
  { to: '/admin/import', label: 'Import fichiers', icon: FiUpload, roles: ['admin', 'superviseur'] },
  { to: '/admin/journal', label: "Journal d'activite", icon: FiActivity, roles: ['admin', 'superviseur'] },
]

export function navItemsPourRole(role) {
  const liens = role === 'client' ? LIENS_CLIENT : LIENS_STAFF
  return liens.filter((l) => !l.roles || l.roles.includes(role))
}
