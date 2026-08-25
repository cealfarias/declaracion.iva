import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { GoogleLogin } from '@react-oauth/google';

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
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    if (!formData.aceptaTerminos) {
      setError('Debes aceptar los Términos de Referencia para continuar.');
      return;
    }

    setLoading(true);

    try {
      await axios.post(`${API_URL}/api/v1/auth/register`, {
        nombre: formData.nombre,
        email: formData.email,
        password: formData.password,
        razon_social: formData.razon_social,
        nit: formData.nit,
        nrc: formData.nrc
      });

      // Registro exitoso
      navigate('/login', { state: { message: 'Registro exitoso. Por favor inicia sesión.' } });
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al registrar usuario.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    // Si queremos prellenar el formulario o manejar un login social para registro,
    // podríamos hacerlo aquí, pero la API principal espera los datos de la empresa.
    setError('Para registrarte con Google, asegúrate de llenar primero los datos de la empresa (Próximamente).');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl p-8 border border-slate-100">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-slate-900">Registro en el Sistema</h2>
          <p className="text-slate-500 mt-2">Crea tu cuenta y registra tu empresa para emitir anexos F-07</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm mb-6 border border-red-200">
            {error}
          </div>
        )}

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
              He leído y acepto los <a href="#" className="font-medium text-indigo-600 hover:underline">Términos de Referencia</a> y la política de privacidad de la plataforma. Entiendo que los datos fiscales son de mi entera responsabilidad.
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
