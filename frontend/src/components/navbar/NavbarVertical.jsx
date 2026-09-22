import { Nav, Navbar } from 'react-bootstrap'
import { NavLink } from 'react-router-dom'
import Flex from '../common/Flex'
import { navItemsPourRole } from '../../routes/navConfig'
import { useAuth } from '../../context/AuthContext'

export default function NavbarVertical({ ouvert, onToggle }) {
  const { utilisateur } = useAuth()
  const items = navItemsPourRole(utilisateur?.role)

  return (
    <Navbar expand="xl" expanded={ouvert} onToggle={onToggle} className="navbar-vertical" variant="light">
      <Flex alignItems="center">
        <Navbar.Brand as={NavLink} to="/" className="navbar-brand text-left">
          <div className="d-flex align-items-center py-3">
            <img className="me-1" alt="BGFIBank" width={26} src="/BGFI_logo.png" />
            <span className="font-sans-serif text-primary fw-bold">BGFIBank</span>
          </div>
        </Navbar.Brand>
      </Flex>
      <Navbar.Collapse id="navbar-vertical-collapse">
        <div className="navbar-vertical-content scrollbar">
          <Nav className="flex-column" as="ul">
            {items.map(({ to, label, icon: Icon }) => (
              <Nav.Item as="li" key={to}>
                <Nav.Link as={NavLink} to={to} end onClick={() => onToggle(false)}>
                  <Flex alignItems="center">
                    <span className="nav-link-icon">
                      <Icon />
                    </span>
                    <span className="nav-link-text ps-1">{label}</span>
                  </Flex>
                </Nav.Link>
              </Nav.Item>
            ))}
          </Nav>
        </div>
      </Navbar.Collapse>
    </Navbar>
  )
}
