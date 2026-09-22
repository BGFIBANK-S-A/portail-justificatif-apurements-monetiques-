import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, Form, Row, Table } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import { ouvrirDocument } from '../../utils/documents'

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}
function formatDate(d) {
  return d ? new Date(d).toLocaleDateString('fr-FR') : '-'
}

const LIBELLES_TYPE_DOCUMENT = {
  passeport: 'Passeport',
  billet_aller: 'Billet aller',
  billet_retour: 'Billet retour',
  visa: 'Visa',
  autre_justificatif: 'Autre justificatif',
  facture_proforma: 'Facture proforma',
  contrat: 'Contrat',
  justificatif_scolarite: 'Justificatif de scolarite',
  justificatif_sante: 'Justificatif medical / sante',
  justificatif_hotel: 'Reservation hotel',
  justificatif: 'Autre justificatif',
}

const OBLIGATION_TYPE_DOCUMENT_VOYAGE = {
  passeport: true,
  billet_aller: 'alternatif',
  billet_retour: 'alternatif',
  visa: false,
  autre_justificatif: false,
}

function EtiquetteObligation({ obligatoire }) {
  if (obligatoire === true) return <span className="badge-pastel badge-pastel-rouge">Obligatoire</span>
  if (obligatoire === 'alternatif') return <span className="badge-pastel badge-pastel-orange">Obligatoire (aller ou retour)</span>
  return <span className="badge-pastel badge-pastel-gris">Optionnel</span>
}

export default function AdminDetailDossier() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [dossier, setDossier] = useState(null)
  const [commentaire, setCommentaire] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  function charger() {
    api.get(`/admin/dossier/${id}/`).then((res) => setDossier(res.data)).catch(() => setErreur('Dossier introuvable.'))
  }

  useEffect(() => { charger() }, [id])

  async function onVoirDocument(docId) {
    try {
      await ouvrirDocument(docId)
    } catch {
      setErreur("Impossible d'ouvrir ce document.")
    }
  }

  async function onDecision(action) {
    if ((action === 'refuser' || action === 'demander_complement') && !commentaire.trim()) {
      setErreur('Un motif est obligatoire pour cette action.')
      return
    }
    setEnvoi(true)
    setErreur(null)
    try {
      await api.post(`/admin/dossier/${id}/decision/`, { action, commentaire })
      charger()
      setCommentaire('')
    } catch (err) {
      setErreur(err.response?.data?.detail || 'Erreur.')
    } finally {
      setEnvoi(false)
    }
  }

  async function onDecisionDocument(docId, valider) {
    const motif = valider ? undefined : prompt('Motif du refus :')
    if (!valider && !motif) return
    await api.post(`/admin/document/${docId}/decision/`, { action: valider ? 'valider' : 'refuser', motif_refus: motif })
    charger()
  }

  async function onSupprimer() {
    if (!confirm('Supprimer definitivement ce dossier ?')) return
    await api.post(`/admin/dossier/${id}/supprimer/`)
    navigate('/admin/dashboard')
  }

  if (erreur && !dossier) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!dossier) return <MiseEnPage>Chargement...</MiseEnPage>

  const cloture = dossier.statut === 'valide' || dossier.statut === 'refuse'

  return (
    <MiseEnPage>
      <h2 className="mb-3">{dossier.reference} <Badge statut={dossier.statut} /></h2>
      {erreur && <Alert variant="danger">{erreur}</Alert>}

      {dossier.incoherences?.length > 0 && (
        <Alert variant="warning">
          <strong>Incoherences detectees :</strong>
          <ul className="mb-0 mt-1">
            {dossier.incoherences.map((inc, i) => <li key={i}>{inc}</li>)}
          </ul>
        </Alert>
      )}

      <Row className="g-3">
        <Col lg={4}>
          <Card className="carte-kpi mb-3">
            <Card.Header className="bg-transparent"><h5 className="mb-0">Client</h5></Card.Header>
            <Card.Body>
              <p>{dossier.client.prenom} {dossier.client.nom}<br /><span className="text-body-secondary fs-10">{dossier.client.email}</span></p>
              <p className="mb-1">Type : {dossier.type_dossier === 'voyage' ? 'Voyage' : 'Paiement en ligne'}</p>
              <p className="mb-1">Periode : {dossier.periode || '-'}</p>
              <p className="mb-1">Montant a justifier : {formatMontant(dossier.montant)} XAF</p>
              <p className="mb-1">Deja justifie : {formatMontant(dossier.montant_justifie)} XAF</p>
              {dossier.jours_restants !== null && <p className="mb-1">Delai restant : {dossier.jours_restants} jour(s)</p>}
              {dossier.date_debut_voyage && <p className="mb-1">Voyage : {formatDate(dossier.date_debut_voyage)} - {formatDate(dossier.date_fin_voyage)}</p>}
              <p className="text-body-secondary fs-10 mb-0">
                {dossier.type_dossier === 'voyage'
                  ? "Seuil reglementaire : 5 000 000 FCFA par voyage (au-dela, justification obligatoire), delai de 30 jours a compter de la 1ere operation."
                  : "Seuil reglementaire : 1 000 000 FCFA par mois (au-dela, justification obligatoire), delai de 30 jours a compter de la 1ere operation."}
              </p>
            </Card.Body>
          </Card>

          {!cloture && (
            <Card className="carte-kpi mb-3">
              <Card.Header className="bg-transparent"><h5 className="mb-0">Decision</h5></Card.Header>
              <Card.Body>
                <Form.Group className="mb-3">
                  <Form.Label className="fs-10">Commentaire (obligatoire pour refuser / demander un complement)</Form.Label>
                  <Form.Control as="textarea" rows={3} value={commentaire} onChange={(e) => setCommentaire(e.target.value)} />
                </Form.Group>
                <div className="d-flex gap-2 flex-wrap">
                  <Button variant="falcon-default" size="sm" disabled={envoi} onClick={() => onDecision('prendre_en_charge')}>Prendre en charge</Button>
                  <Button variant="success" size="sm" disabled={envoi} onClick={() => onDecision('valider')}>Valider</Button>
                  <Button variant="danger" size="sm" disabled={envoi} onClick={() => onDecision('refuser')}>Refuser</Button>
                  <Button variant="falcon-default" size="sm" disabled={envoi} onClick={() => onDecision('demander_complement')}>Demander un complement</Button>
                </div>
              </Card.Body>
            </Card>
          )}

          {dossier.historique?.length > 0 && (
            <Card className="carte-kpi mb-3">
              <Card.Header className="bg-transparent"><h5 className="mb-0">Historique</h5></Card.Header>
              <Card.Body>
                <ul className="fs-10 mb-0 ps-3">
                  {dossier.historique.map((h) => (
                    <li key={h.id}>{new Date(h.date_evenement).toLocaleString('fr-FR')} — {h.description}</li>
                  ))}
                </ul>
              </Card.Body>
            </Card>
          )}

          <Button variant="outline-danger" size="sm" onClick={onSupprimer}>Supprimer ce dossier</Button>
        </Col>

        <Col lg={8}>
          <Card className="carte-kpi mb-3">
            <Card.Header className="bg-transparent">
              <h5 className="mb-0">Documents a valider</h5>
              {dossier.type_dossier === 'voyage' && (
                <p className="text-body-secondary fs-10 mb-0">
                  Conformement a la reglementation (LC BEAC 004/GR/2022), le passeport est obligatoire ainsi qu'au moins un des billets (aller ou retour). Le visa et les autres justificatifs sont optionnels.
                </p>
              )}
            </Card.Header>
            <Card.Body className="p-0">
              <Table responsive className="mb-0">
                <thead className="bg-body-tertiary"><tr><th>Type</th><th>Obligation</th><th>Fichier</th><th>Statut</th><th></th></tr></thead>
                <tbody>
                  {dossier.documents.map((d) => (
                    <tr key={d.id}>
                      <td>{LIBELLES_TYPE_DOCUMENT[d.type_document] || d.type_document}</td>
                      <td>
                        {dossier.type_dossier === 'voyage' ? (
                          <EtiquetteObligation obligatoire={OBLIGATION_TYPE_DOCUMENT_VOYAGE[d.type_document]} />
                        ) : (
                          <EtiquetteObligation obligatoire={true} />
                        )}
                      </td>
                      <td><Button variant="link" className="p-0 align-baseline" onClick={() => onVoirDocument(d.id)}>{d.nom_fichier}</Button></td>
                      <td><Badge statut={d.statut} />{d.motif_refus && <div className="fs-10 text-danger">{d.motif_refus}</div>}</td>
                      <td className="text-nowrap">
                        {!cloture && d.statut !== 'valide' && <Button size="sm" variant="outline-success" onClick={() => onDecisionDocument(d.id, true)}>Valider</Button>}
                        {!cloture && d.statut !== 'refuse' && <Button size="sm" variant="outline-danger" className="ms-2" onClick={() => onDecisionDocument(d.id, false)}>Refuser</Button>}
                      </td>
                    </tr>
                  ))}
                  {dossier.documents.length === 0 && <tr><td colSpan={5} className="text-body-secondary">Aucun document.</td></tr>}
                </tbody>
              </Table>
            </Card.Body>
          </Card>

          <Card className="carte-kpi mb-3">
            <Card.Header className="bg-transparent"><h5 className="mb-0">Transactions</h5></Card.Header>
            <Card.Body className="p-0">
              <Table responsive className="mb-0">
                <thead className="bg-body-tertiary"><tr><th>Date</th><th>Libelle</th><th>Montant</th><th>Justifiee</th></tr></thead>
                <tbody>
                  {dossier.lignes.map((l) => (
                    <tr key={l.id}>
                      <td>{formatDate(l.date_operation)}</td>
                      <td>{l.libelle}</td>
                      <td>{formatMontant(l.montant)} {l.devise}</td>
                      <td>{l.est_justifiee ? <Badge statut="valide" /> : <Badge statut="incomplet" />}</td>
                    </tr>
                  ))}
                  {dossier.lignes.length === 0 && <tr><td colSpan={4} className="text-body-secondary">Aucune transaction.</td></tr>}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </MiseEnPage>
  )
}
