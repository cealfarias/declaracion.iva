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

# CSS ESTILIZADO
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
        .badge-art63 {
            background-color: #e0f2fe;
            color: #0369a1;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
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
if 'sujetos_excluidos' not in st.session_state:
    st.session_state.sujetos_excluidos = []
if 'omitidos' not in st.session_state:
    st.session_state.omitidos = []
if 'vista' not in st.session_state:
    st.session_state.vista = "principal"

DTE_NOMBRES = {
    '01': '01 - Factura', '03': '03 - Crédito Fiscal', '05': '05 - Nota de Débito',
    '06': '06 - Nota de Crédito', '07': '07 - Comprobante de Retención',
    '08': '08 - Comprobante de Liquidación', '09': '09 - Doc. Contable de Liquidación',
    '11': '11 - Factura de Exportación', '12': '12 - Declaración de Mercancías',
    '13': '13 - Mandamiento de Ingreso', '14': '14 - Factura Sujeto Excluido',
    '15': '15 - Comprobante de Donación'
}

MESES_DICT = {
    1: "01 enero", 2: "02 febrero", 3: "03 marzo", 4: "04 abril", 5: "05 mayo", 
    6: "06 junio", 7: "07 julio", 8: "08 agosto", 9: "09 septiembre", 
    10: "10 octubre", 11: "11 noviembre", 12: "12 diciembre"
}

# ===================== FUNCIÓN PARA LOCALIZAR CARPETAS DE COMPRAS =====================
def localizar_carpeta_compras(ruta_base, contribuyente, año, mes_num):
    """Localiza de manera flexible la carpeta de compras tolerando variaciones en la estructura de carpetas."""
    prefijo_mes = f"{mes_num:02d}"
    
    # Posibles rutas para el año
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
            # Coincidencia por prefijo (ej: "09" o "09 septiembre")
            if s.strip().startswith(prefijo_mes) or MESES_DICT.get(mes_num, '').split()[1].lower() in s.lower():
                carpeta_mes = os.path.join(r_año, s)
                # Buscar subcarpeta compras
                candidatos_compras = [
                    os.path.join(carpeta_mes, "Archivos de Trabajo compras y ventas", "compras"),
                    os.path.join(carpeta_mes, "Archivos de Trabajo compras y ventas", "COMPRAS"),
                    os.path.join(carpeta_mes, "compras"),
                    os.path.join(carpeta_mes, "COMPRAS"),
                    os.path.join(carpeta_mes, "Compas")
                ]
                for c in candidatos_compras:
                    if os.path.exists(c):
                        return c
                # Si existe la carpeta del mes directamente
                if os.path.exists(carpeta_mes):
                    return carpeta_mes
    return None

# ===================== SIDEBAR: CONTROL TRIBUTARIO =====================
with st.sidebar:
    st.header("⚙️ Parámetros del Sistema")
    
    if not contribuyentes_disponibles:
        st.error(f"❌ No se encontró la raíz en: `{RUTA_BASE}`")
        contribuyente_sel = None
    else:
        contribuyente_sel = st.selectbox("1. Selecciona Carpeta Cliente:", options=contribuyentes_disponibles)
    
    st.divider()
    st.subheader("📅 Período Tributario a Declarar")
    
    año_sel = st.number_input("2. Año Fiscal:", min_value=2000, max_value=2100, value=2026)
    mes_num = st.selectbox("3. Mes de Declaración:", options=list(MESES_DICT.keys()), format_func=lambda x: MESES_DICT[x].upper())
    
    st.divider()
    st.subheader("⚖️ Aplicación Art. 63 Ley de IVA")
    st.caption("La ley permite deducir crédito fiscal de hasta 3 períodos tributarios anteriores.")
    
    incluir_anteriores = st.checkbox(
        "Buscar automáticamente en carpetas de los 3 meses anteriores",
        value=True,
        help="Si está marcado, el sistema también buscará compras pendientes en las carpetas de los 3 meses previos al período declarado."
    )
    
    carpetas_a_escanear = []
    
    if contribuyente_sel:
        # Período actual (diferencia 0)
        c_actual = localizar_carpeta_compras(RUTA_BASE, contribuyente_sel, año_sel, mes_num)
        if c_actual:
            carpetas_a_escanear.append((año_sel, mes_num, 0, c_actual, "Mes Actual"))
            
        # Si se activó incluir anteriores, calcular M-1, M-2, M-3
        if incluir_anteriores:
            for diff in [1, 2, 3]:
                m_ant = mes_num - diff
                y_ant = año_sel
                if m_ant <= 0:
                    m_ant += 12
                    y_ant -= 1
                c_ant = localizar_carpeta_compras(RUTA_BASE, contribuyente_sel, y_ant, m_ant)
                if c_ant and c_ant != c_actual:
                    carpetas_a_escanear.append((y_ant, m_ant, diff, c_ant, f"{diff} Mes(es) Antes"))
        
        st.markdown("##### 📍 Carpetas Detectadas para Análisis:")
        total_archivos_detectados = 0
        for y, m, diff, ruta_c, etiqueta in carpetas_a_escanear:
            jsons = glob.glob(os.path.join(ruta_c, "*.json")) + glob.glob(os.path.join(ruta_c, "*.JSON"))
            total_archivos_detectados += len(jsons)
            st.caption(f"• **{MESES_DICT[m].upper()} {y} ({etiqueta}):** {len(jsons)} JSONs")
            
        if total_archivos_detectados > 0:
            st.success(f"📂 Total: {total_archivos_detectados} archivos listos para auditar y procesar.")
        else:
            st.warning("⚠️ No se encontraron archivos JSON en las rutas correspondientes.")

    st.markdown("<br>", unsafe_allow_html=True)
    procesar = st.button(
        "🚀 Generar Libros de Compras", 
        type="primary", 
        width='stretch', 
        disabled=(not contribuyente_sel or not carpetas_a_escanear)
    )

# ===================== MÓDULO DE PROCESAMIENTO MULTI-NRC =====================
if procesar and contribuyente_sel:
    st.session_state.datos_mes = []
    st.session_state.sujetos_excluidos = []
    st.session_state.omitidos = []
    
    # Recolectar archivos de todas las carpetas seleccionadas (mes actual y anteriores)
    archivos_por_procesar = []
    for y, m, diff, ruta_c, etiqueta in carpetas_a_escanear:
        raw_files = glob.glob(os.path.join(ruta_c, "*.json")) + glob.glob(os.path.join(ruta_c, "*.JSON"))
        for rf in sorted(list(set(raw_files))):
            archivos_por_procesar.append((rf, etiqueta))
            
    codigos_vistos = {}
    barra = st.progress(0)
    
    for i, (ruta, etiqueta_origen) in enumerate(archivos_por_procesar):
        barra.progress((i + 1) / len(archivos_por_procesar))
        nombre = os.path.basename(ruta)
        motivo = ""
        
        data = cargar_json_seguro(ruta)
        if data is None:
            st.session_state.omitidos.append({'archivo': nombre, 'tipo_dte': "99 - JSON Corrupto", 'motivo': "JSON inválido o vacío", 'RUTA_ORIGEN_INTERNA': ruta})
            continue
        
        ident = data.get('identificacion', {}) or {}
        receptor = data.get('receptor', {}) or {}
        emisor = data.get('emisor', {}) or {}
        resumen = data.get('resumen', {}) or {}
        
        tipo = ident.get('tipoDte', '')
        fecha_raw = ident.get('fecEmi', '')
        codigo_gen = ident.get('codigoGeneracion', '')
        codigo_gen = str(codigo_gen).replace('-', '').strip().upper() if codigo_gen else ''
        
        nrc_receptor_dte = str(receptor.get('nrc', 'SIN_NRC')).replace('-', '').replace('/', '').strip().upper()
        tipo_nombre_descriptivo = DTE_NOMBRES.get(tipo, f"{tipo} - Tipo No Común")
        
        # Validar tipo de DTE para compras:
        # Anexo 3 acepta: 03 (CCF), 05 (NC), 06 (ND), 11 (Fact. Exportación), 12 (Decl. Mercancías), 13 (Mandamiento Ingreso)
        # Nota: DTE 14 (Sujeto Excluido) se procesa por separado para el Anexo 5.
        if tipo not in ['03', '05', '06', '11', '12', '13', '14']:
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
                
                # Cálculo de diferencia en períodos tributarios (meses)
                meses_diferencia = (año_sel - fecha_dte.year) * 12 + (mes_num - fecha_dte.month)
                
                # Validación estricta según Art. 63 Ley de IVA (0 = mismo período, 1, 2, 3 = períodos anteriores)
                if meses_diferencia < 0:
                    motivo = f"Fecha futura no válida ({fecha_raw[:10]}) para el período {mes_num:02d}/{año_sel}"
                elif meses_diferencia > 3:
                    motivo = f"DTE vencido: emitido hace {meses_diferencia} meses ({fecha_raw[:10]}). La ley solo permite deducir hasta 3 períodos anteriores."
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
        total_exenta = resumen.get('totalExenta', 0.0) or 0.0
        total_gravada = resumen.get('totalGravada', 0.0) or 0.0
        for trib in resumen.get('tributos', []) or []:
            if trib.get('codigo') == '20':
                iva = trib.get('valor', 0.0)
                break
        if iva == 0.0 and total_gravada > 0 and tipo != '14':
            iva = round(total_gravada * 0.13, 2)
        
        # ASIGNACIÓN DE COLUMNAS SEGÚN NORMATIVA MH
        g = h = i = j = k = l = m = 0.0
        if tipo in ['03', '05', '06', '11']:
            g = total_exenta
            j = total_gravada
        elif tipo == '12':
            i = total_exenta
            l = total_gravada
        elif tipo == '13':
            i = total_exenta
            m = total_gravada
        elif tipo == '14':
            m = total_gravada # Para Sujetos Excluidos
        
        # Total compras neto requerido por MH en columna O (Suma de G a M)
        total_compras_neto = g + h + i + j + k + l + m
        
        # CLASE DE DOCUMENTO (Columna B):
        # 4: DTE (aplica para 03, 05, 06, 11)
        # 3: Otros (aplica para 12 y 13)
        if tipo in ['03', '05', '06', '11']:
            clase_doc = '4'
        elif tipo in ['12', '13']:
            clase_doc = '3'
        else:
            clase_doc = '4'
        
        # PROVEEDOR
        if tipo == '14' and 'sujetoExcluido' in data:
            prov_data = data['sujetoExcluido'] or {}
        else:
            prov_data = emisor or {}
            
        nrc_prov = str(prov_data.get('nrc', '')).strip()
        nit_prov = str(prov_data.get('nit', '')).strip()
        
        # Prioridad de NIT del proveedor para el Libro de Compras
        if nit_prov:
            nit_nrc = nit_prov
        else:
            nit_nrc = nrc_prov
            
        nombre_prov = str(prov_data.get('nombre', '')).replace(';', ' ').replace('"', '').replace("'", "").strip().upper()
        
        # Para tipos 12 y 13: Dirección General de Tesorería según normativa
        if tipo in ['12', '13'] and not nit_nrc:
            nit_nrc = "06140108140066"
            nombre_prov = "DIRECCION GENERAL DE TESORERIA"
            
        # DUI del proveedor (Persona natural)
        dui = prov_data.get('dui', '') or prov_data.get('documento', '') or prov_data.get('numDocumento', '')
        dui_limpio = ''
        if dui:
            dui_str = str(dui).strip().replace('-', '').replace(' ', '')
            if dui_str.isdigit() and (8 <= len(dui_str) <= 9):
                dui_limpio = dui_str
        
        nit_nrc_final = nit_nrc.replace('-', '').replace('/', '').strip()
        
        # Exclusión mutua según normativa: Si va DUI en P, E debe ir vacío.
        # Para Comprobantes de IVA (03, 05, 06, 11), siempre se exige NIT/NRC en E y DUI en P queda vacío.
        if tipo in ['03', '05', '06', '11', '12', '13']:
            dui_limpio = ''
        else:
            if dui_limpio and not nit_nrc_final:
                pass
            else:
                dui_limpio = ''
                
        if not nit_nrc_final and not dui_limpio:
            nit_nrc_final = nit_prov.replace('-', '').replace('/', '').strip()
        
        # Clasificación por Antigüedad según Art. 63
        if meses_diferencia == 0:
            clasif_art63 = "Mes en Curso"
        elif meses_diferencia == 1:
            clasif_art63 = "1 Mes Anterior"
        elif meses_diferencia == 2:
            clasif_art63 = "2 Meses Anteriores"
        elif meses_diferencia == 3:
            clasif_art63 = "3 Meses Anteriores"
        else:
            clasif_art63 = f"{meses_diferencia} Meses Anteriores"

        registro = {
            'A': fecha_dte.strftime('%d/%m/%Y'), 'B': clase_doc, 'C': tipo, 'D': codigo_gen,
            'E': nit_nrc_final, 'F': nombre_prov,
            'G': round(g, 2), 'H': round(h, 2), 'I': round(i, 2), 'J': round(j, 2),
            'K': round(k, 2), 'L': round(l, 2), 'M': round(m, 2),
            'N': round(iva, 2), 'O': round(total_compras_neto, 2), 'P': dui_limpio,
            'Q': '1', 'R': '1', 'S': '2', 'T': '5', 'U': '3',
            'ANTIGUEDAD_ART63': clasif_art63,
            'MESES_DIFERENCIA': meses_diferencia,
            'RUTA_ORIGEN_INTERNA': ruta,
            'NRC_RECEPTOR_INTERNO': nrc_receptor_dte
        }
        
        # Si es tipo 14 (Sujeto Excluido), no mezclarlo en el Anexo 3 para evitar rechazo de MH
        if tipo == '14':
            registro['U'] = '5' # Anexo 5 Sujetos Excluidos
            st.session_state.sujetos_excluidos.append(registro)
        else:
            st.session_state.datos_mes.append(registro)

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
        
        # MÉTRICAS GENERALES
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total DTEs en Libro", f"{len(df_nrc_valores)} DTEs")
        with col2:
            total_gravado = df_nrc_valores['J'].sum() + df_nrc_valores['L'].sum() + df_nrc_valores['M'].sum()
            st.metric("Total Gravado", f"${total_gravado:,.2f}")
        with col3:
            total_iva = df_nrc_valores['N'].sum()
            st.metric("Crédito Fiscal (IVA)", f"${total_iva:,.2f}")
        with col4:
            total_general = df_nrc_valores['O'].sum()
            st.metric("Total Compras (Neto MH)", f"${total_general:,.2f}")
            
        # PANEL DE VERIFICACIÓN LEGAL ART. 63 (DESGLOSE DE MESES)
        st.write("<br>", unsafe_allow_html=True)
        st.markdown("### ⚖️ Auditoría Legal Art. 63 Ley de IVA (Antigüedad de DTEs)")
        
        df_m0 = df_nrc_valores[df_nrc_valores['MESES_DIFERENCIA'] == 0]
        df_m1 = df_nrc_valores[df_nrc_valores['MESES_DIFERENCIA'] == 1]
        df_m2 = df_nrc_valores[df_nrc_valores['MESES_DIFERENCIA'] == 2]
        df_m3 = df_nrc_valores[df_nrc_valores['MESES_DIFERENCIA'] == 3]
        
        c_m0, c_m1, c_m2, c_m3 = st.columns(4)
        with c_m0:
            st.info(f"**Mes en Curso (M)**\n\n📄 **{len(df_m0)} DTEs**\n\n💵 IVA: ${df_m0['N'].sum():,.2f}")
        with c_m1:
            st.success(f"**1 Mes Antes (M-1)**\n\n📄 **{len(df_m1)} DTEs**\n\n💵 IVA: ${df_m1['N'].sum():,.2f}")
        with c_m2:
            st.success(f"**2 Meses Antes (M-2)**\n\n📄 **{len(df_m2)} DTEs**\n\n💵 IVA: ${df_m2['N'].sum():,.2f}")
        with c_m3:
            st.success(f"**3 Meses Antes (M-3)**\n\n📄 **{len(df_m3)} DTEs**\n\n💵 IVA: ${df_m3['N'].sum():,.2f}")
            
        st.write("<br>", unsafe_allow_html=True)
        st.markdown(f"### 📋 Detalle de Registros - Anexo 3 (NRC: `{nrc_seleccionado}`)")
        
        df_visual = df_nrc_valores.copy()
        columnas_ordenadas = [
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
            'ANTIGUEDAD_ART63', 'RUTA_ORIGEN_INTERNA', 'NRC_RECEPTOR_INTERNO'
        ]
        df_visual = df_visual[columnas_ordenadas]
        df_visual.columns = [
            'Fecha Emisión (A)', 'Clase (B)', 'Tipo DTE (C)', 'Cód. Generación (D)',
            'NIT/NRC Emisor (E)', 'Nombre Proveedor (F)', 'Exenta Int (G)', 'Exenta Imp (H)',
            'Exenta Rec (I)', 'Gravada Int (J)', 'Gravada Imp (K)', 'Gravada Almacén (L)',
            'Gravada Serv (M)', 'IVA (N)', 'Total Documento (O)', 'DUI (P)', 
            'Tipo Operación (Q)', 'Clasificación (R)', 'Sector (S)', 'Tipo Costo/Gasto (T)', 'Anexo (U)', 
            'Antigüedad (Art. 63)', 'RUTA_ORIGEN_INTERNA', 'NRC_RECEPTOR_INTERNO'
        ]
        
        df_tabla_pantalla = df_visual.drop(columns=['RUTA_ORIGEN_INTERNA', 'NRC_RECEPTOR_INTERNO'])
        st.dataframe(df_tabla_pantalla, width='stretch', height=350)
        
        st.write("<br>", unsafe_allow_html=True)
        
        # 🌟 EXPORTACIÓN OFICIAL EXACTA DEL ANEXO 3 (21 COLUMNAS ESTRICTAS: A HASTA U)
        columnas_oficiales_anexo3 = [
            'Fecha Emisión (A)', 'Clase (B)', 'Tipo DTE (C)', 'Cód. Generación (D)',
            'NIT/NRC Emisor (E)', 'Nombre Proveedor (F)', 'Exenta Int (G)', 'Exenta Imp (H)',
            'Exenta Rec (I)', 'Gravada Int (J)', 'Gravada Imp (K)', 'Gravada Almacén (L)',
            'Gravada Serv (M)', 'IVA (N)', 'Total Documento (O)', 'DUI (P)', 
            'Tipo Operación (Q)', 'Clasificación (R)', 'Sector (S)', 'Tipo Costo/Gasto (T)', 'Anexo (U)'
        ]
        df_final_clean = df_tabla_pantalla[columnas_oficiales_anexo3]
        
        csv_string = df_final_clean.to_csv(index=False, header=False, sep=';', float_format='%.2f')
        csv_data = csv_string.rstrip('\r\n').encode('utf-8')
        
        st.download_button(
            label=f"📥 Descargar Libro de Compras Oficial (Anexo 3) para NRC: {nrc_seleccionado}",
            data=csv_data,
            file_name=f"Libro_Compras_NRC_{nrc_seleccionado}_{año_sel}_{mes_num}.csv",
            mime="text/csv",
            width='stretch',
            type="primary"
        )
        
        # SECCIÓN DE SUJETOS EXCLUIDOS (ANEXO 5) SI EXISTEN
        if st.session_state.sujetos_excluidos:
            st.divider()
            df_se = pd.DataFrame(st.session_state.sujetos_excluidos)
            df_se_nrc = df_se[df_se['NRC_RECEPTOR_INTERNO'] == nrc_seleccionado]
            if not df_se_nrc.empty:
                st.warning(f"ℹ️ **Compras a Sujetos Excluidos Detectadas ({len(df_se_nrc)} DTEs):** Por normativa de Hacienda, estas compras se declaran en el **Anexo 5**, no en el Anexo 3. Se separaron automáticamente para proteger tu archivo.")
                df_se_clean = df_se_nrc[['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U']]
                csv_se = df_se_clean.to_csv(index=False, header=False, sep=';', float_format='%.2f').rstrip('\r\n').encode('utf-8')
                st.download_button(
                    label=f"📥 Descargar Compras Sujetos Excluidos (Anexo 5) para NRC: {nrc_seleccionado}",
                    data=csv_se,
                    file_name=f"Sujetos_Excluidos_NRC_{nrc_seleccionado}_{año_sel}_{mes_num}.csv",
                    mime="text/csv"
                )
        
    else:
        st.info("💡 Haz clic en **🚀 Generar Libros de Compras** en la barra lateral para procesar todos los DTEs.")

    # ─── MODULO DE AUDITORÍA: DETALLES DE ARCHIVOS OMITIDOS / DUPLICADOS ───
    if st.session_state.omitidos:
        st.write("<br><br>", unsafe_allow_html=True)
        
        duplicados_lista = [x for x in st.session_state.omitidos if x.get('motivo') == 'Código duplicado']
        vencidos_lista = [x for x in st.session_state.omitidos if 'DTE vencido' in str(x.get('motivo', ''))]
        otras_omisiones = [x for x in st.session_state.omitidos if x.get('motivo') != 'Código duplicado' and 'DTE vencido' not in str(x.get('motivo', ''))]
        
        if vencidos_lista:
            st.error(f"⏳ **DTEs Descartados por Vencimiento legal (> 3 meses): {len(vencidos_lista)}**")
            with st.expander("Ver documentos que excedieron los 3 períodos legales del Art. 63"):
                st.dataframe(pd.DataFrame(vencidos_lista)[['archivo', 'tipo_dte', 'motivo']], width='stretch')
        
        if duplicados_lista:
            st.warning(f"🔍 Inspector de Seguridad: Se detectaron {len(duplicados_lista)} conflictos por Código de Generación Duplicado")
            
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
