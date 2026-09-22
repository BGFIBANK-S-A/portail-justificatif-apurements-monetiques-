import axios from 'axios'

const ACCESS_KEY = 'apurement_access'
const REFRESH_KEY = 'apurement_refresh'

export const tokens = {
  get access() { return localStorage.getItem(ACCESS_KEY) },
  get refresh() { return localStorage.getItem(REFRESH_KEY) },
  set(access, refresh) {
    localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const access = tokens.access
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

let rafraichissementEnCours = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const requeteOriginale = error.config
    const estRouteAuth = requeteOriginale?.url?.startsWith('/auth/')
    if (error.response?.status === 401 && !requeteOriginale._retry && !estRouteAuth && tokens.refresh) {
      requeteOriginale._retry = true
      try {
        if (!rafraichissementEnCours) {
          rafraichissementEnCours = axios
            .post('/api/auth/token/refresh/', { refresh: tokens.refresh })
            .then((res) => {
              tokens.set(res.data.access)
              return res.data.access
            })
            .finally(() => { rafraichissementEnCours = null })
        }
        const nouvelAccess = await rafraichissementEnCours
        requeteOriginale.headers.Authorization = `Bearer ${nouvelAccess}`
        return api(requeteOriginale)
      } catch {
        tokens.clear()
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

export default api
