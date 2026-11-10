import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { GoogleLogin } from '@react-oauth/google';
import { useAssistant } from '../contexts/AssistantContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Registro() {
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    password: '',
    razon_social: '',
    nit: '',
    nrc: '',
    aceptaTerminos: false
  });
  
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { enqueueMessages } = useAssistant();

  const handleRegister = async (e) => {
    e.preventDefault();

    if (!formData.aceptaTerminos) {
      enqueueMessages([{ text: "Debes aceptar los Términos de Referencia para continuar.", type: "error" }]);
      return;
    }

    setLoading(true);

    try {
      await axios.post(`${API_URL}/api/v1/auth/register`, {
        nombre: formData.nombre,
        email: formData.email,
        password: formData.password || "google-auth-random-pass-xyz",
        razon_social: formData.razon_social,
        nit: formData.nit,
        nrc: formData.nrc,
        acepta_terminos: formData.aceptaTerminos
      });

      // Registro exitoso
      enqueueMessages([{ text: "¡Registro exitoso! Por favor inicia sesión.", type: "success" }]);
      navigate('/login');
    } catch (err) {
      const errorDetail = err.response?.data?.detail || 'Error al registrar usuario.';
      
      if (errorDetail.includes("correo ya está registrado")) {
        enqueueMessages([{ text: "Ese correo ya está registrado. Te voy a redirigir para que inicies sesión.", type: "info" }]);
        setTimeout(() => navigate('/login'), 2500);
      } else if (errorDetail.includes("NIT") || errorDetail.includes("NRC")) {
        enqueueMessages([{ text: `Parece que hay un problema: ${errorDetail} Verifica si ya tenías una cuenta.`, type: "error" }]);
      } else {
        enqueueMessages([{ text: errorDetail, type: "error" }]);
      }
    } finally {
      setLoading(false);
    }
  };

  const decodeJwt = (token) => {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      return JSON.parse(jsonPayload);
    } catch (e) {
      return {};
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    const payload = decodeJwt(credentialResponse.credential);
    if (payload.email) {
      setFormData({
        ...formData,
        nombre: payload.name || '',
        email: payload.email || '',
        password: 'google-auth-random-pass-xyz'
      });
      // Dejamos que el Avatar o el usuario maneje el siguiente paso
    } else {
      enqueueMessages([{ text: "No se pudo extraer la información de Google.", type: "error" }]);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl p-8 border border-slate-100">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-slate-900">Registro en el Sistema</h2>
          <p className="text-slate-500 mt-2 mb-6">Crea tu cuenta y registra tu empresa para emitir anexos F-07</p>
          
          <div className="flex justify-center mb-6">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => enqueueMessages([{ text: "No se pudo conectar con Google.", type: "error" }])}
              theme="outline"
              size="large"
              shape="pill"
            />
          </div>
          
          <div className="flex items-center justify-center space-x-4 mb-2">
            <div className="h-px bg-slate-200 flex-1"></div>
            <span className="text-sm text-slate-400">o ingresa tus datos manualmente</span>
            <div className="h-px bg-slate-200 flex-1"></div>
          </div>
        </div>

        <form onSubmit={handleRegister} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Datos del Usuario */}
            <div className="space-y-4">
              <h3 className="font-bold text-slate-800 border-b pb-2">1. Tus Datos</h3>
              
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Nombre Completo</label>
                <input 
                  type="text" required
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={formData.nombre}
                  onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Correo Electrónico</label>
                <input 
                  type="email" required
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Contraseña</label>
                <input 
                  type="password" required
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                />
              </div>
            </div>

            {/* Datos de la Empresa */}
            <div className="space-y-4">
              <h3 className="font-bold text-slate-800 border-b pb-2">2. Datos de Empresa</h3>
              
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Razón Social</label>
                <input 
                  type="text" required
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={formData.razon_social}
                  onChange={(e) => setFormData({...formData, razon_social: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">NIT</label>
                <input 
                  type="text" required
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={formData.nit}
                  onChange={(e) => setFormData({...formData, nit: e.target.value})}
                  placeholder="0000-000000-000-0"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">NRC</label>
                <input 
                  type="text" required
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={formData.nrc}
                  onChange={(e) => setFormData({...formData, nrc: e.target.value})}
                />
              </div>
            </div>
          </div>

          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 mt-6 flex items-start">
            <div className="flex items-center h-5">
              <input
                id="terminos"
                type="checkbox"
                className="w-4 h-4 text-indigo-600 bg-gray-100 border-gray-300 rounded focus:ring-indigo-500"
                checked={formData.aceptaTerminos}
                onChange={(e) => setFormData({...formData, aceptaTerminos: e.target.checked})}
              />
            </div>
            <label htmlFor="terminos" className="ml-3 text-sm text-slate-600">
              He leído y acepto los <Link to="/terminos" target="_blank" className="font-medium text-indigo-600 hover:underline">Términos de Referencia</Link> y la política de privacidad de la plataforma. Entiendo que los datos fiscales son de mi entera responsabilidad.
            </label>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-indigo-600 text-white font-bold py-3 rounded-lg hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-200 transition-all disabled:opacity-70"
          >
            {loading ? 'Creando cuenta...' : 'Completar Registro'}
          </button>
        </form>

        <div className="mt-8 flex items-center justify-center space-x-4">
          <div className="h-px bg-slate-200 flex-1"></div>
          <span className="text-sm text-slate-400">¿Ya tienes cuenta?</span>
          <div className="h-px bg-slate-200 flex-1"></div>
        </div>
        
        <div className="mt-6 text-center">
          <Link to="/login" className="inline-block font-semibold text-indigo-600 hover:text-indigo-500 transition-colors">
            Inicia sesión aquí
          </Link>
        </div>

      </div>
    </div>
  );
}
