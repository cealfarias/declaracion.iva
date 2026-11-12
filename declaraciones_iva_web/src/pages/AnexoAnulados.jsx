import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { Ban, Download, Lock, Trash2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAssistant } from "../contexts/AssistantContext";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function AnexoAnulados() {
  const [searchParams] = useSearchParams();
  const currentDate = new Date();
  const mes = searchParams.get("mes") || localStorage.getItem("dashboard_mes") || String(currentDate.getMonth() + 1).padStart(2, "0");
  const anio = searchParams.get("anio") || localStorage.getItem("dashboard_anio") || String(currentDate.getFullYear());

  const { user, activeEmpresa } = useAuth();
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  const [anulados, setAnulados] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const [versiones, setVersiones] = useState([{version: 1, declarado: false, numero_declaracion: ""}]);
  const [activeVersion, setActiveVersion] = useState(1);
  const [numeroInput, setNumeroInput] = useState("");

  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!activeEmpresa) {
      navigate("/dashboard");
      return;
    }
    enqueueMessages([{ text: `🔍 Verificando el registro de Documentos Anulados para el período ${mes}/${anio}. Un momento por favor, estoy consultando los eventos de invalidación registrados...`, type: "info" }]);
    fetchEstadoDeclaracion();
    fetchAnulados();
  }, [activeEmpresa, mes, anio, activeVersion]);


  const fetchEstadoDeclaracion = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/anulados/estado/${activeEmpresa.id}?mes=${mes}&anio=${anio}&tipo_libro=anulados_cf`);
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
      await axios.put(`${API_URL}/api/v1/anulados/estado/${activeEmpresa.id}/numero?mes=${mes}&anio=${anio}&numero=${numeroInput}&version=${activeVersion}&tipo_libro=anulados_cf`);
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
      await axios.post(`${API_URL}/api/v1/anulados/modificatoria/${activeEmpresa.id}?mes=${mes}&anio=${anio}&numero_original=${original}&tipo_libro=anulados_cf`);
      enqueueMessages([{ text: "Modificatoria creada exitosamente. Candado abierto.", type: "success" }]);
      fetchEstadoDeclaracion();
      if(api_path === "compras") fetchCompras(); else fetchAnulados();
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || "Error al crear modificatoria.", type: "error" }]);
    }
  };

  const currentEstado = versiones.find(v => v.version === activeVersion) || {declarado: false};
  const isDeclarado = currentEstado.declarado;

  const fetchAnulados = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/anulados/list/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      setAnulados(response.data);
    } catch (error) {
      enqueueMessages([{ text: "Error al obtener las anulados a consumidor final.", type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const declararAnexo = async () => {
    if (!window.confirm("¿Seguro que deseas marcar este período como DECLARADO? Ya no podrás agregar, modificar ni eliminar archivos.")) return;
    try {
      await axios.post(`${API_URL}/api/v1/anulados/declarar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}&tipo_libro=anulados_cf`);
      fetchEstadoDeclaracion();
      enqueueMessages([{ text: "Anexo marcado como Declarado exitosamente. Las modificaciones han sido bloqueadas.", type: "success" }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al marcar como declarado.", type: "error" }]);
    }
  };

  const limpiarAnexo = async () => {
    if (!window.confirm("¿Estás seguro de eliminar TODOS los registros de este mes? Esta acción no se puede deshacer.")) return;
    try {
      await axios.delete(`${API_URL}/api/v1/anulados/limpiar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      enqueueMessages([{ text: "Anexo limpiado exitosamente.", type: "success" }]);
      fetchAnulados();
    } catch (error) {
      enqueueMessages([{ text: "Error al limpiar el anexo.", type: "error" }]);
    }
  };

  const handleEliminarIndividual = async (id, codigo) => {
    if (!window.confirm(`¿Estás seguro de eliminar el documento ${codigo} del registro de anulados? Volverá a computarse como venta activa.`)) return;
    try {
      await axios.delete(`${API_URL}/api/v1/anulados/documento/${id}`);
      enqueueMessages([{ text: "Documento eliminado de anulados correctamente.", type: "success" }]);
      fetchAnulados();
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || "Error al eliminar el documento.", type: "error" }]);
    }
  };

  const MESES_NOMBRES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    if (isDeclarado) {
      enqueueMessages([{ text: "El período está declarado, no puedes subir más archivos.", type: "error" }]);
      return;
    }

    const jsonFiles = Array.from(files).filter(file => file.name.toLowerCase().endsWith(".json"));

    if (jsonFiles.length === 0) {
      enqueueMessages([{ text: `⚠️ En esa carpeta no hay archivos JSON para el Anexo de Documentos Anulados. Por favor verifica que estás seleccionando la carpeta correcta con los JSON de Invalidación.`, type: "error" }]);
      return;
    }

    const nombreMes = MESES_NOMBRES[(parseInt(mes, 10) - 1)] || mes;
    enqueueMessages([{ text: `⏳ Procesando y validando contra el Ministerio de Hacienda los JSON de Anulados de ${nombreMes}...`, type: "info" }]);

    const formData = new FormData();
    formData.append("empresa_id", activeEmpresa.id);
    formData.append("periodo_mes", mes);
    formData.append("periodo_anio", anio);
    formData.append("version", activeVersion);

    jsonFiles.forEach(file => {
      formData.append("files", file);
    });

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/v1/anulados/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      const { procesados, errores } = response.data;
      if (procesados > 0) {
        enqueueMessages([{ text: `Se procesaron exitosamente ${procesados} Eventos de Invalidación.`, type: "success" }]);
        fetchAnulados();
      }
      if (errores && errores.length > 0) {
        const errorText = errores.slice(0, 5).join("\n") + (errores.length > 5 ? `\n...y ${errores.length - 5} más.` : "");
        enqueueMessages([{ text: `Errores en ${errores.length} archivos:\n${errorText}`, type: "error" }]);
      }
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || "Error al subir los archivos.", type: "error" }]);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    if (!isDeclarado) setIsDragging(true);
  };
  const onDragLeave = () => setIsDragging(false);
  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (!isDeclarado) handleFileUpload(e.dataTransfer.files);
  };

  const exportCSV = () => {
    window.open(`${API_URL}/api/v1/anulados/export_csv/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`, "_blank");
  };

  if (!activeEmpresa) return null;

  return (
    <div className="space-y-6 animate-fade-in-up">

      <div className="flex w-fit max-w-full flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1.5 shadow-sm">
        {versiones.map(v => (
          <button
            key={v.version}
            onClick={() => setActiveVersion(v.version)}
            className={`rounded-lg px-4 py-2 font-medium text-sm transition-colors ${
              activeVersion === v.version
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
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
            <button onClick={crearModificatoria} className="px-4 py-2 bg-blue-600 text-white rounded-lg shadow-sm text-sm hover:bg-blue-700">
              Crear Modificatoria
            </button>
          )}
        </div>
      )}

      <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-rose-700 ring-1 ring-rose-100">
              <Ban className="h-3 w-3" />
              Invalidados · Consumidor Final
            </span>
            <span className="text-xs text-slate-500">Período {mes}/{anio}</span>
          </div>
          <h2 className="mt-2 truncate text-xl font-bold tracking-tight text-slate-900">
            {activeEmpresa.razon_social}
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            NIT {activeEmpresa.nit} · {anulados.length} documento{anulados.length === 1 ? '' : 's'} invalidado{anulados.length === 1 ? '' : 's'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!isDeclarado && (
            <>
              <button
                onClick={limpiarAnexo}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-100"
              >
                <Trash2 className="h-4 w-4" />
                Limpiar
              </button>
              <button
                onClick={declararAnexo}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800 transition-colors hover:bg-amber-100"
              >
                <Lock className="h-4 w-4" />
                Marcar como declarado
              </button>
            </>
          )}
          <button
            onClick={exportCSV}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700"
          >
            <Download className="h-4 w-4" />
            Descargar CSV F-07
          </button>
        </div>
      </div>

      <div
        className={`mb-8 border-2 border-dashed rounded-xl p-10 text-center transition-colors ${!isDeclarado ? "cursor-pointer" : "opacity-50 cursor-not-allowed"} ${
          isDragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50"
        }`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => { if(!isDeclarado) fileInputRef.current.click(); }}
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
        <div className="mx-auto w-16 h-16 mb-4 text-blue-600">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <p className="text-lg font-medium text-slate-700 mb-1">
          {isDeclarado ? "Período cerrado" : "Arrastra los JSON de Eventos de Invalidación / Anulados aquí"}
        </p>
        <p className="text-sm text-slate-500">
          {isDeclarado ? "No se pueden subir más documentos a este período" : "Validación automática con Ministerio de Hacienda (MH) para evitar anular facturas vigentes por error."}
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-slate-800">
            Detalle de Anulados ({anulados.length})
          </h2>
          <div className="text-sm text-slate-600 font-medium">
            Documentos Anulados: <span className="text-blue-600">${anulados.filter(v => !v.anulado).reduce((acc, v) => acc + (v.total_anulados || 0), 0).toFixed(2)}</span>
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500">Cargando registros...</div>
        ) : anulados.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p>No hay documentos anulados en este período.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 uppercase font-medium">
                <tr>
                  <th className="px-4 py-3">Fecha</th>
                  <th className="px-4 py-3">Tipo Doc</th>
                  <th className="px-4 py-3">Código Generación (Anulado)</th>
                  <th className="px-4 py-3">Sello Recepción (Invalidación)</th>
                  <th className="px-4 py-3 text-center">Estado MH</th>
                  {!isDeclarado && <th className="px-4 py-3 text-center">Acción</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {anulados.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-slate-600">{a.fecha_emision}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{a.tipo_documento}</td>
                    <td className="px-4 py-3 text-red-500 font-mono text-xs">{a.codigo_generacion}</td>
                    <td className="px-4 py-3 text-slate-500 font-mono text-xs">{a.sello_recepcion}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                        ✓ Invalidado en MH
                      </span>
                    </td>
                    {!isDeclarado && (
                      <td className="px-4 py-3 text-center">
                        <button
                          type="button"
                          onClick={() => handleEliminarIndividual(a.id, a.codigo_generacion)}
                          title="Eliminar de anulados (reintegrar como venta activa)"
                          className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors inline-flex items-center justify-center"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
