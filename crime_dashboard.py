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
# 0. COMBINED SUMMARY TABLE — nested Non-Hospital / Hospital
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hdr">📊 Crime Summary — Non-Hospital &amp; Hospital Breakdown</div>', unsafe_allow_html=True)

def _lerp_hex(c1, c2, t):
    """Linearly interpolate between two hex colours."""
    r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t); g = int(g1 + (g2-g1)*t); b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"

def _build_combined_table(data, months_active):
    """
    Build a single combined table with nested rows:
      Crime Type A
        🏘️ Non-Hospital    1  2  0 ...  Total
        🏥 Hospital         3  0  1 ...  Total
      Crime Type B
        ...
      TOTAL NON-HOSPITAL    ...
      TOTAL HOSPITAL        ...
      TOTAL ALL             ...
    Returns row metadata + pivoted values.
    """
    # Pivot both slices
    def _pivot(is_hosp):
        sub = data[data["is_hospital"] == is_hosp]
        piv = sub.groupby(["Crime Type","Month"], observed=True)["Count"].sum().unstack(fill_value=0)
        piv = piv.reindex(columns=months_active, fill_value=0)
        piv["Total"] = piv.sum(axis=1)
        return piv

    piv_nh = _pivot(False)
    piv_h  = _pivot(True)

    # Union of all crime types, sorted by combined total descending
    all_types = sorted(
        set(piv_nh.index) | set(piv_h.index),
        key=lambda ct: (
            (piv_nh.loc[ct, "Total"] if ct in piv_nh.index else 0)
            + (piv_h.loc[ct, "Total"] if ct in piv_h.index else 0)
        ),
        reverse=True,
    )

    cols = list(months_active) + ["Total"]

    # Row structures: list of dicts with label, values, and row_type
    rows = []
    for ct in all_types:
        nh_vals = [int(piv_nh.loc[ct, c]) if ct in piv_nh.index else 0 for c in cols]
        h_vals  = [int(piv_h.loc[ct, c])  if ct in piv_h.index  else 0 for c in cols]

        rows.append({"label": f"<b>{ct}</b>",       "vals": [n + h for n, h in zip(nh_vals, h_vals)], "type": "crime_header"})
        rows.append({"label": "   🏘️ Non-Hospital", "vals": nh_vals, "type": "non_hospital"})
        rows.append({"label": "   🏥 Hospital",     "vals": h_vals,  "type": "hospital"})

    # Totals
    nh_totals = [int(piv_nh[c].sum()) if c in piv_nh.columns else 0 for c in cols]
    h_totals  = [int(piv_h[c].sum())  if c in piv_h.columns  else 0 for c in cols]
    all_totals = [n + h for n, h in zip(nh_totals, h_totals)]

    rows.append({"label": "<b>TOTAL NON-HOSPITAL</b>", "vals": nh_totals,  "type": "total_nh"})
    rows.append({"label": "<b>TOTAL HOSPITAL</b>",     "vals": h_totals,   "type": "total_h"})
    rows.append({"label": "<b>TOTAL ALL CRIMES</b>",   "vals": all_totals, "type": "total_all"})

    return rows, cols


def _render_combined_table(rows, cols, months_active):
    """Render the combined nested table as a Plotly go.Table."""
    dark = _is_dark()

    # ── Theme palette ──
    if dark:
        header_fill      = "#1e293b"
        header_font      = "#e2e8f0"
        crime_hdr_bg     = "#1a2332"
        crime_hdr_font   = "#e2e8f0"
        nh_bg_low        = "#0f172a"
        nh_bg_high       = "#1e3a5f"
        nh_font_low      = "#64748b"
        nh_font_high     = "#93c5fd"
        h_bg_low         = "#0f1118"
        h_bg_high        = "#2d1a1a"
        h_font_low       = "#64748b"
        h_font_high      = "#fca5a5"
        zero_bg          = "#0f1118"
        zero_font        = "#374151"
        total_nh_bg      = "#1e40af"
        total_h_bg       = "#991b1b"
        total_all_bg     = "#1e293b"
        total_font       = "#ffffff"
        line_color       = "#1e293b"
        bg_color         = "#0e1117"
        title_color      = "#e2e8f0"
        label_default    = "#cbd5e1"
    else:
        header_fill      = "#1e293b"
        header_font      = "#ffffff"
        crime_hdr_bg     = "#f1f5f9"
        crime_hdr_font   = "#0f172a"
        nh_bg_low        = "#ffffff"
        nh_bg_high       = "#bfdbfe"
        nh_font_low      = "#94a3b8"
        nh_font_high     = "#1e3a5f"
        h_bg_low         = "#ffffff"
        h_bg_high        = "#fecaca"
        h_font_low       = "#94a3b8"
        h_font_high      = "#7f1d1d"
        zero_bg          = "#ffffff"
        zero_font        = "#d1d5db"
        total_nh_bg      = "#2563eb"
        total_h_bg       = "#dc2626"
        total_all_bg     = "#0f172a"
        total_font       = "#ffffff"
        line_color       = "#e2e8f0"
        bg_color         = "#ffffff"
        title_color      = "#0f172a"
        label_default    = "#334155"

    # Find max for non-hospital intensity (excl totals)
    nh_data_vals = [r["vals"][:-1] for r in rows if r["type"] == "non_hospital"]
    nh_max = max((max(v) for v in nh_data_vals if v), default=1) or 1
    h_data_vals = [r["vals"][:-1] for r in rows if r["type"] == "hospital"]
    h_max = max((max(v) for v in h_data_vals if v), default=1) or 1

    n_rows = len(rows)
    col_headers = ["Crime Type"] + cols
    n_data_cols = len(cols)

    # ── Build column-wise arrays (Plotly wants data by column) ──
    # First column: labels
    label_vals  = []
    label_fills = []
    label_fonts = []
    for r in rows:
        label_vals.append(r["label"])
        t = r["type"]
        if t == "crime_header":
            label_fills.append(crime_hdr_bg)
            label_fonts.append(crime_hdr_font)
        elif t == "total_nh":
            label_fills.append(total_nh_bg)
            label_fonts.append(total_font)
        elif t == "total_h":
            label_fills.append(total_h_bg)
            label_fonts.append(total_font)
        elif t == "total_all":
            label_fills.append(total_all_bg)
            label_fonts.append(total_font)
        else:
            label_fills.append(nh_bg_low if dark else "#fafbfc")
            label_fonts.append(label_default)

    cell_values = [label_vals]
    cell_fills  = [label_fills]
    cell_fonts  = [label_fonts]

    # Data columns
    for ci, col_name in enumerate(cols):
        c_vals  = []
        c_fills = []
        c_fonts = []
        is_total_col = (col_name == "Total")

        for ri, r in enumerate(rows):
            val = r["vals"][ci]
            t = r["type"]

            # ── Total footer rows ──
            if t in ("total_nh", "total_h", "total_all"):
                c_vals.append(f"<b>{val}</b>")
                c_fills.append({"total_nh": total_nh_bg, "total_h": total_h_bg, "total_all": total_all_bg}[t])
                c_fonts.append(total_font)

            # ── Crime header row (combined number) ──
            elif t == "crime_header":
                c_vals.append(f"<b>{val}</b>" if val > 0 else "–")
                c_fills.append(crime_hdr_bg)
                c_fonts.append(crime_hdr_font if val > 0 else zero_font)

            # ── Non-hospital sub-row (primary emphasis) ──
            elif t == "non_hospital":
                if val == 0:
                    c_vals.append("–")
                    c_fills.append(zero_bg)
                    c_fonts.append(zero_font)
                else:
                    ref = max(nh_max, 1) if not is_total_col else max((r2["vals"][-1] for r2 in rows if r2["type"] == "non_hospital"), default=1) or 1
                    intensity = min(val / ref, 1.0)
                    c_fills.append(_lerp_hex(nh_bg_low, nh_bg_high, intensity))
                    c_fonts.append(_lerp_hex(nh_font_low, nh_font_high, intensity))
                    c_vals.append(f"<b>{val}</b>" if (intensity > 0.4 or is_total_col) else str(val))

            # ── Hospital sub-row (secondary, lighter) ──
            elif t == "hospital":
                if val == 0:
                    c_vals.append("–")
                    c_fills.append(zero_bg)
                    c_fonts.append(zero_font)
                else:
                    ref = max(h_max, 1) if not is_total_col else max((r2["vals"][-1] for r2 in rows if r2["type"] == "hospital"), default=1) or 1
                    intensity = min(val / ref, 1.0)
                    c_fills.append(_lerp_hex(h_bg_low, h_bg_high, intensity))
                    c_fonts.append(_lerp_hex(h_font_low, h_font_high, intensity))
                    c_vals.append(str(val))

        cell_values.append(c_vals)
        cell_fills.append(c_fills)
        cell_fonts.append(c_fonts)

    # ── Row heights: crime headers slightly taller for grouping ──
    row_heights = []
    for r in rows:
        if r["type"] == "crime_header":
            row_heights.append(32)
        elif r["type"] in ("total_nh", "total_h", "total_all"):
            row_heights.append(34)
        else:
            row_heights.append(28)

    fig = go.Figure(data=[go.Table(
        columnwidth=[200] + [58] * n_data_cols,
        header=dict(
            values=[f"<b>{c}</b>" for c in col_headers],
            fill_color=header_fill,
            font=dict(color=header_font, size=12, family="DM Sans"),
            align=["left"] + ["center"] * n_data_cols,
            height=36,
            line_color=line_color,
        ),
        cells=dict(
            values=cell_values,
            fill_color=cell_fills,
            font=dict(color=cell_fonts, size=12, family="JetBrains Mono"),
            align=["left"] + ["center"] * n_data_cols,
            height=30,
            line_color=line_color,
        ),
    )])

    table_height = 45 + 36 + n_rows * 30 + 20
    fig.update_layout(
        title=dict(
            text="📊 Crime Breakdown by Type — Non-Hospital vs Hospital",
            font=dict(size=15, color=title_color, family="DM Sans"),
        ),
        paper_bgcolor=bg_color, plot_bgcolor=bg_color,
        margin=dict(l=10, r=10, t=50, b=10),
        height=max(350, table_height),
    )
    return fig

# Build & render
combined_rows, combined_cols = _build_combined_table(data, months_active)
fig_combined = _render_combined_table(combined_rows, combined_cols, months_active)
st.plotly_chart(fig_combined, use_container_width=True)

dl_col1, dl_col2 = st.columns(2)
with dl_col1:
    _dl_png(fig_combined, "crime_summary_combined")
with dl_col2:
    # CSV download of the combined data
    csv_rows = []
    for r in combined_rows:
        row_dict = {"Crime Type": r["label"].replace("<b>","").replace("</b>","")}
        for ci, col_name in enumerate(combined_cols):
            row_dict[col_name] = r["vals"][ci]
        row_dict["Row Type"] = r["type"]
        csv_rows.append(row_dict)
    _dl_csv(pd.DataFrame(csv_rows), "crime_summary_combined")


# ── Separate standalone tables beneath ──

def _build_standalone_pivot(data, months_active, is_hospital):
    """Pivot for a single category: crime types × months with Total row/col."""
    subset = data[data["is_hospital"] == is_hospital]
    piv = subset.groupby(["Crime Type", "Month"], observed=True)["Count"].sum().unstack(fill_value=0)
    piv = piv.reindex(columns=months_active, fill_value=0)
    piv["Total"] = piv.sum(axis=1)
    piv = piv.sort_values("Total", ascending=False)
    totals = piv.sum(axis=0); totals.name = "TOTAL"
    piv = pd.concat([piv, totals.to_frame().T])
    return piv

def _render_standalone_table(piv, title, is_primary=False):
    """
    Render a single-category table as a Plotly go.Table.
    is_primary=True → blue (non-hospital), False → red (hospital).
    """
    dark = _is_dark()

    if is_primary:
        header_fill  = "#1e40af" if dark else "#1e40af"
        header_font  = "#ffffff"
        bg_low       = "#111827" if dark else "#ffffff"
        bg_high      = "#1e3a5f" if dark else "#bfdbfe"
        font_low     = "#64748b" if dark else "#94a3b8"
        font_high    = "#93c5fd" if dark else "#1e3a5f"
        total_bg     = "#2563eb"
        total_font   = "#ffffff"
        zero_bg      = "#0f1118" if dark else "#ffffff"
        zero_font    = "#374151" if dark else "#d1d5db"
    else:
        header_fill  = "#991b1b" if dark else "#991b1b"
        header_font  = "#fecaca" if dark else "#ffffff"
        bg_low       = "#111318" if dark else "#ffffff"
        bg_high      = "#2d1a1a" if dark else "#fecaca"
        font_low     = "#64748b" if dark else "#94a3b8"
        font_high    = "#fca5a5" if dark else "#7f1d1d"
        total_bg     = "#dc2626"
        total_font   = "#ffffff"
        zero_bg      = "#0f1118" if dark else "#ffffff"
        zero_font    = "#374151" if dark else "#d1d5db"

    line_color = "#1e293b" if dark else "#e2e8f0"
    page_bg    = "#0e1117" if dark else "#ffffff"
    title_clr  = "#e2e8f0" if dark else "#0f172a"

    row_labels = list(piv.index)
    col_headers = ["Crime Type"] + list(piv.columns)
    n_rows = len(row_labels)
    n_data_cols = len(piv.columns)

    # Max for intensity scaling (excl Total row & col)
    data_only = piv.iloc[:-1, :-1]
    global_max = max(data_only.max().max(), 1)

    # First column: labels
    lab_vals, lab_fills, lab_fonts = [], [], []
    for i, lbl in enumerate(row_labels):
        is_tot = (i == n_rows - 1)
        lab_vals.append(f"<b>{lbl}</b>" if is_tot else lbl)
        lab_fills.append(total_bg if is_tot else (bg_low if dark else "#f9fafb"))
        lab_fonts.append(total_font if is_tot else ("#e5e7eb" if dark else "#111827"))

    cell_values = [lab_vals]
    cell_fills  = [lab_fills]
    cell_fonts  = [lab_fonts]

    for col_name in piv.columns:
        c_v, c_f, c_c = [], [], []
        is_total_col = (col_name == "Total")
        for ri, rn in enumerate(row_labels):
            val = int(piv.loc[rn, col_name])
            is_tot = (ri == n_rows - 1)
            if is_tot:
                c_v.append(f"<b>{val}</b>"); c_f.append(total_bg); c_c.append(total_font)
            elif val == 0:
                c_v.append("–"); c_f.append(zero_bg); c_c.append(zero_font)
            else:
                ref = max(piv.iloc[:-1]["Total"].max(), 1) if is_total_col else global_max
                intensity = min(val / ref, 1.0)
                c_f.append(_lerp_hex(bg_low, bg_high, intensity))
                c_c.append(_lerp_hex(font_low, font_high, intensity))
                c_v.append(f"<b>{val}</b>" if (intensity > 0.4 or is_total_col) else str(val))
        cell_values.append(c_v); cell_fills.append(c_f); cell_fonts.append(c_c)

    fig = go.Figure(data=[go.Table(
        columnwidth=[200] + [58] * n_data_cols,
        header=dict(
            values=[f"<b>{c}</b>" for c in col_headers],
            fill_color=header_fill,
            font=dict(color=header_font, size=12, family="DM Sans"),
            align=["left"] + ["center"] * n_data_cols,
            height=36, line_color=line_color,
        ),
        cells=dict(
            values=cell_values, fill_color=cell_fills,
            font=dict(color=cell_fonts, size=12, family="JetBrains Mono"),
            align=["left"] + ["center"] * n_data_cols,
            height=30, line_color=line_color,
        ),
    )])
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=title_clr, family="DM Sans")),
        paper_bgcolor=page_bg, plot_bgcolor=page_bg,
        margin=dict(l=10, r=10, t=50, b=10),
        height=max(220, 50 + 36 + n_rows * 30 + 20),
    )
    return fig


st.markdown('<div class="section-hdr">🏘️ Non-Hospital Crimes (standalone)</div>', unsafe_allow_html=True)

piv_nh_solo = _build_standalone_pivot(data, months_active, False)
fig_nh_solo = _render_standalone_table(piv_nh_solo, "🏘️  NON-HOSPITAL CRIMES", is_primary=True)
st.plotly_chart(fig_nh_solo, use_container_width=True)
nh_dl1, nh_dl2 = st.columns(2)
with nh_dl1:
    _dl_png(fig_nh_solo, "non_hospital_standalone")
with nh_dl2:
    _dl_csv(piv_nh_solo.reset_index().rename(columns={"index": "Crime Type"}), "non_hospital_standalone")

st.markdown('<div class="section-hdr">🏥 Hospital Crimes (standalone)</div>', unsafe_allow_html=True)

piv_h_solo = _build_standalone_pivot(data, months_active, True)
fig_h_solo = _render_standalone_table(piv_h_solo, "🏥  HOSPITAL CRIMES", is_primary=False)
st.plotly_chart(fig_h_solo, use_container_width=True)
h_dl1, h_dl2 = st.columns(2)
with h_dl1:
    _dl_png(fig_h_solo, "hospital_standalone")
with h_dl2:
    _dl_csv(piv_h_solo.reset_index().rename(columns={"index": "Crime Type"}), "hospital_standalone")


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
