import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix the broken axios post string
broken = "await axios.post(/api/v1/procesar/guardar-remanente, {"
fixed = "await axios.post(`${API_URL}/api/v1/procesar/guardar-remanente`, {"
code = code.replace(broken, fixed)

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Frontend fixed")
