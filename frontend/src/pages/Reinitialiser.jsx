import { useState } from 'react'
import { Alert, Button, Form } from 'react-bootstrap'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import api from '../api/client'

export default function Reinitialiser() {
  const { token } = useParams()
  const navigate = useNavigate()
  const [motDePasse, setMotDePasse] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [erreur, setErreur] = useState(null)
  const [enCours, setEnCours] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setErreur(null)
    setEnCours(true)
    try {
      await api.post(`/auth/reinitialiser/${token}/`, { mot_de_passe: motDePasse, confirmation })
      navigate('/login')
    } catch (err) {
      setErreur(err.response?.data?.detail || 'Erreur lors de la reinitialisation.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <AuthCard>
      <h5 className="text-center mb-4">Nouveau mot de passe</h5>
      {erreur && <Alert variant="danger">{erreur}</Alert>}
      <Form onSubmit={onSubmit}>
        <Form.Group className="mb-3">
          <Form.Label>Nouveau mot de passe</Form.Label>
          <Form.Control type="password" required minLength={6} value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} />
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label>Confirmation</Form.Label>
          <Form.Control type="password" required minLength={6} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
        </Form.Group>
        <Button type="submit" className="w-100" disabled={enCours}>
          {enCours ? 'Enregistrement...' : 'Reinitialiser'}
        </Button>
      </Form>
      <div className="text-center mt-3 fs-10">
        <Link to="/login">Retour a la connexion</Link>
      </div>
    </AuthCard>
  )
}
