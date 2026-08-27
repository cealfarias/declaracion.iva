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
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!activeEmpresa) {
      navigate('/dashboard');
      return;
    }
    fetchCompras();
  }, [activeEmpresa, mes, anio]);

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

  const handleFileUpload = async (files) => {
    // Solo permitir enviar archivos con extensión .json (ignorando mayúsculas/minúsculas)
    const jsonFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.json'));
    
    if (jsonFiles.length === 0) {
      enqueueMessages([{ text: "Por favor selecciona una carpeta que contenga archivos JSON válidos.", type: "error" }]);
      return;
    }

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

  if (!activeEmpresa) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in-up">
      {/* Cabecera */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <div className="flex items-center space-x-2 text-sm text-slate-500 mb-2">
            <button onClick={() => navigate('/dashboard')} className="hover:text-indigo-600">Dashboard</button>
            <span>/</span>
            <span className="text-slate-800 font-medium">Anexo de Compras</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Anexo de Compras (F07)</h1>
          <p className="text-sm text-slate-500 mt-1">
            {activeEmpresa.razon_social} | NIT: {activeEmpresa.nit} | Período: {mes}/{anio}
          </p>
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={exportCSV}
            className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-sm hover:bg-emerald-700 transition"
          >
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Zona de Drag and Drop */}
      <div 
        className={`mb-8 border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
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

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Fecha</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Proveedor</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Gravadas</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">IVA</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Total</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider" colSpan="4">Configuración F07</th>
              </tr>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th colSpan="5"></th>
                <th className="px-2 py-2 text-xs text-slate-500 font-normal">T. Operación</th>
                <th className="px-2 py-2 text-xs text-slate-500 font-normal">Clasificación</th>
                <th className="px-2 py-2 text-xs text-slate-500 font-normal">Sector</th>
                <th className="px-2 py-2 text-xs text-slate-500 font-normal">Costo/Gasto</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {loading && compras.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-6 py-10 text-center text-slate-500">
                    Cargando compras...
                  </td>
                </tr>
              ) : compras.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-6 py-10 text-center text-slate-500">
                    <div className="flex flex-col items-center">
                      <svg className="w-12 h-12 text-slate-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                      <p>No hay compras procesadas en {mes}/{anio}.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                compras.map((compra) => (
                  <tr key={compra.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">{compra.fecha_emision}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                      <div className="truncate max-w-xs" title={compra.nombre_proveedor}>{compra.nombre_proveedor}</div>
                      <div className="text-xs text-slate-500">{compra.nit_proveedor}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-slate-900">${compra.compras_internas_gravadas.toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-slate-900">${compra.credito_fiscal.toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-slate-900">${compra.total_compras.toFixed(2)}</td>
                    <td className="px-2 py-4 whitespace-nowrap text-sm text-center">
                      <select 
                        value={compra.tipo_operacion || "0"} 
                        onChange={(e) => updateConfig(compra.id, "tipo_operacion", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20"
                      >
                        <option value="0">-</option>
                        <option value="1">1 Grav</option>
                        <option value="2">2 No Grav</option>
                      </select>
                    </td>
                    <td className="px-2 py-4 whitespace-nowrap text-sm text-center">
                      <select 
                        value={compra.clasificacion || "0"} 
                        onChange={(e) => updateConfig(compra.id, "clasificacion", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20"
                      >
                        <option value="0">-</option>
                        <option value="1">1 Costo</option>
                        <option value="2">2 Gasto</option>
                      </select>
                    </td>
                    <td className="px-2 py-4 whitespace-nowrap text-sm text-center">
                      <select 
                        value={compra.sector || "0"} 
                        onChange={(e) => updateConfig(compra.id, "sector", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20"
                      >
                        <option value="0">-</option>
                        <option value="1">1 Ind</option>
                        <option value="2">2 Com</option>
                        <option value="3">3 Agro</option>
                        <option value="4">4 Serv</option>
                      </select>
                    </td>
                    <td className="px-2 py-4 whitespace-nowrap text-sm text-center">
                      <select 
                        value={compra.tipo_costo_gasto || "0"} 
                        onChange={(e) => updateConfig(compra.id, "tipo_costo_gasto", e.target.value)}
                        className="text-xs border-slate-300 rounded p-1 w-20"
                      >
                        <option value="0">-</option>
                        <option value="1">1 Venta</option>
                        <option value="2">2 Admin</option>
                        <option value="3">3 Fin</option>
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
