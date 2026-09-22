import { useState } from 'react'
import { Button, Modal, Navbar } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { FiLogOut, FiMenu } from 'react-icons/fi'
import { useAuth } from '../../context/AuthContext'

export default function NavbarTop({ titre, onToggleSidebar }) {
  const { utilisateur, deconnecter } = useAuth()
  const navigate = useNavigate()
  const [modalOuvert, setModalOuvert] = useState(false)
  const [enCours, setEnCours] = useState(false)

  async function onConfirmerDeconnexion() {
    setEnCours(true)
    await deconnecter()
    navigate('/login')
  }

  return (
    <>
      <Navbar className="navbar-top-institutionnelle fs-10 navbar-top sticky-kit" expand>
        <button
          type="button"
          className="btn btn-link d-flex flex-center d-xl-none me-2 p-0"
          onClick={onToggleSidebar}
          aria-label="Ouvrir le menu"
        >
          <FiMenu size={20} />
        </button>
        {titre && <span className="fw-semibold">{titre}</span>}
        <ul className="ms-auto d-flex align-items-center navbar-nav-icons flex-row list-unstyled mb-0">
          <li className="nav-item me-3 d-none d-sm-block opacity-75">
            {utilisateur?.prenom} {utilisateur?.nom}
          </li>
          <li className="nav-item">
            <Button variant="outline-light" size="sm" onClick={() => setModalOuvert(true)}>
              <FiLogOut className="me-1" />Deconnexion
            </Button>
          </li>
        </ul>
      </Navbar>

      <Modal show={modalOuvert} onHide={() => !enCours && setModalOuvert(false)} centered>
        <Modal.Header closeButton={!enCours}>
          <Modal.Title as="h6">Confirmer la deconnexion</Modal.Title>
        </Modal.Header>
        <Modal.Body>Voulez-vous vraiment vous deconnecter du Portail Justificatif d'Apurement ?</Modal.Body>
        <Modal.Footer>
          <Button variant="falcon-default" onClick={() => setModalOuvert(false)} disabled={enCours}>Annuler</Button>
          <Button variant="primary" onClick={onConfirmerDeconnexion} disabled={enCours}>
            {enCours ? 'Deconnexion...' : 'Se deconnecter'}
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  )
}
