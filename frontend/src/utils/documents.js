import api from '../api/client'

/* Ouvre une piece justificative dans un nouvel onglet. L'API de documents
   exige un jeton JWT (Authorization: Bearer ...), qui n'est jamais envoye
   par une navigation de navigateur classique (<a href> direct vers la
   route de l'API) : un lien direct vers /api/document/<id>/ echoue donc
   toujours (401). On recupere le fichier via le client API authentifie,
   puis on l'ouvre depuis un URL objet local (jamais de route directe ni
   de chemin de stockage expose au navigateur). */
export async function ouvrirDocument(id) {
  const reponse = await api.get(`/document/${id}/`, { responseType: 'blob' })
  const url = URL.createObjectURL(reponse.data)
  window.open(url, '_blank', 'noopener')
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}
