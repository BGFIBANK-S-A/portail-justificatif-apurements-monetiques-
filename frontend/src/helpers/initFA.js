// Enregistrement minimal de FontAwesome (uniquement les icones utilisees
// par les composants Falcon portes tels quels depuis docuflow_IA, ex.
// AdvanceTableSearchBox). Le reste de l'application utilise react-icons.
import { library } from '@fortawesome/fontawesome-svg-core'
import { faSearch } from '@fortawesome/free-solid-svg-icons'

library.add(faSearch)
