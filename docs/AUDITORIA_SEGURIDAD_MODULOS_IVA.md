# Auditoría inicial de autorización — Declaraciones IVA

Estado: revisión estática del código en la rama feature/sidebar-empresas-invalidados. **No equivale a pruebas de penetración ni a validación en producción.**

## Hallazgo crítico: autorización por empresa

Los módulos `compras.py`, `ventas_cf.py`, `ventas_contribuyentes.py`, `anulados.py`, `retenciones.py` y `liquidacion.py` aceptan identificadores de empresa y realizan operaciones sobre datos tributarios sin exigir sistemáticamente una sesión JWT y un vínculo activo entre el usuario y la empresa. Un identificador de empresa no constituye autorización.

**Consecuencia potencial:** un cliente que invoque la API directamente podría acceder o modificar información de una empresa ajena. No se ha intentado explotar este comportamiento con datos de terceros.

## Referencia existente

`app/routers/empresas.py` ya dispone de `usuario_actual` (validación JWT) y `exigir_vinculo` (vínculo no archivado). Extraer estas reglas a `app/core/authorization.py` para que todos los routers compartan la misma política.

## Plan de corrección

1. Exigir JWT en todos los endpoints tributarios; no confiar en identificadores de usuario enviados por el cliente.
2. Autorizar `empresa_id` en parámetros de ruta, consulta y formularios de carga; validar el propietario antes de procesar archivos.
3. En operaciones que reciben un identificador de registro, consultar primero su `empresa_id` y verificar el vínculo; evitar acceso indirecto por ID.
4. Para escritura, comprobar rol y estado de empresa; responder 401 para sesión inválida y 403 para acceso prohibido.
5. Actualizar el frontend para enviar `Authorization: Bearer` sin exponer tokens en mensajes o registros.
6. Incorporar pruebas automatizadas con dos usuarios, dos empresas, vínculo archivado y accesos cruzados a lectura/escritura.
7. Ejecutar pruebas únicamente en `declaraciones_iva_pruebas` y no desplegar sin autorización explícita.

## Otros pendientes

- `app/core/security.py` usa un secreto JWT predeterminado si no se define `SECRET_KEY`; exigir secreto seguro en ambientes no locales.
- Revisar `anulados.py` para eliminar cualquier desactivación de verificación de certificados TLS.
- Registrar fecha, versión y huella del documento de términos aceptado; el indicador booleano actual no aporta trazabilidad completa.
- Evitar migraciones de esquema implícitas durante el arranque de la aplicación; emplear migraciones versionadas.
- Agregar `.venv/` a `.gitignore` sin borrar el entorno local.

## Criterios de aceptación

- Ningún endpoint tributario lee, exporta o modifica datos sin JWT válido y autorización sobre la empresa.
- Los intentos cruzados entre usuarios/empresas devuelven 403 y no modifican datos.
- Las pruebas de registro, inicio de sesión, aceptación de términos y panel siguen funcionando.
- Sin modificaciones de producción hasta revisión y autorización.
