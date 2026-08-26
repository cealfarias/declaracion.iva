import re

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

code = re.sub(r'Subir y Procesar \(\)', r'`Subir y Procesar (${archivos.compras ? archivos.compras.length : 0})`', code)
# wait, for CCF and FCF it's different.
# I'll just change them manually:

# 1. Compras
c = r"`Subir y Procesar (${archivos.compras ? archivos.compras.length : 0})`"
# 2. CCF
vccf = r"`Subir y Procesar (${archivos.ventasContribuyentes ? archivos.ventasContribuyentes.length : 0})`"
# 3. FCF
vfcf = r"`Subir y Procesar (${archivos.ventasConsumidor ? archivos.ventasConsumidor.length : 0})`"

# find all and replace each sequentially
parts = code.split("Subir y Procesar ()")
if len(parts) == 4:
    code = parts[0] + c + parts[1] + vccf + parts[2] + vfcf + parts[3]

with open('../declaraciones_iva_web/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
