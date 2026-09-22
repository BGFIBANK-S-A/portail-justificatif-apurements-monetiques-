import { useId, useState } from 'react'
import { Alert, Button, Card, Col, ProgressBar, Row } from 'react-bootstrap'
import { FiFileText, FiUsers, FiUploadCloud } from 'react-icons/fi'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'

function ZoneDepotFichier({ id, fichier, onChange, accept }) {
  return (
    <label htmlFor={id} className="zone-depot d-block mb-0 cursor-pointer">
      <input type="file" id={id} accept={accept} className="d-none" onChange={(e) => onChange(e.target.files[0] || null)} />
      <FiUploadCloud size={24} className="text-primary mb-2" />
      {fichier ? (
        <div className="fw-semibold text-body-emphasis fs-10 text-truncate">{fichier.name}</div>
      ) : (
        <>
          <div className="fw-semibold fs-10">Cliquez pour choisir un fichier</div>
          <div className="text-body-secondary fs-10">Formats acceptes : .xlsx, .xls, .csv</div>
        </>
      )}
    </label>
  )
}

function StatTuile({ libelle, valeur }) {
  return (
    <div className="stat-tuile">
      <div className="fw-bold">{valeur}</div>
      <div className="fs-10 text-body-secondary">{libelle}</div>
    </div>
  )
}

export default function AdminImport() {
  const idFichier = useId()
  const idPortefeuille = useId()
  const [fichier, setFichier] = useState(null)
  const [portefeuille, setPortefeuille] = useState(null)
  const [enCoursFichier, setEnCoursFichier] = useState(false)
  const [enCoursPortefeuille, setEnCoursPortefeuille] = useState(false)
  const [resumeFichier, setResumeFichier] = useState(null)
  const [resumePortefeuille, setResumePortefeuille] = useState(null)
  const [erreurFichier, setErreurFichier] = useState(null)
  const [erreurPortefeuille, setErreurPortefeuille] = useState(null)

  async function onImporterFichier() {
    if (!fichier) return
    setEnCoursFichier(true)
    setErreurFichier(null)
    setResumeFichier(null)
    const form = new FormData()
    form.append('fichier', fichier)
    try {
      const res = await api.post('/admin/import/fichier/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      setResumeFichier(res.data)
    } catch (err) {
      setErreurFichier(err.response?.data?.erreur || "Erreur lors de l'import.")
    } finally {
      setEnCoursFichier(false)
    }
  }

  async function onImporterPortefeuille() {
    if (!portefeuille) return
    setEnCoursPortefeuille(true)
    setErreurPortefeuille(null)
    setResumePortefeuille(null)
    const form = new FormData()
    form.append('fichier', portefeuille)
    try {
      const res = await api.post('/admin/import/portefeuille/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      setResumePortefeuille(res.data)
    } catch (err) {
      setErreurPortefeuille(err.response?.data?.erreur || "Erreur lors de l'import.")
    } finally {
      setEnCoursPortefeuille(false)
    }
  }

  return (
    <MiseEnPage titre="Import de fichiers">
      <h2 className="mb-4">Import de fichiers</h2>

      <Row className="g-3">
        <Col md={6}>
          <Card className="carte-accent h-100">
            <Card.Header>
              <div className="d-flex align-items-center gap-2">
                <span className="icone-carte"><FiFileText /></span>
                <div>
                  <h5 className="mb-0">Fichier journalier de transactions</h5>
                  <div className="fs-10 text-body-secondary">Depassements voyage et paiement en ligne</div>
                </div>
              </div>
            </Card.Header>
            <Card.Body>
              <ZoneDepotFichier id={idFichier} fichier={fichier} onChange={setFichier} accept=".xlsx,.xls,.csv" />
              {enCoursFichier && <ProgressBar animated now={100} className="mt-3" />}
              {erreurFichier && <Alert variant="danger" className="mt-3 mb-0">{erreurFichier}</Alert>}
              {resumeFichier && (
                <div className="mt-3">
                  <Row className="g-2 mb-2">
                    <Col xs={6} md={4}><StatTuile libelle="Lignes lues" valeur={resumeFichier.lignes_lues} /></Col>
                    <Col xs={6} md={4}><StatTuile libelle="Lignes importees" valeur={resumeFichier.lignes} /></Col>
                    <Col xs={6} md={4}><StatTuile libelle="Dossiers crees" valeur={resumeFichier.dossiers_crees} /></Col>
                    <Col xs={6} md={4}><StatTuile libelle="Dossiers actualises" valeur={resumeFichier.dossiers_actualises} /></Col>
                    <Col xs={6} md={4}><StatTuile libelle="Comptes crees" valeur={resumeFichier.comptes_crees} /></Col>
                    <Col xs={6} md={4}><StatTuile libelle="Doublons ignores" valeur={resumeFichier.lignes_doublons} /></Col>
                  </Row>
                  {resumeFichier.a_notifier?.length > 0 && (
                    <p className="fs-10 text-body-secondary mb-0">{resumeFichier.a_notifier.length} client(s) a notifier.</p>
                  )}
                </div>
              )}
              <Button variant="primary" className="w-100 mt-3" disabled={!fichier || enCoursFichier} onClick={onImporterFichier}>
                {enCoursFichier ? 'Import en cours...' : 'Importer le fichier'}
              </Button>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          <Card className="carte-accent-violet h-100">
            <Card.Header>
              <div className="d-flex align-items-center gap-2">
                <span className="icone-carte icone-carte-violet"><FiUsers /></span>
                <div>
                  <h5 className="mb-0">Referentiel portefeuille</h5>
                  <div className="fs-10 text-body-secondary">Agence / Gestionnaire CRC / Client</div>
                </div>
              </div>
            </Card.Header>
            <Card.Body>
              <ZoneDepotFichier id={idPortefeuille} fichier={portefeuille} onChange={setPortefeuille} accept=".xlsx,.xls,.csv" />
              {enCoursPortefeuille && <ProgressBar animated now={100} className="mt-3" />}
              {erreurPortefeuille && <Alert variant="danger" className="mt-3 mb-0">{erreurPortefeuille}</Alert>}
              {resumePortefeuille && (
                <div className="mt-3">
                  <Row className="g-2 mb-2">
                    <Col xs={6} md={4}><StatTuile libelle="Agences creees" valeur={resumePortefeuille.agences_creees} /></Col>
                    <Col xs={6} md={4}><StatTuile libelle="CRC crees" valeur={resumePortefeuille.crc_crees} /></Col>
                    <Col xs={6} md={4}><StatTuile libelle="Clients relies" valeur={resumePortefeuille.clients_relies} /></Col>
                  </Row>
                  {resumePortefeuille.crc_a_completer?.length > 0 && (
                    <p className="fs-10 text-body-secondary mb-0">
                      {resumePortefeuille.crc_a_completer.length} compte(s) CRC cree(s) avec un email provisoire, a completer.
                    </p>
                  )}
                </div>
              )}
              <Button variant="primary" className="w-100 mt-3" disabled={!portefeuille || enCoursPortefeuille} onClick={onImporterPortefeuille}>
                {enCoursPortefeuille ? 'Import en cours...' : 'Importer le portefeuille'}
              </Button>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </MiseEnPage>
  )
}
