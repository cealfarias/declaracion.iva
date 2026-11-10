"""Pruebas de integridad JSON para Compras y ambos libros de Ventas.

Usa SQLite en memoria; no modifica PostgreSQL.
"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.models import DteCompra, DteVenta, DteVentaContribuyente
from app.routers.compras import router as compras_router
from app.routers.ventas_cf import router as cf_router
from app.routers.ventas_contribuyentes import router as ccf_router
from test_compras_autorizacion import escenario, headers


MODULOS = [
    ("/api/v1/compras", DteCompra, "03", "receptor"),
    ("/api/v1/ventas-cf", DteVenta, "01", "emisor"),
    ("/api/v1/ventas-contribuyentes", DteVentaContribuyente, "03", "emisor"),
]


@pytest.fixture
def cliente_json(escenario):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(compras_router, prefix="/api/v1/compras")
    app.include_router(cf_router, prefix="/api/v1/ventas-cf")
    app.include_router(ccf_router, prefix="/api/v1/ventas-contribuyentes")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client, db, ids


def subir(client, prefix, ids, contenido):
    return client.post(
        f"{prefix}/upload",
        data={"empresa_id": str(ids["e1"]), "periodo_mes": "11",
              "periodo_anio": "2026"},
        files=[("files", ("documento.json", contenido, "application/json"))],
        headers=headers(ids["u1"]),
    )


def documento(tipo, titular, nit, fecha="2026-11-01"):
    datos = {
        "identificacion": {
            "tipoDte": tipo, "codigoGeneracion": "TEST-JSON-001",
            "fecEmi": fecha, "numeroControl": "DTE-PRUEBA",
        },
        "emisor": {"nit": "TEST-PROVEEDOR", "nrc": "TEST-PROVEEDOR"},
        "receptor": {"nit": "TEST-CLIENTE", "nrc": "TEST-CLIENTE"},
        "resumen": {"totalPagar": 113.0, "totalGravada": 100.0,
                    "totalExenta": 0.0, "totalNoSuj": 0.0},
        "selloRecibido": "SELLO-PRUEBA",
    }
    datos[titular] = {"nit": nit, "nrc": nit}
    return json.dumps(datos).encode("utf-8")


@pytest.mark.parametrize("prefix,modelo,tipo,titular", MODULOS)
def test_json_malformado_no_guarda_documentos(cliente_json, prefix, modelo, tipo, titular):
    client, db, ids = cliente_json
    r = subir(client, prefix, ids, b'{"identificacion":')
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0, r.text
    assert r.json()["errores"], r.text
    assert db.query(modelo).count() == 0


@pytest.mark.parametrize("prefix,modelo,tipo,titular", MODULOS)
def test_nit_de_otra_empresa_no_guarda_documentos(cliente_json, prefix, modelo, tipo, titular):
    client, db, ids = cliente_json
    r = subir(client, prefix, ids, documento(tipo, titular, "TEST-DOS"))
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0, r.text
    assert db.query(modelo).count() == 0


@pytest.mark.parametrize("prefix,modelo,tipo,titular", MODULOS)
def test_fecha_futura_no_guarda_documentos(cliente_json, prefix, modelo, tipo, titular):
    client, db, ids = cliente_json
    r = subir(client, prefix, ids, documento(tipo, titular, "TEST-UNO", "2026-12-01"))
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0, r.text
    assert db.query(modelo).count() == 0


@pytest.mark.parametrize("prefix,modelo,tipo,titular", MODULOS)
def test_nit_parcial_no_se_acepta_como_empresa(cliente_json, prefix, modelo, tipo, titular):
    client, db, ids = cliente_json
    # TEST-UNO es el NIT completo; TEST es solo un fragmento.
    r = subir(client, prefix, ids, documento(tipo, titular, "TEST"))
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0, r.text
    assert db.query(modelo).count() == 0


@pytest.mark.parametrize("prefix,modelo,tipo,titular", MODULOS)
def test_nit_con_sufijo_extra_no_se_acepta(cliente_json, prefix, modelo, tipo, titular):
    client, db, ids = cliente_json
    r = subir(client, prefix, ids, documento(tipo, titular, "TEST-UNO-EXTRA"))
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0, r.text
    assert db.query(modelo).count() == 0


@pytest.mark.parametrize("prefix,modelo,tipo,titular", MODULOS)
def test_reimportacion_mismo_dte_no_duplica(cliente_json, prefix, modelo, tipo, titular):
    client, db, ids = cliente_json
    contenido = documento(tipo, titular, "TEST-UNO")
    primero = subir(client, prefix, ids, contenido)
    assert primero.status_code == 200, primero.text
    assert primero.json()["procesados"] == 1, primero.text
    segundo = subir(client, prefix, ids, contenido)
    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["procesados"] == 0, segundo.text
    assert db.query(modelo).filter_by(empresa_id=ids["e1"]).count() == 1


@pytest.mark.parametrize("prefix,modelo,tipo,titular", MODULOS)
def test_codigo_generacion_con_y_sin_guiones_no_duplica(cliente_json, prefix, modelo, tipo, titular):
    client, db, ids = cliente_json
    primero = subir(client, prefix, ids, documento(tipo, titular, "TEST-UNO"))
    assert primero.status_code == 200, primero.text
    assert primero.json()["procesados"] == 1, primero.text
    segundo_dte = json.loads(documento(tipo, titular, "TEST-UNO"))
    segundo_dte["identificacion"]["codigoGeneracion"] = "TESTJSON001"
    segundo = subir(client, prefix, ids, json.dumps(segundo_dte).encode("utf-8"))
    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["procesados"] == 0, segundo.text
    assert db.query(modelo).filter_by(empresa_id=ids["e1"]).count() == 1
