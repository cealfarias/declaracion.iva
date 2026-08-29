
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';

const API_URL = import.meta.env.VITE_API_URL || 'https://declaraciones-iva-api.onrender.com';

export default function Liquidacion() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const mes = queryParams.get("mes");
  const anio = queryParams.get("anio");
  
  const { token, activeEmpresa, logout } = useAuth();
  const { enqueueMessages } = useAssistant();
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [editRemanente, setEditRemanente] = useState(false);
  const [remanenteInput, setRemanenteInput] = useState("");

  useEffect(() => {
    if (!token) return;
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    if (!activeEmpresa) {
      navigate('/dashboard');
    }
  }, [token, activeEmpresa, navigate]);

  useEffect(() => {
    if (activeEmpresa && mes && anio) {
      fetchLiquidacion();
    }
  }, [activeEmpresa, mes, anio]);

  const fetchLiquidacion = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/liquidacion/${activeEmpresa.id}?mes=${mes}&anio=${anio}`);
      setData(response.data);
      setRemanenteInput(response.data.remanente_anterior.toString());
    } catch (error) {
      enqueueMessages([{ text: "Error al cargar la liquidación.", type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const saveRemanente = async () => {
    try {
      const val = parseFloat(remanenteInput) || 0;
      await axios.post(`${API_URL}/api/v1/liquidacion/${activeEmpresa.id}/remanente?mes=${mes}&anio=${anio}&remanente=${val}`);
      enqueueMessages([{ text: "Remanente actualizado.", type: "success" }]);
      setEditRemanente(false);
      fetchLiquidacion();
    } catch (error) {
      enqueueMessages([{ text: "Error al guardar remanente.", type: "error" }]);
    }
  };

  if (!activeEmpresa) return null;

  return (
    <div className="bg-slate-50 min-h-screen pb-12">
      {/* Header */}
      <div className="bg-indigo-600 border-b border-indigo-700 sticky top-0 z-30 shadow-md">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <button 
                onClick={() => navigate("/dashboard")}
                className="text-indigo-100 hover:text-white transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              </button>
              <div>
                <h1 className="text-xl font-bold text-white">Liquidación de Impuestos F-07</h1>
                <p className="text-sm text-indigo-200">Período: <span className="font-medium text-white">{mes}/{anio}</span></p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button 
                onClick={() => window.print()}
                className="bg-indigo-500 hover:bg-indigo-400 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm flex items-center border border-indigo-400"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" /></svg>
                Imprimir
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {loading || !data ? (
          <div className="text-center py-10 text-slate-500">Calculando liquidación...</div>
        ) : (
          <div className="space-y-6">
            
            {/* Débito Fiscal */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="bg-sky-50 px-6 py-4 border-b border-sky-100 flex justify-between items-center">
                <h2 className="text-lg font-bold text-sky-800 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  Operaciones de Venta (Débito Fiscal)
                </h2>
              </div>
              <div className="p-0">
                <table className="w-full text-sm text-left text-slate-600">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-xs">
                    <tr>
                      <th className="px-6 py-3 font-semibold">Concepto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Valor Neto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Débito Fiscal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-700">Ventas a Consumidor Final</td>
                      <td className="px-6 py-3 text-right">${data.ventas_cf.neto.toFixed(2)}</td>
                      <td className="px-6 py-3 text-right font-medium text-slate-900">${data.ventas_cf.debito.toFixed(2)}</td>
                    </tr>
                    <tr className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-700">Ventas a Contribuyentes (CCF)</td>
                      <td className="px-6 py-3 text-right">${data.ventas_ccf.neto.toFixed(2)}</td>
                      <td className="px-6 py-3 text-right font-medium text-slate-900">${data.ventas_ccf.debito.toFixed(2)}</td>
                    </tr>
                  </tbody>
                  <tfoot className="bg-sky-50 font-bold border-t border-sky-100">
                    <tr>
                      <td className="px-6 py-3 text-sky-900 text-right" colSpan="2">TOTAL DÉBITO FISCAL:</td>
                      <td className="px-6 py-3 text-right text-sky-900 text-lg">${data.totales.debito.toFixed(2)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Crédito Fiscal */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="bg-amber-50 px-6 py-4 border-b border-amber-100 flex justify-between items-center">
                <h2 className="text-lg font-bold text-amber-800 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                  Operaciones de Compra (Crédito Fiscal)
                </h2>
              </div>
              <div className="p-0">
                <table className="w-full text-sm text-left text-slate-600">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-xs">
                    <tr>
                      <th className="px-6 py-3 font-semibold">Concepto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Valor Neto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Crédito Fiscal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-700">Compras Locales e Importaciones Gravadas</td>
                      <td className="px-6 py-3 text-right">${data.compras.neto.toFixed(2)}</td>
                      <td className="px-6 py-3 text-right font-medium text-slate-900">${data.compras.credito.toFixed(2)}</td>
                    </tr>
                  </tbody>
                  <tfoot className="bg-amber-50 font-bold border-t border-amber-100">
                    <tr>
                      <td className="px-6 py-3 text-amber-900 text-right" colSpan="2">TOTAL CRÉDITO FISCAL:</td>
                      <td className="px-6 py-3 text-right text-amber-900 text-lg">${data.totales.credito.toFixed(2)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Liquidación Final */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="bg-emerald-600 px-6 py-4 flex justify-between items-center">
                <h2 className="text-lg font-bold text-white flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                  Liquidación de Impuesto
                </h2>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  <div className="flex justify-between items-center text-slate-600">
                    <span>(+) Total Débito Fiscal</span>
                    <span className="font-medium">${data.totales.debito.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600">
                    <span>(-) Total Crédito Fiscal</span>
                    <span className="font-medium">-${data.totales.credito.toFixed(2)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center text-slate-600 pt-4 border-t border-slate-200">
                    <div className="flex items-center">
                      <span>(-) Remanente mes anterior</span>
                      <button onClick={() => setEditRemanente(!editRemanente)} className="ml-2 text-indigo-500 hover:text-indigo-700">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                      </button>
                    </div>
                    {editRemanente ? (
                      <div className="flex items-center space-x-2">
                        <span className="text-slate-500">$</span>
                        <input 
                          type="number" 
                          step="0.01" 
                          value={remanenteInput} 
                          onChange={(e) => setRemanenteInput(e.target.value)}
                          className="w-24 border border-slate-300 rounded px-2 py-1 text-right text-sm"
                        />
                        <button onClick={saveRemanente} className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded text-xs font-bold hover:bg-emerald-200">OK</button>
                      </div>
                    ) : (
                      <span className="font-medium">-${data.remanente_anterior.toFixed(2)}</span>
                    )}
                  </div>

                  <div className="pt-4 border-t-2 border-slate-200 mt-4">
                    {data.impuesto_a_pagar > 0 ? (
                      <div className="flex justify-between items-center bg-red-50 p-4 rounded-lg border border-red-100">
                        <span className="text-red-800 font-bold text-lg">Impuesto a Pagar</span>
                        <span className="text-red-700 font-black text-2xl">${data.impuesto_a_pagar.toFixed(2)}</span>
                      </div>
                    ) : (
                      <div className="flex justify-between items-center bg-emerald-50 p-4 rounded-lg border border-emerald-100">
                        <span className="text-emerald-800 font-bold text-lg">Remanente para Siguiente Mes</span>
                        <span className="text-emerald-700 font-black text-2xl">${data.remanente_siguiente.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                  
                </div>
              </div>
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
}
