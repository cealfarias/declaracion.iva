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


def preparar_arrastre_excedente_impuesto(*, periodo_origen, periodo_destino, casilla_167):
    """Prepara 167 -> 164 solo entre meses consecutivos, sin escribir en DB.

    Los períodos son cadenas YYYY-MM. No mezcla el remanente de crédito 155.
    """
    from datetime import date

    def leer_periodo(valor):
        if not isinstance(valor, str) or len(valor) != 7 or valor[4] != "-" or not (
            valor[:4].isascii() and valor[:4].isdigit()
            and valor[5:].isascii() and valor[5:].isdigit()
        ):
            raise ValueError("Período inválido; use YYYY-MM.")
        anio, mes = int(valor[:4]), int(valor[5:])
        if anio < 1 or mes < 1 or mes > 12:
            raise ValueError("Período fuera de rango.")
        return date(anio, mes, 1)

    origen = leer_periodo(periodo_origen)
    destino = leer_periodo(periodo_destino)
    siguiente = (
        date(origen.year + 1, 1, 1) if origen.month == 12
        else date(origen.year, origen.month + 1, 1)
    )
    if destino != siguiente:
        raise ValueError("El arrastre fiscal requiere meses consecutivos.")
    return {"periodo_destino": periodo_destino, "casilla_164": _importe(casilla_167, "167")}
