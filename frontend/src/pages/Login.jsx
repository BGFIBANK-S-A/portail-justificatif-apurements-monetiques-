import { useState } from 'react'
import { Alert, Button, Form, InputGroup } from 'react-bootstrap'
import { Link, useNavigate } from 'react-router-dom'
import { FiLock, FiMail } from 'react-icons/fi'
import AuthCard from '../components/AuthCard'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [erreur, setErreur] = useState(null)
  const [enCours, setEnCours] = useState(false)
  const { connecter } = useAuth()
  const navigate = useNavigate()

  async function onSubmit(e) {
    e.preventDefault()
    setErreur(null)
    setEnCours(true)
    try {
      const utilisateur = await connecter(email, motDePasse)
      navigate(utilisateur.role === 'client' ? '/dashboard' : '/admin/dashboard')
    } catch (err) {
      setErreur(err.response?.data?.detail || 'Email ou mot de passe incorrect.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <AuthCard>
      <h5 className="text-center mb-4">Connexion</h5>
      {erreur && <Alert variant="danger">{erreur}</Alert>}
      <Form onSubmit={onSubmit}>
        <Form.Group className="mb-3">
          <Form.Label>Email</Form.Label>
          <InputGroup>
            <InputGroup.Text><FiMail /></InputGroup.Text>
            <Form.Control type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </InputGroup>
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label>Mot de passe</Form.Label>
          <InputGroup>
            <InputGroup.Text><FiLock /></InputGroup.Text>
            <Form.Control type="password" required value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} />
          </InputGroup>
        </Form.Group>
        <Button type="submit" className="w-100" disabled={enCours}>
          {enCours ? 'Connexion...' : 'Se connecter'}
        </Button>
        <div className="d-flex justify-content-between mt-3 fs-10">
          <Link to="/mot-de-passe-oublie">Mot de passe oublie ?</Link>
          <Link to="/renvoyer-activation">Renvoyer le lien d'acces</Link>
        </div>
      </Form>
    </AuthCard>
  )
}
