"""Pruebas aritméticas de ajustes de liquidación con datos ficticios.

Estas pruebas verifican el comportamiento del código, no certifican
el tratamiento legal de los saldos en el formulario F-07.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.models import Liquidacion
from app.routers.liquidacion import router as liquidacion_router
from test_compras_autorizacion import escenario, headers
from test_liquidacion_aritmetica import venta_ccf


def consultar(escenario, ajustes, debito=100.0):
    _, db, ids = escenario
    if debito:
        db.add(venta_ccf(ids["e1"], "CCF-AJUSTES", round(debito / 0.13, 2), debito))
    db.add(Liquidacion(empresa_id=ids["e1"], mes="11", anio="2026", **ajustes))
    db.commit()
    app = FastAPI()
    app.include_router(liquidacion_router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        respuesta = client.get(
            f"/api/v1/liquidacion/{ids['e1']}",
            params={"mes": "11", "anio": "2026"},
            headers=headers(ids["u1"]),
        )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_retenciones_y_percepciones_recibidas_disminuyen_impuesto(escenario):
    r = consultar(escenario, {
        "retenciones_recibidas": 15.0,
        "percepciones_recibidas": 10.0,
        "anticipo_cuenta_2": 5.0,
    })
    liq = r["liquidacion"]
    assert liq["impuesto_determinado"] == 100.0
    assert liq["total_deducciones"] == 30.0
    assert liq["deducciones_aplicadas"] == 30.0
    assert liq["impuesto_propio"] == 70.0
    assert liq["impuesto_a_pagar"] == 70.0


def test_remanente_previo_se_aplica_antes_de_ajustes(escenario):
    r = consultar(escenario, {
        "remanente_anterior": 40.0,
        "retenciones_recibidas": 15.0,
        "percepciones_recibidas": 5.0,
    })
    liq = r["liquidacion"]
    assert liq["remanente_aplicado"] == 40.0
    assert liq["total_deducciones"] == 20.0
    assert liq["impuesto_propio"] == 40.0
    assert liq["impuesto_a_pagar"] == 40.0


def test_retenciones_y_percepciones_efectuadas_se_suman_al_pago(escenario):
    r = consultar(escenario, {
        "retenciones_efectuadas": 12.0,
        "percepciones_efectuadas": 8.0,
    })
    liq = r["liquidacion"]
    assert liq["total_terceros"] == 20.0
    assert liq["impuesto_propio"] == 100.0
    assert liq["impuesto_a_pagar"] == 120.0


def test_deducciones_mayores_que_impuesto_no_generan_pago_negativo(escenario):
    r = consultar(escenario, {
        "retenciones_recibidas": 80.0,
        "percepciones_recibidas": 50.0,
        "retenciones_efectuadas": 7.0,
    })
    liq = r["liquidacion"]
    assert liq["deducciones_aplicadas"] == 100.0
    assert liq["deducciones_sobrantes"] == 30.0
    assert liq["impuesto_propio"] == 0.0
    assert liq["impuesto_a_pagar"] == 7.0
