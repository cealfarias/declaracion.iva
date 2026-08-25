import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';
import axios from 'axios';

const APP_VERSION = "v1.3 (Tabs & Assistant)";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const [anio, setAnio] = useState(new Date().getFullYear());
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [archivos, setArchivos] = useState({
    compras: [],
    ventasContribuyentes: [],
    ventasConsumidor: []
  });
  const [loading, setLoading] = useState(false);
  const [activeTabs, setActiveTabs] = useState({});

  const meses = [
    { id: 1, nombre: 'Enero' }, { id: 2, nombre: 'Febrero' }, { id: 3, nombre: 'Marzo' },
    { id: 4, nombre: 'Abril' }, { id: 5, nombre: 'Mayo' }, { id: 6, nombre: 'Junio' },
    { id: 7, nombre: 'Julio' }, { id: 8, nombre: 'Agosto' }, { id: 9, nombre: 'Septiembre' },
    { id: 10, nombre: 'Octubre' }, { id: 11, nombre: 'Noviembre' }, { id: 12, nombre: 'Diciembre' }
  ];

  const handleFileChange = (e, tipo) => {
    const files = Array.from(e.target.files).filter(file => file.name.endsWith('.json'));
    setArchivos({ ...archivos, [tipo]: files });
    enqueueMessages([{ text: `Se seleccionaron ${files.length} archivos JSON para ${tipo}.`, type: 'success' }]);
  };

  const [resumen, setResumen] = useState(null);
  const [selectedJson, setSelectedJson] = useState(null); // Para mostrar el JSON rechazado

  const fetchPeriodoData = async () => {
    if (!user?.id) return null;
    try {
      const response = await axios.get(`${API_URL}/api/v1/procesar/consultar`, {
        params: { mes, anio, usuario_id: user.id }
      });
      return response.data?.data || null;
    } catch (error) {
      console.error("Error buscando periodo", error);
      return null;
    }
  };
  
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const data = await fetchPeriodoData();
      if (data) {
        setResumen(data);
        enqueueMessages([{ text: `Se cargaron los datos guardados para ${mes}/${anio}.`, type: 'success' }]);
      } else {
        setResumen(null);
      }
      setLoading(false);
    };
    load();
  }, [mes, anio, user]);

  const processFiles = async (tipo, endpoint, filename) => {
    if (archivos[tipo].length === 0) return { omitidos: [] };
    
    const formData = new FormData();
    archivos[tipo].forEach(file => formData.append('files', file));
    formData.append('mes', mes);
    formData.append('anio', anio);
    formData.append('usuario_id', user.id);

    try {
      const response = await axios.post(`${API_URL}/api/v1/${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'json' 
      });
      return { omitidos: response.data.omitidos || [], error: null };
    } catch (error) {
      const errMsg = error.response?.data?.detail || `Error al procesar lote`;
      return { omitidos: [], error: errMsg };
    }
  };

  const descargarCSV = (csvString, filename) => {
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${filename}_${mes}_${anio}.csv`);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
  };

  const handleProcesarTodo = async () => {
    setLoading(true);
    let allOmitidos = { compras: [], ventasContribuyentes: [], ventasConsumidor: [] };
    let errors = [];

    if (archivos.compras.length > 0) {
      const res = await processFiles('compras', 'procesar/compras', 'F07_Anexo_Compras');
      allOmitidos.compras = res.omitidos;
      if (res.error) errors.push(res.error);
    }
    if (archivos.ventasContribuyentes.length > 0) {
      const res = await processFiles('ventasContribuyentes', 'procesar/ventas-contribuyentes', 'F07_Anexo_Ventas_CCF');
      allOmitidos.ventasContribuyentes = res.omitidos;
      if (res.error) errors.push(res.error);
    }
    if (archivos.ventasConsumidor.length > 0) {
      const res = await processFiles('ventasConsumidor', 'procesar/ventas-consumidor', 'F07_Anexo_Ventas_FCF');
      allOmitidos.ventasConsumidor = res.omitidos;
      if (res.error) errors.push(res.error);
    }
    
    // Re-fetch to get new valid data
    let dbData = await fetchPeriodoData();
    if (!dbData) dbData = {};

    let newTabs = { ...activeTabs };
    let msgs = [];
    
    const mergeOmitidos = (key, filenameFallback) => {
      if (allOmitidos[key].length > 0) {
        if (!dbData[key]) {
          dbData[key] = { filename: filenameFallback, documentos:0, gravado:0, iva:0, total:0, registros:[], omitidos: [], csv: "" };
        }
        dbData[key].omitidos = allOmitidos[key];
        newTabs[key] = 'rechazados'; // Select tab rechazados if there are any
      } else {
        if (dbData[key]) dbData[key].omitidos = [];
      }
    };

    mergeOmitidos('compras', 'F07_Anexo_Compras');
    mergeOmitidos('ventasContribuyentes', 'F07_Anexo_Ventas_CCF');
    mergeOmitidos('ventasConsumidor', 'F07_Anexo_Ventas_FCF');

    if (Object.keys(dbData).length > 0) {
      setResumen(dbData);
      setActiveTabs(newTabs);
      msgs.push({ text: `Lote procesado. Se cargaron los datos actualizados.`, type: 'success' });
    } else {
      setResumen(null);
    }
    
    errors.forEach(e => msgs.push({ text: e, type: 'error' }));
    if (msgs.length > 0) enqueueMessages(msgs);

    setArchivos({ compras: [], ventasContribuyentes: [], ventasConsumidor: [] });
    setLoading(false);
  };

  const handleTabChange = (tipoKey, tabName) => {
    setActiveTabs(prev => ({ ...prev, [tipoKey]: tabName }));
  };

  return (
    <div className="min-h-screen bg-slate-100 font-sans">
      <div className="bg-white py-6 flex flex-col items-center justify-center shadow-sm relative">
        <h1 className="text-3xl text-slate-700 font-normal">Procesamiento de Declaración de IVA</h1>
        <h2 className="text-xl text-slate-600 font-light mt-1">Generador de Anexos F-07</h2>
        <p className="text-sm text-slate-500 mt-1">demiempresa.online</p>
        
        <div className="absolute right-6 top-6 text-right hidden sm:block">
          <p className="text-sm font-semibold text-slate-700">Usuario Activo:</p>
          <p className="text-sm text-slate-600">{user?.nombre || 'Usuario'}</p>
          <p className="text-xs font-mono text-slate-400 mt-1 px-2 py-0.5 bg-slate-100 rounded-full border border-slate-200">
            {APP_VERSION}
          </p>
        </div>
      </div>

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

      <main className="max-w-6xl mx-auto p-6 mt-6">
        <div className="bg-white border border-blue-300 rounded shadow-sm p-6 mb-8">
          <div className="flex flex-col md:flex-row justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-[#004b79] uppercase flex items-center">
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
              Periodo a procesar
            </h2>
          </div>

          <div className="flex flex-col md:flex-row gap-6 mb-4">
            <div className="w-full md:w-1/2">
              <label className="block text-sm font-bold text-slate-700 mb-2 uppercase">Mes a declarar</label>
              <select 
                value={mes} 
                onChange={(e) => setMes(parseInt(e.target.value))}
                className="w-full border border-slate-300 p-3 rounded focus:ring-2 focus:ring-[#337ab7] focus:border-transparent outline-none bg-slate-50 transition"
              >
                {meses.map(m => (
                  <option key={m.id} value={m.id}>{m.nombre}</option>
                ))}
              </select>
            </div>
            
            <div className="w-full md:w-1/2">
              <label className="block text-sm font-bold text-slate-700 mb-2 uppercase">Año</label>
              <input 
                type="number" 
                value={anio} 
                onChange={(e) => setAnio(parseInt(e.target.value))}
                className="w-full border border-slate-300 p-3 rounded focus:ring-2 focus:ring-[#337ab7] focus:border-transparent outline-none bg-slate-50 transition"
                min="2000"
                max="2100"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className="flex bg-slate-50 border border-blue-300 rounded overflow-hidden shadow-sm hover:shadow-md transition">
            <div className="w-16 bg-[#337ab7] flex items-center justify-center text-white shrink-0">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
            </div>
            <label className="flex-1 p-4 cursor-pointer flex flex-col justify-center">
              <h3 className="font-bold text-[#004b79] text-sm uppercase">Anexo 3 - Compras</h3>
              <p className="text-xs text-slate-600 mt-1">Sube los DTEs de compras recibidos.</p>
              
              <div className="mt-3 text-xs bg-white border border-slate-300 p-2 text-center text-slate-500 rounded hover:bg-slate-100">
                {archivos.compras.length > 0 ? (
                  <span className="font-bold text-green-600">{archivos.compras.length} archivos JSON listos</span>
                ) : (
                  <span>Haz clic para seleccionar la carpeta contenedora</span>
                )}
              </div>
              <input type="file" webkitdirectory="true" directory="true" multiple className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
            </label>
          </div>

          <div className="flex bg-slate-50 border border-blue-300 rounded overflow-hidden shadow-sm hover:shadow-md transition">
            <div className="w-16 bg-[#337ab7] flex items-center justify-center text-white shrink-0">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            </div>
            <label className="flex-1 p-4 cursor-pointer flex flex-col justify-center">
              <h3 className="font-bold text-[#004b79] text-sm uppercase">Anexo 1 - Ventas CCF</h3>
              <p className="text-xs text-slate-600 mt-1">Sube los Créditos Fiscales emitidos.</p>
              
              <div className="mt-3 text-xs bg-white border border-slate-300 p-2 text-center text-slate-500 rounded hover:bg-slate-100">
                {archivos.ventasContribuyentes.length > 0 ? (
                  <span className="font-bold text-green-600">{archivos.ventasContribuyentes.length} archivos JSON listos</span>
                ) : (
                  <span>Haz clic para seleccionar la carpeta contenedora</span>
                )}
              </div>
              <input type="file" webkitdirectory="true" directory="true" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
            </label>
          </div>

          <div className="flex bg-slate-50 border border-blue-300 rounded overflow-hidden shadow-sm hover:shadow-md transition md:col-span-2 md:w-1/2 md:mx-auto">
            <div className="w-16 bg-[#337ab7] flex items-center justify-center text-white shrink-0">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
            </div>
            <label className="flex-1 p-4 cursor-pointer flex flex-col justify-center">
              <h3 className="font-bold text-[#004b79] text-sm uppercase">Anexo 2 - Ventas FCF</h3>
              <p className="text-xs text-slate-600 mt-1">Sube las Facturas de Consumidor emitidas.</p>
              
              <div className="mt-3 text-xs bg-white border border-slate-300 p-2 text-center text-slate-500 rounded hover:bg-slate-100">
                {archivos.ventasConsumidor.length > 0 ? (
                  <span className="font-bold text-green-600">{archivos.ventasConsumidor.length} archivos JSON listos</span>
                ) : (
                  <span>Haz clic para seleccionar la carpeta contenedora</span>
                )}
              </div>
              <input type="file" webkitdirectory="true" directory="true" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
            </label>
          </div>
        </div>

        <div className="flex justify-center mt-6 mb-10">
          <button 
            onClick={handleProcesarTodo}
            disabled={loading || (archivos.compras.length === 0 && archivos.ventasContribuyentes.length === 0 && archivos.ventasConsumidor.length === 0)}
            className="bg-[#004b79] hover:bg-[#00385c] text-white font-bold py-3 px-10 rounded shadow transition-all focus:ring-4 focus:ring-blue-300 disabled:opacity-50 disabled:shadow-none text-sm uppercase tracking-wide flex items-center space-x-3"
          >
            {loading ? (
              <span>Generando Anexos y Validando...</span>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                <span>Procesar</span>
              </>
            )}
          </button>
        </div>

        {resumen && (
          <div className="bg-white border border-blue-300 rounded shadow-sm p-6 mb-8 mt-4 border-t-4 border-t-[#004b79]">
            <h2 className="text-lg font-bold text-[#004b79] uppercase mb-6 text-center border-b pb-4">Detalle y Validación de Declaración</h2>
            <div className="space-y-12">
              {Object.keys(resumen).map((tipoKey) => {
                const data = resumen[tipoKey];
                const activeTab = activeTabs[tipoKey] || 'admitidos';
                
                return (
                  <div key={tipoKey} className="bg-slate-50 p-4 rounded border border-slate-200">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="font-bold text-slate-700 uppercase text-sm">{data.filename.replace(/_/g, ' ')}</h3>
                      <div className="space-x-3">
                        <span className="text-xs px-3 py-1 bg-[#004b79] text-white rounded-full">
                          {data.documentos} DTEs Validados
                        </span>
                        {data.csv && (
                          <button 
                            onClick={() => descargarCSV(data.csv, data.filename)}
                            className="text-xs px-3 py-1 bg-green-600 hover:bg-green-700 transition text-white rounded shadow-sm inline-flex items-center"
                          >
                            Descargar CSV
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-white p-3 rounded border border-slate-200 text-center">
                        <p className="text-xs text-slate-500 font-semibold mb-1 uppercase">Monto Gravado</p>
                        <p className="text-lg font-bold text-[#004b79]">${data.gravado.toFixed(2)}</p>
                      </div>
                      <div className="bg-white p-3 rounded border border-slate-200 text-center">
                        <p className="text-xs text-slate-500 font-semibold mb-1 uppercase">Crédito / Débito Fiscal</p>
                        <p className="text-lg font-bold text-[#004b79]">${data.iva.toFixed(2)}</p>
                      </div>
                      <div className="bg-white p-3 rounded border border-slate-200 text-center">
                        <p className="text-xs text-slate-500 font-semibold mb-1 uppercase">Total General</p>
                        <p className="text-lg font-bold text-[#004b79]">${data.total.toFixed(2)}</p>
                      </div>
                      <div className="bg-white p-3 rounded border border-slate-200 text-center">
                        <p className="text-xs text-slate-500 font-semibold mb-1 uppercase">Omitidos / Rechazados</p>
                        <p className="text-lg font-bold text-red-600">{data.omitidos?.length || 0}</p>
                      </div>
                    </div>

                    <div className="flex border-b border-slate-200 mb-4">
                      <button
                        onClick={() => handleTabChange(tipoKey, 'admitidos')}
                        className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'admitidos' ? 'border-[#004b79] text-[#004b79]' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                      >
                        Archivos Admitidos ({data.registros?.length || 0})
                      </button>
                      <button
                        onClick={() => handleTabChange(tipoKey, 'rechazados')}
                        className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'rechazados' ? 'border-red-600 text-red-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                      >
                        Archivos Rechazados ({data.omitidos?.length || 0})
                      </button>
                    </div>

                    {activeTab === 'admitidos' && data.registros && data.registros.length > 0 && (
                      <div className="overflow-x-auto bg-white border border-slate-200 rounded">
                        <table className="w-full text-left text-xs whitespace-nowrap">
                          <thead className="bg-[#004b79] text-white uppercase font-semibold">
                            <tr>
                              <th className="px-4 py-2 border-r border-[#00385c]">Fecha</th>
                              <th className="px-4 py-2 border-r border-[#00385c]">Tipo</th>
                              <th className="px-4 py-2 border-r border-[#00385c]">Núm. Documento</th>
                              <th className="px-4 py-2 border-r border-[#00385c]">NIT/NRC</th>
                              <th className="px-4 py-2 border-r border-[#00385c]">Razón Social</th>
                              <th className="px-4 py-2 border-r border-[#00385c] text-right">Gravado ($)</th>
                              <th className="px-4 py-2 border-r border-[#00385c] text-right">IVA ($)</th>
                              <th className="px-4 py-2 text-right">Total ($)</th>
                            </tr>
                          </thead>
                          <tbody className="text-slate-600 divide-y divide-slate-100">
                            {data.registros.map((row, idx) => {
                              let fecha, tipo, doc, nit, nombre, gravado, iva, total;
                              if (tipoKey === 'compras') {
                                fecha = row[0]; tipo = row[2]; doc = row[3]; nit = row[4]; nombre = row[5];
                                gravado = (parseFloat(row[9]) + parseFloat(row[11]) + parseFloat(row[12])).toFixed(2);
                                iva = row[13]; total = row[14];
                              } else if (tipoKey === 'ventasContribuyentes') {
                                fecha = row[0]; tipo = row[2]; doc = row[5]; nit = row[7]; nombre = row[8];
                                gravado = row[11]; iva = row[12]; total = row[15];
                              } else {
                                fecha = row[0]; tipo = row[2]; doc = row[7]; nit = "N/A"; nombre = "Consumidor Final";
                                gravado = row[13]; iva = "0.00"; total = row[19];
                              }
                              return (
                                <tr key={idx} className="hover:bg-slate-50">
                                  <td className="px-4 py-2 border-r border-slate-100">{fecha}</td>
                                  <td className="px-4 py-2 border-r border-slate-100 text-center">{tipo}</td>
                                  <td className="px-4 py-2 border-r border-slate-100 font-mono">{doc}</td>
                                  <td className="px-4 py-2 border-r border-slate-100">{nit}</td>
                                  <td className="px-4 py-2 border-r border-slate-100 truncate max-w-[200px]" title={nombre}>{nombre}</td>
                                  <td className="px-4 py-2 border-r border-slate-100 text-right">{gravado}</td>
                                  <td className="px-4 py-2 border-r border-slate-100 text-right">{iva}</td>
                                  <td className="px-4 py-2 text-right font-bold">{total}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {activeTab === 'admitidos' && (!data.registros || data.registros.length === 0) && (
                      <p className="text-center text-slate-500 py-4">No hay archivos admitidos.</p>
                    )}

                    {activeTab === 'rechazados' && data.omitidos && data.omitidos.length > 0 && (
                      <div className="flex flex-col md:flex-row gap-4">
                        {/* Columna Izquierda: Lista */}
                        <div className="w-full md:w-1/3 border border-red-200 rounded bg-white overflow-hidden flex flex-col h-96 shadow-inner">
                          <div className="bg-red-600 text-white px-3 py-2 text-xs font-semibold uppercase sticky top-0">Archivos y Motivos</div>
                          <div className="overflow-y-auto flex-1 divide-y divide-red-100 bg-red-50/30">
                            {data.omitidos.map((omi, idx) => (
                              <div 
                                key={idx} 
                                onClick={() => setSelectedJson(omi.contenido || '{"error": "Contenido JSON no disponible"}')}
                                className="p-3 hover:bg-red-100 cursor-pointer transition border-l-4 border-transparent hover:border-red-500"
                              >
                                <p className="font-mono text-red-700 text-xs font-bold mb-1 break-all">{omi.archivo}</p>
                                <p className="text-xs text-slate-700">{omi.motivo}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                        
                        {/* Columna Derecha: JSON Viewer */}
                        <div className="w-full md:w-2/3 border border-slate-700 rounded bg-[#1e1e1e] overflow-hidden flex flex-col h-96 shadow-lg">
                          <div className="bg-[#2d2d2d] text-slate-300 px-3 py-2 text-xs font-semibold uppercase flex justify-between items-center border-b border-black">
                            <span className="flex items-center"><svg className="w-4 h-4 mr-1 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg> Inconsistencia JSON</span>
                            {selectedJson && (
                              <button className="text-blue-400 hover:text-blue-300 transition" onClick={() => navigator.clipboard.writeText(selectedJson)}>Copiar al portapapeles</button>
                            )}
                          </div>
                          <div className="overflow-y-auto flex-1 p-4 text-[11px] leading-relaxed font-mono text-[#d4d4d4]">
                            {selectedJson ? (
                              <pre className="whitespace-pre-wrap break-all">{selectedJson}</pre>
                            ) : (
                              <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3">
                                <svg className="w-12 h-12 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                                <p className="italic text-center">Selecciona un archivo de la lista izquierda<br/>para inspeccionar su contenido interno</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    {activeTab === 'rechazados' && (!data.omitidos || data.omitidos.length === 0) && (
                      <p className="text-center text-slate-500 py-4">No hay archivos rechazados.</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
