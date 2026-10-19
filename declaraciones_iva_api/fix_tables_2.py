import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add fmt function at the top of Dashboard
fmt_func = '''
  const fmt = (val) => {
    const num = parseFloat(val);
    return isNaN(num) ? '0.00' : num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
'''
if 'const fmt =' not in code:
    code = code.replace('  const { say } = useAssistant();', '  const { say } = useAssistant();\n' + fmt_func)

# Replace the thead for compras
thead_compras_old = '''                    {tipoKey === 'compras' && (
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
                    )}'''
thead_compras_new = '''                    {tipoKey === 'compras' && (
                      <tr>
                        <th className="px-3 py-2 border-r border-[#00385c]">N°</th>
                        <th className="px-3 py-2 border-r border-[#00385c]">Fecha</th>
                        <th className="px-3 py-2 border-r border-[#00385c]">Clase</th>
                        <th className="px-3 py-2 border-r border-[#00385c]">Tipo</th>
                        <th className="px-3 py-2 border-r border-[#00385c]">Núm. Documento</th>
                        <th className="px-3 py-2 border-r border-[#00385c]">NIT/NRC/DUI</th>
                        <th className="px-3 py-2 border-r border-[#00385c]">Razón Social del Proveedor</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas (G)</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas (H)</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Exentas (I)</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (J)</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (K)</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (L)</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Gravadas (M)</th>
                        <th className="px-3 py-2 border-r border-[#00385c] text-right">Crédito Fiscal (N)</th>
                        <th className="px-3 py-2 text-right">Total (O)</th>
                      </tr>
                    )}'''
code = code.replace(thead_compras_old, thead_compras_new)

# Replace tbody mapping for compras
tbody_compras_old = '''                        const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; const doc = reg[3];
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
                        );'''
tbody_compras_new = '''                        const fecha = reg[0]; const clase = reg[1]; const tipo = reg[2]; const doc = reg[3];
                        const nrc = reg[4] || reg[15]; const nombre = reg[5]; 
                        return (
                          <tr key={idx} className="hover:bg-blue-50 transition-colors">
                            <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200">{nrc}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 truncate max-w-[200px]" title={nombre}>{nombre}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[6])}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[7])}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[8])}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[9])}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[10])}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[11])}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(reg[12])}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono text-blue-700 font-bold">{fmt(reg[13])}</td>
                            <td className="px-3 py-1.5 text-right font-mono font-bold text-slate-800">{fmt(reg[14])}</td>
                          </tr>
                        );'''
code = code.replace(tbody_compras_old, tbody_compras_new)

# Format Ventas CCF
tbody_ccf_old = '''                        const exe = reg[9]; const nosuj = reg[10]; const grav = reg[11];
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
                        );'''
tbody_ccf_new = '''                        const exe = reg[9]; const nosuj = reg[10]; const grav = reg[11];
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
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(exe)}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(nosuj)}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(grav)}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono text-red-700 font-bold">{fmt(iva)}</td>
                            <td className="px-3 py-1.5 text-right font-mono font-bold text-slate-800">{fmt(total)}</td>
                          </tr>
                        );'''
code = code.replace(tbody_ccf_old, tbody_ccf_new)

# Format Ventas Consumidor
tbody_fcf_old = '''                        const doc = reg[8]; const exe = reg[10]; const nosuj = reg[12]; 
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
                        );'''
tbody_fcf_new = '''                        const doc = reg[8]; const exe = reg[10]; const nosuj = reg[12]; 
                        const grav = reg[13]; const total = reg[19];
                        return (
                          <tr key={idx} className="hover:bg-blue-50 transition-colors">
                            <td className="px-3 py-1.5 border-r border-slate-200 text-center text-slate-500">{idx+1}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200">{fecha}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-center">{clase}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-center">{tipo}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200">{doc}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(exe)}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(nosuj)}</td>
                            <td className="px-3 py-1.5 border-r border-slate-200 text-right font-mono">{fmt(grav)}</td>
                            <td className="px-3 py-1.5 text-right font-mono font-bold text-slate-800">{fmt(total)}</td>
                          </tr>
                        );'''
code = code.replace(tbody_fcf_old, tbody_fcf_new)

# Avatar saying "se cargaron los json precargados del mes" when data is loaded automatically
# We can do this by adding a parameter to cargarDatosHistoricos or doing it on mount
cargar_old = '''  const cargarDatosHistoricos = async () => {
    try {
      const resp = await axios.get(${API_URL}/api/v1/procesar/consultar, {
        params: { mes, anio, usuario_id: user?.id || 1 }
      });
      if (resp.data.data === null) {
        setResumen(null);
      } else {
        setResumen(resp.data.data);
      }
    } catch (error) {
      console.error("Error al cargar datos del periodo:", error);
    }
  };'''
cargar_new = '''  const cargarDatosHistoricos = async (isAutoLoad = false) => {
    try {
      const resp = await axios.get(${API_URL}/api/v1/procesar/consultar, {
        params: { mes, anio, usuario_id: user?.id || 1 }
      });
      if (resp.data.data === null) {
        setResumen(null);
      } else {
        setResumen(resp.data.data);
        if (isAutoLoad) {
          enqueueMessages([{ text: "Se cargaron los libros precargados del mes desde la base de datos.", type: "success" }]);
        }
      }
    } catch (error) {
      console.error("Error al cargar datos del periodo:", error);
    }
  };'''
code = code.replace(cargar_old, cargar_new)
code = code.replace('useEffect(() => {\n    cargarDatosHistoricos();\n  }, [mes, anio]);', 'useEffect(() => {\n    cargarDatosHistoricos(true);\n  }, [mes, anio]);')

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

