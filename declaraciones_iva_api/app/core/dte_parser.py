import json
from datetime import datetime

def format_date(date_str):
    # Convierte "2026-07-16" a "16/07/2026"
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return date_str

def parse_compras(dte: dict):
    """
    Convierte JSON DTE a la fila de CSV para Anexo 3 (Compras)
    """
    ident = dte.get("identificacion", {})
    emisor = dte.get("emisor", {})
    resumen = dte.get("resumen", {})
    
    fecha = format_date(ident.get("fecEmi", ""))
    clase = "4" # DTE
    tipo_doc = ident.get("tipoDte", "")
    
    # D: Código de Generación sin guiones para DTE en Compras
    num_doc = ident.get("codigoGeneracion", "").replace("-", "")
    
    nit_prov = emisor.get("nit", "").replace("-", "")
    nombre_prov = emisor.get("nombre", "")
    
    compras_exentas = resumen.get("totalNoSuj", 0) + resumen.get("totalExenta", 0)
    compras_gravadas = resumen.get("totalGravada", 0)
    
    # Buscar IVA (Código 20)
    iva = 0.0
    for trib in resumen.get("tributos", []):
        if trib.get("codigo") == "20":
            iva += trib.get("valor", 0)
            
    total = resumen.get("montoTotalOperacion", 0)
    
    return [
        fecha,                      # A. FECHA
        clase,                      # B. CLASE DOC
        tipo_doc,                   # C. TIPO DOC
        num_doc,                    # D. NUM DOCUMENTO (Cod Generacion)
        nit_prov,                   # E. NIT PROVEEDOR
        nombre_prov,                # F. NOMBRE PROVEEDOR
        f"{compras_exentas:.2f}",   # G. COMPRAS EXENTAS / NO SUJETAS
        "0.00",                     # H. INTERNACIONES EXENTAS
        "0.00",                     # I. IMPORTACIONES EXENTAS
        f"{compras_gravadas:.2f}",  # J. COMPRAS GRAVADAS
        "0.00",                     # K. INTERNACIONES GRAVADAS
        "0.00",                     # L. IMPORTACIONES GRAVADAS
        "0.00",                     # M. IMPORTACIONES SERVICIOS
        f"{iva:.2f}",               # N. CREDITO FISCAL (IVA)
        f"{total:.2f}",             # O. TOTAL COMPRAS
        "",                         # P. DUI
        "1",                        # Q. TIPO OPERACION (1=Gravada)
        "2",                        # R. CLASIFICACION (2=Gasto)
        "2",                        # S. SECTOR (2=Comercio)
        "2",                        # T. TIPO COSTO/GASTO (2=Administracion)
        "3"                         # U. NUMERO ANEXO (3)
    ]

def parse_ventas_contribuyente(dte: dict):
    """
    Convierte JSON DTE a la fila de CSV para Anexo 1 (Ventas a Contribuyentes)
    """
    ident = dte.get("identificacion", {})
    receptor = dte.get("receptor", {})
    resumen = dte.get("resumen", {})
    resp = dte.get("responseMH", {})
    
    fecha = format_date(ident.get("fecEmi", ""))
    clase = "4" # DTE
    tipo_doc = ident.get("tipoDte", "03")
    
    # Resolucion = Numero de Control sin guiones para DTE
    resolucion = ident.get("numeroControl", "").replace("-", "")
    # Serie = Sello de recepcion
    serie = resp.get("selloRecibido", "")
    # Numero Doc = Codigo Generacion sin guiones
    num_doc = ident.get("codigoGeneracion", "").replace("-", "")
    
    nit_cliente = receptor.get("nit", "").replace("-", "")
    if not nit_cliente:
        nit_cliente = receptor.get("nrc", "").replace("-", "")
        
    nombre_cliente = receptor.get("nombre", "")
    
    exentas = resumen.get("totalExenta", 0)
    no_sujetas = resumen.get("totalNoSuj", 0)
    gravadas = resumen.get("totalGravada", 0)
    
    iva = 0.0
    for trib in resumen.get("tributos", []):
        if trib.get("codigo") == "20":
            iva += trib.get("valor", 0)
            
    total = resumen.get("montoTotalOperacion", 0)
    
    return [
        fecha,                   # A
        clase,                   # B
        tipo_doc,                # C
        resolucion,              # D
        serie,                   # E
        num_doc,                 # F
        "",                      # G. Num Control Interno (Blanco para DTE)
        nit_cliente,             # H
        nombre_cliente,          # I
        f"{exentas:.2f}",        # J
        f"{no_sujetas:.2f}",     # K
        f"{gravadas:.2f}",       # L
        f"{iva:.2f}",            # M. DEBITO FISCAL
        "0.00",                  # N. VENTAS A TERCEROS
        "0.00",                  # O. DEBITO TERCEROS
        f"{total:.2f}",          # P. TOTAL
        "",                      # Q. DUI
        "1",                     # R. TIPO OPERACION (1=Gravada)
        "3",                     # S. TIPO INGRESO (3=Comerciales)
        "1",                     # T. ANEXO (1)
    ]

def parse_ventas_consumidor(dte: dict):
    """
    Convierte JSON DTE a la fila de CSV para Anexo 2 (Ventas a Consumidor Final)
    """
    ident = dte.get("identificacion", {})
    resumen = dte.get("resumen", {})
    resp = dte.get("responseMH", {})
    
    fecha = format_date(ident.get("fecEmi", ""))
    clase = "4" # DTE
    tipo_doc = ident.get("tipoDte", "01")
    
    # D: Resolución = Número de Control sin guiones para DTE
    resolucion = ident.get("numeroControl", "").replace("-", "")
    # E: Serie = Sello de recepcion
    serie = resp.get("selloRecibido", "")
    # H e I: Número Doc DEL / AL = Código de Generación sin guiones
    num_doc = ident.get("codigoGeneracion", "").replace("-", "")
    
    exentas = resumen.get("totalExenta", 0)
    no_sujetas = resumen.get("totalNoSuj", 0)
    gravadas = resumen.get("totalGravada", 0)
    total = resumen.get("montoTotalOperacion", 0)
    
    return [
        fecha,                   # A. FECHA DE EMISION
        clase,                   # B. CLASE DE DOCUMENTO
        tipo_doc,                # C. TIPO DE DOCUMENTO
        resolucion,              # D. NUMERO DE RESOLUCION
        serie,                   # E. SERIE DE DOCUMENTO
        "",                      # F. NUMERO DE CONTROL INTERNO (DEL)
        "",                      # G. NUMERO DE CONTROL INTERNO (AL)
        num_doc,                 # H. NUMERO DE DOCUMENTO (DEL)
        num_doc,                 # I. NUMERO DE DOCUMENTO (AL)
        "",                      # J. N DE MAQUINA REGISTRADORA
        f"{exentas:.2f}",        # K. VENTAS EXENTAS
        "0.00",                  # L. VENTAS INTERNAS EXENTAS NO SUJETAS A PROPORCIONALIDAD
        f"{no_sujetas:.2f}",     # M. VENTAS NO SUJETAS
        f"{gravadas:.2f}",       # N. VENTAS GRAVADAS LOCALES
        "0.00",                  # O. EXPORTACIONES DENTRO DE CA
        "0.00",                  # P. EXPORTACIONES FUERA DE CA
        "0.00",                  # Q. EXPORTACIONES DE SERVICIOS
        "0.00",                  # R. VENTAS A ZONAS FRANCAS Y DPA
        "0.00",                  # S. VENTAS A CUENTA DE TERCEROS NO DOMICILIADOS
        f"{total:.2f}",          # T. TOTAL VENTAS
        "1",                     # U. TIPO DE OPERACION (1=Gravada)
        "3",                     # V. TIPO DE INGRESO (3=Actividades Comerciales)
        "2"                      # W. NUMERO DE ANEXO (2)
    ]

