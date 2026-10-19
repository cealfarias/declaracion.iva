import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix consultar_periodo compras
code = re.sub(
    r'(elif d.clasificacion == \'compra\':.*?resultado\["compras"\]\["documentos"\] \+= 1\n\s+)(resultado\["compras"\]\["gravado"\] \+= float\(row\[9\]\) \+ float\(row\[11\]\) \+ float\(row\[12\]\)\n\s+resultado\["compras"\]\["iva"\] \+= float\(row\[13\]\)\n\s+resultado\["compras"\]\["total"\] \+= float\(row\[14\]\))',
    r'\1tipo = d.datos_json.get("identificacion", {}).get("tipoDte", "")\n                factor = -1 if tipo == "05" else 1\n                resultado["compras"]["gravado"] += factor * (float(row[9]) + float(row[11]) + float(row[12]))\n                resultado["compras"]["iva"] += factor * float(row[13])\n                resultado["compras"]["total"] += factor * float(row[14])',
    code,
    flags=re.DOTALL
)

# Fix consultar_periodo ventas
code = re.sub(
    r'(elif d.clasificacion == \'venta\':.*?resultado\["ventasContribuyentes"\]\["documentos"\] \+= 1\n\s+)(resultado\["ventasContribuyentes"\]\["gravado"\] \+= float\(row\[11\]\)\n\s+resultado\["ventasContribuyentes"\]\["iva"\] \+= float\(row\[12\]\)\n\s+resultado\["ventasContribuyentes"\]\["total"\] \+= float\(row\[15\]\))',
    r'\1tipo = d.datos_json.get("identificacion", {}).get("tipoDte", "")\n                factor = -1 if tipo == "05" else 1\n                resultado["ventasContribuyentes"]["gravado"] += factor * float(row[11])\n                resultado["ventasContribuyentes"]["iva"] += factor * float(row[12])\n                resultado["ventasContribuyentes"]["total"] += factor * float(row[15])',
    code,
    flags=re.DOTALL
)

# Fix consultar_periodo ventas consumidor
code = re.sub(
    r'(elif d.clasificacion == \'venta_consumidor\':.*?resultado\["ventasConsumidor"\]\["documentos"\] \+= 1\n\s+)(resultado\["ventasConsumidor"\]\["gravado"\] \+= float\(row\[13\]\)\n\s+resultado\["ventasConsumidor"\]\["total"\] \+= float\(row\[19\]\))',
    r'\1tipo = d.datos_json.get("identificacion", {}).get("tipoDte", "")\n                factor = -1 if tipo == "05" else 1\n                resultado["ventasConsumidor"]["gravado"] += factor * float(row[13])\n                resultado["ventasConsumidor"]["total"] += factor * float(row[19])',
    code,
    flags=re.DOTALL
)

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Consultar_periodo patched.")
