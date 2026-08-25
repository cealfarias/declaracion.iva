import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const { user, logout } = useAuth();
  
  const [anio, setAnio] = useState(new Date().getFullYear());
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [archivos, setArchivos] = useState({
    compras: [],
    ventasContribuyentes: [],
    ventasConsumidor: []
  });
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);

  const meses = [
    { id: 1, nombre: 'Enero' }, { id: 2, nombre: 'Febrero' }, { id: 3, nombre: 'Marzo' },
    { id: 4, nombre: 'Abril' }, { id: 5, nombre: 'Mayo' }, { id: 6, nombre: 'Junio' },
    { id: 7, nombre: 'Julio' }, { id: 8, nombre: 'Agosto' }, { id: 9, nombre: 'Septiembre' },
    { id: 10, nombre: 'Octubre' }, { id: 11, nombre: 'Noviembre' }, { id: 12, nombre: 'Diciembre' }
  ];

  const handleFileChange = (e, tipo) => {
    setArchivos({
      ...archivos,
      [tipo]: Array.from(e.target.files)
    });
  };

  const processFiles = async (tipo, endpoint, filename) => {
    if (archivos[tipo].length === 0) return;
    
    const formData = new FormData();
    archivos[tipo].forEach(file => {
      formData.append('files', file);
    });
    // Puedes incluir el periodo_id si luego agregas la lógica de periodos en la BD
    // formData.append('periodo_id', 1);

    try {
      const response = await axios.post(`${API_URL}/api/v1/procesamiento/${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob'
      });

      // Descargar CSV
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${filename}_${mes}_${anio}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      
      setMessages(prev => [...prev, { text: `✅ ${filename} procesado con éxito.`, type: 'success' }]);
    } catch (error) {
      setMessages(prev => [...prev, { text: `❌ Error al procesar ${filename}.`, type: 'error' }]);
    }
  };

  const handleProcesarTodo = async () => {
    setLoading(true);
    setMessages([]);
    
    if (archivos.compras.length > 0) {
      await processFiles('compras', 'procesar/compras', 'F07_Anexo_Compras');
    }
    if (archivos.ventasContribuyentes.length > 0) {
      await processFiles('ventasContribuyentes', 'procesar/ventas-contribuyentes', 'F07_Anexo_Ventas_CCF');
    }
    if (archivos.ventasConsumidor.length > 0) {
      await processFiles('ventasConsumidor', 'procesar/ventas-consumidor', 'F07_Anexo_Ventas_FCF');
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-indigo-700">Declaraciones IVA</h1>
          <p className="text-sm text-slate-500">Generador de Anexos F-07</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <p className="text-sm font-semibold text-slate-800">{user?.nombre || 'Usuario'}</p>
          </div>
          <button 
            onClick={logout}
            className="text-sm bg-red-50 text-red-600 px-4 py-2 rounded-lg hover:bg-red-100 font-medium transition"
          >
            Cerrar Sesión
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto p-6 mt-8">
        
        {/* Panel de Período Fiscal */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Período Fiscal</h2>
            <p className="text-sm text-slate-500">Selecciona el mes y año a declarar</p>
          </div>
          <div className="flex space-x-4">
            <select 
              value={mes} 
              onChange={(e) => setMes(e.target.value)}
              className="bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-2.5 outline-none"
            >
              {meses.map(m => <option key={m.id} value={m.id}>{m.nombre}</option>)}
            </select>
            <input 
              type="number" 
              value={anio} 
              onChange={(e) => setAnio(e.target.value)}
              className="bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-2.5 w-24 outline-none"
            />
          </div>
        </div>

        {/* Panel de Archivos */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          
          {/* Compras */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col h-full">
            <div className="flex-1">
              <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
              </div>
              <h3 className="font-bold text-slate-800 text-lg">Compras</h3>
              <p className="text-sm text-slate-500 mb-4">Anexo 3 - Sube los archivos JSON de DTEs recibidos.</p>
            </div>
            
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-slate-300 border-dashed rounded-lg cursor-pointer bg-slate-50 hover:bg-slate-100 transition">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <p className="mb-2 text-sm text-slate-500"><span className="font-semibold">Clic para subir</span> o arrastra carpetas</p>
                <p className="text-xs text-slate-400">{archivos.compras.length} archivos seleccionados</p>
              </div>
              <input type="file" multiple accept=".json" className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
            </label>
          </div>

          {/* Ventas Contribuyentes (CCF) */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col h-full">
            <div className="flex-1">
              <div className="w-12 h-12 bg-green-100 text-green-600 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              </div>
              <h3 className="font-bold text-slate-800 text-lg">Ventas CCF</h3>
              <p className="text-sm text-slate-500 mb-4">Anexo 1 - Sube los JSON de Créditos Fiscales emitidos.</p>
            </div>
            
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-slate-300 border-dashed rounded-lg cursor-pointer bg-slate-50 hover:bg-slate-100 transition">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <p className="mb-2 text-sm text-slate-500"><span className="font-semibold">Clic para subir</span> o arrastra carpetas</p>
                <p className="text-xs text-slate-400">{archivos.ventasContribuyentes.length} archivos seleccionados</p>
              </div>
              <input type="file" multiple accept=".json" className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
            </label>
          </div>

          {/* Ventas Consumidor Final */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col h-full">
            <div className="flex-1">
              <div className="w-12 h-12 bg-orange-100 text-orange-600 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
              </div>
              <h3 className="font-bold text-slate-800 text-lg">Ventas FCF</h3>
              <p className="text-sm text-slate-500 mb-4">Anexo 2 - Sube los JSON de Facturas de Consumidor emitidas.</p>
            </div>
            
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-slate-300 border-dashed rounded-lg cursor-pointer bg-slate-50 hover:bg-slate-100 transition">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <p className="mb-2 text-sm text-slate-500"><span className="font-semibold">Clic para subir</span> o arrastra carpetas</p>
                <p className="text-xs text-slate-400">{archivos.ventasConsumidor.length} archivos seleccionados</p>
              </div>
              <input type="file" multiple accept=".json" className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
            </label>
          </div>

        </div>

        {/* Console / Status */}
        {messages.length > 0 && (
          <div className="mb-8 bg-slate-800 rounded-lg p-4 text-sm font-mono text-slate-300">
            {messages.map((msg, i) => (
              <div key={i} className={msg.type === 'error' ? 'text-red-400' : 'text-green-400'}>
                {msg.text}
              </div>
            ))}
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-center">
          <button 
            onClick={handleProcesarTodo}
            disabled={loading || (archivos.compras.length === 0 && archivos.ventasContribuyentes.length === 0 && archivos.ventasConsumidor.length === 0)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 px-12 rounded-full shadow-lg shadow-indigo-200 transition-all focus:ring-4 focus:ring-indigo-300 disabled:opacity-50 disabled:shadow-none text-lg flex items-center space-x-3"
          >
            {loading ? (
              <span>Generando Anexos CSV...</span>
            ) : (
              <>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
                <span>Procesar y Descargar CSV</span>
              </>
            )}
          </button>
        </div>

      </main>
    </div>
  );
}
