# Auditoría normativa F-07 v14: separación de saldos

Fecha de revisión: 2026-11-10. Estado: **hallazgo confirmado en código; corrección pendiente de diseño y pruebas**.

## Fuentes oficiales

- Formulario F-07 v14, Ministerio de Hacienda: https://www.mh.gob.sv/wp-content/uploads/2025/08/F07_V14_COMPLE.pdf
- Manual de anexos F-07 v14: https://transparencia.mh.gob.sv/downloads/pdf/700-DGII-MN-2021-26031.pdf
- Ley del IVA, artículo 67: https://transparencia.mh.gob.sv/downloads/pdf/DC5828.pdf

## Hallazgo de alta prioridad

En `declaraciones_iva_api/app/routers/liquidacion.py`, función `get_liquidacion`:

```python
remanente_siguiente = round(excedente_credito + remanente_no_utilizado + deducciones_sobrantes, 2)
```

El resultado agrupa dos conceptos que el F-07 v14 presenta por separado:

1. **Casilla 155**: remanente de crédito fiscal para próximo período, calculado a partir de créditos y débitos; la **casilla 110** representa el remanente de crédito del período anterior.
2. **Casilla 167**: excedente del impuesto para próximo período a favor del declarante, asociado al bloque de retenciones, percepciones y anticipos; la **casilla 164** representa el excedente de impuesto del período anterior.

La fórmula oficial de la casilla 167 se expresa como `max(166 - 160 - 203, 0)`; la de la casilla 168 como `max(160 - 166 + 203, 0)`. El sistema aún no modela todas las casillas y ajustes necesarios para reproducir estas fórmulas íntegramente.

**No usar `remanente_siguiente` como sinónimo de casilla 155 ni como base de arrastre fiscal sin corregir el modelo.**

## Riesgos adicionales por revisar

- La función `get_remanente_historico` calcula saldos a partir de compras y ventas, pero no incorpora todos los conceptos de las casillas 145 y 150 del formulario; tampoco distingue claramente versiones en su reconstrucción histórica.
- `get_liquidacion` aplica `remanente_anterior` después de determinar `impuesto_determinado`, mientras el F-07 incluye la casilla 110 en la suma de créditos previa a la determinación de las casillas 155/160. Es necesario comprobar equivalencia y efectos de redondeo.
- El campo `remanente_anterior` se utiliza para un único tipo de saldo; falta modelar explícitamente `excedente_impuesto_anterior` (casilla 164).
- El código suma `retenciones_efectuadas + percepciones_efectuadas` en `total_terceros`; se debe mapear individualmente a las casillas oficiales y considerar las otras operaciones exigidas.
- Las pruebas actuales verifican la aritmética implementada, no su conformidad normativa. **77 pruebas aprobadas no certifican el F-07.**

## Plan de corrección propuesto (sin ejecutar aún)

1. Definir contrato de respuesta que separe `remanente_credito_fiscal_siguiente` (155) de `excedente_impuesto_siguiente` (167).
2. Modelar saldo de casilla 164 y los conceptos de casillas 166, 168, 203 y otros ajustes aplicables.
3. Añadir pruebas de regresión para ambas clases de saldo, incluso cuando coexistan y al pasar de un período al siguiente.
4. Revisar los componentes frontend que leen `remanente_siguiente` antes de cambiar su significado.
5. Validar ejemplos con un profesional tributario o instrucciones oficiales aplicables al contribuyente antes de habilitar declaración real.

No se ha modificado código de cálculo ni producción como parte de esta auditoría.
