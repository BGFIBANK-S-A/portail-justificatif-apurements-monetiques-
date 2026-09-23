import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import AdvanceTable from '../../components/common/advance-table/AdvanceTable'
import AdvanceTableSearchBox from '../../components/common/advance-table/AdvanceTableSearchBox'
import AdvanceTableFooter from '../../components/common/advance-table/AdvanceTableFooter'
import AdvanceTableProvider from '../../providers/AdvanceTableProvider'
import useAdvanceTable from '../../hooks/useAdvanceTable'

export default function AdminSuspendus() {
  const [clients, setClients] = useState(null)
  const [erreur, setErreur] = useState(null)

  function charger() {
    api.get('/admin/suspendus/').then((res) => setClients(res.data)).catch(() => setErreur('Impossible de charger les clients suspendus.'))
  }

  useEffect(() => { charger() }, [])

  async function onReactiver(id) {
    if (!confirm('Reactiver ce client ?')) return
    await api.post(`/admin/clients/${id}/reactiver/`)
    charger()
  }

  const columns = useMemo(() => [
    {
      accessorKey: 'nom',
      header: 'Client',
      cell: ({ row }) => `${row.original.prenom} ${row.original.nom}`,
    },
    { accessorKey: 'email', header: 'Email' },
    {
      accessorKey: 'motif_suspension',
      header: 'Motif',
      cell: ({ row }) => row.original.motif_suspension || '-',
    },
    {
      accessorKey: 'date_suspension',
      header: 'Date',
      cell: ({ row }) => (row.original.date_suspension ? new Date(row.original.date_suspension).toLocaleDateString('fr-FR') : '-'),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <Button size="sm" variant="outline-success" onClick={() => onReactiver(row.original.id)}>Reactiver</Button>
      ),
    },
  ], [])

  const table = useAdvanceTable({
    data: clients || [],
    columns,
    sortable: true,
    pagination: true,
    perPage: 10,
  })

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
        {clients.length === 0 ? (
          <Card.Body>
            <p className="text-body-secondary mb-0">Aucun client suspendu.</p>
          </Card.Body>
        ) : (
          <AdvanceTableProvider {...table}>
            <Card.Body className="p-3 pb-0">
              <AdvanceTableSearchBox placeholder="Rechercher un client..." className="w-auto" />
            </Card.Body>
            <Card.Body className="p-0">
              <AdvanceTable
                headerClassName="bg-body-tertiary fw-medium font-sans-serif"
                tableProps={{ hover: true, className: 'mb-0' }}
              />
            </Card.Body>
            <Card.Footer>
              <AdvanceTableFooter rowInfo rowsPerPageSelection navButtons />
            </Card.Footer>
          </AdvanceTableProvider>
        )}
      </Card>
    </MiseEnPage>
  )
}
