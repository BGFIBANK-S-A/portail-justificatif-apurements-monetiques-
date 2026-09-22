import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Form, InputGroup, Table } from 'react-bootstrap'
import { FiSearch } from 'react-icons/fi'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Pagination from '../../components/common/Pagination'
import { usePagination } from '../../hooks/usePagination'

export default function AdminSuspendus() {
  const [clients, setClients] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [recherche, setRecherche] = useState('')

  function charger() {
    api.get('/admin/suspendus/').then((res) => setClients(res.data)).catch(() => setErreur('Impossible de charger les clients suspendus.'))
  }

  useEffect(() => { charger() }, [])

  async function onReactiver(id) {
    if (!confirm('Reactiver ce client ?')) return
    await api.post(`/admin/clients/${id}/reactiver/`)
    charger()
  }

  const clientsFiltres = useMemo(() => {
    if (!clients) return []
    const q = recherche.trim().toLowerCase()
    if (!q) return clients
    return clients.filter((c) => `${c.prenom} ${c.nom} ${c.email}`.toLowerCase().includes(q))
  }, [clients, recherche])

  const { page, setPage, totalPages, itemsPage, total } = usePagination(clientsFiltres, 10)

  if (erreur) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!clients) return <MiseEnPage>Chargement...</MiseEnPage>

  return (
    <MiseEnPage titre="Clients suspendus">
      <h2 className="mb-3">Clients suspendus ({clients.length})</h2>
      <p className="text-body-secondary fs-10">
        Suspension automatique conformement a la LC BEAC 004/GR/2022 : justificatifs non transmis dans le delai
        de 8 jours suivant la mise en demeure (elle-meme declenchee 30 jours apres la 1ere operation).
      </p>

      <Card>
        {clients.length > 0 && (
          <Card.Body className="p-3 pb-0">
            <InputGroup size="sm" style={{ maxWidth: 320 }}>
              <InputGroup.Text><FiSearch /></InputGroup.Text>
              <Form.Control placeholder="Rechercher un client..." value={recherche} onChange={(e) => setRecherche(e.target.value)} />
            </InputGroup>
          </Card.Body>
        )}
        <Card.Body className="p-0">
          {clients.length === 0 ? (
            <p className="text-body-secondary p-3 mb-0">Aucun client suspendu.</p>
          ) : (
            <div className="table-responsive">
              <Table hover className="mb-0">
                <thead className="bg-body-tertiary"><tr><th>Client</th><th>Email</th><th>Motif</th><th>Date</th><th></th></tr></thead>
                <tbody>
                  {itemsPage.map((c) => (
                    <tr key={c.id}>
                      <td>{c.prenom} {c.nom}</td>
                      <td>{c.email}</td>
                      <td>{c.motif_suspension || '-'}</td>
                      <td className="text-nowrap">{c.date_suspension ? new Date(c.date_suspension).toLocaleDateString('fr-FR') : '-'}</td>
                      <td><Button size="sm" variant="outline-success" onClick={() => onReactiver(c.id)}>Reactiver</Button></td>
                    </tr>
                  ))}
                  {itemsPage.length === 0 && <tr><td colSpan={5} className="text-body-secondary">Aucun resultat.</td></tr>}
                </tbody>
              </Table>
            </div>
          )}
          <Pagination page={page} totalPages={totalPages} onChange={setPage} total={total} />
        </Card.Body>
      </Card>
    </MiseEnPage>
  )
}
