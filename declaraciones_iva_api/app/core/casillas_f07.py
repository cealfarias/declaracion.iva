"""Aritmética aislada de casillas F-07 v14.

No infiere la composición normativa de 166 ni de 203. Esos importes deben
provenir de una conciliación explícita antes de usarse en una declaración.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _importe(valor, nombre):
    if isinstance(valor, bool) or valor is None:
        raise ValueError(f"{nombre}: importe requerido.")
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{nombre}: importe inválido.") from exc
    if not numero.is_finite() or numero < 0 or numero.as_tuple().exponent < -2:
        raise ValueError(f"{nombre}: debe ser no negativo y tener máximo dos decimales.")
    return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_excedente_impuesto_f07(*, casilla_160, casilla_166, casilla_203):
    """Devuelve casillas 167 y 168 sin mezclar el crédito fiscal de la 155.

    167 = max(166 - 160 - 203, 0)
    168 = max(160 - 166 + 203, 0)
    """
    impuesto = _importe(casilla_160, "160")
    disponible = _importe(casilla_166, "166")
    ajustes = _importe(casilla_203, "203")
    diferencia = disponible - impuesto - ajustes
    return {
        "167": max(diferencia, Decimal("0.00")),
        "168": max(-diferencia, Decimal("0.00")),
    }
