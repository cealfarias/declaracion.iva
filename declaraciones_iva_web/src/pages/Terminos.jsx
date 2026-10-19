import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import ReactMarkdown from 'react-markdown';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Terminos() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login } = useAuth();
  const [accepted, setAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [markdown, setMarkdown] = useState('');
  const [loadingTerms, setLoadingTerms] = useState(true);

  useEffect(() => {
    const url = window.location.hostname === 'localhost' 
      ? '/terminos.md' 
      : 'https://demiempresa.vercel.app/terminos.md';
      
    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error('No se pudo cargar los términos');
        return res.text();
      })
      .then(text => {
        setMarkdown(text);
        setLoadingTerms(false);
      })
      .catch(err => {
        console.error(err);
        setLoadingTerms(false);
      });
  }, []);

  const handleAccept = async () => {
    if (!accepted) return;
    setLoading(true);
    try {
      await axios.post(`${API_URL}/api/v1/auth/aceptar-terminos`, { usuario_id: user.id });
      // Update local storage and context
      const updatedUser = { ...user, terminos_aceptados: true };
      login(localStorage.getItem('iva_token'), updatedUser);
      navigate('/dashboard');
    } catch (error) {
      console.error("Error aceptando términos:", error);
      alert("Hubo un error al guardar tu aceptación. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8fafc', padding: '3rem 1rem' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto', backgroundColor: 'white', padding: '2rem', borderRadius: '1rem', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
        
        {loadingTerms ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
            Cargando términos centralizados...
          </div>
        ) : (
          <div className="prose prose-sm max-w-none" style={{ color: '#334155', lineHeight: '1.6', marginBottom: '2rem' }}>
            <ReactMarkdown>{markdown}</ReactMarkdown>
          </div>
        )}

        {user && !user.terminos_aceptados && (
          <div style={{ marginTop: '3rem', borderTop: '1px solid #e2e8f0', paddingTop: '2rem' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', cursor: 'pointer' }}>
              <input 
                type="checkbox" 
                checked={accepted} 
                onChange={(e) => setAccepted(e.target.checked)}
                style={{ marginTop: '0.25rem', width: '1.25rem', height: '1.25rem' }}
              />
              <span style={{ fontSize: '1rem', color: '#1e293b', fontWeight: '500' }}>
                He leído, comprendido y acepto en su totalidad los Términos de Referencia y Condiciones de Servicio.
              </span>
            </label>
            
            <button 
              onClick={handleAccept}
              disabled={!accepted || loading}
              style={{ 
                marginTop: '2rem', 
                width: '100%', 
                padding: '1rem', 
                backgroundColor: accepted ? '#0284c7' : '#94a3b8', 
                color: 'white', 
                fontWeight: 'bold', 
                borderRadius: '0.5rem', 
                cursor: accepted ? 'pointer' : 'not-allowed',
                border: 'none',
                transition: 'background-color 0.2s'
              }}
            >
              {loading ? 'Procesando...' : 'Aceptar Términos y Continuar'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
