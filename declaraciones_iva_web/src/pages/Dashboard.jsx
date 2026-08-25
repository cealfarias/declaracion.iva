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
    <div className="min-h-screen bg-slate-100 font-sans">
      {/* Header Superior Blanco */}
      <div className="bg-white py-6 flex flex-col items-center justify-center shadow-sm relative">
        <h1 className="text-3xl text-slate-700 font-normal">Declaraciones IVA</h1>
        <h2 className="text-xl text-slate-600 font-light mt-1">Generador de Anexos F-07</h2>
        <p className="text-sm text-slate-500 mt-1">demiempresa.online</p>
        
        {/* User Info flotante */}
        <div className="absolute right-6 top-6 text-right hidden sm:block">
          <p className="text-sm font-semibold text-slate-700">Usuario Activo:</p>
          <p className="text-sm text-slate-600">{user?.nombre || 'Usuario'}</p>
        </div>
      </div>

      {/* Menú Azul Corporativo (Estilo MH) */}
      <nav className="bg-[#004b79] text-white px-4 md:px-12 py-3 flex justify-between items-center text-sm font-medium">
        <div className="flex space-x-8">
          <a href="#" className="hover:text-blue-200 transition uppercase">Inicio</a>
          <a href="#" className="hover:text-blue-200 transition uppercase">Declaraciones</a>
          <a href="#" className="hover:text-blue-200 transition uppercase">Informes</a>
        </div>
        <button 
          onClick={logout}
          className="hover:text-red-300 transition uppercase tracking-wider text-xs font-bold"
        >
          Salir
        </button>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto p-6 mt-6">
        
        <div className="text-center mb-8">
          <h3 className="text-xl font-bold text-slate-800 uppercase tracking-wide">Procesamiento de Declaraciones F-07</h3>
        </div>
        
        {/* Panel de Período Fiscal */}
        <div className="bg-white border border-blue-300 rounded shadow-sm p-5 mb-8 flex flex-col sm:flex-row items-center justify-between border-t-4 border-t-[#004b79]">
          <div>
            <h2 className="text-md font-bold text-[#004b79] uppercase">Período Fiscal</h2>
            <p className="text-sm text-slate-500">Selecciona el mes y año a declarar</p>
          </div>
          <div className="flex space-x-4 mt-4 sm:mt-0">
            <select 
              value={mes} 
              onChange={(e) => setMes(e.target.value)}
              className="bg-white border border-slate-300 text-slate-700 text-sm rounded-sm focus:ring-[#004b79] focus:border-[#004b79] block p-2 outline-none w-36"
            >
              {meses.map(m => <option key={m.id} value={m.id}>{m.nombre}</option>)}
            </select>
            <input 
              type="number" 
              value={anio} 
              onChange={(e) => setAnio(e.target.value)}
              className="bg-white border border-slate-300 text-slate-700 text-sm rounded-sm focus:ring-[#004b79] focus:border-[#004b79] block p-2 w-24 outline-none text-center"
            />
          </div>
        </div>

        {/* Panel de Archivos (Estilo MH Botones Rectangulares) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          
          {/* Compras */}
          <div className="flex bg-slate-50 border border-blue-300 rounded overflow-hidden shadow-sm hover:shadow-md transition">
            <div className="w-16 bg-[#337ab7] flex items-center justify-center text-white shrink-0">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
            </div>
            <label className="flex-1 p-4 cursor-pointer flex flex-col justify-center">
              <h3 className="font-bold text-[#004b79] text-sm uppercase">Anexo 3 - Compras</h3>
              <p className="text-xs text-slate-600 mt-1">Sube los DTEs de compras recibidos.</p>
              
              <div className="mt-3 text-xs bg-white border border-slate-300 p-2 text-center text-slate-500 rounded hover:bg-slate-100">
                {archivos.compras.length > 0 ? (
                  <span className="font-bold text-green-600">{archivos.compras.length} archivos seleccionados</span>
                ) : (
                  <span>Haz clic aquí para seleccionar archivos JSON</span>
                )}
              </div>
              <input type="file" multiple accept=".json" className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
            </label>
          </div>

          {/* Ventas Contribuyentes (CCF) */}
          <div className="flex bg-slate-50 border border-blue-300 rounded overflow-hidden shadow-sm hover:shadow-md transition">
            <div className="w-16 bg-[#337ab7] flex items-center justify-center text-white shrink-0">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            </div>
            <label className="flex-1 p-4 cursor-pointer flex flex-col justify-center">
              <h3 className="font-bold text-[#004b79] text-sm uppercase">Anexo 1 - Ventas CCF</h3>
              <p className="text-xs text-slate-600 mt-1">Sube los Créditos Fiscales emitidos.</p>
              
              <div className="mt-3 text-xs bg-white border border-slate-300 p-2 text-center text-slate-500 rounded hover:bg-slate-100">
                {archivos.ventasContribuyentes.length > 0 ? (
                  <span className="font-bold text-green-600">{archivos.ventasContribuyentes.length} archivos seleccionados</span>
                ) : (
                  <span>Haz clic aquí para seleccionar archivos JSON</span>
                )}
              </div>
              <input type="file" multiple accept=".json" className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
            </label>
          </div>

          {/* Ventas Consumidor Final */}
          <div className="flex bg-slate-50 border border-blue-300 rounded overflow-hidden shadow-sm hover:shadow-md transition md:col-span-2 md:w-1/2 md:mx-auto">
            <div className="w-16 bg-[#337ab7] flex items-center justify-center text-white shrink-0">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
            </div>
            <label className="flex-1 p-4 cursor-pointer flex flex-col justify-center">
              <h3 className="font-bold text-[#004b79] text-sm uppercase">Anexo 2 - Ventas FCF</h3>
              <p className="text-xs text-slate-600 mt-1">Sube las Facturas de Consumidor emitidas.</p>
              
              <div className="mt-3 text-xs bg-white border border-slate-300 p-2 text-center text-slate-500 rounded hover:bg-slate-100">
                {archivos.ventasConsumidor.length > 0 ? (
                  <span className="font-bold text-green-600">{archivos.ventasConsumidor.length} archivos seleccionados</span>
                ) : (
                  <span>Haz clic aquí para seleccionar archivos JSON</span>
                )}
              </div>
              <input type="file" multiple accept=".json" className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
            </label>
          </div>

        </div>

        {/* Console / Status */}
        {messages.length > 0 && (
          <div className="mb-8 bg-slate-800 rounded p-4 text-sm font-mono text-slate-300 border-l-4 border-[#337ab7]">
            {messages.map((msg, i) => (
              <div key={i} className={msg.type === 'error' ? 'text-red-400' : 'text-green-400'}>
                {msg.text}
              </div>
            ))}
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-center mt-12 mb-10">
          <button 
            onClick={handleProcesarTodo}
            disabled={loading || (archivos.compras.length === 0 && archivos.ventasContribuyentes.length === 0 && archivos.ventasConsumidor.length === 0)}
            className="bg-[#004b79] hover:bg-[#00385c] text-white font-bold py-3 px-10 rounded shadow transition-all focus:ring-4 focus:ring-blue-300 disabled:opacity-50 disabled:shadow-none text-sm uppercase tracking-wide flex items-center space-x-3"
          >
            {loading ? (
              <span>Generando Anexos CSV...</span>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                <span>Procesar y Descargar CSV</span>
              </>
            )}
          </button>
        </div>

      </main>
    </div>
  );
}
