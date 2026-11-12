import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { Download, Lock, Receipt, Trash2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAssistant } from "../contexts/AssistantContext";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function AnexoVentasCF() {
  const [searchParams] = useSearchParams();
  const currentDate = new Date();
  const mes = searchParams.get("mes") || localStorage.getItem("dashboard_mes") || String(currentDate.getMonth() + 1).padStart(2, "0");
  const anio = searchParams.get("anio") || localStorage.getItem("dashboard_anio") || String(currentDate.getFullYear());

  const { user, activeEmpresa } = useAuth();
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  const [ventas, setVentas] = useState([]);
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
    enqueueMessages([{ text: `🧾 Cargando el Libro de Ventas a Consumidor Final del período ${mes}/${anio}. Dame un instante, estoy procesando la información fiscal del período...`, type: "info" }]);
    fetchEstadoDeclaracion();
    fetchVentas();
  }, [activeEmpresa, mes, anio, activeVersion]);


  const fetchEstadoDeclaracion = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/ventas-cf/estado/${activeEmpresa.id}?mes=${mes}&anio=${anio}&tipo_libro=ventas_cf`);
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
      await axios.put(`${API_URL}/api/v1/ventas-cf/estado/${activeEmpresa.id}/numero?mes=${mes}&anio=${anio}&numero=${numeroInput}&version=${activeVersion}&tipo_libro=ventas_cf`);
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
      await axios.post(`${API_URL}/api/v1/ventas-cf/modificatoria/${activeEmpresa.id}?mes=${mes}&anio=${anio}&numero_original=${original}&tipo_libro=ventas_cf`);
      enqueueMessages([{ text: "Modificatoria creada exitosamente. Candado abierto.", type: "success" }]);
      fetchEstadoDeclaracion();
      if(api_path === "compras") fetchCompras(); else fetchVentas();
    } catch (error) {
      enqueueMessages([{ text: error.response?.data?.detail || "Error al crear modificatoria.", type: "error" }]);
    }
  };

  const currentEstado = versiones.find(v => v.version === activeVersion) || {declarado: false};
  const isDeclarado = currentEstado.declarado;

  const fetchVentas = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/ventas-cf/list/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      setVentas(response.data);
    } catch (error) {
      enqueueMessages([{ text: "Error al obtener las ventas a consumidor final.", type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const declararAnexo = async () => {
    if (!window.confirm("¿Seguro que deseas marcar este período como DECLARADO? Ya no podrás agregar, modificar ni eliminar archivos.")) return;
    try {
      await axios.post(`${API_URL}/api/v1/ventas-cf/declarar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}&tipo_libro=ventas_cf`);
      fetchEstadoDeclaracion();
      enqueueMessages([{ text: "Anexo marcado como Declarado exitosamente. Las modificaciones han sido bloqueadas.", type: "success" }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al marcar como declarado.", type: "error" }]);
    }
  };

  const limpiarAnexo = async () => {
    if (!window.confirm("¿Estás seguro de eliminar TODOS los registros de este mes? Esta acción no se puede deshacer.")) return;
    try {
      await axios.delete(`${API_URL}/api/v1/ventas-cf/limpiar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      enqueueMessages([{ text: "Anexo limpiado exitosamente.", type: "success" }]);
      fetchVentas();
    } catch (error) {
      enqueueMessages([{ text: "Error al limpiar el anexo.", type: "error" }]);
    }
  };

  const MESES_NOMBRES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    if (isDeclarado) {
      enqueueMessages([{ text: "El período está declarado, no puedes subir más archivos.", type: "error" }]);
      return;
    }

    const validExtensions = ['.json', '.xlsx', '.xls', '.csv'];
    const validFiles = Array.from(files).filter(f => {
      const name = f.name.toLowerCase();
      return validExtensions.some(ext => name.endsWith(ext));
    });

    if (validFiles.length === 0) {
      enqueueMessages([{ text: `⚠️ No se encontraron archivos válidos. Por favor sube archivos JSON de Facturas (01), o el archivo Excel/CSV del Libro de Ventas a Consumidor Final de Hacienda.`, type: "error" }]);
      return;
    }

    const nombreMes = MESES_NOMBRES[(parseInt(mes, 10) - 1)] || mes;
    const hasExcel = validFiles.some(f => f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls') || f.name.toLowerCase().endsWith('.csv'));
    const tipoTexto = hasExcel ? "archivos de Excel / JSON" : "archivos JSON";
    enqueueMessages([{ text: `⏳ Procesando los ${tipoTexto} del Anexo de Ventas a Consumidor Final del mes de ${nombreMes}... Por favor espera mientras importo los comprobantes.`, type: "info" }]);

    setLoading(true);
    let totalProcesados = 0;
    let todosErrores = [];

    try {
      // Para evitar bloqueos por tamaño o límite WAF, subimos 1 por 1
      for (let i = 0; i < validFiles.length; i++) {
        const formData = new FormData();
        formData.append("empresa_id", activeEmpresa.id);
        formData.append("periodo_mes", mes);
        formData.append("periodo_anio", anio);
        formData.append("version", activeVersion);
        formData.append("files", validFiles[i]);

        try {
          const response = await axios.post(`${API_URL}/api/v1/ventas-cf/upload`, formData, {
            headers: { "Content-Type": "multipart/form-data" }
          });
          const { procesados, errores } = response.data;
          totalProcesados += (procesados || 0);
          if (errores && errores.length > 0) {
            todosErrores = [...todosErrores, ...errores];
          }
        } catch (fileErr) {
          const errDetail = fileErr.response?.data?.detail || fileErr.message || "Error procesando archivo";
          todosErrores.push(`${validFiles[i].name}: ${errDetail}`);
        }
      }

      if (totalProcesados > 0) {
        enqueueMessages([{ text: `✅ Se procesaron exitosamente ${totalProcesados} comprobantes/facturas (01).`, type: "success" }]);
        fetchVentas();
      }
      if (todosErrores.length > 0) {
        const errorText = todosErrores.slice(0, 5).join("\n") + (todosErrores.length > 5 ? `\n...y ${todosErrores.length - 5} más.` : "");
        enqueueMessages([{ text: `Avisos en ${todosErrores.length} archivos:\n${errorText}`, type: "error" }]);
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
    window.open(`${API_URL}/api/v1/ventas-cf/export_csv/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`, "_blank");
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
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-blue-700 ring-1 ring-blue-100">
              <Receipt className="h-3 w-3" />
              F-07 · Consumidor Final
            </span>
            <span className="text-xs text-slate-500">Período {mes}/{anio}</span>
          </div>
          <h2 className="mt-2 truncate text-xl font-bold tracking-tight text-slate-900">
            {activeEmpresa.razon_social}
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            NIT {activeEmpresa.nit} · {ventas.filter(v => !v.anulado).length} documento{ventas.filter(v => !v.anulado).length === 1 ? '' : 's'} válido{ventas.filter(v => !v.anulado).length === 1 ? '' : 's'}
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
          accept=".json,.xlsx,.xls,.csv"
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
          {isDeclarado ? "Período cerrado" : "Arrastra tus archivos aquí o haz clic para seleccionarlos"}
        </p>
        {!isDeclarado && (
          <p className="text-sm text-slate-500">
            Soporta <strong>archivos JSON</strong> de Facturas (01) o el <strong>archivo Excel / CSV</strong> del Libro de Ventas a Consumidor oficial de Hacienda
          </p>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-slate-800">
            Detalle de Ventas ({ventas.length})
          </h2>
          <div className="text-sm text-slate-600 font-medium">
            Total Ventas: <span className="text-blue-600">${ventas.filter(v => !v.anulado).reduce((acc, v) => acc + (v.total_ventas || 0), 0).toFixed(2)}</span>
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500">Cargando registros...</div>
        ) : ventas.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p>Aún no hay facturas en este período.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 uppercase font-medium">
                <tr>
                  <th className="px-4 py-3">Fecha</th>
                  <th className="px-4 py-3">Cliente</th>
                  <th className="px-4 py-3">Resolución (Cód. Generación)</th>
                  <th className="px-4 py-3 text-right">Gravadas</th>
                  <th className="px-4 py-3 text-right">Exentas</th>
                  <th className="px-4 py-3 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {ventas.map((v) => (
                  <tr key={v.id} className={`${v.anulado ? "bg-red-50 hover:bg-red-100" : "hover:bg-slate-50"} transition-colors`} title={v.anulado ? "DTE anulado, y no se toma en cuenta en el cálculo" : ""}>
                    <td className={`px-4 py-3 ${v.anulado ? "text-red-500" : "text-slate-600"}`}>
                      {v.fecha_emision}
                      {v.anulado && <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Anulado</span>}
                    </td>
                    <td className={`px-4 py-3 font-medium ${v.anulado ? "text-red-700" : "text-slate-900"}`}>{v.nit_cliente || "Consumidor Final"}</td>
                    <td className={`px-4 py-3 font-mono text-xs ${v.anulado ? "text-red-400" : "text-slate-500"}`}>{v.codigo_generacion}</td>
                    <td className={`px-4 py-3 text-right ${v.anulado ? "text-red-500 line-through" : "text-slate-700"}`}>${v.ventas_gravadas?.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right ${v.anulado ? "text-red-500 line-through" : "text-slate-700"}`}>${v.ventas_exentas?.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right font-medium ${v.anulado ? "text-red-700 line-through" : "text-slate-900"}`}>${v.total_ventas?.toFixed(2)}</td>
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
