from pathlib import Path
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Dashboard Ejecutivo | Proyecto Vial",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent

# -------------------- ESTILO --------------------
st.markdown("""
<style>
:root {
  --bg-soft: #f7f9fc;
  --card: #ffffff;
  --border: #e5e7eb;
  --text-soft: #667085;
}
.block-container {
  padding-top: 1.1rem;
  padding-bottom: 2rem;
}
[data-testid="stSidebar"] {
  border-right: 1px solid #e5e7eb;
}
.hero {
  padding: 1.1rem 1.25rem;
  border: 1px solid var(--border);
  border-radius: 16px;
  margin-bottom: 1rem;
  background: linear-gradient(135deg, rgba(248,250,252,.98), rgba(255,255,255,.98));
}
.hero h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.15;
}
.hero p {
  margin: .45rem 0 0 0;
  color: var(--text-soft);
}
.kpi-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 16px;
  min-height: 114px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04);
}
.kpi-label {
  font-size: .82rem;
  color: #667085;
  font-weight: 600;
  margin-bottom: .25rem;
}
.kpi-value {
  font-size: 1.55rem;
  font-weight: 750;
  color: #101828;
}
.kpi-sub {
  margin-top: .25rem;
  font-size: .80rem;
  color: #667085;
}
.badge-green, .badge-amber, .badge-red, .badge-blue {
  display:inline-block;
  padding:4px 9px;
  border-radius:999px;
  font-size:.75rem;
  font-weight:700;
}
.badge-green{background:#ecfdf3;color:#027a48;}
.badge-amber{background:#fffaeb;color:#b54708;}
.badge-red{background:#fef3f2;color:#b42318;}
.badge-blue{background:#eff8ff;color:#175cd3;}
.section-note {
  color:#667085;
  font-size:.86rem;
}
div[data-testid="stTabs"] button {
  font-weight: 650;
}
</style>
""", unsafe_allow_html=True)

# -------------------- CARGA --------------------
@st.cache_data
def load(name):
    return pd.read_csv(BASE / name)

rend = load("rendimientos_cuadrillas.csv")
hist = load("histograma_personal.csv")
curva = load("curva_s_hh.csv")
personal = load("personal_mensual.csv")
esc = load("escenarios_roca_fija.csv")
resumen = load("resumen_proyecto.csv")

# Tipificación
num_cols_r = [
    "Rendimiento Diario (Día)", "N° Cuadrillas Estimadas",
    "Rendimiento Total Efectivo", "Personal Equivalente / Día"
]
for c in num_cols_r:
    if c in rend.columns:
        rend[c] = pd.to_numeric(rend[c], errors="coerce")

for c in ["Mes inicio", "Mes fin", "Personal equiv./día", "N° cuadrillas"]:
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

# Resumen
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
cuad_base = rnum("Cuadrillas requeridas")
cap_base = rnum("Rendimiento total efectivo")
dur_base = rnum("Duración recalculada")
peq_roca = rnum("Personal equivalente redondeado")

# Derivados
hh_total = float(curva["HH mensual"].sum())
peak_row = personal.loc[personal["Personal equivalente/día"].idxmax()]
personal_peak = float(peak_row["Personal equivalente/día"])
peak_month = int(peak_row["Mes"])
personal_avg = float(personal["Personal equivalente/día"].mean())
critical_count = int(rend["Ruta Crítica"].astype(str).str.strip().str.lower().eq("sí").sum())
total_partidas = len(rend)
critical_pct = critical_count / total_partidas * 100 if total_partidas else 0

# -------------------- SIDEBAR --------------------
st.sidebar.markdown("## ⚙️ Control del dashboard")
st.sidebar.caption("Filtros y visualización")

crit_opt = st.sidebar.radio(
    "Ruta crítica",
    ["Todas", "Solo críticas", "No críticas"],
    index=0,
)

familias = {
    "Todas": None,
    "1.xx – Preliminares": "1.",
    "2.xx – Movimiento de tierras": "2.",
    "3.xx – Capas granulares": "3.",
    "4.xx – Pavimentos": "4.",
}
familia = st.sidebar.selectbox("Grupo de partidas", list(familias.keys()))

rend_f = rend.copy()
hist_f = hist.copy()

if crit_opt == "Solo críticas":
    mask = rend_f["Ruta Crítica"].astype(str).str.strip().str.lower().eq("sí")
    rend_f = rend_f[mask]
elif crit_opt == "No críticas":
    mask = ~rend_f["Ruta Crítica"].astype(str).str.strip().str.lower().eq("sí")
    rend_f = rend_f[mask]

prefix = familias[familia]
if prefix:
    rend_f = rend_f[rend_f["Item"].astype(str).str.startswith(prefix)]
    hist_f = hist_f[hist_f["Item"].astype(str).str.startswith(prefix)]

st.sidebar.divider()
st.sidebar.markdown("### 🪨 Simulador roca fija")
sim_eff = st.sidebar.slider(
    "Eficiencia (%)", 50, 95, int(round(ef_base*100)), 5
)
sim_crews = st.sidebar.slider(
    "Número de cuadrillas", 1, 10, int(cuad_base), 1
)

sim_eff_dec = sim_eff / 100
sim_rend_cuad = rend_original * sim_eff_dec
sim_cap = sim_rend_cuad * sim_crews
sim_days = math.ceil(vol_roca / sim_cap) if sim_cap > 0 else 0
delta_days = sim_days - int(dur_base)

# -------------------- HERO --------------------
st.markdown("""
<div class="hero">
  <h1>🏗️ Dashboard Ejecutivo de Planificación y Control</h1>
  <p>Proyecto vial · Horizonte contractual: 720 días / 24 meses · Control de HH, recursos, rendimientos, ruta crítica y recuperación de roca fija.</p>
</div>
""", unsafe_allow_html=True)

# -------------------- KPI CARDS --------------------
def card(label, value, sub, badge=None, badge_class="badge-blue"):
    badge_html = f'<span class="{badge_class}">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div>
          <div style="margin-top:7px">{badge_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

c1,c2,c3,c4,c5,c6 = st.columns(6)
with c1:
    card("Duración contractual", "720 días", "24 meses de programación", "BASE", "badge-blue")
with c2:
    card("HH programadas", f"{hh_total:,.0f}", "Horas-Hombre acumuladas", "RECURSOS", "badge-blue")
with c3:
    card("Personal pico", f"{personal_peak:.2f}", f"Mes {peak_month}", "PICO", "badge-amber")
with c4:
    card("Ruta crítica", f"{critical_count}/{total_partidas}", f"{critical_pct:.0f}% de las partidas", "CRÍTICO", "badge-red")
with c5:
    card("Roca fija", f"{vol_roca:,.0f} m³", f"{cuad_base:.0f} cuadrillas base", "RECUPERACIÓN", "badge-amber")
with c6:
    card("Duración roca fija", f"{dur_base:.0f} días", f"{cap_base:,.0f} m³/día", "PLAN BASE", "badge-green")

# -------------------- TABS --------------------
tabs = st.tabs([
    "📌 Resumen",
    "📈 Curva S",
    "👷 Recursos",
    "🧭 Ruta crítica",
    "🪨 Roca fija",
    "📋 Datos",
])

# ========== RESUMEN ==========
with tabs[0]:
    st.subheader("Resumen ejecutivo")
    a,b = st.columns([1.45, 1])

    with a:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curva["Mes"],
            y=curva["% acumulado"]*100,
            mode="lines+markers",
            name="Avance programado acumulado",
            line=dict(width=3),
        ))
        fig.update_layout(
            title="Curva S programada por consumo de Horas-Hombre",
            xaxis_title="Mes",
            yaxis_title="Avance acumulado (%)",
            xaxis=dict(dtick=1),
            yaxis=dict(range=[0,105]),
            hovermode="x unified",
            margin=dict(l=20,r=20,t=55,b=20),
            height=430,
            legend=dict(orientation="h", y=1.10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with b:
        st.markdown("#### Estado de control")
        st.markdown(
            f"""
            **Ruta crítica:** {critical_count} partidas identificadas  
            **Personal promedio:** {personal_avg:.2f} personas equivalentes/día  
            **Personal máximo:** {personal_peak:.2f} en el mes {peak_month}  
            **Roca fija:** {vol_roca:,.2f} m³  
            **Plan base roca:** {cuad_base:.0f} cuadrillas · {cap_base:,.0f} m³/día · {dur_base:.0f} días
            """
        )

        if critical_pct >= 50:
            st.warning(
                "La programación concentra una proporción alta de partidas en ruta crítica. "
                "Conviene priorizar seguimiento de producción, equipos y restricciones en estas actividades."
            )
        else:
            st.success("La proporción de partidas críticas es moderada dentro del conjunto analizado.")

    st.markdown("#### Carga mensual de personal")
    fig_p = px.area(
        personal,
        x="Mes",
        y="Personal equivalente/día",
        markers=True,
    )
    fig_p.update_layout(
        xaxis=dict(dtick=1),
        yaxis_title="Personal equivalente/día",
        margin=dict(l=20,r=20,t=20,b=20),
        height=330,
    )
    st.plotly_chart(fig_p, use_container_width=True)

# ========== CURVA S ==========
with tabs[1]:
    st.subheader("Curva S y distribución temporal de HH")
    c1,c2 = st.columns([1.4,1])

    with c1:
        fig_s = go.Figure()
        fig_s.add_trace(go.Bar(
            x=curva["Mes"],
            y=curva["% mensual"]*100,
            name="% mensual",
            opacity=.55,
        ))
        fig_s.add_trace(go.Scatter(
            x=curva["Mes"],
            y=curva["% acumulado"]*100,
            mode="lines+markers",
            name="% acumulado",
            yaxis="y2",
        ))
        fig_s.update_layout(
            title="Avance mensual vs. acumulado",
            xaxis=dict(title="Mes", dtick=1),
            yaxis=dict(title="% mensual"),
            yaxis2=dict(
                title="% acumulado",
                overlaying="y",
                side="right",
                range=[0,105],
            ),
            hovermode="x unified",
            height=450,
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig_s, use_container_width=True)

    with c2:
        fig_hh = px.bar(
            curva,
            x="Mes",
            y="HH mensual",
            text_auto=".0f",
            title="HH programadas por mes",
        )
        fig_hh.update_layout(
            xaxis=dict(dtick=1),
            yaxis_title="HH",
            height=450,
        )
        st.plotly_chart(fig_hh, use_container_width=True)

    st.markdown(
        "<div class='section-note'>La Curva S mostrada corresponde a la distribución programada de Horas-Hombre del archivo fuente; no representa valorización económica ni avance físico real.</div>",
        unsafe_allow_html=True,
    )

# ========== RECURSOS ==========
with tabs[2]:
    st.subheader("Recursos, cuadrillas y carga de trabajo")

    a,b = st.columns([1.25,1])

    with a:
        tmp = rend_f.dropna(subset=["Personal Equivalente / Día"]).copy()
        tmp = tmp.sort_values("Personal Equivalente / Día")
        fig_res = px.bar(
            tmp,
            x="Personal Equivalente / Día",
            y="Descripción de la Partida",
            orientation="h",
            color="Ruta Crítica",
            title="Personal equivalente por partida",
            hover_data=["Item","N° Cuadrillas Estimadas","Equipos / Maquinaria Principal"],
        )
        fig_res.update_layout(height=max(470, 31*len(tmp)))
        st.plotly_chart(fig_res, use_container_width=True)

    with b:
        top = (
            rend_f[["Descripción de la Partida","Personal Equivalente / Día","N° Cuadrillas Estimadas","Ruta Crítica"]]
            .dropna(subset=["Personal Equivalente / Día"])
            .sort_values("Personal Equivalente / Día", ascending=False)
            .head(8)
        )
        st.markdown("#### Partidas con mayor carga")
        st.dataframe(
            top,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Personal Equivalente / Día": st.column_config.NumberColumn(format="%.2f"),
                "N° Cuadrillas Estimadas": st.column_config.NumberColumn(format="%d"),
            }
        )

    st.markdown("#### Histograma mensual de personal")
    fig_personal = px.bar(
        personal,
        x="Mes",
        y="Personal equivalente/día",
        text_auto=".2f",
    )
    fig_personal.update_layout(
        xaxis=dict(dtick=1),
        yaxis_title="Personal equivalente/día",
        height=370,
    )
    st.plotly_chart(fig_personal, use_container_width=True)

# ========== RUTA CRÍTICA ==========
with tabs[3]:
    st.subheader("Ruta crítica y secuencia temporal")

    crit = rend[rend["Ruta Crítica"].astype(str).str.strip().str.lower().eq("sí")].copy()
    crit_items = set(crit["Item"].astype(str))
    gantt = hist[hist["Item"].astype(str).isin(crit_items)].copy()
    gantt = gantt.dropna(subset=["Mes inicio","Mes fin"])
    gantt["Inicio"] = pd.to_datetime("2026-01-01") + pd.to_timedelta((gantt["Mes inicio"]-1)*30, unit="D")
    gantt["Fin"] = pd.to_datetime("2026-01-01") + pd.to_timedelta(gantt["Mes fin"]*30, unit="D")

    fig_g = px.timeline(
        gantt.sort_values("Mes inicio"),
        x_start="Inicio",
        x_end="Fin",
        y="Descripción",
        color="N° cuadrillas",
        hover_data=["Item","Mes inicio","Mes fin","Personal equiv./día"],
        title="Secuencia aproximada de partidas críticas por mes",
    )
    fig_g.update_yaxes(autorange="reversed")
    fig_g.update_layout(height=max(480, 34*len(gantt)))
    st.plotly_chart(fig_g, use_container_width=True)

    st.caption(
        "La línea de tiempo es una representación mensual derivada de Mes inicio / Mes fin del histograma; "
        "se usa para visualización ejecutiva y no sustituye el cronograma CPM de detalle."
    )

    crit_cols = [
        "Item","Descripción de la Partida","Rendimiento Diario (Día)",
        "N° Cuadrillas Estimadas","Rendimiento Total Efectivo",
        "Personal Equivalente / Día","Equipos / Maquinaria Principal"
    ]
    st.dataframe(crit[crit_cols], use_container_width=True, hide_index=True)

# ========== ROCA FIJA ==========
with tabs[4]:
    st.subheader("Recuperación de excavación en roca fija")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Volumen", f"{vol_roca:,.2f} m³")
    c2.metric("Rendimiento original", f"{rend_original:,.0f} m³/día/cuadrilla")
    c3.metric("Escenario base", f"{ef_base*100:.0f}% · {cuad_base:.0f} cuadrillas")
    c4.metric("Duración base", f"{dur_base:.0f} días")

    st.markdown("#### Simulador interactivo")
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Eficiencia simulada", f"{sim_eff}%")
    s2.metric("Cuadrillas", f"{sim_crews}")
    s3.metric("Capacidad total", f"{sim_cap:,.0f} m³/día")

    if delta_days < 0:
        s4.metric("Duración", f"{sim_days} días", delta=f"{abs(delta_days)} días menos")
    elif delta_days > 0:
        s4.metric("Duración", f"{sim_days} días", delta=f"{delta_days} días más", delta_color="inverse")
    else:
        s4.metric("Duración", f"{sim_days} días", delta="igual al plan base")

    sim_table = pd.DataFrame({
        "Escenario": ["Plan base", "Simulación"],
        "Eficiencia (%)": [ef_base*100, sim_eff],
        "Cuadrillas": [cuad_base, sim_crews],
        "Rendimiento/cuadrilla": [rend_efectivo, sim_rend_cuad],
        "Capacidad total": [cap_base, sim_cap],
        "Duración": [dur_base, sim_days],
    })

    fig_sim = px.bar(
        sim_table,
        x="Escenario",
        y="Duración",
        text_auto=".0f",
        hover_data=["Eficiencia (%)","Cuadrillas","Capacidad total"],
        title="Comparación plan base vs. simulación",
    )
    st.plotly_chart(fig_sim, use_container_width=True)

    st.markdown("#### Escenarios precalculados del archivo")
    esc_v = esc.copy()
    esc_v["Eficiencia (%)"] = esc_v["Eficiencia"]*100

    fig_esc = px.scatter(
        esc_v,
        x="Eficiencia (%)",
        y="Duración",
        size="Cuadrillas req.",
        color="Escenario",
        hover_data=["Rend. real/cuadrilla","Capacidad total","Personal eq. redondeado"],
    )
    fig_esc.update_yaxes(autorange="reversed", title="Duración (días)")
    st.plotly_chart(fig_esc, use_container_width=True)

    st.dataframe(
        esc_v[[
            "Escenario","Eficiencia (%)","Rend. real/cuadrilla",
            "Cuadrillas req.","Capacidad total","Duración",
            "Personal eq. redondeado"
        ]],
        use_container_width=True,
        hide_index=True,
    )

# ========== DATOS ==========
with tabs[5]:
    st.subheader("Datos y trazabilidad")

    option = st.selectbox(
        "Conjunto de datos",
        [
            "Rendimientos y cuadrillas",
            "Histograma de personal",
            "Curva S HH",
            "Personal mensual",
            "Escenarios roca fija",
            "Resumen del proyecto",
        ],
    )

    datasets = {
        "Rendimientos y cuadrillas": rend,
        "Histograma de personal": hist,
        "Curva S HH": curva,
        "Personal mensual": personal,
        "Escenarios roca fija": esc,
        "Resumen del proyecto": resumen,
    }

    data = datasets[option]
    st.dataframe(data, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Descargar vista en CSV",
        data=data.to_csv(index=False).encode("utf-8-sig"),
        file_name=option.lower().replace(" ","_") + ".csv",
        mime="text/csv",
    )

    st.info(
        "El Excel original se conserva dentro del repositorio como fuente de trazabilidad. "
        "La aplicación usa CSV preparados para mejorar estabilidad y velocidad de despliegue en Streamlit."
    )

st.divider()
st.caption(
    "Dashboard académico de planificación y control. "
    "Los indicadores son derivados exclusivamente del archivo fuente proporcionado."
)
