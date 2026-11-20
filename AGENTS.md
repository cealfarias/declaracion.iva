# AGENTS.md — Sistema de Declaración de IVA

> Instrucciones permanentes para agentes de IA y desarrolladores que trabajen en este repositorio.
> Antes de modificar código, lee este archivo y verifica el estado real con `git status`, `git log` y los tests.
> Si una instrucción del usuario contradice una regla crítica de este documento, detente y explica el conflicto antes de tocar el código.

## 1. Contexto del proyecto

Aplicación web para la gestión y declaración de IVA en El Salvador. Permite a una empresa:

- Registrar y administrar empresas (razón social, NIT, NRC).
- Importar comprobantes DTE y reportes Excel/CSV del Ministerio de Hacienda (MH).
- Generar los anexos del formulario **F-07 V14**:
  - Detalle de Ventas a Contribuyentes (Anexo 1).
  - Detalle de Ventas a Consumidor Final (Anexo 2).
  - Libro de Compras (Anexo 3).
  - Documentos Invalidados.
  - Retenciones 1% (Anexo 7 / Casilla 162).
- Consolidar compras, ventas, retenciones, remanentes y ajustes en la liquidación F-07.
- Exportar CSV con el formato oficial para cargarlos en el portal de Hacienda.
- Mantener versiones originales/modificatorias por período y bloquear períodos ya declarados.

Es un sistema multiempresa y multiperiodo. La unidad de aislamiento es la empresa (`empresa_id`), no el esquema de PostgreSQL.

**Este proyecto NO es NEXO.** No usa un esquema PostgreSQL por tenant ni `search_path` por cliente. Usa una sola base de datos y un solo esquema (`public`), con tablas `iva_*` y aislamiento mediante `empresa_id` + la tabla de vínculos `iva_usuario_empresa`.

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 19, Vite 8, React Router 7, Tailwind CSS 4, `lucide-react`, `axios`, `@react-oauth/google`, `react-markdown`, `react-hot-toast` |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Pydantic, Uvicorn |
| Auth | JWT HS256 (`python-jose`), bcrypt (`passlib`/`bcrypt`), Google OAuth |
| Base de datos local | SQLite (`sql_app.db` por defecto) |
| Base de datos producción | PostgreSQL en Render (`DATABASE_URL`) |
| Archivos | `openpyxl`, `pandas`, CSV |
| Frontend hosting | Vercel (proyecto en `declaraciones_iva_web`) |
| Backend hosting | Render (proyecto en `declaraciones_iva_api`) |
| CI | GitHub Actions: build frontend, tests backend SQLite y test PostgreSQL F-07 |
| Control de versiones | Git / GitHub |

Ramas principales:

- `feature/sidebar-empresas-invalidados`: rama de desarrollo.
- `main`: producción.
- El workflow `.github/workflows/verify-development.yml` se ejecuta en pushes a la rama de desarrollo y en PRs hacia `main`.

## 3. Arquitectura y rutas

### Backend

- Entrada: `declaraciones_iva_api/main.py` (FastAPI).
- Routers: `declaraciones_iva_api/app/routers/`
  - `auth.py`, `empresas.py`, `compras.py`, `ventas_cf.py`,
    `ventas_contribuyentes.py`, `anulados.py`, `retenciones.py`,
    `liquidacion.py`.
- Modelos SQLAlchemy: `app/models/models.py`.
- Seguridad y autorización: `app/core/security.py`, `app/core/authorization.py`.
- Preflight/normativa F-07: `app/core/casillas_f07.py`, `app/core/preflight_f07_164.py`.
- Migraciones SQL: `db/migrations/` y `declaraciones_iva_api/db/migrations/`.
- Tests: `declaraciones_iva_api/tests/`.

### Frontend

- Rutas lazy: `declaraciones_iva_web/src/App.jsx`.
- Layout/sidebar/topbar: `src/components/AppShell.jsx`.
- Páginas: `src/pages/`.
- Descarga autenticada de archivos: `src/utils/downloadAuthenticatedFile.js`.
- Cliente HTTP y adjunto de JWT: `src/main.jsx` (interceptor de `axios`).
- Auth global: `src/context/AuthContext.jsx`.
- Estilos y tokens: `src/index.css`.

Rutas principales: `/login`, `/registro`, `/terminos`, `/dashboard`, `/anexos`,
`/compras`, `/consumidor-final`, `/ventas-contribuyentes`, `/anulados`,
`/retenciones`, `/liquidacion`, `/configuracion`.

## 4. Reglas críticas del negocio

### 4.1 El formato CSV para Hacienda es intocable

Los CSV son un contrato externo con el portal del MH. **No cambies columnas, orden, separadores, decimales, anexo ni identificadores para “arreglar” una pantalla o una descarga.**

Reglas generales:

- Separador: `;` (punto y coma).
- Sin fila de encabezados ni títulos.
- Fin de línea CRLF (`\r\n`), codificación UTF-8.
- Importes con punto decimal y máximo 2 decimales; sin separador de miles.
- NIT/NRC/DUI sin guiones ni pleca.
- No inventar NIT/NRC/DUI si el dato de origen no existe: eso debe corregirse en el origen.
- El número de anexo depende del libro: Ventas Contribuyentes = `1`, Consumidor Final = `2`, Compras = `3`, Retenciones = `7`.
- Cada exportador tiene su propio contrato. No reutilices la estructura de un anexo en otro.

Contrato de **Detalle de Ventas a Contribuyentes** (20 columnas A–T):

| Col | Dato |
|---|---|
| A | Fecha de emisión (`DD/MM/AAAA`) |
| B | Clase de documento |
| C | Tipo de documento (`03`, `05`, `06`) |
| D | Número de resolución / código de generación sin guiones |
| E | Número de serie / sello de recepción |
| F | Número de documento / código de generación |
| G | Número de control interno (vacío para DTE) |
| H | NIT o NRC del cliente |
| I | Nombre o razón social |
| J | Ventas exentas |
| K | Ventas no sujetas |
| L | Ventas gravadas locales |
| M | Débito fiscal |
| N | Ventas a cuenta de terceros no domiciliados |
| O | Débito fiscal por venta a cuenta de terceros |
| P | Total ventas |
| Q | DUI del cliente |
| R | Tipo de operación (renta) |
| S | Tipo de ingreso (renta) |
| T | Número de anexo (`1`) |

La columna G vacía es correcta para DTE; no la elimines ni muevas el NIT a otra columna sin validar contra el manual oficial y los tests.

Otros exportadores:

- `compras.py`: Anexo 3 (21 columnas A–U) y Anexo 5 separado para DTE 14.
- `ventas_cf.py`: Anexo 2.
- `anulados.py`: formato propio de documentos invalidados.
- `retenciones.py`: Anexo 7 (9 columnas A–I).

**Regla de oro:** si el portal del MH rechaza un CSV, diagnostica datos (NIT/NRC/DUI, período, anexo, totales) antes de tocar el exportador. No cambies la estructura para “hacer que suba”.

### 4.2 Cálculo F-07 y trazabilidad fiscal

- La fuente de verdad de los importes es el backend; el frontend no debe recalcular ni maquillar cifras fiscales.
- No modifiques casillas, fórmulas, remanentes, excedentes, ajustes, propuestas de devoluciones, auditoría 164, conciliación DTE 05 ni avisos de impresión sin revisión fiscal y pruebas específicas.
- `remanente_siguiente` es una cifra de compatibilidad; **no equivale automáticamente a la casilla 155**. La separación 110/155/164/167 está documentada como pendiente/bloqueante en `docs/AUDITORIA_NORMATIVA_F07_SALDOS.md` y `docs/PLAN_MAESTRO_CIERRE_F07.md`.
- Las propuestas documentales y ajustes manuales son de solo lectura/auditoría hasta que exista aprobación explícita; no deben sumarse silenciosamente a los totales fiscales.
- Aprobar tests no significa certificación normativa. Los documentos de `docs/` son evidencia histórica y pueden estar desactualizados; el código y los tests actuales son la referencia, pero la validación fiscal requiere aprobación humana.

### 4.3 Seguridad multiempresa

- Todos los endpoints tributarios deben exigir JWT `Authorization: Bearer <token>`.
- La autorización por empresa se valida con `autorizar_compras` / `autorizar_empresa_tributaria` y el vínculo activo en `iva_usuario_empresa`.
- **Nunca confíes en un `empresa_id`, `usuario_id` o ID de registro enviado por el cliente** sin validar el vínculo.
- No desactives TLS, CORS, validaciones de pertenencia ni controles de acceso para “probar”.
- `SECRET_KEY` debe estar definida en producción; el valor por defecto solo sirve para desarrollo local.
- No reintroduzcas el bypass de login/demo. El login real es obligatorio.
- Google OAuth debe tener autorizado el dominio exacto (producción y previews). Si el preview falla por origen no autorizado, se corrige en Google Cloud/backend; no se agrega un bypass.

### 4.4 Base de datos y migraciones

- Producción: PostgreSQL de Render. Local/tests: SQLite.
- `DATABASE_URL` se normaliza a `postgresql+psycopg2://` y agrega `sslmode=require` para Render.
- El esquema es único (`public`). El aislamiento es por `empresa_id`; **no hay esquemas por tenant**.
- No hay Alembic. Las migraciones son SQL versionado en `db/migrations/` y `declaraciones_iva_api/db/migrations/`.
- `main.py` ejecuta `Base.metadata.create_all` y varios `ALTER TABLE` idempotentes al arrancar. Es legado; **no agregues DDL implícito nuevo** ni confíes en esto como sustituto de una migración.
- No ejecutes migraciones ni tests destructivos contra la base de producción. Para cambios de esquema en producción: respaldo, migración revisada, plan de reversión y autorización explícita.
- No borres ni renombres tablas/columnas con datos fiscales sin migración y aprobación.

### 4.5 Descargas y frontend

- Las descargas autenticadas deben usar `downloadAuthenticatedFile.js` con `fetch`, `Authorization: Bearer`, `cache: 'no-store'`, parámetro anticaché y descarga Blob.
- **Nunca uses `window.open`/`window.location.href` hacia la API para descargar CSV**: no adjuntan el JWT y provocan `Not authenticated`.
- No reconstruyas el CSV en el frontend. El backend es el generador oficial.
- No quites el anticaché ni el aviso de filas sin NIT/NRC/DUI; evitan descargar archivos viejos o inválidos.
- `Content-Disposition` puede no ser legible en llamadas cross-origin; el helper usa un nombre de respaldo con período y versión. No agregues lógica frágil por el nombre.
- El frontend usa lazy loading; mantén las rutas con `React.lazy` y `Suspense`.
- No cambies IDs, nombres de handlers ni el endpoint del botón de exportación por cambios puramente visuales.

### 4.6 Datos sensibles y Git

- Nunca hagas commit de `.venv/`, `venv/`, `.env`, `.env.local`, bases SQLite/PostgreSQL, DTE/JSON de clientes, certificados, llaves, PDFs ni archivos `iva*`.
- No ejecutes `git add .` ni `git commit -a`. Agrega archivos explícitamente, uno por uno.
- No toques ni archives los entornos virtuales existentes.
- No hagas push a `main` ni despliegues a producción sin autorización explícita del usuario.
- Mantén mensajes de commit claros (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).

## 5. Comandos de desarrollo y pruebas

### Backend local (Windows PowerShell)

```powershell
cd C:\demiempresa\declaraciones_iva\declaraciones_iva_api

# Solo si no existe el entorno local; NO lo agregues a Git.
python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest pytest-subtests httpx

# Desarrollo con SQLite local
$env:DATABASE_URL = "sqlite:///./sql_app.db"
$env:SECRET_KEY = "dev-only-change-me"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API local: `http://127.0.0.1:8000` — documentación: `http://127.0.0.1:8000/docs`.

> El módulo de arranque es `main:app` (desde `declaraciones_iva_api`), no `app.main:app`.

### Frontend local

```powershell
cd C:\demiempresa\declaraciones_iva\declaraciones_iva_web
npm ci

# .env.local (ignorado por Git): VITE_API_URL=http://127.0.0.1:8000
npm run dev
```

Frontend local: `http://localhost:5173` (el backend permite CORS para 5173–5175).

Build y lint:

```powershell
npm run build
npm run lint
```

No hay suite de tests unitarios de frontend. La verificación mínima es `npm run build`, `npm run lint` y prueba manual en navegador.

### Tests backend (SQLite en memoria, igual que CI)

```powershell
cd C:\demiempresa\declaraciones_iva\declaraciones_iva_api
$env:DATABASE_URL = "sqlite:///:memory:"
python -m pytest -q tests
```

Test PostgreSQL específico de F-07 (requiere un PostgreSQL local levantado):

```powershell
$env:F07_TEST_DATABASE_URL = "postgresql+psycopg2://usuario:clave@localhost:5432/base_pruebas"
python -m pytest -q tests/test_f07_postgresql_ci.py
```

Chequeo de sintaxis (desde la raíz):

```powershell
python -m compileall -q declaraciones_iva_api
```

Comandos de CI de referencia: `.github/workflows/verify-development.yml`.

## 6. Flujo de trabajo esperado para un agente

1. **Reconocer:** `git status`, rama actual, `git log -5`, leer los archivos involucrados y los tests relacionados.
2. **No romper el contrato:** si el pedido toca CSV, cálculos F-07, auth o base de datos, aplicar las reglas de la sección 4.
3. **Cambio mínimo:** no refactorices módulos completos ni cambies lógica de negocio para resolver un problema visual/de conexión.
4. **Probar:** backend `pytest`; frontend `npm run build` y `npm run lint`; prueba manual de la ruta afectada.
5. **Git:** stage explícito de archivos, commit con mensaje descriptivo, push a la rama de desarrollo. No `git add .`, no `.venv`.
6. **Producción:** solo con autorización explícita. El flujo es `feature/sidebar-empresas-invalidados` → `main`; después de mergear, volver a la rama de desarrollo.
7. **Reportar:** qué cambió, qué se verificó, qué no se pudo verificar y qué riesgo queda.

Si una tarea requiere cambiar el formato CSV, las casillas F-07, el tratamiento de NIT/NRC o las migraciones de producción, y el usuario no lo autorizó de forma explícita, **no lo hagas**: explica el riesgo y pide confirmación.

## 7. Mapa rápido de archivos

| Necesitas… | Archivo |
|---|---|
| Arranque API | `declaraciones_iva_api/main.py` |
| Configuración DB | `declaraciones_iva_api/app/core/database.py` |
| JWT | `declaraciones_iva_api/app/core/security.py` |
| Autorización por empresa | `declaraciones_iva_api/app/core/authorization.py` |
| Modelos/tablas | `declaraciones_iva_api/app/models/models.py` |
| Exportación Ventas Contribuyentes | `declaraciones_iva_api/app/routers/ventas_contribuyentes.py` |
| Exportación Compras | `declaraciones_iva_api/app/routers/compras.py` |
| Exportación Ventas CF | `declaraciones_iva_api/app/routers/ventas_cf.py` |
| Exportación Retenciones | `declaraciones_iva_api/app/routers/retenciones.py` |
| Liquidación F-07 | `declaraciones_iva_api/app/routers/liquidacion.py` |
| Descarga CSV frontend | `declaraciones_iva_web/src/utils/downloadAuthenticatedFile.js` |
| Rutas/lazy | `declaraciones_iva_web/src/App.jsx` |
| Layout/sidebar | `declaraciones_iva_web/src/components/AppShell.jsx` |
| Auth frontend | `declaraciones_iva_web/src/context/AuthContext.jsx` |
| Reglas normativas F-07 | `docs/AUDITORIA_NORMATIVA_F07_SALDOS.md`, `docs/PLAN_MAESTRO_CIERRE_F07.md` |
| Plan de devoluciones/ajustes | `docs/PLAN_PERSISTENCIA_DEVOLUCIONES_F07.md` |

## 8. Trampas conocidas

- `.venv/` existe localmente y no está en `.gitignore`; **jamás lo agregues**. `.env.local` está ignorado por `*.local`.
- Hay varias bases SQLite de Desarrollo (`sql_app.db`, `iva_pruebas.db`, etc.); no las commitees ni asumas cuál usa el servidor: depende del `DATABASE_URL` y del directorio de trabajo.
- `main.py` hace DDL al arrancar y tiene CORS/orígenes hardcodeados. No lo uses como mecanismo de migración para producción.
- El login de Google exige que el dominio exacto del preview esté autorizado. Un error de origen no se arregla con un bypass.
- Un CSV que Hacienda rechaza por “Completar NIT, NRC o DUI” normalmente tiene identidad fiscal vacía en el origen; no es un problema de orden de columnas.
- Si la descarga usa `window.open`, vuelve el `Not authenticated`. No lo hagas.
- El comando de arranque correcto es `uvicorn main:app`, no `uvicorn app.main:app`.
- Los documentos de `docs/` pueden reflejar un estado anterior a los últimos merges; contrástalos con el código y los tests, y no declares hitos cerrados sin evidencia actual.

---

Última actualización de este documento: 2026-11-19. Si cambias la arquitectura, los comandos o una regla de negocio, actualiza `AGENTS.md` en el mismo commit.
