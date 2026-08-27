import re

with open('../declaraciones_iva_web/src/pages/SeleccionEmpresa.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update state for newEmpresa
code = code.replace("const [newEmpresa, setNewEmpresa] = useState({ razon_social: '', nit: '', nrc: '' });", "const [newEmpresa, setNewEmpresa] = useState({ razon_social: '', nit: '', nrc: '', actividad_economica: '', combustible_50_porciento: false });")

# 2. Update fetchEmpresas
fetch_old = '''    try {
      // Si tenemos backend real conectado:
      // const response = await axios.get(${API_URL}/api/v1/empresas/usuario/);
      // setEmpresas(response.data);
      
      // Simularemos unas de prueba mientras conectamos el backend 100%
      setEmpresas([
        { id: 1, razon_social: 'Iva Marielos', nit: '0614-123456-101-1', nrc: '123456-7' },
        { id: 2, razon_social: 'Zenia Mendoza', nit: '0614-654321-102-2', nrc: '765432-1' }
      ]);
    } catch (error) {'''

fetch_new = '''    try {
      const response = await axios.get(${API_URL}/api/v1/empresas/usuario/);
      setEmpresas(response.data);
    } catch (error) {'''
code = code.replace(fetch_old, fetch_new)

# 3. Update handleCreate
create_old = '''    try {
      /* 
      const response = await axios.post(${API_URL}/api/v1/empresas, {
        ...newEmpresa,
        usuario_id: user?.id || 1
      });
      */
      
      // Simulación visual por ahora
      const created = { id: Date.now(), ...newEmpresa };
      setEmpresas([...empresas, created]);
      setShowModal(false);
      setNewEmpresa({ razon_social: '', nit: '', nrc: '' });
    } catch (error) {'''

create_new = '''    try {
      await axios.post(${API_URL}/api/v1/empresas, {
        ...newEmpresa,
        usuario_id: user?.id || 1
      });
      
      await fetchEmpresas();
      setShowModal(false);
      setNewEmpresa({ razon_social: '', nit: '', nrc: '', actividad_economica: '', combustible_50_porciento: false });
    } catch (error) {'''
code = code.replace(create_old, create_new)

# 4. Add combustible_50_porciento Checkbox to the modal form
form_nrc = '''                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">NRC</label>
                    <input 
                      type="text" 
                      required
                      value={newEmpresa.nrc}
                      onChange={(e) => setNewEmpresa({...newEmpresa, nrc: e.target.value})}
                      className="w-full border border-slate-300 rounded px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      placeholder="123456-7"
                    />
                  </div>
                </div>'''
form_nrc_new = form_nrc + '''
                <div className="mt-4 flex items-center">
                  <input 
                    id="combustible" 
                    type="checkbox" 
                    checked={newEmpresa.combustible_50_porciento}
                    onChange={(e) => setNewEmpresa({...newEmpresa, combustible_50_porciento: e.target.checked})}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <label htmlFor="combustible" className="ml-2 block text-sm text-slate-700">
                    Aplicar 50% al impuesto de combustible (FOVIAL/COTRANS)
                  </label>
                </div>'''
code = code.replace(form_nrc, form_nrc_new)

with open('../declaraciones_iva_web/src/pages/SeleccionEmpresa.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
