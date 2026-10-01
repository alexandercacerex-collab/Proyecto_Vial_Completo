from pathlib import Path
import math
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Dashboard Dinámico | Proyecto Vial",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent

# ============================================================
# ESTILO
# ============================================================
st.markdown("""
<style>
.block-container {padding-top:1rem; padding-bottom:2rem;}
[data-testid="stSidebar"] {border-right:1px solid #e5e7eb;}
.hero {
    padding:1.1rem 1.3rem;
    border:1px solid #e5e7eb;
    border-radius:16px;
    margin-bottom:1rem;
    background:linear-gradient(135deg,#f8fafc,#ffffff);
}
.hero-title {font-size:2rem;font-weight:800;margin:0;}
.hero-sub {color:#667085;margin-top:.35rem;}
.kpi {
    background:#fff;
    border:1px solid #e5e7eb;
    border-radius:14px;
    padding:14px 16px;
    box-shadow:0 1px 2px rgba(16,24,40,.05);
    min-height:110px;
}
.kpi-label {font-size:.78rem;color:#667085;font-weight:700;}
.kpi-value {font-size:1.5rem;font-weight:800;margin-top:.15rem;}
.kpi-sub {font-size:.78rem;color:#667085;margin-top:.2rem;}
.pill {
    display:inline-block;
    padding:3px 8px;
    border-radius:999px;
    font-size:.72rem;
    font-weight:700;
    background:#eff8ff;
    color:#175cd3;
    margin-top:.45rem;
}
.small {font-size:.82rem;color:#667085;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATOS
# ============================================================
@st.cache_data
def load_csv(name):
    return pd.read_csv(BASE / name)

rend = load_csv("rendimientos_cuadrillas.csv")
hist = load_csv("histograma_personal.csv")
curva = load_csv("curva_s_hh.csv")
personal = load_csv("personal_mensual.csv")
esc = load_csv("escenarios_roca_fija.csv")
resumen = load_csv("resumen_proyecto.csv")

# Tipos
for c in ["Rendimiento Diario (Día)","N° Cuadrillas Estimadas","Rendimiento Total Efectivo","Personal Equivalente / Día"]:
    if c in rend.columns:
        rend[c] = pd.to_numeric(rend[c], errors="coerce")

for c in ["Mes inicio","Mes fin","Personal equiv./día","N° cuadrillas"]:
    if c in hist.columns:
        hist[c] = pd.to_numeric(hist[c], errors="coerce")

for c in curva.columns:
    if c != "Mes":
        curva[c] = pd.to_numeric(curva[c], errors="coerce")
curva["Mes"] = pd.to_numeric(curva["Mes"], errors="coerce")

for c in personal.columns:
    personal[c] = pd.to_numeric(personal[c], errors="coerce")

for c in ["Eficiencia","Rend. real/cuadrilla","Cuadrillas req.","Capacidad total","Duración","Personal eq. redondeado"]:
    if c in esc.columns:
        esc[c] = pd.to_numeric(esc[c], errors="coerce")

rmap = dict(zip(resumen["Concepto"], resumen["Resultado"]))
def rnum(key, default=0):
    try:
        return float(rmap.get(key, default))
    except Exception:
        return default

vol_roca = rnum("Volumen de roca fija")
rend_original = rnum("Rendimiento original")
ef_base = rnum("Factor de eficiencia")
rend_efectivo = rnum("Rendimiento efectivo por cuadrilla")
cuad_base = int(rnum("Cuadrillas requeridas"))
cap_base = rnum("Rendimiento total efectivo")
dur_base = int(rnum("Duración recalculada"))

# ============================================================
# SIDEBAR / FILTROS
# ============================================================
st.sidebar.markdown("## 🎛️ Filtros dinámicos")

mes_ini, mes_fin = st.sidebar.slider(
    "Rango de meses",
    min_value=1,
    max_value=24,
    value=(1,24),
    step=1
)

criticidad = st.sidebar.multiselect(
    "Ruta crítica",
    options=["Sí","No"],
    default=["Sí","No"]
)

grupos = {
    "1.xx – Preliminares":"1.",
    "2.xx – Movimiento de tierras":"2.",
    "3.xx – Capas granulares":"3.",
    "4.xx – Pavimentos":"4.",
}
grupos_sel = st.sidebar.multiselect(
    "Grupos de partidas",
    options=list(grupos.keys()),
    default=list(grupos.keys())
)
prefixes = tuple(grupos[g] for g in grupos_sel)

rend_f = rend.copy()
if prefixes:
    rend_f = rend_f[rend_f["Item"].astype(str).str.startswith(prefixes)]
else:
    rend_f = rend_f.iloc[0:0]

rend_f = rend_f[rend_f["Ruta Crítica"].astype(str).isin(criticidad)]

partidas_disp = sorted(rend_f["Descripción de la Partida"].dropna().astype(str).unique())
partidas_sel = st.sidebar.multiselect(
    "Partidas",
    options=partidas_disp,
    default=partidas_disp
)
rend_f = rend_f[rend_f["Descripción de la Partida"].isin(partidas_sel)]

# Hist filtered by selected items + month overlap
items_sel = set(rend_f["Item"].astype(str))
hist_f = hist[hist["Item"].astype(str).isin(items_sel)].copy()
hist_f = hist_f[
    (hist_f["Mes fin"] >= mes_ini) &
    (hist_f["Mes inicio"] <= mes_fin)
]

curva_f = curva[(curva["Mes"] >= mes_ini) & (curva["Mes"] <= mes_fin)].copy()
personal_f = personal[(personal["Mes"] >= mes_ini) & (personal["Mes"] <= mes_fin)].copy()

st.sidebar.divider()
st.sidebar.markdown("### 📐 Métrica principal")
metrica = st.sidebar.radio(
    "Visualizar",
    ["Personal equivalente","Cuadrillas","Rendimiento efectivo"],
    label_visibility="collapsed"
)

st.sidebar.divider()
st.sidebar.markdown("### 🪨 Simulador roca fija")
sim_eff = st.sidebar.slider("Eficiencia (%)", 50, 95, int(round(ef_base*100)), 5)
sim_crews = st.sidebar.slider("Cuadrillas", 1, 10, cuad_base, 1)

# ============================================================
# DERIVADOS
# ============================================================
hh_periodo = float(curva_f["HH mensual"].sum()) if not curva_f.empty else 0
hh_total = float(curva["HH mensual"].sum())
hh_pct = hh_periodo / hh_total * 100 if hh_total else 0

personal_prom = float(personal_f["Personal equivalente/día"].mean()) if not personal_f.empty else 0
personal_max = float(personal_f["Personal equivalente/día"].max()) if not personal_f.empty else 0
mes_peak = int(personal_f.loc[personal_f["Personal equivalente/día"].idxmax(),"Mes"]) if not personal_f.empty else 0

crit_count = int(rend_f["Ruta Crítica"].astype(str).eq("Sí").sum()) if not rend_f.empty else 0
cuad_sum = float(rend_f["N° Cuadrillas Estimadas"].sum()) if not rend_f.empty else 0
peq_sum = float(rend_f["Personal Equivalente / Día"].sum()) if not rend_f.empty else 0

# Sim
sim_rend_cuad = rend_original * (sim_eff/100)
sim_cap = sim_rend_cuad * sim_crews
sim_days = math.ceil(vol_roca / sim_cap) if sim_cap > 0 else 0
delta_days = sim_days - dur_base

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="hero">
  <div class="hero-title">🏗️ Dashboard Dinámico de Planificación y Control</div>
  <div class="hero-sub">Proyecto vial · análisis interactivo de programación, HH, recursos, ruta crítica y recuperación de excavación en roca fija.</div>
</div>
""", unsafe_allow_html=True)

def card(label, value, sub="", pill=""):
    st.markdown(
        f"""
        <div class="kpi">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div>
          <div class="pill">{pill}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

c1,c2,c3,c4,c5,c6 = st.columns(6)
with c1: card("Periodo", f"M{mes_ini}–M{mes_fin}", f"{mes_fin-mes_ini+1} meses", "FILTRO")
with c2: card("HH del periodo", f"{hh_periodo:,.0f}", f"{hh_pct:.1f}% del total", "HORAS-HOMBRE")
with c3: card("Personal promedio", f"{personal_prom:.2f}", f"Pico {personal_max:.2f} en M{mes_peak}", "RECURSOS")
with c4: card("Partidas visibles", f"{len(rend_f)}", f"{crit_count} críticas", "ALCANCE")
with c5: card("Cuadrillas agregadas", f"{cuad_sum:,.0f}", f"Personal eq. {peq_sum:.2f}", "CAPACIDAD")
with c6: card("Roca fija simulada", f"{sim_days} días", f"{sim_cap:,.0f} m³/día", "WHAT-IF")

# ============================================================
# TABS
# ============================================================
t1,t2,t3,t4,t5,t6 = st.tabs([
    "📌 Ejecutivo",
    "📈 Curva S",
    "👷 Recursos",
    "🧭 Ruta crítica",
    "🪨 Simulador",
    "🔎 Explorador",
])

# ------------------------------------------------------------
# Ejecutivo
# ------------------------------------------------------------
with t1:
    left,right = st.columns([1.55,1])

    with left:
        if not curva_f.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=curva_f["Mes"],
                y=curva_f["% mensual"]*100,
                name="Avance mensual",
                opacity=.45
            ))
            fig.add_trace(go.Scatter(
                x=curva_f["Mes"],
                y=curva_f["% acumulado"]*100,
                mode="lines+markers",
                name="Avance acumulado",
                yaxis="y2"
            ))
            fig.update_layout(
                title="Curva S interactiva",
                xaxis=dict(title="Mes", dtick=1),
                yaxis=dict(title="% mensual"),
                yaxis2=dict(title="% acumulado", overlaying="y", side="right", range=[0,105]),
                hovermode="x unified",
                legend=dict(orientation="h", y=1.1),
                height=430,
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Lectura rápida")
        if personal_max > personal_prom * 1.35 and personal_prom > 0:
            st.warning(f"Se observa concentración de recursos en el mes {mes_peak}.")
        else:
            st.success("La carga de personal del periodo no presenta un pico extremo.")

        if crit_count > 0:
            st.error(f"Hay {crit_count} partidas críticas dentro del filtro actual.")
        else:
            st.info("No hay partidas críticas en la selección actual.")

        st.metric(
            "Simulación roca fija",
            f"{sim_days} días",
            delta=f"{delta_days:+d} días vs. plan base",
            delta_color="inverse"
        )

        st.markdown("##### Parámetros simulados")
        st.write(f"- Eficiencia: **{sim_eff}%**")
        st.write(f"- Cuadrillas: **{sim_crews}**")
        st.write(f"- Rendimiento por cuadrilla: **{sim_rend_cuad:,.1f} m³/día**")
        st.write(f"- Capacidad total: **{sim_cap:,.1f} m³/día**")

    st.markdown("#### Carga mensual del periodo seleccionado")
    fig_area = px.area(
        personal_f, x="Mes", y="Personal equivalente/día",
        markers=True
    )
    fig_area.update_layout(xaxis=dict(dtick=1), height=330)
    st.plotly_chart(fig_area, use_container_width=True)

# ------------------------------------------------------------
# Curva S
# ------------------------------------------------------------
with t2:
    st.subheader("Curva S y consumo de HH")
    if curva_f.empty:
        st.info("No hay datos para el rango seleccionado.")
    else:
        display_mode = st.radio(
            "Modo",
            ["Mensual + acumulado","Solo acumulado","HH mensuales"],
            horizontal=True
        )

        if display_mode == "Mensual + acumulado":
            fig = go.Figure()
            fig.add_trace(go.Bar(x=curva_f["Mes"],y=curva_f["% mensual"]*100,name="% mensual"))
            fig.add_trace(go.Scatter(x=curva_f["Mes"],y=curva_f["% acumulado"]*100,
                                     mode="lines+markers",name="% acumulado",yaxis="y2"))
            fig.update_layout(
                yaxis=dict(title="% mensual"),
                yaxis2=dict(title="% acumulado",overlaying="y",side="right",range=[0,105]),
                xaxis=dict(dtick=1),
                hovermode="x unified",
                height=470
            )
        elif display_mode == "Solo acumulado":
            fig = px.line(curva_f,x="Mes",y="% acumulado",markers=True)
            fig.update_traces(hovertemplate="Mes %{x}<br>Acumulado %{y:.2%}<extra></extra>")
            fig.update_layout(xaxis=dict(dtick=1),height=470)
        else:
            fig = px.bar(curva_f,x="Mes",y="HH mensual",text_auto=".0f")
            fig.update_layout(xaxis=dict(dtick=1),height=470)

        st.plotly_chart(fig,use_container_width=True)

        st.dataframe(
            curva_f,
            use_container_width=True,
            hide_index=True,
            column_config={
                "% mensual": st.column_config.NumberColumn(format="%.2f"),
                "% acumulado": st.column_config.NumberColumn(format="%.2f"),
            }
        )

# ------------------------------------------------------------
# Recursos
# ------------------------------------------------------------
with t3:
    st.subheader("Análisis dinámico de recursos")

    metric_map = {
        "Personal equivalente":"Personal Equivalente / Día",
        "Cuadrillas":"N° Cuadrillas Estimadas",
        "Rendimiento efectivo":"Rendimiento Total Efectivo",
    }
    ycol = metric_map[metrica]

    if rend_f.empty:
        st.info("No hay partidas con los filtros actuales.")
    else:
        sort_desc = st.toggle("Ordenar de mayor a menor", value=True)
        temp = rend_f.sort_values(ycol, ascending=not sort_desc).copy()

        fig = px.bar(
            temp,
            x=ycol,
            y="Descripción de la Partida",
            orientation="h",
            color="Ruta Crítica",
            hover_data=["Item","N° Cuadrillas Estimadas","Equipos / Maquinaria Principal"],
        )
        fig.update_layout(height=max(480, 30*len(temp)))
        st.plotly_chart(fig,use_container_width=True)

        st.markdown("#### Drill-down por partida")
        part = st.selectbox(
            "Selecciona una partida",
            temp["Descripción de la Partida"].tolist()
        )
        row = temp[temp["Descripción de la Partida"] == part].iloc[0]

        d1,d2,d3,d4 = st.columns(4)
        d1.metric("Rendimiento diario", f"{row['Rendimiento Diario (Día)']:,.2f}")
        d2.metric("Cuadrillas", f"{row['N° Cuadrillas Estimadas']:,.0f}")
        d3.metric("Rendimiento efectivo", f"{row['Rendimiento Total Efectivo']:,.2f}")
        d4.metric("Personal eq./día", f"{row['Personal Equivalente / Día']:,.2f}")

        st.write("**Equipo principal:**", row.get("Equipos / Maquinaria Principal",""))
        st.write("**Observación:**", row.get("Observación",""))

# ------------------------------------------------------------
# Ruta crítica
# ------------------------------------------------------------
with t4:
    st.subheader("Ruta crítica dinámica")
    crit = rend_f[rend_f["Ruta Crítica"].astype(str).eq("Sí")].copy()

    if crit.empty:
        st.info("No hay partidas críticas dentro del filtro actual.")
    else:
        crit_items = set(crit["Item"].astype(str))
        g = hist_f[hist_f["Item"].astype(str).isin(crit_items)].copy()
        g = g.dropna(subset=["Mes inicio","Mes fin"])
        g["Inicio"] = pd.to_datetime("2026-01-01") + pd.to_timedelta((g["Mes inicio"]-1)*30, unit="D")
        g["Fin"] = pd.to_datetime("2026-01-01") + pd.to_timedelta(g["Mes fin"]*30, unit="D")

        color_by = st.selectbox("Colorear por", ["N° cuadrillas","Personal equiv./día"])
        fig = px.timeline(
            g.sort_values("Mes inicio"),
            x_start="Inicio",
            x_end="Fin",
            y="Descripción",
            color=color_by,
            hover_data=["Item","Mes inicio","Mes fin","N° cuadrillas","Personal equiv./día"]
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=max(480,35*len(g)))
        st.plotly_chart(fig,use_container_width=True)

# ------------------------------------------------------------
# Simulador roca fija
# ------------------------------------------------------------
with t5:
    st.subheader("Simulador interactivo de recuperación de roca fija")

    a,b,c,d = st.columns(4)
    a.metric("Volumen",f"{vol_roca:,.2f} m³")
    b.metric("Rendimiento base",f"{rend_original:,.0f} m³/día/cuadrilla")
    c.metric("Plan base",f"{cuad_base} cuadrillas · {ef_base*100:.0f}%")
    d.metric("Duración base",f"{dur_base} días")

    st.markdown("#### Resultado de la simulación")
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Eficiencia",f"{sim_eff}%")
    s2.metric("Cuadrillas",f"{sim_crews}")
    s3.metric("Capacidad",f"{sim_cap:,.0f} m³/día")
    s4.metric("Duración",f"{sim_days} días",delta=f"{delta_days:+d} días",delta_color="inverse")

    comp = pd.DataFrame({
        "Escenario":["Plan base","Simulación"],
        "Eficiencia (%)":[ef_base*100,sim_eff],
        "Cuadrillas":[cuad_base,sim_crews],
        "Capacidad total":[cap_base,sim_cap],
        "Duración":[dur_base,sim_days],
    })
    fig = px.bar(
        comp,x="Escenario",y="Duración",
        text_auto=".0f",
        hover_data=["Eficiencia (%)","Cuadrillas","Capacidad total"]
    )
    st.plotly_chart(fig,use_container_width=True)

    st.markdown("#### Mapa de sensibilidad: duración (días)")
    efficiencies = list(range(50,100,5))
    crews = list(range(1,11))
    z = []
    for e in efficiencies:
        row = []
        for q in crews:
            cap = rend_original*(e/100)*q
            row.append(math.ceil(vol_roca/cap))
        z.append(row)

    heat = go.Figure(data=go.Heatmap(
        z=z,
        x=crews,
        y=efficiencies,
        colorbar=dict(title="Días"),
        hovertemplate="Eficiencia %{y}%<br>Cuadrillas %{x}<br>Duración %{z} días<extra></extra>"
    ))
    heat.update_layout(
        xaxis_title="N° de cuadrillas",
        yaxis_title="Eficiencia (%)",
        height=470
    )
    st.plotly_chart(heat,use_container_width=True)

    st.markdown("#### Tabla editable de escenarios")
    default_scen = pd.DataFrame({
        "Nombre":["Conservador","Base","Acelerado"],
        "Eficiencia (%)":[65,75,85],
        "Cuadrillas":[7,6,6],
    })
    edited = st.data_editor(
        default_scen,
        num_rows="dynamic",
        use_container_width=True,
        key="scenario_editor"
    )
    if not edited.empty:
        calc = edited.copy()
        calc["Rend./cuadrilla"] = rend_original*(calc["Eficiencia (%)"]/100)
        calc["Capacidad total"] = calc["Rend./cuadrilla"]*calc["Cuadrillas"]
        calc["Duración (días)"] = np.ceil(vol_roca/calc["Capacidad total"]).astype(int)
        st.dataframe(calc,use_container_width=True,hide_index=True)

# ------------------------------------------------------------
# Explorador
# ------------------------------------------------------------
with t6:
    st.subheader("Explorador de datos")

    dataset_name = st.selectbox(
        "Dataset",
        [
            "Rendimientos y cuadrillas",
            "Histograma",
            "Curva S",
            "Personal mensual",
            "Escenarios roca fija",
            "Resumen",
        ]
    )

    datasets = {
        "Rendimientos y cuadrillas": rend_f,
        "Histograma": hist_f,
        "Curva S": curva_f,
        "Personal mensual": personal_f,
        "Escenarios roca fija": esc,
        "Resumen": resumen,
    }

    d = datasets[dataset_name].copy()

    search = st.text_input("Buscar texto")
    if search:
        mask = d.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)
        ).any(axis=1)
        d = d[mask]

    st.write(f"**Registros visibles:** {len(d)}")
    st.dataframe(d,use_container_width=True,hide_index=True)

    st.download_button(
        "⬇️ Descargar filtro actual",
        d.to_csv(index=False).encode("utf-8-sig"),
        file_name="datos_filtrados.csv",
        mime="text/csv"
    )

st.divider()
st.caption(
    "Dashboard académico interactivo generado a partir del archivo de planificación del proyecto vial. "
    "Los filtros y simuladores actualizan los indicadores en tiempo real."
)
