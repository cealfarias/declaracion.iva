"""Pruebas funcionales de ventas y retenciones, aisladas en SQLite."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.models import DteVenta, DteVentaContribuyente, DteRetencion
from app.routers.ventas_cf import router as cf_router
from app.routers.ventas_contribuyentes import router as ccf_router
from app.routers.retenciones import router as ret_router
from test_compras_autorizacion import escenario, headers


@pytest.fixture
def modulos(escenario):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(cf_router, prefix="/api/v1/ventas-cf")
    app.include_router(ccf_router, prefix="/api/v1/ventas-contribuyentes")
    app.include_router(ret_router, prefix="/api/v1/retenciones")
    app.dependency_overrides[get_db] = lambda: db

    for empresa_id, sufijo in [(ids["e1"], "UNO"), (ids["e2"], "DOS")]:
        db.add(DteVenta(
            empresa_id=empresa_id, periodo_mes="11", periodo_anio="2026",
            fecha_emision="01/11/2026", numero_resolucion="N/A",
            serie_documento="N/A", numero_control_del="N/A", numero_control_al="N/A",
            codigo_generacion=f"CF-{sufijo}", sello_recepcion="SELLO",
            ventas_gravadas=113.0, total_ventas=113.0, raw_json={}
        ))
        db.add(DteVentaContribuyente(
            empresa_id=empresa_id, periodo_mes="11", periodo_anio="2026",
            fecha_emision="01/11/2026", numero_resolucion="RES",
            serie_documento="SELLO", numero_documento=f"CCF-{sufijo}",
            nombre_cliente="Cliente ficticio", ventas_gravadas=100.0,
            debito_fiscal=13.0, total_ventas=113.0, raw_json={}
        ))
        db.add(DteRetencion(
            empresa_id=empresa_id, periodo_mes="11", periodo_anio="2026",
            fecha_emision="01/11/2026", numero_documento=f"RET-{sufijo}",
            monto_sujeto=100.0, monto_retencion=1.0, raw_json={}
        ))
    db.commit()
    with TestClient(app) as client:
        yield client, db, ids


@pytest.mark.parametrize("prefix,endpoint,identificador", [
    ("/api/v1/ventas-cf", "list", "CF-"),
    ("/api/v1/ventas-contribuyentes", "list", "CCF-"),
    ("/api/v1/retenciones", "", "RET-"),
])
def test_listados_aislados(modulos, prefix, endpoint, identificador):
    client, _, ids = modulos
    path = f"{prefix}/{endpoint + '/' if endpoint else ''}{ids['e1']}"
    r = client.get(path, params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1, r.text
    r = client.get(path.replace(str(ids["e1"]), str(ids["e2"])),
                   params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
    assert r.status_code == 403, r.text


@pytest.mark.parametrize("prefix,endpoint,propio,ajeno", [
    ("/api/v1/ventas-cf", "export_csv", "CF-UNO", "CF-DOS"),
    ("/api/v1/ventas-contribuyentes", "export_csv", "CCF-UNO", "CCF-DOS"),
    ("/api/v1/retenciones", "exportar-csv", "RET-UNO", "RET-DOS"),
])
def test_csv_no_filtra_datos_ajenos(modulos, prefix, endpoint, propio, ajeno):
    client, _, ids = modulos
    path = f"{prefix}/{endpoint}/{ids['e1']}"
    r = client.get(path, params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
    assert r.status_code == 200, r.text
    assert propio in r.text
    assert ajeno not in r.text
    r = client.get(f"{prefix}/{endpoint}/{ids['e2']}",
                   params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
    assert r.status_code == 403, r.text


def test_actualizar_venta_contribuyente_propia(modulos):
    client, db, ids = modulos
    registro = db.query(DteVentaContribuyente).filter_by(empresa_id=ids["e1"]).one()
    r = client.put(f"/api/v1/ventas-contribuyentes/update_operacion/{registro.id}",
        params={"tipo_operacion": "2", "tipo_ingreso": "3"}, headers=headers(ids["u1"]))
    assert r.status_code == 200, r.text
    db.refresh(registro)
    assert (registro.tipo_operacion, registro.tipo_ingreso) == ("2", "3")


def test_actualizar_venta_contribuyente_ajena_rechazado(modulos):
    client, db, ids = modulos
    registro = db.query(DteVentaContribuyente).filter_by(empresa_id=ids["e2"]).one()
    r = client.put(f"/api/v1/ventas-contribuyentes/update_operacion/{registro.id}",
        params={"tipo_operacion": "2", "tipo_ingreso": "3"}, headers=headers(ids["u1"]))
    assert r.status_code == 403, r.text
    db.refresh(registro)
    assert registro.tipo_operacion != "2"


def test_limpiar_retenciones_propia(modulos):
    client, db, ids = modulos
    r = client.delete(f"/api/v1/retenciones/{ids['e1']}",
        params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
    assert r.status_code == 200, r.text
    assert db.query(DteRetencion).filter_by(empresa_id=ids["e1"]).count() == 0
    assert db.query(DteRetencion).filter_by(empresa_id=ids["e2"]).count() == 1


def test_limpiar_retenciones_ajenas_rechazado(modulos):
    client, db, ids = modulos
    r = client.delete(f"/api/v1/retenciones/{ids['e2']}",
        params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
    assert r.status_code == 403, r.text
    assert db.query(DteRetencion).filter_by(empresa_id=ids["e2"]).count() == 1
