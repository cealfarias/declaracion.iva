import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update the buttons in the tabs
def replace_buttons(tipo_key, label_str):
    pattern = r'<div className="flex items-center gap-4">.*?</div>\s*</div>'
    
    # We find the specific block for each tab
    # Compras
    # Ventas a Contribuyentes
    # Ventas a Consumidor Final
    pass

# A safer regex approach:
compras_old = r'''<div className="flex items-center gap-4">\s*<label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-\[#004b79\] transition cursor-pointer">\s*<span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de Compras</span>\s*<input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange=\{\(e\) => handleFileChange\(e, 'compras'\)\} />\s*</label>\s*<button \s*onClick=\{\(\) => handleProcesar\('compras', '/procesar/compras'\)\}\s*disabled=\{loading \|\| archivos\.compras\.length === 0\}\s*className=\{`px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap \$\{loading \|\| archivos\.compras\.length === 0 \? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-\[#004b79\] hover:bg-\[#00385c\] text-white'\}`\}\s*>\s*\{loading \? 'Procesando\.\.\.' : `Subir y Procesar \(\$\{archivos\.compras \? archivos\.compras\.length : 0\}\)`\}\s*</button>\s*</div>'''

ccf_old = r'''<div className="flex items-center gap-4">\s*<label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-\[#004b79\] transition cursor-pointer">\s*<span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de CCF Emitidos</span>\s*<input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange=\{\(e\) => handleFileChange\(e, 'ventasContribuyentes'\)\} />\s*</label>\s*<button \s*onClick=\{\(\) => handleProcesar\('ventasContribuyentes', '/procesar/ventas-contribuyentes'\)\}\s*disabled=\{loading \|\| archivos\.ventasContribuyentes\.length === 0\}\s*className=\{`px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap \$\{loading \? "bg-slate-300 text-slate-500 cursor-not-allowed" : "bg-\[#004b79\] hover:bg-\[#00385c\] text-white"\}`\}\s*>\s*\{loading \? 'Procesando\.\.\.' : `Subir y Procesar \(\$\{archivos\.ventasContribuyentes \? archivos\.ventasContribuyentes\.length : 0\}\)`\}\s*</button>\s*</div>'''

fcf_old = r'''<div className="flex items-center gap-4">\s*<label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-\[#004b79\] transition cursor-pointer">\s*<span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de FCF Emitidos</span>\s*<input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange=\{\(e\) => handleFileChange\(e, 'ventasConsumidor'\)\} />\s*</label>\s*<button \s*onClick=\{\(\) => handleProcesar\('ventasConsumidor', '/procesar/ventas-consumidor'\)\}\s*disabled=\{loading \|\| archivos\.ventasConsumidor\.length === 0\}\s*className=\{`px-6 py-3 rounded font-bold shadow transition flex items-center whitespace-nowrap \$\{loading \? "bg-slate-300 text-slate-500 cursor-not-allowed" : "bg-\[#004b79\] hover:bg-\[#00385c\] text-white"\}`\}\s*>\s*\{loading \? 'Procesando\.\.\.' : `Subir y Procesar \(\$\{archivos\.ventasConsumidor \? archivos\.ventasConsumidor\.length : 0\}\)`\}\s*</button>\s*</div>'''

def gen_new_btns(tipo, endpoint, label):
    return f'''<div className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                  <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-white text-[#004b79] font-bold rounded border-2 border-[#004b79] hover:bg-slate-50 transition cursor-pointer shadow-sm">
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    <span>Seleccionar Carpeta ({label})</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={{(e) => handleFileChange(e, '{tipo}')}} />
                  </label>
                  <button 
                    onClick={{() => handleProcesar('{tipo}', '{endpoint}')}}
                    disabled={{loading || archivos.{tipo}.length === 0}}
                    className={{`flex-1 px-6 py-3 rounded font-bold shadow transition flex items-center justify-center whitespace-nowrap ${{loading || archivos.{tipo}.length === 0 ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-[#004b79] hover:bg-[#00385c] text-white'}}`}}
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    {{loading ? 'Procesando...' : `Procesar Archivos (${{archivos.{tipo} ? archivos.{tipo}.length : 0}})`}}
                  </button>
                </div>
              </div>'''

code = re.sub(compras_old, gen_new_btns('compras', '/procesar/compras', 'Compras'), code)
code = re.sub(ccf_old, gen_new_btns('ventasContribuyentes', '/procesar/ventas-contribuyentes', 'CCF Emitidos'), code)
code = re.sub(fcf_old, gen_new_btns('ventasConsumidor', '/procesar/ventas-consumidor', 'FCF Emitidos'), code)


# 2. Rewrite renderResumen to include sorting and the new tables
render_resumen_old = r'''const renderResumen = \(tipoKey, titulo = ""\) => \{.*?</div>\s*</div>\s*\);\s*\};'''

render_resumen_new = '''const renderResumen = (tipoKey, titulo = "") => {
    const data = resumen[tipoKey];
    if (!data) return null;
    const activeTab = activeTabs[tipoKey] || 'admitidos';
    
    let registrosSorted = [];
    if (data.registros) {
      registrosSorted = [...data.registros].sort((a, b) => {
        try {
          const [d1, m1, y1] = a[0].split('/');
          const [d2, m2, y2] = b[0].split('/');
          const date1 = new Date(y1, m1 - 1, d1);
          const date2 = new Date(y2, m2 - 1, d2);
          return date1 - date2;
        } catch(e) {
          return 0;
        }
      });
    }

    return (
      <div key={tipoKey} className="bg-white p-6 rounded shadow-sm border border-slate-200 mb-8">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-[#004b79] uppercase text-lg">{titulo || data.filename.replace(/_/g, ' ')}</h3>
          <div className="space-x-3">
            <span className="text-sm px-4 py-1.5 bg-[#004b79] text-white rounded-full font-medium">
              {data.documentos} DTEs Validados
            </span>
            {data.csv && (
              <button 
                onClick={() => descargarCSV(data.csv, data.filename)}
                className="text-sm px-4 py-1.5 bg-green-600 hover:bg-green-700 transition text-white rounded shadow-sm inline-flex items-center font-medium"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                Descargar CSV
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Monto Gravado</p>
            <p className="text-xl font-bold text-[#004b79]">${data.gravado?.toFixed(2)}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Crédito / Débito Fiscal</p>
            <p className="text-xl font-bold text-[#004b79]">${data.iva?.toFixed(2)}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Total General</p>
            <p className="text-xl font-bold text-[#004b79]">${data.total?.toFixed(2)}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center">
            <p className="text-xs text-slate-500 font-bold mb-1 uppercase tracking-wider">Omitidos / Rechazados</p>
            <p className="text-xl font-bold text-red-600">{data.omitidos?.length || 0}</p>
          </div>
        </div>

        <div>
          <div className="flex border-b border-slate-200 mb-4">
            <button
              onClick={() => handleTabChange(tipoKey, 'admitidos')}
              className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'admitidos' ? 'border-[#004b79] text-[#004b79]' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
            >
              Archivos Admitidos ({registrosSorted.length})
            </button>
            <button
              onClick={() => handleTabChange(tipoKey, 'rechazados')}
              className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'rechazados' ? 'border-red-600 text-red-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
            >
              Archivos Rechazados ({data.omitidos?.length || 0})
            </button>
          </div>

          {activeTab === 'admitidos' && registrosSorted.length > 0 && (
            <div className="overflow-x-auto bg-white border border-slate-200 rounded pb-2">
              <table className="w-full text-left text-[10px] whitespace-nowrap min-w-max">
                <thead className="bg-[#004b79] text-white uppercase font-semibold">
                  {tipoKey === 'compras' && (
                    <tr>
                      <th className="px-3 py-2 border-r border-[#00385c]">N°</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Fecha</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Clase</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Tipo</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Núm. Documento</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">NIT/NRC/DUI</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Razón Social del Proveedor</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas Internas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas Import.</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas Internas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas Import.</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Crédito Fiscal</th>
                      <th className="px-3 py-2 text-right">Total Compras</th>
                    </tr>
                  )}
                  {tipoKey === 'ventasContribuyentes' && (
                    <tr>
                      <th className="px-3 py-2 border-r border-[#00385c]">N°</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Fecha</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Clase</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Tipo</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Núm. Documento</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">NIT/NRC</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Razón Social del Cliente</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Exentas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas No Sujetas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Gravadas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Débito Fiscal</th>
                      <th className="px-3 py-2 text-right">Total Ventas</th>
                    </tr>
                  )}
                  {tipoKey === 'ventasConsumidor' && (
                    <tr>
                      <th className="px-3 py-2 border-r border-[#00385c]">N°</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Fecha</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Clase</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Tipo</th>
                      <th className="px-3 py-2 border-r border-[#00385c]">Núm. Documento</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Exentas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas No Sujetas</th>
                      <th className="px-3 py-2 border-r border-[#00385c] text-right">Ventas Gravadas</th>
                      <th className="px-3 py-2 text-right">Total Ventas</th>
                    </tr>
                  )}
                </thead>
                <tbody className="text-slate-700 divide-y divide-slate-100 font-mono">
                  {registrosSorted.map((reg, idx) => {
                    if (tipoKey === 'compras') {
                      const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; const doc = reg[3];
                      const nrc = reg[4] || reg[15]; const nombre = reg[5]; 
                      const exInt = (parseFloat(reg[6]||0) + parseFloat(reg[8]||0)).toFixed(2);
                      const exImp = parseFloat(reg[7]||0).toFixed(2);
                      const grInt = (parseFloat(reg[9]||0) + parseFloat(reg[11]||0) + parseFloat(reg[12]||0)).toFixed(2);
                      const grImp = parseFloat(reg[10]||0).toFixed(2);
                      const iva = reg[13]; const total = reg[14];
                      return (
                        <tr key={idx} className="hover:bg-blue-50 transition-colors">
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{nrc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 truncate max-w-[200px]" title={nombre}>{nombre}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{exInt}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{exImp}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{grInt}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{grImp}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right text-blue-700 font-bold">{iva}</td>
                          <td className="px-3 py-1.5 text-right font-bold text-slate-800">{total}</td>
                        </tr>
                      );
                    } else if (tipoKey === 'ventasContribuyentes') {
                      const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; 
                      const doc = reg[5] || reg[7]; const nrc = reg[7]; const nombre = reg[8];
                      const exe = reg[9]; const nosuj = reg[10]; const grav = reg[11];
                      const iva = reg[12]; const total = reg[15];
                      return (
                        <tr key={idx} className="hover:bg-blue-50 transition-colors">
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{nrc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 truncate max-w-[200px]" title={nombre}>{nombre}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{exe}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{nosuj}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{grav}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right text-red-700 font-bold">{iva}</td>
                          <td className="px-3 py-1.5 text-right font-bold text-slate-800">{total}</td>
                        </tr>
                      );
                    } else if (tipoKey === 'ventasConsumidor') {
                      const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; 
                      const doc = reg[8]; const exe = reg[10]; const nosuj = reg[12]; 
                      const grav = reg[13]; const total = reg[19];
                      return (
                        <tr key={idx} className="hover:bg-blue-50 transition-colors">
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{exe}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{nosuj}</td>
                          <td className="px-3 py-1.5 border-r border-slate-200 text-right">{grav}</td>
                          <td className="px-3 py-1.5 text-right font-bold text-slate-800">{total}</td>
                        </tr>
                      );
                    }
                  })}
                </tbody>
              </table>
            </div>
          )}
          {activeTab === 'admitidos' && (!registrosSorted || registrosSorted.length === 0) && (
            <p className="text-center text-slate-500 py-4">No hay archivos admitidos.</p>
          )}

          {activeTab === 'rechazados' && data.omitidos && data.omitidos.length > 0 && (
            <div className="flex flex-col md:flex-row gap-4">
              <div className="w-full md:w-1/3 border border-red-200 rounded bg-white overflow-hidden flex flex-col h-[500px] shadow-inner">
                <div className="bg-red-600 text-white px-3 py-2 text-xs font-semibold uppercase sticky top-0">Archivos y Motivos</div>
                <div className="overflow-y-auto flex-1 divide-y divide-red-100 bg-red-50/30">
                  {data.omitidos.map((omi, idx) => (
                    <div 
                      key={idx} 
                      onClick={() => setSelectedJson(omi.contenido || '{"error": "Contenido JSON no disponible"}')}
                      className="p-3 hover:bg-red-100 cursor-pointer transition border-l-4 border-transparent hover:border-red-500"
                    >
                      <p className="font-mono text-red-700 text-[10px] font-bold mb-1 break-all leading-tight">{omi.archivo}</p>
                      <p className="text-xs text-slate-700 leading-snug">{omi.motivo}</p>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="w-full md:w-2/3 border border-slate-700 rounded bg-[#1e1e1e] overflow-hidden flex flex-col h-[500px] shadow-lg">
                <div className="bg-[#2d2d2d] text-slate-300 px-3 py-2 text-xs font-semibold uppercase flex justify-between items-center border-b border-black">
                  <span className="flex items-center"><svg className="w-4 h-4 mr-1 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg> Inconsistencia JSON</span>
                  {selectedJson && (
                    <button className="text-blue-400 hover:text-blue-300 transition" onClick={() => navigator.clipboard.writeText(selectedJson)}>Copiar</button>
                  )}
                </div>
                <div className="overflow-y-auto flex-1 p-4 text-[11px] leading-relaxed font-mono text-[#d4d4d4]">
                  {selectedJson ? (
                    <pre className="whitespace-pre-wrap break-all">{selectedJson}</pre>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3">
                      <p className="italic text-center">Selecciona un archivo en la izquierda para ver su contenido</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          {activeTab === 'rechazados' && (!data.omitidos || data.omitidos.length === 0) && (
            <p className="text-center text-slate-500 py-4">No hay archivos rechazados.</p>
          )}
        </div>
      </div>
    );
  };'''

code = re.sub(render_resumen_old, render_resumen_new, code, flags=re.DOTALL)

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Dashboard Updated.")
