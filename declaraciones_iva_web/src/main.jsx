import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import axios from 'axios'

// Añadir la sesión a las llamadas API del cliente, sin registrar el token.
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('iva_token')
  if (token && !config.headers?.Authorization) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
