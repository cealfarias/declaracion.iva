from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.security import SECRET_KEY, ALGORITHM
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.core.database import get_db
from app.models.models import Empresa, UsuarioEmpresa, Usuario
# A simple dependency to get the current user ID would go here, we'll mock it for now or require it in the schema

router = APIRouter()
bearer = HTTPBearer()

def usuario_actual(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> Usuario:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("id"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida.")
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")
    return usuario

def exigir_vinculo(db: Session, usuario_id: int, empresa_id: int) -> UsuarioEmpresa:
    vinculo = db.query(UsuarioEmpresa).filter(
        UsuarioEmpresa.usuario_id == usuario_id,
        UsuarioEmpresa.empresa_id == empresa_id
    ).first()
    if not vinculo:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa.")
    return vinculo


class EmpresaCreate(BaseModel):
    razon_social: str
    nit: str
    nrc: str = None
    actividad_economica: str = None
    combustible_50_porciento: bool = False
    usuario_id: int # El ID del usuario creador (temporal)

@router.post("/empresas")
def create_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    empresa.usuario_id = usuario.id
    try:
        # Verify if NIT or NRC already exists
        existing_empresa = db.query(Empresa).filter(
            (Empresa.nit == empresa.nit) | (Empresa.nrc == empresa.nrc)
        ).first()
        
        if existing_empresa:
            # If it already exists, just link the user to the existing company
            # Check if link already exists
            existing_link = db.query(UsuarioEmpresa).filter(
                UsuarioEmpresa.usuario_id == empresa.usuario_id,
                UsuarioEmpresa.empresa_id == existing_empresa.id
            ).first()
            
            if not existing_link:
                db_usuario_empresa = UsuarioEmpresa(
                    usuario_id=empresa.usuario_id,
                    empresa_id=existing_empresa.id,
                    rol="admin"
                )
                db.add(db_usuario_empresa)
                db.commit()
                
            return {"message": "Empresa vinculada exitosamente", "empresa_id": existing_empresa.id}

        # Crear nueva Empresa si no existe
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
        raise HTTPException(status_code=500, detail="Error interno al crear o vincular la empresa.")

@router.get("/empresas/usuario/{usuario_id}")
def get_empresas(usuario_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    if usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes consultar empresas de otro usuario.")
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
def update_empresa(empresa_id: int, empresa_data: EmpresaUpdate, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    vinculo = exigir_vinculo(db, usuario.id, empresa_id)
    if vinculo.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo un administrador puede editar la empresa.")
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

@router.delete("/empresas/{empresa_id}/mi-vinculo")
def desvincular_empresa(empresa_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Retira una empresa del panel del usuario sin borrar registros contables."""
    vinculo = exigir_vinculo(db, usuario.id, empresa_id)
    db.delete(vinculo)
    db.commit()
    return {"message": "Empresa retirada de tu panel. Sus documentos permanecen intactos."}
