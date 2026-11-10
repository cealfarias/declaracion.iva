import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import axios from 'axios'

// Adjuntar JWT únicamente a solicitudes destinadas a nuestra API configurada.
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('iva_token')
  const target = new URL(config.url || '', config.baseURL || window.location.origin)
  const api = new URL(API_URL, window.location.origin)
  if (token && target.origin === api.origin && target.pathname.startsWith('/api/v1/')) {
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
