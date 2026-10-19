import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace utf-8 with utf-8-sig
code = code.replace("content.decode('utf-8')", "content.decode('utf-8-sig')")

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patched utf-8-sig successfully")
