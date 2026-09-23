import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Form, Row } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import SubtleBadge from '../../components/common/SubtleBadge'
import AdvanceTable from '../../components/common/advance-table/AdvanceTable'
import AdvanceTableSearchBox from '../../components/common/advance-table/AdvanceTableSearchBox'
import AdvanceTableFooter from '../../components/common/advance-table/AdvanceTableFooter'
import AdvanceTableProvider from '../../providers/AdvanceTableProvider'
import useAdvanceTable from '../../hooks/useAdvanceTable'
import { useAuth } from '../../context/AuthContext'

export default function AdminUtilisateurs() {
  const { utilisateur: moi } = useAuth()
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [form, setForm] = useState({ nom: '', prenom: '', email: '', role: 'admin', mot_de_passe: '' })
  const [enCours, setEnCours] = useState(false)

  function charger() {
    api.get('/admin/utilisateurs/').then((res) => setDonnees(res.data)).catch(() => setErreur('Impossible de charger les utilisateurs.'))
  }

  useEffect(() => { charger() }, [])

  async function onCreer(e) {
    e.preventDefault()
    setErreur(null)
    setEnCours(true)
    try {
      await api.post('/admin/utilisateurs/', form)
      setForm({ nom: '', prenom: '', email: '', role: 'admin', mot_de_passe: '' })
      charger()
    } catch (err) {
      setErreur(err.response?.data?.detail || 'Erreur lors de la creation.')
    } finally {
      setEnCours(false)
    }
  }

  async function onBasculer(id) {
    try {
      await api.post(`/admin/utilisateurs/${id}/basculer/`)
      charger()
    } catch (err) {
      setErreur(err.response?.data?.detail || 'Erreur.')
    }
  }

  async function onSupprimer(id) {
    if (!confirm('Supprimer ce compte ?')) return
    try {
      await api.post(`/admin/utilisateurs/${id}/supprimer/`)
      charger()
    } catch (err) {
      setErreur(err.response?.data?.detail || 'Erreur.')
    }
  }

  const columns = useMemo(() => [
    {
      accessorKey: 'nom',
      header: 'Nom',
      cell: ({ row }) => `${row.original.prenom} ${row.original.nom}`,
    },
    { accessorKey: 'email', header: 'Email' },
    {
      accessorKey: 'role',
      header: 'Role',
      cell: ({ row }) => (row.original.role === 'admin' ? 'Administrateur' : 'Superviseur'),
    },
    {
      accessorKey: 'actif',
      header: 'Statut',
      cell: ({ row }) => (row.original.actif ? <SubtleBadge bg="success">Actif</SubtleBadge> : <SubtleBadge bg="secondary">Inactif</SubtleBadge>),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const a = row.original
        if (a.id === moi?.id) return null
        return (
          <>
            <Button size="sm" variant="outline-secondary" onClick={() => onBasculer(a.id)}>{a.actif ? 'Desactiver' : 'Activer'}</Button>
            <Button size="sm" variant="outline-danger" className="ms-2" onClick={() => onSupprimer(a.id)}>Supprimer</Button>
          </>
        )
      },
    },
  ], [moi])

  const table = useAdvanceTable({
    data: donnees?.admins || [],
    columns,
    sortable: true,
    pagination: true,
    perPage: 10,
  })

  if (erreur && !donnees) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!donnees) return <MiseEnPage>Chargement...</MiseEnPage>

  return (
    <MiseEnPage titre="Utilisateurs">
      <h2 className="mb-3">Utilisateurs</h2>
      {erreur && <Alert variant="danger">{erreur}</Alert>}
      <p className="text-body-secondary fs-10">{donnees.nb_clients} compte(s) client au total.</p>

      <Card className="mb-4">
        <Card.Header><h5 className="mb-0">Ajouter un membre du personnel</h5></Card.Header>
        <Card.Body>
          <Form onSubmit={onCreer}>
            <Row className="g-3">
              <Col md={3}>
                <Form.Label className="fs-10">Prenom</Form.Label>
                <Form.Control required value={form.prenom} onChange={(e) => setForm({ ...form, prenom: e.target.value })} />
              </Col>
              <Col md={3}>
                <Form.Label className="fs-10">Nom</Form.Label>
                <Form.Control required value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} />
              </Col>
              <Col md={3}>
                <Form.Label className="fs-10">Email</Form.Label>
                <Form.Control type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </Col>
              <Col md={2}>
                <Form.Label className="fs-10">Role</Form.Label>
                <Form.Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                  <option value="admin">Administrateur</option>
                  <option value="superviseur">Superviseur</option>
                </Form.Select>
              </Col>
              <Col md={1} className="d-flex align-items-end">
                <Button type="submit" disabled={enCours} className="w-100">+</Button>
              </Col>
              <Col md={4}>
                <Form.Label className="fs-10">Mot de passe</Form.Label>
                <Form.Control type="password" required minLength={6} value={form.mot_de_passe} onChange={(e) => setForm({ ...form, mot_de_passe: e.target.value })} />
              </Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>

      <Card>
        <AdvanceTableProvider {...table}>
          <Card.Body className="p-3 pb-0">
            <AdvanceTableSearchBox placeholder="Rechercher un utilisateur..." className="w-auto" />
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
