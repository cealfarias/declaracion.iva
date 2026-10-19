import os
import pandas as pd
import streamlit as st
import glob
from datetime import datetime

st.set_page_config(page_title="Conversor XLSX a CSV MH", layout="wide", page_icon="📊")

RUTA_BASE = r"C:\Users\cealf\OneDrive\delcaraciones de IVA"

st.title("📊 Conversor: Reporte Excel MH ➡️ Anexo 3 CSV")
st.markdown("Convierte el reporte visual de DTEs descargado del portal del Ministerio de Hacienda al archivo oficial de 21 columnas para la declaración de IVA.")

if os.path.exists(RUTA_BASE):
    clientes = [f for f in os.listdir(RUTA_BASE) if os.path.isdir(os.path.join(RUTA_BASE, f)) and not f.startswith(('.', '_'))]
else:
    clientes = []

col1, col2, col3 = st.columns(3)
with col1:
    cliente_sel = st.selectbox("1. Selecciona Cliente:", options=clientes)
with col2:
    año_sel = st.number_input("2. Año a Declarar:", min_value=2000, max_value=2100, value=2026)
with col3:
    meses_dict = {1:"01 enero", 2:"02 febrero", 3:"03 marzo", 4:"04 abril", 5:"05 mayo", 6:"06 junio", 7:"07 julio", 8:"08 agosto", 9:"09 septiembre", 10:"10 octubre", 11:"11 noviembre", 12:"12 diciembre"}
    mes_num = st.selectbox("3. Mes a Declarar:", options=list(meses_dict.keys()), format_func=lambda x: meses_dict[x].upper())

if cliente_sel:
    carpeta_archivos = os.path.join(RUTA_BASE, cliente_sel, "años", str(año_sel), meses_dict[mes_num], "Archivos de Trabajo compras y ventas", "compras")
    if not os.path.exists(carpeta_archivos):
        carpeta_archivos = os.path.join(RUTA_BASE, cliente_sel, str(año_sel), meses_dict[mes_num], "Archivos de Trabajo compras y ventas", "compras")
    
    st.markdown(f"**📍 Buscando reportes Excel/CSV en:** `{carpeta_archivos}`")
    
    if os.path.exists(carpeta_archivos):
        archivos = glob.glob(os.path.join(carpeta_archivos, "*.xlsx")) + glob.glob(os.path.join(carpeta_archivos, "*.XLSX")) + glob.glob(os.path.join(carpeta_archivos, "*.csv")) + glob.glob(os.path.join(carpeta_archivos, "*.CSV"))
        archivos = [f for f in archivos if "Libro_Compras_NRC" not in f and "Anexo_Compras" not in f and "F07_Ventas" not in f]
        
        if archivos:
            archivo_sel = st.selectbox("📁 Archivo Reporte encontrado:", options=archivos, format_func=lambda x: os.path.basename(x))
            
            if st.button("🚀 Convertir a Formato F-930 (Anexo 3)", type="primary", width="stretch"):
                try:
                    if archivo_sel.lower().endswith('.csv'):
                        df_raw = pd.read_csv(archivo_sel, skiprows=7, header=None, sep=',', encoding='utf-8', on_bad_lines='skip')
                    else:
                        df_raw = pd.read_excel(archivo_sel, skiprows=7, header=None)
                    
                    datos_anexo3 = []
                    datos_sujeto_excluido = []
                    omitidos_vencidos = []
                    
                    for index, row in df_raw.iterrows():
                        if pd.isna(row[2]) or str(row[2]).strip() == "":
                            continue
                        
                        # Extraer fecha
                        try:
                            if isinstance(row[2], datetime):
                                fecha_obj = row[2]
                                fecha_str = fecha_obj.strftime("%d/%m/%Y")
                            else:
                                fecha_raw = str(row[2]).strip().split()[0]
                                if '-' in fecha_raw:
                                    partes = fecha_raw.split('-')
                                    if len(partes[0]) == 4: # YYYY-MM-DD
                                        fecha_obj = datetime(int(partes[0]), int(partes[1]), int(partes[2]))
                                        fecha_str = f"{partes[2]}/{partes[1]}/{partes[0]}"
                                    else:
                                        fecha_obj = datetime.strptime(fecha_raw, "%d-%m-%Y")
                                        fecha_str = fecha_obj.strftime("%d/%m/%Y")
                                elif '/' in fecha_raw:
                                    partes = fecha_raw.split('/')
                                    if len(partes[2]) == 4: # DD/MM/YYYY
                                        fecha_obj = datetime(int(partes[2]), int(partes[1]), int(partes[0]))
                                        fecha_str = fecha_raw
                                    else:
                                        fecha_obj = datetime.now()
                                        fecha_str = fecha_raw
                                else:
                                    fecha_obj = datetime.now()
                                    fecha_str = fecha_raw
                        except:
                            fecha_obj = datetime.now()
                            fecha_str = "01/01/2000"
                            
                        # Validación legal Art. 63 (hasta 3 períodos fiscales de antigüedad)
                        meses_diff = (año_sel - fecha_obj.year) * 12 + (mes_num - fecha_obj.month)
                        if meses_diff > 3:
                            omitidos_vencidos.append({
                                'Fila': index + 1,
                                'Documento': str(row[3]).strip(),
                                'Fecha': fecha_str,
                                'Motivo': f'Excede los 3 períodos anteriores permitidos por Art. 63 Ley de IVA ({meses_diff} meses)'
                            })
                            continue
                        elif meses_diff < 0:
                            omitidos_vencidos.append({
                                'Fila': index + 1,
                                'Documento': str(row[3]).strip(),
                                'Fecha': fecha_str,
                                'Motivo': f'Fecha futura no permitida para el período {mes_num:02d}/{año_sel}'
                            })
                            continue
                            
                        clase = "4"
                        
                        # Sujeto Excluido
                        val_suj_excluido = 0.0
                        try:
                            val_suj_excluido = float(row[16]) if not pd.isna(row[16]) else 0.0
                        except:
                            pass
                            
                        es_sujeto_excluido = (val_suj_excluido > 0)
                        tipo = "14" if es_sujeto_excluido else "03"
                        
                        codigo_gen = str(row[3]).strip().replace('-', '').upper()
                        
                        nrc = str(row[4]).strip().replace('.0', '') if not pd.isna(row[4]) else ""
                        nit_dui = str(row[5]).strip() if not pd.isna(row[5]) else ""
                        
                        nrc = nrc.replace('-', '').replace('/', '').replace(' ', '')
                        nit_dui = nit_dui.replace('-', '').replace('/', '').replace(' ', '')
                        
                        # Prioridad de NIT del proveedor
                        if nit_dui and nit_dui.upper() != "NAN":
                            nit_nrc_final = nit_dui
                        elif nrc and nrc.upper() != "NAN":
                            nit_nrc_final = nrc
                        else:
                            nit_nrc_final = ""
                        
                        nombre = str(row[6]).replace(';', ' ').replace('"', '').strip() if not pd.isna(row[6]) else ""
                        
                        def clean_float(val):
                            try:
                                return float(str(val).replace(',', ''))
                            except:
                                return 0.0
                                
                        g_exenta = clean_float(row[8])
                        j_gravada = clean_float(row[10])
                        iva = clean_float(row[12])
                        total = clean_float(row[15])
                        
                        dui_final = ""
                        if es_sujeto_excluido:
                            m_gravada_suj = val_suj_excluido
                            j_gravada = 0.0
                            if len(nit_nrc_final) == 9:
                                dui_final = nit_nrc_final
                                nit_nrc_final = ""
                        else:
                            m_gravada_suj = 0.0
                            dui_final = ""
                            
                        antiguedad_label = "Mes Actual" if meses_diff == 0 else f"{meses_diff} Mes(es) Antes"
                            
                        registro = {
                            'A': fecha_str, 'B': clase, 'C': tipo, 'D': codigo_gen,
                            'E': nit_nrc_final, 'F': nombre,
                            'G': round(g_exenta, 2), 'H': 0.0, 'I': 0.0, 'J': round(j_gravada, 2),
                            'K': 0.0, 'L': 0.0, 'M': round(m_gravada_suj, 2),
                            'N': round(iva, 2), 'O': round(total, 2), 'P': dui_final,
                            'Q': '1', 'R': '1', 'S': '2', 'T': '5', 'U': '3' if not es_sujeto_excluido else '5',
                            'Antigüedad': antiguedad_label
                        }
                        
                        if es_sujeto_excluido:
                            datos_sujeto_excluido.append(registro)
                        else:
                            datos_anexo3.append(registro)
                        
                    if datos_anexo3:
                        df_final = pd.DataFrame(datos_anexo3)
                        st.success(f"✅ ¡Éxito! Se detectaron y procesaron {len(datos_anexo3)} comprobantes para el Libro de Compras (Anexo 3).")
                        
                        # Desglose Art. 63
                        col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                        with col_a1:
                            st.info(f"**Mes en Curso:** {len(df_final[df_final['Antigüedad'] == 'Mes Actual'])} DTEs")
                        with col_a2:
                            st.success(f"**1 Mes Antes:** {len(df_final[df_final['Antigüedad'] == '1 Mes(es) Antes'])} DTEs")
                        with col_a3:
                            st.success(f"**2 Meses Antes:** {len(df_final[df_final['Antigüedad'] == '2 Mes(es) Antes'])} DTEs")
                        with col_a4:
                            st.success(f"**3 Meses Antes:** {len(df_final[df_final['Antigüedad'] == '3 Mes(es) Antes'])} DTEs")
                            
                        st.dataframe(df_final, width='stretch', height=300)
                        
                        # Generar CSV oficial de 21 columnas
                        cols_21 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U']
                        csv_string = df_final[cols_21].to_csv(index=False, header=False, sep=';', float_format='%.2f')
                        csv_data = csv_string.rstrip('\r\n').encode('utf-8')
                        
                        st.download_button(
                            "📥 Descargar Archivo Oficial Anexo 3 (Libro de Compras F-930)",
                            data=csv_data,
                            file_name=f"Anexo_3_Compras_{año_sel}_{mes_num:02d}.csv",
                            mime="text/csv",
                            type="primary",
                            width="stretch"
                        )
                    else:
                        st.warning("No se encontraron comprobantes de compras a contribuyentes válidos en este archivo.")
                        
                    if datos_sujeto_excluido:
                        st.divider()
                        df_se = pd.DataFrame(datos_sujeto_excluido)
                        st.warning(f"ℹ️ Se detectaron {len(datos_sujeto_excluido)} compras a Sujetos Excluidos. Por ley, se declaran en el **Anexo 5**:")
                        cols_21 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U']
                        csv_se = df_se[cols_21].to_csv(index=False, header=False, sep=';', float_format='%.2f').rstrip('\r\n').encode('utf-8')
                        st.download_button(
                            "📥 Descargar Archivo Oficial Anexo 5 (Sujetos Excluidos)",
                            data=csv_se,
                            file_name=f"Anexo_5_Sujetos_Excluidos_{año_sel}_{mes_num:02d}.csv",
                            mime="text/csv"
                        )
                        
                    if omitidos_vencidos:
                        st.error(f"⚠️ Documentos omitidos por fecha ({len(omitidos_vencidos)}):")
                        st.dataframe(pd.DataFrame(omitidos_vencidos), width='stretch')
                        
                except Exception as e:
                    st.error(f"Ocurrió un error al leer el reporte: {e}")
        else:
            st.info("No hay archivos Excel ni CSV visuales en la carpeta seleccionada.")
