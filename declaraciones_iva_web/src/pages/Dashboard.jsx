import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';
import axios from 'axios';
import { useGoogleLogin } from '@react-oauth/google';

const APP_VERSION = "v2.1 (Integración Gmail)";

export default function Dashboard() {
  const { user, logout, activeEmpresa } = useAuth();
  
  const [loadingGmail, setLoadingGmail] = useState(false);
  const { say, enqueueMessages } = useAssistant();

  const handleGmailImport = useGoogleLogin({
    scope: 'https://www.googleapis.com/auth/gmail.readonly',
    onSuccess: async (tokenResponse) => {
      try {
        setLoadingGmail(true);
        enqueueMessages([{ text: "Buscando DTEs en tu correo, esto puede tomar unos segundos...", type: "info" }]);
        
        let targetTipo = '';
        if (activeWizardTab === 'compras') targetTipo = 'compras';
        else if (activeWizardTab === 'ventas_ccf') targetTipo = 'ventas_ccf';
        else if (activeWizardTab === 'ventas_fcf') targetTipo = 'ventas_consumidor';

        const formData = new FormData();
        formData.append('access_token', tokenResponse.access_token);
        formData.append('tipo_anexo', targetTipo);
        formData.append('mes', mes);
        formData.append('anio', anio);
        formData.append('empresa_id', activeEmpresa?.id || 1);

        const resp = await axios.post(`${API_URL}/api/v1/procesar/gmail`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        if (resp.data.documentos === undefined) {
           // Si devolvió el mensaje de que no encontró
           enqueueMessages([{ text: resp.data.message || "No se encontraron adjuntos en Gmail.", type: "warning" }]);
        } else {
           await cargarDatosHistoricos();
           enqueueMessages([{ text: `Se extrajeron ${resp.data.documentos} documentos de Gmail exitosamente.`, type: 'success' }]);
        }
      } catch (error) {
        enqueueMessages([{ text: `Error al importar de Gmail: ${error.response?.data?.detail || error.message}`, type: 'error' }]);
      } finally {
        setLoadingGmail(false);
      }
    },
    onError: (error) => {
      enqueueMessages([{ text: "Error de autenticación con Google.", type: "error" }]);
    }
  });


  const fmt = (val) => {
    const num = parseFloat(val);
    return isNaN(num) ? '0.00' : num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
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
  const [activeWizardTab, setActiveWizardTab] = useState('compras');
  const [selectedJson, setSelectedJson] = useState('');
  const [remanenteAnterior, setRemanenteAnterior] = useState(0.0);

  const meses = [
    { id: 1, nombre: 'Enero' }, { id: 2, nombre: 'Febrero' }, { id: 3, nombre: 'Marzo' },
    { id: 4, nombre: 'Abril' }, { id: 5, nombre: 'Mayo' }, { id: 6, nombre: 'Junio' },
    { id: 7, nombre: 'Julio' }, { id: 8, nombre: 'Agosto' }, { id: 9, nombre: 'Septiembre' },
    { id: 10, nombre: 'Octubre' }, { id: 11, nombre: 'Noviembre' }, { id: 12, nombre: 'Diciembre' }
  ];

  const cargarDatosHistoricos = async (isAutoLoad = false) => {
    try {
      const resp = await axios.get(`${API_URL}/api/v1/procesar/consultar`, {
        params: { mes, anio, empresa_id: activeEmpresa?.id || 1 }
      });
      if (resp.data.data === null) {
        setResumen(null);
      } else {
        setResumen(resp.data.data);
        if (isAutoLoad) {
          const nombreMes = meses.find(m => m.id === mes)?.nombre || '';
          enqueueMessages([{ text: `Se cargaron los libros precargados del mes ${nombreMes} desde la base de datos.`, type: "success" }]);
        }
        if(resp.data.data.remanente_anterior) setRemanenteAnterior(resp.data.data.remanente_anterior);
      }
    } catch (error) {
      console.error("Error al cargar datos del periodo:", error);
    }
  };

  useEffect(() => {
    cargarDatosHistoricos(true);
  }, [mes, anio]);

  const handleFileChange = (e, tipo) => {
    if (e.target.files) {
      setArchivos({
        ...archivos,
        [tipo]: Array.from(e.target.files)
      });
    }
  };

  const handleProcesar = async (tipo, endpoint) => {
    if (archivos[tipo].length === 0) return;

    setLoading(true);
    const formData = new FormData();
    archivos[tipo].forEach(file => {
      formData.append('files', file);
    });
    formData.append('mes', mes);
    formData.append('anio', anio);
    formData.append('usuario_id', user?.id || 1);
    
    try {
      await axios.post(`${API_URL}/api/v1${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      await cargarDatosHistoricos();
      enqueueMessages([{ text: `Se procesó ${tipo} correctamente.`, type: 'success' }]);
    } catch (error) {
      enqueueMessages([{ text: `Error al procesar: ${error.message}`, type: 'error' }]);
    } finally {
      setLoading(false);
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
    
    let registrosSorted = [];
    if (data.registros) {
      registrosSorted = [...data.registros].sort((a, b) => {
        try {
          const [d1, m1, y1] = a[0].split('/');
          const [d2, m2, y2] = b[0].split('/');
          const date1 = new Date(y1, m1 - 1, d1);
          const date2 = new Date(y2, m2 - 1, d2);
          return date1 - date2;
        } catch(e) {
          return 0;
        }
      });
    }

    return (
      <div key={tipoKey} className="bg-white p-6 rounded shadow-sm border border-slate-200 mb-8">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-[#004b79] uppercase text-lg">{titulo || data.filename.replace(/_/g, ' ')}</h3>
          <div className="space-x-3">
            <span className="text-sm px-4 py-1.5 bg-[#004b79] text-white rounded-full font-medium">
              {data.documentos} DTEs Validados
            </span>
            {data.csv && (
              <button type="button" 
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
              Archivos Admitidos ({registrosSorted.length})
            </button>
            <button
              onClick={() => handleTabChange(tipoKey, 'rechazados')}
              className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'rechazados' ? 'border-red-600 text-red-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
            >
              Archivos Rechazados ({data.omitidos?.length || 0})
            </button>
          </div>

          {activeTab === 'admitidos' && registrosSorted.length > 0 && (
            <div className="overflow-x-auto bg-white border border-slate-200 rounded pb-2">
              <table className="w-full text-left text-[10px] whitespace-nowrap min-w-max">
                <thead className="bg-[#004b79] text-white uppercase font-semibold">
                  {tipoKey === 'compras' && (
                    <tr>
                      <th className="px-3 py-2 border-r border-[#00385c]">N°</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Fecha</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Clase</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Tipo</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Núm. Documento</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">NIT/NRC/DUI</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Razón Social del Proveedor</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas (G)</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas (H)</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas (I)</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (J)</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (K)</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (L)</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (M)</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Crédito Fiscal (N)</th>
                      <th className="px-3 py-2 text-right">Total (O)</th>
                    </tr>
                  )}
                  {tipoKey === 'ventasContribuyentes' && (
                    <tr>
                      <th className="px-3 py-2 border-r border-[#00385c]">N°</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Fecha</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Clase</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Tipo</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Núm. Documento</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">NIT/NRC</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Razón Social del Cliente</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Exentas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas No Sujetas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Gravadas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Débito Fiscal</th>
                      <th className="px-3 py-2 text-right">Total Ventas</th>
                    </tr>
                  )}
                  {tipoKey === 'ventasConsumidor' && (
                    <tr>
                      <th className="px-3 py-2 border-r border-[#00385c]">N°</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Fecha</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Clase</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Tipo</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Núm. Documento</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Exentas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas No Sujetas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Gravadas</th>
                      <th className="px-3 py-2 text-right">Total Ventas</th>
                    </tr>
                  )}
                </thead>
                <tbody className="text-slate-700 divide-y divide-slate-100 font-mono">
                  {registrosSorted.map((reg, idx) => {
                    if (tipoKey === 'compras') {
                      const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; const doc = reg[3];
                      const nrc = reg[4] || reg[15]; const nombre = reg[5]; 
                      return (
                        <tr key={idx} className="hover:bg-blue-50 transition-colors">
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{nrc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 truncate max-w-[200px]" title={nombre}>{nombre}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[6])}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[7])}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[8])}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[9])}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[10])}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[11])}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[12])}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono text-blue-700 font-bold">{fmt(reg[13])}</td>
                          <td className="px-3 py-1.5 text-right font-mono font-bold text-slate-800">{fmt(reg[14])}</td>
                        </tr>
                      );
                    } else if (tipoKey === 'ventasContribuyentes') {
                      const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; 
                      const doc = reg[5] || reg[7]; const nrc = reg[7]; const nombre = reg[8];
                      const exe = reg[9]; const nosuj = reg[10]; const grav = reg[11];
                      const iva = reg[12]; const total = reg[15];
                      return (
                        <tr key={idx} className="hover:bg-blue-50 transition-colors">
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{nrc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 truncate max-w-[200px]" title={nombre}>{nombre}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(exe)}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(nosuj)}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(grav)}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono text-red-700 font-bold">{fmt(iva)}</td>
                          <td className="px-3 py-1.5 text-right font-mono font-bold text-slate-800">{fmt(total)}</td>
                        </tr>
                      );
                    } else if (tipoKey === 'ventasConsumidor') {
                      const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; 
                      const doc = reg[8]; const exe = reg[10]; const nosuj = reg[12]; 
                      const grav = reg[13]; const total = reg[19];
                      return (
                        <tr key={idx} className="hover:bg-blue-50 transition-colors">
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(exe)}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(nosuj)}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(grav)}</td>
                          <td className="px-3 py-1.5 text-right font-mono font-bold text-slate-800">{fmt(total)}</td>
                        </tr>
                      );
                    }
                  })}
                </tbody>
              </table>
            </div>
          )}
          {activeTab === 'admitidos' && (!registrosSorted || registrosSorted.length === 0) && (
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
                    <button type="button" className="text-blue-400 hover:text-blue-300 transition" onClick={() => navigator.clipboard.writeText(selectedJson)}>Copiar</button>
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
  const creditoFiscalReal = (resumen?.compras?.iva || 0) + remanenteAnterior;
  const impuestoDeterminado = debitoFiscalReal > creditoFiscalReal ? debitoFiscalReal - creditoFiscalReal : 0;
  const remanenteFavor = creditoFiscalReal > debitoFiscalReal ? creditoFiscalReal - debitoFiscalReal : 0;

  
  const handleGuardarLiquidacion = async () => {
    try {
      await axios.post(`${API_URL}/api/v1/procesar/guardar-remanente`, {
        mes, anio, empresa_id: activeEmpresa?.id || 1, remanente_anterior: parseFloat(remanenteAnterior) || 0.0
      });
      enqueueMessages([{ text: "Liquidación y remanente guardados con éxito.", type: 'success' }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al guardar: " + error.message, type: 'error' }]);
    }
  };

  const TabButton = ({ id, icon, label, badgeCount }) => (
    <button type="button" 
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
        <div className="text-right flex items-center space-x-4">
          <span className="hidden md:inline">Nombre: <span className="font-bold bg-blue-100 text-[#004b79] px-2 py-0.5 rounded">{user?.nombre || 'Usuario'}</span></span>
          <span className="hidden lg:inline ml-2">Versión del Sistema <span className="font-mono bg-blue-100 text-[#004b79] px-2 py-0.5 rounded ml-1">{APP_VERSION}</span></span>
          
          <button type="button" onClick={() => navigate('/empresas')} className="ml-4 text-xs font-bold uppercase bg-white text-[#5a1e2f] px-3 py-1 rounded hover:bg-slate-200 transition">
            Cambiar Empresa
          </button>
          <button type="button" onClick={() => { logout(); navigate('/login'); }} className="text-xs font-bold uppercase text-white hover:text-red-200 transition underline">
            Salir
          </button>
        </div>
      </div>
      {activeEmpresa && (
        <div className="bg-[#004b79] text-white px-6 py-1.5 flex text-xs justify-end items-center space-x-3 font-mono shadow-inner border-b border-[#00385c]">
          <span className="font-bold text-blue-100 uppercase">{activeEmpresa.razon_social}</span>
          <span className="text-blue-300">|</span>
          <span>NIT: {activeEmpresa.nit}</span>
          <span className="text-blue-300">|</span>
          <span>NRC: {activeEmpresa.nrc}</span>
        </div>
      )}

      <div className="bg-[#004b79] text-white px-6 py-2 flex items-center text-xs font-bold uppercase space-x-6 tracking-wide shadow-sm z-0">
        <span className="text-blue-200 cursor-pointer">Inicio</span>
        <span className="cursor-pointer">Declaraciones</span>
        <span className="text-blue-200 cursor-pointer">Informes</span>
      </div>

      <div className="bg-white border-b border-slate-200 shadow-sm px-6 py-4 flex flex-wrap gap-6 items-end relative z-0">
        <div>
          <label className="block text-[11px] font-bold text-slate-500 mb-1 uppercase">Ejercicio:</label>
          <input 
            type="number" 
            value={anio} 
            onChange={(e) => setAnio(parseInt(e.target.value) || new Date().getFullYear())}
            min="2000"
            max="2100"
            className="w-32 border border-slate-300 p-2 text-sm rounded focus:ring-1 focus:ring-[#004b79] focus:border-[#004b79] outline-none"
          />
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
          <button type="button" onClick={() => {
            if(activeWizardTab==='compras') setActiveWizardTab('ventas_ccf');
            else if(activeWizardTab==='ventas_ccf') setActiveWizardTab('ventas_fcf');
            else if(activeWizardTab==='ventas_fcf') setActiveWizardTab('liquidacion');
            else if(activeWizardTab==='liquidacion') setActiveWizardTab('compras');
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
            badgeCount={resumen ? ((resumen.ventasContribuyentes?.documentos || 0) + (resumen.ventasConsumidor?.documentos || 0)) : 0} 
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>} 
          />
          <TabButton 
            id="compras" 
            label="Compras y Créditos" 
            badgeCount={resumen ? (resumen.compras?.documentos || 0) : 0} 
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
        {activeWizardTab === 'compras' && (
          <div className="animate-in fade-in zoom-in-95 duration-300 space-y-6">
            <div className="bg-white border border-slate-200 rounded shadow-sm p-6">
              <div className="border-b-2 border-orange-400 pb-2 mb-4 flex justify-between items-center">
                <h2 className="text-lg font-bold text-slate-700">Importar Compras (Créditos Fiscales)</h2>
              </div>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col md:flex-row items-center gap-4">
                  <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-white text-[#004b79] font-bold rounded border-2 border-[#004b79] hover:bg-slate-50 transition cursor-pointer shadow-sm">
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    <span>Seleccionar Carpeta (Compras)</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
                  </label>
                  <button type="button" 
                    onClick={() => handleProcesar('compras', '/procesar/compras')}
                    disabled={loading || archivos.compras?.length === 0}
                    className={`flex-1 px-6 py-3 rounded font-bold shadow transition flex items-center justify-center whitespace-nowrap ${loading || archivos.compras?.length === 0 ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-[#004b79] hover:bg-[#00385c] text-white'}`}
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    {loading ? 'Procesando...' : `Procesar Archivos (${archivos.compras?.length || 0})`}
                  </button>
                </div>
                <button type="button" 
                  onClick={() => handleGmailImport()}
                  disabled={loadingGmail || loading}
                  className="w-full flex items-center justify-center px-4 py-3 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition disabled:opacity-50"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12.713l-11.985-9.713h23.971l-11.986 9.713zm-12 1.545v-10.258l12 9.728 12-9.728v10.258l-12 9.728-12-9.728z"/>
                  </svg>
                  {loadingGmail ? 'Importando desde Gmail...' : 'Importar Automáticamente desde Gmail'}
                </button>
              </div>
            </div>
            
            {resumen && resumen.compras ? renderResumen('compras', 'Detalle de Compras (CCF recibidos)') : (
              <div className="bg-white p-6 rounded shadow-sm border border-slate-200 text-center text-slate-500">
                No hay datos de Compras procesados en este periodo. Sube una carpeta para comenzar.
              </div>
            )}
          </div>
        )}

        {activeWizardTab === 'ventas_ccf' && (
          <div className="animate-in fade-in zoom-in-95 duration-300 space-y-6">
            <div className="bg-white border border-slate-200 rounded shadow-sm p-6">
              <div className="border-b-2 border-orange-400 pb-2 mb-4 flex justify-between items-center">
                <h2 className="text-lg font-bold text-slate-700">Importar Ventas a Contribuyentes (CCF Emitidos)</h2>
              </div>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col md:flex-row items-center gap-4">
                  <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                    <span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de CCF Emitidos</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
                  </label>
                  <button type="button" 
                    onClick={() => handleProcesar('ventasContribuyentes', '/procesar/ventas-contribuyentes')}
                    disabled={loading || archivos.ventasContribuyentes?.length === 0}
                    className={`flex-1 px-6 py-3 rounded font-bold shadow transition flex items-center justify-center whitespace-nowrap ${loading || archivos.ventasContribuyentes?.length === 0 ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-[#004b79] hover:bg-[#00385c] text-white'}`}
                  >
                    {loading ? 'Procesando...' : `Procesar (${archivos.ventasContribuyentes?.length || 0})`}
                  </button>
                </div>
                <button type="button" 
                  onClick={() => handleGmailImport()}
                  disabled={loadingGmail || loading}
                  className="w-full flex items-center justify-center px-4 py-3 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition disabled:opacity-50"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12.713l-11.985-9.713h23.971l-11.986 9.713zm-12 1.545v-10.258l12 9.728 12-9.728v10.258l-12 9.728-12-9.728z"/>
                  </svg>
                  {loadingGmail ? 'Importando desde Gmail...' : 'Importar Automáticamente desde Gmail'}
                </button>
              </div>
            </div>
            
            {resumen && resumen.ventasContribuyentes ? renderResumen('ventasContribuyentes', 'Ventas a Contribuyentes (CCF)') : (
              <div className="bg-white p-6 rounded shadow-sm border border-slate-200 text-center text-slate-500">
                No hay datos de CCF procesados en este periodo.
              </div>
            )}
          </div>
        )}

        {activeWizardTab === 'ventas_fcf' && (
          <div className="animate-in fade-in zoom-in-95 duration-300 space-y-6">
            <div className="bg-white border border-slate-200 rounded shadow-sm p-6">
              <div className="border-b-2 border-orange-400 pb-2 mb-4 flex justify-between items-center">
                <h2 className="text-lg font-bold text-slate-700">Importar Ventas a Consumidor Final (FCF Emitidos)</h2>
              </div>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col md:flex-row items-center gap-4">
                  <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                    <span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de FCF Emitidos</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
                  </label>
                  <button type="button" 
                    onClick={() => handleProcesar('ventasConsumidor', '/procesar/ventas-consumidor')}
                    disabled={loading || archivos.ventasConsumidor?.length === 0}
                    className={`flex-1 px-6 py-3 rounded font-bold shadow transition flex items-center justify-center whitespace-nowrap ${loading || archivos.ventasConsumidor?.length === 0 ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-[#004b79] hover:bg-[#00385c] text-white'}`}
                  >
                    {loading ? 'Procesando...' : `Subir y Procesar (${archivos.ventasConsumidor?.length || 0})`}
                  </button>
                </div>
                <button type="button" 
                  onClick={() => handleGmailImport()}
                  disabled={loadingGmail || loading}
                  className="w-full flex items-center justify-center px-4 py-3 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition disabled:opacity-50"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12.713l-11.985-9.713h23.971l-11.986 9.713zm-12 1.545v-10.258l12 9.728 12-9.728v10.258l-12 9.728-12-9.728z"/>
                  </svg>
                  {loadingGmail ? 'Importando desde Gmail...' : 'Importar Automáticamente desde Gmail'}
                </button>
              </div>
            </div>
            
            {resumen && resumen.ventasConsumidor ? renderResumen('ventasConsumidor', 'Ventas a Consumidor Final (FCF)') : (
              <div className="bg-white p-6 rounded shadow-sm border border-slate-200 text-center text-slate-500">
                No hay datos de FCF procesados en este periodo.
              </div>
            )}
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
                      <span className="font-mono font-bold"></span>
                    </td>
                    <td className="px-6 py-4 flex justify-between items-center border-l border-slate-200">
                      <span className="text-slate-600">Suma de Compras Gravadas</span>
                      <span className="font-mono font-bold"></span>
                    </td>
                  </tr>
                  <tr className="bg-slate-50">
                    <td className="px-6 py-4 flex justify-between items-center">
                      <span className="font-bold text-slate-700">Suma de Débitos (IVA Ventas 13%)</span>
                      <span className="font-mono text-lg text-red-600 font-bold"></span>
                    </td>
                    <td className="px-6 py-4 flex justify-between items-start border-l border-slate-200">
                      <div className="flex flex-col">
                        <span className="font-bold text-slate-700 mb-2">Suma de Créditos (IVA Compras)</span>
                        <div className="flex items-center text-xs mt-1 bg-yellow-50 p-2 border border-yellow-200 rounded">
                          <span className="mr-2 font-semibold text-yellow-800">+ Remanente Anterior: $</span>
                          <input type="number" step="0.01" value={remanenteAnterior} onChange={(e) => setRemanenteAnterior(parseFloat(e.target.value) || 0)} className="w-24 p-1 border border-yellow-300 rounded text-right outline-none focus:ring-1 focus:ring-yellow-500 font-mono" />
                        </div>
                      </div>
                      <span className="font-mono text-lg text-green-600 font-bold"></span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div className="border-t-4 border-slate-300 p-6 bg-white relative">
                <button type="button" onClick={handleGuardarLiquidacion} className="absolute -top-5 right-6 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-full shadow-lg text-xs font-bold uppercase tracking-wider flex items-center transition">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>
                  Guardar Liquidación
                </button>
                {impuestoDeterminado > 0 ? (
                  <div className="flex justify-between items-center mt-2">
                    <div>
                      <span className="font-bold text-red-800 text-lg uppercase block">Impuesto Determinado</span>
                      <span className="text-xs text-slate-500">(Cuando el débito excede al crédito)</span>
                    </div>
                    <span className="font-mono text-3xl font-bold text-red-700"></span>
                  </div>
                ) : (
                  <div className="flex justify-between items-center mt-2">
                    <div>
                      <span className="font-bold text-green-800 text-lg uppercase block">Remanente de Crédito para el Próximo Periodo</span>
                      <span className="text-xs text-slate-500">(Cuando el crédito excede al débito)</span>
                    </div>
                    <span className="font-mono text-3xl font-bold text-green-700"></span>
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
