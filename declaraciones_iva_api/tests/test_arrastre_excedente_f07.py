"""Regresión del arrastre 167 -> 164 entre meses consecutivos."""
from decimal import Decimal

import pytest

from app.core.casillas_f07 import preparar_arrastre_excedente_impuesto


@pytest.mark.parametrize("origen,destino", [
    ("2026-01", "2026-02"),
    ("2026-11", "2026-12"),
    ("2026-12", "2027-01"),
])
def test_arrastre_valido(origen, destino):
    assert preparar_arrastre_excedente_impuesto(
        periodo_origen=origen, periodo_destino=destino, casilla_167="45.67"
    ) == {"periodo_destino": destino, "casilla_164": Decimal("45.67")}


@pytest.mark.parametrize("origen,destino", [
    ("2026-01", "2026-01"),
    ("2026-01", "2026-03"),
    ("2026-02", "2026-01"),
    ("2026-13", "2027-01"),
    ("2026-12", "2027-02"),
    ("2026-1", "2026-02"),
])
def test_arrastre_rechaza_periodos_no_consecutivos(origen, destino):
    with pytest.raises(ValueError):
        preparar_arrastre_excedente_impuesto(
            periodo_origen=origen, periodo_destino=destino, casilla_167="45.67"
        )


@pytest.mark.parametrize("valor", ["-1", "1.234", "NaN", None])
def test_arrastre_rechaza_importes_invalidos(valor):
    with pytest.raises(ValueError):
        preparar_arrastre_excedente_impuesto(
            periodo_origen="2026-12", periodo_destino="2027-01", casilla_167=valor
        )
