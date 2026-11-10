"""Contrato HTTP de la casilla 164 sin base de datos real."""
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.authorization import autorizar_empresa_tributaria
from app.core.database import get_db
from app.models.models import Liquidacion
from app.routers.liquidacion import router


class ConsultaFalsa:
    def __init__(self, db):
        self.db = db

    def filter(self, *_args):
        return self

    def first(self):
        return self.db.existing


class DBFalsa:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.commits = 0

    def query(self, *_args):
        return ConsultaFalsa(self)

    def add(self, obj):
        self.added.append(obj)

    def execute(self, _statement):
        # El test de no sobrescritura modela una actualización condicional
        # que no modifica filas cuando el saldo ya está registrado.
        class Resultado:
            rowcount = 0
        return Resultado()

    def rollback(self):
        pass

    def commit(self):
        self.commits += 1


def cliente(db):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[autorizar_empresa_tributaria] = lambda: None
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


RUTA = "/api/v1/liquidacion/7/excedente-impuesto-anterior?mes=01&anio=2027"


@pytest.mark.parametrize("payload", [
    {"importe": "-1"}, {"importe": "0.001"}, {"importe": "NaN"},
    {"importe": "Infinity"}, {"importe": None}, {"importe": True},
    {"importe": "abc"}, {},
])
def test_164_rechaza_importes_invalidos_antes_de_db(payload):
    db = DBFalsa()
    respuesta = cliente(db).post(RUTA, json=payload)
    assert respuesta.status_code == 422
    assert db.commits == 0


def test_164_rechaza_periodo_invalido_antes_de_db():
    db = DBFalsa()
    respuesta = cliente(db).post(
        "/api/v1/liquidacion/7/excedente-impuesto-anterior?mes=13&anio=2027",
        json={"importe": "5.00"},
    )
    assert respuesta.status_code == 422
    assert db.commits == 0


def test_164_registra_importe_sin_modificar_otros_campos():
    db = DBFalsa()
    respuesta = cliente(db).post(RUTA, json={"importe": "45.67"})
    assert respuesta.status_code == 409
    assert "sin respaldo" in respuesta.json()["detail"]
    assert len(db.added) == 0
    assert db.commits == 0


@pytest.mark.parametrize("saldo", [Decimal("0.00"), Decimal("10.00")])
def test_164_no_sobrescribe_saldo_ya_registrado(saldo):
    existente = Liquidacion(empresa_id=7, mes="01", anio="2027")
    existente.excedente_impuesto_anterior = saldo
    db = DBFalsa(existing=existente)
    respuesta = cliente(db).post(RUTA, json={"importe": "45.67"})
    assert respuesta.status_code == 409
    assert existente.excedente_impuesto_anterior == saldo
    assert db.commits == 0
