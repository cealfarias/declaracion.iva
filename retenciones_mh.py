import os
import re
import json
import glob
from datetime import datetime
import pandas as pd
import streamlit as st

# ===================== CONFIGURACIÓN DE LA PÁGINA =====================
st.set_page_config(
    page_title="Retenciones IVA 1% al Declarante (Casilla 162 - F-07)",
    layout="wide",
    page_icon="✂️"
)

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .stMetric { 
            background-color: #f8fafc !important; 
            padding: 16px !important; 
            border-radius: 10px !important; 
            border: 1px solid #e2e8f0 !important; 
        }
        [data-testid="stMetricLabel"] { color: #475569 !important; font-weight: 600 !important; }
        [data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 700 !important; }
        .mh-badge {
            background-color: #0284c7;
            color: white;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# ===================== DICCIONARIOS Y CONSTANTES =====================
RUTA_BASE = r"C:\Users\cealf\OneDrive\delcaraciones de IVA"

MESES_DICT = {
    1: "01 enero", 2: "02 febrero", 3: "03 marzo", 4: "04 abril", 5: "05 mayo", 
    6: "06 junio", 7: "07 julio", 8: "08 agosto", 9: "09 septiembre", 
    10: "10 octubre", 11: "11 noviembre", 12: "12 diciembre"
}

# Inicialización de Estados de Sesión
if 'datos_anexo_7' not in st.session_state:
    st.session_state.datos_anexo_7 = []
if 'omitidos_retencion' not in st.session_state:
    st.session_state.omitidos_retencion = []

# ===================== FUNCIONES AUXILIARES =====================
def cargar_json_seguro(fuente):
    """Carga un JSON ya sea desde una ruta de archivo o desde un buffer en memoria."""
    encodings = ['utf-8', 'utf-8-sig', 'windows-1252', 'latin-1', 'iso-8859-1']
    if isinstance(fuente, str):
        for enc in encodings:
            try:
                with open(fuente, 'r', encoding=enc) as f:
                    return json.load(f, strict=False)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            except Exception:
                return None
    else:
        # Buffer de archivo subido (BytesIO)
        raw_bytes = fuente.read()
        fuente.seek(0)
        for enc in encodings:
            try:
                texto = raw_bytes.decode(enc)
                return json.loads(texto, strict=False)
            except Exception:
                continue
    return None

def localizar_carpeta_compras(ruta_base, contribuyente, año, mes_num):
    """Localiza de manera inteligente la carpeta de compras tolerando variaciones tipográficas."""
    prefijo_mes = f"{mes_num:02d}"
    nombre_mes = MESES_DICT.get(mes_num, '').split()[1].lower() if mes_num in MESES_DICT else ''
    
    rutas_año = [
        os.path.join(ruta_base, contribuyente, "años", str(año)),
        os.path.join(ruta_base, contribuyente, "a\u00f1os", str(año)),
        os.path.join(ruta_base, contribuyente, str(año))
    ]
    
    for r_año in rutas_año:
        if not os.path.exists(r_año):
            continue
        try:
            subdirs = os.listdir(r_año)
        except Exception:
            continue
            
        for s in subdirs:
            s_lower = s.strip().lower()
            if s_lower.startswith(prefijo_mes) or (nombre_mes and nombre_mes in s_lower):
                carpeta_mes = os.path.join(r_año, s)
                candidatos = [
                    os.path.join(carpeta_mes, "Archivos de Trabajo compras y ventas", "compras"),
                    os.path.join(carpeta_mes, "Archivos de Trabajo compras y ventas", "COMPRAS"),
                    os.path.join(carpeta_mes, "compras"),
                    os.path.join(carpeta_mes, "COMPRAS"),
                    carpeta_mes
                ]
                for c in candidatos:
                    if os.path.exists(c):
                        return c
    return None

def procesar_dte_07(data, nombre_origen, año_sel, mes_num, permitir_anteriores=True):
    """
    Valida y extrae el registro de Retención 1% según la Página 35 del Manual F-07 V14:
    A: NIT Agente (14)
    B: Fecha de Emisión (10, DD/MM/AAAA)
    C: Tipo de Documento (2, '07')
    D: Serie (hasta 100, Sello de Recepción de MH)
    E: Número de Documento (hasta 100, Código de Generación sin guiones)
    F: Monto Sujeto (10, con 2 decimales)
    G: Monto Retención 1% (10, con 2 decimales)
    H: DUI Agente (9, si no tiene NIT)
    I: Número de Anexo (1, valor '7' para Casilla 162)
    """
    ident = data.get('identificacion', {}) or {}
    emisor = data.get('emisor', {}) or {}
    resumen = data.get('resumen', {}) or {}
    
    tipo_dte = str(ident.get('tipoDte', '')).strip()
    if tipo_dte != '07':
        return None, f"No es Comprobante de Retención (tipoDte: {tipo_dte or 'Desconocido'})"
        
    codigo_gen = ident.get('codigoGeneracion', '')
    codigo_gen_limpio = str(codigo_gen).replace('-', '').strip().upper() if codigo_gen else ''
    if not codigo_gen_limpio:
        return None, "Código de generación vacío"
        
    fecha_raw = ident.get('fecEmi', '')
    try:
        fecha_dte = datetime.strptime(fecha_raw[:10], '%Y-%m-%d')
    except Exception:
        return None, f"Formato de fecha inválido ({fecha_raw})"
        
    # Control de período tributario (período actual y hasta 3 meses previos)
    diff_meses = (año_sel - fecha_dte.year) * 12 + (mes_num - fecha_dte.month)
    if diff_meses < 0:
        return None, f"Fecha futura al período declarado ({fecha_raw[:10]})"
    if diff_meses > 3 and not permitir_anteriores:
        return None, f"DTE emitido hace más de 3 meses ({fecha_raw[:10]})"
        
    # Extracción del Sello de Recepción otorgado por Hacienda
    sello = (
        data.get('selloRecibido') or 
        data.get('respuestaMH', {}).get('selloRecibido') or 
        ident.get('selloRecibido') or 
        ''
    )
    sello_limpio = str(sello).strip()
    
    # Identificación del Agente Retenedor (El EMISOR del DTE 07)
    nit_raw = str(emisor.get('nit', '') or '').strip()
    nit_limpio = re.sub(r'[^0-9]', '', nit_raw)
    
    dui_raw = str(emisor.get('dui', '') or '').strip()
    dui_limpio = re.sub(r'[^0-9]', '', dui_raw)
    
    # Columna A (NIT) y Columna H (DUI) son excluyentes
    if nit_limpio:
        nit_agente = nit_limpio.zfill(14)[-14:] if len(nit_limpio) <= 14 else nit_limpio
        dui_agente = ""
    elif dui_limpio:
        nit_agente = ""
        dui_agente = dui_limpio.zfill(9)[-9:] if len(dui_limpio) <= 9 else dui_limpio
    else:
        return None, "Agente sin NIT ni DUI registrado en emisor"
        
    # Valores monetarios: soporte DTE v1 (totalIVAretenido), DTE v2 (totalIvaRetenido), y cuerpoDocumento
    monto_sujeto = float(
        resumen.get('totalSujetoRetencion') or
        sum(float(item.get('montoSujetoGrav', 0.0) or 0.0) for item in data.get('cuerpoDocumento', [])) or
        0.0
    )
    monto_retencion = float(
        resumen.get('totalIvaRetenido') or
        resumen.get('totalIVAretenido') or
        sum(float(item.get('ivaRetenido', 0.0) or 0.0) for item in data.get('cuerpoDocumento', [])) or
        0.0
    )
    
    if monto_sujeto <= 0 and monto_retencion <= 0:
        return None, "Montos de retención en cero o inválidos"
        
    # Si viene monto sujeto pero el monto de retención no vino desglosado o dio 0, calculamos el 1% oficial
    if monto_retencion <= 0 and monto_sujeto > 0:
        monto_retencion = round(monto_sujeto * 0.01, 2)
        
    # Verificación de tasa del 1%
    pct = round((monto_retencion / monto_sujeto) * 100, 2) if monto_sujeto > 0 else 0.0
    if not (0.5 <= pct <= 1.5):
        return None, f"La tasa de retención no corresponde al 1% (calculado: {pct}%)"
            
    fecha_formateada = fecha_dte.strftime('%d/%m/%Y')
    
    registro = {
        'A': nit_agente,
        'B': fecha_formateada,
        'C': '07',
        'D': sello_limpio,
        'E': codigo_gen_limpio,
        'F': f"{monto_sujeto:.2f}",
        'G': f"{monto_retencion:.2f}",
        'H': dui_agente,
        'I': '7',  # Número de Anexo oficial para Casilla 162
        # Metadatos para visualización
        '_agente_nombre': emisor.get('nombre', 'Agente Retenedor'),
        '_monto_sujeto_num': monto_sujeto,
        '_monto_ret_num': monto_retencion,
        '_archivo': nombre_origen,
        '_codigo_gen': codigo_gen_limpio
    }
    return registro, None

# ===================== SIDEBAR: PARÁMETROS =====================
if os.path.exists(RUTA_BASE):
    contribuyentes_disponibles = sorted([
        f for f in os.listdir(RUTA_BASE) 
        if os.path.isdir(os.path.join(RUTA_BASE, f)) and not f.startswith(('.', '_'))
    ])
else:
    contribuyentes_disponibles = []

with st.sidebar:
    st.header("⚙️ Período de Declaración")
    
    año_sel = st.number_input("Año Fiscal:", min_value=2000, max_value=2100, value=2026, step=1)
    mes_num = st.selectbox("Mes a Declarar:", options=list(MESES_DICT.keys()), format_func=lambda x: MESES_DICT[x].upper(), index=5)
    
    st.divider()
    st.subheader("📑 Normativa MH - F-07 V14")
    st.caption("""
    **Anexo 7 (Casilla 162):**
    Retención IVA del 1% efectuada al declarante por Agentes de Retención.
    Estructura de 9 columnas (A hasta I) delimitadas por punto y coma (`;`), sin encabezados.
    """)
    
    permitir_anteriores = st.checkbox("Aceptar retenciones de hasta 3 meses anteriores", value=True, help="Permite incluir retenciones emitidas en períodos anteriores pendientes de deducir.")

# ===================== INTERFAZ PRINCIPAL =====================
st.markdown('<span class="mh-badge">MINISTERIO DE HACIENDA · EL SALVADOR · F-07 V14 (PÁGINA 35)</span>', unsafe_allow_html=True)
st.title("✂️ Generador Anexo Retención IVA 1% Efectuada al Declarante (Casilla 162)")
st.caption("Procesa Documentos Tributarios Electrónicos tipo 07 (Comprobante de Retención) y genera el archivo CSV oficial para carga en el portal de Hacienda.")
st.divider()

tab_carpetas, tab_subida = st.tabs(["📁 Escanear Carpetas del Contribuyente", "📤 Subir Archivos DTE (Arrastrar y Soltar)"])

# ----------------- TAB 1: CARPETAS LOCALES -----------------
with tab_carpetas:
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        if contribuyentes_disponibles:
            contribuyente_sel = st.selectbox("Selecciona la Carpeta del Contribuyente:", options=contribuyentes_disponibles, key="sel_contribuyente")
        else:
            contribuyente_sel = None
            st.warning(f"No se detectaron carpetas de clientes en `{RUTA_BASE}`.")
            
    with col_c2:
        escanear_3_meses = st.checkbox("Escanear automáticamente carpetas de meses previos", value=True, key="esc_3m")

    carpetas_a_procesar = []
    if contribuyente_sel:
        # Mes actual
        c_actual = localizar_carpeta_compras(RUTA_BASE, contribuyente_sel, año_sel, mes_num)
        if c_actual:
            carpetas_a_procesar.append((año_sel, mes_num, 0, c_actual, "Mes Actual"))
            
        if escanear_3_meses:
            for diff in [1, 2, 3]:
                m_ant = mes_num - diff
                y_ant = año_sel
                if m_ant <= 0:
                    m_ant += 12
                    y_ant -= 1
                c_ant = localizar_carpeta_compras(RUTA_BASE, contribuyente_sel, y_ant, m_ant)
                if c_ant and c_ant != c_actual and all(c_ant != item[3] for item in carpetas_a_procesar):
                    carpetas_a_procesar.append((y_ant, m_ant, diff, c_ant, f"{diff} mes(es) antes"))
                    
        st.write("##### 📂 Carpetas detectadas:")
        if carpetas_a_procesar:
            for y, m, diff, ruta_f, etq in carpetas_a_procesar:
                n_jsons = len(glob.glob(os.path.join(ruta_f, "*.json")) + glob.glob(os.path.join(ruta_f, "*.JSON")))
                st.caption(f"• **{MESES_DICT[m].upper()} {y}** ({etq}): `{ruta_f}` — **{n_jsons} JSONs**")
        else:
            st.error("No se localizó ninguna carpeta de compras para el período seleccionado.")

    btn_procesar_carpetas = st.button("🚀 Procesar Retenciones desde Carpetas", type="primary", disabled=(not contribuyente_sel or not carpetas_a_procesar), key="btn_proc_carp")

# ----------------- TAB 2: SUBIDA DIRECTA (DRAG & DROP) -----------------
with tab_subida:
    st.info("💡 Puedes arrastrar y soltar todos tus archivos `.json` de retención (o una carpeta con múltiples DTEs) directamente aquí:")
    archivos_subidos = st.file_uploader(
        "Arrastra los archivos JSON aquí:",
        type=['json'],
        accept_multiple_files=True,
        key="uploader_dtes"
    )
    if archivos_subidos:
        st.success(f"📎 **{len(archivos_subidos)}** archivos preparados para procesamiento.")
    btn_procesar_subidos = st.button("🚀 Procesar Archivos Subidos", type="primary", disabled=(not archivos_subidos), key="btn_proc_sub")

# ===================== PROCESAMIENTO =====================
if btn_procesar_carpetas or btn_procesar_subidos:
    st.session_state.datos_anexo_7 = []
    st.session_state.omitidos_retencion = []
    codigos_vistos = set()
    
    lista_fuentes = []
    if btn_procesar_carpetas and carpetas_a_procesar:
        for y, m, diff, ruta_c, etq in carpetas_a_procesar:
            raw_files = glob.glob(os.path.join(ruta_c, "*.json")) + glob.glob(os.path.join(ruta_c, "*.JSON"))
            for rf in sorted(list(set(raw_files))):
                lista_fuentes.append((rf, os.path.basename(rf)))
    elif btn_procesar_subidos and archivos_subidos:
        for af in archivos_subidos:
            lista_fuentes.append((af, af.name))
            
    if lista_fuentes:
        progreso = st.progress(0)
        for idx, (fuente, nombre) in enumerate(lista_fuentes):
            progreso.progress((idx + 1) / len(lista_fuentes))
            data = cargar_json_seguro(fuente)
            if not data:
                st.session_state.omitidos_retencion.append({
                    'archivo': nombre,
                    'codigo_generacion': 'N/A',
                    'motivo': 'Archivo JSON dañado o ilegible'
                })
                continue
                
            registro, motivo = procesar_dte_07(data, nombre, año_sel, mes_num, permitir_anteriores)
            if motivo:
                # Solo registramos en omitidos si es un DTE 07 con error, o si el usuario subió específicamente archivos
                if data.get('identificacion', {}).get('tipoDte') == '07' or btn_procesar_subidos:
                    cod_g = data.get('identificacion', {}).get('codigoGeneracion', 'N/A')
                    st.session_state.omitidos_retencion.append({
                        'archivo': nombre,
                        'codigo_generacion': cod_g,
                        'motivo': motivo
                    })
                continue
                
            codigo_gen = registro['_codigo_gen']
            if codigo_gen in codigos_vistos:
                st.session_state.omitidos_retencion.append({
                    'archivo': nombre,
                    'codigo_generacion': codigo_gen,
                    'motivo': 'Comprobante duplicado (mismo Código de Generación)'
                })
                continue
                
            codigos_vistos.add(codigo_gen)
            st.session_state.datos_anexo_7.append(registro)
            
        st.rerun()

# ===================== RESULTADOS Y EXPORTACIÓN =====================
if st.session_state.datos_anexo_7:
    df_completo = pd.DataFrame(st.session_state.datos_anexo_7)
    
    total_docs = len(df_completo)
    total_sujeto = df_completo['_monto_sujeto_num'].sum()
    total_retencion = df_completo['_monto_ret_num'].sum()
    
    st.subheader("📊 Resumen de Retenciones Procesadas")
    m1, m2, m3 = st.columns(3)
    m1.metric("Comprobantes Válidos", f"{total_docs}")
    m2.metric("Monto Sujeto Gravado", f"${total_sujeto:,.2f}")
    m3.metric("IVA Retenido 1% (Casilla 162)", f"${total_retencion:,.2f}")
    
    # Columnas oficiales para el archivo del Ministerio de Hacienda (A hasta I)
    columnas_oficiales = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
    df_hacienda = df_completo[columnas_oficiales].copy()
    
    # Vista interactiva amigable
    st.write("##### 📋 Detalle de Filas para el Anexo:")
    df_vista = df_completo[['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', '_agente_nombre', '_archivo']].copy()
    df_vista.columns = [
        'NIT Agente (A)', 'Fecha (B)', 'Tipo (C)', 'Serie/Sello (D)', 
        'No. Documento (E)', 'Monto Sujeto (F)', 'Retención 1% (G)', 
        'DUI Agente (H)', 'Anexo (I)', 'Nombre del Agente', 'Archivo Origen'
    ]
    st.dataframe(df_vista, use_container_width=True, height=280)
    
    # Generación estricta del archivo CSV según nota de Página 35:
    # "Sin encabezados o títulos de los datos a ingresar ni celdas combinadas"
    csv_bytes = df_hacienda.to_csv(index=False, header=False, sep=';', lineterminator='\r\n').encode('utf-8')
    
    nombre_archivo = f"Anexo7_Retencion1_Casilla162_{año_sel}_{mes_num:02d}.csv"
    
    col_d1, col_d2 = st.columns([2, 1])
    with col_d1:
        st.download_button(
            label=f"📥 Descargar CSV Oficial para Hacienda: {nombre_archivo}",
            data=csv_bytes,
            file_name=nombre_archivo,
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
    with col_c2:
        st.caption("✅ Delimitado por `;` | 9 columnas | Sin encabezados | UTF-8")
        
    st.success(f"Archivo listo con **{total_docs}** filas y un total a deducir en la Casilla 162 de **${total_retencion:,.2f}**.")

else:
    st.info("💡 Selecciona una carpeta de contribuyente y haz clic en **Procesar Retenciones** o arrastra los archivos JSON en la pestaña de subida.")

if st.session_state.omitidos_retencion:
    st.write("<br>", unsafe_allow_html=True)
    with st.expander(f"⚠️ Documentos Omitidos o con Observaciones ({len(st.session_state.omitidos_retencion)})", expanded=False):
        st.dataframe(pd.DataFrame(st.session_state.omitidos_retencion), use_container_width=True)
