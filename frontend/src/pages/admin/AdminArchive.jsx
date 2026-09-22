import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Card, Form, InputGroup, Table } from 'react-bootstrap'
import { FiSearch } from 'react-icons/fi'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import Pagination from '../../components/common/Pagination'
import { usePagination } from '../../hooks/usePagination'

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}

export default function AdminArchive() {
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [recherche, setRecherche] = useState('')

  useEffect(() => {
    api.get('/admin/archive/').then((res) => setDonnees(res.data)).catch(() => setErreur('Impossible de charger les archives.'))
  }, [])

  const groupesFiltres = useMemo(() => {
    if (!donnees) return []
    const q = recherche.trim().toLowerCase()
    if (!q) return donnees.groupes
    return donnees.groupes.filter((g) => `${g.client.prenom} ${g.client.nom} ${g.client.email}`.toLowerCase().includes(q))
  }, [donnees, recherche])

  const { page, setPage, totalPages, itemsPage, total } = usePagination(groupesFiltres, 5)

  if (erreur) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!donnees) return <MiseEnPage>Chargement...</MiseEnPage>

  return (
    <MiseEnPage titre="Archives">
      <h2 className="mb-3">Archives ({donnees.total})</h2>

      {donnees.groupes.length === 0 ? (
        <p className="text-body-secondary">Aucun dossier archive.</p>
      ) : (
        <>
          <InputGroup size="sm" className="mb-3" style={{ maxWidth: 320 }}>
            <InputGroup.Text><FiSearch /></InputGroup.Text>
            <Form.Control placeholder="Rechercher un client..." value={recherche} onChange={(e) => setRecherche(e.target.value)} />
          </InputGroup>

          {itemsPage.map((g) => (
            <Card className="mb-3" key={g.client.id}>
              <Card.Header className="bg-transparent"><h5 className="mb-0">{g.client.prenom} {g.client.nom}</h5><div className="fs-10 text-body-secondary">{g.client.email}</div></Card.Header>
              <Card.Body className="p-0">
                <div className="table-responsive">
                  <Table hover className="mb-0">
                    <thead className="bg-body-tertiary"><tr><th>Reference</th><th>Type</th><th>Montant</th><th>Statut</th><th></th></tr></thead>
                    <tbody>
                      {g.dossiers.map((d) => (
                        <tr key={d.id}>
                          <td className="text-nowrap">{d.reference}</td>
                          <td className="text-nowrap">{d.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'}</td>
                          <td className="text-nowrap">{formatMontant(d.montant)} XAF</td>
                          <td><Badge statut={d.statut} /></td>
                          <td><Link to={`/admin/dossier/${d.id}`}>Voir</Link></td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              </Card.Body>
            </Card>
          ))}
          {itemsPage.length === 0 && <p className="text-body-secondary">Aucun client ne correspond a cette recherche.</p>}

          {totalPages > 1 && (
            <Card className="carte-kpi">
              <Pagination page={page} totalPages={totalPages} onChange={setPage} total={total} />
            </Card>
          )}
        </>
      )}
    </MiseEnPage>
  )
}
