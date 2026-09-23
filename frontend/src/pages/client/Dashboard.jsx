import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Table } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import SubtleBadge from '../../components/common/SubtleBadge'

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}

function CarteDossierMobile({ d }) {
  return (
    <div className="p-3 border-bottom">
      <div className="d-flex justify-content-between align-items-start mb-1">
        <span className="fw-semibold">{d.reference}</span>
        <SubtleBadge bg="primary">{d.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'}</SubtleBadge>
      </div>
      <div className="d-flex justify-content-between align-items-center mb-2">
        <span className="fw-semibold">{formatMontant(d.montant)} XAF</span>
        <Badge statut={d.statut} />
      </div>
      {d.jours_restants !== null && (
        <div className="fs-10 text-body-secondary mb-2">Delai restant : {d.jours_restants} jour(s)</div>
      )}
      <Link to={`/dossier/${d.id}`} className="btn btn-primary btn-sm w-100">Ouvrir</Link>
    </div>
  )
}

export default function Dashboard() {
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState(null)
  const navigate = useNavigate()

  function charger() {
    api.get('/dashboard/').then((res) => setDonnees(res.data)).catch(() => setErreur('Impossible de charger vos dossiers.'))
  }

  useEffect(() => { charger() }, [])

  async function onAnticiperVoyage() {
    const res = await api.post('/dossier/anticiper-voyage/')
    navigate(`/dossier/${res.data.id}`)
  }

  if (erreur) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!donnees) return <MiseEnPage>Chargement...</MiseEnPage>

  const voyageHorsCemac = donnees.dossiers.some((d) => d.type_dossier === 'voyage' && d.preuve_voyage_manquante)

  return (
    <MiseEnPage titre="Mon espace">
      <h2 className="mb-3">Mes dossiers de justification</h2>

      {voyageHorsCemac && (
        <Alert variant="warning">
          Votre carte a effectue une transaction hors de la zone CEMAC. Nous avons besoin d'une preuve de voyage
          (passeport + billet d'avion) pour instruire votre dossier.
        </Alert>
      )}

      <div className="mb-3">
        <Button onClick={onAnticiperVoyage}>+ Declarer un voyage a venir</Button>
      </div>

      <Card className="mb-4">
        <Card.Header><h5 className="mb-0">Dossiers en cours ({donnees.dossiers.length})</h5></Card.Header>
        <Card.Body className="p-0">
          {donnees.dossiers.length === 0 ? (
            <p className="text-body-secondary p-3 mb-0">Aucun dossier en cours.</p>
          ) : (
            <>
              <div className="d-md-none">
                {donnees.dossiers.map((d) => <CarteDossierMobile key={d.id} d={d} />)}
              </div>
              <div className="table-responsive d-none d-md-block">
                <Table hover className="mb-0">
                  <thead className="bg-body-tertiary">
                    <tr>
                      <th>Reference</th><th>Type</th><th>Montant a justifier</th><th>Statut</th><th>Jours restants</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {donnees.dossiers.map((d) => (
                      <tr key={d.id}>
                        <td className="text-nowrap">{d.reference}</td>
                        <td className="text-nowrap">{d.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'}</td>
                        <td className="text-nowrap">{formatMontant(d.montant)} XAF</td>
                        <td><Badge statut={d.statut} /></td>
                        <td className="text-nowrap">{d.jours_restants !== null ? `${d.jours_restants} j` : '-'}</td>
                        <td><Link to={`/dossier/${d.id}`}>Voir</Link></td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </>
          )}
        </Card.Body>
      </Card>

      <Card>
        <Card.Header><h5 className="mb-0">Archives ({donnees.archives.length})</h5></Card.Header>
        <Card.Body className="p-0">
          {donnees.archives.length === 0 ? (
            <p className="text-body-secondary p-3 mb-0">Aucun dossier archive.</p>
          ) : (
            <>
              <div className="d-md-none">
                {donnees.archives.map((d) => <CarteDossierMobile key={d.id} d={d} />)}
              </div>
              <div className="table-responsive d-none d-md-block">
                <Table hover className="mb-0">
                  <thead className="bg-body-tertiary"><tr><th>Reference</th><th>Type</th><th>Montant</th><th>Statut</th><th></th></tr></thead>
                  <tbody>
                    {donnees.archives.map((d) => (
                      <tr key={d.id}>
                        <td className="text-nowrap">{d.reference}</td>
                        <td className="text-nowrap">{d.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'}</td>
                        <td className="text-nowrap">{formatMontant(d.montant)} XAF</td>
                        <td><Badge statut={d.statut} /></td>
                        <td><Link to={`/dossier/${d.id}`}>Voir</Link></td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </>
          )}
        </Card.Body>
      </Card>
    </MiseEnPage>
  )
}
