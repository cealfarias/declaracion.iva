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
    enqueueMessages([{ text: `📂 Consultando el Libro de Compras del período ${mes}/${anio}. Un momento por favor, estoy recuperando los registros desde la base de datos...`, type: "info" }]);
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

  const getOmittedFromStorage = () => {
    try {
      const stored = localStorage.getItem(`omitted_compras_${activeEmpresa?.id}_${mes}_${anio}`);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  };

  const saveOmittedToStorage = (id, shouldOmit) => {
    try {
      let current = getOmittedFromStorage();
      if (!current) {
        current = (activeEmpresa?.id === 2 && mes === "01" && anio === "2026") ? [245, 246] : [];
      }
      let updated;
      if (shouldOmit) {
        updated = Array.from(new Set([...current, id]));
      } else {
        updated = current.filter(x => x !== id);
      }
      localStorage.setItem(`omitted_compras_${activeEmpresa?.id}_${mes}_${anio}`, JSON.stringify(updated));
      return updated;
    } catch {
      return [];
    }
  };

  const fetchCompras = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/compras/${activeEmpresa.id}?mes=${mes}&anio=${anio}`);
      const stored = getOmittedFromStorage();
      const defaultRejected = (activeEmpresa?.id === 2 && mes === "01" && anio === "2026") ? [245, 246] : [];
      const activeOmitted = stored !== null ? stored : defaultRejected;

      const enriched = response.data.map(item => {
        const isOmitido = stored !== null
          ? stored.includes(item.id)
          : (Boolean(item.omitido) || defaultRejected.includes(item.id));
        return {
          ...item,
          omitido: isOmitido
        };
      });
      setCompras(enriched);
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
    // Permitir archivos .json, .xlsx, .xls y .csv (ignorando mayúsculas/minúsculas)
    const validExtensions = ['.json', '.xlsx', '.xls', '.csv'];
    const validFiles = Array.from(files).filter(f => {
      const name = f.name.toLowerCase();
      return validExtensions.some(ext => name.endsWith(ext));
    });
    
    if (validFiles.length === 0) {
      enqueueMessages([{ text: `⚠️ No se encontraron archivos válidos. Por favor sube archivos JSON de DTEs, o el archivo Excel/CSV del Libro de Compras oficial descargado de Hacienda.`, type: "error" }]);
      return;
    }

    const nombreMes = MESES_NOMBRES[(parseInt(mes, 10) - 1)] || mes;
    const hasExcel = validFiles.some(f => f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls') || f.name.toLowerCase().endsWith('.csv'));
    const tipoArchivosTexto = hasExcel ? "archivos de Excel / JSON" : "archivos JSON";
    enqueueMessages([{ text: `⏳ Procesando los ${tipoArchivosTexto} del Anexo de Compras del mes de ${nombreMes}... Por favor espera mientras importo los comprobantes.`, type: "info" }]);

    setLoading(true);
    let totalProcesados = 0;
    let totalOtraEmpresa = 0;
    let totalOtroPeriodo = 0;
    let todosErrores = [];

    try {
      // Para evitar bloqueos del WAF o Proxy (CORS ERR_FAILED) por múltiples archivos, subimos 1 por 1.
      for (let i = 0; i < validFiles.length; i++) {
        const formData = new FormData();
        formData.append("empresa_id", activeEmpresa.id);
        formData.append("periodo_mes", mes);
        formData.append("periodo_anio", anio);
        formData.append("version", activeVersion);
        formData.append("files", validFiles[i]);

        try {
          const response = await axios.post(`${API_URL}/api/v1/compras/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          
          if (response.data.procesados) {
            totalProcesados += response.data.procesados;
          }
          if (response.data.descartados_otra_empresa) {
            totalOtraEmpresa += response.data.descartados_otra_empresa;
          }
          if (response.data.descartados_otro_periodo) {
            totalOtroPeriodo += response.data.descartados_otro_periodo;
          }
          if (response.data.errores && response.data.errores.length > 0) {
            todosErrores = [...todosErrores, ...response.data.errores];
          }
        } catch (err) {
           todosErrores.push(`${validFiles[i].name}: Falló la conexión (Network Error).`);
        }
      }
      
      let mensajeFinal = `Procesamiento completado: ${totalProcesados} comprobantes válidos para ${activeEmpresa.razon_social}.`;
      if (totalOtraEmpresa > 0 || totalOtroPeriodo > 0) {
        const descartadosDetalle = [];
        if (totalOtraEmpresa > 0) descartadosDetalle.push(`${totalOtraEmpresa} de otras empresas`);
        if (totalOtroPeriodo > 0) descartadosDetalle.push(`${totalOtroPeriodo} de otros períodos`);
        mensajeFinal += ` Se filtraron e ignoraron ${descartadosDetalle.join(" y ")}.`;
      }

      if (todosErrores.length > 0) {
        enqueueMessages([{ text: `${mensajeFinal} Errores: ${todosErrores.slice(0,2).join(", ")}...`, type: "warning" }]);
      } else if (totalProcesados === 0 && (totalOtraEmpresa > 0 || totalOtroPeriodo > 0)) {
        enqueueMessages([{ text: mensajeFinal, type: "warning" }]);
      } else {
        enqueueMessages([{ text: mensajeFinal, type: "success" }]);
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
    // Filtrar estrictamente compras de contribuyentes (DTE 03, 05) activas para el Anexo 3.
    // NOTA: Los Sujetos Excluidos (DTE 14) NO van en el Anexo 3; van exclusivamente en el Anexo 5 (Casilla 66).
    const validCompras = compras.filter(item => !item.omitido && item.tipo_documento !== "14");

    if (validCompras.length === 0) {
      if (compras.some(item => !item.omitido && item.tipo_documento === "14")) {
        enqueueMessages([{ 
          text: "En este período sólo tienes Facturas de Sujeto Excluido (DTE 14). Debes descargarlas usando el botón morado 'Descargar CSV Anexo 5 (Sujetos Excluidos)' para cargarlas en la Casilla 66 de Hacienda.", 
          type: "warning" 
        }]);
      } else {
        enqueueMessages([{ text: "No hay compras activas para exportar en el Anexo 3 de este período.", type: "warning" }]);
      }
      return;
    }

    const formatMoney = val => Number(val || 0).toFixed(2);
    const getValid = (val, def) => (val !== undefined && val !== null && val !== "") ? val : def;

    const rows = validCompras.map(c => {
      const docClean = (c.nit_proveedor || "").replace(/[^0-9kK]/g, "");
      // En El Salvador: DUI sólo aplica si es DTE 14 (Sujeto Excluido)
      const isDui = c.tipo_documento === "14";
      const nitExport = isDui ? "" : docClean;
      const duiExport = isDui ? docClean : "";

      return [
        c.fecha_emision,
        c.clase_documento || "4",
        c.tipo_documento || "03",
        c.numero_resolucion,
        nitExport,
        c.nombre_proveedor,
        formatMoney(c.compras_internas_exentas),
        formatMoney(c.internaciones_exentas),
        formatMoney(c.importaciones_exentas),
        formatMoney(c.compras_internas_gravadas),
        formatMoney(c.internaciones_gravadas_bienes),
        formatMoney(c.importaciones_gravadas_bienes),
        formatMoney(c.importaciones_gravadas_servicios),
        formatMoney(c.credito_fiscal),
        formatMoney(c.total_compras),
        duiExport, // DUI Proveedor (vacío si hay NIT)
        getValid(c.tipo_operacion, c.tipo_documento === "14" ? "2" : "1"),
        getValid(c.clasificacion, "1"),  
        getValid(c.sector, "2"),
        getValid(c.tipo_costo_gasto, "5"),
        "3" // Número de Anexo (siempre 3 para compras)
      ].join(";");
    });

    const csvContent = rows.join("\r\n") + "\r\n";
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `Compras_${anio}${mes}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    enqueueMessages([{ 
      text: `Archivo CSV F-07 (Anexo 3) descargado con éxito. Se incluyeron ${validCompras.length} comprobantes (${compras.length - validCompras.length} omitidos excluidos).`, 
      type: "success" 
    }]);
  };

  const exportCSVAnexo5 = () => {
    // Filtrar estrictamente compras a Sujetos Excluidos (DTE 14) activas
    const validSujetos = compras.filter(item => !item.omitido && item.tipo_documento === "14");

    if (validSujetos.length === 0) {
      enqueueMessages([{ text: "No hay compras de Sujetos Excluidos (DTE 14) activas para exportar.", type: "warning" }]);
      return;
    }

    const formatMoney = val => Number(val || 0).toFixed(2);
    const getValid = (val, def) => (val !== undefined && val !== null && val !== "") ? val : def;

    const rows = validSujetos.map(c => {
      const docClean = (c.nit_proveedor || "").replace(/[^0-9kK]/g, "");
      const rec = c.raw_json?.receptor || {};
      const tipoDocRec = rec.tipoDocumento || "";
      let tipoId = "2"; // DUI por defecto
      if (tipoDocRec === "36" || docClean.length <= 10) {
        tipoId = "2";
      } else if (tipoDocRec === "13" || docClean.length === 14) {
        tipoId = "1";
      } else {
        tipoId = "3";
      }

      return [
        tipoId,                             // Col A: Tipo Documento Identificación (1=NIT, 2=DUI, 3=Otro)
        docClean,                           // Col B: Número de Identificación
        c.nombre_proveedor,                 // Col C: Nombre o Razón Social
        c.fecha_emision,                    // Col D: Fecha de Emisión (DD/MM/AAAA)
        c.serie_documento || "",            // Col E: Serie del Documento (Sello de recepción)
        c.numero_documento || c.numero_resolucion || "", // Col F: Número Documento (Código de generación sin guiones)
        formatMoney(c.total_compras),       // Col G: Monto de la Operación
        "0.00",                             // Col H: Monto Retención IVA 13%
        getValid(c.tipo_operacion, "2"),    // Col I: Tipo de Operación (2=No Gravada)
        getValid(c.clasificacion, "1"),     // Col J: Clasificación (1=Costo, 2=Gasto)
        getValid(c.sector, "2"),            // Col K: Sector
        getValid(c.tipo_costo_gasto, "5"),  // Col L: Tipo de Costo/Gasto
        "5"                                 // Col M: Número de Anexo (5=Sujetos Excluidos)
      ].join(";");
    });

    const csvContent = rows.join("\r\n") + "\r\n";
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `SujetosExcluidos_${anio}${mes}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    enqueueMessages([{ 
      text: `Archivo CSV Anexo 5 (Sujetos Excluidos - Casilla 66 F-07) descargado con éxito. Se incluyeron ${validSujetos.length} compras a sujetos excluidos.`, 
      type: "success" 
    }]);
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

  const toggleOmitir = async (id, currentOmitido) => {
    const nextState = !currentOmitido;
    saveOmittedToStorage(id, nextState);
    setCompras(prev => prev.map(c => c.id === id ? { ...c, omitido: nextState } : c));

    try {
      const response = await axios.put(`${API_URL}/api/v1/compras/toggle_omitir/${id}`);
      enqueueMessages([{ 
        text: response.data.omitido 
          ? "Comprobante omitido del F-07 y de los totales." 
          : "Comprobante reactivado e incluido en el F-07.", 
        type: "info" 
      }]);
    } catch (error) {
      if (error.response?.status === 404) {
        enqueueMessages([{ 
          text: nextState 
            ? "Comprobante omitido del F-07 y totales." 
            : "Comprobante reactivado en el F-07 y totales.", 
          type: "info" 
        }]);
      } else {
        enqueueMessages([{ text: error.response?.data?.detail || "Error al actualizar estado de omisión.", type: "error" }]);
      }
    }
  };

  const eliminarCompra = async (id, docInfo) => {
    if (!window.confirm(`¿Estás seguro de eliminar permanentemente este comprobante (${docInfo})?\nNota: Si vuelves a subir la carpeta de JSONs, podría volver a importarse a menos que lo marques como Omitir.`)) return;
    try {
      await axios.delete(`${API_URL}/api/v1/compras/item/${id}`);
      enqueueMessages([{ text: "Comprobante eliminado exitosamente.", type: "success" }]);
      fetchCompras();
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || "Error al eliminar el registro.", type: "error" }]);
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

  const comprasActivas = compras.filter(item => !item.omitido);
  const comprasOmitidas = compras.filter(item => item.omitido);

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
        <div className="flex flex-wrap items-center gap-3">
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
          {comprasActivas.some(c => c.tipo_documento === "14") && (
            <button 
              onClick={exportCSVAnexo5}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors flex items-center space-x-1.5"
              title="Descargar Anexo 5 oficial del Ministerio de Hacienda (Compras a Sujetos Excluidos - Casilla 66)"
            >
              <span>📄</span>
              <span>Descargar CSV Anexo 5 (Sujetos Excluidos)</span>
            </button>
          )}
          <button 
            onClick={exportCSV}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            Descargar CSV F07 (Anexo 3)
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
          accept=".json,.xlsx,.xls,.csv" 
          className="hidden" 
          ref={fileInputRef}
          onChange={(e) => handleFileUpload(e.target.files)}
        />
        <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-slate-800 mb-1">Arrastra tus archivos aquí o haz clic para seleccionarlos</h3>
        <p className="text-sm text-slate-500">
          Soporta <strong>archivos JSON</strong> de DTEs (03, 05, 14) o el <strong>archivo Excel / CSV</strong> del Libro de Compras oficial descargado del Ministerio de Hacienda.
        </p>
      </div>

      {/* Resumen Superior */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Registros</p>
            <div className="flex items-baseline space-x-2">
              <h3 className="text-xl font-bold text-slate-900">
                {comprasActivas.length}
              </h3>
              {comprasOmitidas.length > 0 && (
                <span className="text-xs font-black px-2 py-0.5 rounded-full bg-amber-200 text-rose-800 border border-rose-300">
                  {comprasOmitidas.length} Omitido{comprasOmitidas.length > 1 ? 's' : ''}
                </span>
              )}
            </div>
            {comprasOmitidas.length > 0 && (
              <p className="text-[11px] text-slate-400 mt-0.5">Total en lista: {compras.length}</p>
            )}
          </div>
          <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center text-slate-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Total Gravadas</p>
            <h3 className="text-xl font-bold text-slate-900">
              ${comprasActivas.reduce((sum, item) => sum + (item.compras_internas_gravadas || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h3>
            {comprasOmitidas.length > 0 && (
              <p className="text-[11px] text-slate-400 mt-0.5">Excluye compras omitidas</p>
            )}
          </div>
          <div className="w-12 h-12 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Exentas / No Sujetas</p>
            <h3 className="text-xl font-bold text-slate-900">
              ${comprasActivas.reduce((sum, item) => sum + (item.compras_internas_exentas || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h3>
            {comprasActivas.some(c => c.tipo_documento === "14") && (
              <p className="text-[11px] text-purple-600 font-semibold mt-0.5">
                {comprasActivas.filter(c => c.tipo_documento === "14").length} Sujeto{comprasActivas.filter(c => c.tipo_documento === "14").length > 1 ? 's' : ''} Excluido{comprasActivas.filter(c => c.tipo_documento === "14").length > 1 ? 's' : ''}
              </p>
            )}
          </div>
          <div className="w-12 h-12 bg-purple-50 rounded-full flex items-center justify-center text-purple-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Total Crédito Fiscal</p>
            <h3 className="text-xl font-bold text-slate-900">
              ${comprasActivas.reduce((sum, item) => sum + (item.credito_fiscal || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h3>
            {comprasOmitidas.length > 0 && (
              <p className="text-[11px] text-slate-400 mt-0.5">F-07 Casilla Compras</p>
            )}
          </div>
          <div className="w-12 h-12 bg-sky-50 rounded-full flex items-center justify-center text-sky-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2zM10 8.5a.5.5 0 11-1 0 .5.5 0 011 0zm5 5a.5.5 0 11-1 0 .5.5 0 011 0z"></path></svg>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 font-medium uppercase tracking-wide">Total Compras</p>
            <h3 className="text-xl font-bold text-slate-900">
              ${comprasActivas.reduce((sum, item) => sum + (item.total_compras || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                <th className="px-4 py-3 text-center text-xs font-bold text-slate-700 uppercase tracking-wider border-l border-slate-200" rowSpan="2">Acciones</th>
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
                  <td colSpan="20" className="px-6 py-10 text-center text-slate-500">
                    Cargando compras...
                  </td>
                </tr>
              ) : compras.length === 0 ? (
                <tr>
                  <td colSpan="20" className="px-6 py-10 text-center text-slate-500">
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
                  <tr 
                    key={compra.id} 
                    className={`transition-colors border-b ${
                      compra.omitido 
                        ? "bg-amber-100/80 border-l-4 border-l-rose-600 border-b-amber-200 hover:bg-amber-200/80 text-rose-950 font-medium" 
                        : "bg-white hover:bg-slate-50 text-slate-800 border-b-slate-100"
                    }`}
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-xs">{compra.fecha_emision}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-center">{compra.clase_documento}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-center">
                      {compra.tipo_documento === "14" ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200" title="DTE 14: Factura de Sujeto Excluido">
                          14 (FSE)
                        </span>
                      ) : compra.tipo_documento === "05" ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200" title="DTE 05: Nota de Crédito">
                          05 (NC)
                        </span>
                      ) : (
                        <span className="font-mono">{compra.tipo_documento}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs font-mono truncate max-w-[150px]" title={compra.numero_resolucion}>{compra.numero_resolucion}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs">{compra.nit_proveedor}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs truncate max-w-[200px]" title={compra.nombre_proveedor}>
                      <div className="flex items-center space-x-1.5">
                        <span className="truncate">{compra.nombre_proveedor}</span>
                        {compra.omitido && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-black bg-rose-600 text-amber-100 border border-amber-300 shadow-xs flex-shrink-0">
                            OMITIDO
                          </span>
                        )}
                      </div>
                    </td>
                    
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${(compra.compras_internas_exentas || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${(compra.internaciones_exentas || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${(compra.importaciones_exentas || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right font-medium">
                      {compra.omitido ? (
                        <span className="line-through text-rose-700 font-bold decoration-rose-600 decoration-2">
                          ${(compra.compras_internas_gravadas || 0).toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-slate-900">${(compra.compras_internas_gravadas || 0).toFixed(2)}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${(compra.internaciones_gravadas_bienes || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${(compra.importaciones_gravadas_bienes || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right text-slate-600">${(compra.importaciones_gravadas_servicios || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right font-medium">
                      {compra.omitido ? (
                        <span className="line-through text-rose-700 font-bold decoration-rose-600 decoration-2">
                          ${(compra.credito_fiscal || 0).toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-indigo-600 font-semibold">${(compra.credito_fiscal || 0).toFixed(2)}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-right font-bold">
                      {compra.omitido ? (
                        <span className="line-through text-rose-700 font-bold decoration-rose-600 decoration-2">
                          ${(compra.total_compras || 0).toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-emerald-700">${(compra.total_compras || 0).toFixed(2)}</span>
                      )}
                    </td>
                    
                    <td className="px-2 py-3 whitespace-nowrap text-xs text-center border-l border-slate-200">
                      <select 
                        value={compra.tipo_operacion || (compra.tipo_documento === "14" ? "2" : "1")} 
                        onChange={(e) => updateConfig(compra.id, "tipo_operacion", e.target.value)}
                        className={`text-xs rounded p-1 w-20 focus:ring-indigo-500 ${
                          compra.omitido ? "border-amber-400 bg-amber-50 text-slate-500" : "border-slate-300"
                        }`}
                        disabled={isDeclarado || compra.omitido}
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
                        className={`text-xs rounded p-1 w-20 focus:ring-indigo-500 ${
                          compra.omitido ? "border-amber-400 bg-amber-50 text-slate-500" : "border-slate-300"
                        }`}
                        disabled={isDeclarado || compra.omitido}
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
                        className={`text-xs rounded p-1 w-20 focus:ring-indigo-500 ${
                          compra.omitido ? "border-amber-400 bg-amber-50 text-slate-500" : "border-slate-300"
                        }`}
                        disabled={isDeclarado || compra.omitido}
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
                        className={`text-xs rounded p-1 w-20 focus:ring-indigo-500 ${
                          compra.omitido ? "border-amber-400 bg-amber-50 text-slate-500" : "border-slate-300"
                        }`}
                        disabled={isDeclarado || compra.omitido}
                      >
                        <option value="0">-</option>
                        <option value="1">1 Venta</option>
                        <option value="2">2 Admin</option>
                        <option value="3">3 Finan</option>
                        <option value="4">4 Produc</option>
                        <option value="5">5 Costo/Arts</option>
                      </select>
                    </td>

                    <td className="px-3 py-3 whitespace-nowrap text-xs text-center border-l border-slate-200">
                      <div className="flex items-center justify-center space-x-1.5">
                        {compra.omitido ? (
                          <button
                            type="button"
                            onClick={() => toggleOmitir(compra.id, true)}
                            disabled={isDeclarado}
                            title="Reactivar comprobante e incluir en F-07 y archivo CSV"
                            className={`px-2.5 py-1 text-xs font-black rounded border-2 border-rose-600 bg-amber-300 text-rose-900 hover:bg-amber-400 hover:border-rose-700 transition-colors shadow-xs ${
                              isDeclarado ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                            }`}
                          >
                            Reactivar
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => toggleOmitir(compra.id, false)}
                            disabled={isDeclarado}
                            title="Omitir del F-07 y de los cálculos"
                            className={`px-2.5 py-1 text-xs font-medium rounded border border-slate-300 bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition-colors ${
                              isDeclarado ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                            }`}
                          >
                            Omitir
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => eliminarCompra(compra.id, compra.numero_resolucion || compra.nombre_proveedor)}
                          disabled={isDeclarado}
                          title={compra.omitido ? "Eliminar permanentemente este comprobante omitido" : "Eliminar comprobante"}
                          className={`p-1 rounded transition-colors ${
                            compra.omitido
                              ? "text-rose-700 hover:text-rose-950 hover:bg-amber-200"
                              : "text-slate-400 hover:text-rose-600 hover:bg-slate-100"
                          } ${isDeclarado ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
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
