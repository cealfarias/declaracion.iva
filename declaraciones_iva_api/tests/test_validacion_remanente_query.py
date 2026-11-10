"""Protección del remanente fiscal recibido por query string."""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.routers.liquidacion import validar_remanente_query


@pytest.mark.parametrize("valor", ["0", "0.00", "12", "12.3", "12.34"])
def test_remanente_query_acepta_importes_validos(valor):
    assert validar_remanente_query(valor) == Decimal(valor)


@pytest.mark.parametrize("valor", ["-0.01", "12.345", "NaN", "Infinity", "-Infinity", "abc", ""])
def test_remanente_query_rechaza_importes_invalidos(valor):
    with pytest.raises(HTTPException) as exc:
        validar_remanente_query(valor)
    assert exc.value.status_code == 422
