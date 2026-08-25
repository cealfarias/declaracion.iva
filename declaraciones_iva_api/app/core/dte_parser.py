import json
from datetime import datetime

def format_date(date_str):
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return date_str

def parse_compras(dte: dict):
    """
    Convierte JSON DTE a la fila de CSV para Anexo 3 (Compras)
    Utilizando exactamente las reglas de negocio provistas por el usuario.
    """
    ident = dte.get("identificacion", {})
    emisor = dte.get("emisor", {})
    resumen = dte.get("resumen", {})
    
    tipo = ident.get("tipoDte", "")
    fecha_raw = ident.get("fecEmi", "")
    fecha_csv = format_date(fecha_raw)
    
    codigo_gen = ident.get("codigoGeneracion", "")
    codigo_gen = str(codigo_gen).replace('-', '').strip().upper() if codigo_gen else ''
    
    # EXTRACCIÓN DE MONTOS
    iva = 0.0
    total_exenta = resumen.get('totalExenta', 0.0) or 0.0
    total_gravada = resumen.get('totalGravada', 0.0) or 0.0
    
    for trib in resumen.get('tributos', []) or []:
        if trib.get('codigo') == '20':
            iva = float(trib.get('valor', 0.0))
            break
            
    if iva == 0.0 and total_gravada > 0:
        iva = round(float(total_gravada) * 0.13, 2)
    
    # ASIGNACIÓN COLUMNAS MH
    g = h = i = j = k = l = m = 0.0
    if tipo in ['03', '05', '06', '11']:
        g = float(total_exenta)
        j = float(total_gravada)
    elif tipo == '12':
        i = float(total_exenta)
        l = float(total_gravada)
    elif tipo in ['13', '14']:
        i = float(total_exenta)
        m = float(total_gravada)
    else:
        # Default fallback
        g = float(total_exenta)
        j = float(total_gravada)
    
    total_compras_neto = g + h + i + j + k + l + m
    clase_doc = '4'
    
    if tipo == '14' and 'sujetoExcluido' in dte:
        prov_data = dte['sujetoExcluido'] or {}
    else:
        prov_data = emisor or {}
        
    nit_nrc = str(prov_data.get('nit', '') or prov_data.get('nrc', ''))
    nombre_prov = str(prov_data.get('nombre', '')).replace(';', ' ').replace('"', '').replace("'", "").strip().upper()
    
    dui = prov_data.get('dui', '') or prov_data.get('documento', '') or prov_data.get('numDocumento', '')
    dui_limpio = ''
    if dui:
        dui_str = str(dui).strip().replace('-', '').replace(' ', '')
        if dui_str.isdigit() and (8 <= len(dui_str) <= 9):
            dui_limpio = dui_str
    
    if dui_limpio:
        nit_nrc_final = ''
    else:
        nit_nrc_final = nit_nrc.replace('-','').replace('/','').strip()
        
    return [
        fecha_csv,              # A
        clase_doc,              # B
        tipo,                   # C
        codigo_gen,             # D
        nit_nrc_final,          # E
        nombre_prov,            # F
        f"{g:.2f}",             # G
        f"{h:.2f}",             # H
        f"{i:.2f}",             # I
        f"{j:.2f}",             # J
        f"{k:.2f}",             # K
        f"{l:.2f}",             # L
        f"{m:.2f}",             # M
        f"{iva:.2f}",           # N
        f"{total_compras_neto:.2f}", # O
        dui_limpio,             # P
        "1",                    # Q
        "2",                    # R
        "2",                    # S
        "2",                    # T
        "3"                     # U
    ]

def parse_ventas_contribuyente(dte: dict):
    ident = dte.get("identificacion", {})
    receptor = dte.get("receptor", {})
    resumen = dte.get("resumen", {})
    resp = dte.get("responseMH", {})
    
    fecha = format_date(ident.get("fecEmi", ""))
    clase = "4" # DTE
    tipo_doc = ident.get("tipoDte", "03")
    
    resolucion = ident.get("numeroControl", "").replace("-", "")
    serie = resp.get("selloRecibido", "")
    num_doc = ident.get("codigoGeneracion", "").replace("-", "")
    
    nit_cliente = str(receptor.get("nit", "")).replace("-", "")
    if not nit_cliente:
        nit_cliente = str(receptor.get("nrc", "")).replace("-", "")
        
    nombre_cliente = str(receptor.get("nombre", "")).replace(";", " ")
    
    exentas = float(resumen.get("totalExenta", 0))
    no_sujetas = float(resumen.get("totalNoSuj", 0))
    gravadas = float(resumen.get("totalGravada", 0))
    
    iva = 0.0
    for trib in resumen.get("tributos", []):
        if trib.get("codigo") == "20":
            iva += float(trib.get("valor", 0))
            
    total = float(resumen.get("montoTotalOperacion", 0))
    
    return [
        fecha, clase, tipo_doc, resolucion, serie, num_doc, "",
        nit_cliente, nombre_cliente,
        f"{exentas:.2f}", f"{no_sujetas:.2f}", f"{gravadas:.2f}",
        f"{iva:.2f}", "0.00", "0.00", f"{total:.2f}", "",
        "1", "3", "1"
    ]

def parse_ventas_consumidor(dte: dict):
    ident = dte.get("identificacion", {})
    resumen = dte.get("resumen", {})
    resp = dte.get("responseMH", {})
    
    fecha = format_date(ident.get("fecEmi", ""))
    clase = "4" 
    tipo_doc = ident.get("tipoDte", "01")
    
    resolucion = ident.get("numeroControl", "").replace("-", "")
    serie = resp.get("selloRecibido", "")
    num_doc = ident.get("codigoGeneracion", "").replace("-", "")
    
    exentas = float(resumen.get("totalExenta", 0))
    no_sujetas = float(resumen.get("totalNoSuj", 0))
    gravadas = float(resumen.get("totalGravada", 0))
    total = float(resumen.get("montoTotalOperacion", 0))
    
    return [
        fecha, clase, tipo_doc, resolucion, serie, "", "", num_doc, num_doc, "",
        f"{exentas:.2f}", "0.00", f"{no_sujetas:.2f}", f"{gravadas:.2f}",
        "0.00", "0.00", "0.00", "0.00", "0.00", f"{total:.2f}",
        "1", "3", "2"
    ]
