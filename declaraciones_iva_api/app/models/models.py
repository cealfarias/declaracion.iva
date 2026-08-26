from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Usuario(Base):
    __tablename__ = "iva_usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    terminos_aceptados = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresas = relationship("UsuarioEmpresa", back_populates="usuario")

class Empresa(Base):
    __tablename__ = "iva_empresas"

    id = Column(Integer, primary_key=True, index=True)
    razon_social = Column(String, nullable=False)
    nit = Column(String, unique=True, index=True, nullable=False)
    nrc = Column(String, unique=True, index=True, nullable=False)
    combustible_50_porciento = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuarios = relationship("UsuarioEmpresa", back_populates="empresa")

class UsuarioEmpresa(Base):
    __tablename__ = "iva_usuario_empresa"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("iva_usuarios.id"))
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"))
    rol = Column(String, default="admin")  # admin, contador, asistente

    usuario = relationship("Usuario", back_populates="empresas")
    empresa = relationship("Empresa", back_populates="usuarios")


