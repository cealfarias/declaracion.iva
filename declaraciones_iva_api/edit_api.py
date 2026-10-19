import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace the content = await file.read() / try: dte_json = json.loads(content)
decode_logic = '''
        content = await file.read()
        try:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            dte_json = json.loads(text)
            if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                dte_json = dte_json["dteJson"]
'''

code = code.replace(
    '        content = await file.read()\n        try:\n            dte_json = json.loads(content)',
    decode_logic.strip('\n')
)

# Now suppress the "ya declarado" errors by changing the if not es_valido: logic
code = re.sub(
    r'if not es_valido:\s+omitidos\.append\(\{"archivo": file\.filename, "motivo": resultado, "contenido": json\.dumps\(dte_json, indent=2, ensure_ascii=False\)\}\)\s+continue',
    '''if not es_valido:
                if "ya declarado" not in resultado.lower():
                    omitidos.append({"archivo": file.filename, "motivo": resultado, "contenido": json.dumps(dte_json, indent=2, ensure_ascii=False)})
                continue''',
    code
)

# Now suppress "Duplicado en lote" and "Duplicado en este mismo lote"
code = re.sub(
    r'if codigo_gen in codigos_vistos:\s+omitidos\.append\(\{"archivo": file\.filename, "motivo": "Duplicado en este mismo lote[^}]+\}\)\s+continue',
    '''if codigo_gen in codigos_vistos:
                continue''',
    code
)
code = re.sub(
    r'if resultado in codigos_vistos:\s+omitidos\.append\(\{"archivo": file\.filename, "motivo": "Duplicado[^}]+\}\)\s+continue',
    '''if resultado in codigos_vistos:
                continue''',
    code
)

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied")
