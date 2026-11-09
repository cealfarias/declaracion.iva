import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [empresas, setEmpresas] = useState([]);
  const [archivadas, setArchivadas] = useState([]);
  const [mostrarArchivadas, setMostrarArchivadas] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [newEmpresa, setNewEmpresa] = useState({ razon_social: '', nit: '', nrc: '', actividad_economica: '', combustible_50_porciento: false });
  
  const currentDate = new Date();
  const [mes, setMes] = useState(localStorage.getItem('dashboard_mes') || (currentDate.getMonth() + 1).toString().padStart(2, '0'));
  const [anio, setAnio] = useState(localStorage.getItem('dashboard_anio') || currentDate.getFullYear().toString());

  useEffect(() => {
    localStorage.setItem('dashboard_mes', mes);
  }, [mes]);

  useEffect(() => {
    localStorage.setItem('dashboard_anio', anio);
  }, [anio]);

  const { user, token, selectEmpresa, activeEmpresa, logout } = useAuth();
  const authConfig = { headers: { Authorization: `Bearer ${token}` } };
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  useEffect(() => {
    if (!activeEmpresa) {
      fetchEmpresas();
    }
  }, [activeEmpresa]);

  const fetchEmpresas = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/empresas/usuario/${user?.id}`, authConfig);
      setEmpresas(response.data);
      const archivedResponse = await axios.get(`${API_URL}/api/v1/empresas/archivadas`, authConfig);
      setArchivadas(archivedResponse.data);
    } catch (error) {
      console.error('Error fetching empresas', error);
      enqueueMessages([{ text: "Ocurrió un error al cargar tus empresas.", type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (empresa) => {
    selectEmpresa(empresa);
    enqueueMessages([{ text: `Has seleccionado la empresa ${empresa.razon_social}.`, type: "success" }]);
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
      if (editingId) {
        await axios.put(`${API_URL}/api/v1/empresas/${editingId}`, newEmpresa, authConfig);
        setEmpresas(empresas.map(emp => emp.id === editingId ? { ...emp, ...newEmpresa } : emp));
        enqueueMessages([{ text: "Empresa actualizada correctamente.", type: "success" }]);
      } else {
        const response = await axios.post(`${API_URL}/api/v1/empresas`, {
          ...newEmpresa,
          usuario_id: user?.id
        }, authConfig);
        const created = { id: response.data.empresa_id, ...newEmpresa };
        setEmpresas([...empresas, created]);
        enqueueMessages([{ text: "Empresa registrada exitosamente.", type: "success" }]);
      }
      setShowModal(false);
      setNewEmpresa({ razon_social: '', nit: '', nrc: '', combustible_50_porciento: false });
    } catch (error) {
      console.error('Error creando empresa', error);
      const errorMsg = error.response?.data?.detail || "Hubo un error al guardar los datos de la empresa.";
      enqueueMessages([{ text: errorMsg, type: "error" }]);
    }
  };

  const handleRetirarEmpresa = async (e, empresa) => {
    e.stopPropagation();
    if (!window.confirm(`¿Retirar "${empresa.razon_social}" de tu lista? No se borrarán sus documentos ni declaraciones. Para volver a verla tendrás que vincularla nuevamente.`)) return;
    try {
      await axios.delete(`${API_URL}/api/v1/empresas/${empresa.id}/mi-vinculo`, authConfig);
      setEmpresas(actual => actual.filter(item => item.id !== empresa.id));
      setArchivadas(actual => [...actual, empresa]);
      if (activeEmpresa?.id === empresa.id) selectEmpresa(null);
      enqueueMessages([{ text: 'Empresa archivada. Puedes restaurarla cuando quieras.', type: 'success' }]);
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || 'No se pudo retirar la empresa.', type: 'error' }]);
    }
  };

  const handleRestaurarEmpresa = async (empresa) => {
    try {
      await axios.post(`${API_URL}/api/v1/empresas/${empresa.id}/restaurar`, {}, authConfig);
      setArchivadas(actual => actual.filter(item => item.id !== empresa.id));
      setEmpresas(actual => [...actual, empresa]);
      enqueueMessages([{ text: 'Empresa restaurada correctamente.', type: 'success' }]);
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || 'No se pudo restaurar la empresa.', type: 'error' }]);
    }
  };

  const renderSeleccionEmpresa = () => (
    <>
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

      <div className="mb-6">
        <button type="button" onClick={() => setMostrarArchivadas(actual => !actual)} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
          {mostrarArchivadas ? 'Ocultar archivadas' : 'Ver empresas archivadas'} ({archivadas.length})
        </button>
        {mostrarArchivadas && (
          <div className="mt-3 space-y-2 rounded-xl border border-slate-200 bg-white p-4">
            {archivadas.length === 0 ? <p className="text-sm text-slate-500">No hay empresas archivadas.</p> : archivadas.map(empresa => (
              <div key={empresa.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 py-2">
                <div><p className="font-semibold text-slate-800">{empresa.razon_social}</p><p className="text-xs text-slate-500">NIT: {empresa.nit}</p></div>
                <button type="button" onClick={() => handleRestaurarEmpresa(empresa)} className="rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-700">Restaurar</button>
              </div>
            ))}
          </div>
        )}
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
                <button
                  type="button"
                  onClick={(e) => handleRetirarEmpresa(e, empresa)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-700"
                  title="Retirar empresa de mi panel (sin borrar documentos)"
                  aria-label={`Retirar ${empresa.razon_social} de mi panel`}
                >
                  <span aria-hidden="true">✕</span>
                </button>
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-1 truncate" title={empresa.razon_social}>{empresa.razon_social}</h3>
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
    </>
  );

  const renderF07Dashboard = () => (
    <div className="flex flex-col space-y-6 animate-fade-in-up">
      <div className="flex justify-between items-end mb-2">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Panel Principal - {activeEmpresa.razon_social}</h2>
          <p className="text-sm text-slate-500 mt-1">NIT: {activeEmpresa.nit} | NRC: {activeEmpresa.nrc}</p>
          
          <div className="flex items-center space-x-4 mt-3">
            <div className="flex items-center space-x-2">
              <label className="text-sm font-semibold text-slate-700">Año:</label>
              <input 
                type="number" 
                min="2000" 
                max="2100" 
                className="border border-slate-300 rounded-lg px-2 py-1 text-sm focus:ring-2 focus:ring-indigo-500 outline-none w-24" 
                value={anio} 
                onChange={(e) => setAnio(e.target.value)} 
              />
            </div>
            <div className="flex items-center space-x-2">
              <label className="text-sm font-semibold text-slate-700">Mes:</label>
              <select className="border border-slate-300 rounded-lg px-2 py-1 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" value={mes} onChange={(e) => setMes(e.target.value)}>
                <option value="01">Enero</option>
                <option value="02">Febrero</option>
                <option value="03">Marzo</option>
                <option value="04">Abril</option>
                <option value="05">Mayo</option>
                <option value="06">Junio</option>
                <option value="07">Julio</option>
                <option value="08">Agosto</option>
                <option value="09">Septiembre</option>
                <option value="10">Octubre</option>
                <option value="11">Noviembre</option>
                <option value="12">Diciembre</option>
              </select>
            </div>
          </div>
        </div>
        <button 
          onClick={() => selectEmpresa(null)}
          className="bg-white border border-slate-300 text-slate-700 px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-slate-50 transition shadow-sm"
        >
          Cambiar Empresa
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card for Contribuyentes */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-50 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-1">Libro de Contribuyentes</h3>
          <p className="text-sm text-slate-500 mb-5">Importa tus CCF, NC y ND generados para tu anexo de contribuyentes.</p>
          <button 
            onClick={() => navigate(`/ventas-contribuyentes?mes=${mes}&anio=${anio}`)}
            className="w-full bg-blue-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-blue-700 transition"
          >
            Generar Anexo
          </button>
        </div>

        {/* Card for Consumidor Final */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-50 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-1">Libro de Consumidor Final</h3>
          <p className="text-sm text-slate-500 mb-5">Importa tus FCF emitidas para tu anexo a consumidor final.</p>
          <button 
            onClick={() => navigate(`/consumidor-final?mes=${mes}&anio=${anio}`)}
            className="w-full bg-emerald-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-emerald-700 transition"
          >
            Generar Anexo
          </button>
        </div>

        {/* Card for Compras */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-50 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          <div className="w-10 h-10 bg-amber-100 text-amber-600 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-1">Libro de Compras</h3>
          <p className="text-sm text-slate-500 mb-5">Importa los comprobantes recibidos de tus proveedores para tu anexo de compras.</p>
          <button 
            onClick={() => navigate(`/compras?mes=${mes}&anio=${anio}`)}
            className="w-full bg-amber-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-amber-700 transition"
          >
            Generar Anexo
          </button>
        </div>

        {/* Card for Liquidacion */}
        <div className="bg-indigo-700 rounded-xl p-6 border border-indigo-800 shadow-md hover:shadow-lg transition-shadow relative overflow-hidden group col-span-1 md:col-span-2 lg:col-span-3 mt-4">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-600 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center">
            <div>
              <div className="w-12 h-12 bg-white text-indigo-700 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
              </div>
              <h3 className="text-xl font-bold text-white mb-1">Liquidación de Impuestos</h3>
              <p className="text-sm text-indigo-200 mb-5 sm:mb-0 max-w-md">Consolida la información de tus anexos de compras y ventas para determinar el pago a cuenta o remanente del mes de forma automática.</p>
            </div>
            <button 
              onClick={() => navigate(`/liquidacion?mes=${mes}&anio=${anio}`)}
              className="bg-white text-indigo-700 text-sm font-bold py-3 px-8 rounded-lg hover:bg-indigo-50 transition w-full sm:w-auto whitespace-nowrap shadow-sm"
            >
              Ver Liquidación (F-07)
            </button>
          </div>
        </div>

        {/* Card for Anulados */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-red-50 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          <div className="w-10 h-10 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-1">Documentos Anulados</h3>
          <p className="text-sm text-slate-500 mb-5">Importa los JSON de Invalidación para excluirlos de tus impuestos.</p>
          <button 
            onClick={() => navigate(`/anulados?mes=${mes}&anio=${anio}`)}
            className="w-full bg-red-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-red-700 transition"
          >
            Gestionar Anulados
          </button>
        </div>

        {/* Card for Retenciones 1% al Declarante */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-50 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          <div className="w-10 h-10 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l4-2 4 2 4-2 4 2z" /></svg>
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-1">Retenciones 1% (Casilla 162)</h3>
          <p className="text-sm text-slate-500 mb-5">Importa tus DTE 07 para generar el anexo y deducir retenciones efectuadas al declarante.</p>
          <button 
            onClick={() => navigate(`/retenciones?mes=${mes}&anio=${anio}`)}
            className="w-full bg-purple-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-purple-700 transition"
          >
            Generar Anexo
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex justify-between items-center sticky top-0 z-10">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800">Declaraciones de IVA</h1>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-sm text-slate-600 font-medium">Hola, {user?.nombre || 'Usuario'}</span>
          <button onClick={() => { logout(); navigate('/login'); }} className="text-sm text-red-600 font-medium hover:underline">
            Cerrar Sesión
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-8">
        {!activeEmpresa ? renderSeleccionEmpresa() : renderF07Dashboard()}
      </main>

      {/* Modal Nueva Empresa */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl overflow-hidden animate-fade-in-up">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h3 className="text-lg font-bold text-slate-800">{editingId ? 'Editar Empresa' : 'Registrar Nueva Empresa'}</h3>
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
                  {editingId ? 'Actualizar' : 'Guardar Empresa'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
