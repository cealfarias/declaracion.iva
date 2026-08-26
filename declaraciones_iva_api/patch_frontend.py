import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add state
code = code.replace(
    "const [selectedJson, setSelectedJson] = useState('');",
    "const [selectedJson, setSelectedJson] = useState('');\n  const [remanenteAnterior, setRemanenteAnterior] = useState(0.0);"
)

# Set remanenteAnterior when data loads
code = code.replace(
    "setResumen(resp.data.data);",
    "setResumen(resp.data.data);\n        setRemanenteAnterior(resp.data.data.remanente_anterior || 0.0);"
)
# Wait, the code actually has:
# setResumen(resp.data);
code = code.replace(
    "setResumen(resp.data);",
    "setResumen(resp.data);\n        if(resp.data.remanente_anterior) setRemanenteAnterior(resp.data.remanente_anterior);"
)

# Compute liquidacion
code = code.replace(
    "const creditoFiscalReal = (resumen?.compras?.iva || 0);",
    "const creditoFiscalReal = (resumen?.compras?.iva || 0) + remanenteAnterior;"
)

# Save function
save_logic = '''
  const handleGuardarLiquidacion = async () => {
    try {
      await axios.post(${API_URL}/api/v1/procesar/guardar-remanente, {
        mes, anio, usuario_id: user?.id || 1, remanente_anterior: parseFloat(remanenteAnterior) || 0.0
      });
      enqueueMessages([{ text: "Liquidación y remanente guardados con éxito.", type: 'success' }]);
    } catch (error) {
      enqueueMessages([{ text: "Error al guardar: " + error.message, type: 'error' }]);
    }
  };
'''
code = code.replace("const TabButton =", save_logic + "\n  const TabButton =")

# Render UI for liquidacion
ui_old = '''<span className="font-bold text-slate-700">Suma de Créditos (IVA Compras)</span>'''
ui_new = '''<div className="flex flex-col">
                        <span className="font-bold text-slate-700 mb-2">Suma de Créditos (IVA Compras)</span>
                        <div className="flex items-center text-xs mt-1 bg-yellow-50 p-2 border border-yellow-200 rounded">
                          <span className="mr-2 font-semibold text-yellow-800">+ Remanente Anterior: $</span>
                          <input type="number" step="0.01" value={remanenteAnterior} onChange={(e) => setRemanenteAnterior(parseFloat(e.target.value) || 0)} className="w-24 p-1 border border-yellow-300 rounded text-right outline-none focus:ring-1 focus:ring-yellow-500 font-mono" />
                        </div>
                      </div>'''
code = code.replace(ui_old, ui_new)

btn_ui = '''
              <div className="border-t-4 border-slate-300 p-6 bg-white">
'''
btn_ui_new = '''
              <div className="border-t-4 border-slate-300 p-6 bg-white relative">
                <button onClick={handleGuardarLiquidacion} className="absolute -top-5 right-6 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-full shadow-lg text-xs font-bold uppercase tracking-wider flex items-center transition">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>
                  Guardar Liquidación
                </button>
'''
code = code.replace(btn_ui, btn_ui_new)

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Frontend patched")
