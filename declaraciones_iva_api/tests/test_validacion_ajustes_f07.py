"""Validación de importes fiscales antes de escribir ajustes en PostgreSQL."""
import pytest
from pydantic import ValidationError

from app.routers.liquidacion import AjustesLiquidacionRequest


@pytest.mark.parametrize("valor", [-1, "-0.01", "NaN", "Infinity", "12.345", "abc", True])
def test_rechaza_importes_invalidos(valor):
    with pytest.raises(ValidationError):
        AjustesLiquidacionRequest(retenciones_recibidas=valor)


@pytest.mark.parametrize("valor", ["0", "12", "12.3", "12.34", 0, 12.34])
def test_acepta_importes_validos(valor):
    ajuste = AjustesLiquidacionRequest(retenciones_recibidas=valor)
    assert ajuste.retenciones_recibidas >= 0


def test_conserva_ausencia_explicita_para_actualizaciones_parciales():
    ajuste = AjustesLiquidacionRequest(retenciones_recibidas=None)
    assert ajuste.retenciones_recibidas is None
