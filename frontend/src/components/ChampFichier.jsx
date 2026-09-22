import { useId, useState } from 'react'
import { FiPaperclip, FiUploadCloud } from 'react-icons/fi'

/* Champ fichier stylise : masque l'input natif (moche, "Browse..." non
   traduisible) au profit d'un declencheur personnalise, comme dans
   l'ancienne application Flask (input caché + <label> declencheur). */
export default function ChampFichier({ name, accept, onChange, disabled, variante = 'zone', texte, texteChoisi = 'Fichier selectionne' }) {
  const id = useId()
  const [nomFichier, setNomFichier] = useState(null)

  function onFileChange(e) {
    const fichier = e.target.files[0] || null
    setNomFichier(fichier ? fichier.name : null)
    onChange?.(fichier)
  }

  if (variante === 'lien') {
    return (
      <>
        <label htmlFor={id} className="d-inline-flex align-items-center gap-1 fs-10 text-primary cursor-pointer mb-0">
          <FiPaperclip />{nomFichier || texte || 'Joindre un fichier'}
        </label>
        <input type="file" id={id} name={name} accept={accept} className="d-none" disabled={disabled} onChange={onFileChange} />
      </>
    )
  }

  return (
    <label htmlFor={id} className={`zone-depot d-block mb-0 ${disabled ? 'opacity-50' : 'cursor-pointer'}`}>
      <input type="file" id={id} name={name} accept={accept} className="d-none" disabled={disabled} onChange={onFileChange} />
      <FiUploadCloud size={22} className="text-primary mb-1" />
      {nomFichier ? (
        <div className="fw-semibold text-body-emphasis fs-10 text-truncate">{nomFichier}</div>
      ) : (
        <div className="fs-10 fw-semibold">{texte || 'Choisir un fichier'}</div>
      )}
    </label>
  )
}
