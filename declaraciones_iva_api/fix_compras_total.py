import re

with open('app/core/dte_parser.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace total_compras_neto = g + h + i + j + k + l + m
code = code.replace(
    'total_compras_neto = g + h + i + j + k + l + m',
    'total_compras_neto = float(resumen.get("montoTotalOperacion", 0.0) or 0.0)'
)

with open('app/core/dte_parser.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Fixed total general for compras.")
