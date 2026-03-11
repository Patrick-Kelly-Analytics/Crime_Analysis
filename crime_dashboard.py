import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(page_title="Crime Stats Analyser", page_icon="🔍", layout="wide")

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

MONTH_SHEET_MAP = {
    "Jan": "JAN", "Feb": "FEB", "Mar": "MAR", "Apr": "APR",
    "May": "MAY", "Jun": "JUN", "Jul": "JUL", "Aug": "AUG",
    "Sep": "SEP", "Oct": "OCT", "Nov": "NOV", "Dec": "DEC",
}

CRIME_TYPES = [
    "Burglary", "ASB", "Robbery", "Vehicle Crime",
    "Violent Crime and Sexual Offences", "Public Disorder & Weapons",
    "Shop-lifting", "Criminal Damage & Arson", "Other Theft",
    "Drugs", "Other Crime",
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CUSTOM CSS  (adapts to light / dark via CSS variables)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── Theme-adaptive variables ── */
:root {
    --kpi-bg: #f4f6f8;
    --kpi-bg2: #edf0f4;
    --kpi-border: #d1d5db;
    --kpi-border-hover: #3b82f6;
    --kpi-label: #6b7280;
    --kpi-value: #1f2937;
    --section-color: #1f2937;
    --section-border: #d1d5db;
}

/* Dark mode overrides – triggers when Streamlit is in dark theme */
@media (prefers-color-scheme: dark) {
    :root {
        --kpi-bg: #161b26;
        --kpi-bg2: #1c2130;
        --kpi-border: #262d3d;
        --kpi-label: #9ca3af;
        --kpi-value: #f0f2f6;
        --section-color: #d0d3da;
        --section-border: #1e2433;
    }
}

/* Also hook into Streamlit's own theme data attribute */
[data-testid="stAppViewContainer"][data-theme="dark"],
.stApp[data-theme="dark"] {
    --kpi-bg: #161b26;
    --kpi-bg2: #1c2130;
    --kpi-border: #262d3d;
    --kpi-label: #9ca3af;
    --kpi-value: #f0f2f6;
    --section-color: #d0d3da;
    --section-border: #1e2433;
}

.kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
.kpi-card {
    flex: 1 1 140px;
    background: linear-gradient(145deg, var(--kpi-bg), var(--kpi-bg2));
    border: 1px solid var(--kpi-border);
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
    min-width: 140px;
    transition: border-color 0.2s ease;
}
.kpi-card:hover { border-color: var(--kpi-border-hover); }
.kpi-label {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.1px;
    color: var(--kpi-label); font-weight: 600; margin-bottom: 6px;
}
.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem; font-weight: 700; color: var(--kpi-value);
}

/* Accent colours – these work on both light and dark backgrounds */
.kpi-blue   .kpi-value { color: #2563eb; }
.kpi-red    .kpi-value { color: #dc2626; }
.kpi-green  .kpi-value { color: #16a34a; }
.kpi-amber  .kpi-value { color: #d97706; }
.kpi-purple .kpi-value { color: #7c3aed; }
.kpi-cyan   .kpi-value { color: #0891b2; }

.section-hdr {
    font-size: 1.1rem; font-weight: 700; color: var(--section-color);
    margin: 28px 0 12px 0; padding-bottom: 6px;
    border-bottom: 2px solid var(--section-border);
}
</style>
""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLOTLY HELPERS  (adapt to Streamlit light / dark)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAL = ["#3b82f6","#dc2626","#16a34a","#d97706","#7c3aed",
       "#0891b2","#db2777","#ea580c","#0d9488","#6d28d9","#475569"]

def _is_dark():
    """Detect whether Streamlit is running in dark mode."""
    try:
        theme = st.get_option("theme.base")
        if theme == "dark":
            return True
        if theme == "light":
            return False
    except Exception:
        pass
    # Default: check if backgroundColor looks dark
    try:
        bg = st.get_option("theme.backgroundColor") or ""
        if bg:
            r = int(bg[1:3], 16)
            return r < 128
    except Exception:
        pass
    return False  # fallback to light

def _theme_colors():
    dark = _is_dark()
    if dark:
        return {
            "bg": "#0e1117", "grid": "#1e2433",
            "txt": "#9ca3af", "title": "#dde0e7",
            "template": "plotly_dark",
        }
    else:
        return {
            "bg": "#ffffff", "grid": "#e5e7eb",
            "txt": "#4b5563", "title": "#111827",
            "template": "plotly_white",
        }

def _style(fig, h=400):
    t = _theme_colors()
    fig.update_layout(
        template=t["template"], paper_bgcolor=t["bg"], plot_bgcolor=t["bg"],
        font=dict(family="DM Sans", color=t["txt"], size=12),
        title_font=dict(color=t["title"], size=14), height=h,
        margin=dict(l=40, r=30, t=50, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
    )
    fig.update_xaxes(gridcolor=t["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], zeroline=False)
    return fig

def _dl_png(fig, key):
    """Offer chart download as PNG (needs kaleido)."""
    try:
        img = fig.to_image(format="png", width=1200, height=600, scale=2)
        st.download_button("⬇ Download PNG", img, f"{key}.png", "image/png", key=f"dlp_{key}")
    except Exception:
        pass

def _dl_csv(df, key):
    st.download_button("⬇ Download CSV", df.to_csv(index=False).encode(), f"{key}.csv", "text/csv", key=f"dlc_{key}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA LOADER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data(show_spinner="Crunching crime numbers…")
def load_data(file_bytes):
    """
    Parse the multi-sheet workbook (one 'Stats by road' sheet per month).
    Returns long-form DataFrame and list of active months.
    """
    xls = pd.ExcelFile(BytesIO(file_bytes))
    all_sheets = xls.sheet_names
    records = []

    for month_short, month_code in MONTH_SHEET_MAP.items():
        # Find matching sheet (case-insensitive)
        target = None
        for s in all_sheets:
            if month_code.lower() in s.lower() and "road" in s.lower():
                target = s
                break
        if target is None:
            continue

        df = pd.read_excel(BytesIO(file_bytes), sheet_name=target)

        # Normalise column names to standard crime types
        col_map = {}
        for c in df.columns:
            cl = c.strip().lower()
            if cl == "road":
                col_map[c] = "Road"
            elif "burglary" in cl:
                col_map[c] = "Burglary"
            elif cl == "asb":
                col_map[c] = "ASB"
            elif "robbery" in cl:
                col_map[c] = "Robbery"
            elif "vehicle" in cl:
                col_map[c] = "Vehicle Crime"
            elif "violent" in cl:
                col_map[c] = "Violent Crime and Sexual Offences"
            elif "disorder" in cl or "weapons" in cl:
                col_map[c] = "Public Disorder & Weapons"
            elif "shop" in cl:
                col_map[c] = "Shop-lifting"
            elif "damage" in cl or "arson" in cl:
                col_map[c] = "Criminal Damage & Arson"
            elif "other theft" in cl:
                col_map[c] = "Other Theft"
            elif "drug" in cl:
                col_map[c] = "Drugs"
            elif "other crime" in cl:
                col_map[c] = "Other Crime"

        df = df.rename(columns=col_map)
        if "Road" not in df.columns:
            continue

        # Drop the TOTAL row
        df = df[df["Road"].astype(str).str.strip().str.upper() != "TOTAL"].copy()
        df["Road"] = df["Road"].astype(str).str.strip()

        # Tag hospital rows
        df["is_hospital"] = df["Road"].str.lower().str.contains("hospital")

        avail_crimes = [c for c in CRIME_TYPES if c in df.columns]
        if not avail_crimes:
            continue

        row_sum = df[avail_crimes].fillna(0).sum(axis=1)
        if row_sum.sum() == 0:
            continue  # empty month – skip

        # Melt to long form
        for _, row in df.iterrows():
            for ct in avail_crimes:
                val = row.get(ct, 0)
                if pd.isna(val):
                    val = 0
                val = int(val)
                if val != 0:
                    records.append({
                        "Month": month_short,
                        "Road": row["Road"],
                        "Crime Type": ct,
                        "Count": val,
                        "is_hospital": bool(row["is_hospital"]),
                    })

    if not records:
        return pd.DataFrame(), []

    road_month = pd.DataFrame(records)
    road_month["Month"] = pd.Categorical(road_month["Month"], categories=MONTH_ORDER, ordered=True)
    months_active = sorted(road_month["Month"].dropna().unique(), key=lambda m: MONTH_ORDER.index(m))

    return road_month, months_active


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEADER & UPLOAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("## 🔍 Crime Stats Analyser")
st.caption("Upload your crime spreadsheet (standard format). All analysis is generated automatically.")

uploaded = st.file_uploader("Upload Excel workbook (.xlsx)", type=["xlsx"])

if uploaded is None:
    st.info("👆 Upload a file to get started. The spreadsheet should contain monthly **Stats by road** sheets.")
    st.stop()

file_bytes = uploaded.read()
result = load_data(file_bytes)
if isinstance(result[0], pd.DataFrame) and result[0].empty:
    st.error("Could not find any crime data in the uploaded file. Please check the format.")
    st.stop()

data, months_active = result
n_months = len(months_active)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CORE METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
total_all      = int(data["Count"].sum())
hospital_mask  = data["is_hospital"]
total_hospital = int(data.loc[hospital_mask, "Count"].sum())
total_non_hosp = total_all - total_hospital
avg_per_month  = round(total_all / max(n_months, 1), 1)
most_common    = data.groupby("Crime Type")["Count"].sum().idxmax()
hosp_pct       = round(total_hospital / max(total_all, 1) * 100, 1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KPI ROW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def kpi(label, value, color=""):
    cls = f"kpi-card kpi-{color}" if color else "kpi-card"
    return f'<div class="{cls}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>'

# Shorten the crime name for display
most_common_short = most_common.replace(" and Sexual Offences","").replace("& Weapons","").strip()

st.markdown(
    '<div class="kpi-row">'
    + kpi("Total Crimes YTD", total_all, "blue")
    + kpi("Hospital Crimes", total_hospital, "red")
    + kpi("Non-Hospital", total_non_hosp, "green")
    + kpi("Avg / Month", avg_per_month, "amber")
    + kpi("Most Common Crime", most_common_short, "purple")
    + kpi("Hospital % of Total", f"{hosp_pct}%", "cyan")
    + '</div>', unsafe_allow_html=True,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. MONTHLY TREND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">📈 Monthly Crime Trend</div>', unsafe_allow_html=True)

monthly      = data.groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
monthly_hosp = data[hospital_mask].groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
monthly_non  = monthly - monthly_hosp

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(x=monthly.index.tolist(), y=monthly.values, name="All Crimes",
                               line=dict(color="#2563eb", width=3), mode="lines+markers"))
fig_trend.add_trace(go.Scatter(x=monthly_hosp.index.tolist(), y=monthly_hosp.values, name="Hospital",
                               line=dict(color="#dc2626", width=2, dash="dot"), mode="lines+markers"))
fig_trend.add_trace(go.Scatter(x=monthly_non.index.tolist(), y=monthly_non.values, name="Non-Hospital",
                               line=dict(color="#16a34a", width=2, dash="dash"), mode="lines+markers"))
fig_trend.update_layout(title="Total Crimes by Month (All / Hospital / Non-Hospital)")
_style(fig_trend)
st.plotly_chart(fig_trend, use_container_width=True)
_dl_png(fig_trend, "monthly_trend")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. CRIME TYPE BREAKDOWN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">🧩 Crime Type Breakdown</div>', unsafe_allow_html=True)

by_type = data.groupby("Crime Type")["Count"].sum().sort_values(ascending=False).reset_index()

col_a, col_b = st.columns(2)
with col_a:
    fig_bar = px.bar(by_type, x="Crime Type", y="Count", color="Crime Type",
                     color_discrete_sequence=PAL, title="Crimes by Type (YTD)")
    fig_bar.update_layout(showlegend=False, xaxis_tickangle=-35)
    _style(fig_bar)
    st.plotly_chart(fig_bar, use_container_width=True)
    _dl_png(fig_bar, "type_bar")

with col_b:
    fig_pie = px.pie(by_type, names="Crime Type", values="Count",
                     color_discrete_sequence=PAL, title="Crime Type Distribution", hole=0.45)
    _style(fig_pie)
    st.plotly_chart(fig_pie, use_container_width=True)
    _dl_png(fig_pie, "type_pie")

_dl_csv(by_type, "crime_type_summary")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. CRIME TYPE DEEP DIVE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">🔬 Crime Type Deep Dive</div>', unsafe_allow_html=True)

selected_crime = st.selectbox("Select a crime type:", sorted(data["Crime Type"].unique()), key="ct_dd")

ct_data    = data[data["Crime Type"] == selected_crime]
ct_monthly = ct_data.groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
ct_hosp    = ct_data[ct_data["is_hospital"]].groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
ct_roads   = ct_data[~ct_data["is_hospital"]].groupby("Road")["Count"].sum().sort_values(ascending=False).head(10).reset_index()

c1, c2 = st.columns(2)
with c1:
    fig_ct = go.Figure()
    fig_ct.add_trace(go.Bar(x=ct_monthly.index.tolist(), y=ct_monthly.values, name="All", marker_color="#2563eb"))
    fig_ct.add_trace(go.Bar(x=ct_hosp.index.tolist(), y=ct_hosp.values, name="Hospital", marker_color="#dc2626"))
    fig_ct.update_layout(title=f"{selected_crime} – Monthly Trend", barmode="group")
    _style(fig_ct)
    st.plotly_chart(fig_ct, use_container_width=True)
    _dl_png(fig_ct, "dd_monthly")

with c2:
    if not ct_roads.empty:
        fig_cr = px.bar(ct_roads, x="Count", y="Road", orientation="h",
                        color_discrete_sequence=["#7c3aed"],
                        title=f"{selected_crime} – Top Roads (excl. Hospital)")
        _style(fig_cr)
        st.plotly_chart(fig_cr, use_container_width=True)
        _dl_png(fig_cr, "dd_roads")
    else:
        st.info("No non-hospital incidents for this crime type.")

ct_total     = int(ct_data["Count"].sum())
ct_hosp_tot  = int(ct_data[ct_data["is_hospital"]]["Count"].sum())
st.markdown(
    '<div class="kpi-row">'
    + kpi(f"Total {selected_crime.split(' and ')[0]}", ct_total, "blue")
    + kpi("Hospital", ct_hosp_tot, "red")
    + kpi("Non-Hospital", ct_total - ct_hosp_tot, "green")
    + kpi("% of All Crime", f"{round(ct_total / max(total_all,1) * 100, 1)}%", "amber")
    + '</div>', unsafe_allow_html=True,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. HOSPITAL CRIME ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">🏥 Hospital Crime Analysis</div>', unsafe_allow_html=True)

hosp_data = data[hospital_mask]
if not hosp_data.empty:
    h1, h2 = st.columns(2)
    with h1:
        hosp_by_type = hosp_data.groupby("Crime Type")["Count"].sum().sort_values(ascending=False).reset_index()
        fig_hbt = px.bar(hosp_by_type, x="Crime Type", y="Count", color="Crime Type",
                         color_discrete_sequence=PAL, title="Hospital Crimes by Type")
        fig_hbt.update_layout(showlegend=False, xaxis_tickangle=-35)
        _style(fig_hbt)
        st.plotly_chart(fig_hbt, use_container_width=True)
        _dl_png(fig_hbt, "hosp_by_type")

    with h2:
        hosp_monthly = hosp_data.groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
        fig_hm = go.Figure(go.Bar(x=hosp_monthly.index.tolist(), y=hosp_monthly.values, marker_color="#dc2626"))
        fig_hm.update_layout(title="Hospital Crimes – Monthly Trend")
        _style(fig_hm)
        st.plotly_chart(fig_hm, use_container_width=True)
        _dl_png(fig_hm, "hosp_monthly")

    _dl_csv(hosp_by_type, "hospital_breakdown")
else:
    st.info("No hospital crime data found.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. ROAD-SPECIFIC ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">🛣️ Road-Specific Analysis</div>', unsafe_allow_html=True)

non_hosp   = data[~hospital_mask]
roads_list = sorted(non_hosp["Road"].unique())
selected_road = st.selectbox("Select a road:", roads_list, key="road_sel")

rd_data = non_hosp[non_hosp["Road"] == selected_road]
if not rd_data.empty:
    r1, r2 = st.columns(2)
    with r1:
        rd_monthly = rd_data.groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
        fig_rd = go.Figure(go.Bar(x=rd_monthly.index.tolist(), y=rd_monthly.values, marker_color="#0891b2"))
        fig_rd.update_layout(title=f"{selected_road} – Monthly Trend")
        _style(fig_rd)
        st.plotly_chart(fig_rd, use_container_width=True)
        _dl_png(fig_rd, "road_monthly")

    with r2:
        rd_types = rd_data.groupby("Crime Type")["Count"].sum().sort_values(ascending=False).reset_index()
        fig_rdt = px.bar(rd_types, x="Count", y="Crime Type", orientation="h",
                         color_discrete_sequence=["#0891b2"], title=f"{selected_road} – Crime Types")
        _style(fig_rdt)
        st.plotly_chart(fig_rdt, use_container_width=True)
        _dl_png(fig_rdt, "road_types")

    rd_total = int(rd_data["Count"].sum())
    rd_pct   = round(rd_total / max(total_non_hosp, 1) * 100, 1)
    st.markdown(
        '<div class="kpi-row">'
        + kpi(f"Total on {selected_road}", rd_total, "cyan")
        + kpi("% of Non-Hospital Crime", f"{rd_pct}%", "amber")
        + kpi("Active Months", int((rd_monthly > 0).sum()), "purple")
        + '</div>', unsafe_allow_html=True,
    )
    _dl_csv(rd_types, f"road_{selected_road.replace(' ','_')}")
else:
    st.info("No recorded crimes on this road.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. TOP 10 CRIME HOTSPOTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">🔥 Top 10 Crime Hotspots</div>', unsafe_allow_html=True)

hotspots = (
    non_hosp.groupby("Road")["Count"].sum()
    .sort_values(ascending=False).head(10)
    .reset_index().rename(columns={"Count": "Total Crimes"})
)

hc1, hc2 = st.columns([3, 2])
with hc1:
    fig_hot = px.bar(hotspots, x="Total Crimes", y="Road", orientation="h",
                     color="Total Crimes", color_continuous_scale="YlOrRd",
                     title="Top 10 Roads by Crime Count (excl. Hospital)")
    fig_hot.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
    _style(fig_hot, 420)
    st.plotly_chart(fig_hot, use_container_width=True)
    _dl_png(fig_hot, "top10_hotspots")

with hc2:
    st.dataframe(hotspots.set_index("Road"), use_container_width=True, height=400)
    _dl_csv(hotspots, "top10_hotspots_tbl")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. HEATMAP – Crime Type × Month
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">🗓️ Crime Type × Month Heatmap</div>', unsafe_allow_html=True)

pivot = data.groupby(["Crime Type", "Month"], observed=True)["Count"].sum().unstack(fill_value=0)
pivot = pivot.reindex(columns=months_active, fill_value=0)

fig_hm2 = px.imshow(pivot.values, x=months_active, y=pivot.index.tolist(),
                     color_continuous_scale="Blues", aspect="auto",
                     title="Crime Intensity Heatmap",
                     labels=dict(color="Crimes"))
_style(fig_hm2, 450)
st.plotly_chart(fig_hm2, use_container_width=True)
_dl_png(fig_hm2, "heatmap")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. ANOMALY DETECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">⚠️ Anomaly Detection – Unusual Spikes</div>', unsafe_allow_html=True)
st.caption("A spike is flagged when a monthly count exceeds 1.5 standard deviations above the mean for that crime type.")

anomalies = []
for ct in data["Crime Type"].unique():
    ct_s = data[data["Crime Type"] == ct].groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
    m, s = ct_s.mean(), ct_s.std()
    if s == 0:
        continue
    thresh = m + 1.5 * s
    for month, val in ct_s.items():
        if val > thresh:
            anomalies.append({
                "Month": month, "Crime Type": ct,
                "Count": int(val), "Mean": round(m, 1),
                "Threshold": round(thresh, 1),
                "Std Devs Above Mean": round((val - m) / s, 2),
            })

if anomalies:
    anom_df = pd.DataFrame(anomalies).sort_values("Std Devs Above Mean", ascending=False)

    a1, a2 = st.columns([3, 2])
    with a1:
        fig_anom = px.scatter(anom_df, x="Month", y="Crime Type", size="Count",
                              color="Std Devs Above Mean", color_continuous_scale="YlOrRd",
                              title="Detected Anomalies (bubble = crime count)", size_max=35)
        _style(fig_anom, 400)
        st.plotly_chart(fig_anom, use_container_width=True)
        _dl_png(fig_anom, "anomalies_chart")

    with a2:
        st.dataframe(anom_df.reset_index(drop=True), use_container_width=True, height=350)
        _dl_csv(anom_df, "anomaly_table")

    worst = anom_df.iloc[0]
    st.warning(
        f"**Largest spike:** {worst['Crime Type']} in **{worst['Month']}** "
        f"with **{worst['Count']} incidents** "
        f"({worst['Std Devs Above Mean']}σ above the mean of {worst['Mean']})."
    )
else:
    st.success("No significant anomalies detected. Crime levels are relatively consistent month to month.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RAW DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.expander("📋 View / Download Full Data Table"):
    wide = (data.pivot_table(index=["Road", "Month"], columns="Crime Type",
                             values="Count", aggfunc="sum").fillna(0).astype(int))
    wide["Total"] = wide.sum(axis=1)
    wide = wide.reset_index()
    st.dataframe(wide, use_container_width=True, height=400)
    _dl_csv(wide, "raw_data_full")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.caption("Crime Stats Analyser · Upload any spreadsheet in the standard format · Charts downloadable as PNG")
