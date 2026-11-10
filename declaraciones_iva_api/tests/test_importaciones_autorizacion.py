"""Autorización de cargas multipart: ninguna empresa ajena debe aceptar archivos."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.models.models import DteCompra, DteVenta, DteVentaContribuyente, DteRetencion
from app.routers.compras import router as compras_router
from app.routers.ventas_cf import router as cf_router
from app.routers.ventas_contribuyentes import router as ccf_router
from app.routers.retenciones import router as ret_router
from test_compras_autorizacion import escenario, headers


@pytest.fixture
def uploads(escenario):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(compras_router, prefix="/api/v1/compras")
    app.include_router(cf_router, prefix="/api/v1/ventas-cf")
    app.include_router(ccf_router, prefix="/api/v1/ventas-contribuyentes")
    app.include_router(ret_router, prefix="/api/v1/retenciones")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client, db, ids


@pytest.mark.parametrize("prefix,modelo", [
    ("/api/v1/compras", DteCompra),
    ("/api/v1/ventas-cf", DteVenta),
    ("/api/v1/ventas-contribuyentes", DteVentaContribuyente),
    ("/api/v1/retenciones", DteRetencion),
])
def test_carga_empresa_ajena_denegada(uploads, prefix, modelo):
    client, db, ids = uploads
    if prefix.endswith("/retenciones"):
        url = f"{prefix}/upload/{ids['e2']}"
        data = {"mes": "11", "anio": "2026"}
    else:
        url = f"{prefix}/upload"
        data = {"empresa_id": str(ids["e2"]), "periodo_mes": "11", "periodo_anio": "2026"}
    r = client.post(url, data=data,
        files=[("files", ("ficticio.json", b"{}", "application/json"))],
        headers=headers(ids["u1"]))
    assert r.status_code == 403, r.text
    assert db.query(modelo).filter_by(empresa_id=ids["e2"]).count() == 0


@pytest.mark.parametrize("prefix", [
    "/api/v1/compras", "/api/v1/ventas-cf",
    "/api/v1/ventas-contribuyentes", "/api/v1/retenciones",
])
def test_carga_sin_sesion_denegada(uploads, prefix):
    client, _, ids = uploads
    if prefix.endswith("/retenciones"):
        url = f"{prefix}/upload/{ids['e1']}"
        data = {"mes": "11", "anio": "2026"}
    else:
        url = f"{prefix}/upload"
        data = {"empresa_id": str(ids["e1"]), "periodo_mes": "11", "periodo_anio": "2026"}
    r = client.post(url, data=data,
        files=[("files", ("ficticio.json", b"{}", "application/json"))])
    assert r.status_code in (401, 403), r.text
