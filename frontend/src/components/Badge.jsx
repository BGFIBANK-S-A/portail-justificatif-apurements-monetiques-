import SubtleBadge from './common/SubtleBadge'

const CONFIG = {
  incomplet: { libelle: 'Incomplet', bg: 'warning' },
  en_attente: { libelle: 'En attente', bg: 'info' },
  en_cours: { libelle: 'En cours', bg: 'primary' },
  valide: { libelle: 'Valide', bg: 'success' },
  refuse: { libelle: 'Refuse', bg: 'danger' },
  actif: { libelle: 'Actif', bg: 'success' },
  suspendu: { libelle: 'Suspendu', bg: 'danger' },
}

export default function Badge({ statut }) {
  const { libelle, bg } = CONFIG[statut] || { libelle: statut, bg: 'secondary' }
  return (
    <SubtleBadge bg={bg} pill>
      {libelle}
    </SubtleBadge>
  )
}
