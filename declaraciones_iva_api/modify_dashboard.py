import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add import
if 'from "@react-oauth/google"' not in code and "from '@react-oauth/google'" not in code:
    code = code.replace("import axios from 'axios';", "import axios from 'axios';\nimport { useGoogleLogin } from '@react-oauth/google';")

# 2. Add useGoogleLogin hook and state
hook_code = '''
  const [loadingGmail, setLoadingGmail] = useState(false);
  const { say, enqueueMessages } = useAssistant();

  const handleGmailImport = useGoogleLogin({
    scope: 'https://www.googleapis.com/auth/gmail.readonly',
    onSuccess: async (tokenResponse) => {
      try {
        setLoadingGmail(true);
        enqueueMessages([{ text: "Buscando DTEs en tu correo, esto puede tomar unos segundos...", type: "info" }]);
        
        let targetTipo = '';
        if (activeWizardTab === 'compras') targetTipo = 'compras';
        else if (activeWizardTab === 'ventas_ccf') targetTipo = 'ventas_ccf';
        else if (activeWizardTab === 'ventas_fcf') targetTipo = 'ventas_consumidor';

        const formData = new FormData();
        formData.append('access_token', tokenResponse.access_token);
        formData.append('tipo_anexo', targetTipo);
        formData.append('mes', mes);
        formData.append('anio', anio);
        formData.append('empresa_id', activeEmpresa?.id || 1);

        const resp = await axios.post(${API_URL}/api/v1/procesar/gmail, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        if (resp.data.documentos === undefined) {
           // Si devolvió el mensaje de que no encontró
           enqueueMessages([{ text: resp.data.message || "No se encontraron adjuntos en Gmail.", type: "warning" }]);
        } else {
           await cargarDatosHistoricos();
           enqueueMessages([{ text: Se extrajeron  documentos de Gmail exitosamente., type: 'success' }]);
        }
      } catch (error) {
        enqueueMessages([{ text: Error al importar de Gmail: , type: 'error' }]);
      } finally {
        setLoadingGmail(false);
      }
    },
    onError: (error) => {
      enqueueMessages([{ text: "Error de autenticación con Google.", type: "error" }]);
    }
  });
'''
code = code.replace("const { say, enqueueMessages } = useAssistant();", hook_code)

# 3. Add Gmail import buttons in the UI for compras
btn_compras = '''                  <div className="flex items-center gap-4">
                    <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-white text-[#004b79] font-bold rounded border-2 border-[#004b79] hover:bg-slate-50 transition cursor-pointer shadow-sm">
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                      Seleccionar Carpeta (Compras)
                      <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'compras')} />
                    </label>
                    <button type="button" 
                      onClick={() => handleProcesar('compras')}
                      disabled={archivos.compras.length === 0 || loading}
                      className={lex-1 flex items-center justify-center px-4 py-3 font-bold rounded shadow-sm transition }
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                      {loading ? 'Procesando...' : Procesar Archivos ()}
                    </button>
                  </div>'''
btn_compras_new = btn_compras + '''
                  <button type="button" 
                    onClick={() => handleGmailImport()}
                    disabled={loadingGmail || loading}
                    className="w-full flex items-center justify-center px-4 py-3 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition disabled:opacity-50"
                  >
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 12.713l-11.985-9.713h23.971l-11.986 9.713zm-12 1.545v-10.258l12 9.728 12-9.728v10.258l-12 9.728-12-9.728z"/>
                    </svg>
                    {loadingGmail ? 'Importando desde Gmail...' : 'Importar Automáticamente desde Gmail'}
                  </button>'''
code = code.replace(btn_compras, btn_compras_new)

# Apply same for Ventas CCF
btn_ccf = '''                <div className="flex items-center gap-4">
                  <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                    <span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de CCF Emitidos</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasContribuyentes')} />
                  </label>
                  <button type="button" 
                    onClick={() => handleProcesar('ventasContribuyentes')}
                    disabled={archivos.ventasContribuyentes.length === 0 || loading}
                    className={px-8 py-3 font-bold rounded shadow-sm transition }
                  >
                    {loading ? 'Procesando...' : Procesar ()}
                  </button>
                </div>'''
btn_ccf_new = btn_ccf + '''
                <button type="button" 
                  onClick={() => handleGmailImport()}
                  disabled={loadingGmail || loading}
                  className="w-full mt-4 flex items-center justify-center px-4 py-3 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition disabled:opacity-50"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12.713l-11.985-9.713h23.971l-11.986 9.713zm-12 1.545v-10.258l12 9.728 12-9.728v10.258l-12 9.728-12-9.728z"/>
                  </svg>
                  {loadingGmail ? 'Importando desde Gmail...' : 'Importar Automáticamente desde Gmail'}
                </button>'''
code = code.replace(btn_ccf, btn_ccf_new)


# Apply same for Ventas Consumidor
btn_fcf = '''                <div className="flex items-center gap-4">
                  <label className="flex-1 relative flex items-center justify-center px-4 py-3 bg-slate-50 text-slate-600 rounded border border-slate-300 border-dashed hover:bg-slate-100 hover:border-[#004b79] transition cursor-pointer">
                    <span className="text-sm font-medium text-center">Haz clic para seleccionar la carpeta de FCF Emitidos</span>
                    <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={(e) => handleFileChange(e, 'ventasConsumidor')} />
                  </label>
                  <button type="button" 
                    onClick={() => handleProcesar('ventasConsumidor')}
                    disabled={archivos.ventasConsumidor.length === 0 || loading}
                    className={px-8 py-3 font-bold rounded shadow-sm transition }
                  >
                    {loading ? 'Procesando...' : Procesar ()}
                  </button>
                </div>'''
btn_fcf_new = btn_fcf + '''
                <button type="button" 
                  onClick={() => handleGmailImport()}
                  disabled={loadingGmail || loading}
                  className="w-full mt-4 flex items-center justify-center px-4 py-3 bg-red-600 text-white font-bold rounded shadow-sm hover:bg-red-700 transition disabled:opacity-50"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12.713l-11.985-9.713h23.971l-11.986 9.713zm-12 1.545v-10.258l12 9.728 12-9.728v10.258l-12 9.728-12-9.728z"/>
                  </svg>
                  {loadingGmail ? 'Importando desde Gmail...' : 'Importar Automáticamente desde Gmail'}
                </button>'''
code = code.replace(btn_fcf, btn_fcf_new)


with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
