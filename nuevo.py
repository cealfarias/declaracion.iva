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
st.set_page_config(page_title="Libro de Compras MH - Multi NRC", layout="wide", page_icon="📊")

# CSS CORREGIDO
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
if 'datos_mes' not in st.session_state:
    st.session_state.datos_mes = []
if 'omitidos' not in st.session_state:
    st.session_state.omitidos = []
if 'vista' not in st.session_state:
    st.session_state.vista = "principal"

DTE_NOMBRES = {
    '01': '01 - Factura', '03': '03 - Crédito Fiscal', '05': '05 - Nota de Débito',
    '06': '06 - Nota de Crédito', '07': '07 - Comprobante de Retención',
    '08': '08 - Comprobante de Liquidación', '09': '09 - Doc. Contable de Liquidación',
    '11': '11 - Factura de Exportación', '12': '12 - Doc. Contable Liquidación',
    '13': '13 - Sujeto Excluido', '14': '14 - Factura Sujeto Excluido',
    '15': '15 - Comprobante de Donación'
}

# ===================== SIDEBAR: CONTROL TRIBUTARIO =====================
with st.sidebar:
    st.header("⚙️ Parámetros del Sistema")
    
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
            st.success(f"📂 Conectado: {len(jsons)} JSONs listos para procesar de forma única.")
        else:
            st.error("🚫 Directorio no encontrado.")

    st.markdown("<br>", unsafe_allow_html=True)
    procesar = st.button("🚀 Generar Libros de Compras", type="primary", width='stretch', disabled=(not contribuyente_sel or not os.path.exists(st.session_state.carpeta_fuente)))

# ===================== MÓDULO DE PROCESAMIENTO MULTI-NRC =====================
if procesar and contribuyente_sel:
    st.session_state.datos_mes = []
    st.session_state.omitidos = []
    
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
            st.session_state.omitidos.append({'archivo': nombre, 'tipo_dte': "99 - JSON Corrupto", 'motivo': "JSON inválido o vacío", 'RUTA_ORIGEN_INTERNA': ruta})
            continue
        
        ident = data.get('identificacion', {})
        receptor = data.get('receptor', {})
        emisor = data.get('emisor', {})
        resumen = data.get('resumen', {})
        
        tipo = ident.get('tipoDte', '')
        fecha_raw = ident.get('fecEmi', '')
        codigo_gen = ident.get('codigoGeneracion', '')
        codigo_gen = str(codigo_gen).replace('-', '').strip().upper() if codigo_gen else ''
        
        nrc_receptor_dte = str(receptor.get('nrc', 'SIN_NRC')).replace('-', '').replace('/', '').strip().upper()
        tipo_nombre_descriptivo = DTE_NOMBRES.get(tipo, f"{tipo} - Tipo No Común")
        
        if tipo not in ['03', '05', '06', '09', '11', '12', '13']:
            motivo = f"Tipo no compra ({tipo})"
        elif len(fecha_raw) < 10:
            motivo = "Error en longitud de fecha"
        elif not codigo_gen:
            motivo = "Código de generación vacío"
        elif codigo_gen in codigos_vistos:
            orig = codigos_vistos[codigo_gen]
            st.session_state.omitidos.append({
                'archivo': nombre,
                'tipo_dte': tipo_nombre_descriptivo,
                'motivo': 'Código duplicado',
                'codigo_gen': codigo_gen,
                'orig_archivo': orig['archivo'],
                'orig_fecha': orig['fecha'],
                'orig_nit': orig['nit'],
                'orig_nrc': orig['nrc'],
                'orig_nombre': orig['nombre'],
                'dup_archivo': nombre,
                'dup_fecha': fecha_raw[:10] if fecha_raw else 'N/A',
                'dup_nit': str(emisor.get('nit', 'N/A')),
                'dup_nrc': str(emisor.get('nrc', 'N/A')),
                'dup_nombre': str(emisor.get('nombre', 'N/A')),
                'RUTA_ORIGEN_INTERNA': ruta
            })
            continue
        else:
            try:
                fecha_dte = datetime.strptime(fecha_raw[:10], '%Y-%m-%d')
                
                # Calculamos la diferencia matemática en meses entre la declaración y el DTE
                meses_diferencia = (año_sel - fecha_dte.year) * 12 + (mes_num - fecha_dte.month)
                
                # Validamos según la Ley (Mes actual = 0, hasta 3 meses anteriores)
                if meses_diferencia < 0:
                    motivo = f"Fecha futura no válida ({fecha_raw[:10]})"
                elif meses_diferencia > 3:
                    motivo = f"DTE vencido, excede los 3 meses legales ({fecha_raw[:10]})"
            except Exception:
                motivo = "Fallo crítico al parsear fecha"
        
        if motivo:
            st.session_state.omitidos.append({'archivo': nombre, 'tipo_dte': tipo_nombre_descriptivo, 'motivo': motivo, 'RUTA_ORIGEN_INTERNA': ruta})
            continue
        
        codigos_vistos[codigo_gen] = {
            'archivo': nombre,
            'fecha': fecha_raw[:10] if fecha_raw else 'N/A',
            'nit': str(emisor.get('nit', 'N/A')),
            'nrc': str(emisor.get('nrc', 'N/A')),
            'nombre': str(emisor.get('nombre', 'N/A'))
        }

        # EXTRACCIÓN DE MONTOS
        iva = 0.0
        if tipo == '09':
            total_gravada = resumen.get('totalComision', 0.0) or resumen.get('comision', 0.0) or 0.0
            iva = resumen.get('ivaComision', 0.0) or 0.0
            total_exenta = 0.0
        else:
            total_exenta = resumen.get('totalExenta', 0.0) or 0.0
            total_gravada = resumen.get('totalGravada', 0.0) or 0.0
            for trib in resumen.get('tributos', []) or []:
                if trib.get('codigo') == '20':
                    iva = trib.get('valor', 0.0)
                    break
            if iva == 0.0 and total_gravada > 0:
                iva = round(total_gravada * 0.13, 2)
        
        # ASIGNACIÓN COLUMNAS MH
        g = h = i = j = k = l = m = 0.0
        if tipo in ['03', '05', '06', '11', '09']:
            g = total_exenta; j = total_gravada
        elif tipo == '12':
            i = total_exenta; l = total_gravada
        elif tipo == '13':
            i = total_exenta; m = total_gravada
        
        # Total compras neto requerido por MH en columna O (Suma de G a M)
        total_compras_neto = g + h + i + j + k + l + m
        
        clase_doc = '4'
        nit_nrc = str(emisor.get('nit', '') or emisor.get('nrc', ''))
        
        nombre_prov = str(emisor.get('nombre', '')).replace(';', ' ').replace('"', '').replace("'", "").strip().upper()
        dui = emisor.get('dui', '')
        
        dui_limpio = ''
        if dui:
            dui_str = str(dui).strip().replace('-', '').replace(' ', '')
            if dui_str.isdigit() and (8 <= len(dui_str) <= 9):
                dui_limpio = dui_str
        
        # Lógica estricta de exclusión mutua DUI vs NIT/NRC según normativa
        if dui_limpio:
            nit_nrc_final = ''
        else:
            nit_nrc_final = nit_nrc.replace('-','').replace('/','').strip()
        
        # 🌟 ESTRUCTURA LEGAL EXACTA MH (21 COLUMNAS: DE LA 'A' A LA 'U')
        # Configuración fija ajustada según manual MH (Costo Comercial)
        registro = {
            'A': fecha_dte.strftime('%d/%m/%Y'), 'B': clase_doc, 'C': tipo, 'D': codigo_gen,
            'E': nit_nrc_final, 'F': nombre_prov,
            'G': round(g, 2), 'H': round(h, 2), 'I': round(i, 2), 'J': round(j, 2),
            'K': round(k, 2), 'L': round(l, 2), 'M': round(m, 2),
            'N': round(iva, 2), 'O': round(total_compras_neto, 2), 'P': dui_limpio,
            'Q': '1', 'R': '1', 'S': '2', 'T': '5', 'U': '3',
            'RUTA_ORIGEN_INTERNA': ruta,
            'NRC_RECEPTOR_INTERNO': nrc_receptor_dte
        }
        st.session_state.datos_mes.append(registro)
    st.rerun()

# ===================== CUERPO CENTRAL (VISTA MULTI-CLIENTE) =====================
if st.session_state.vista == "principal":
    st.title("📊 Consolidador Multi-NRC - Ministerio de Hacienda")
    st.markdown("---")
    
    if st.session_state.datos_mes:
        df_completo = pd.DataFrame(st.session_state.datos_mes)
        lista_nrcs = sorted(df_completo['NRC_RECEPTOR_INTERNO'].unique())
        
        st.subheader("🏢 Distribución por Contribuyente Receptor")
        nrc_seleccionado = st.selectbox("Selecciona el NRC del libro que deseas revisar/exportar:", options=lista_nrcs)
        
        df_nrc_valores = df_completo[df_completo['NRC_RECEPTOR_INTERNO'] == nrc_seleccionado]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Documentos de este NRC", f"{len(df_nrc_valores)} DTEs")
        with col2:
            total_gravado = df_nrc_valores['J'].sum() + df_nrc_valores['L'].sum() + df_nrc_valores['M'].sum()
            st.metric("Total Gravado", f"${total_gravado:,.2f}")
        with col3:
            total_iva = df_nrc_valores['N'].sum()
            st.metric("Crédito Fiscal (IVA)", f"${total_iva:,.2f}")
        with col4:
            total_general = df_nrc_valores['O'].sum()
            st.metric("Total de Compras (Neto MH)", f"${total_general:,.2f}")
            
        st.write("<br>", unsafe_allow_html=True)
        st.markdown(f"### 📋 Registros para NRC: `{nrc_seleccionado}`")
        
        df_visual = df_nrc_valores.copy()
        df_visual.columns = [
            'Fecha Emisión (A)', 'Clase (B)', 'Tipo DTE (C)', 'Cód. Generación (D)',
            'NIT/NRC Emisor (E)', 'Nombre Proveedor (F)', 'Exenta Int (G)', 'Exenta Imp (H)',
            'Exenta Rec (I)', 'Gravada Int (J)', 'Gravada Imp (K)', 'Gravada Almacén (L)',
            'Gravada Sujeto Excl (M)', 'IVA (N)', 'Total Documento (O)', 'DUI (P)', 
            'Tipo Operación (Q)', 'Clasificación (R)', 'Sector (S)', 'Tipo Costo/Gasto (T)', 'Anexo (U)', 
            'RUTA_ORIGEN_INTERNA', 'NRC_RECEPTOR_INTERNO'
        ]
        
        df_final_clean = df_visual.drop(columns=['RUTA_ORIGEN_INTERNA', 'NRC_RECEPTOR_INTERNO'])
        st.dataframe(df_final_clean, width='stretch', height=350)
        
        st.write("<br>", unsafe_allow_html=True)
        
        # 🌟 EXPORTACIÓN OFICIAL E ESTRICTA EXIGIDA POR MINISTERIO DE HACIENDA:
        csv_string = df_final_clean.to_csv(index=False, header=False, sep=';')
        
        # Eliminamos saltos de línea al final del string antes de enviar a bytes (Evita fila vacía al final)
        csv_data = csv_string.rstrip('\r\n').encode('utf-8')
        
        st.download_button(
            label=f"📥 Descargar Libro de Compras Oficial para NRC: {nrc_seleccionado}",
            data=csv_data,
            file_name=f"Libro_Compras_NRC_{nrc_seleccionado}_{año_sel}_{mes_num}.csv",
            mime="text/csv",
            width='stretch'
        )
        
    else:
        st.info("💡 Haz clic en **🚀 Generar Libros de Compras** en la barra lateral para procesar todos los DTEs.")

    # ─── MODULO DE AUDITORÍA: DETALLES DE ARCHIVOS OMITIDOS / DUPLICADOS ───
    if st.session_state.omitidos:
        st.write("<br><br>", unsafe_allow_html=True)
        
        duplicados_lista = [x for x in st.session_state.omitidos if x.get('motivo') == 'Código duplicado']
        otras_omisiones = [x for x in st.session_state.omitidos if x.get('motivo') != 'Código duplicado']
        
        if duplicados_lista:
            st.error(f"🔍 Inspector de Seguridad: Se detectaron {len(duplicados_lista)} conflictos por Código de Generación Duplicado REAL")
            
            opciones_selector = [f"Código: {d['codigo_gen'][:15]}... | Archivo Omitido: {d['archivo']}" for d in duplicados_lista]
            idx_seleccionado = st.selectbox(
                "🎯 Selecciona un DTE en conflicto para examinarlo cara a cara:",
                options=range(len(opciones_selector)),
                format_func=lambda x: opciones_selector[x]
            )
            
            dup = duplicados_lista[idx_seleccionado]
            st.markdown(f"##### 🔎 Análisis Técnico de Estructura Interna (Código Completo: `{dup['codigo_gen']}`)")
            
            col_izq, col_der = st.columns(2)
            with col_izq:
                st.info("🟢 **DTE ACEPTADO (Primer archivo leído)**")
                st.markdown(f"**📄 Nombre de Archivo:** `{dup['orig_archivo']}`")
                st.markdown(f"**📅 Fecha Emisión:** `{dup['orig_fecha']}`")
                st.markdown(f"**🆔 NIT Emisor:** `{dup['orig_nit']}`")
                st.markdown(f"**🏢 NRC Emisor:** `{dup['orig_nrc']}`")
                st.markdown(f"**👤 Nombre / Razón Social:** `{dup['orig_nombre']}`")
                
            with col_der:
                st.warning("🔴 **DTE DUPLICADO (Omitido por Seguridad)**")
                st.markdown(f"**📄 Nombre de Archivo:** `{dup['dup_archivo']}`")
                st.markdown(f"**📅 Fecha Emisión:** `{dup['dup_fecha']}`")
                st.markdown(f"**🆔 NIT Emisor:** `{dup['dup_nit']}`")
                st.markdown(f"**🏢 NRC Emisor:** `{dup['dup_nrc']}`")
                st.markdown(f"**👤 Nombre / Razón Social:** `{dup['dup_nombre']}`")
                
            st.divider()
            
        if otras_omisiones:
            with st.expander(f"⚠️ Ver Otros Archivos Omitidos por Errores de Tipo o Fecha ({len(otras_omisiones)})", expanded=False):
                df_omitidos = pd.DataFrame(otras_omisiones)
                columnas_a_borrar = [c for c in ['orig_archivo','orig_fecha','orig_nit','orig_nrc','orig_nombre','dup_archivo','dup_fecha','dup_nit','dup_nrc','dup_nombre','codigo_gen'] if c in df_omitidos.columns]
                st.dataframe(df_omitidos.drop(columns=columnas_a_borrar), width='stretch')