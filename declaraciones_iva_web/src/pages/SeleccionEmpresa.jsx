import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function SeleccionEmpresa() {
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [newEmpresa, setNewEmpresa] = useState({ razon_social: '', nit: '', nrc: '', actividad_economica: '', combustible_50_porciento: false });
  
  const { user, token, selectEmpresa, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchEmpresas();
  }, []);

  const fetchEmpresas = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/empresas/usuario/${user?.id || 1}`);
      setEmpresas(response.data);
    } catch (error) {
      console.error('Error fetching empresas', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (empresa) => {
    selectEmpresa(empresa);
    navigate('/dashboard');
  };

  
  const handleEditClick = (e, emp) => {
    e.stopPropagation();
    setEditingId(emp.id);
    setNewEmpresa({
      razon_social: emp.razon_social,
      nit: emp.nit,
      nrc: emp.nrc || '',
      combustible_50_porciento: emp.combustible_50_porciento || false
    });
    setShowModal(true);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_URL}/api/v1/empresas`, {
        ...newEmpresa,
        usuario_id: user?.id || 1
      });
      
      const created = { id: response.data.empresa_id, ...newEmpresa };
      setEmpresas([...empresas, created]);
      setShowModal(false);
      setNewEmpresa({ razon_social: '', nit: '', nrc: '' });
    } catch (error) {
      console.error('Error creando empresa', error);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800">Declaraciones de IVA</h1>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-sm text-slate-600 font-medium">Hola, {user?.nombre || 'César'}</span>
          <button onClick={() => { logout(); navigate('/login'); }} className="text-sm text-red-600 font-medium hover:underline">
            Cerrar Sesión
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-8">
        <div className="flex justify-between items-end mb-8">
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Selecciona una Empresa</h2>
            <p className="text-slate-500 mt-2">Elige el perfil con el que trabajarás hoy o registra uno nuevo.</p>
          </div>
          <button 
            onClick={() => { setShowModal(true); setEditingId(null); setNewEmpresa({ razon_social: '', nit: '', nrc: '', combustible_50_porciento: false }); }}
            className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-indigo-700 transition shadow-sm flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
            Nueva Empresa
          </button>
        </div>

        {loading ? (
          <div className="text-center py-20 text-slate-500">Cargando empresas...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {empresas.map(empresa => (
              <div 
                key={empresa.id} 
                onClick={() => handleSelect(empresa)}
                className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-300 cursor-pointer transition-all group"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-lg flex items-center justify-center group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                  </div>
                  <button 
                    onClick={(e) => handleEditClick(e, empresa)}
                    className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                    title="Editar empresa"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                  </button>
                </div>
                <h3 className="text-xl font-bold text-slate-800 mb-1">{empresa.razon_social}</h3>
                <div className="text-sm text-slate-500 space-y-1 mt-3">
                  <p><span className="font-medium text-slate-700">NIT:</span> {empresa.nit}</p>
                  <p><span className="font-medium text-slate-700">NRC:</span> {empresa.nrc}</p>
                </div>
              </div>
            ))}
            
            {empresas.length === 0 && (
              <div className="col-span-full bg-indigo-50 border border-dashed border-indigo-200 rounded-xl p-12 text-center">
                <h3 className="text-lg font-bold text-indigo-900 mb-2">No tienes empresas registradas</h3>
                <p className="text-indigo-700 mb-4">Comienza registrando tu primera empresa para generar declaraciones.</p>
                <button onClick={() => { setShowModal(true); setEditingId(null); setNewEmpresa({ razon_social: '', nit: '', nrc: '', combustible_50_porciento: false }); }} className="text-indigo-600 font-semibold hover:underline">
                  Registrar mi primera empresa
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Modal Nueva Empresa */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h3 className="text-lg font-bold text-slate-800">Registrar Nueva Empresa</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Razón Social</label>
                <input 
                  type="text" 
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  value={newEmpresa.razon_social}
                  onChange={(e) => setNewEmpresa({...newEmpresa, razon_social: e.target.value})}
                  placeholder="Ej. Distribuidora S.A. de C.V."
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">NIT</label>
                  <input 
                    type="text" 
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    value={newEmpresa.nit}
                    onChange={(e) => setNewEmpresa({...newEmpresa, nit: e.target.value})}
                    placeholder="0000-000000-000-0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">NRC</label>
                  <input 
                    type="text" 
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    value={newEmpresa.nrc}
                    onChange={(e) => setNewEmpresa({...newEmpresa, nrc: e.target.value})}
                    placeholder="123456-7"
                  />
                </div>
              </div>
              
              <div className="pt-4 flex space-x-3">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 px-4 py-2 bg-slate-100 text-slate-700 font-medium rounded-lg hover:bg-slate-200 transition">
                  Cancelar
                </button>
                <button type="submit" className="flex-1 px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition">
                  Guardar Empresa
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
