import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle2, Download, Receipt, Upload } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function AnexoVentasContribuyentes() {
  const [searchParams] = useSearchParams();
  const currentDate = new Date();
  const mes = searchParams.get("mes") || localStorage.getItem("dashboard_mes") || String(currentDate.getMonth() + 1).padStart(2, "0");
  const anio = searchParams.get("anio") || localStorage.getItem("dashboard_anio") || String(currentDate.getFullYear());

  const { user, activeEmpresa } = useAuth();
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  const [ventasContribuyentes, setventasContribuyentes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const [versiones, setVersiones] = useState([{version: 1, declarado: false, numero_declaracion: ""}]);
  const [activeVersion, setActiveVersion] = useState(1);
  const [numeroInput, setNumeroInput] = useState("");
  const [showModificatoriaModal, setShowModificatoriaModal] = useState(false);
  const [numeroDeclaracionOriginal, setNumeroDeclaracionOriginal] = useState("");

  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!activeEmpresa) {
      navigate('/dashboard');
      return;
    }
    enqueueMessages([{ text: `📊 Accediendo al Libro de Ventas a Contribuyentes para el período ${mes}/${anio}. Por favor aguarda, estoy sincronizando la información con el servidor...`, type: "info" }]);
    fetchEstadoDeclaracion();
    fetchventasContribuyentes();
  }, [activeEmpresa, mes, anio, activeVersion]);


  const fetchEstadoDeclaracion = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/ventas-contribuyentes/estado/${activeEmpresa.id}?mes=${mes}&anio=${anio}&tipo_libro=ventas_contribuyentes`);
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
      await axios.put(`${API_URL}/api/v1/ventas-contribuyentes/estado/${activeEmpresa.id}/numero?mes=${mes}&anio=${anio}&numero=${numeroInput}&version=${activeVersion}&tipo_libro=ventas_contribuyentes`);
      enqueueMessages([{ text: "Número de declaración guardado correctamente.", type: "success" }]);
      fetchEstadoDeclaracion();
    } catch (error) {
      enqueueMessages([{ text: "Error al guardar el número.", type: "error" }]);
    }
  };

    const handleCrearModificatoria = async () => {
    if (!numeroDeclaracionOriginal) {
      enqueueMessages([{ text: "Por favor, ingresa el número de declaración original.", type: "error" }]);
      return;
    }

    try {
      await axios.post(`${API_URL}/api/v1/ventas-contribuyentes/modificatoria/${activeEmpresa.id}?mes=${mes}&anio=${anio}&numero_original=${numeroDeclaracionOriginal}&tipo_libro=ventas_contribuyentes`);
      enqueueMessages([{ text: "Modificatoria creada exitosamente. Candado abierto.", type: "success" }]);
      setShowModificatoriaModal(false);
      setNumeroDeclaracionOriginal("");
      fetchEstadoDeclaracion();
      fetchventasContribuyentes();
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || "Error al crear modificatoria.", type: "error" }]);
    }
  };

  const currentEstado = versiones.find(v => v.version === activeVersion) || {declarado: false};
  const isDeclarado = currentEstado.declarado;

  const fetchventasContribuyentes = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/ventas-contribuyentes/list/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      setventasContribuyentes(response.data);
    } catch (error) {
      enqueueMessages([{ text: "Error al cargar las ventasContribuyentes.", type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeclarar = async () => {
    if (!window.confirm("¿Estás seguro de marcar este anexo como Declarado? Ya no podrás subir ni modificar ventasContribuyentes para este mes.")) return;
    try {
      await axios.post(`${API_URL}/api/v1/ventas-contribuyentes/declarar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      fetchEstadoDeclaracion();
      enqueueMessages([{ text: "Anexo marcado como Declarado exitosamente.", type: "success" }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al marcar como declarado.", type: "error" }]);
    }
  };

  const MESES_NOMBRES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

  const handleFileUpload = async (files) => {
    // Solo permitir enviar archivos con extensión .json (ignorando mayúsculas/minúsculas)
    // Permitir archivos .json, .xlsx, .xls y .csv (ignorando mayúsculas/minúsculas)
    const validExtensions = ['.json', '.xlsx', '.xls', '.csv'];
    const validFiles = Array.from(files).filter(f => {
      const name = f.name.toLowerCase();
      return validExtensions.some(ext => name.endsWith(ext));
    });

    if (validFiles.length === 0) {
      enqueueMessages([{ text: `⚠️ No se encontraron archivos válidos. Por favor sube archivos JSON de DTEs, o el archivo Excel/CSV del Libro de Ventas a Contribuyentes de Hacienda.`, type: "error" }]);
      return;
    }

    const nombreMes = MESES_NOMBRES[(parseInt(mes, 10) - 1)] || mes;
    const hasExcel = validFiles.some(f => f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls') || f.name.toLowerCase().endsWith('.csv'));
    const tipoTexto = hasExcel ? "archivos de Excel / JSON" : "archivos JSON";
    enqueueMessages([{ text: `⏳ Procesando los ${tipoTexto} del Anexo de Ventas a Contribuyentes del mes de ${nombreMes}... Por favor espera mientras importo los comprobantes.`, type: "info" }]);

    setLoading(true);
    let totalProcesados = 0;
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
          const response = await axios.post(`${API_URL}/api/v1/ventas-contribuyentes/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
                    if (response.data.procesados) {
              totalProcesados += response.data.procesados;
            }
            if (response.data.errores && response.data.errores.length > 0) {
              todosErrores = [...todosErrores, ...response.data.errores];
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
      fetchventasContribuyentes();
    } catch (error) {
      console.error(error);
      enqueueMessages([{ text: `Error inesperado al procesar los archivos.`, type: "error" }]);
      fetchventasContribuyentes();
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

  const handleExportCSV = () => {
    window.open(`${API_URL}/api/v1/ventas-contribuyentes/export_csv/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`, "_blank");
  };

    const updateConfig = async (id, field, value) => {
    const newData = ventasContribuyentes.map(item => {
      if (item.id === id) {
        return { ...item, [field]: value };
      }
      return item;
    });
    setventasContribuyentes(newData);

    try {
      const item = newData.find(i => i.id === id);
      await axios.put(`${API_URL}/api/v1/ventas-contribuyentes/update_operacion/${id}?tipo_operacion=${item.tipo_operacion || "1"}&tipo_ingreso=${item.tipo_ingreso || "2"}`);
    } catch (error) {
      console.error(error);
      enqueueMessages([{ text: "Error guardando configuración", type: "error" }]);
      fetchventasContribuyentes();
    }
  };

  const handleLimpiar = async () => {
    if (!window.confirm("¿Estás seguro de limpiar todas las ventas registradas en este mes?")) return;
    try {
      await axios.delete(`${API_URL}/api/v1/ventas-contribuyentes/limpiar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      fetchventasContribuyentes();
      enqueueMessages([{ text: "Mes limpiado exitosamente", type: "success" }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al limpiar mes", type: "error" }]);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-blue-700 ring-1 ring-blue-100">
              <Receipt className="h-3 w-3" />
              F-07 · Contribuyentes
            </span>
            <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ring-1 ${
              isDeclarado
                ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
                : "bg-amber-50 text-amber-700 ring-amber-100"
            }`}>
              {isDeclarado ? "Declarado" : "En borrador"}
            </span>
            <span className="text-xs text-slate-500">Período {mes}/{anio}</span>
          </div>
          <h2 className="mt-2 truncate text-xl font-bold tracking-tight text-slate-900">
            {activeEmpresa.razon_social}
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">NIT {activeEmpresa.nit}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!isDeclarado && (
            <>
              <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50">
                <Upload className="h-4 w-4" />
                Importar JSON
                <input type="file" multiple webkitdirectory="true" directory="true" accept=".json" className="hidden" onChange={(e) => handleFileUpload(e.target.files)} />
              </label>
              <button
                onClick={handleDeclarar}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
              >
                <CheckCircle2 className="h-4 w-4" />
                Declarar
              </button>
            </>
          )}

          <button
            onClick={handleExportCSV}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            <Download className="h-4 w-4" />
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="space-y-6">

        {/* Modificatorias Tabs */}
        <div className="flex w-fit max-w-full flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1.5 shadow-sm">
          {versiones.map(v => (
            <button
              key={v.version}
              onClick={() => setActiveVersion(v.version)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${activeVersion === v.version ? "bg-blue-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"}`}
            >
              {v.version === 1 ? "Original" : `Modificatoria ${v.version - 1}`}
              {v.declarado && <span className="ml-2 text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">Cerrada</span>}
            </button>
          ))}

          {versiones.length > 0 && versiones[versiones.length - 1].declarado && versiones.length < 3 && (
            <button
              onClick={() => setShowModificatoriaModal(true)}
              className="ml-auto flex items-center rounded-lg px-3 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-50"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" /></svg>
              Nueva Modificatoria
            </button>
          )}
        </div>

        {/* Action Bar */}
        <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <div className="bg-sky-50 text-sky-700 px-3 py-1.5 rounded-lg text-sm font-medium border border-sky-100">
              <span className="text-slate-500 font-normal mr-1">Total Documentos:</span>
              {ventasContribuyentes.length}
            </div>
            <div className="bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-lg text-sm font-medium border border-emerald-100">
              <span className="text-slate-500 font-normal mr-1">IVA Generado:</span>
              ${ventasContribuyentes.reduce((sum, item) => sum + (item.debito_fiscal || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="bg-blue-50 text-blue-700 px-3 py-1.5 rounded-lg text-sm font-medium border border-blue-100">
              <span className="text-slate-500 font-normal mr-1">Total Ventas:</span>
              ${ventasContribuyentes.reduce((sum, item) => sum + (item.total_ventas || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          {!isDeclarado && ventasContribuyentes.length > 0 && (
             <button
               onClick={handleLimpiar}
               className="text-red-500 hover:text-red-700 text-sm font-medium flex items-center transition"
             >
               <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
               Limpiar Mes
             </button>
          )}
        </div>


        <div
          className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${!isDeclarado ? "cursor-pointer" : "opacity-50 cursor-not-allowed"} ${
            isDragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50"
          }`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => { if(!isDeclarado) document.getElementById('fileUploadCCF').click(); }}
        >
          <input
            id="fileUploadCCF"
            type="file"
            multiple
            accept=".json,.xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
          <div className="mx-auto w-16 h-16 mb-4 text-blue-500">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <p className="text-lg font-medium text-slate-700 mb-1">
            {isDeclarado ? "Período cerrado" : "Arrastra tus archivos aquí o haz clic para seleccionarlos"}
          </p>
          {!isDeclarado && (
            <p className="text-sm text-slate-500">
              Soporta <strong>archivos JSON</strong> de DTEs (CCF, NC, ND) o el <strong>archivo Excel / CSV</strong> del Libro de Ventas a Contribuyentes oficial de Hacienda
            </p>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="min-w-max w-full divide-y divide-slate-200">
              <thead className="bg-slate-50 sticky top-0 z-10 shadow-sm">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">Fecha</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">Documento</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">NIT/NRC</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">Nombre Cliente</th>
                  <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider">Exentas</th>
                  <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider">Gravadas</th>
                  <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider">Débito Fiscal</th>
                  <th className="px-4 py-3 text-right text-xs font-bold text-slate-700 uppercase tracking-wider">Total</th>
                  <th className="px-4 py-3 text-center text-xs font-bold text-blue-700 uppercase tracking-wider border-l border-slate-200">T. Operación</th>
                  <th className="px-4 py-3 text-center text-xs font-bold text-blue-700 uppercase tracking-wider">T. Ingreso</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {loading && ventasContribuyentes.length === 0 ? (
                  <tr><td colSpan="10" className="px-6 py-10 text-center text-slate-500">Cargando...</td></tr>
                ) : ventasContribuyentes.length === 0 ? (
                  <tr><td colSpan="10" className="px-6 py-10 text-center text-slate-500">No hay ventas registradas.</td></tr>
                ) : (
                  [...ventasContribuyentes]
                    .sort((a, b) => new Date(a.fecha_emision.split("/").reverse().join("-")) - new Date(b.fecha_emision.split("/").reverse().join("-")))
                    .map((v) => (
                    <tr key={v.id} className={`hover:bg-slate-50 ${v.anulado ? "bg-red-50 opacity-60" : ""}`}>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs ${v.anulado ? "text-red-700 line-through" : "text-slate-900"}`}>{v.fecha_emision}</td>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs ${v.anulado ? "text-red-700 line-through" : "text-slate-900"}`}>{v.numero_documento}</td>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs ${v.anulado ? "text-red-700 line-through" : "text-slate-500"}`}>{v.nit_nrc_cliente}</td>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs truncate max-w-[200px] ${v.anulado ? "text-red-700 line-through" : "text-slate-900"}`} title={v.nombre_cliente}>
                        {v.anulado && <span className="mr-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Anulado</span>}
                        {v.nombre_cliente}
                      </td>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs text-right ${v.anulado ? "text-red-700 line-through" : "text-slate-600"}`}>${v.ventas_exentas.toFixed(2)}</td>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs text-right ${v.anulado ? "text-red-700 line-through" : "text-slate-900 font-medium"}`}>${v.ventas_gravadas.toFixed(2)}</td>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs text-right ${v.anulado ? "text-red-700 line-through" : "text-slate-600"}`}>${v.debito_fiscal.toFixed(2)}</td>
                      <td className={`px-4 py-3 whitespace-nowrap text-xs text-right ${v.anulado ? "text-red-700 line-through" : "text-emerald-700 font-bold"}`}>${v.total_ventas.toFixed(2)}</td>
                      <td className="px-2 py-3 whitespace-nowrap text-xs text-center border-l border-slate-200">
                        <select
                          value={v.tipo_operacion || "1"}
                          onChange={(e) => updateConfig(v.id, "tipo_operacion", e.target.value)}
                          className="text-xs border-slate-300 rounded p-1 w-24 focus:ring-blue-500"
                          disabled={isDeclarado || v.anulado}
                        >
                          <option value="1">1 Grav</option>
                          <option value="2">2 No Grav</option>
                          <option value="3">3 Excluido</option>
                          <option value="4">4 Mixta</option>
                        </select>
                      </td>
                      <td className="px-2 py-3 whitespace-nowrap text-xs text-center">
                        <select
                          value={v.tipo_ingreso || "2"}
                          onChange={(e) => updateConfig(v.id, "tipo_ingreso", e.target.value)}
                          className="text-xs border-slate-300 rounded p-1 w-24 focus:ring-blue-500"
                          disabled={isDeclarado || v.anulado}
                        >
                          <option value="1">1 Ind.</option>
                          <option value="2">2 Comer.</option>
                          <option value="3">3 Agrop.</option>
                          <option value="4">4 Serv.</option>
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

      {showModificatoriaModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-slate-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={() => setShowModificatoriaModal(false)}></div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-white rounded-xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-sky-100 sm:mx-0 sm:h-10 sm:w-10">
                    <svg className="h-6 w-6 text-sky-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-slate-900" id="modal-title">
                      Crear Declaración Modificatoria
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-slate-500 mb-4">
                        Esto clonará todos los datos de la versión actual a una nueva pestaña donde podrás agregar o quitar facturas para corregir tus impuestos.
                      </p>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                          Nº de Declaración Original (pagada):
                        </label>
                        <input
                          type="text"
                          value={numeroDeclaracionOriginal}
                          onChange={(e) => setNumeroDeclaracionOriginal(e.target.value)}
                          className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-sky-500 focus:border-sky-500 outline-none"
                          placeholder="Ej: 10712000000"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-slate-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={handleCrearModificatoria}
                  className="w-full inline-flex justify-center rounded-lg border border-transparent shadow-sm px-4 py-2 bg-sky-600 text-base font-medium text-white hover:bg-sky-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Crear Modificatoria
                </button>
                <button
                  type="button"
                  onClick={() => setShowModificatoriaModal(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-lg border border-slate-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-slate-700 hover:bg-slate-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

