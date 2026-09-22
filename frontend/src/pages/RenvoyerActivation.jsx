import { useState } from 'react'
import { Alert, Button, Form } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import api from '../api/client'

export default function RenvoyerActivation() {
  const [email, setEmail] = useState('')
  const [envoye, setEnvoye] = useState(false)
  const [enCours, setEnCours] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setEnCours(true)
    try {
      await api.post('/auth/renvoyer-activation/', { email })
    } finally {
      setEnvoye(true)
      setEnCours(false)
    }
  }

  return (
    <AuthCard>
      <h5 className="text-center mb-4">Renvoyer le lien d'acces</h5>
      {envoye ? (
        <Alert variant="success">Si un compte existe pour cet email, un lien a ete envoye.</Alert>
      ) : (
        <Form onSubmit={onSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Email</Form.Label>
            <Form.Control type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Form.Group>
          <Button type="submit" className="w-100" disabled={enCours}>
            {enCours ? 'Envoi...' : 'Envoyer le lien'}
          </Button>
        </Form>
      )}
      <div className="text-center mt-3 fs-10">
        <Link to="/login">Retour a la connexion</Link>
      </div>
    </AuthCard>
  )
}
