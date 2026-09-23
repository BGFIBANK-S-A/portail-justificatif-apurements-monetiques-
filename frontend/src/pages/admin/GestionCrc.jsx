import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FiChevronRight, FiUsers } from 'react-icons/fi'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import './gestionCrc.css'

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}

export default function GestionCrc() {
  const [groupes, setGroupes] = useState(null)
  const [groupesOuverts, setGroupesOuverts] = useState({})
  const [recherche, setRecherche] = useState('')
  const [crcSelectionne, setCrcSelectionne] = useState(null)
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    api.get('/admin/crcs/').then((res) => {
      setGroupes(res.data.groupes)
      const ouverts = {}
      res.data.groupes.forEach((g) => { ouverts[g.id] = true })
      setGroupesOuverts(ouverts)
    })
  }, [])

  function onSelectionnerCrc(crc) {
    setCrcSelectionne(crc)
    setDetail(null)
    api.get(`/admin/crcs/${crc.id}/dossiers/`).then((res) => setDetail(res.data))
  }

  if (!groupes) return <MiseEnPage titre="Gestion des CRC">Chargement...</MiseEnPage>

  const rechercheNorm = recherche.trim().toLowerCase()
  const groupesFiltres = groupes
    .map((g) => ({
      ...g,
      crcs: g.crcs.filter((c) => !rechercheNorm || `${c.prenom} ${c.nom}`.toLowerCase().includes(rechercheNorm)),
    }))
    .filter((g) => g.crcs.length > 0)

  return (
    <MiseEnPage titre="Gestion des CRC">
      <h2 className="mb-3">Gestion des CRC</h2>
      <div className="crc-mgmt">
        <div className="crc-mgmt-sidebar">
          <div className="crc-mgmt-sidebar-header"><FiUsers /> Portefeuille CRC</div>
          <div className="crc-mgmt-search">
            <input placeholder="Rechercher un CRC..." value={recherche} onChange={(e) => setRecherche(e.target.value)} />
          </div>
          {groupesFiltres.map((g) => (
            <div key={g.id}>
              <div
                className={`crc-mgmt-groupe-titre ${groupesOuverts[g.id] ? 'ouvert' : ''}`}
                onClick={() => setGroupesOuverts({ ...groupesOuverts, [g.id]: !groupesOuverts[g.id] })}
              >
                <FiChevronRight className="chevron" />
                {g.nom} ({g.crcs.length})
              </div>
              {groupesOuverts[g.id] && g.crcs.map((c) => (
                <div
                  key={c.id}
                  className={`crc-mgmt-crc-item ${crcSelectionne?.id === c.id ? 'actif' : ''}`}
                  onClick={() => onSelectionnerCrc(c)}
                >
                  <span>{c.prenom} {c.nom}</span>
                  {c.nb_en_attente > 0 && <span className="badge-attente">{c.nb_en_attente}</span>}
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="crc-mgmt-main">
          {!crcSelectionne ? (
            <>
              <div className="crc-mgmt-topbar"><h5>Selectionnez un CRC</h5></div>
              <div className="crc-mgmt-vide">
                <FiUsers size={40} />
                Selectionnez un CRC dans la liste pour voir ses dossiers en attente de justification.
              </div>
            </>
          ) : (
            <>
              <div className="crc-mgmt-detail-header">
                <div>
                  <div className="nom">{crcSelectionne.prenom} {crcSelectionne.nom}</div>
                  <div className="sous">{crcSelectionne.email}</div>
                </div>
                <div className="stat-pill">
                  <span className="valeur">{detail ? detail.dossiers.length : '-'}</span>
                  dossier(s) en attente
                </div>
              </div>
              <div className="crc-mgmt-table-wrap">
                {!detail ? (
                  <div className="p-4 text-body-secondary">Chargement...</div>
                ) : detail.dossiers.length === 0 ? (
                  <div className="p-4 text-body-secondary">Aucun dossier en attente pour ce CRC.</div>
                ) : (
                  <table className="crc-mgmt-table">
                    <thead>
                      <tr><th>Reference</th><th>Client</th><th>Type</th><th>Montant</th><th>Statut</th><th></th></tr>
                    </thead>
                    <tbody>
                      {detail.dossiers.map((d) => (
                        <tr key={d.id}>
                          <td>{d.reference}</td>
                          <td>{d.client.prenom} {d.client.nom}</td>
                          <td>{d.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'}</td>
                          <td>{formatMontant(d.montant)} XAF</td>
                          <td><Badge statut={d.statut} /></td>
                          <td><Link to={`/admin/dossier/${d.id}`}>Voir</Link></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </MiseEnPage>
  )
}
