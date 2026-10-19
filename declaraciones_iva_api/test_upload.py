import requests
import json
import io

url = "http://localhost:8000/api/v1/compras/upload"

# Crear un JSON simulado
dummy_dte = {
    "identificacion": {
        "tipoDte": "03",
        "fecEmi": "2026-08-26",
        "codigoGeneracion": "12345678-ABCD-1234-EFGH-123456789012",
        "selloRecibido": "SELLO-TEST"
    },
    "emisor": {
        "nit": "0614-010190-101-1",
        "nombre": "Proveedor Test S.A."
    },
    "resumen": {
        "tributos": [
            {"codigo": "20", "valor": "13.00"}
        ],
        "totalGravada": "100.00",
        "totalPagar": "113.00"
    }
}

file_content = json.dumps(dummy_dte).encode('utf-8')
file_io = io.BytesIO(file_content)

files = [
    ("files", ("test_dte.json", file_io, "application/json"))
]

data = {
    "empresa_id": 1,
    "periodo_mes": "08",
    "periodo_anio": "2026"
}

response = requests.post(url, data=data, files=files)
print(response.status_code)
print(response.text)
