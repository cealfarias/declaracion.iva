import re

with open('../declaraciones_iva_web/src/pages/SeleccionEmpresa.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add state for editing
code = code.replace("const [loading, setLoading] = useState(true);", "const [loading, setLoading] = useState(true);\n  const [editingId, setEditingId] = useState(null);")

# 2. Modify "NUEVA EMPRESA" button to clear editing state
code = code.replace("onClick={() => setShowModal(true)}", "onClick={() => { setShowModal(true); setEditingId(null); setNewEmpresa({ razon_social: '', nit: '', nrc: '', combustible_50_porciento: false }); }}")

# 3. Add handleEditClick function
handle_edit_func = '''
  const handleEditClick = (e, emp) => {
    e.stopPropagation();
    setEditingId(emp.id);
    setNewEmpresa({
      razon_social: emp.razon_social,
      nit: emp.nit,
      nrc: emp.nrc || '',
      combustible_50_porciento: emp.combustible_50_porciento || false
    });
    setShowModal(true);
  };
'''
code = code.replace("const handleCreate = async (e) => {", handle_edit_func + "\n  const handleCreate = async (e) => {")

# 4. Modify handleCreate to call PUT if editing
handle_create_old = '''      const response = await axios.post(${API_URL}/api/v1/empresas, {
        ...newEmpresa,
        usuario_id: user?.id || 1
      });
      
      const created = { id: response.data.empresa_id, ...newEmpresa };
      setEmpresas([...empresas, created]);'''
handle_create_new = '''      if (editingId) {
        await axios.put(${API_URL}/api/v1/empresas/, newEmpresa);
        setEmpresas(empresas.map(emp => emp.id === editingId ? { ...emp, ...newEmpresa } : emp));
      } else {
        const response = await axios.post(${API_URL}/api/v1/empresas, {
          ...newEmpresa,
          usuario_id: user?.id || 1
        });
        const created = { id: response.data.empresa_id, ...newEmpresa };
        setEmpresas([...empresas, created]);
      }'''
code = code.replace(handle_create_old, handle_create_new)

# 5. Modify Modal Title
code = code.replace(">Crear Nueva Empresa</h2>", ">{editingId ? 'Editar Empresa' : 'Crear Nueva Empresa'}</h2>")

# 6. Add Edit button to company card
edit_btn = '''                <button 
                  onClick={(e) => handleEditClick(e, emp)}
                  className="px-4 py-2 bg-slate-200 text-slate-700 font-bold rounded shadow-sm hover:bg-slate-300 transition"
                >
                  Editar
                </button>
                <button '''
code = code.replace("<button \n                  onClick={() => handleSelect(emp)}", edit_btn + "\n                  onClick={() => handleSelect(emp)}")

with open('../declaraciones_iva_web/src/pages/SeleccionEmpresa.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
