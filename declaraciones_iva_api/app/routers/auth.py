from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os

from app.core.database import get_db
from app.models.models import Usuario, Empresa, UsuarioEmpresa
from app.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

GOOGLE_CLIENT_ID = "231508841464-22ln2h2p8k524lb6njdqmsk7s9e9bvl7.apps.googleusercontent.com"

router = APIRouter()

class UserCreate(BaseModel):
    email: str
    password: str
    nombre: str
    # Datos de la Empresa (1 a 1 por ahora)
    razon_social: str
    nit: str
    nrc: str

class UserLogin(BaseModel):
    email: str
    password: str

class GoogleToken(BaseModel):
    token: str

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(Usuario).filter(Usuario.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    # 1. Crear Usuario
    hashed_password = get_password_hash(user.password)
    new_user = Usuario(email=user.email, password_hash=hashed_password, nombre=user.nombre)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 2. Crear Empresa
    nueva_empresa = Empresa(
        razon_social=user.razon_social,
        nit=user.nit,
        nrc=user.nrc
    )
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    
    # 3. Vincular (1 Usuario = 1 Empresa)
    vinculo = UsuarioEmpresa(usuario_id=new_user.id, empresa_id=nueva_empresa.id, rol="admin")
    db.add(vinculo)
    db.commit()
    
    return {"message": "Usuario y Empresa creados exitosamente", "id": new_user.id}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(Usuario).filter(Usuario.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario no registrado o credenciales incorrectas. Por favor, regístrate primero.")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email, "id": db_user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "nombre": db_user.nombre, "id": db_user.id}

@router.post("/google")
def google_login(token_data: GoogleToken, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(
            token_data.token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        email = idinfo['email']
        
        db_user = db.query(Usuario).filter(Usuario.email == email).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="Usuario no registrado en el sistema. Por favor regístrate primero.")
            
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email, "id": db_user.id}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "nombre": db_user.nombre, "id": db_user.id}
        
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido")
    except HTTPException as he:
        raise he
    except Exception as e:
        print("Error en Google Auth:", e)
        raise HTTPException(status_code=500, detail="Error interno en autenticación")
