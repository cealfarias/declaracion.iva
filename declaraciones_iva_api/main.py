from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.models import models

# Crear tablas en la base de datos local SQLite (o PostgreSQL)
Base.metadata.create_all(bind=engine)

# Migración para la nueva columna combustible_50_porciento
from sqlalchemy import text
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE iva_empresas ADD COLUMN combustible_50_porciento BOOLEAN DEFAULT FALSE;"))
except Exception:
    pass

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE iva_usuarios ADD COLUMN terminos_aceptados BOOLEAN DEFAULT FALSE;"))
except Exception:
    pass

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE iva_declaraciones_estado ADD COLUMN tipo_libro VARCHAR(50) DEFAULT 'compras' NOT NULL;"))
except Exception:
    pass

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE iva_dtes_compras ADD COLUMN version INTEGER DEFAULT 1 NOT NULL;"))
        conn.execute(text("ALTER TABLE iva_dtes_ventas_cf ADD COLUMN version INTEGER DEFAULT 1 NOT NULL;"))
        conn.execute(text("ALTER TABLE iva_declaraciones_estado ADD COLUMN version INTEGER DEFAULT 1 NOT NULL;"))
        conn.execute(text("ALTER TABLE iva_declaraciones_estado ADD COLUMN numero_declaracion VARCHAR;"))
except Exception:
    pass

# Migración idempotente de vínculos archivados (no elimina datos).
with engine.begin() as conn:
    if engine.dialect.name == "postgresql":
        conn.execute(text("ALTER TABLE iva_usuario_empresa ADD COLUMN IF NOT EXISTS archivado BOOLEAN NOT NULL DEFAULT FALSE"))
    elif engine.dialect.name == "sqlite":
        from sqlalchemy import inspect
        columns = {col["name"] for col in inspect(conn).get_columns("iva_usuario_empresa")}
        if "archivado" not in columns:
            conn.execute(text("ALTER TABLE iva_usuario_empresa ADD COLUMN archivado BOOLEAN NOT NULL DEFAULT 0"))
    else:
        raise RuntimeError("Migración archivado pendiente para este motor de base de datos.")

app = FastAPI(title="Declaraciones de IVA API", version="1.0.0")

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "https://declaraciones.iva.demiempresa.online",
    "https://planilla.demiempresa.online",
    "https://demiempresa.online",
    "https://www.demiempresa.online"
]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.demiempresa\.online",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import auth, empresas, compras, ventas_cf, anulados, ventas_contribuyentes, liquidacion, retenciones

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(empresas.router, prefix="/api/v1", tags=["empresas"])
app.include_router(compras.router, prefix="/api/v1/compras", tags=["compras"])
app.include_router(ventas_cf.router, prefix="/api/v1/ventas-cf", tags=["ventas-cf"])
app.include_router(anulados.router, prefix="/api/v1/anulados", tags=["anulados"])
app.include_router(ventas_contribuyentes.router, prefix="/api/v1/ventas-contribuyentes", tags=["ventas-contribuyentes"])
app.include_router(liquidacion.router, prefix="/api/v1/liquidacion", tags=["liquidacion"])
app.include_router(retenciones.router, prefix="/api/v1/retenciones", tags=["retenciones"])

@app.get("/")
def root():
    return {"message": "API de Declaraciones de IVA en funcionamiento"}

