import { useEffect, useState } from 'react'
import { Alert, Button, Form } from 'react-bootstrap'
import { useNavigate, useParams } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import api from '../api/client'
import { tokens } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Activer() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { setUtilisateur } = useAuth()
  const [email, setEmail] = useState(null)
  const [erreurChargement, setErreurChargement] = useState(null)
  const [motDePasse, setMotDePasse] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [erreur, setErreur] = useState(null)
  const [enCours, setEnCours] = useState(false)

  useEffect(() => {
    api.get(`/auth/activer/${token}/`)
      .then((res) => setEmail(res.data.email))
      .catch((err) => setErreurChargement(err.response?.data?.detail || "Lien d'activation invalide ou expire."))
  }, [token])

  async function onSubmit(e) {
    e.preventDefault()
    setErreur(null)
    setEnCours(true)
    try {
      const res = await api.post(`/auth/activer/${token}/`, { mot_de_passe: motDePasse, confirmation })
      tokens.set(res.data.access, res.data.refresh)
      setUtilisateur(res.data.utilisateur)
      navigate('/dashboard')
    } catch (err) {
      setErreur(err.response?.data?.detail || "Erreur lors de l'activation.")
    } finally {
      setEnCours(false)
    }
  }

  if (erreurChargement) return <AuthCard><Alert variant="danger">{erreurChargement}</Alert></AuthCard>
  if (!email) return <AuthCard>Chargement...</AuthCard>

  return (
    <AuthCard>
      <h5 className="text-center mb-2">Activation du compte</h5>
      <p className="text-center text-body-secondary fs-10 mb-4">{email}</p>
      {erreur && <Alert variant="danger">{erreur}</Alert>}
      <Form onSubmit={onSubmit}>
        <Form.Group className="mb-3">
          <Form.Label>Choisissez un mot de passe</Form.Label>
          <Form.Control type="password" required minLength={6} value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} />
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label>Confirmation</Form.Label>
          <Form.Control type="password" required minLength={6} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
        </Form.Group>
        <Button type="submit" className="w-100" disabled={enCours}>
          {enCours ? 'Activation...' : 'Activer mon compte'}
        </Button>
      </Form>
    </AuthCard>
  )
}
