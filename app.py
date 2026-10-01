from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Control de Proyecto Vial",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent

# ---------- Theme / CSS ----------
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {
    background: rgba(245,247,250,.9);
    border: 1px solid #e5e7eb;
    padding: 14px 16px;
    border-radius: 12px;
}
[data-testid="stMetricLabel"] {font-weight: 600;}
div[data-testid="stTabs"] button {font-weight: 600;}
.small-note {color:#6b7280;font-size:.88rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def cargar_csv(nombre):
    return pd.read_csv(BASE / nombre)

rend = cargar_csv("rendimientos_cuadrillas.csv")
hist = cargar_csv("histograma_personal.csv")
curva = cargar_csv("curva_s_hh.csv")
personal = cargar_csv("personal_mensual.csv")
escenarios = cargar_csv("escenarios_roca_fija.csv")
resumen = cargar_csv("resumen_proyecto.csv")

# Normalize numeric columns
for df in (rend, hist, curva, personal, escenarios, resumen):
    for c in df.columns:
        if c not in ["Descripción de la Partida","Descripción","Equipos / Maquinaria Principal",
                     "Ruta Crítica","Observación","Unidad","Unid.","Escenario","Concepto"]:
            try:
                df[c] = pd.to_numeric(df[c])
            except Exception:
                pass

# Header
st.title("🏗️ Dashboard de Planificación y Control – Proyecto Vial")
st.caption("Fuente: Proyecto_Vial_Completo_Actualizado(1).xlsx | Horizonte de planificación: 720 días / 24 meses")

# Sidebar
st.sidebar.header("Panel de control")
solo_critica = st.sidebar.toggle("Mostrar solo Ruta Crítica", value=False)

rend_f = rend.copy()
if solo_critica and "Ruta Crítica" in rend_f.columns:
    rend_f = rend_f[rend_f["Ruta Crítica"].astype(str).str.lower().eq("sí")]

descripciones = ["Todas"] + sorted(rend_f["Descripción de la Partida"].dropna().astype(str).unique().tolist())
partida_sel = st.sidebar.selectbox("Partida", descripciones)

if partida_sel != "Todas":
    rend_f = rend_f[rend_f["Descripción de la Partida"] == partida_sel]

# KPIs from workbook
duracion_dias = 720
meses = 24
hh_total = float(curva["HH mensual"].sum())
personal_prom = float(curva["Personal equiv./día"].mean())
personal_max = float(curva["Personal equiv./día"].max())

r_roca = resumen.set_index("Concepto")["Resultado"]
vol_roca = float(r_roca.get("Volumen de roca fija", 0))
rend_roca = float(r_roca.get("Rendimiento total efectivo", 0))
dias_roca = float(r_roca.get("Duración recalculada", 0))
cuad_roca = float(r_roca.get("Cuadrillas requeridas", 0))

k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("Duración", f"{duracion_dias:,.0f} días")
k2.metric("Horizonte", f"{meses} meses")
k3.metric("HH programadas", f"{hh_total:,.0f}")
k4.metric("Personal promedio", f"{personal_prom:.2f}")
k5.metric("Personal máximo", f"{personal_max:.2f}")
k6.metric("Cuadrillas roca fija", f"{cuad_roca:.0f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Resumen ejecutivo",
    "📈 Curva S e Histograma",
    "👷 Rendimientos y Cuadrillas",
    "🪨 Roca fija",
    "📋 Datos",
])

with tab1:
    st.subheader("Resumen ejecutivo")
    a,b = st.columns([1.45,1])

    with a:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curva["Mes"], y=curva["% acumulado"]*100,
            mode="lines+markers", name="Avance acumulado HH"
        ))
        fig.update_layout(
            title="Curva S programada por Horas-Hombre",
            xaxis_title="Mes",
            yaxis_title="Avance acumulado (%)",
            yaxis=dict(range=[0,105]),
            hovermode="x unified",
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    with b:
        st.markdown("#### Indicadores de recuperación – roca fija")
        c1,c2 = st.columns(2)
        c1.metric("Volumen", f"{vol_roca:,.2f} m³")
        c2.metric("Rendimiento efectivo", f"{rend_roca:,.0f} m³/día")
        c1.metric("Duración recalculada", f"{dias_roca:.0f} días")
        c2.metric("Cuadrillas requeridas", f"{cuad_roca:.0f}")

        st.info(
            "El escenario base del archivo considera 75% de eficiencia y "
            "6 cuadrillas para recuperar el atraso inicial de 14 días."
        )

    st.markdown("#### Perfil mensual de recursos")
    figp = px.area(
        personal, x="Mes", y="Personal equivalente/día",
        markers=True,
        title="Personal equivalente programado por mes"
    )
    figp.update_layout(height=360, xaxis=dict(dtick=1))
    st.plotly_chart(figp, use_container_width=True)

with tab2:
    c1,c2 = st.columns(2)

    with c1:
        fig_hh = px.bar(
            curva, x="Mes", y="HH mensual",
            title="Horas-Hombre mensuales programadas",
            text_auto=".0f"
        )
        fig_hh.update_layout(height=420, xaxis=dict(dtick=1))
        st.plotly_chart(fig_hh, use_container_width=True)

    with c2:
        fig_per = px.line(
            personal, x="Mes", y="Personal equivalente/día",
            markers=True,
            title="Histograma de personal equivalente"
        )
        fig_per.update_layout(height=420, xaxis=dict(dtick=1))
        st.plotly_chart(fig_per, use_container_width=True)

    st.subheader("Curva S – avance mensual y acumulado")
    curva_long = curva.melt(
        id_vars=["Mes"],
        value_vars=["% mensual","% acumulado"],
        var_name="Serie",
        value_name="Porcentaje"
    )
    curva_long["Porcentaje"] = curva_long["Porcentaje"] * 100
    fig_s = px.line(
        curva_long, x="Mes", y="Porcentaje",
        color="Serie", markers=True
    )
    fig_s.update_layout(
        yaxis_title="%",
        xaxis=dict(dtick=1),
        height=430
    )
    st.plotly_chart(fig_s, use_container_width=True)

    st.dataframe(
        curva.style.format({
            "Personal equiv./día":"{:.2f}",
            "HH mensual":"{:,.0f}",
            "HH acumulada":"{:,.0f}",
            "% mensual":"{:.2%}",
            "% acumulado":"{:.2%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.subheader("Matriz de rendimientos y cuadrillas")

    n_partidas = len(rend_f)
    rutas = (rend_f["Ruta Crítica"].astype(str).str.lower()=="sí").sum() if "Ruta Crítica" in rend_f.columns else 0
    cuad_total = pd.to_numeric(rend_f["N° Cuadrillas Estimadas"], errors="coerce").sum()
    peq = pd.to_numeric(rend_f["Personal Equivalente / Día"], errors="coerce").sum()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Partidas mostradas", f"{n_partidas}")
    c2.metric("En ruta crítica", f"{rutas}")
    c3.metric("Cuadrillas estimadas", f"{cuad_total:,.0f}")
    c4.metric("Personal eq. agregado", f"{peq:.2f}")

    # chart selected subset
    tmp = rend_f.copy()
    tmp["Personal Equivalente / Día"] = pd.to_numeric(tmp["Personal Equivalente / Día"], errors="coerce")
    tmp = tmp.dropna(subset=["Personal Equivalente / Día"])

    fig_r = px.bar(
        tmp.sort_values("Personal Equivalente / Día"),
        x="Personal Equivalente / Día",
        y="Descripción de la Partida",
        orientation="h",
        color="Ruta Crítica" if "Ruta Crítica" in tmp.columns else None,
        title="Personal equivalente por partida"
    )
    fig_r.update_layout(height=max(450, 25*len(tmp)))
    st.plotly_chart(fig_r, use_container_width=True)

    mostrar_cols = [
        "Item","Descripción de la Partida","Unid.","Rendimiento Diario (Día)",
        "N° Cuadrillas Estimadas","Ruta Crítica","Rendimiento Total Efectivo",
        "Personal Equivalente / Día","Equipos / Maquinaria Principal","Observación"
    ]
    mostrar_cols = [c for c in mostrar_cols if c in rend_f.columns]
    st.dataframe(rend_f[mostrar_cols], use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Recálculo de excavación en roca fija")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Volumen total", f"{vol_roca:,.2f} m³")
    c2.metric("Rendimiento base", "250 m³/día/cuadrilla")
    c3.metric("Retraso inicial", "14 días")
    c4.metric("Escenario base", "75% eficiencia")

    st.markdown("#### Comparación de escenarios")
    esc = escenarios.copy()
    esc["Eficiencia (%)"] = esc["Eficiencia"] * 100

    fig_e = px.bar(
        esc,
        x="Escenario",
        y="Duración",
        color="Cuadrillas req.",
        text_auto=".0f",
        title="Duración estimada por escenario"
    )
    st.plotly_chart(fig_e, use_container_width=True)

    fig_c = px.scatter(
        esc,
        x="Eficiencia (%)",
        y="Capacidad total",
        size="Cuadrillas req.",
        color="Escenario",
        hover_data=["Duración","Personal eq. redondeado"],
        title="Capacidad diaria vs. eficiencia"
    )
    st.plotly_chart(fig_c, use_container_width=True)

    st.dataframe(
        esc[[
            "Escenario","Eficiencia (%)","Rend. real/cuadrilla",
            "Cuadrillas req.","Capacidad total","Duración",
            "Personal eq. redondeado"
        ]],
        use_container_width=True,
        hide_index=True
    )

    st.warning(
        "Interpretación del archivo: el plan de recuperación utiliza 6 cuadrillas "
        "y una capacidad efectiva de 1,125 m³/día, con una duración recalculada de 101 días."
    )

with tab5:
    st.subheader("Datos utilizados")
    dataset = st.selectbox(
        "Selecciona el conjunto de datos",
        ["Rendimientos y cuadrillas","Histograma","Curva S","Escenarios roca fija","Resumen"]
    )

    mapping = {
        "Rendimientos y cuadrillas": rend,
        "Histograma": hist,
        "Curva S": curva,
        "Escenarios roca fija": escenarios,
        "Resumen": resumen,
    }
    data = mapping[dataset]
    st.dataframe(data, use_container_width=True, hide_index=True)

    st.download_button(
        "Descargar vista en CSV",
        data=data.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{dataset.lower().replace(' ','_')}.csv",
        mime="text/csv",
    )

st.divider()
st.markdown(
    "<div class='small-note'>Dashboard académico generado a partir del archivo de planificación del proyecto vial. "
    "La Curva S representa consumo programado de Horas-Hombre, no valorización económica.</div>",
    unsafe_allow_html=True
)
