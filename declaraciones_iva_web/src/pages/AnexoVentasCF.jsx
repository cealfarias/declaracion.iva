import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { useAssistant } from "../contexts/AssistantContext";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function AnexoVentasCF() {
  const [searchParams] = useSearchParams();
  const mes = searchParams.get("mes");
  const anio = searchParams.get("anio");
  
  const { user, activeEmpresa } = useAuth();
  const { enqueueMessages } = useAssistant();
  const navigate = useNavigate();

  const [ventas, setVentas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isDeclarado, setIsDeclarado] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!activeEmpresa) {
      navigate("/dashboard");
      return;
    }
    fetchEstadoDeclaracion();
    fetchVentas();
  }, [activeEmpresa, mes, anio]);

  const fetchEstadoDeclaracion = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/compras/estado/${activeEmpresa.id}?mes=${mes}&anio=${anio}&tipo_libro=ventas_cf`);
      setIsDeclarado(response.data.declarado);
      if (response.data.declarado) {
        enqueueMessages([{ text: "Este período ya fue declarado al Ministerio de Hacienda. Se encuentra bloqueado para evitar alteraciones.", type: "warning" }]);
      }
    } catch (error) {
      console.error("Error al cargar el estado de la declaración");
    }
  };

  const fetchVentas = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/ventas-cf/list/${activeEmpresa.id}?mes=${mes}&anio=${anio}`);
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
      await axios.post(`${API_URL}/api/v1/compras/declarar/${activeEmpresa.id}?mes=${mes}&anio=${anio}&tipo_libro=ventas_cf`);
      setIsDeclarado(true);
      enqueueMessages([{ text: "Anexo marcado como Declarado exitosamente. Las modificaciones han sido bloqueadas.", type: "success" }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al marcar como declarado.", type: "error" }]);
    }
  };

  const limpiarAnexo = async () => {
    if (!window.confirm("¿Estás seguro de eliminar TODOS los registros de este mes? Esta acción no se puede deshacer.")) return;
    try {
      await axios.delete(`${API_URL}/api/v1/ventas-cf/limpiar/${activeEmpresa.id}?mes=${mes}&anio=${anio}`);
      enqueueMessages([{ text: "Anexo limpiado exitosamente.", type: "success" }]);
      fetchVentas();
    } catch (error) {
      enqueueMessages([{ text: "Error al limpiar el anexo.", type: "error" }]);
    }
  };

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    if (isDeclarado) {
      enqueueMessages([{ text: "El período está declarado, no puedes subir más archivos.", type: "error" }]);
      return;
    }
    
    const formData = new FormData();
    formData.append("empresa_id", activeEmpresa.id);
    formData.append("periodo_mes", mes);
    formData.append("periodo_anio", anio);
    
    Array.from(files).forEach(file => {
      if (file.name.toLowerCase().endsWith(".json")) {
        formData.append("files", file);
      }
    });

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/v1/ventas-cf/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      
      const { procesados, errores } = response.data;
      if (procesados > 0) {
        enqueueMessages([{ text: `Se procesaron exitosamente ${procesados} Facturas (01).`, type: "success" }]);
        fetchVentas();
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
    window.open(`${API_URL}/api/v1/ventas-cf/export_csv/${activeEmpresa.id}?mes=${mes}&anio=${anio}`, "_blank");
  };

  if (!activeEmpresa) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in-up">
      <div className="flex justify-between items-start mb-6">
        <div>
          <div className="flex items-center space-x-2 text-sm text-slate-500 mb-2">
            <button onClick={() => navigate("/dashboard")} className="hover:text-indigo-600">Dashboard</button>
            <span>/</span>
            <span className="text-slate-800 font-medium">Anexo Ventas C.F.</span>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
            {activeEmpresa.razon_social}
          </h1>
          <p className="text-slate-500 mt-1">Período: {mes}/{anio} - Consumidor Final</p>
        </div>
        <div className="flex space-x-3">
          {!isDeclarado && (
            <>
              <button 
                onClick={limpiarAnexo}
                className="px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
              >
                🗑️ Limpiar Anexo
              </button>
              <button 
                onClick={declararAnexo}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
              >
                🔒 Marcar como Declarado
              </button>
            </>
          )}
          <button 
            onClick={exportCSV}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
          >
            Descargar CSV F07
          </button>
        </div>
      </div>

      <div 
        className={`mb-8 border-2 border-dashed rounded-xl p-10 text-center transition-colors ${!isDeclarado ? "cursor-pointer" : "opacity-50 cursor-not-allowed"} ${
          isDragging ? "border-amber-500 bg-amber-50" : "border-slate-300 bg-white hover:border-amber-400 hover:bg-slate-50"
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
        <div className="mx-auto w-16 h-16 mb-4 text-slate-400">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <p className="text-lg font-medium text-slate-700 mb-1">
          {isDeclarado ? "Período cerrado" : "Arrastra los DTEs (Facturas 01) aquí"}
        </p>
        <p className="text-sm text-slate-500">
          {isDeclarado ? "No se pueden subir más documentos a este período" : "Sube carpetas completas o archivos JSON individuales"}
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-slate-800">
            Detalle de Ventas ({ventas.length})
          </h2>
          <div className="text-sm text-slate-600 font-medium">
            Total Ventas: <span className="text-indigo-600">${ventas.reduce((acc, v) => acc + v.total_ventas, 0).toFixed(2)}</span>
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
                  <tr key={v.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-slate-600">{v.fecha_emision}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{v.nit_cliente || "Consumidor Final"}</td>
                    <td className="px-4 py-3 text-slate-500 font-mono text-xs">{v.codigo_generacion}</td>
                    <td className="px-4 py-3 text-right text-slate-700">${v.ventas_gravadas.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right text-slate-700">${v.ventas_exentas.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-medium text-slate-900">${v.total_ventas.toFixed(2)}</td>
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
