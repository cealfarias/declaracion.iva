"""Regresiones del cálculo aislado del excedente de impuesto F-07."""
from decimal import Decimal

import pytest

from app.core.casillas_f07 import calcular_excedente_impuesto_f07


@pytest.mark.parametrize("casilla_160,casilla_166,casilla_203,esperado_167,esperado_168", [
    ("100.00", "150.00", "0.00", "50.00", "0.00"),
    ("150.00", "100.00", "0.00", "0.00", "50.00"),
    ("100.00", "150.00", "25.00", "25.00", "0.00"),
    ("100.00", "100.00", "0.00", "0.00", "0.00"),
    ("0.00", "0.00", "0.00", "0.00", "0.00"),
    ("0.01", "0.02", "0.00", "0.01", "0.00"),
])
def test_casillas_excedente_y_pago(casilla_160, casilla_166, casilla_203, esperado_167, esperado_168):
    resultado = calcular_excedente_impuesto_f07(
        casilla_160=casilla_160, casilla_166=casilla_166, casilla_203=casilla_203
    )
    assert resultado == {"167": Decimal(esperado_167), "168": Decimal(esperado_168)}


@pytest.mark.parametrize("invalido", [None, -1, "NaN", "Infinity", "1.234", True, "abc"])
def test_importes_invalidos_rechazados(invalido):
    with pytest.raises(ValueError):
        calcular_excedente_impuesto_f07(
            casilla_160="0.00", casilla_166=invalido, casilla_203="0.00"
        )


def test_calculo_no_recibe_ni_arrastra_casilla_155():
    assert "155" not in calcular_excedente_impuesto_f07(
        casilla_160="10.00", casilla_166="20.00", casilla_203="0.00"
    )
