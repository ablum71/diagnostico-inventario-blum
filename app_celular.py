import streamlit as st
import pandas as pd
import numpy as np
import io
import os

# --- 1. SEGURIDAD SIMPLE ---
def check_password():
    """Retorna True si el usuario ingresó la contraseña correcta."""
    def password_entered():
        if st.session_state["password"] == "Blum2026": # <--- CAMBIÁ TU CLAVE ACÁ
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # No guardar la clave en texto plano
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Pantalla de Login
        st.title("🔐 Acceso Restringido")
        st.text_input("Ingresá la contraseña para continuar", type="password", on_change=password_entered, key="password")
        st.info("Blum & Asociados | Inventory Intelligence System")
        return False
    elif not st.session_state["password_correct"]:
        # Contraseña incorrecta
        st.text_input("Contraseña incorrecta. Reintentar:", type="password", on_change=password_entered, key="password")
        st.error("❌ Acceso denegado")
        return False
    else:
        # Contraseña correcta
        return True

# Solo si el login es exitoso, ejecutamos la App
if check_password():
    
    # --- CONFIGURACIÓN DE PÁGINA ---
    st.set_page_config(page_title="Blum & Asociados | Dashboard", layout="wide")

    # --- ENCABEZADO ---
    col_logo, col_tit = st.columns([1, 4])
    with col_logo:
        if os.path.exists("logo_v3.png"):
            st.image("logo_v3.png", width=120)
        else:
            st.subheader("B&A")
    with col_tit:
        st.title("Inventory Intelligence")
        st.markdown("**Operational Excellence Consulting**")

    st.divider()

    # --- PANEL DE CONTROL ---
    with st.expander("⚙️ Parámetros del Proyecto", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            empresa_activa = st.text_input("🏢 Empresa", "Cliente Demo")
            tasa_wacc = st.number_input("Tasa WACC (%)", value=30.0) / 100
        with c2:
            nombre_reporte = st.text_input("📁 Nombre del Archivo", f"Reporte_{empresa_activa}")
            honorarios = st.number_input("Inversión Proyecto ($)", value=1000000.0)

    # --- SUBIDA DE ARCHIVO ---
    archivo = st.file_uploader("📂 Cargar base de inventario (Excel)", type=["xlsx", "xls"])

    if archivo:
        try:
            df = pd.read_excel(archivo)
            meses = [c for c in df.columns if c.startswith("Mes_")]
            
            # --- MOTOR DE CÁLCULO (Tu lógica validada) ---
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

            # KPIs
            inv_total = df["Inv_Total"].sum()
            lib_total = ((df["Stock_Actual"] - (df["Promedio_Mensual"] * df["ABC"].map({"A":2,"B":3,"C":4}))).clip(lower=0) * df["Costo_Unitario"]).sum()
            ahorro_anual = lib_total * tasa_wacc

            # Dashboard Visual Rápido para Celular
            st.subheader("📊 Resumen de Capital")
            kpi1, kpi2 = st.columns(2)
            kpi1.metric("Inventario Total", f"$ {inv_total:,.0f}")
            kpi2.metric("Cap. Liberable", f"$ {lib_total:,.0f}", delta=f"{(lib_total/inv_total)*100:.1f}%", delta_color="inverse")

            # --- GENERADOR EXCEL (Mantenemos tu lógica de XlsxWriter) ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, sheet_name="Analisis", index=False)
                # (Aquí iría el resto de tus formatos de ayer si los querés incluir)
            
            st.divider()
            st.download_button(
                label="📥 DESCARGAR REPORTE COMPLETO",
                data=output.getvalue(),
                file_name=f"{nombre_reporte}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"Hubo un error al procesar el archivo: {e}")