import streamlit as st
import pandas as pd
import numpy as np
import io
import os

# --- 1. SEGURIDAD ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Blum2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Contraseña incorrecta. Reintentar:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="Blum & Asociados | Intelligence", layout="wide")

    # --- 2. ENCABEZADO ---
    col_logo, col_tit = st.columns([1, 4])
    with col_logo:
        if os.path.exists("logo_v3.png"):
            st.image("logo_v3.png", width=120)
        else:
            st.subheader("B&A")
    with col_tit:
        st.title("Inventory Intelligence")
        st.markdown("**Consultoría en Excelencia Operacional**")

    st.divider()

    # --- 3. PANEL DE CONTROL ---
    with st.expander("⚙️ Configuración del Análisis"):
        c1, c2 = st.columns(2)
        with c1:
            empresa_activa = st.text_input("Empresa", "Cliente Demo")
            tasa_wacc = st.number_input("Tasa WACC (%)", value=30.0) / 100
        with c2:
            nombre_reporte = st.text_input("Nombre Reporte", f"Reporte_{empresa_activa}")
            honorarios = st.number_input("Inversión Proyecto ($)", value=1000000.0)

    archivo = st.file_uploader("📂 Subir Excel de Inventario", type=["xlsx", "xls"])

    if archivo:
        try:
            df = pd.read_excel(archivo)
            meses = [c for c in df.columns if c.startswith("Mes_")]
            
            # --- MOTOR DE CÁLCULO ---
            df["Consumo_Total"] = df[meses].sum(axis=1)
            df["Promedio_Mensual"] = df[meses].mean(axis=1)
            df["Inv_Total"] = df["Stock_Actual"] * df["Costo_Unitario"]
            df["Valor_Consumo"] = df["Consumo_Total"] * df["Costo_Unitario"]
            
            df = df.sort_values(by="Valor_Consumo", ascending=False)
            df["%_Acum"] = df["Valor_Consumo"].cumsum() / df["Valor_Consumo"].sum()
            df["ABC"] = df["%_Acum"].apply(lambda p: "A" if p <= 0.8 else ("B" if p <= 0.95 else "C"))
            df["CV"] = df[meses].std(axis=1) / df["Promedio_Mensual"].replace(0, np.nan)
            df["XYZ"] = df["CV"].apply(lambda cv: "X" if pd.isna(cv) or cv <= 0.5 else ("Y" if cv <= 1 else "Z"))
            df["Categorizacion_Final"] = df["ABC"].astype(str) + df["XYZ"].astype(str)

            cob_dict = {"A": 2, "B": 3, "C": 4}
            df["Stock_Objetivo"] = df["Promedio_Mensual"] * df["ABC"].map(cob_dict)
            df["Cap_Liberable"] = (df["Stock_Actual"] - df["Stock_Objetivo"]).clip(lower=0) * df["Costo_Unitario"]
            df["Cap_Riesgo"] = (df["Stock_Objetivo"] - df["Stock_Actual"]).clip(lower=0) * df["Costo_Unitario"]
            df["Rotacion_Anual"] = df["Consumo_Total"] / df["Stock_Actual"].replace(0, np.nan)
            df["DOH"] = df["Stock_Actual"] / (df["Promedio_Mensual"] / 30).replace(0, np.nan)
            df["Cap_Obsoleto_Real"] = np.where(df["Consumo_Total"] == 0, df["Inv_Total"], 0)
            df["Cap_Obsoleto_Est"] = np.where(df["DOH"] > 365, df["Inv_Total"], 0)

            # Acción Sugerida
            def motor_acciones(row):
                comb, es_exceso = row["Categorizacion_Final"], row["Cap_Liberable"] > 0
                if es_exceso:
                    if "AX" in comb: return "frenar compras inmediatamente. prioridad #1."
                    if "AY" in comb: return "ajuste progresivo. evaluar estacionalidad."
                    if "AZ" in comb: return "riesgo obsolescencia. evaluar promociones."
                    if "BX" in comb or "BY" in comb: return "reducir lote de compra o frecuencia."
                    if "BZ" in comb: return "analizar si exceso justifica costo oportunidad."
                    if "CX" in comb or "CY" in comb: return "bajo impacto financiero. agotar naturalmente."
                    if "CZ" in comb: return "evaluar eliminación. capital muerto."
                else:
                    if "AX" in comb: return "emitir orden de compra hoy. riesgo pérdida."
                    if "AY" in comb: return "revisar stock de seguridad. demanda variable."
                    if "AZ" in comb: return "evaluar si conviene stockear o bajo pedido."
                    if "BX" in comb or "BY" in comb: return "ajustar parámetros de reposición en sistema."
                    if "BZ" in comb: return "revisar si el ítem sigue activo en catálogo."
                    if "CX" in comb or "CY" in comb: return "reposición estándar. sin gestión expedita."
                    if "CZ" in comb: return "no reponer sin pedido firme del cliente."
                return "monitoreo."
            df["Accion_Sugerida"] = df.apply(motor_acciones, axis=1)

            # --- RESUMEN EN PANTALLA ---
            inv_total, lib_total = df["Inv_Total"].sum(), df["Cap_Liberable"].sum()
            ahorro_anual = lib_total * tasa_wacc
            
            st.subheader("📊 Métricas Clave")
            k1, k2 = st.columns(2)
            k1.metric("Inventario Total", f"$ {inv_total:,.0f}")
            k2.metric("Cap. Liberable", f"$ {lib_total:,.0f}", delta=f"{(lib_total/inv_total)*100:.1f}%", delta_color="inverse")

            # --- GENERADOR EXCEL PROFESIONAL ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                workbook = writer.book
                # Formatos (Exactamente iguales a los de ayer)
                f_card = workbook.add_format({'bold': True, 'bg_color': '#1E293B', 'font_color': 'white', 'align': 'center', 'border': 1})
                f_header = workbook.add_format({'bold': True, 'bg_color': '#0F172A', 'font_color': 'white', 'border': 1, 'align': 'center'})
                f_label = workbook.add_format({'bold': True, 'font_color': '#475569'})
                f_money = workbook.add_format({'num_format': '$#,##0', 'bold': True})
                f_pct = workbook.add_format({'num_format': '0.0%', 'bold': True})
                f_std = workbook.add_format({'num_format': '#,##0.0', 'bold': True})
                f_wrap = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1, 'font_size': 10})

                # Formatos Base
                f_ba_money = workbook.add_format({'num_format': '$#,##0', 'border': 1})
                f_ba_std = workbook.add_format({'num_format': '#,##0.0', 'border': 1})
                f_ba_pct = workbook.add_format({'num_format': '0.0%', 'border': 1})
                f_ba_txt = workbook.add_format({'border': 1})

                # Hoja 1: DASHBOARD
                ws_d = workbook.add_worksheet("DASHBOARD")
                ws_d.hide_gridlines(2)
                ws_d.set_column('B:E', 28)
                ws_d.merge_range('B2:C2', 'IMPACTO FINANCIERO', f_card)
                ws_d.write('B3', 'Inventario Total', f_label); ws_d.write('C3', inv_total, f_money)
                ws_d.write('B4', 'Capital Liberable', f_label); ws_d.write('C4', lib_total, f_money)
                ws_d.write('B5', 'Capital en Riesgo', f_label); ws_d.write('C5', df["Cap_Riesgo"].sum(), f_money)
                ws_d.write('B6', '% Cap. Liberable', f_label); ws_d.write('C6', lib_total/inv_total if inv_total > 0 else 0, f_pct)
                
                ws_d.merge_range('D2:E2', 'RENTABILIDAD Y RETORNO', f_card)
                ws_d.write('D3', 'Costo WACC', f_label); ws_d.write('E3', tasa_wacc, f_pct)
                ws_d.write('D4', 'Ahorro Anual', f_label); ws_d.write('E4', ahorro_anual, f_money)
                ws_d.write('D5', 'Flujo 1er Año', f_label); ws_d.write('E5', lib_total + ahorro_anual - honorarios, f_money)
                ws_d.write('D6', 'ROI (%)', f_label); ws_d.write('E6', (ahorro_anual/honorarios if honorarios > 0 else 0), f_pct)

                # Hoja 2: BASE_ANALISIS
                df.to_excel(writer, sheet_name="Base_Analisis", index=False)
                ws_b = writer.sheets["Base_Analisis"]
                for col_num, col_name in enumerate(df.columns):
                    ws_b.write(0, col_num, col_name, f_header)
                    if any(x in col_name for x in ["Costo", "Inv_Total", "Valor_Consumo", "Cap_Liberable", "Cap_Riesgo", "Cap_Obsoleto"]):
                        ws_b.set_column(col_num, col_num, 18, f_ba_money)
                    elif any(x in col_name for x in ["Promedio", "CV", "Rotacion", "DOH", "Stock_Actual", "Stock_Objetivo"]):
                        ws_b.set_column(col_num, col_num, 15, f_ba_std)
                    elif "%" in col_name:
                        ws_b.set_column(col_num, col_num, 12, f_ba_pct)
                    else:
                        ws_b.set_column(col_num, col_num, 20, f_ba_txt)
                ws_b.autofilter(0, 0, len(df), len(df.columns)-1)
                ws_b.freeze_panes(1, 0)

            st.divider()
            st.download_button(
                label="📥 DESCARGAR REPORTE TÉCNICO COMPLETO",
                data=output.getvalue(),
                file_name=f"{nombre_reporte}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"Error técnico: {e}")
