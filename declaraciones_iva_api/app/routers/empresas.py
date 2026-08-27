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
    combustible_50_porciento: bool = False
    usuario_id: int # El ID del usuario creador (temporal)

@router.post("/empresas")
def create_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    # Verify if NIT or NRC already exists
    existing_empresa = db.query(Empresa).filter(
        (Empresa.nit == empresa.nit) | (Empresa.nrc == empresa.nrc)
    ).first()
    
    if existing_empresa:
        raise HTTPException(status_code=400, detail=f"El NIT o NRC ingresado ya se encuentra registrado.")

    try:
        # Crear Empresa
        db_empresa = Empresa(
            razon_social=empresa.razon_social,
            nit=empresa.nit,
            nrc=empresa.nrc,
            combustible_50_porciento=empresa.combustible_50_porciento
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al crear la empresa.")

@router.get("/empresas/usuario/{usuario_id}")
def get_empresas(usuario_id: int, db: Session = Depends(get_db)):
    vinculos = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.usuario_id == usuario_id).all()
    empresas = []
    for v in vinculos:
        empresas.append({
            "id": v.empresa.id,
            "razon_social": v.empresa.razon_social,
            "nit": v.empresa.nit,
            "nrc": v.empresa.nrc,
            "combustible_50_porciento": v.empresa.combustible_50_porciento
        })
    return empresas
from typing import Optional

class EmpresaUpdate(BaseModel):
    razon_social: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    combustible_50_porciento: Optional[bool] = None

@router.put("/empresas/{empresa_id}")
def update_empresa(empresa_id: int, empresa_data: EmpresaUpdate, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter_by(id=empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    if empresa_data.razon_social is not None:
        empresa.razon_social = empresa_data.razon_social
    if empresa_data.nit is not None:
        empresa.nit = empresa_data.nit
    if empresa_data.nrc is not None:
        empresa.nrc = empresa_data.nrc
    if empresa_data.combustible_50_porciento is not None:
        empresa.combustible_50_porciento = empresa_data.combustible_50_porciento
        
    db.commit()
    return {"message": "Empresa actualizada correctamente"}
