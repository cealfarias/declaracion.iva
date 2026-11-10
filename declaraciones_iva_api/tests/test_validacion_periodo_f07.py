"""Validación de períodos fiscales en escrituras F-07."""
import pytest
from fastapi import HTTPException

from app.routers.liquidacion import validar_periodo_fiscal


@pytest.mark.parametrize("mes,anio", [
    ("01", "2026"), ("02", "2026"), ("12", "2025"), ("11", "1999"),
])
def test_periodos_validos(mes, anio):
    assert validar_periodo_fiscal(mes, anio) is None


@pytest.mark.parametrize("mes,anio", [
    ("00", "2026"), ("13", "2026"), ("1", "2026"),
    ("02", "26"), ("02", "0000"), ("02", "20a6"),
    ("02", "٢٠٢٦"), ("02", "20260"), ("02", "-026"),
])
def test_periodos_invalidos(mes, anio):
    with pytest.raises(HTTPException) as exc:
        validar_periodo_fiscal(mes, anio)
    assert exc.value.status_code == 422
