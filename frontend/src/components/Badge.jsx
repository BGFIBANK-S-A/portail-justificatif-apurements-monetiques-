const CONFIG = {
  incomplet: { libelle: 'Incomplet', ton: 'orange' },
  en_attente: { libelle: 'En attente', ton: 'orange' },
  en_cours: { libelle: 'En cours', ton: 'bleu' },
  valide: { libelle: 'Valide', ton: 'vert' },
  refuse: { libelle: 'Refuse', ton: 'rouge' },
  actif: { libelle: 'Actif', ton: 'vert' },
  suspendu: { libelle: 'Suspendu', ton: 'rouge' },
}

export default function Badge({ statut }) {
  const { libelle, ton } = CONFIG[statut] || { libelle: statut, ton: 'gris' }
  return <span className={`badge-pastel badge-pastel-${ton} badge-statut`}>{libelle}</span>
}
