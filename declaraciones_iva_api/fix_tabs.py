import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Advance the tab after upload
old_load = "await cargarDatosHistoricos();\\n    setLoading(false);"
new_load = "await cargarDatosHistoricos();\\n    setLoading(false);\\n    setActiveWizardTab('ventas');"
code = code.replace(old_load, new_load)

# 2. Add badges to the TabButton
tab_button_old = '''  const TabButton = ({ id, icon, label }) => (
    <button 
      onClick={() => setActiveWizardTab(id)}'''

tab_button_new = '''  const TabButton = ({ id, icon, label, badgeCount }) => (
    <button 
      onClick={() => setActiveWizardTab(id)}'''

code = code.replace(tab_button_old, tab_button_new)

icon_old = '''<div className={mb-2 }>
        {icon}
      </div>'''
icon_new = '''<div className={mb-2 relative }>
        {icon}
        {badgeCount > 0 && (
          <span className="absolute -top-2 -right-3 bg-green-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full shadow-sm">
            {badgeCount}
          </span>
        )}
      </div>'''
code = code.replace(icon_old, icon_new)

# 3. Pass badges to the tabs
count_v = "resumen ? ((resumen.ventasContribuyentes?.documentos || 0) + (resumen.ventasConsumidor?.documentos || 0)) : 0"
count_c = "resumen ? (resumen.compras?.documentos || 0) : 0"
count_l = "resumen ? 1 : 0"

code = code.replace(
    '''id="ventas" \n            label="Ventas y Débitos"''',
    f'''id="ventas" \n            label="Ventas y Débitos" \n            badgeCount={{{count_v}}}'''
)
code = code.replace(
    '''id="compras" \n            label="Compras y Créditos"''',
    f'''id="compras" \n            label="Compras y Créditos" \n            badgeCount={{{count_c}}}'''
)
code = code.replace(
    '''id="liquidacion" \n            label="Liquidación del Periodo"''',
    f'''id="liquidacion" \n            label="Liquidación del Periodo"'''
)

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Dashboard tab advances fixed")
