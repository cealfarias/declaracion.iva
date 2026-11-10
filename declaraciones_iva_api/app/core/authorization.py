"""Autorización de acceso a datos tributarios por empresa.

La identidad proviene exclusivamente del JWT; los IDs de empresa se validan
contra vínculos activos antes de ejecutar la operación del router.
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import DteCompra, Usuario, UsuarioEmpresa
from app.routers.empresas import usuario_actual


async def autorizar_compras(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    params = request.path_params
    empresa_id = params.get("empresa_id")

    if empresa_id is None and "dte_id" in params:
        compra = db.query(DteCompra).filter(DteCompra.id == int(params["dte_id"])).first()
        if compra is None:
            raise HTTPException(status_code=404, detail="Compra no encontrada.")
        empresa_id = compra.empresa_id

    if empresa_id is None and request.url.path.endswith("/upload"):
        # Starlette conserva el formulario para que FastAPI lo procese después.
        form = await request.form()
        empresa_id = form.get("empresa_id")

    if empresa_id is None:
        raise HTTPException(status_code=400, detail="Falta identificar la empresa.")

    try:
        empresa_id = int(empresa_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Identificador de empresa inválido.")

    vinculo = db.query(UsuarioEmpresa).filter(
        UsuarioEmpresa.usuario_id == usuario.id,
        UsuarioEmpresa.empresa_id == empresa_id,
        UsuarioEmpresa.archivado.is_(False),
    ).first()
    if vinculo is None:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa.")


async def autorizar_empresa_tributaria(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """Verifica la empresa en rutas, formularios y registros con ID propio."""
    from app.models.models import DteVentaContribuyente, DteAnulado

    if request.url.path == "/api/v1/anulados/consultar-mh":
        return  # Consulta externa sin empresa: requiere JWT, no vínculo.
    params = request.path_params
    empresa_id = params.get("empresa_id")
    if empresa_id is None and "id" in params:
        registro = db.query(DteVentaContribuyente).filter(
            DteVentaContribuyente.id == int(params["id"])
        ).first()
        if registro is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado.")
        empresa_id = registro.empresa_id
    if empresa_id is None and "anulado_id" in params:
        registro = db.query(DteAnulado).filter(
            DteAnulado.id == int(params["anulado_id"])
        ).first()
        if registro is None:
            raise HTTPException(status_code=404, detail="Documento no encontrado.")
        empresa_id = registro.empresa_id
    if empresa_id is None and request.url.path.endswith("/upload"):
        form = await request.form()
        empresa_id = form.get("empresa_id")
    if empresa_id is None:
        raise HTTPException(status_code=400, detail="Falta identificar la empresa.")
    try:
        empresa_id = int(empresa_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Identificador de empresa inválido.")
    vinculo = db.query(UsuarioEmpresa).filter(
        UsuarioEmpresa.usuario_id == usuario.id,
        UsuarioEmpresa.empresa_id == empresa_id,
        UsuarioEmpresa.archivado.is_(False),
    ).first()
    if vinculo is None:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa.")
