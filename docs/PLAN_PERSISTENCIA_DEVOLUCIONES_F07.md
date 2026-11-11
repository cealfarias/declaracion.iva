# Plan de persistencia y conciliación de devoluciones F-07

Estado: diseño propuesto; **no aplicado a ninguna base de datos**.

## Situación comprobada en código

- `iva_liquidaciones` guarda empresa, mes, año, remanente anterior, retenciones, percepciones y anticipo; no guarda ajustes manuales de devoluciones.
- `Liquidacion.jsx` conserva `devoluciones_manual_<empresa>_<mes>_<anio>` en `localStorage`, con valores `neto` y `credito`.
- El backend calcula devoluciones a partir de compras tipo DTE `05`; por ello, un ajuste manual debe ser explícito y auditable, sin sobrescribir los DTE.
- Existen reglas históricas en frontend para empresa ID 2 en enero, febrero y marzo de 2026. Son referencias a conciliar, **no valores autorizados para migración automática**.

## Diseño propuesto (pendiente de aprobación técnica y pruebas)

Crear una tabla separada `iva_ajustes_devoluciones`, sin alterar los importes originales de `iva_dtes_compras`:

| Campo | Propósito |
|---|---|
| `id` | Identificador interno |
| `empresa_id` | Empresa propietaria, FK obligatoria |
| `mes`, `anio` | Período fiscal, validado |
| `neto`, `credito` | Importes decimales NUMERIC(18,2), no Float |
| `origen` | `manual` o `migracion_local_confirmada` |
| `justificacion` | Motivo de la corrección y referencia documental |
| `creado_por`, `actualizado_por` | Usuario autenticado |
| `creado_en`, `actualizado_en` | Marcas de tiempo |
| `version` | Control de concurrencia o historial de cambios |

Definir unicidad de ajuste vigente por empresa y período o permitir múltiples asientos con suma explícita; decidir antes de crear el esquema. Preservar un historial inmutable de modificaciones, especialmente para importes ya declarados.

## Reglas imprescindibles

1. GET de conciliación autenticado y autorizado por pertenencia a la empresa, con los valores DTE, ajustes existentes y valores propuestos separados.
2. POST de ajustes con validación de importes finitos, no negativos y máximo dos decimales; sin escritura implícita al consultar.
3. No confiar en el ID de empresa o usuario enviado por el navegador sin validar el JWT y la relación usuario-empresa.
4. Evitar doble descuento: definir si el ajuste **sustituye** la devolución calculada por DTE o si representa una diferencia adicional. No combinar ambas cifras hasta decidirlo y probarlo.
5. No importar `localStorage` automáticamente. Mostrar comparación y requerir confirmación expresa por período.
6. No borrar las copias locales hasta confirmar lectura posterior de PostgreSQL y conservar respaldo.
7. Si los importes difieren de una declaración ya presentada, marcar el período para revisión contable; no modificar declaraciones históricas silenciosamente.
8. Preparar migración reversible con copia de seguridad, pruebas SQLite/PostgreSQL y control de permisos. No ejecutar en producción sin autorización expresa.

## Pruebas previstas

- Aislamiento entre empresas y JWT inválido.
- Lectura sin efectos secundarios.
- Validación de importes, período y precisión decimal.
- Idempotencia, concurrencia y trazabilidad de modificaciones.
- Cálculo de devoluciones DTE 05 frente a ajuste manual, sin duplicidad.
- Conciliación enero-marzo 2026: valores del navegador, PostgreSQL y documentación tributaria.
- No alteración de datos existentes al instalar la migración.

## Siguiente decisión

Confirmar con documentación fiscal si el ajuste manual debe reemplazar las cifras DTE 05 o reflejar un asiento complementario. Hasta entonces, no añadir columnas ni alterar la fórmula tributaria.


## Evidencia de regresión agregada (2026-11-10)

Las pruebas en `tests/test_liquidacion_aritmetica.py` comprueban que las devoluciones DTE tipo 05 se restan una sola vez de compras y crédito de su misma versión, sin mezclar documentos omitidos, otras versiones u otras empresas. También documentan el caso límite de una nota de crédito tipo 05 sin compra de origen: el contrato actual puede producir compras y crédito netos negativos. **Este comportamiento queda identificado para revisión fiscal; no se normaliza silenciosamente a cero.**

**Límite:** estas pruebas no resuelven la elección entre sustituir el importe DTE por un ajuste manual o sumar una diferencia complementaria. La interfaz conserva ajustes en `localStorage` y no existe migración aprobada. No combinar automáticamente ambos importes ni modificar datos de producción.
