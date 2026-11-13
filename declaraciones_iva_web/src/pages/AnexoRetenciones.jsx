import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { Download, Percent, Trash2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAssistant } from "../contexts/AssistantContext";
import { downloadAuthenticatedFile } from "../utils/downloadAuthenticatedFile";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function AnexoRetenciones() {
  const [searchParams] = useSearchParams();
  const currentDate = new Date();
  const mes = searchParams.get("mes") || localStorage.getItem("dashboard_mes") || String(currentDate.getMonth() + 1).padStart(2, "0");
  const anio = searchParams.get("anio") || localStorage.getItem("dashboard_anio") || String(currentDate.getFullYear());

  const { token, activeEmpresa } = useAuth();
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  const [documentos, setDocumentos] = useState([]);
  const [totales, setTotales] = useState({ total_documentos: 0, total_monto_sujeto: 0, total_retencion: 0 });
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [activeVersion, setActiveVersion] = useState(1);

  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!activeEmpresa) {
      navigate("/dashboard");
      return;
    }
    fetchRetenciones();
  }, [activeEmpresa, mes, anio, activeVersion]);

  const fetchRetenciones = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_URL}/api/v1/retenciones/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      setDocumentos(res.data.documentos || []);
      setTotales(res.data.totales || { total_documentos: 0, total_monto_sujeto: 0, total_retencion: 0 });
    } catch (error) {
      console.error("Error al cargar retenciones", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;
    const formData = new FormData();
    formData.append("mes", mes);
    formData.append("anio", anio);
    formData.append("version", activeVersion);

    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      setLoading(true);
      enqueueMessages([{ text: "⏳ Procesando comprobantes de retención tipo 07...", type: "info" }]);
      const response = await axios.post(`${API_URL}/api/v1/retenciones/upload/${activeEmpresa.id}`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      const { procesados, errores, ignorados_no_07 } = response.data;
      if (procesados > 0) {
        enqueueMessages([{ text: `✅ Se procesaron exitosamente ${procesados} comprobantes de retención (Casilla 162).`, type: "success" }]);
      } else {
        enqueueMessages([{ text: "No se agregaron nuevas retenciones. Verifica que los archivos correspondan al tipo DTE 07.", type: "warning" }]);
      }

      if (errores && errores.length > 0) {
        enqueueMessages([{ text: `Observaciones: ${errores.slice(0, 3).join("; ")}`, type: "warning" }]);
      }

      fetchRetenciones();
    } catch (error) {
      console.error("Error al subir archivos", error);
      const msg = error.response?.data?.detail || "Error al procesar los archivos";
      enqueueMessages([{ text: `❌ ${msg}`, type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCsv = async () => {
    if (!activeEmpresa || exporting) return;
    setExporting(true);
    try {
      const filename = await downloadAuthenticatedFile({
        url: `${API_URL}/api/v1/retenciones/exportar-csv/${activeEmpresa.id}?mes=${encodeURIComponent(mes)}&anio=${encodeURIComponent(anio)}&version=${activeVersion}`,
        token,
        fallbackFilename: `Anexo7_Retencion1_Casilla162_${anio}_${mes}.csv`,
      });
      enqueueMessages([{ text: `Archivo ${filename} descargado correctamente.`, type: "success" }]);
    } catch (error) {
      enqueueMessages([{ text: error.message || "No se pudo exportar el CSV.", type: "error" }]);
    } finally {
      setExporting(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar todas las retenciones registradas para este período?")) return;
    try {
      setLoading(true);
      await axios.delete(`${API_URL}/api/v1/retenciones/${activeEmpresa.id}?mes=${mes}&anio=${anio}&version=${activeVersion}`);
      enqueueMessages([{ text: "Retenciones eliminadas correctamente.", type: "info" }]);
      fetchRetenciones();
    } catch (error) {
      const msg = error.response?.data?.detail || "Error al limpiar registros";
      enqueueMessages([{ text: `❌ ${msg}`, type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in-up">
      <div className="space-y-6">

        {/* Encabezado */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-white p-6 rounded-xl border border-slate-200 shadow-sm gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                <Percent className="h-3 w-3" />
                Retenciones 1%
              </span>
              <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full bg-slate-50 text-slate-600 border border-slate-200">
                F-07 V14 · Pág. 35
              </span>
              <span className="text-xs text-slate-500">Período {mes}/{anio}</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">
              Anexo Retención IVA 1% Efectuada al Declarante
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              {activeEmpresa?.razon_social} · NIT: {activeEmpresa?.nit} · <span className="text-blue-700 font-semibold">Casilla 162 de F-07</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleClear}
              disabled={documentos.length === 0 || loading}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold text-rose-700 bg-rose-50 border border-rose-200 rounded-lg hover:bg-rose-100 transition disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              Limpiar
            </button>
            <button
              onClick={handleDownloadCsv}
              disabled={documentos.length === 0 || loading || exporting}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              {exporting ? "Exportando…" : "Descargar CSV Hacienda"}
            </button>
          </div>
        </div>

        {/* Métricas */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Comprobantes Válidos</span>
            <div className="text-3xl font-black text-slate-800 mt-1">{totales.total_documentos}</div>
            <span className="text-xs text-slate-400 mt-1 block">DTE tipo 07 únicos</span>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Monto Sujeto Total</span>
            <div className="text-3xl font-black text-slate-800 mt-1">${Number(totales.total_monto_sujeto).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <span className="text-xs text-slate-400 mt-1 block">Base gravada declarada</span>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-blue-200 shadow-sm bg-gradient-to-br from-white to-blue-50/50">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-600">Total IVA Retenido (1%)</span>
            <div className="text-3xl font-black text-blue-700 mt-1">${Number(totales.total_retencion).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <span className="text-xs text-blue-600/80 font-medium mt-1 block">Monto a deducir en Casilla 162</span>
          </div>
        </div>

        {/* Zona Drag & Drop */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFileUpload(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition ${
            isDragging
              ? "border-blue-600 bg-blue-50"
              : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50/50"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFileUpload(e.target.files)}
            multiple
            accept=".json"
            className="hidden"
          />
          <div className="flex flex-col items-center justify-center">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center mb-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
            </div>
            <h3 className="text-base font-bold text-slate-800">Arrastra tus archivos JSON de Retención (DTE 07) aquí</h3>
            <p className="text-xs text-slate-500 mt-1">O haz clic para seleccionar archivos desde tu computadora</p>
            <span className="mt-3 text-[11px] font-semibold text-blue-600 bg-blue-50 border border-blue-200/60 px-2.5 py-1 rounded-md">
              Acepta múltiples archivos · Filtra automáticamente tipo 07 · Valida tasa del 1%
            </span>
          </div>
        </div>

        {/* Tabla de Documentos */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
            <h3 className="text-sm font-bold text-slate-800">
              Estructura Oficial para Hacienda (9 Columnas: A - I)
            </h3>
            <span className="text-xs text-slate-500 font-medium">
              {documentos.length} comprobante(s)
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-600 font-bold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">A: NIT Agente</th>
                  <th className="px-4 py-3">B: Fecha</th>
                  <th className="px-4 py-3">C: Tipo</th>
                  <th className="px-4 py-3">D: Sello / Serie</th>
                  <th className="px-4 py-3">E: Código Generación</th>
                  <th className="px-4 py-3 text-right">F: Monto Sujeto</th>
                  <th className="px-4 py-3 text-right">G: Retención 1%</th>
                  <th className="px-4 py-3">H: DUI</th>
                  <th className="px-4 py-3 text-center">I: Anexo</th>
                  <th className="px-4 py-3">Agente Retenedor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {documentos.length === 0 ? (
                  <tr>
                    <td colSpan="10" className="px-6 py-12 text-center text-slate-400 font-sans">
                      No hay comprobantes de retención cargados para este período.
                    </td>
                  </tr>
                ) : (
                  documentos.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-4 py-2.5 text-slate-800 font-medium">{doc.nit_agente || "-"}</td>
                      <td className="px-4 py-2.5 text-slate-600">{doc.fecha_emision}</td>
                      <td className="px-4 py-2.5 text-blue-600 font-semibold">{doc.tipo_documento}</td>
                      <td className="px-4 py-2.5 text-slate-500 max-w-[120px] truncate" title={doc.serie_documento}>
                        {doc.serie_documento || "-"}
                      </td>
                      <td className="px-4 py-2.5 text-slate-700 font-semibold max-w-[140px] truncate" title={doc.numero_documento}>
                        {doc.numero_documento}
                      </td>
                      <td className="px-4 py-2.5 text-right text-slate-700">
                        ${Number(doc.monto_sujeto).toFixed(2)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-bold text-blue-700">
                        ${Number(doc.monto_retencion).toFixed(2)}
                      </td>
                      <td className="px-4 py-2.5 text-slate-500">{doc.dui_agente || "-"}</td>
                      <td className="px-4 py-2.5 text-center font-bold text-slate-600">{doc.numero_anexo}</td>
                      <td className="px-4 py-2.5 font-sans text-slate-800 max-w-[180px] truncate" title={doc.nombre_agente}>
                        {doc.nombre_agente}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
