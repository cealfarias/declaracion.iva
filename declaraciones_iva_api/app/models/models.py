from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to intermediate table
    empresas = relationship("UsuarioEmpresa", back_populates="usuario")

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    razon_social = Column(String, nullable=False)
    nit = Column(String(14), nullable=False)
    nrc = Column(String, nullable=True)
    actividad_economica = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    usuarios = relationship("UsuarioEmpresa", back_populates="empresa")
    periodos = relationship("PeriodoFiscal", back_populates="empresa")

class UsuarioEmpresa(Base):
    __tablename__ = "usuarios_empresas"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    rol = Column(String, default="admin") # admin, auxiliar

    usuario = relationship("Usuario", back_populates="empresas")
    empresa = relationship("Empresa", back_populates="usuarios")

class PeriodoFiscal(Base):
    __tablename__ = "periodos_fiscales"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False) # 1 a 12
    estado = Column(String, default="abierto") # abierto, cerrado
    created_at = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="periodos")
    dtes = relationship("DteProcesado", back_populates="periodo")

class DteProcesado(Base):
    __tablename__ = "dtes_procesados"
    id = Column(Integer, primary_key=True, index=True)
    periodo_id = Column(Integer, ForeignKey("periodos_fiscales.id"), nullable=False)
    tipo_anexo = Column(String, nullable=False) # 'compras', 'ventas_contribuyente', 'ventas_consumidor'
    json_original = Column(JSON, nullable=False)
    fecha_emision = Column(String, nullable=False) # YYYY-MM-DD
    numero_control = Column(String, nullable=False)
    codigo_generacion = Column(String, nullable=True)
    monto_total = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    periodo = relationship("PeriodoFiscal", back_populates="dtes")
