import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update initial active wizard tab
code = code.replace("useState('subir_detalle')", "useState('compras')")

# 2. Refactor handleProcesarTodo into a parametrized handleProcesar
old_procesar = '''  const handleProcesarTodo = async () => {
    if (!archivos.compras.length && !archivos.ventasContribuyentes.length && !archivos.ventasConsumidor.length) {
      enqueueMessages([{ text: "Por favor selecciona al menos una carpeta con archivos JSON.", type: 'warning' }]);
      return;
    }

    setLoading(true);
    let allOmitidos = [];
    let countAdmitidos = 0;
    
    const processFiles = async (tipo, endpoint) => {
      if (archivos[tipo].length > 0) {
        const formData = new FormData();
        archivos[tipo].forEach(file => {
          formData.append('files', file);
        });
        formData.append('mes', mes);
        formData.append('anio', anio);
        formData.append('usuario_id', user?.id || 1);
        
        try {
          const resp = await axios.post(${API_URL}/api/v1, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          
          if (resp.data.omitidos && resp.data.omitidos.length > 0) {
            allOmitidos = [...allOmitidos, ...resp.data.omitidos];
          }
          if (resp.data.resumen) {
            countAdmitidos += resp.data.resumen.documentos || 0;
          }
        } catch (error) {
          enqueueMessages([{ text: Error al procesar : , type: 'error' }]);
        }
      }
    };

    await processFiles('compras', '/procesar/compras');
    await processFiles('ventasContribuyentes', '/procesar/ventas-contribuyentes');
    await processFiles('ventasConsumidor', '/procesar/ventas-consumidor');

    await cargarDatosHistoricos();
    setLoading(false);
    setActiveWizardTab('ventas');
    
    const msgs = [];
    if (countAdmitidos > 0) {
      msgs.push({ text: Se procesaron y admitieron  documentos exitosamente., type: 'success' });
    }
    if (allOmitidos.length > 0) {
      msgs.push({ text: Se omitieron o rechazaron  archivos por inconsistencias. Revisa la pestaña de archivos rechazados para ver el detalle., type: 'warning' });
    }
    if (msgs.length > 0) {
      enqueueMessages(msgs);
    }
  };'''

new_procesar = '''  const handleProcesar = async (tipo, endpoint) => {
    if (!archivos[tipo] || archivos[tipo].length === 0) {
      enqueueMessages([{ text: "Por favor selecciona una carpeta con archivos JSON.", type: 'warning' }]);
      return;
    }

    setLoading(true);
    const formData = new FormData();
    archivos[tipo].forEach(file => {
      formData.append('files', file);
    });
    formData.append('mes', mes);
    formData.append('anio', anio);
    formData.append('usuario_id', user?.id || 1);
    
    try {
      const resp = await axios.post(${API_URL}/api/v1, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      await cargarDatosHistoricos();
      
      const omitidos = resp.data.omitidos || [];
      const admitidos = resp.data.resumen?.documentos || 0;
      
      const msgs = [];
      if (admitidos > 0) {
        msgs.push({ text: Se procesaron y admitieron  documentos exitosamente., type: 'success' });
      }
      if (omitidos.length > 0) {
        msgs.push({ text: Se omitieron o rechazaron  archivos por inconsistencias., type: 'warning' });
      }
      if (msgs.length > 0) {
        enqueueMessages(msgs);
      }
    } catch (error) {
      enqueueMessages([{ text: Error al procesar: , type: 'error' }]);
    }
    setLoading(false);
  };'''
code = code.replace(old_procesar, new_procesar)

# 3. Fix next button logic
old_next = '''if(activeWizardTab==='subir_detalle') setActiveWizardTab('ventas');
            else if(activeWizardTab==='ventas') setActiveWizardTab('compras');
            else if(activeWizardTab==='compras') setActiveWizardTab('liquidacion');
            else if(activeWizardTab==='liquidacion') setActiveWizardTab('subir_detalle');'''
new_next = '''if(activeWizardTab==='compras') setActiveWizardTab('ventas_ccf');
            else if(activeWizardTab==='ventas_ccf') setActiveWizardTab('ventas_fcf');
            else if(activeWizardTab==='ventas_fcf') setActiveWizardTab('liquidacion');
            else if(activeWizardTab==='liquidacion') setActiveWizardTab('compras');'''
code = code.replace(old_next, new_next)

# 4. Replace the TabButtons
old_tabs_html = '''<div className="flex min-w-max px-2 max-w-5xl mx-auto">
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
        </div>'''
        
new_tabs_html = '''<div className="flex min-w-max px-2 max-w-5xl mx-auto">
          <TabButton 
            id="compras" 
            label="Compras (Créditos)" 
            badgeCount={resumen ? (resumen.compras?.documentos || 0) : 0}
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>} 
          />
          <TabButton 
            id="ventas_ccf" 
            label="Ventas a Contribuyentes (CCF)" 
            badgeCount={resumen ? (resumen.ventasContribuyentes?.documentos || 0) : 0}
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>} 
          />
          <TabButton 
            id="ventas_fcf" 
            label="Ventas a Consumidor (FCF)" 
            badgeCount={resumen ? (resumen.ventasConsumidor?.documentos || 0) : 0}
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>} 
          />
          <TabButton 
            id="liquidacion" 
            label="Liquidación del Periodo"
            badgeCount={0}
            icon={<svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>} 
          />
        </div>'''
code = code.replace(old_tabs_html, new_tabs_html)

# 5. Replace main views
import re
view_regex = r"<main className=\"flex-1 max-w-7xl w-full mx-auto p-4 md:p-8\">.*?(?=</main>)"
new_views = '''<main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8">
        {activeWizardTab === 'compras' && (
          <div className="animate-in fade-in zoom-in-95 duration-300 space-y-6">
            <div className="bg-white border border-slate-200 rounded shadow-sm p-6">
              <div className="border-b-2 border-orange-400 pb-2 mb-4 flex justify-between items-center">
                <h2 className="text-lg font-bold text-slate-700">Importar Compras (Créditos Fiscales)</h2>
              </div>
              <div className="flex items-center gap-4">
                <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                  <span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de Compras</span>
                  <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
                </label>
                <button 
                  onClick={() => handleProcesar('compras', '/procesar/compras')}
                  disabled={loading || archivos.compras.length === 0}
                  className={px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap }
                >
                  {loading ? 'Procesando...' : Subir y Procesar ()}
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
              <div className="flex items-center gap-4">
                <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                  <span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de CCF Emitidos</span>
                  <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
                </label>
                <button 
                  onClick={() => handleProcesar('ventasContribuyentes', '/procesar/ventas-contribuyentes')}
                  disabled={loading || archivos.ventasContribuyentes.length === 0}
                  className={px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap }
                >
                  {loading ? 'Procesando...' : Subir y Procesar ()}
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
              <div className="flex items-center gap-4">
                <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                  <span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de FCF Emitidos</span>
                  <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
                </label>
                <button 
                  onClick={() => handleProcesar('ventasConsumidor', '/procesar/ventas-consumidor')}
                  disabled={loading || archivos.ventasConsumidor.length === 0}
                  className={px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap }
                >
                  {loading ? 'Procesando...' : Subir y Procesar ()}
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
                <button onClick={handleGuardarLiquidacion} className="absolute -top-5 right-6 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-full shadow-lg text-xs font-bold uppercase tracking-wider flex items-center transition">
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
'''
import re
code = re.sub(r'<main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8">.*?(?=</main>)', new_views, code, flags=re.DOTALL)

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Restructured to Tabs")
