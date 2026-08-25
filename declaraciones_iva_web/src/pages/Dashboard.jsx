import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const APP_VERSION = "v1.2 (Commit 302147d)";

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
    const allFiles = Array.from(e.target.files);
    // Filtrar solo los archivos .json de la carpeta seleccionada
    const jsonFiles = allFiles.filter(file => file.name.toLowerCase().endsWith('.json'));
    
    setArchivos({
      ...archivos,
      [tipo]: jsonFiles
    });
  };

  const [resumen, setResumen] = useState(null);
  
  // Nuevo useEffect para buscar automáticamente si hay datos en el periodo seleccionado
  useEffect(() => {
    const checkPeriodo = async () => {
      if (!user?.id) return;
      try {
        setLoading(true);
        const response = await axios.get(`${API_URL}/api/v1/procesar/consultar`, {
          params: { mes, anio, usuario_id: user.id }
        });
        
        if (response.data?.data) {
          setResumen(response.data.data);
          setMessages([{ text: `ℹ️ Se cargaron los datos guardados para ${mes}/${anio}.`, type: 'success' }]);
        } else {
          setResumen(null);
          setMessages([]);
        }
      } catch (error) {
        console.error("Error buscando periodo", error);
      } finally {
        setLoading(false);
      }
    };
    checkPeriodo();
  }, [mes, anio, user]);

  const processFiles = async (tipo, endpoint, filename) => {
    if (archivos[tipo].length === 0) return;
    
    const formData = new FormData();
    archivos[tipo].forEach(file => {
      formData.append('files', file);
    });
    
    formData.append('mes', mes);
    formData.append('anio', anio);
    formData.append('usuario_id', user.id);

    try {
      const response = await axios.post(`${API_URL}/api/v1/${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'json' 
      });

      const { csv, resumen: resumen_data, registros, omitidos } = response.data;
      
      setResumen((prev) => ({
        ...prev,
        [tipo]: { ...resumen_data, filename, registros, omitidos, csv }
      }));

      // Descargar CSV automáticamente
      if (csv && csv.trim().length > 0) {
        descargarCSV(csv, filename);
      }
      
      setMessages(prev => [...prev, { text: `✅ Nuevos DTEs de ${filename} procesados y guardados.`, type: 'success' }]);
    } catch (error) {
      const errMsg = error.response?.data?.detail || `Error al procesar ${filename}`;
      setMessages(prev => [...prev, { text: `❌ ${errMsg}`, type: 'error' }]);
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
    setMessages([]);
    // Conservamos resumen previo por si estamos agregando nuevos DTEs
    
    if (archivos.compras.length > 0) {
      await processFiles('compras', 'procesar/compras', 'F07_Anexo_Compras');
    }
    if (archivos.ventasContribuyentes.length > 0) {
      await processFiles('ventasContribuyentes', 'procesar/ventas-contribuyentes', 'F07_Anexo_Ventas_CCF');
    }
    if (archivos.ventasConsumidor.length > 0) {
      await processFiles('ventasConsumidor', 'procesar/ventas-consumidor', 'F07_Anexo_Ventas_FCF');
    }
    
    // Limpiar archivos despues de subidos
    setArchivos({ compras: [], ventasContribuyentes: [], ventasConsumidor: [] });
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-100 font-sans">
      {/* Header Superior Blanco */}
      <div className="bg-white py-6 flex flex-col items-center justify-center shadow-sm relative">
        <h1 className="text-3xl text-slate-700 font-normal">Procesamiento de Declaración de IVA</h1>
        <h2 className="text-xl text-slate-600 font-light mt-1">Generador de Anexos F-07</h2>
        <p className="text-sm text-slate-500 mt-1">demiempresa.online</p>
        
        {/* User Info flotante */}
        <div className="absolute right-6 top-6 text-right hidden sm:block">
          <p className="text-sm font-semibold text-slate-700">Usuario Activo:</p>
          <p className="text-sm text-slate-600">{user?.nombre || 'Usuario'}</p>
          <p className="text-xs font-mono text-slate-400 mt-1 px-2 py-0.5 bg-slate-100 rounded-full border border-slate-200">
            {APP_VERSION}
          </p>
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
      <main className="max-w-7xl mx-auto p-4 sm:p-6 mt-6">
        
        <div className="text-center mb-8">
          <h3 className="text-xl font-bold text-slate-800 uppercase tracking-wide">Procesamiento de Declaración de IVA</h3>
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

        {/* Panel de Archivos */}
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
                  <span className="font-bold text-green-600">{archivos.compras.length} archivos JSON listos</span>
                ) : (
                  <span>Haz clic para seleccionar la carpeta contenedora</span>
                )}
              </div>
              <input type="file" webkitdirectory="true" directory="true" multiple className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
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
                  <span className="font-bold text-green-600">{archivos.ventasContribuyentes.length} archivos JSON listos</span>
                ) : (
                  <span>Haz clic para seleccionar la carpeta contenedora</span>
                )}
              </div>
              <input type="file" webkitdirectory="true" directory="true" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
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
                  <span className="font-bold text-green-600">{archivos.ventasConsumidor.length} archivos JSON listos</span>
                ) : (
                  <span>Haz clic para seleccionar la carpeta contenedora</span>
                )}
              </div>
              <input type="file" webkitdirectory="true" directory="true" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
            </label>
          </div>
        </div>

        {/* Asistente Virtual / Avatar de Mensajes */}
        {messages.length > 0 && (
          <div className="mb-8 flex items-end space-x-4 max-w-4xl mx-auto">
            <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-[#004b79] to-[#337ab7] flex items-center justify-center shadow-lg border-2 border-white shrink-0 animate-bounce-short">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <div className="flex-1 bg-white p-5 rounded-2xl rounded-bl-none shadow-md border border-blue-100 relative">
              <div className="absolute w-4 h-4 bg-white border-b border-l border-blue-100 transform rotate-45 -left-[8.5px] bottom-5"></div>
              <p className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-wider flex items-center">
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                Asistente del Sistema
              </p>
              <div className="space-y-3">
                {messages.map((msg, i) => {
                  const cleanText = msg.text.replace('✅', '').replace('❌', '').replace('ℹ️', '').trim();
                  return (
                    <div key={i} className={`text-sm flex items-start ${msg.type === 'error' ? 'text-red-700 bg-red-50 p-2 rounded' : 'text-[#004b79] bg-blue-50 p-2 rounded'}`}>
                      <span className="mr-2 text-lg leading-none">{msg.type === 'error' ? '❌' : (msg.text.includes('ℹ️') ? 'ℹ️' : '✅')}</span>
                      <span className="font-medium">{cleanText}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
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
                <span>Procesar y Descargar CSV</span>
              </>
            )}
          </button>
        </div>

        {/* Cuadro Resumen Extendido (Grilla de Datos) */}
        {resumen && (
          <div className="bg-white border border-blue-300 rounded shadow-sm p-6 mb-8 mt-4 border-t-4 border-t-[#004b79]">
            <h2 className="text-lg font-bold text-[#004b79] uppercase mb-6 text-center border-b pb-4">Detalle y Validación de Declaración</h2>
            <div className="space-y-12">
              {Object.keys(resumen).map((tipoKey) => {
                const data = resumen[tipoKey];
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
                            className="text-xs px-3 py-1 bg-green-600 hover:bg-green-700 transition text-white rounded shadow-sm"
                          >
                            Descargar CSV
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Resumen Numeros */}
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

                    {/* Tabla de Registros Exitosos */}
                    {data.registros && data.registros.length > 0 && (
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
                              // Adaptación de los índices de CSV según el anexo para previsualizar:
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

                    {/* Alertas de Omitidos */}
                    {data.omitidos && data.omitidos.length > 0 && (
                      <div className="mt-4 bg-red-50 border border-red-200 rounded p-4">
                        <h4 className="font-bold text-red-700 text-sm mb-2 flex items-center">
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                          Documentos Omitidos (No incluidos en el CSV)
                        </h4>
                        <ul className="list-disc pl-5 text-xs text-red-600 space-y-1">
                          {data.omitidos.map((omi, idx) => (
                            <li key={idx}><strong>{omi.archivo}</strong>: {omi.motivo}</li>
                          ))}
                        </ul>
                      </div>
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
