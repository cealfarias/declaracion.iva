import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace the _validar_dte function calls
code = code.replace("es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas', file.filename, db)", 
                    "es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas_ccf', file.filename, db)", 1)
# The second one is in procesar_ventas_consumidor
code = code.replace("es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas', file.filename, db)", 
                    "es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas_consumidor', file.filename, db)", 1)

# Now inject the type checking logic into _validar_dte
valid_logic = '''
    ident = dte_json.get("identificacion", {})
    tipo_dte = ident.get("tipoDte", "")
    codigo_gen = ident.get("codigoGeneracion", "").replace("-", "").upper()
    fecha_raw = ident.get("fecEmi", "")
    
    if tipo_anexo == 'compras' and tipo_dte not in ["03", "11", "12", "14"]:
        return False, f"Tipo incorrecto para Compras: DTE {tipo_dte} (Se esperan CCF 03, FSE 14, NC/ND)"
    if tipo_anexo == 'ventas_ccf' and tipo_dte not in ["03", "11", "12"]:
        return False, f"Tipo incorrecto para Ventas CCF: DTE {tipo_dte} (Se esperan CCF 03 o NC/ND)"
    if tipo_anexo == 'ventas_consumidor' and tipo_dte not in ["01", "11", "12"]:
        return False, f"Tipo incorrecto para Consumidor: DTE {tipo_dte} (Se esperan Facturas 01 o NC/ND)"
'''

# Find the start of _validar_dte
old_start = '''    ident = dte_json.get("identificacion", {})
    codigo_gen = ident.get("codigoGeneracion", "").replace("-", "").upper()
    fecha_raw = ident.get("fecEmi", "")'''

code = code.replace(old_start, valid_logic.strip())

# Fix the receptor/emisor check because the names 'ventas_ccf' and 'ventas_consumidor' are used instead of just 'ventas'
code = code.replace("if tipo_anexo == 'compras':", "if tipo_anexo == 'compras':") # no-op
code = code.replace("else:\n        emi_nit = str(emisor.get(\"nit\", \"\")).replace(\"-\", \"\")", 
                    "elif tipo_anexo in ['ventas_ccf', 'ventas_consumidor']:\n        emi_nit = str(emisor.get(\"nit\", \"\")).replace(\"-\", \"\")")


with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Logic updated successfully")
