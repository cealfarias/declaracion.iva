# Criterios verificables para versión candidata F-07

Estado: **en construcción; no es versión candidata aprobada ni lista para producción**.

La versión candidata para revisión debe poder ejecutarse en entorno de pruebas, sin modificar declaraciones ni bases de producción. No equivale a aceptación fiscal.

## Puertas de salida (8 hitos del plan maestro)

| Hito | Evidencia mínima | Estado |
|---|---|---|
| 1. Seguridad multiempresa | JWT ausente/inválido, acceso propio y rechazo de empresa ajena para todas las rutas fiscales | Parcial |
| 2. Integridad DTE | Importación y conciliación con casos reales, anulados, omisiones y versiones | Parcial |
| 3. Normativa F-07 | Matriz casilla-fórmula-fuente oficial, 110/155/164/167/168/203, arrastres y pruebas | Bloqueado |
| 4. Persistencia histórica | Ajustes auditables en PostgreSQL, conciliación por período y sin dependencia fiscal de localStorage | Bloqueado |
| 5. Interfaz/API | Importes idénticos al servidor, errores y permisos visibles, prueba en navegador | Parcial |
| 6. Calidad | CI, PostgreSQL, regresión de frontend, backup/restauración en pruebas | Parcial |
| 7. Aceptación fiscal | Comparación con F-07 oficial y casos documentados, aprobación responsable | Pendiente del usuario |
| 8. Publicación controlada | Plan de rollback, checklist, aprobación expresa y verificación posterior | No autorizado |

**Conteo formal: 0/8 hitos cerrados. Prioridad activa: 4/8, dependiente de 3/8.**

## Contratos ya implementados en desarrollo

- Casilla 164: registro auditado por usuario, empresa, período, origen y referencia; GET de respaldo con discrepancia HTTP 409.
- Inventario y resumen históricos 164: SQL de solo lectura y pruebas PostgreSQL; scripts de migración en borrador, no ejecutados en producción.
- Devoluciones DTE 05: GET autenticado `/{empresa_id}/conciliacion-devoluciones` con importes del servidor y sin ajuste manual persistido; la interfaz los compara con copias locales, sin migrarlas ni sumarlas.
- CI: compila frontend, prueba backend y usa PostgreSQL efímero. Cada commit debe verificarse por separado; no se presume éxito de una ejecución pendiente.

## Bloqueos que impiden declarar la versión candidata terminada

1. Definición normativa comprobada de 167/168/203 y relación de 110/155 con 164, incluyendo pruebas de arrastre y casos reales.
2. Tratamiento fiscal de devoluciones manuales: sustitución del importe DTE 05 o ajuste adicional; documentar respaldo y evitar doble cómputo.
3. Migración de ajustes locales con respaldo, consentimiento por período, auditoría e idempotencia; retirar dependencia de cálculos locales no conciliados.
4. Prueba completa en navegador, conciliación histórica y restauración de respaldo en entorno aislado.
5. Revisión final del usuario y responsable tributario; producción siempre requiere autorización independiente.

## Procedimiento para entregar a revisión

1. Congelar SHA exacto y registrar resultados de los tres trabajos de CI.
2. Ejecutar migraciones solo en PostgreSQL de pruebas y probar restauración.
3. Verificar acceso propio/ajeno, DTE y casillas en navegador con datos ficticios y un caso real anonimizado autorizado.
4. Adjuntar matriz de diferencias por casilla y respaldo documental.
5. Etiquetar como candidata **solo si** los bloqueos de ingeniería están resueltos; la revisión fiscal y la autorización de producción son puertas separadas.

No borrar datos del navegador, modificar Render ni desplegar sin autorización expresa.
