import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update useAuth to include activeEmpresa
code = code.replace('const { user, logout } = useAuth();', 'const { user, logout, activeEmpresa } = useAuth();')

# 2. Update params for backend endpoints
code = code.replace('usuario_id: user?.id || 1', 'empresa_id: activeEmpresa?.id || 1')

# 3. Update the avatar message to include month name
meses_list = "[{ id: 1, nombre: 'Enero' }, { id: 2, nombre: 'Febrero' }, { id: 3, nombre: 'Marzo' },\n    { id: 4, nombre: 'Abril' }, { id: 5, nombre: 'Mayo' }, { id: 6, nombre: 'Junio' },\n    { id: 7, nombre: 'Julio' }, { id: 8, nombre: 'Agosto' }, { id: 9, nombre: 'Septiembre' },\n    { id: 10, nombre: 'Octubre' }, { id: 11, nombre: 'Noviembre' }, { id: 12, nombre: 'Diciembre' }]"
avatar_msg_old = '''        if (isAutoLoad) {
          enqueueMessages([{ text: "Se cargaron los libros precargados del mes desde la base de datos.", type: "success" }]);
        }'''
avatar_msg_new = '''        if (isAutoLoad) {
          const nombreMes = meses.find(m => m.id === mes)?.nombre || '';
          enqueueMessages([{ text: Se cargaron los libros precargados del mes  desde la base de datos., type: "success" }]);
        }'''
code = code.replace(avatar_msg_old, avatar_msg_new)

# 4. Header changes (Company info & Change company button)
header_old = '''      {/* Header */}
      <header className="bg-[#004b79] border-b border-[#00385c] px-8 py-4 flex justify-between items-center text-white shadow-md">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-[#004b79]">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </div>
          <h1 className="text-xl font-bold tracking-tight">Declaraciones de IVA <span className="text-blue-200 text-sm ml-2 font-normal">{APP_VERSION}</span></h1>
        </div>
        <div className="flex items-center space-x-6">
          <span className="text-sm font-medium">Hola, {user?.nombre || 'Usuario'}</span>
          <button onClick={() => { logout(); navigate('/login'); }} className="text-sm text-blue-200 hover:text-white font-medium hover:underline flex items-center transition">
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
            Cerrar Sesión
          </button>
        </div>
      </header>'''

header_new = '''      {/* Header */}
      <header className="bg-[#004b79] border-b border-[#00385c] px-8 py-4 flex flex-col md:flex-row justify-between items-center text-white shadow-md gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-[#004b79] shrink-0">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight flex items-center">
              Declaraciones de IVA <span className="text-blue-200 text-sm ml-2 font-normal hidden sm:inline">{APP_VERSION}</span>
            </h1>
            {activeEmpresa && (
              <div className="text-xs text-blue-100 flex items-center space-x-2 mt-0.5 font-mono">
                <span className="font-semibold text-white">{activeEmpresa.razon_social}</span>
                <span className="text-blue-300">|</span>
                <span>NIT: {activeEmpresa.nit}</span>
                <span className="text-blue-300">|</span>
                <span>NRC: {activeEmpresa.nrc}</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-4 md:space-x-6">
          <span className="text-sm font-medium hidden sm:inline">Hola, {user?.nombre || 'Usuario'}</span>
          <button onClick={() => navigate('/empresas')} className="text-sm text-white bg-[#00385c] hover:bg-[#002b4a] px-3 py-1.5 rounded font-medium flex items-center transition border border-[#004b79]">
            <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
            Cambiar Empresa
          </button>
          <button onClick={() => { logout(); navigate('/login'); }} className="text-sm text-blue-200 hover:text-white font-medium hover:underline flex items-center transition">
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
            Salir
          </button>
        </div>
      </header>'''

code = code.replace(header_old, header_new)

# 5. Replace Year selector
year_old = '''          <select value={anio} onChange={(e) => setAnio(parseInt(e.target.value))} className="border border-slate-300 rounded px-4 py-2 font-medium bg-white focus:ring-2 focus:ring-[#004b79] focus:border-[#004b79] outline-none">
            <option value={2026}>2026</option>
            <option value={2025}>2025</option>
            <option value={2024}>2024</option>
          </select>'''
year_new = '''          <input 
            type="number" 
            value={anio} 
            onChange={(e) => setAnio(parseInt(e.target.value) || new Date().getFullYear())} 
            className="border border-slate-300 rounded px-4 py-2 w-24 font-medium bg-white focus:ring-2 focus:ring-[#004b79] focus:border-[#004b79] outline-none"
            min="2000"
            max="2100"
          />'''
code = code.replace(year_old, year_new)

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
