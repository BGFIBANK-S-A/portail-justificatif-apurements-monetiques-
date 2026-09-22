import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Button, Card, Form, InputGroup, Table } from 'react-bootstrap'
import { Bar } from 'react-chartjs-2'
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip } from 'chart.js'
import { FiAlertTriangle, FiClock, FiFileText, FiSearch, FiUserX } from 'react-icons/fi'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import Pagination from '../../components/common/Pagination'
import { usePagination } from '../../hooks/usePagination'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip)

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}

const TUILES = [
  { cle: 'actifs', libelle: 'Dossiers actifs', icone: FiFileText, ton: '' },
  { cle: 'incomplets', libelle: 'Incomplets', icone: FiAlertTriangle, ton: 'violet' },
  { cle: 'en_attente', libelle: 'En attente', icone: FiClock, ton: 'alerte' },
  { cle: 'en_cours', libelle: 'En cours', icone: FiClock, ton: '' },
  { cle: 'mises_en_demeure', libelle: 'Mises en demeure', icone: FiAlertTriangle, ton: 'alerte' },
  { cle: 'suspendus', libelle: 'Clients suspendus', icone: FiUserX, ton: 'alerte' },
]

export default function AdminDashboard() {
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [filtreStatut, setFiltreStatut] = useState('')
  const [filtreType, setFiltreType] = useState('')
  const [recherche, setRecherche] = useState('')

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

  const dossiersFiltres = useMemo(() => {
    if (!donnees) return []
    const q = recherche.trim().toLowerCase()
    if (!q) return donnees.dossiers
    return donnees.dossiers.filter((d) =>
      d.reference.toLowerCase().includes(q) || `${d.client.prenom} ${d.client.nom}`.toLowerCase().includes(q)
    )
  }, [donnees, recherche])

  const { page, setPage, totalPages, itemsPage, total } = usePagination(dossiersFiltres, 8)

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
            <Card className="carte-kpi h-100">
              <Card.Body>
                <span className={`icone-carte mb-2 ${t.ton ? `icone-carte-${t.ton}` : ''}`}><t.icone /></span>
                <div className="valeur">{donnees.stats[t.cle]}</div>
                <div className="fs-10 text-body-secondary">{t.libelle}</div>
              </Card.Body>
            </Card>
          </div>
        ))}
      </div>

      <Card className="carte-kpi mb-4">
        <Card.Header className="bg-transparent border-0 pb-0"><h5 className="mb-0">Activite par categorie</h5></Card.Header>
        <Card.Body>
          <Bar data={dataChart} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }} height={90} />
        </Card.Body>
      </Card>

      <Card className="carte-kpi mb-3">
        <Card.Body>
          <Form onSubmit={onFiltrer} className="d-flex flex-wrap gap-3 align-items-end">
            <Form.Group>
              <Form.Label className="fs-10 mb-1">Rechercher</Form.Label>
              <InputGroup size="sm">
                <InputGroup.Text><FiSearch /></InputGroup.Text>
                <Form.Control placeholder="Reference ou client..." value={recherche} onChange={(e) => setRecherche(e.target.value)} />
              </InputGroup>
            </Form.Group>
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

      <Card className="carte-kpi">
        <Card.Body className="p-0">
          <div className="table-responsive">
            <Table hover className="mb-0">
              <thead className="bg-body-tertiary">
                <tr><th>Reference</th><th>Client</th><th>Type</th><th>Montant</th><th>Statut</th><th></th></tr>
              </thead>
              <tbody>
                {itemsPage.map((d) => (
                  <tr key={d.id}>
                    <td className="text-nowrap">{d.reference}</td>
                    <td>{d.client.prenom} {d.client.nom}</td>
                    <td className="text-nowrap">{d.type_dossier === 'voyage' ? 'Voyage' : 'En ligne'}</td>
                    <td className="text-nowrap">{formatMontant(d.montant)} XAF</td>
                    <td><Badge statut={d.statut} /></td>
                    <td><Link to={`/admin/dossier/${d.id}`}>Voir</Link></td>
                  </tr>
                ))}
                {itemsPage.length === 0 && <tr><td colSpan={6} className="text-body-secondary">Aucun dossier.</td></tr>}
              </tbody>
            </Table>
          </div>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} total={total} />
        </Card.Body>
      </Card>
    </MiseEnPage>
  )
}
