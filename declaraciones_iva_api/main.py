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

app = FastAPI(title="Declaraciones de IVA API", version="1.0.0")

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://declaraciones.iva.demiempresa.online"
]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import auth, empresas, compras

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(empresas.router, prefix="/api/v1", tags=["Empresas"])
app.include_router(compras.router, prefix="/api/v1/compras", tags=["Compras"])

@app.get("/")
def root():
    return {"message": "API de Declaraciones de IVA en funcionamiento"}

@app.delete("/api/v1/debug/wipe_db")
def wipe_database():
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"message": "Base de datos borrada y recreada exitosamente"}
    except Exception as e:
        return {"error": str(e)}
