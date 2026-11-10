# Plan maestro de cierre — Declaración IVA F-07

Estado al 10 de noviembre de 2026. **Este documento es el alcance fijo de cierre**, no una lista que crece con cada prueba. Los hallazgos nuevos se registran dentro de la etapa correspondiente; solo se amplía el alcance por cambio de requisitos explícito.

## Meta de aceptación
Aplicación F-07 que importe DTE, concilie cifras y saldos, presente casillas conforme a la versión oficial aplicable, permita revisión fiscal trazable, mantenga aislamiento por empresa y esté validada de extremo a extremo antes de autorizar producción.

## Ruta de ocho hitos (orden y criterios de salida)

| # | Hito | Estado | Criterio verificable de cierre |
|---|---|---|---|
| 1 | Seguridad multiempresa y autenticación | Avance probado, no cerrado | Pruebas HTTP de JWT ausente/inválido, acceso autorizado y 403 entre empresas para todos los endpoints tributarios |
| 2 | Integridad de importación DTE | Avance probado, no cerrado | Casos reales de compras, ventas, anulados, duplicados, versiones, omisiones y totales conciliados |
| 3 | Motor de cálculo F-07 y normativa | **Bloqueante** | Casillas 110/155 y 164/167 separadas, fórmulas oficiales contrastadas y pruebas de arrastre entre períodos |
| 4 | Persistencia y conciliación histórica | **Bloqueante** | Sustituir dependencia fiscal de localStorage; definir devoluciones DTE 05 vs ajuste manual, migración auditable y conciliación de períodos heredados |
| 5 | Integración frontend/backend | En curso | La pantalla presenta exactamente las cifras oficiales del servidor; manejo de errores, permisos, impresión y ajustes verificados en navegador |
| 6 | Pruebas integrales y calidad | En curso | API HTTP, PostgreSQL local, frontend, regresión, revisión de warnings y respaldo/restauración |
| 7 | Revisión fiscal y aceptación del usuario | Pendiente | Comparación casilla por casilla con F-07 oficial y casos contables aprobados por el responsable tributario |
| 8 | Preparación y publicación controlada | Pendiente | Checklist de seguridad, migración reversible, rollback, autorización explícita de despliegue y prueba posterior |

## Cómo se mide el avance
- **Pruebas aprobadas** es una métrica de calidad, NO un porcentaje de producto terminado.
- **Hitos cerrados / 8** solo aumenta cuando se cumple el criterio de salida, no cuando se crea una prueba.
- No se declara un porcentaje de avance total sin medir trabajo y riesgos de cada hito.
- Prioridad de ejecución: resolver bloqueos normativos y persistencia; después cerrar integración y pruebas; finalmente aceptación y producción.
- Cada actualización debe mostrar los ocho hitos y sus estados, los bloqueos y el siguiente entregable concreto. No inventar etapas.

## Evidencia actual
- 128 pruebas backend aprobadas, 515 warnings y 6 subtests aprobados en 6.04 s (resultado reportado por el usuario).
- Última compilación frontend verificada: 514 ms.
- Validación de importes y períodos implementada en endpoints de liquidación.
- Sin prueba de aceptación completa en navegador; sin certificación normativa; sin migración histórica; producción no modificada.

## Corte de seguimiento — 10 de noviembre de 2026

**Hitos cerrados: 0/8. Hito prioritario en ejecución: 4 (persistencia y conciliación histórica), con dependencia crítica del hito 3 (normativa).**

| Hito | Evidencia reciente | Falta para cerrar |
| --- | --- | --- |
| 1 Seguridad | Pruebas JWT, acceso entre empresas y vínculo archivado para consulta/escritura auditada 164 | Cobertura de todos los endpoints tributarios |
| 2 Integridad DTE | Pruebas previas de importación y aislamiento | Conciliación de casos reales, versiones, anulados y omisiones |
| 3 Normativa | Separación preliminar de 110/155/164/167; advertencia visible | Confirmar fórmulas y arrastres oficiales, especialmente 167/168/203 |
| 4 Persistencia | Registro 164 auditado, inventario y resumen histórico, CI PostgreSQL | Migraciones aprobadas, reconciliar históricos y eliminar dependencia fiscal localStorage; decidir DTE 05 vs ajustes manuales |
| 5 Interfaz | Panel de respaldo 164, estados diferenciados | Prueba completa en navegador y cifras oficiales del servidor |
| 6 Calidad | CI de backend, frontend y PostgreSQL efímero aprobada hasta `aa2c500` | Regresión integral, restauración y pruebas de entorno real |
| 7 Aceptación | Sin aceptación documentada | Revisión tributaria casilla por casilla |
| 8 Publicación | Sin cambios de producción | Plan de reversión, aprobación expresa y despliegue controlado |

**Siguiente entregable concreto:** contrato verificable de casillas 110/155/164/167 y sus consumidores; después abordar persistencia de devoluciones y ajustes manuales sin perder históricos. No cerrar el hito 4 solo porque su submódulo 164 tiene pruebas aprobadas.

## Riesgos críticos documentados
- `docs/AUDITORIA_NORMATIVA_F07_SALDOS.md`: saldo fiscal 155 vs excedente 167; faltan conceptos y casillas.
- `docs/PLAN_PERSISTENCIA_DEVOLUCIONES_F07.md`: DTE 05 y devoluciones manuales, doble descuento, trazabilidad, datos locales.
- La cifra `remanente_siguiente` de compatibilidad NO debe usarse como casilla 155 sin resolver separación de saldos.

## Próximo entregable prioritario
Diseño y pruebas de contrato del cálculo de casillas 110, 155, 164 y 167; identificar consumidores del frontend y eliminar el uso fiscal ambiguo de `remanente_siguiente` sin migraciones silenciosas ni cambios en producción.
