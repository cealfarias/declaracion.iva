"""Pruebas de autorización para módulos tributarios adicionales.

Usa la fixture SQLite en memoria definida en test_compras_autorizacion.py.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_compras_autorizacion import escenario, headers
from app.core.database import get_db
from app.routers.ventas_cf import router as ventas_cf_router
from app.routers.ventas_contribuyentes import router as contrib_router
from app.routers.retenciones import router as retenciones_router
from app.routers.liquidacion import router as liquidacion_router


@pytest.mark.parametrize("prefix,router,path", [
    ("/api/v1/ventas-cf", ventas_cf_router, "/list/{empresa_id}?mes=11&anio=2026"),
    ("/api/v1/ventas-contribuyentes", contrib_router, "/list/{empresa_id}?mes=11&anio=2026"),
    ("/api/v1/retenciones", retenciones_router, "/{empresa_id}?mes=11&anio=2026"),
    ("/api/v1/liquidacion", liquidacion_router, "/{empresa_id}?mes=11&anio=2026"),
])
def test_aislamiento_entre_empresas(escenario, prefix, router, path):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix=prefix)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        ruta_ajena = prefix + path.format(empresa_id=ids["e2"])
        r = client.get(ruta_ajena, headers=headers(ids["u1"]))
        assert r.status_code == 403, (ruta_ajena, r.status_code, r.text)
        r = client.get(ruta_ajena)
        assert r.status_code in (401, 403), (ruta_ajena, r.status_code, r.text)
