import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace pass with print
code = code.replace(
    'except Exception:\n            pass # ignore corrupt DB entries if any',
    'except Exception as e:\n            import traceback; traceback.print_exc()\n            pass'
)

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

