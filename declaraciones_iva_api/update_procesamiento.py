import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace endpoint parameters
code = code.replace('usuario_id: int = Form(...)', 'empresa_id: int = Form(...)')
code = code.replace('usuario_id: int = Query(...)', 'empresa_id: int = Query(...)')

# Replace the db query
query_old = '''    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no tiene empresa vinculada")
        
    empresa = vinculo.empresa'''

query_new = '''    empresa = db.query(Empresa).filter_by(id=empresa_id).first()
    if not empresa: raise HTTPException(status_code=400, detail="Empresa no encontrada")'''

code = code.replace(query_old, query_new)

# For POST endpoints
query_old2 = '''    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo:
        raise HTTPException(status_code=400, detail="Usuario no vinculado")
        
    empresa = vinculo.empresa'''
query_new2 = '''    empresa = db.query(Empresa).filter_by(id=empresa_id).first()
    if not empresa: raise HTTPException(status_code=400, detail="Empresa no encontrada")'''

code = code.replace(query_old2, query_new2)

with open('app/routers/procesamiento.py', 'w', encoding='utf-8') as f:
    f.write(code)
