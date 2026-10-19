import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('["03", "11", "12", "14"]', '["03", "05", "06", "14"]')
code = code.replace('["03", "11", "12"]', '["03", "05", "06"]')
code = code.replace('["01", "11", "12"]', '["01", "05", "06"]')

# In procesar_compras, we need to adjust the accumulator logic based on tipoDte.
# We will use the 'dte_json' which is available in the loop to check tipoDte.

# Wait, the accumulator is:
# total_gravado += float(row[9]) + float(row[11]) + float(row[12]) # J, L, M
# total_iva += float(row[13]) # N
# total_general += float(row[14]) # O

replace_compras = '''
            tipo = dte_json.get("identificacion", {}).get("tipoDte", "")
            factor = -1 if tipo == "05" else 1
            
            total_docs += 1
            total_gravado += factor * (float(row[9]) + float(row[11]) + float(row[12]))
            total_iva += factor * float(row[13])
            total_general += factor * float(row[14])
'''

code = re.sub(
    r'total_docs \+= 1\s+total_gravado \+= float\(row\[9\]\) \+ float\(row\[11\]\) \+ float\(row\[12\]\).*?\n\s+total_iva \+= float\(row\[13\]\).*?\n\s+total_general \+= float\(row\[14\]\).*?\n',
    replace_compras,
    code,
    flags=re.DOTALL
)

# In procesar_ventas
replace_ventas = '''
            tipo = dte_json.get("identificacion", {}).get("tipoDte", "")
            factor = -1 if tipo == "05" else 1

            total_docs += 1
            total_gravado += factor * float(row[11])
            total_iva += factor * float(row[12])
            total_general += factor * float(row[15])
'''
code = re.sub(
    r'total_docs \+= 1\s+total_gravado \+= float\(row\[11\]\).*?\n\s+total_iva \+= float\(row\[12\]\).*?\n\s+total_general \+= float\(row\[15\]\).*?\n',
    replace_ventas,
    code,
    flags=re.DOTALL
)

# In procesar_ventas_consumidor
replace_ventas_consumidor = '''
            tipo = dte_json.get("identificacion", {}).get("tipoDte", "")
            factor = -1 if tipo == "05" else 1

            total_docs += 1
            total_gravado += factor * float(row[13])
            total_general += factor * float(row[19])
'''
code = re.sub(
    r'total_docs \+= 1\s+total_gravado \+= float\(row\[13\]\).*?\n\s+total_general \+= float\(row\[19\]\).*?\n',
    replace_ventas_consumidor,
    code,
    flags=re.DOTALL
)

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Accumulators patched.")
