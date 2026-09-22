import { Card, Col, Container, Row } from 'react-bootstrap'

export default function AuthCard({ children }) {
  return (
    <Container fluid className="min-vh-100-auth d-flex align-items-center justify-content-center py-5" style={{ background: '#eef2f7' }}>
      <Row className="w-100 justify-content-center">
        <Col xs={11} sm={9} md={7} lg={5} xl={4}>
          <Card className="overflow-hidden">
            <div className="auth-header-bande">
              <div className="auth-logo-badge">
                <img src="/BGFI_logo.png" alt="BGFIBank" />
              </div>
              <div className="fw-bolder fs-4">BGFIBank</div>
              <div className="fs-10 opacity-75">Portail Justificatif d'Apurement</div>
            </div>
            <Card.Body className="auth-card-corps p-4 p-sm-5">
              {children}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}
