import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Card } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import AdvanceTable from '../../components/common/advance-table/AdvanceTable'
import AdvanceTableSearchBox from '../../components/common/advance-table/AdvanceTableSearchBox'
import AdvanceTableFooter from '../../components/common/advance-table/AdvanceTableFooter'
import AdvanceTableProvider from '../../providers/AdvanceTableProvider'
import useAdvanceTable from '../../hooks/useAdvanceTable'

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}

export default function AdminArchive() {
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    api.get('/admin/archive/').then((res) => setDonnees(res.data)).catch(() => setErreur('Impossible de charger les archives.'))
  }, [])

  const dossiers = useMemo(() => {
    if (!donnees) return []
    return donnees.groupes.flatMap((g) => g.dossiers.map((d) => ({ ...d, client: g.client })))
  }, [donnees])

  const columns = useMemo(() => [
    {
      id: 'client',
      header: 'Client',
      accessorFn: (d) => `${d.client.prenom} ${d.client.nom} ${d.client.email}`,
      cell: ({ row }) => (
        <>
          <div className="fw-semibold">{row.original.client.prenom} {row.original.client.nom}</div>
          <div className="fs-10 text-body-secondary">{row.original.client.email}</div>
        </>
      ),
    },
    { accessorKey: 'reference', header: 'Reference' },
    {
      accessorKey: 'type_dossier',
      header: 'Type',
      cell: ({ row }) => (row.original.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'),
    },
    {
      accessorKey: 'montant',
      header: 'Montant',
      cell: ({ row }) => `${formatMontant(row.original.montant)} XAF`,
    },
    {
      accessorKey: 'statut',
      header: 'Statut',
      cell: ({ row }) => <Badge statut={row.original.statut} />,
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => <Link to={`/admin/dossier/${row.original.id}`}>Voir</Link>,
    },
  ], [])

  const table = useAdvanceTable({
    data: dossiers,
    columns,
    sortable: true,
    pagination: true,
    perPage: 10,
  })

  if (erreur) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!donnees) return <MiseEnPage>Chargement...</MiseEnPage>

  return (
    <MiseEnPage titre="Archives">
      <h2 className="mb-3">Archives ({donnees.total})</h2>

      {donnees.groupes.length === 0 ? (
        <p className="text-body-secondary">Aucun dossier archive.</p>
      ) : (
        <Card>
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
        </Card>
      )}
    </MiseEnPage>
  )
}
