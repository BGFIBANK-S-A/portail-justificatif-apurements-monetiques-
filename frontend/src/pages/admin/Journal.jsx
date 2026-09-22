import { useEffect, useState } from 'react'
import { Alert, Card, Table } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'

export default function Journal() {
  const [evenements, setEvenements] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    api.get('/admin/journal/').then((res) => setEvenements(res.data)).catch(() => setErreur("Impossible de charger le journal d'activite."))
  }, [])

  if (erreur) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!evenements) return <MiseEnPage>Chargement...</MiseEnPage>

  return (
    <MiseEnPage titre="Journal d'activite">
      <h2 className="mb-3">Journal d'activite</h2>
      <Card>
        <Card.Body className="p-0">
          <div className="table-responsive">
            <Table hover className="mb-0">
              <thead className="bg-body-tertiary"><tr><th>Date</th><th>Action</th><th>Description</th><th>Acteur</th></tr></thead>
              <tbody>
                {evenements.map((e) => (
                  <tr key={e.id}>
                    <td className="text-nowrap">{new Date(e.date_evenement).toLocaleString('fr-FR')}</td>
                    <td className="text-nowrap">{e.type_action}</td>
                    <td>{e.description || '-'}</td>
                    <td className="text-nowrap">{e.utilisateur || '-'}</td>
                  </tr>
                ))}
                {evenements.length === 0 && <tr><td colSpan={4} className="text-body-secondary">Aucun evenement.</td></tr>}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>
    </MiseEnPage>
  )
}
