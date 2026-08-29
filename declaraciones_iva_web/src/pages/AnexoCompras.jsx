import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function AnexoCompras() {
  const [searchParams] = useSearchParams();
  const mes = searchParams.get("mes");
  const anio = searchParams.get("anio");
  
  const { user, activeEmpresa } = useAuth();
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  const [compras, setCompras] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const [versiones, setVersiones] = useState([{version: 1, declarado: false, numero_declaracion: ""}]);
  const [activeVersion, setActiveVersion] = useState(1);
  const [numeroInput, setNumeroInput] = useState("");

  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!activeEmpresa) {
      navigate('/dashboard');
      return;
    }
    fetchEstadoDeclaracion();
    fetchCompras();
  }, [activeEmpresa, mes, anio, activeVersion]);

  
  const fetchEstadoDeclaracion = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/compras/estado/${activeEmpresa.id}?mes=${mes}&anio=${anio}&tipo_libro=compras`);
      const vers = response.data.versiones || [{version: 1, declarado: false, numero_declaracion: ""}];
      setVersiones(vers);
      const maxV = Math.max(...vers.map(v => v.version));
      setActiveVersion(maxV);
      
      if (vers.find(v => v.version === maxV)?.declarado) {
        enqueueMessages([{ text: "Este período ya fue declarado al Ministerio de Hacienda. Se encuentra bloqueado para evitar alteraciones.", type: "warning" }]);
      }
    } catch (error) {
      console.error("Error al cargar el estado de la declaración");
    }
  };
  
  const handleSaveNumero = async () => {
    try {
      await axios.put(`${API_URL}/api/v1/compras/estado/${activeEmpresa.id}/numero?mes=${mes}&anio=${anio}&numero=${numeroInput}&version=${activeVersion}&tipo_libro=compras`);
      enqueueMessages([{ text: "Número de declaración guardado correctamente.", type: "success" }]);
      fetchEstadoDeclaracion();
    } catch (error) {
      enqueueMessages([{ text: "Error al guardar el número.", type: "error" }]);
    }
  };
  
  const crearModificatoria = async () => {
    const original = prompt("Ingresa el Número de la Declaración original que vas a modificar:");
    if (!original) return;
    
    try {
      await axios.post(`${API_URL}/api/v1/compras/modificatoria/${activeEmpresa.id}?mes=${mes}&anio=${anio}&numero_original=${original}&tipo_libro=compras`);
      enqueueMessages([{ text: "Modificatoria creada exitosamente. Candado abierto.", type: "success" }]);
      fetchEstadoDeclaracion();
      if(api_path === "compras") fetchCompras(); else fetchVentas();
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || "Error al crear modificatoria.", type: "error" }]);
    }
  };
  
  const currentEstado = versiones.find(v => v.version === activeVersion) || {declarado: false};
  const isDeclarado = currentEstado.declarado;

  const fetchCompras = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/compras/${activeEmpresa.id}?mes=${mes}&anio=${anio}`);
      setCompras(response.data);
    } catch (error) {
      enqueueMessages([{ text: "Error al cargar las compras.", type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const declararAnexo = async () => {
    if (!window.confirm("¿Estás seguro de marcar este anexo como Declarado? Ya no podrás subir ni modificar compras para este mes.")) return;
    try {
      await axios.post(`${API_URL}/api/v1/compras/declarar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      fetchEstadoDeclaracion();
      enqueueMessages([{ text: "Anexo marcado como Declarado exitosamente.", type: "success" }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al marcar como declarado.", type: "error" }]);
    }
  };

  const MESES_NOMBRES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

  const handleFileUpload = async (files) => {
    // Solo permitir enviar archivos con extensión .json (ignorando mayúsculas/minúsculas)
    const jsonFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.json'));
    
    if (jsonFiles.length === 0) {
      enqueueMessages([{ text: `⚠️ En esa carpeta no hay archivos JSON para el Anexo de Compras. Por favor verifica que estás seleccionando la carpeta correcta con los comprobantes de tus proveedores.`, type: "error" }]);
      return;
    }

    const nombreMes = MESES_NOMBRES[(parseInt(mes, 10) - 1)] || mes;
    enqueueMessages([{ text: `⏳ Procesando los JSON del Anexo de Compras del mes de ${nombreMes}... Por favor espera mientras valido cada comprobante.`, type: "info" }]);

    setLoading(true);
    let totalProcesados = 0;
    let todosErrores = [];

    try {
      // Para evitar bloqueos del WAF o Proxy (CORS ERR_FAILED) por múltiples archivos, subimos 1 por 1.
      for (let i = 0; i < jsonFiles.length; i++) {
        const formData = new FormData();
        formData.append("empresa_id", activeEmpresa.id);
        formData.append("periodo_mes", mes);
        formData.append("periodo_anio", anio);
    formData.append("version", activeVersion);
        formData.append("files", jsonFiles[i]);

        try {
          const response = await axios.post(`${API_URL}/api/v1/compras/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          
          if (response.data.errores && response.data.errores.length > 0) {
            todosErrores = [...todosErrores, ...response.data.errores];
          } else {
            totalProcesados += 1;
          }
        } catch (err) {
           todosErrores.push(`${jsonFiles[i].name}: Falló la conexión (Network Error).`);
        }
      }
      
      if (todosErrores.length > 0) {
        enqueueMessages([{ text: `Subida completada. Éxitos: ${totalProcesados}. Errores en ${todosErrores.length} archivos: ${todosErrores.slice(0,2).join(", ")}...`, type: "warning" }]);
      } else {
        enqueueMessages([{ text: `Se procesaron ${totalProcesados} comprobantes exitosamente.`, type: "success" }]);
      }
      fetchCompras();
    } catch (error) {
      console.error(error);
      enqueueMessages([{ text: `Error inesperado al procesar los archivos.`, type: "error" }]);
      fetchCompras();
    } finally {
      setLoading(false);
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  const exportCSV = () => {
    window.location.href = `${API_URL}/api/v1/compras/${activeEmpresa.id}/export?mes=${mes}&anio=${anio}`;
  };

  const updateConfig = async (id, field, value) => {
    // Buscar compra actual
    const compra = compras.find(c => c.id === id);
    if (!compra) return;

    const payload = {
      tipo_operacion: compra.tipo_operacion || "0",
      clasificacion: compra.clasificacion || "0",
      sector: compra.sector || "0",
      tipo_costo: compra.tipo_costo_gasto || "0"
    };
    
    // Actualizar campo
    payload[field === "tipo_costo_gasto" ? "tipo_costo" : field] = value;

    try {
      await axios.put(`${API_URL}/api/v1/compras/update_operacion/${id}?tipo_operacion=${payload.tipo_operacion}&clasificacion=${payload.clasificacion}&sector=${payload.sector}&tipo_costo=${payload.tipo_costo}`);
      fetchCompras(); // Refrescar para ver el estado actual
    } catch(err) {
      enqueueMessages([{ text: "Error al actualizar la configuración.", type: "error" }]);
    }
  };

  const limpiarAnexo = async () => {
    if (!window.confirm("¿Estás seguro de eliminar TODOS los registros de este mes? Esta acción no se puede deshacer y tendrás que volver a subir los archivos.")) return;
    try {
      await axios.delete(`${API_URL}/api/v1/compras/limpiar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      enqueueMessages([{ text: "Anexo limpiado exitosamente.", type: "success" }]);
      fetchCompras();
    } catch (error) {
      enqueueMessages([{ text: "Error al limpiar el anexo.", type: "error" }]);
    }
  };

  if (!activeEmpresa) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in-up">

      <div className="mb-6 flex border-b border-slate-200">
        {versiones.map(v => (
          <button
            key={v.version}
            onClick={() => setActiveVersion(v.version)}
            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
              activeVersion === v.version 
                ? "border-indigo-600 text-indigo-600" 
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            {v.version === 1 ? "Original" : `Modificatoria ${v.version - 1}`}
            {v.declarado && " 🔒"}
          </button>
        ))}
      </div>
      
      {isDeclarado && (
        <div className="mb-6 p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-lg flex items-center justify-between">
          <div className="flex">
            <svg className="h-5 w-5 text-amber-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <p className="text-sm text-amber-700 font-medium">Período Bloqueado</p>
              <div className="mt-2 flex items-center space-x-2">
                <span className="text-sm text-amber-800">Número de Declaración MH:</span>
                <input 
                  type="text" 
                  value={numeroInput || currentEstado.numero_declaracion || ""} 
                  onChange={e => setNumeroInput(e.target.value)}
                  placeholder="Ej. 12345678"
                  className="px-2 py-1 border border-amber-300 rounded text-sm focus:ring-amber-500 focus:border-amber-500"
                />
                <button onClick={handleSaveNumero} className="px-3 py-1 bg-amber-600 text-white rounded text-sm hover:bg-amber-700">Guardar</button>
              </div>
            </div>
          </div>
          {activeVersion === Math.max(...versiones.map(v=>v.version)) && activeVersion < 3 && (
            <button onClick={crearModificatoria} className="px-4 py-2 bg-indigo-600 text-white rounded-lg shadow-sm text-sm hover:bg-indigo-700">
              Crear Modificatoria
            </button>
          )}
        </div>
      )}

      <div className="flex justify-between items-start mb-6">
        <div>
          <div className="flex items-center space-x-2 text-sm text-slate-500 mb-2">
            <button onClick={() => navigate('/dashboard')} className="hover:text-indigo-600">Dashboard</button>
            <span>/</span>
            <span className="text-slate-800 font-medium">Anexo de Compras</span>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
            {activeEmpresa.razon_social}
          </h1>
          <p className="text-slate-500 mt-1">Período: {mes}/{anio}</p>
        </div>
        <div className="flex space-x-3">
          {!isDeclarado && (
            <>
              <button 
                onClick={limpiarAnexo}
                className="px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white text-sm font-medium rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rose-500 transition-colors"
              >
                🗑️ Limpiar Anexo
              </button>
              <button 
                onClick={declararAnexo}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
              >
                🔒 Marcar como Declarado
              </button>
            </>
          )}
          <button 
            onClick={exportCSV}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            Descargar CSV F07
          </button>
        </div>
      </div>

      {/* Zona de Drag and Drop */}
      <div 
        className={`mb-8 border-2 border-dashed rounded-xl p-10 text-center transition-colors ${!isDeclarado ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'} ${
          isDragging ? 'border-amber-500 bg-amber-50' : 'border-slate-300 bg-white hover:border-amber-400 hover:bg-slate-50'
        }`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current.click()}
      >
        <input 
          type="file" 
          multiple 
          webkitdirectory="true"
          directory="true"
          accept=".json" 
          className="hidden" 
          ref={fileInputRef}
          onChange={(e) => handleFileUpload(e.target.files)}
        />
        <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-slate-800 mb-1">Arrastra tus archivos JSON o una carpeta completa aquí</h3>
        <p className="text-sm text-slate-500">o haz clic para buscar la carpeta en tu equipo (Comprobantes de Crédito Fiscal emitidos por proveedores)</p>
      </div>

      {/* Resumen Superior */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Registros</p>
            <h3 className="text-xl font-bold text-slate-900">
              {compras.length}
            </h3>
          </div>
          <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center text-slate-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Total Gravadas</p>
            <h3 className="text-xl font-bold text-slate-900">
              ${compras.reduce((sum, item) => sum + (item.compras_internas_gravadas || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h3>
          </div>
          <div className="w-12 h-12 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Total Crédito Fiscal</p>
            <h3 className="text-xl font-bold text-slate-900">
              ${compras.reduce((sum, item) => sum + (item.credito_fiscal || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h3>
          </div>
          <div className="w-12 h-12 bg-sky-50 rounded-full flex items-center justify-center text-sky-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2zM10 8.5a.5.5 0 11-1 0 .5.5 0 011 0zm5 5a.5.5 0 11-1 0 .5.5 0 011 0z"></path></svg>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Total Compras</p>
            <h3 className="text-xl font-bold text-slate-900">
              ${compras.reduce((sum, item) => sum + (item.total_compras || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h3>
          </div>
          <div className="w-12 h-12 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col">
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
          <table className="min-w-max w-full divide-y divide-slate-200">
            <thead className="bg-slate-50 sticky top-0 z-10 shadow-sm">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider" title="A: Fecha de Emisión">A. Fecha</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider" title="B: Clase de Documento">B. Clase</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider" title="C: Tipo de Documento">C. Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider" title="D: Número de Resolución / Código de Generación">D. Resolución / Cód. Generación</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider" title="E: NIT Proveedor">E. NIT Prov.</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider" title="F: Nombre Proveedor">F. Nombre Proveedor</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="G: Compras Internas Exentas">G. Exent. Int.</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="H: Internaciones Exentas">H. Internac. Exent.</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="I: Importaciones Exentas">I. Import. Exent.</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="J: Compras Internas Gravadas">J. Gravadas Int.</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="K: Internaciones Gravadas Bienes">K. Internac. Grav.</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="L: Importaciones Gravadas Bienes">L. Import. Grav. Bs.</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="M: Importaciones Gravadas Servicios">M. Import. Grav. Sv.</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="N: Crédito Fiscal">N. Crédito Fiscal</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider" title="O: Total Compras">O. Total</th>
                <th className="px-4 py-3 text-center text-xs font-bold text-indigo-700 uppercase tracking-wider border-l border-slate-200" colSpan="4">Configuración F07</th>
              </tr>
              <tr className="bg-slate-100 border-b border-slate-300">
                <th colSpan="15" className="border-r border-slate-200"></th>
                <th className="px-2 py-1 text-xs text-indigo-700 font-medium">T. Operación</th>
                <th className="px-2 py-1 text-xs text-indigo-700 font-medium">Clasificación</th>
                <th className="px-2 py-1 text-xs text-indigo-700 font-medium">Sector</th>
                <th className="px-2 py-1 text-xs text-indigo-700 font-medium">Costo/Gasto</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {loading && compras.length === 0 ? (
                <tr>
                  <td colSpan="19" className="px-6 py-10 text-center text-slate-500">
                    Cargando compras...
                  </td>
                </tr>
              ) : compras.length === 0 ? (
                <tr>
                  <td colSpan="19" className="px-6 py-10 text-center text-slate-500">
                    <div className="flex flex-col items-center">
                      <svg className="w-12 h-12 text-slate-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                      <p>No hay compras procesadas en {mes}/{anio}.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                [...compras]
                  .sort((a, b) => {
                    // Convertir "DD/MM/YYYY" a Date para ordenar
                    const dateA = a.fecha_emision.split('/').reverse().join('-');
                    const dateB = b.fecha_emision.split('/').reverse().join('-');
                    return new Date(dateA) - new Date(dateB);
                  })
                  .map((compra) => (
                  <tr key={compra.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-900">{compra.fecha_emision}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-900 text-center">{compra.clase_documento}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-900 text-center">{compra.tipo_documento}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-500 truncate max-w-[150px]" title={compra.numero_resolucion}>{compra.numero_resolucion}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-500">{compra.nit_proveedor}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-900 truncate max-w-[200px]" title={compra.nombre_proveedor}>{compra.nombre_proveedor}</td>
                    
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${compra.compras_internas_exentas.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${compra.internaciones_exentas.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${compra.importaciones_exentas.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-900 font-medium">${compra.compras_internas_gravadas.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${compra.internaciones_gravadas_bienes.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${compra.importaciones_gravadas_bienes.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${compra.importaciones_gravadas_servicios.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-900 font-medium">${compra.credito_fiscal.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-emerald-700 font-bold">${compra.total_compras.toFixed(2)}</td>
                    
                    <td className="px-2 py-3 whitespace-nowrap text-xs text-center border-l border-slate-200">
                      <select 
                        value={compra.tipo_operacion || "1"} 
                        onChange={(e) => updateConfig(compra.id, "tipo_operacion", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20 focus:ring-indigo-500"
                        disabled={isDeclarado}
                      >
                        <option value="0">-</option>
                        <option value="1">1 Grav</option>
                        <option value="2">2 No Grav</option>
                      </select>
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-xs text-center border-l border-slate-200">
                      <select 
                        value={compra.clasificacion || "1"} 
                        onChange={(e) => updateConfig(compra.id, "clasificacion", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20 focus:ring-indigo-500"
                        disabled={isDeclarado}
                      >
                        <option value="0">-</option>
                        <option value="1">1 Costo</option>
                        <option value="2">2 Gasto</option>
                      </select>
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-xs text-center border-l border-slate-200">
                      <select 
                        value={compra.sector || "2"} 
                        onChange={(e) => updateConfig(compra.id, "sector", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20 focus:ring-indigo-500"
                        disabled={isDeclarado}
                      >
                        <option value="0">-</option>
                        <option value="1">1 Ind</option>
                        <option value="2">2 Com</option>
                        <option value="3">3 Serv</option>
                        <option value="4">4 Agro</option>
                        <option value="5">5 Otro</option>
                      </select>
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-xs text-center border-l border-slate-200">
                      <select 
                        value={compra.tipo_costo_gasto || "5"} 
                        onChange={(e) => updateConfig(compra.id, "tipo_costo_gasto", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20 focus:ring-indigo-500"
                        disabled={isDeclarado}
                      >
                        <option value="0">-</option>
                        <option value="1">1 Venta</option>
                        <option value="2">2 Admin</option>
                        <option value="3">3 Finan</option>
                        <option value="4">4 Produc</option>
                        <option value="5">5 Costo/Arts</option>
                      </select>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
