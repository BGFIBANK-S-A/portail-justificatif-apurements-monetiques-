import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Form, InputGroup, Row, Table } from 'react-bootstrap'
import { FiSearch } from 'react-icons/fi'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Pagination from '../../components/common/Pagination'
import { usePagination } from '../../hooks/usePagination'
import { useAuth } from '../../context/AuthContext'

export default function AdminUtilisateurs() {
  const { utilisateur: moi } = useAuth()
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [form, setForm] = useState({ nom: '', prenom: '', email: '', role: 'admin', mot_de_passe: '' })
  const [enCours, setEnCours] = useState(false)
  const [recherche, setRecherche] = useState('')

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

  const adminsFiltres = useMemo(() => {
    if (!donnees) return []
    const q = recherche.trim().toLowerCase()
    if (!q) return donnees.admins
    return donnees.admins.filter((a) => `${a.prenom} ${a.nom} ${a.email}`.toLowerCase().includes(q))
  }, [donnees, recherche])

  const { page, setPage, totalPages, itemsPage, total } = usePagination(adminsFiltres, 10)

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
        <Card.Body className="p-3 pb-0">
          <InputGroup size="sm" style={{ maxWidth: 320 }}>
            <InputGroup.Text><FiSearch /></InputGroup.Text>
            <Form.Control placeholder="Rechercher un utilisateur..." value={recherche} onChange={(e) => setRecherche(e.target.value)} />
          </InputGroup>
        </Card.Body>
        <Card.Body className="p-0">
          <div className="table-responsive">
            <Table hover className="mb-0">
              <thead className="bg-body-tertiary"><tr><th>Nom</th><th>Email</th><th>Role</th><th>Statut</th><th></th></tr></thead>
              <tbody>
                {itemsPage.map((a) => (
                  <tr key={a.id}>
                    <td>{a.prenom} {a.nom}</td>
                    <td>{a.email}</td>
                    <td className="text-nowrap">{a.role === 'admin' ? 'Administrateur' : 'Superviseur'}</td>
                    <td>{a.actif ? <span className="badge-pastel badge-pastel-vert">Actif</span> : <span className="badge-pastel badge-pastel-gris">Inactif</span>}</td>
                    <td className="text-nowrap">
                      {a.id !== moi?.id && (
                        <>
                          <Button size="sm" variant="outline-secondary" onClick={() => onBasculer(a.id)}>{a.actif ? 'Desactiver' : 'Activer'}</Button>
                          <Button size="sm" variant="outline-danger" className="ms-2" onClick={() => onSupprimer(a.id)}>Supprimer</Button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
                {itemsPage.length === 0 && <tr><td colSpan={5} className="text-body-secondary">Aucun utilisateur.</td></tr>}
              </tbody>
            </Table>
          </div>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} total={total} />
        </Card.Body>
      </Card>
    </MiseEnPage>
  )
}
