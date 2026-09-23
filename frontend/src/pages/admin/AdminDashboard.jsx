import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Button, Card, Form } from 'react-bootstrap'
import { Bar } from 'react-chartjs-2'
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip } from 'chart.js'
import { FiAlertTriangle, FiClock, FiFileText, FiUserX } from 'react-icons/fi'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import Flex from '../../components/common/Flex'
import AdvanceTable from '../../components/common/advance-table/AdvanceTable'
import AdvanceTableSearchBox from '../../components/common/advance-table/AdvanceTableSearchBox'
import AdvanceTableFooter from '../../components/common/advance-table/AdvanceTableFooter'
import AdvanceTableProvider from '../../providers/AdvanceTableProvider'
import useAdvanceTable from '../../hooks/useAdvanceTable'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip)

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}

const TUILES = [
  { cle: 'actifs', libelle: 'Dossiers actifs', icone: FiFileText, ton: 'primary' },
  { cle: 'incomplets', libelle: 'Incomplets', icone: FiAlertTriangle, ton: 'warning' },
  { cle: 'en_attente', libelle: 'En attente', icone: FiClock, ton: 'info' },
  { cle: 'en_cours', libelle: 'En cours', icone: FiClock, ton: 'secondary' },
  { cle: 'mises_en_demeure', libelle: 'Mises en demeure', icone: FiAlertTriangle, ton: 'danger' },
  { cle: 'suspendus', libelle: 'Clients suspendus', icone: FiUserX, ton: 'danger' },
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

  const columns = useMemo(() => [
    { accessorKey: 'reference', header: 'Reference' },
    {
      id: 'client',
      header: 'Client',
      accessorFn: (d) => `${d.client.prenom} ${d.client.nom}`,
      cell: ({ row }) => `${row.original.client.prenom} ${row.original.client.nom}`,
    },
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
    data: donnees?.dossiers || [],
    columns,
    sortable: true,
    pagination: true,
    perPage: 10,
  })

  if (erreur) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!donnees) return <MiseEnPage>Chargement...</MiseEnPage>

  const dataChart = {
    labels: TUILES.map((t) => t.libelle),
    datasets: [{
      data: TUILES.map((t) => donnees.stats[t.cle]),
      backgroundColor: '#0d2b4e',
      borderRadius: 6,
      maxBarThickness: 42,
    }],
  }

  return (
    <MiseEnPage titre="Tableau de bord">
      <h2 className="mb-4">Tableau de bord</h2>

      <div className="row g-3 mb-4">
        {TUILES.map((t) => (
          <div className="col-6 col-md-4 col-lg-2" key={t.cle}>
            <Card className="h-100">
              <Card.Body as={Flex} justifyContent="between" alignItems="center">
                <div>
                  <p className="fs-9 fw-medium text-body-secondary mb-1">{t.libelle}</p>
                  <h4 className="mb-0 fw-bold">{donnees.stats[t.cle]}</h4>
                </div>
                <div className={`icon-item icon-item-lg bg-${t.ton}-subtle text-${t.ton}`}>
                  <t.icone size={18} />
                </div>
              </Card.Body>
            </Card>
          </div>
        ))}
      </div>

      <Card className="mb-4">
        <Card.Header className="pb-0"><h6 className="mb-0 mt-2">Activite par categorie</h6></Card.Header>
        <Card.Body>
          <Bar data={dataChart} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }} height={90} />
        </Card.Body>
      </Card>

      <Card className="mb-3">
        <Card.Body>
          <Form onSubmit={onFiltrer} className="d-flex flex-wrap gap-3 align-items-end">
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
            <Button type="submit" size="sm" variant="primary">Filtrer</Button>
          </Form>
        </Card.Body>
      </Card>

      <Card>
        <AdvanceTableProvider {...table}>
          <Card.Body className="p-3 pb-0">
            <AdvanceTableSearchBox placeholder="Rechercher un dossier..." className="w-auto" />
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
    </MiseEnPage>
  )
}
