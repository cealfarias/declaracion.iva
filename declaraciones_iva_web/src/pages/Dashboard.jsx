import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';
import axios from 'axios';

const APP_VERSION = "v1.6 (API Fix)";

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
  
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTabs, setActiveTabs] = useState({ compras: 'admitidos', ventasContribuyentes: 'admitidos', ventasConsumidor: 'admitidos' });
  const [activeWizardTab, setActiveWizardTab] = useState('subir_detalle');
  const [selectedJson, setSelectedJson] = useState('');

  const meses = [
    { id: 1, nombre: 'Enero' }, { id: 2, nombre: 'Febrero' }, { id: 3, nombre: 'Marzo' },
    { id: 4, nombre: 'Abril' }, { id: 5, nombre: 'Mayo' }, { id: 6, nombre: 'Junio' },
    { id: 7, nombre: 'Julio' }, { id: 8, nombre: 'Agosto' }, { id: 9, nombre: 'Septiembre' },
    { id: 10, nombre: 'Octubre' }, { id: 11, nombre: 'Noviembre' }, { id: 12, nombre: 'Diciembre' }
  ];

  const cargarDatosHistoricos = async () => {
    try {
      const resp = await axios.get(`${API_URL}/api/v1/procesar/consultar`, {
        params: { mes, anio, usuario_id: user?.id || 1 }
      });
      if (resp.data.data === null) {
        setResumen(null);
      } else {
        setResumen(resp.data);
      }
    } catch (error) {
      console.error("Error al cargar datos del periodo:", error);
    }
  };

  useEffect(() => {
    cargarDatosHistoricos();
  }, [mes, anio]);

  const handleFileChange = (e, tipo) => {
    if (e.target.files) {
      setArchivos({
        ...archivos,
        [tipo]: Array.from(e.target.files)
      });
    }
  };

  const handleProcesarTodo = async () => {
    if (!archivos.compras.length && !archivos.ventasContribuyentes.length && !archivos.ventasConsumidor.length) {
      enqueueMessages([{ text: "Por favor selecciona al menos una carpeta con archivos JSON.", type: 'warning' }]);
      return;
    }

    setLoading(true);
    let allOmitidos = [];
    let countAdmitidos = 0;
    
    const processFiles = async (tipo, endpoint) => {
      if (archivos[tipo].length > 0) {
        const formData = new FormData();
        archivos[tipo].forEach(file => {
          formData.append('files', file);
        });
        formData.append('mes', mes);
        formData.append('anio', anio);
        formData.append('usuario_id', user?.id || 1);
        
        try {
          const resp = await axios.post(`${API_URL}/api/v1${endpoint}`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          
          if (resp.data.omitidos && resp.data.omitidos.length > 0) {
            allOmitidos = [...allOmitidos, ...resp.data.omitidos];
          }
          if (resp.data.resumen) {
            countAdmitidos += resp.data.resumen.documentos || 0;
          }
        } catch (error) {
          enqueueMessages([{ text: `Error al procesar ${tipo}: ${error.message}`, type: 'error' }]);
        }
      }
    };

    await processFiles('compras', '/procesar/compras');
    await processFiles('ventasContribuyentes', '/procesar/ventas-contribuyentes');
    await processFiles('ventasConsumidor', '/procesar/ventas-consumidor');

    await cargarDatosHistoricos();
    setLoading(false);
    
    const msgs = [];
    if (countAdmitidos > 0) {
      msgs.push({ text: `Se procesaron y admitieron ${countAdmitidos} documentos exitosamente.`, type: 'success' });
    }
    if (allOmitidos.length > 0) {
      msgs.push({ text: `Se omitieron o rechazaron ${allOmitidos.length} archivos por inconsistencias. Revisa la pestaña de archivos rechazados para ver el detalle.`, type: 'warning' });
    }
    if (msgs.length > 0) {
      enqueueMessages(msgs);
    }
  };

  const descargarCSV = (csvContent, filename) => {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleTabChange = (tipoKey, tabName) => {
    setActiveTabs(prev => ({ ...prev, [tipoKey]: tabName }));
  };

  const renderResumen = (tipoKey, titulo = "") => {
    const data = resumen[tipoKey];
    if (!data) return null;
    const activeTab = activeTabs[tipoKey] || 'admitidos';
    
    return (
      <div key={tipoKey} className="bg-white p-6 rounded shadow-sm border border-slate-200 mb-8">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-[#004b79] uppercase text-lg">{titulo || data.filename.replace(/_/g, ' ')}</h3>
          <div className="space-x-3">
            <span className="text-sm px-4 py-1.5 bg-[#004b79] text-white rounded-full font-medium">
              {data.documentos} DTEs Validados
            </span>
            {data.csv && (
              <button 
                onClick={() => descargarCSV(data.csv, data.filename)}
                className="text-sm px-4 py-1.5 bg-green-600 hover:bg-green-700 transition text-white rounded shadow-sm inline-flex items-center font-medium"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                Descargar CSV
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Monto Gravado</p>
            <p className="text-xl font-bold text-[#004b79]">${data.gravado?.toFixed(2)}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Crédito / Débito Fiscal</p>
            <p className="text-xl font-bold text-[#004b79]">${data.iva?.toFixed(2)}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Total General</p>
            <p className="text-xl font-bold text-[#004b79]">${data.total?.toFixed(2)}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Omitidos / Rechazados</p>
            <p className="text-xl font-bold text-red-600">{data.omitidos?.length || 0}</p>
          </div>
        </div>

        <div>
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
                  {data.registros.map((reg, idx) => {
                    let fecha = '', tipo = '', doc = '', nit = '', nombre = '', gravado = '', iva = '', total = '';
                    if (tipoKey === 'compras') {
                      fecha = reg[0]; tipo = reg[2]; doc = reg[3]; nit = reg[4]; nombre = reg[5]; gravado = (parseFloat(reg[9])+parseFloat(reg[11])+parseFloat(reg[12])).toFixed(2); iva = reg[13]; total = reg[14];
                    } else if (tipoKey === 'ventasContribuyentes') {
                      fecha = reg[0]; tipo = reg[2]; doc = reg[5] || reg[7]; nit = reg[7]; nombre = reg[8]; gravado = reg[11]; iva = reg[12]; total = reg[15];
                    } else if (tipoKey === 'ventasConsumidor') {
                      fecha = reg[0]; tipo = reg[2]; doc = reg[8]; nit = ''; nombre = ''; gravado = reg[13]; iva = '0.00'; total = reg[19];
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
              <div className="w-full md:w-1/3 border border-red-200 rounded bg-white overflow-hidden flex flex-col h-[500px] shadow-inner">
                <div className="bg-red-600 text-white px-3 py-2 text-xs font-semibold uppercase sticky top-0">Archivos y Motivos</div>
                <div className="overflow-y-auto flex-1 divide-y divide-red-100 bg-red-50/30">
                  {data.omitidos.map((omi, idx) => (
                    <div 
                      key={idx} 
                      onClick={() => setSelectedJson(omi.contenido || '{"error": "Contenido JSON no disponible"}')}
                      className="p-3 hover:bg-red-100 cursor-pointer transition border-l-4 border-transparent hover:border-red-500"
                    >
                      <p className="font-mono text-red-700 text-[10px] font-bold mb-1 break-all leading-tight">{omi.archivo}</p>
                      <p className="text-xs text-slate-700 leading-snug">{omi.motivo}</p>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="w-full md:w-2/3 border border-slate-700 rounded bg-[#1e1e1e] overflow-hidden flex flex-col h-[500px] shadow-lg">
                <div className="bg-[#2d2d2d] text-slate-300 px-3 py-2 text-xs font-semibold uppercase flex justify-between items-center border-b border-black">
                  <span className="flex items-center"><svg className="w-4 h-4 mr-1 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg> Inconsistencia JSON</span>
                  {selectedJson && (
                    <button className="text-blue-400 hover:text-blue-300 transition" onClick={() => navigator.clipboard.writeText(selectedJson)}>Copiar</button>
                  )}
                </div>
                <div className="overflow-y-auto flex-1 p-4 text-[11px] leading-relaxed font-mono text-[#d4d4d4]">
                  {selectedJson ? (
                    <pre className="whitespace-pre-wrap break-all">{selectedJson}</pre>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3">
                      <p className="italic text-center">Selecciona un archivo en la izquierda para ver su contenido</p>
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
      </div>
    );
  };

  const sumaVentasGravadas = (resumen?.ventasContribuyentes?.gravado || 0) + (resumen?.ventasConsumidor?.gravado || 0);
  const debitoFiscalReal = sumaVentasGravadas * 0.13;
  const creditoFiscalReal = (resumen?.compras?.iva || 0);
  const impuestoDeterminado = debitoFiscalReal > creditoFiscalReal ? debitoFiscalReal - creditoFiscalReal : 0;
  const remanenteFavor = creditoFiscalReal > debitoFiscalReal ? creditoFiscalReal - debitoFiscalReal : 0;

  const TabButton = ({ id, icon, label }) => (
    <button 
      onClick={() => setActiveWizardTab(id)}
      className={`flex flex-col items-center justify-center py-4 px-6 min-w-[160px] flex-1 border-b-4 transition-all duration-200 ${
        activeWizardTab === id 
          ? 'border-[#004b79] text-[#004b79] bg-slate-50' 
          : 'border-transparent text-slate-400 hover:text-slate-600 hover:bg-slate-50'
      }`}
    >
      <div className={`mb-2 ${activeWizardTab === id ? 'text-[#004b79]' : 'text-slate-400'}`}>
        {icon}
      </div>
      <span className="text-[11px] font-bold uppercase tracking-wider text-center h-8 leading-tight flex items-center justify-center">{label}</span>
    </button>
  );

  return (
    <div className="min-h-screen bg-slate-100 font-sans flex flex-col">
      <div className="bg-[#5a1e2f] text-white py-2 px-6 flex justify-between items-center text-sm shadow-sm relative z-10">
        <div className="flex items-center space-x-4 font-bold">
          <span className="uppercase tracking-wider">Ministerio de Hacienda</span>
        </div>
        <div className="text-right hidden md:block">
          <span>Nombre: <span className="font-bold bg-blue-100 text-[#004b79] px-2 py-0.5 rounded">{user?.nombre || 'Usuario'}</span></span>
          <span className="ml-4">Versión del Sistema <span className="font-mono bg-blue-100 text-[#004b79] px-2 py-0.5 rounded ml-1">{APP_VERSION}</span></span>
        </div>
      </div>

      <div className="bg-[#004b79] text-white px-6 py-2 flex items-center text-xs font-bold uppercase space-x-6 tracking-wide shadow-sm z-0">
        <span className="text-blue-200 cursor-pointer">Inicio</span>
        <span className="cursor-pointer">Declaraciones</span>
        <span className="text-blue-200 cursor-pointer">Informes</span>
      </div>

      <div className="bg-white border-b border-slate-200 shadow-sm px-6 py-4 flex flex-wrap gap-6 items-end relative z-0">
        <div>
          <label className="block text-[11px] font-bold text-slate-500 mb-1 uppercase">Ejercicio:</label>
          <select 
            value={anio} 
            onChange={(e) => setAnio(parseInt(e.target.value))}
            className="w-32 border border-slate-300 p-2 text-sm rounded focus:ring-1 focus:ring-[#004b79] focus:border-[#004b79] outline-none"
          >
            {[2023, 2024, 2025, 2026, 2027].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-bold text-slate-500 mb-1 uppercase">Periodo:</label>
          <select 
            value={mes} 
            onChange={(e) => setMes(parseInt(e.target.value))}
            className="w-40 border border-slate-300 p-2 text-sm rounded focus:ring-1 focus:ring-[#004b79] focus:border-[#004b79] outline-none"
          >
            {meses.map(m => <option key={m.id} value={m.id}>{m.nombre}</option>)}
          </select>
        </div>
        <div className="ml-auto flex flex-col items-end">
          <button onClick={() => {
            if(activeWizardTab==='subir_detalle') setActiveWizardTab('ventas');
            else if(activeWizardTab==='ventas') setActiveWizardTab('compras');
            else if(activeWizardTab==='compras') setActiveWizardTab('liquidacion');
            else if(activeWizardTab==='liquidacion') setActiveWizardTab('subir_detalle');
          }} className="bg-[#5cb85c] hover:bg-[#4cae4c] text-white px-8 py-3 rounded shadow flex items-center font-bold transition uppercase tracking-wider text-sm">
            Siguiente <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
          </button>
        </div>
      </div>

      <div className="bg-white border-b border-slate-200 shadow-sm overflow-x-auto">
        <div className="flex min-w-max px-2 max-w-5xl mx-auto">
          <TabButton 
            id="subir_detalle" 
            label="Subir Detalle de Ventas y Compras" 
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>} 
          />
          <TabButton 
            id="ventas" 
            label="Ventas y Débitos" 
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>} 
          />
          <TabButton 
            id="compras" 
            label="Compras y Créditos" 
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>} 
          />
          <TabButton 
            id="liquidacion" 
            label="Liquidación del Periodo" 
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>} 
          />
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8">
        {activeWizardTab === 'subir_detalle' && (
          <div className="bg-white border border-slate-200 rounded shadow-sm p-6 animate-in fade-in zoom-in-95 duration-300">
            <div className="border-b-2 border-orange-400 pb-2 mb-6">
              <h2 className="text-lg font-bold text-slate-700">Subir Detalle de Ventas y Compras</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="border border-slate-200 rounded overflow-hidden shadow-sm hover:shadow-md transition bg-white flex flex-col h-full">
                <div className="bg-[#004b79] p-4 flex items-center justify-center text-white h-20">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
                </div>
                <div className="p-4 flex flex-col flex-1">
                  <h3 className="font-bold text-[#004b79] mb-1 text-sm uppercase">Detalle de Compras</h3>
                  <p className="text-xs text-slate-500 mb-4 flex-1">Sube los DTEs de compras y créditos fiscales recibidos.</p>
                  <label className="w-full relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                    <span className="text-xs font-medium text-center">Haz clic para seleccionar carpeta</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
                  </label>
                  {archivos.compras.length > 0 && <p className="mt-2 text-xs text-green-600 font-bold text-center">✓ {archivos.compras.length} archivos listos</p>}
                </div>
              </div>

              <div className="border border-slate-200 rounded overflow-hidden shadow-sm hover:shadow-md transition bg-white flex flex-col h-full">
                <div className="bg-[#004b79] p-4 flex items-center justify-center text-white h-20">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                </div>
                <div className="p-4 flex flex-col flex-1">
                  <h3 className="font-bold text-[#004b79] mb-1 text-sm uppercase">Detalle de Ventas a Contribuyentes</h3>
                  <p className="text-xs text-slate-500 mb-4 flex-1">Sube los Créditos Fiscales emitidos.</p>
                  <label className="w-full relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                    <span className="text-xs font-medium text-center">Haz clic para seleccionar carpeta</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
                  </label>
                  {archivos.ventasContribuyentes.length > 0 && <p className="mt-2 text-xs text-green-600 font-bold text-center">✓ {archivos.ventasContribuyentes.length} archivos listos</p>}
                </div>
              </div>

              <div className="border border-slate-200 rounded overflow-hidden shadow-sm hover:shadow-md transition bg-white flex flex-col h-full">
                <div className="bg-[#004b79] p-4 flex items-center justify-center text-white h-20">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
                </div>
                <div className="p-4 flex flex-col flex-1">
                  <h3 className="font-bold text-[#004b79] mb-1 text-sm uppercase">Detalle de Ventas Consumidor Final</h3>
                  <p className="text-xs text-slate-500 mb-4 flex-1">Sube las Facturas emitidas a consumidores.</p>
                  <label className="w-full relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                    <span className="text-xs font-medium text-center">Haz clic para seleccionar carpeta</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
                  </label>
                  {archivos.ventasConsumidor.length > 0 && <p className="mt-2 text-xs text-green-600 font-bold text-center">✓ {archivos.ventasConsumidor.length} archivos listos</p>}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button 
                onClick={handleProcesarTodo}
                disabled={loading || (archivos.compras.length === 0 && archivos.ventasContribuyentes.length === 0 && archivos.ventasConsumidor.length === 0)}
                className={`flex items-center space-x-2 px-8 py-3 rounded font-bold shadow transition ${loading || (archivos.compras.length === 0 && archivos.ventasContribuyentes.length === 0 && archivos.ventasConsumidor.length === 0) ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-[#004b79] hover:bg-[#00385c] text-white'}`}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    Procesando Archivos...
                  </>
                ) : (
                  <>
                    <span>Cargar Datos al Servidor</span>
                    <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {activeWizardTab === 'ventas' && (
          <div className="animate-in fade-in zoom-in-95 duration-300 space-y-6">
            <div className="border-b-2 border-orange-400 pb-2 mb-2">
              <h2 className="text-lg font-bold text-slate-700">Ventas de Bienes y/o Servicios</h2>
            </div>
            {resumen && resumen.ventasContribuyentes ? renderResumen('ventasContribuyentes', 'Ventas a Contribuyentes (CCF)') : <p className="text-sm text-slate-500">No hay datos de CCF procesados en este periodo.</p>}
            {resumen && resumen.ventasConsumidor ? renderResumen('ventasConsumidor', 'Ventas a Consumidor Final (FCF)') : <p className="text-sm text-slate-500">No hay datos de FCF procesados en este periodo.</p>}
          </div>
        )}

        {activeWizardTab === 'compras' && (
          <div className="animate-in fade-in zoom-in-95 duration-300 space-y-6">
            <div className="border-b-2 border-orange-400 pb-2 mb-2">
              <h2 className="text-lg font-bold text-slate-700">Compras de Bienes y/o Servicios</h2>
            </div>
            {resumen && resumen.compras ? renderResumen('compras', 'Detalle de Compras (CCF recibidos)') : <p className="text-sm text-slate-500">No hay datos de Compras procesados en este periodo.</p>}
          </div>
        )}

        {activeWizardTab === 'liquidacion' && (
          <div className="animate-in fade-in zoom-in-95 duration-300">
            <div className="border-b-2 border-orange-400 pb-2 mb-6">
              <h2 className="text-lg font-bold text-slate-700">Liquidación del Impuesto del Periodo</h2>
            </div>
            <div className="bg-white border border-slate-200 rounded shadow-sm p-0 max-w-5xl mx-auto overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-4 font-bold text-slate-700 w-1/2 uppercase text-xs">Ventas (Débitos)</th>
                    <th className="px-6 py-4 font-bold text-slate-700 w-1/2 uppercase text-xs border-l border-slate-200">Compras (Créditos)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="bg-white">
                    <td className="px-6 py-4 flex justify-between items-center">
                      <span className="text-slate-600">Suma de Ventas Gravadas</span>
                      <span className="font-mono font-bold">${sumaVentasGravadas.toFixed(2)}</span>
                    </td>
                    <td className="px-6 py-4 flex justify-between items-center border-l border-slate-200">
                      <span className="text-slate-600">Suma de Compras Gravadas</span>
                      <span className="font-mono font-bold">${(resumen?.compras?.gravado || 0).toFixed(2)}</span>
                    </td>
                  </tr>
                  <tr className="bg-slate-50">
                    <td className="px-6 py-4 flex justify-between items-center">
                      <span className="font-bold text-slate-700">Suma de Débitos (IVA Ventas 13%)</span>
                      <span className="font-mono text-lg text-red-600 font-bold">${debitoFiscalReal.toFixed(2)}</span>
                    </td>
                    <td className="px-6 py-4 flex justify-between items-center border-l border-slate-200">
                      <span className="font-bold text-slate-700">Suma de Créditos (IVA Compras)</span>
                      <span className="font-mono text-lg text-green-600 font-bold">${creditoFiscalReal.toFixed(2)}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div className="border-t-4 border-slate-300 p-6 bg-white">
                {impuestoDeterminado > 0 ? (
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="font-bold text-red-800 text-lg uppercase block">Impuesto Determinado</span>
                      <span className="text-xs text-slate-500">(Cuando el débito excede al crédito)</span>
                    </div>
                    <span className="font-mono text-3xl font-bold text-red-700">${impuestoDeterminado.toFixed(2)}</span>
                  </div>
                ) : (
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="font-bold text-green-800 text-lg uppercase block">Remanente de Crédito para el Próximo Periodo</span>
                      <span className="text-xs text-slate-500">(Cuando el crédito excede al débito)</span>
                    </div>
                    <span className="font-mono text-3xl font-bold text-green-700">${remanenteFavor.toFixed(2)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
