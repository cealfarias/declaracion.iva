from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.models import models

# Crear tablas en la base de datos local SQLite (o PostgreSQL)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Declaraciones de IVA API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import procesamiento, auth, empresas, periodos

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(empresas.router, prefix="/api/v1", tags=["Empresas"])
app.include_router(periodos.router, prefix="/api/v1", tags=["Periodos"])
app.include_router(procesamiento.router, prefix="/api/v1", tags=["Procesamiento"])

@app.get("/")
def root():
    return {"message": "API de Declaraciones de IVA en funcionamiento"}
