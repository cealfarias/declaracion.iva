from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.core.database import get_db
from app.models.models import Empresa, UsuarioEmpresa, Usuario
# A simple dependency to get the current user ID would go here, we'll mock it for now or require it in the schema

router = APIRouter()

class EmpresaCreate(BaseModel):
    razon_social: str
    nit: str
    nrc: str = None
    actividad_economica: str = None
    usuario_id: int # El ID del usuario creador (temporal)

@router.post("/empresas")
def create_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    # Crear Empresa
    db_empresa = Empresa(
        razon_social=empresa.razon_social,
        nit=empresa.nit,
        nrc=empresa.nrc,
        actividad_economica=empresa.actividad_economica
    )
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    
    # Vincular al usuario
    db_usuario_empresa = UsuarioEmpresa(
        usuario_id=empresa.usuario_id,
        empresa_id=db_empresa.id,
        rol="admin"
    )
    db.add(db_usuario_empresa)
    db.commit()
    
    return {"message": "Empresa creada", "empresa_id": db_empresa.id}

@router.get("/empresas/usuario/{usuario_id}")
def get_empresas(usuario_id: int, db: Session = Depends(get_db)):
    vinculos = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.usuario_id == usuario_id).all()
    empresas = []
    for v in vinculos:
        empresas.append({
            "id": v.empresa.id,
            "razon_social": v.empresa.razon_social,
            "nit": v.empresa.nit,
            "nrc": v.empresa.nrc
        })
    return empresas
