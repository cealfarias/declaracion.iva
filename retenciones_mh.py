import os
import json
import pandas as pd
from datetime import datetime
import glob
import streamlit as st

# ===================== FUNCIÓN SEGURA PARA CARGAR JSON =====================
def cargar_json_seguro(ruta):
    encodings = ['utf-8', 'utf-8-sig', 'windows-1252', 'latin-1', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(ruta, 'r', encoding=enc) as f:
                return json.load(f, strict=False)
        except UnicodeDecodeError:
            continue
        except json.JSONDecodeError:
            continue
        except Exception:
            return None
    return None

# ===================== CONFIGURACIÓN DE LA PÁGINA =====================
st.set_page_config(page_title="Retenciones 1% AL Declarante (Anexo 7)", layout="wide", page_icon="✂️")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stMetric { 
            background-color: #f1f5f9 !important; 
            padding: 15px !important; 
            border-radius: 10px !important; 
            border: 1px solid #cbd5e1 !important; 
        }
        [data-testid="stMetricLabel"] { color: #334155 !important; font-weight: 600 !important; }
        [data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 700 !important; }
    </style>
""", unsafe_allow_html=True)

# ===================== CONFIGURACIÓN DE TU RAÍZ GENERAL =====================
RUTA_BASE = r"C:\Users\cealf\OneDrive\delcaraciones de IVA"

if os.path.exists(RUTA_BASE):
    contribuyentes_disponibles = [f for f in os.listdir(RUTA_BASE) if os.path.isdir(os.path.join(RUTA_BASE, f)) and not f.startswith(('.', '_'))]
else:
    contribuyentes_disponibles = []

# Inicialización de Estados
if 'datos_anexo_7' not in st.session_state:
    st.session_state.datos_anexo_7 = []
if 'omitidos_retencion' not in st.session_state:
    st.session_state.omitidos_retencion = []

# ===================== SIDEBAR: CONTROL TRIBUTARIO =====================
with st.sidebar:
    st.header("⚙️ Parámetros de Retención")
    
    if not contribuyentes_disponibles:
        st.error(f"❌ No se encontró la raíz en: `{RUTA_BASE}`")
        contribuyente_sel = None
    else:
        contribuyente_sel = st.selectbox("1. Selecciona Carpeta Cliente:", options=contribuyentes_disponibles)
    
    st.divider()
    st.subheader("📅 Línea de Tiempo")
    
    año_sel = st.number_input("2. Año Fiscal:", min_value=2000, max_value=2100, value=2026)
    
    meses_dict = {
        1: "01 enero", 2: "02 febrero", 3: "03 marzo", 4: "04 abril", 5: "05 mayo", 
        6: "06 junio", 7: "07 julio", 8: "08 agosto", 9: "09 septiembre", 
        10: "10 octubre", 11: "11 noviembre", 12: "12 diciembre"
    }
    
    mes_num = st.selectbox("3. Mes de Declaración:", options=list(meses_dict.keys()), format_func=lambda x: meses_dict[x].upper())
    
    if contribuyente_sel:
        carpeta_final_compras = os.path.join(RUTA_BASE, contribuyente_sel, "años", str(año_sel), meses_dict[mes_num], "Archivos de Trabajo compras y ventas", "compras")
        st.session_state.carpeta_fuente = carpeta_final_compras
        
        st.markdown("---")
        st.markdown("##### 📍 Ruta Objetivo Detectada:")
        st.caption(f"`{st.session_state.carpeta_fuente}`")
        
        if os.path.exists(st.session_state.carpeta_fuente):
            jsons_raw = glob.glob(os.path.join(st.session_state.carpeta_fuente, "*.json")) + glob.glob(os.path.join(st.session_state.carpeta_fuente, "*.JSON"))
            jsons = sorted(list(set(jsons_raw)))
            st.success(f"📂 Conectado: {len(jsons)} JSONs encontrados.")
        else:
            st.error("🚫 Directorio no encontrado.")

    st.markdown("<br>", unsafe_allow_html=True)
    procesar = st.button("🚀 Generar Anexo 7 (Retención 1%)", type="primary", width='stretch', disabled=(not contribuyente_sel or not os.path.exists(st.session_state.carpeta_fuente)))

# ===================== MÓDULO DE PROCESAMIENTO =====================
if procesar and contribuyente_sel:
    st.session_state.datos_anexo_7 = []
    st.session_state.omitidos_retencion = []
    
    archivos_raw = glob.glob(os.path.join(st.session_state.carpeta_fuente, "*.json")) + glob.glob(os.path.join(st.session_state.carpeta_fuente, "*.JSON"))
    archivos = sorted(list(set(archivos_raw)))
    
    codigos_vistos = {}
    barra = st.progress(0)
    
    for i, ruta in enumerate(archivos):
        barra.progress((i + 1) / len(archivos))
        nombre = os.path.basename(ruta)
        motivo = ""
        
        data = cargar_json_seguro(ruta)
        if data is None:
            continue
        
        ident = data.get('identificacion', {})
        emisor = data.get('emisor', {})
        resumen = data.get('resumen', {})
        
        tipo = ident.get('tipoDte', '')
        
        # Filtro estricto: Solo procesar Comprobantes de Retención (07)
        if tipo != '07':
            continue
            
        fecha_raw = ident.get('fecEmi', '')
        codigo_gen = ident.get('codigoGeneracion', '')
        codigo_gen_limpio = str(codigo_gen).replace('-', '').strip().upper() if codigo_gen else ''
        
        # El sello viene en la raíz como "selloRecibido" en tu estructura real
        sello_recepcion = data.get('selloRecibido', '0000000000000000000000000000000000000000') 
        
        if not codigo_gen_limpio:
            motivo = "Código de generación vacío"
        elif codigo_gen_limpio in codigos_vistos:
            motivo = "Código duplicado en retenciones"
        
        try:
            fecha_dte = datetime.strptime(fecha_raw[:10], '%Y-%m-%d')
            meses_diferencia = (año_sel - fecha_dte.year) * 12 + (mes_num - fecha_dte.month)
            if meses_diferencia < 0 or meses_diferencia > 3:
                motivo = f"DTE fuera de rango temporal ({fecha_raw[:10]})"
        except Exception:
            motivo = "Fallo al parsear fecha"
            
        if motivo:
            st.session_state.omitidos_retencion.append({'archivo': nombre, 'motivo': motivo, 'codigo': codigo_gen_limpio})
            continue
            
        codigos_vistos[codigo_gen_limpio] = True
        
        # Extracción de valores monetarios
        monto_sujeto = resumen.get('totalSujetoRetencion', 0.0) or 0.0
        monto_retencion = resumen.get('totalIVAretenido', 0.0) or 0.0
        
        # LÓGICA CORREGIDA: Identificación del Agente de Retención (El EMISOR del DTE)
        nit_agente = str(emisor.get('nit', '')).replace('-', '').strip()
        dui_agente = str(emisor.get('dui', '')).replace('-', '').strip() if emisor.get('dui') else ''
        
        porcentaje_calculado = 0
        if monto_sujeto > 0:
            porcentaje_calculado = round((monto_retencion / monto_sujeto) * 100, 2)
            
        fecha_str = fecha_dte.strftime('%d/%m/%Y')
        
        # Validamos que sea retención del 1%
        if 0.5 <= porcentaje_calculado <= 1.5:
            # ESTRUCTURA EXACTA ANEXO 7 (9 Columnas: A - I)
            registro_7 = {
                'A': nit_agente,
                'B': fecha_str,
                'C': tipo,
                'D': sello_recepcion,
                'E': codigo_gen_limpio,
                'F': round(monto_sujeto, 2),
                'G': round(monto_retencion, 2),
                'H': dui_agente,
                'I': '7'
            }
            st.session_state.datos_anexo_7.append(registro_7)
        else:
            st.session_state.omitidos_retencion.append({'archivo': nombre, 'motivo': f"No es retención del 1% (Calculado: {porcentaje_calculado}%)", 'codigo': codigo_gen_limpio})

    st.rerun()

# ===================== INTERFAZ DE EXPORTACIÓN =====================
st.title("✂️ Anexo 7 - Retenciones IVA 1% Efectuadas al Declarante")
st.markdown("---")

if st.session_state.datos_anexo_7:
    df_7 = pd.DataFrame(st.session_state.datos_anexo_7)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Documentos", len(df_7))
    col2.metric("Monto Sujeto Total", f"${df_7['F'].sum():,.2f}")
    col3.metric("IVA Retenido Total (1%)", f"${df_7['G'].sum():,.2f}")
    
    # Renombrar columnas para visualización amigable
    df_visual = df_7.copy()
    df_visual.columns = ['NIT Agente (A)', 'Fecha (B)', 'Tipo (C)', 'Sello/Serie (D)', 'Código/Doc (E)', 'Monto Sujeto (F)', 'Retención 1% (G)', 'DUI Agente (H)', 'Anexo (I)']
    
    st.dataframe(df_visual, height=300, width='stretch')
    
    csv_7 = df_7.to_csv(index=False, header=False, sep=';').rstrip('\r\n').encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV Anexo 7 Oficial (Casilla 162)",
        data=csv_7,
        file_name=f"Anexo7_Retencion1_AlDeclarante_{año_sel}_{mes_num}.csv",
        mime="text/csv",
        width='stretch'
    )
else:
    st.info("💡 Haz clic en **🚀 Generar Anexo 7** en la barra lateral para procesar las retenciones.")

if st.session_state.omitidos_retencion:
    st.write("<br><br>", unsafe_allow_html=True)
    with st.expander(f"⚠️ Archivos tipo '07' omitidos o con errores ({len(st.session_state.omitidos_retencion)})", expanded=False):
        st.dataframe(pd.DataFrame(st.session_state.omitidos_retencion), width='stretch')