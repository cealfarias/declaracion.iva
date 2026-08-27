import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { GoogleLogin } from '@react-oauth/google';
import bgIva from '../assets/bg-iva.png'; // Importamos la imagen de fondo

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/api/v1/auth/google`, {
        token: credentialResponse.credential
      });
      
      if (response.data.access_token) {
        login(response.data.access_token, { 
          nombre: response.data.nombre, 
          id: response.data.id,
          terminos_aceptados: response.data.terminos_aceptados 
        });
        navigate('/dashboard');
      }
    } catch (err) {
      if (err.response?.status === 404) {
        navigate('/registro');
      } else {
        setError(err.response?.data?.detail || 'Error al autenticar con Google.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/api/v1/auth/login`, {
        email,
        password
      });

      if (response.data.access_token) {
        login(response.data.access_token, { 
          nombre: response.data.nombre, 
          id: response.data.id,
          terminos_aceptados: response.data.terminos_aceptados 
        });
        navigate('/dashboard');
      }
    } catch (err) {
      if (err.response?.status === 401 && err.response.data.detail.includes("registrado")) {
        navigate('/registro');
      } else {
        setError(err.response?.data?.detail || 'Error al iniciar sesión. Verifica tus credenciales.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-white">
      {/* Panel Izquierdo - Imagen y Frases (Oculto en móviles) */}
      <div className="hidden lg:flex lg:w-1/2 relative">
        <div className="absolute inset-0 bg-slate-900/20 z-10"></div>
        <img 
          src={bgIva} 
          alt="Declaración de IVA" 
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="relative z-20 flex flex-col justify-center p-8 lg:p-12 text-white">
          <div className="bg-slate-900/30 p-6 rounded-2xl backdrop-blur-md border border-white/20 shadow-2xl max-w-lg">
            <h1 className="text-2xl lg:text-3xl font-extrabold mb-3 tracking-tight">Cumplimiento Tributario Simplificado</h1>
            <p className="text-sm lg:text-base text-indigo-100 mb-5 leading-relaxed">
              Genera tus Anexos F-07 (Compras, Ventas a Contribuyentes y Consumidor Final) de manera automática a partir de tus archivos DTE.
            </p>
            
            <ul className="space-y-3">
              <li className="flex items-start">
                <svg className="w-5 h-5 text-indigo-300 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <span className="text-indigo-50 text-sm font-medium">Extrae datos precisos con base en la normativa del Ministerio de Hacienda.</span>
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-indigo-300 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <span className="text-indigo-50 text-sm font-medium">Optimiza tu tiempo de horas a segundos.</span>
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-indigo-300 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <span className="text-indigo-50 text-sm font-medium">Sistema Multi-Empresa para control de múltiples clientes.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Panel Derecho - Formulario de Login */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-slate-50">
        <div className="max-w-md w-full">
          <div className="text-center mb-10">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-100 text-indigo-600 mb-4 shadow-sm border border-indigo-200">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-slate-800">Iniciar Sesión</h2>
            <p className="text-slate-500 mt-2 font-medium">Accede a tu cuenta para continuar</p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm mb-6 border border-red-200 shadow-sm flex items-start">
              <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Correo Electrónico</label>
              <input 
                type="email" 
                required
                className="w-full px-4 py-3 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all shadow-sm"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@correo.com"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Contraseña</label>
              <input 
                type="password" 
                required
                className="w-full px-4 py-3 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all shadow-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-indigo-600 text-white font-semibold py-3 rounded-lg hover:bg-indigo-700 hover:shadow-md focus:ring-4 focus:ring-indigo-200 transition-all disabled:opacity-70 mt-4"
            >
              {loading ? 'Ingresando...' : 'Ingresar al Sistema'}
            </button>
          </form>

          <div className="mt-8 flex items-center justify-center space-x-4">
            <div className="h-px bg-slate-300 flex-1"></div>
            <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">o ingresar con</span>
            <div className="h-px bg-slate-300 flex-1"></div>
          </div>

          <div className="mt-8 flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => {
                setError('Falló la conexión con Google');
              }}
              theme="outline"
              size="large"
              shape="pill"
              width="100%"
            />
          </div>

          <p className="text-center text-sm text-slate-600 mt-10">
            ¿No tienes cuenta? <Link to="/registro" className="text-indigo-600 font-bold hover:underline">Regístrate aquí</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
