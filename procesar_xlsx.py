import os
import io
import csv
import pandas as pd
import streamlit as st
import glob
from datetime import datetime

st.set_page_config(page_title="Consolidador 3 Meses MH (Excel/CSV)", layout="wide", page_icon="📊")

RUTA_BASE = r"C:\Users\cealf\OneDrive\delcaraciones de IVA"

st.title("📊 Consolidador Multi-Reporte: Excel / CSV ➡️ Anexo 3 (Art. 63)")
st.markdown("Carga y consolida de un solo jalón los reportes de **Julio, Agosto y Septiembre** (o hasta 3 meses anteriores) para generar el Libro de Compras oficial F-930.")

MESES_DICT = {
    1: "01 enero", 2: "02 febrero", 3: "03 marzo", 4: "04 abril", 5: "05 mayo", 
    6: "06 junio", 7: "07 julio", 8: "08 agosto", 9: "09 septiembre", 
    10: "10 octubre", 11: "11 noviembre", 12: "12 diciembre"
}

# ===================== PARÁMETROS DEL PERÍODO =====================
col1, col2 = st.columns(2)
with col1:
    año_sel = st.number_input("📅 Año de la Declaración:", min_value=2000, max_value=2100, value=2026)
with col2:
    mes_num = st.selectbox("📅 Mes a Declarar:", options=list(MESES_DICT.keys()), index=8, format_func=lambda x: MESES_DICT[x].upper())

st.divider()

# ===================== FUENTE DE LOS REPORTES =====================
tab_upload, tab_carpetas = st.tabs(["📤 1. Arrastrar y Soltar Archivos (Recomendado)", "📁 2. Buscar en Carpetas del Disco"])

archivos_a_procesar = []

with tab_upload:
    st.info("💡 **Puedes seleccionar o arrastrar los 3 archivos de un solo** (ejemplo: reporte de Julio, Agosto y Septiembre en Excel o CSV).")
    uploaded_files = st.file_uploader(
        "Arrastra aquí tus archivos Excel o CSV descargados del Ministerio de Hacienda:",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True
    )
    if uploaded_files:
        for uf in uploaded_files:
            archivos_a_procesar.append(("uploaded", uf.name, uf))

with tab_carpetas:
    if os.path.exists(RUTA_BASE):
        clientes = [f for f in os.listdir(RUTA_BASE) if os.path.isdir(os.path.join(RUTA_BASE, f)) and not f.startswith(('.', '_'))]
    else:
        clientes = []
        
    cliente_sel = st.selectbox("Selecciona Cliente:", options=clientes)
    
    if cliente_sel:
        # Buscar en los 3 meses anteriores + mes actual
        periodos_buscar = []
        for diff in range(4): # 0, 1, 2, 3 meses
            m_calc = mes_num - diff
            y_calc = año_sel
            if m_calc <= 0:
                m_calc += 12
                y_calc -= 1
            periodos_buscar.append((y_calc, m_calc, diff))
            
        reportes_encontrados = []
        for y, m, diff in periodos_buscar:
            prefijo = f"{m:02d}"
            # Posibles rutas
            rutas_año = [
                os.path.join(RUTA_BASE, cliente_sel, "años", str(y)),
                os.path.join(RUTA_BASE, cliente_sel, "a\u00f1os", str(y)),
                os.path.join(RUTA_BASE, cliente_sel, str(y))
            ]
            for r_año in rutas_año:
                if not os.path.exists(r_año):
                    continue
                try:
                    for s in os.listdir(r_año):
                        if s.strip().startswith(prefijo) or MESES_DICT[m].split()[1].lower() in s.lower():
                            c_mes = os.path.join(r_año, s)
                            for sub_c in [os.path.join(c_mes, "Archivos de Trabajo compras y ventas", "compras"), os.path.join(c_mes, "compras")]:
                                if os.path.exists(sub_c):
                                    f_excel = glob.glob(os.path.join(sub_c, "*.xlsx")) + glob.glob(os.path.join(sub_c, "*.XLSX")) + glob.glob(os.path.join(sub_c, "*.csv")) + glob.glob(os.path.join(sub_c, "*.CSV"))
                                    for fe in f_excel:
                                        base = os.path.basename(fe)
                                        if not base.startswith(("Libro_Compras_NRC", "Anexo", "F07")):
                                            reportes_encontrados.append((fe, f"{MESES_DICT[m].upper()} ({diff} meses antes)"))
                except Exception:
                    pass
                    
        if reportes_encontrados:
            st.success(f"🔍 Se detectaron {len(reportes_encontrados)} reportes en las carpetas de los últimos meses:")
            for p, et in reportes_encontrados:
                st.caption(f"• `{os.path.basename(p)}` ({et})")
            if st.button("📥 Cargar estos reportes desde el disco"):
                for p, et in reportes_encontrados:
                    archivos_a_procesar.append(("disk", os.path.basename(p), p))
        else:
            st.caption("No se encontraron reportes automáticamente en las subcarpetas del cliente.")

# ===================== PARSER INTELIGENTE =====================
def parsear_reporte(file_item):
    """Lee un archivo Excel o CSV de Hacienda de forma dinámica detectando encabezados reales."""
    tipo_origen, nombre_archivo, fuente = file_item
    rows = []
    
    if nombre_archivo.lower().endswith(('.xlsx', '.xls')):
        import openpyxl
        try:
            if tipo_origen == "uploaded":
                wb = openpyxl.load_workbook(io.BytesIO(fuente.read()), data_only=True)
            else:
                wb = openpyxl.load_workbook(fuente, data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                rows.append([str(c) if c is not None else "" for c in row])
        except Exception as e:
            return None, f"Error leyendo Excel: {e}"
    else:
        # CSV
        raw_bytes = fuente.read() if tipo_origen == "uploaded" else open(fuente, 'rb').read()
        decoded = None
        for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']:
            try:
                decoded = raw_bytes.decode(enc)
                break
            except Exception:
                continue
        if decoded is None:
            return None, "Codificación de texto no soportada"
        reader = csv.reader(io.StringIO(decoded))
        rows = list(reader)
        
    header_idx = -1
    for idx, r in enumerate(rows[:25]):
        line_str = " ".join(r).lower()
        if "fecha de emision" in line_str or "fecha de emisión" in line_str:
            header_idx = idx
            break
            
    start_row = (header_idx + 2) if header_idx != -1 else 0
    return rows[start_row:], None

def is_item_num(val):
    try:
        f = float(str(val or '').strip())
        return f > 0 and (f == int(f))
    except Exception:
        return False

# ===================== PROCESAMIENTO =====================
if archivos_a_procesar:
    st.markdown("---")
    if st.button("🚀 Procesar y Consolidar Todos los Archivos", type="primary", width="stretch"):
        todos_anexo3 = []
        todos_sujeto_excluido = []
        omitidos = []
        docs_vistos = set()
        
        barra = st.progress(0)
        
        for file_idx, item in enumerate(archivos_a_procesar):
            barra.progress((file_idx + 1) / len(archivos_a_procesar))
            _, fname, _ = item
            rows, err = parsear_reporte(item)
            if err or not rows:
                omitidos.append({'archivo': fname, 'motivo': err or "Sin datos legibles"})
                continue
                
            for r in rows:
                try:
                    shift = 0
                    if len(r) > 1 and r[0].strip() == "" and is_item_num(r[1]):
                        shift = 1
                    elif is_item_num(r[0]):
                        shift = 0
                    else:
                        continue
                        
                    if len(r) <= shift + 10:
                        continue
                        
                    fecha_str_raw = str(r[shift + 1]).strip()
                    if not fecha_str_raw:
                        continue
                        
                    # Parsear fecha
                    try:
                        clean_date = fecha_str_raw.split()[0].split('T')[0]
                        if '-' in clean_date:
                            partes = clean_date.split('-')
                            f_obj = datetime(int(partes[0]), int(partes[1]), int(partes[2]))
                            fecha_emision = f"{partes[2]}/{partes[1]}/{partes[0]}"
                        elif '/' in clean_date:
                            partes = clean_date.split('/')
                            if len(partes[2]) == 4:
                                f_obj = datetime(int(partes[2]), int(partes[1]), int(partes[0]))
                                fecha_emision = clean_date
                            else:
                                f_obj = datetime.strptime(clean_date, "%d/%m/%Y")
                                fecha_emision = clean_date
                        else:
                            continue
                    except Exception:
                        continue
                        
                    # Validar Art. 63 (hasta 3 meses antes)
                    meses_diff = (año_sel - f_obj.year) * 12 + (mes_num - f_obj.month)
                    if meses_diff < 0:
                        omitidos.append({'archivo': fname, 'motivo': f'Fecha futura ({fecha_emision})'})
                        continue
                    elif meses_diff > 3:
                        omitidos.append({'archivo': fname, 'motivo': f'Excede los 3 meses legales ({fecha_emision}, {meses_diff} meses antes)'})
                        continue
                        
                    no_doc_raw = str(r[shift + 2]).strip()
                    num_doc = no_doc_raw.replace("-", "").upper() if no_doc_raw else ""
                    if not num_doc:
                        continue
                        
                    # Evitar duplicados si una compra se repite entre reportes
                    if num_doc in docs_vistos:
                        continue
                    docs_vistos.add(num_doc)
                    
                    nrc_prov = str(r[shift + 3]).strip()
                    nit_dui_excluido = str(r[shift + 4]).strip() if len(r) > shift + 4 else ""
                    nombre_prov = str(r[shift + 5]).replace(';', ' ').replace('"', '').strip() if len(r) > shift + 5 else ""
                    
                    def to_float(val_c):
                        try:
                            s = str(val_c).replace("$", "").replace(",", "").strip()
                            return float(s) if s else 0.0
                        except Exception:
                            return 0.0
                            
                    no_sujetas = to_float(r[shift + 6]) if len(r) > shift + 6 else 0.0
                    exentas = to_float(r[shift + 7]) if len(r) > shift + 7 else 0.0
                    import_exentas = to_float(r[shift + 8]) if len(r) > shift + 8 else 0.0
                    gravadas_int = to_float(r[shift + 9]) if len(r) > shift + 9 else 0.0
                    import_gravadas = to_float(r[shift + 10]) if len(r) > shift + 10 else 0.0
                    credito_fiscal = to_float(r[shift + 11]) if len(r) > shift + 11 else 0.0
                    total_compras = to_float(r[shift + 14]) if len(r) > shift + 14 else (gravadas_int + credito_fiscal + exentas)
                    sujetos_excluidos = to_float(r[shift + 15]) if len(r) > shift + 15 else 0.0
                    
                    es_sujeto_excluido = (sujetos_excluidos > 0 or (nit_dui_excluido and not nrc_prov))
                    
                    if es_sujeto_excluido:
                        tipo_dte = "14"
                        nit_proveedor = nit_dui_excluido.replace("-", "").strip()
                        tipo_op_default = "2"
                        total_exenta = sujetos_excluidos if sujetos_excluidos > 0 else (exentas or total_compras)
                        total_gravada = 0.0
                        iva = 0.0
                        dui_final = nit_proveedor if len(nit_proveedor) == 9 else ""
                        if dui_final:
                            nit_proveedor = ""
                    else:
                        tipo_dte = "03"
                        # Prioridad NIT
                        nit_proveedor = nit_dui_excluido.replace("-", "").strip() if (nit_dui_excluido and len(nit_dui_excluido) >= 14) else nrc_prov.replace("-", "").strip()
                        tipo_op_default = "1"
                        total_exenta = exentas + no_sujetas + import_exentas
                        total_gravada = gravadas_int + import_gravadas
                        iva = credito_fiscal
                        dui_final = ""
                        
                    antiguedad_label = "Mes Actual (M)" if meses_diff == 0 else f"{meses_diff} Mes(es) Antes"
                    
                    reg = {
                        'A': fecha_emision, 'B': '4', 'C': tipo_dte, 'D': num_doc,
                        'E': nit_proveedor, 'F': nombre_prov,
                        'G': round(total_exenta, 2), 'H': 0.0, 'I': 0.0, 'J': round(total_gravada, 2),
                        'K': 0.0, 'L': 0.0, 'M': 0.0,
                        'N': round(iva, 2), 'O': round(total_compras, 2), 'P': dui_final,
                        'Q': tipo_op_default, 'R': '1', 'S': '2', 'T': '5',
                        'U': '3' if not es_sujeto_excluido else '5',
                        'Periodo_DTE': antiguedad_label,
                        'Meses_Antiguedad': meses_diff,
                        'Archivo_Origen': fname
                    }
                    
                    if es_sujeto_excluido:
                        todos_sujeto_excluido.append(reg)
                    else:
                        todos_anexo3.append(reg)
                        
                except Exception:
                    continue
                    
        if todos_anexo3:
            df_res = pd.DataFrame(todos_anexo3)
            st.success(f"🎉 ¡Consolidación exitosa! Se extrajeron **{len(df_res)} compras válidas** en total para el Anexo 3.")
            
            # Tarjetas de auditoría Art. 63
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                sub0 = df_res[df_res['Meses_Antiguedad'] == 0]
                st.info(f"**Mes en Curso (M):**\n\n📄 **{len(sub0)} DTEs** | IVA: ${sub0['N'].sum():,.2f}")
            with c2:
                sub1 = df_res[df_res['Meses_Antiguedad'] == 1]
                st.success(f"**1 Mes Antes (M-1):**\n\n📄 **{len(sub1)} DTEs** | IVA: ${sub1['N'].sum():,.2f}")
            with c3:
                sub2 = df_res[df_res['Meses_Antiguedad'] == 2]
                st.success(f"**2 Meses Antes (M-2):**\n\n📄 **{len(sub2)} DTEs** | IVA: ${sub2['N'].sum():,.2f}")
            with c4:
                sub3 = df_res[df_res['Meses_Antiguedad'] == 3]
                st.success(f"**3 Meses Antes (M-3):**\n\n📄 **{len(sub3)} DTEs** | IVA: ${sub3['N'].sum():,.2f}")
                
            st.dataframe(df_res, width='stretch', height=350)
            
            # Exportación Anexo 3 de 21 columnas
            cols_21 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U']
            csv_str = df_res[cols_21].to_csv(index=False, header=False, sep=';', float_format='%.2f')
            csv_bytes = csv_str.rstrip('\r\n').encode('utf-8')
            
            st.download_button(
                f"📥 Descargar Libro de Compras Oficial Consolidado (Anexo 3)",
                data=csv_bytes,
                file_name=f"Anexo3_Compras_Consolidado_{año_sel}_{mes_num:02d}.csv",
                mime="text/csv",
                type="primary",
                width="stretch"
            )
        else:
            st.warning("No se encontraron compras válidas en los reportes proporcionados.")
            
        if todos_sujeto_excluido:
            st.divider()
            df_se = pd.DataFrame(todos_sujeto_excluido)
            st.warning(f"ℹ️ Se detectaron {len(df_se)} compras a Sujetos Excluidos. Por ley corresponden al **Anexo 5**:")
            cols_21 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U']
            csv_se = df_se[cols_21].to_csv(index=False, header=False, sep=';', float_format='%.2f').rstrip('\r\n').encode('utf-8')
            st.download_button(
                f"📥 Descargar Compras a Sujetos Excluidos (Anexo 5)",
                data=csv_se,
                file_name=f"Anexo5_Sujetos_Excluidos_{año_sel}_{mes_num:02d}.csv",
                mime="text/csv"
            )
            
        if omitidos:
            with st.expander(f"Ver advertencias u omisiones ({len(omitidos)})"):
                st.dataframe(pd.DataFrame(omitidos), width='stretch')
