from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Numeric, JSON, UniqueConstraint, func
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
    archivado = Column(Boolean, default=False, nullable=False)

    usuario = relationship("Usuario", back_populates="empresas")
    empresa = relationship("Empresa", back_populates="usuarios")

class DteCompra(Base):
    __tablename__ = "iva_dtes_compras"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), index=True, nullable=False)
    
    # Contexto
    periodo_mes = Column(String(2), nullable=False)
    periodo_anio = Column(String(4), nullable=False)
    
    # Datos extraídos del DTE necesarios para F-07
    fecha_emision = Column(String, nullable=False)
    clase_documento = Column(String, nullable=False, default="4") # 4=DTE
    tipo_documento = Column(String, nullable=False, default="03") # 03=CCF
    numero_resolucion = Column(String, nullable=False) # Código de generación
    serie_documento = Column(String, nullable=False) # Sello de recepción
    numero_documento = Column(String, nullable=False) # Código de generación o correlativo
    nit_proveedor = Column(String, nullable=False)
    nombre_proveedor = Column(String, nullable=False)
    
    compras_internas_exentas = Column(Float, default=0.0)
    internaciones_exentas = Column(Float, default=0.0)
    importaciones_exentas = Column(Float, default=0.0)
    compras_internas_gravadas = Column(Float, default=0.0)
    internaciones_gravadas_bienes = Column(Float, default=0.0)
    importaciones_gravadas_bienes = Column(Float, default=0.0)
    importaciones_gravadas_servicios = Column(Float, default=0.0)
    credito_fiscal = Column(Float, default=0.0)
    total_compras = Column(Float, default=0.0)
    
    # Nuevas casillas a partir de Feb 2024
    tipo_operacion = Column(String(1), nullable=True) # 1 Gravada, 2 No Gravada...
    clasificacion = Column(String(1), nullable=True) # 1 Costo, 2 Gasto
    sector = Column(String(1), nullable=True) # 1 Industria, 2 Comercio...
    tipo_costo_gasto = Column(String(1), nullable=True) # 1,2,3,4...
    
    # Payload crudo
    raw_json = Column(JSON, nullable=False)
    
    version = Column(Integer, default=1, nullable=False)
    omitido = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")

class DteVenta(Base):
    __tablename__ = "iva_dtes_ventas_cf"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), index=True, nullable=False)
    
    # Contexto
    periodo_mes = Column(String(2), nullable=False)
    periodo_anio = Column(String(4), nullable=False)
    
    fecha_emision = Column(String, nullable=False)
    clase_documento = Column(String, nullable=False, default="4")
    tipo_documento = Column(String, nullable=False, default="01")
    numero_resolucion = Column(String, nullable=False) # N/A para DTE
    serie_documento = Column(String, nullable=False) # N/A
    numero_control_del = Column(String, nullable=False) # N/A
    numero_control_al = Column(String, nullable=False) # N/A
    codigo_generacion = Column(String, nullable=False) # Máquina
    sello_recepcion = Column(String, nullable=False) # Control interno
    
    nit_cliente = Column(String, nullable=True)
    
    ventas_exentas = Column(Float, default=0.0)
    ventas_no_sujetas = Column(Float, default=0.0)
    ventas_gravadas = Column(Float, default=0.0)
    exportaciones = Column(Float, default=0.0)
    ventas_zona_franca = Column(Float, default=0.0)
    ventas_terceros = Column(Float, default=0.0)
    total_ventas = Column(Float, default=0.0)
    
    raw_json = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    omitido = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")


class DteAnulado(Base):
    __tablename__ = "iva_dtes_anulados"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), index=True, nullable=False)
    
    periodo_mes = Column(String(2), nullable=False)
    periodo_anio = Column(String(4), nullable=False)
    
    fecha_emision = Column(String, nullable=False)
    tipo_documento = Column(String, nullable=False)
    codigo_generacion = Column(String, nullable=False)
    sello_recepcion = Column(String, nullable=False)
    
    raw_json = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")

class DteVentaContribuyente(Base):
    __tablename__ = "iva_dtes_ventas_contribuyentes"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), index=True, nullable=False)
    
    periodo_mes = Column(String(2), nullable=False)
    periodo_anio = Column(String(4), nullable=False)
    
    fecha_emision = Column(String, nullable=False)
    clase_documento = Column(String, nullable=False, default="4")
    tipo_documento = Column(String, nullable=False, default="03")
    numero_resolucion = Column(String, nullable=False)
    serie_documento = Column(String, nullable=False)
    numero_documento = Column(String, nullable=False)
    numero_control_interno = Column(String, nullable=True)
    
    nit_nrc_cliente = Column(String, nullable=True)
    nombre_cliente = Column(String, nullable=False)
    
    ventas_exentas = Column(Float, default=0.0)
    ventas_no_sujetas = Column(Float, default=0.0)
    ventas_gravadas = Column(Float, default=0.0)
    debito_fiscal = Column(Float, default=0.0)
    ventas_terceros = Column(Float, default=0.0)
    debito_terceros = Column(Float, default=0.0)
    total_ventas = Column(Float, default=0.0)
    dui_cliente = Column(String, nullable=True)
    
    tipo_operacion = Column(String(1), nullable=True)
    tipo_ingreso = Column(String(2), nullable=True)
    
    raw_json = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    omitido = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")

class DeclaracionEstado(Base):
    __tablename__ = "iva_declaraciones_estado"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), nullable=False)
    anio = Column(String(4), nullable=False)
    mes = Column(String(2), nullable=False)
    tipo_libro = Column(String(50), nullable=False, default="compras")
    version = Column(Integer, default=1, nullable=False)
    declarado = Column(Boolean, default=False)
    numero_declaracion = Column(String, nullable=True)
    fecha_declaracion = Column(DateTime, default=datetime.utcnow)
    
    empresa = relationship("Empresa")

class Liquidacion(Base):
    __tablename__ = "iva_liquidaciones"

    __table_args__ = (
        UniqueConstraint("empresa_id", "anio", "mes", name="ux_iva_liquidaciones_empresa_periodo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), nullable=False)
    anio = Column(String(4), nullable=False)
    mes = Column(String(2), nullable=False)
    
    remanente_anterior = Column(Float, default=0.0)
    # Casilla 164: NULL indica saldo aún no conciliado; requiere migración SQL previa.
    excedente_impuesto_anterior = Column(Numeric(18, 2), nullable=True)
    retenciones_recibidas = Column(Float, default=0.0)
    percepciones_recibidas = Column(Float, default=0.0)
    retenciones_efectuadas = Column(Float, default=0.0)
    percepciones_efectuadas = Column(Float, default=0.0)
    anticipo_cuenta_2 = Column(Float, default=0.0)
    
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa = relationship("Empresa")



class Excedente164Auditoria(Base):
    """Procedencia de la casilla 164, pendiente de habilitación HTTP."""
    __tablename__ = "iva_excedentes_164_auditoria"

    __table_args__ = (
        UniqueConstraint("liquidacion_id", name="uq_excedentes_164_liquidacion"),
        UniqueConstraint("empresa_id", "anio", "mes", name="uq_excedentes_164_empresa_periodo"),
    )

    id = Column(Integer, primary_key=True)
    liquidacion_id = Column(Integer, ForeignKey("iva_liquidaciones.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("iva_usuarios.id"), nullable=False)
    anio = Column(String(4), nullable=False)
    mes = Column(String(2), nullable=False)
    importe = Column(Numeric(18, 2), nullable=False)
    origen = Column(String(32), nullable=False)
    referencia = Column(String(250), nullable=False)
    registrado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())



class DteRetencion(Base):
    __tablename__ = "iva_dtes_retenciones"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("iva_empresas.id"), index=True, nullable=False)
    
    periodo_mes = Column(String(2), nullable=False)
    periodo_anio = Column(String(4), nullable=False)
    
    # 9 Columnas Oficiales (Pagina 35 Manual F-07 V14 - Casilla 162)
    nit_agente = Column(String(14), nullable=True) # Col A: NIT Agente (14 digitos sin guiones)
    fecha_emision = Column(String(10), nullable=False) # Col B: DD/MM/AAAA
    tipo_documento = Column(String(2), nullable=False, default="07") # Col C: 07
    serie_documento = Column(String(100), nullable=True) # Col D: Sello MH
    numero_documento = Column(String(100), nullable=False) # Col E: Codigo de generacion sin guiones
    monto_sujeto = Column(Float, default=0.0) # Col F: Base imponible
    monto_retencion = Column(Float, default=0.0) # Col G: 1% retenido
    dui_agente = Column(String(9), nullable=True) # Col H: DUI si Col A esta vacia
    numero_anexo = Column(String(1), default="7") # Col I: Anexo 7 para Casilla 162
    
    nombre_agente = Column(String, nullable=True)
    raw_json = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    omitido = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")
