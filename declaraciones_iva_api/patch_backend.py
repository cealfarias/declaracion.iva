import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Modify consultar_periodo to look for remanente
consultar_pattern = '''
    dtes = db.query(DteProcesado).filter_by(periodo_id=periodo.id).all()
    if not dtes:
        return JSONResponse({"data": None})
'''
consultar_replacement = '''
    dtes = db.query(DteProcesado).filter_by(periodo_id=periodo.id).all()
    if not dtes:
        return JSONResponse({"data": None})
        
    remanente_anterior = 0.0
    for d in dtes:
        if d.tipo_documento == 'REMANENTE':
            remanente_anterior = d.datos_json.get('remanente_anterior', 0.0)
'''

code = code.replace(consultar_pattern, consultar_replacement)

# 2. Include remanente_anterior in the output
return_pattern = '''
    return JSONResponse({"data": resultado if len(resultado) > 0 else None})
'''
return_replacement = '''
    resultado["remanente_anterior"] = remanente_anterior
    return JSONResponse({"data": resultado if len(resultado) > 0 else None})
'''
code = code.replace(return_pattern, return_replacement)

# 3. Add the POST endpoint for saving remanente
new_endpoint = '''
from pydantic import BaseModel

class RemanenteRequest(BaseModel):
    mes: int
    anio: int
    usuario_id: int
    remanente_anterior: float

@router.post("/procesar/guardar-remanente")
async def guardar_remanente(req: RemanenteRequest, db: Session = Depends(get_db)):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=req.usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no vinculado")
    
    periodo = get_or_create_periodo(db, vinculo.empresa_id, req.anio, req.mes)
    
    # Buscar si ya hay un DTE de remanente
    dte_rem = db.query(DteProcesado).filter_by(periodo_id=periodo.id, tipo_documento='REMANENTE').first()
    if dte_rem:
        dte_rem.datos_json = {"remanente_anterior": req.remanente_anterior}
    else:
        dte_rem = DteProcesado(
            periodo_id=periodo.id,
            tipo_documento='REMANENTE',
            clasificacion='ajuste',
            datos_json={"remanente_anterior": req.remanente_anterior}
        )
        db.add(dte_rem)
        
    db.commit()
    return {"message": "Remanente guardado con éxito"}
'''

if 'guardar_remanente' not in code:
    code += new_endpoint

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Backend patched")
