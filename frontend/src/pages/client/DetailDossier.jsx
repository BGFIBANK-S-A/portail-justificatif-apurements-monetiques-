import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, Form, Row, Table } from 'react-bootstrap'
import api from '../../api/client'
import MiseEnPage from '../../components/MiseEnPage'
import Badge from '../../components/Badge'
import ChampFichier from '../../components/ChampFichier'
import { ouvrirDocument } from '../../utils/documents'

function formatMontant(m) {
  return new Intl.NumberFormat('fr-FR').format(m || 0)
}
function formatDate(d) {
  return d ? new Date(d).toLocaleDateString('fr-FR') : '-'
}

const TYPES_DOC_VOYAGE = [
  { cle: 'passeport', libelle: 'Passeport', obligatoire: true },
  { cle: 'billet_aller', libelle: "Billet aller", obligatoire: 'alternatif' },
  { cle: 'billet_retour', libelle: 'Billet retour', obligatoire: 'alternatif' },
  { cle: 'visa', libelle: 'Visa', obligatoire: false },
  { cle: 'autre_justificatif', libelle: 'Autre justificatif', obligatoire: false },
]

function EtiquetteObligation({ obligatoire }) {
  if (obligatoire === true) return <span className="badge badge-subtle-danger">Obligatoire</span>
  if (obligatoire === 'alternatif') return <span className="badge badge-subtle-warning">Obligatoire (aller ou retour)</span>
  return <span className="badge badge-subtle-secondary">Optionnel</span>
}

const TYPES_JUSTIF_LIGNE = [
  { cle: 'facture_proforma', libelle: 'Facture proforma' },
  { cle: 'contrat', libelle: 'Contrat' },
  { cle: 'justificatif_scolarite', libelle: 'Justificatif de scolarite' },
  { cle: 'justificatif_sante', libelle: 'Justificatif medical / sante' },
  { cle: 'justificatif_hotel', libelle: 'Reservation hotel' },
  { cle: 'justificatif', libelle: 'Autre justificatif' },
]

function ChampJustificatifLigne({ ligne, typeDossier, typeChoisi, onChangerType }) {
  return (
    <div className="d-flex flex-wrap gap-2 align-items-center">
      {typeDossier === 'ligne' && (
        <Form.Select
          size="sm" style={{ width: 'auto' }}
          name={`type_justif_${ligne.id}`}
          value={typeChoisi || 'justificatif'}
          onChange={(e) => onChangerType(ligne.id, e.target.value)}
        >
          {TYPES_JUSTIF_LIGNE.map((t) => <option key={t.cle} value={t.cle}>{t.libelle}</option>)}
        </Form.Select>
      )}
      <ChampFichier name={`justif_${ligne.id}`} accept=".png,.jpg,.jpeg,.pdf" variante="lien" texte="Joindre un fichier" />
    </div>
  )
}

export default function DetailDossier() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [dossier, setDossier] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [envoiEnCours, setEnvoiEnCours] = useState(null)
  const [dateAller, setDateAller] = useState('')
  const [dateRetour, setDateRetour] = useState('')
  const [typesJustifLigne, setTypesJustifLigne] = useState({})

  function charger() {
    api.get(`/dossier/${id}/`).then((res) => setDossier(res.data)).catch(() => setErreur('Dossier introuvable.'))
  }

  useEffect(() => { charger() }, [id])

  function docParType(type) {
    return dossier.documents.find((d) => d.type_document === type && !d.ligne)
  }

  async function onVoirDocument(docId) {
    try {
      await ouvrirDocument(docId)
    } catch {
      setErreur("Impossible d'ouvrir ce document.")
    }
  }

  async function onUpload(type, fichier) {
    if (!fichier) return
    const form = new FormData()
    form.append('type_document', type)
    form.append('file', fichier)
    setEnvoiEnCours(type)
    try {
      await api.post(`/dossier/${id}/upload/`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      charger()
    } catch (err) {
      setErreur(err.response?.data?.erreur || "Erreur lors de l'envoi.")
    } finally {
      setEnvoiEnCours(null)
    }
  }

  async function onJustifierLignes(e) {
    e.preventDefault()
    const form = new FormData(e.target)
    if (dateAller) form.append('date_aller_manuelle', dateAller)
    if (dateRetour) form.append('date_retour_manuelle', dateRetour)
    setEnvoiEnCours('lignes')
    try {
      await api.post(`/dossier/${id}/justifier/`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      charger()
    } catch (err) {
      setErreur(err.response?.data?.detail || "Erreur lors de l'envoi.")
    } finally {
      setEnvoiEnCours(null)
    }
  }

  async function onAnnuler() {
    if (!confirm('Supprimer ce dossier ?')) return
    await api.post(`/dossier/${id}/annuler/`)
    navigate('/dashboard')
  }

  if (erreur && !dossier) return <MiseEnPage><Alert variant="danger">{erreur}</Alert></MiseEnPage>
  if (!dossier) return <MiseEnPage>Chargement...</MiseEnPage>

  const modifiable = dossier.modifiable
  const dateVoyageConnue = dossier.date_debut_voyage && dossier.date_fin_voyage
  const peutAnnuler = dossier.lignes.length === 0 && dossier.documents.length === 0

  return (
    <MiseEnPage titre={dossier.reference}>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <h2 className="mb-0">{dossier.reference} <Badge statut={dossier.statut} /></h2>
        {peutAnnuler && <Button variant="outline-danger" size="sm" onClick={onAnnuler}>Supprimer ce dossier</Button>}
      </div>

      {erreur && <Alert variant="danger">{erreur}</Alert>}

      {dossier.preuve_voyage_manquante && (
        <Alert variant="warning">
          Votre carte a effectue une transaction hors de la zone CEMAC, nous avons besoin d'une preuve de voyage
          (passeport et billet d'avion) pour instruire ce dossier.
        </Alert>
      )}

      <Card className="mb-4">
        <Card.Header><h5 className="mb-0">Informations</h5></Card.Header>
        <Card.Body>
          <p>Type : {dossier.type_dossier === 'voyage' ? 'Voyage' : 'Paiement en ligne'}</p>
          <p>Montant a justifier : {formatMontant(dossier.montant)} XAF (deja justifie : {formatMontant(dossier.montant_justifie)} XAF)</p>
          {dossier.jours_restants !== null && <p>Delai restant pour la justification : {dossier.jours_restants} jour(s)</p>}
          <p className="text-body-secondary fs-10">
            {dossier.type_dossier === 'voyage'
              ? "Seule la part de vos operations hors CEMAC qui depasse 5 000 000 FCFA par voyage doit etre justifiee, dans un delai de 30 jours a compter de la 1ere operation."
              : "Seule la part de vos paiements en ligne qui depasse 1 000 000 FCFA par mois doit etre justifiee, dans un delai de 30 jours a compter de la 1ere operation."}
          </p>
          {dossier.commentaire_admin && <p className="mb-0"><strong>Commentaire de la banque :</strong> {dossier.commentaire_admin}</p>}
        </Card.Body>
      </Card>

      {dossier.type_dossier === 'voyage' && (
        <Card className="mb-4">
          <Card.Header><h5 className="mb-0">Documents de voyage</h5></Card.Header>
          <Card.Body>
            <p className="text-body-secondary fs-10">
              Conformement a la reglementation (LC BEAC 004/GR/2022), le passeport est obligatoire ainsi qu'au moins un des billets (aller ou retour). Le visa et les autres justificatifs sont optionnels.
            </p>
            {!dateVoyageConnue && modifiable && (
              <p className="text-body-secondary fs-10">
                Les dates de votre voyage seront detectees automatiquement depuis vos billets, ou vous pouvez les saisir manuellement ci-dessous.
              </p>
            )}
            <Row className="g-3">
              {TYPES_DOC_VOYAGE.map(({ cle, libelle, obligatoire }) => {
                const doc = docParType(cle)
                return (
                  <Col xs={12} sm={6} lg={4} key={cle}>
                    <div className="upload-tile">
                      <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
                        <div className="fw-semibold fs-10">{libelle}</div>
                        <EtiquetteObligation obligatoire={obligatoire} />
                      </div>
                      {doc ? (
                        <div className="fs-10">
                          <button type="button" className="btn btn-link p-0 align-baseline" onClick={() => onVoirDocument(doc.id)}>{doc.nom_fichier}</button>
                          <div className="mt-1"><Badge statut={doc.statut} /></div>
                          {doc.motif_refus && <div className="text-danger">{doc.motif_refus}</div>}
                        </div>
                      ) : (
                        <span className="text-body-secondary fs-10">Aucun document</span>
                      )}
                      {modifiable && (
                        <div className="mt-2">
                          <ChampFichier
                            name={cle} accept=".png,.jpg,.jpeg,.pdf" variante="zone"
                            texte={doc ? 'Remplacer' : 'Choisir un fichier'}
                            disabled={envoiEnCours === cle}
                            onChange={(fichier) => onUpload(cle, fichier)}
                          />
                        </div>
                      )}
                    </div>
                  </Col>
                )
              })}
            </Row>
          </Card.Body>
        </Card>
      )}

      {dossier.lignes.length > 0 && dossier.montant > 0 && (
        <Card>
          <Card.Header>
            <h5 className="mb-0">Vos transactions {dossier.type_dossier === 'ligne' ? 'du mois' : 'a justifier'}</h5>
            <p className="text-body-secondary fs-10 mb-0">
              {formatMontant(dossier.montant_justifie)} XAF justifie sur {formatMontant(dossier.montant)} XAF a justifier.
            </p>
            {dossier.type_dossier === 'ligne' && (
              <p className="text-body-secondary fs-10 mb-0">
                Un justificatif est <span className="badge badge-subtle-danger">Obligatoire</span> pour chaque transaction ; choisissez la nature qui correspond le mieux a la depense.
              </p>
            )}
          </Card.Header>
          <Form onSubmit={onJustifierLignes}>
            {dossier.type_dossier === 'voyage' && !dateVoyageConnue && modifiable && (
              <Row className="mx-0 px-3 pt-3 g-3">
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>Date de depart</Form.Label>
                    <Form.Control type="date" value={dateAller} onChange={(e) => setDateAller(e.target.value)} />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>Date de retour</Form.Label>
                    <Form.Control type="date" value={dateRetour} onChange={(e) => setDateRetour(e.target.value)} />
                  </Form.Group>
                </Col>
              </Row>
            )}

            <Card.Body className="p-0">
              <div className="d-md-none">
                {dossier.lignes.map((l) => (
                  <div key={l.id} className="p-3 border-bottom">
                    <div className="d-flex justify-content-between align-items-start mb-1">
                      <span className="fw-semibold">{l.libelle}</span>
                      <span className="fs-10 text-body-secondary text-nowrap ms-2">{formatDate(l.date_operation)}</span>
                    </div>
                    <div className="mb-2">{formatMontant(l.montant)} {l.devise}</div>
                    {l.est_justifiee ? (
                      <Badge statut="valide" />
                    ) : modifiable ? (
                      <ChampJustificatifLigne
                        ligne={l} typeDossier={dossier.type_dossier}
                        typeChoisi={typesJustifLigne[l.id]}
                        onChangerType={(idLigne, valeur) => setTypesJustifLigne({ ...typesJustifLigne, [idLigne]: valeur })}
                      />
                    ) : (
                      <span className="text-body-secondary fs-10">Non justifiee</span>
                    )}
                  </div>
                ))}
              </div>

              <div className="table-responsive d-none d-md-block">
                <Table hover className="mb-0">
                  <thead className="bg-body-tertiary">
                    <tr><th>Date</th><th>Libelle</th><th>Montant</th><th>Justificatif</th></tr>
                  </thead>
                  <tbody>
                    {dossier.lignes.map((l) => (
                      <tr key={l.id}>
                        <td className="text-nowrap">{formatDate(l.date_operation)}</td>
                        <td>{l.libelle}</td>
                        <td className="text-nowrap">{formatMontant(l.montant)} {l.devise}</td>
                        <td>
                          {l.est_justifiee ? (
                            <Badge statut="valide" />
                          ) : modifiable ? (
                            <ChampJustificatifLigne
                              ligne={l} typeDossier={dossier.type_dossier}
                              typeChoisi={typesJustifLigne[l.id]}
                              onChangerType={(idLigne, valeur) => setTypesJustifLigne({ ...typesJustifLigne, [idLigne]: valeur })}
                            />
                          ) : (
                            <span className="text-body-secondary">Non justifiee</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>

              {modifiable && (
                <div className="p-3">
                  <Button type="submit" disabled={envoiEnCours === 'lignes'}>
                    {envoiEnCours === 'lignes' ? 'Envoi...' : 'Envoyer les justificatifs'}
                  </Button>
                </div>
              )}
            </Card.Body>
          </Form>
        </Card>
      )}
    </MiseEnPage>
  )
}
