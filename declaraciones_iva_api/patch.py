import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace validation fail append
code = code.replace(
    'omitidos.append({"archivo": file.filename, "motivo": resultado})',
    'omitidos.append({"archivo": file.filename, "motivo": resultado, "contenido": json.dumps(dte_json, indent=2, ensure_ascii=False)})'
)

# Replace duplicado en lote append
code = code.replace(
    'omitidos.append({"archivo": file.filename, "motivo": "Duplicado en lote"})',
    'omitidos.append({"archivo": file.filename, "motivo": "Duplicado en lote", "contenido": json.dumps(dte_json, indent=2, ensure_ascii=False)})'
)
code = code.replace(
    'omitidos.append({"archivo": file.filename, "motivo": "Duplicado en este mismo lote de archivos"})',
    'omitidos.append({"archivo": file.filename, "motivo": "Duplicado en este mismo lote de archivos", "contenido": json.dumps(dte_json, indent=2, ensure_ascii=False)})'
)

# Replace JSON decode fail append
code = code.replace(
    'omitidos.append({"archivo": file.filename, "motivo": "Archivo no es un JSON vlido"})',
    'omitidos.append({"archivo": file.filename, "motivo": "Archivo no es un JSON válido", "contenido": content.decode("utf-8", errors="ignore")})'
)
code = code.replace(
    'omitidos.append({"archivo": file.filename, "motivo": "Archivo no es un JSON válido"})',
    'omitidos.append({"archivo": file.filename, "motivo": "Archivo no es un JSON válido", "contenido": content.decode("utf-8", errors="ignore")})'
)

# Replace structural error append
code = re.sub(
    r'omitidos\.append\(\{"archivo": file\.filename, "motivo": f"Error estructural: \{str\(e\)\}"\}\)',
    r'omitidos.append({"archivo": file.filename, "motivo": f"Error estructural: {str(e)}", "contenido": content.decode("utf-8", errors="ignore")})',
    code
)

# Replace generic Exception append
code = re.sub(
    r'omitidos\.append\(\{"archivo": file\.filename, "motivo": str\(e\)\}\)',
    r'omitidos.append({"archivo": file.filename, "motivo": str(e), "contenido": content.decode("utf-8", errors="ignore")})',
    code
)

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patched procesamiento.py successfully")
