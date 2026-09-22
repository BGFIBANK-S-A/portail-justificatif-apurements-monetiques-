import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Card, Form, Table } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}

const TUILES = [
  { cle: 'actifs', libelle: 'Dossiers actifs' },
  { cle: 'incomplets', libelle: 'Incomplets' },
  { cle: 'en_attente', libelle: 'En attente' },
  { cle: 'en_cours', libelle: 'En cours' },
  { cle: 'mises_en_demeure', libelle: 'Mises en demeure' },
  { cle: 'suspendus', libelle: 'Clients suspendus' },
]

export default function AdminDashboard() {
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [filtreStatut, setFiltreStatut] = useState('')
  const [filtreType, setFiltreType] = useState('')

  function charger(statut = filtreStatut, type = filtreType) {
    const params = {}
    if (statut) params.statut = statut
    if (type) params.type = type
    api.get('/admin/dashboard/', { params }).then((res) => setDonnees(res.data)).catch(() => setErreur('Impossible de charger le tableau de bord.'))
  }

  useEffect(() => { charger() }, [])

  function onFiltrer(e) {
    e.preventDefault()
    charger()
  }

  if (erreur) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!donnees) return <MiseEnPage>Chargement...</MiseEnPage>

  return (
    <MiseEnPage titre="Tableau de bord">
      <h2 className="mb-3">Tableau de bord</h2>

      <div className="row g-3 mb-4">
        {TUILES.map((t) => (
          <div className="col-6 col-md-4 col-lg-2" key={t.cle}>
            <Card className="stat-tuile h-100">
              <div className="fs-3 fw-bold">{donnees.stats[t.cle]}</div>
              <div className="fs-10 text-body-secondary">{t.libelle}</div>
            </Card>
          </div>
        ))}
      </div>

      <Form onSubmit={onFiltrer} className="d-flex flex-wrap gap-3 align-items-end mb-3">
        <Form.Group>
          <Form.Label className="fs-10 mb-1">Statut</Form.Label>
          <Form.Select size="sm" value={filtreStatut} onChange={(e) => setFiltreStatut(e.target.value)}>
            <option value="">Tous</option>
            <option value="incomplet">Incomplet</option>
            <option value="en_attente">En attente</option>
            <option value="en_cours">En cours</option>
          </Form.Select>
        </Form.Group>
        <Form.Group>
          <Form.Label className="fs-10 mb-1">Type</Form.Label>
          <Form.Select size="sm" value={filtreType} onChange={(e) => setFiltreType(e.target.value)}>
            <option value="">Tous</option>
            <option value="voyage">Voyage</option>
            <option value="ligne">En ligne</option>
          </Form.Select>
        </Form.Group>
        <button type="submit" className="btn btn-primary btn-sm">Filtrer</button>
      </Form>

      <Card>
        <Card.Body className="p-0">
          <div className="table-responsive">
            <Table hover className="mb-0">
              <thead className="bg-body-tertiary">
                <tr><th>Reference</th><th>Client</th><th>Type</th><th>Montant</th><th>Statut</th><th>Incoherences</th><th></th></tr>
              </thead>
              <tbody>
                {donnees.dossiers.map((d) => (
                  <tr key={d.id}>
                    <td className="text-nowrap">{d.reference}</td>
                    <td>{d.client.prenom} {d.client.nom}</td>
                    <td className="text-nowrap">{d.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'}</td>
                    <td className="text-nowrap">{formatMontant(d.montant)} XAF</td>
                    <td><Badge statut={d.statut} /></td>
                    <td>-</td>
                    <td><Link to={`/admin/dossier/${d.id}`}>Voir</Link></td>
                  </tr>
                ))}
                {donnees.dossiers.length === 0 && <tr><td colSpan={7} className="text-body-secondary">Aucun dossier.</td></tr>}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>
    </MiseEnPage>
  )
}
