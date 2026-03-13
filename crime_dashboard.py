import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

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
# CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
:root {
    --kpi-bg: #f4f6f8; --kpi-bg2: #edf0f4; --kpi-border: #d1d5db;
    --kpi-border-hover: #3b82f6; --kpi-label: #6b7280; --kpi-value: #1f2937;
    --section-color: #1f2937; --section-border: #d1d5db;
}
@media (prefers-color-scheme: dark) {
    :root { --kpi-bg:#161b26; --kpi-bg2:#1c2130; --kpi-border:#262d3d;
            --kpi-label:#9ca3af; --kpi-value:#f0f2f6;
            --section-color:#d0d3da; --section-border:#1e2433; }
}
[data-testid="stAppViewContainer"][data-theme="dark"], .stApp[data-theme="dark"] {
    --kpi-bg:#161b26; --kpi-bg2:#1c2130; --kpi-border:#262d3d;
    --kpi-label:#9ca3af; --kpi-value:#f0f2f6;
    --section-color:#d0d3da; --section-border:#1e2433;
}
.kpi-row { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px; }
.kpi-card {
    flex:1 1 140px; background:linear-gradient(145deg,var(--kpi-bg),var(--kpi-bg2));
    border:1px solid var(--kpi-border); border-radius:10px;
    padding:18px 20px; text-align:center; min-width:140px;
    transition:border-color .2s;
}
.kpi-card:hover { border-color:var(--kpi-border-hover); }
.kpi-label { font-size:.7rem; text-transform:uppercase; letter-spacing:1.1px;
             color:var(--kpi-label); font-weight:600; margin-bottom:6px; }
.kpi-value { font-family:'JetBrains Mono',monospace; font-size:1.6rem;
             font-weight:700; color:var(--kpi-value); }
.kpi-blue   .kpi-value { color:#2563eb; }
.kpi-red    .kpi-value { color:#dc2626; }
.kpi-green  .kpi-value { color:#16a34a; }
.kpi-amber  .kpi-value { color:#d97706; }
.kpi-purple .kpi-value { color:#7c3aed; }
.kpi-cyan   .kpi-value { color:#0891b2; }
.section-hdr { font-size:1.1rem; font-weight:700; color:var(--section-color);
               margin:28px 0 12px 0; padding-bottom:6px;
               border-bottom:2px solid var(--section-border); }
</style>
""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLOTLY HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAL = ["#3b82f6","#dc2626","#16a34a","#d97706","#7c3aed",
       "#0891b2","#db2777","#ea580c","#0d9488","#6d28d9","#475569"]

def _is_dark():
    try:
        theme = st.get_option("theme.base")
        if theme == "dark": return True
        if theme == "light": return False
    except Exception: pass
    try:
        bg = st.get_option("theme.backgroundColor") or ""
        if bg: return int(bg[1:3], 16) < 128
    except Exception: pass
    return False

def _tc():
    dark = _is_dark()
    if dark:
        return {"bg":"#0e1117","grid":"#1e2433","txt":"#9ca3af",
                "title":"#dde0e7","tpl":"plotly_dark","lbl":"#c9cdd6"}
    return {"bg":"#ffffff","grid":"#e5e7eb","txt":"#4b5563",
            "title":"#111827","tpl":"plotly_white","lbl":"#374151"}

def _style(fig, h=400):
    t = _tc()
    fig.update_layout(
        template=t["tpl"], paper_bgcolor=t["bg"], plot_bgcolor=t["bg"],
        font=dict(family="DM Sans", color=t["txt"], size=12),
        title_font=dict(color=t["title"], size=14), height=h,
        margin=dict(l=40, r=30, t=50, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
    )
    fig.update_xaxes(gridcolor=t["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], zeroline=False)
    return fig

def _add_labels(fig):
    """Add rounded data labels to all traces in a figure."""
    t = _tc()
    for trace in fig.data:
        if isinstance(trace, (go.Bar,)):
            trace.update(
                texttemplate="%{value:.0f}", textposition="outside",
                textfont=dict(size=11, color=t["lbl"]),
                cliponaxis=False,
            )
        elif isinstance(trace, (go.Scatter,)):
            if trace.mode and "markers" in trace.mode:
                trace.update(
                    mode="lines+markers+text",
                    texttemplate="%{y:.0f}", textposition="top center",
                    textfont=dict(size=10, color=t["lbl"]),
                    cliponaxis=False,
                )
    # Pie / donut: update via update_traces
    fig.update_traces(
        textinfo="label+percent", textposition="outside",
        selector=dict(type="pie"),
    )
    return fig

def _dl_png(fig, key):
    try:
        img = fig.to_image(format="png", width=1200, height=600, scale=2)
        st.download_button("⬇ PNG", img, f"{key}.png", "image/png", key=f"dlp_{key}")
    except Exception: pass

def _dl_csv(df, key):
    st.download_button("⬇ CSV", df.to_csv(index=False).encode(), f"{key}.csv", "text/csv", key=f"dlc_{key}")

def kpi(label, value, color=""):
    cls = f"kpi-card kpi-{color}" if color else "kpi-card"
    return f'<div class="{cls}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>'

def kpi_card_png(label, value, color=""):
    """Render a KPI card as a PNG: white background, coloured accent bar + value text."""
    W, H        = 520, 220
    RADIUS      = 18
    BORDER      = 3
    ACCENT_BAR_H = 6

    accent_map = {
        "blue":   "#2563eb",
        "red":    "#dc2626",
        "green":  "#16a34a",
        "amber":  "#d97706",
        "purple": "#7c3aed",
        "cyan":   "#0891b2",
    }
    accent      = accent_map.get(color, "#6b7280")
    label_color = "#6b7280"
    bg_color    = (255, 255, 255)
    border_rgb  = tuple(int(accent[i:i+2], 16) for i in (1, 3, 5))

    img  = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # White rounded card
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=RADIUS,
                            fill=bg_color, outline=border_rgb, width=BORDER)

    # Coloured accent bar at top
    draw.rounded_rectangle([0, 0, W - 1, ACCENT_BAR_H + RADIUS],
                            radius=RADIUS, fill=border_rgb)
    draw.rectangle([0, ACCENT_BAR_H, W - 1, ACCENT_BAR_H + RADIUS], fill=bg_color)
    draw.rectangle([BORDER, ACCENT_BAR_H, W - 1 - BORDER, ACCENT_BAR_H + RADIUS], fill=bg_color)

    # Fonts
    try:
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf", 22)
        font_value = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 58)
    except Exception:
        font_label = ImageFont.load_default()
        font_value = font_label

    # Label
    lbl_text = label.upper()
    lbl_bbox = draw.textbbox((0, 0), lbl_text, font=font_label)
    lbl_w    = lbl_bbox[2] - lbl_bbox[0]
    lbl_y    = ACCENT_BAR_H + 18
    draw.text(((W - lbl_w) / 2, lbl_y), lbl_text, font=font_label, fill=label_color)

    # Value
    val_text     = str(value)
    val_bbox     = draw.textbbox((0, 0), val_text, font=font_value)
    val_w        = val_bbox[2] - val_bbox[0]
    val_h        = val_bbox[3] - val_bbox[1]
    label_bottom = lbl_y + (lbl_bbox[3] - lbl_bbox[1]) + 8
    remaining    = H - label_bottom
    val_y        = label_bottom + (remaining - val_h) / 2 - 4
    draw.text(((W - val_w) / 2, val_y), val_text, font=font_value, fill=border_rgb)

    buf = BytesIO()
    img.save(buf, format="PNG", dpi=(144, 144))
    return buf.getvalue()


def _dl_kpi_png(label, value, color=""):
    """Render a download button for a single KPI card PNG."""
    png = kpi_card_png(label, value, color)
    safe = label.lower().replace(" ", "_").replace("/", "_").replace("%", "pct")
    st.download_button(
        label="⬇ PNG",
        data=png,
        file_name=f"kpi_{safe}.png",
        mime="image/png",
        key=f"kpi_dl_{safe}_{str(value)[:8]}",
    )


def _lerp_hex(c1, c2, t_val):
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    r=int(r1+(r2-r1)*t_val); g=int(g1+(g2-g1)*t_val); b=int(b1+(b2-b1)*t_val)
    return f"#{r:02x}{g:02x}{b:02x}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA LOADER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data(show_spinner="Crunching crime numbers…")
def load_data(file_bytes):
    xls = pd.ExcelFile(BytesIO(file_bytes))
    records = []
    for month_short, month_code in MONTH_SHEET_MAP.items():
        target = None
        for s in xls.sheet_names:
            if month_code.lower() in s.lower() and "road" in s.lower():
                target = s; break
        if target is None: continue
        df = pd.read_excel(BytesIO(file_bytes), sheet_name=target)
        col_map = {}
        for c in df.columns:
            cl = c.strip().lower()
            if cl == "road": col_map[c] = "Road"
            elif "burglary" in cl: col_map[c] = "Burglary"
            elif cl == "asb": col_map[c] = "ASB"
            elif "robbery" in cl: col_map[c] = "Robbery"
            elif "vehicle" in cl: col_map[c] = "Vehicle Crime"
            elif "violent" in cl: col_map[c] = "Violent Crime and Sexual Offences"
            elif "disorder" in cl or "weapons" in cl: col_map[c] = "Public Disorder & Weapons"
            elif "shop" in cl: col_map[c] = "Shop-lifting"
            elif "damage" in cl or "arson" in cl: col_map[c] = "Criminal Damage & Arson"
            elif "other theft" in cl: col_map[c] = "Other Theft"
            elif "drug" in cl: col_map[c] = "Drugs"
            elif "other crime" in cl: col_map[c] = "Other Crime"
        df = df.rename(columns=col_map)
        if "Road" not in df.columns: continue
        df = df[df["Road"].astype(str).str.strip().str.upper() != "TOTAL"].copy()
        df["Road"] = df["Road"].astype(str).str.strip()
        df["is_hospital"] = df["Road"].str.lower().str.contains("hospital")
        avail = [c for c in CRIME_TYPES if c in df.columns]
        if not avail: continue
        if df[avail].fillna(0).sum(axis=1).sum() == 0: continue
        for _, row in df.iterrows():
            for ct in avail:
                val = row.get(ct, 0)
                if pd.isna(val): val = 0
                val = int(val)
                if val != 0:
                    records.append({"Month":month_short,"Road":row["Road"],
                                    "Crime Type":ct,"Count":val,
                                    "is_hospital":bool(row["is_hospital"])})
    if not records: return pd.DataFrame(), []
    road_month = pd.DataFrame(records)
    road_month["Month"] = pd.Categorical(road_month["Month"], categories=MONTH_ORDER, ordered=True)
    months_active = sorted(road_month["Month"].dropna().unique(), key=lambda m: MONTH_ORDER.index(m))
    return road_month, months_active

def _extract_year(fb):
    try:
        xls = pd.ExcelFile(BytesIO(fb))
        for s in xls.sheet_names:
            m = re.search(r'(20\d{2})', s)
            if m: return m.group(1)
    except Exception: pass
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE BUILDERS (shared by both pages)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_combined_table(data, months_active):
    """Build nested rows: Crime Type header → 🏘️ Non-Hospital → 🏥 Hospital, with footer totals."""
    def _pivot(is_hosp):
        sub = data[data["is_hospital"] == is_hosp]
        piv = sub.groupby(["Crime Type","Month"], observed=True)["Count"].sum().unstack(fill_value=0)
        piv = piv.reindex(columns=months_active, fill_value=0)
        piv["Total"] = piv.sum(axis=1)
        return piv
    piv_nh = _pivot(False); piv_h = _pivot(True)
    all_types = sorted(set(piv_nh.index)|set(piv_h.index),
        key=lambda ct:(piv_nh.loc[ct,"Total"] if ct in piv_nh.index else 0)+(piv_h.loc[ct,"Total"] if ct in piv_h.index else 0),
        reverse=True)
    cols = list(months_active)+["Total"]; rows = []
    for ct in all_types:
        nh_vals=[int(piv_nh.loc[ct,c]) if ct in piv_nh.index else 0 for c in cols]
        h_vals =[int(piv_h.loc[ct,c])  if ct in piv_h.index  else 0 for c in cols]
        rows.append({"label":f"<b>{ct}</b>","vals":[n+h for n,h in zip(nh_vals,h_vals)],"type":"crime_header"})
        rows.append({"label":"   🏘️ Non-Hospital","vals":nh_vals,"type":"non_hospital"})
        rows.append({"label":"   🏥 Hospital","vals":h_vals,"type":"hospital"})
    nh_totals=[int(piv_nh[c].sum()) if c in piv_nh.columns else 0 for c in cols]
    h_totals =[int(piv_h[c].sum())  if c in piv_h.columns  else 0 for c in cols]
    rows.append({"label":"<b>TOTAL NON-HOSPITAL</b>","vals":nh_totals,"type":"total_nh"})
    rows.append({"label":"<b>TOTAL HOSPITAL</b>","vals":h_totals,"type":"total_h"})
    rows.append({"label":"<b>TOTAL ALL CRIMES</b>","vals":[n+h for n,h in zip(nh_totals,h_totals)],"type":"total_all"})
    return rows, cols

def _render_combined_table(rows, cols, months_active):
    dark = _is_dark()
    if dark:
        header_fill="#1e293b"; header_font="#e2e8f0"; crime_hdr_bg="#1a2332"; crime_hdr_font="#e2e8f0"
        nh_bg_low="#0f172a"; nh_bg_high="#1e3a5f"; nh_font_low="#64748b"; nh_font_high="#93c5fd"
        h_bg_low="#0f1118"; h_bg_high="#2d1a1a"; h_font_low="#64748b"; h_font_high="#fca5a5"
        zero_bg="#0f1118"; zero_font="#374151"
        total_nh_bg="#1e40af"; total_h_bg="#991b1b"; total_all_bg="#1e293b"
        total_font="#ffffff"; line_color="#1e293b"; bg_color="#0e1117"; title_color="#e2e8f0"; label_def="#cbd5e1"
    else:
        header_fill="#1e293b"; header_font="#ffffff"; crime_hdr_bg="#f1f5f9"; crime_hdr_font="#0f172a"
        nh_bg_low="#ffffff"; nh_bg_high="#bfdbfe"; nh_font_low="#94a3b8"; nh_font_high="#1e3a5f"
        h_bg_low="#ffffff"; h_bg_high="#fecaca"; h_font_low="#94a3b8"; h_font_high="#7f1d1d"
        zero_bg="#ffffff"; zero_font="#d1d5db"
        total_nh_bg="#2563eb"; total_h_bg="#dc2626"; total_all_bg="#0f172a"
        total_font="#ffffff"; line_color="#e2e8f0"; bg_color="#ffffff"; title_color="#0f172a"; label_def="#334155"
    nh_data_vals=[r["vals"][:-1] for r in rows if r["type"]=="non_hospital"]
    nh_max=max((max(v) for v in nh_data_vals if v),default=1) or 1
    h_data_vals=[r["vals"][:-1] for r in rows if r["type"]=="hospital"]
    h_max=max((max(v) for v in h_data_vals if v),default=1) or 1
    n_rows=len(rows); n_dc=len(cols)
    lab_v,lab_f,lab_c=[],[],[]
    for r in rows:
        lab_v.append(r["label"]); t=r["type"]
        if t=="crime_header": lab_f.append(crime_hdr_bg); lab_c.append(crime_hdr_font)
        elif t=="total_nh": lab_f.append(total_nh_bg); lab_c.append(total_font)
        elif t=="total_h": lab_f.append(total_h_bg); lab_c.append(total_font)
        elif t=="total_all": lab_f.append(total_all_bg); lab_c.append(total_font)
        else: lab_f.append(nh_bg_low if dark else "#fafbfc"); lab_c.append(label_def)
    cv,cf,cc=[lab_v],[lab_f],[lab_c]
    for ci,cn in enumerate(cols):
        v,f,c=[],[],[]
        is_tc=(cn=="Total")
        for ri,r in enumerate(rows):
            val=r["vals"][ci]; tp=r["type"]
            if tp in("total_nh","total_h","total_all"):
                v.append(f"<b>{val}</b>"); f.append({"total_nh":total_nh_bg,"total_h":total_h_bg,"total_all":total_all_bg}[tp]); c.append(total_font)
            elif tp=="crime_header":
                v.append(f"<b>{val}</b>" if val>0 else "–"); f.append(crime_hdr_bg); c.append(crime_hdr_font if val>0 else zero_font)
            elif tp=="non_hospital":
                if val==0: v.append("–"); f.append(zero_bg); c.append(zero_font)
                else:
                    ref=max(nh_max,1) if not is_tc else max((r2["vals"][-1] for r2 in rows if r2["type"]=="non_hospital"),default=1) or 1
                    i=min(val/ref,1.0); f.append(_lerp_hex(nh_bg_low,nh_bg_high,i)); c.append(_lerp_hex(nh_font_low,nh_font_high,i))
                    v.append(f"<b>{val}</b>" if(i>0.4 or is_tc) else str(val))
            elif tp=="hospital":
                if val==0: v.append("–"); f.append(zero_bg); c.append(zero_font)
                else:
                    ref=max(h_max,1) if not is_tc else max((r2["vals"][-1] for r2 in rows if r2["type"]=="hospital"),default=1) or 1
                    i=min(val/ref,1.0); f.append(_lerp_hex(h_bg_low,h_bg_high,i)); c.append(_lerp_hex(h_font_low,h_font_high,i))
                    v.append(str(val))
        cv.append(v); cf.append(f); cc.append(c)
    fig=go.Figure(data=[go.Table(
        columnwidth=[200]+[58]*n_dc,
        header=dict(values=[f"<b>{c}</b>" for c in ["Crime Type"]+cols],fill_color=header_fill,
            font=dict(color=header_font,size=12,family="DM Sans"),align=["left"]+["center"]*n_dc,height=36,line_color=line_color),
        cells=dict(values=cv,fill_color=cf,font=dict(color=cc,size=12,family="JetBrains Mono"),
            align=["left"]+["center"]*n_dc,height=30,line_color=line_color),
    )])
    fig.update_layout(title=dict(text="📊 Crime Breakdown — Non-Hospital vs Hospital",font=dict(size=15,color=title_color,family="DM Sans")),
        paper_bgcolor=bg_color,plot_bgcolor=bg_color,margin=dict(l=10,r=10,t=50,b=10),height=max(350,50+36+n_rows*30+20))
    return fig

def _build_standalone_pivot(data, months_active, is_hospital):
    sub=data[data["is_hospital"]==is_hospital]
    piv=sub.groupby(["Crime Type","Month"],observed=True)["Count"].sum().unstack(fill_value=0)
    piv=piv.reindex(columns=months_active,fill_value=0); piv["Total"]=piv.sum(axis=1)
    piv=piv.sort_values("Total",ascending=False)
    totals=piv.sum(axis=0); totals.name="TOTAL"
    return pd.concat([piv,totals.to_frame().T])

def _render_standalone_table(piv, title, is_primary=False):
    dark=_is_dark()
    if is_primary:
        hf="#1e40af"; hfc="#ffffff"
        bl,bh="#111827" if dark else "#ffffff","#1e3a5f" if dark else "#bfdbfe"
        fl,fh="#64748b" if dark else "#94a3b8","#93c5fd" if dark else "#1e3a5f"
        tb="#2563eb"; tf="#ffffff"
        zb="#0f1118" if dark else "#ffffff"; zf="#374151" if dark else "#d1d5db"
    else:
        hf="#991b1b"; hfc="#fecaca" if dark else "#ffffff"
        bl,bh="#111318" if dark else "#ffffff","#2d1a1a" if dark else "#fecaca"
        fl,fh="#64748b" if dark else "#94a3b8","#fca5a5" if dark else "#7f1d1d"
        tb="#dc2626"; tf="#ffffff"
        zb="#0f1118" if dark else "#ffffff"; zf="#374151" if dark else "#d1d5db"
    lc="#1e293b" if dark else "#e2e8f0"; pbg="#0e1117" if dark else "#ffffff"; tc="#e2e8f0" if dark else "#0f172a"
    rl=list(piv.index); ch=["Crime Type"]+list(piv.columns); nr=len(rl); nd=len(piv.columns)
    gm=max(piv.iloc[:-1,:-1].max().max(),1)
    lv,lf,lc2=[],[],[]
    for i,l in enumerate(rl):
        it=(i==nr-1); lv.append(f"<b>{l}</b>" if it else l)
        lf.append(tb if it else (bl if dark else "#f9fafb")); lc2.append(tf if it else ("#e5e7eb" if dark else "#111827"))
    cv,cfl,cfc=[lv],[lf],[lc2]
    for cn in piv.columns:
        v,f,c=[],[],[]
        itc=(cn=="Total")
        for ri,rn in enumerate(rl):
            val=int(piv.loc[rn,cn]); it=(ri==nr-1)
            if it: v.append(f"<b>{val}</b>"); f.append(tb); c.append(tf)
            elif val==0: v.append("–"); f.append(zb); c.append(zf)
            else:
                ref=max(piv.iloc[:-1]["Total"].max(),1) if itc else gm
                inten=min(val/ref,1.0); f.append(_lerp_hex(bl,bh,inten)); c.append(_lerp_hex(fl,fh,inten))
                v.append(f"<b>{val}</b>" if(inten>0.4 or itc) else str(val))
        cv.append(v); cfl.append(f); cfc.append(c)
    fig=go.Figure(data=[go.Table(columnwidth=[200]+[58]*nd,
        header=dict(values=[f"<b>{c}</b>" for c in ch],fill_color=hf,font=dict(color=hfc,size=12,family="DM Sans"),
            align=["left"]+["center"]*nd,height=36,line_color=lc),
        cells=dict(values=cv,fill_color=cfl,font=dict(color=cfc,size=12,family="JetBrains Mono"),
            align=["left"]+["center"]*nd,height=30,line_color=lc))])
    fig.update_layout(title=dict(text=title,font=dict(size=15,color=tc,family="DM Sans")),
        paper_bgcolor=pbg,plot_bgcolor=pbg,margin=dict(l=10,r=10,t=50,b=10),height=max(220,50+36+nr*30+20))
    return fig

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIDEBAR — file upload & navigation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.sidebar:
    st.markdown("## 🔍 Crime Stats Analyser")
    st.markdown("---")
    uploaded = st.file_uploader("📂 Current Year", type=["xlsx"], key="curr")
    uploaded_prev = st.file_uploader("📂 Previous Year (optional)", type=["xlsx"], key="prev")
    st.markdown("---")
    pages = ["📊 Dashboard"]
    if uploaded_prev:
        pages.append("📅 Year-on-Year")
    page = st.radio("Navigate", pages, label_visibility="collapsed")
    st.markdown("---")
    st.caption("Upload spreadsheets in the standard format. Add a previous year file to unlock **Year-on-Year** comparison.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOAD DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if uploaded is None:
    st.markdown("## 🔍 Crime Stats Analyser")
    st.info("👆 Upload a current year file in the sidebar to get started.")
    st.stop()

file_bytes = uploaded.read()
result = load_data(file_bytes)
if isinstance(result[0], pd.DataFrame) and result[0].empty:
    st.error("Could not find any crime data. Please check the file format.")
    st.stop()

data, months_active = result
n_months = len(months_active)
current_year_label = _extract_year(file_bytes) or "Current Year"

data_prev = None; months_active_prev = None; prev_year_label = None
if uploaded_prev is not None:
    prev_bytes = uploaded_prev.read()
    rp = load_data(prev_bytes)
    if not (isinstance(rp[0], pd.DataFrame) and rp[0].empty):
        data_prev, months_active_prev = rp
        prev_year_label = _extract_year(prev_bytes) or "Previous Year"

# Core metrics
total_all      = int(data["Count"].sum())
hospital_mask  = data["is_hospital"]
total_hospital = int(data.loc[hospital_mask, "Count"].sum())
total_non_hosp = total_all - total_hospital
avg_per_month  = round(total_all / max(n_months, 1), 1)
most_common    = data.groupby("Crime Type")["Count"].sum().idxmax()
hosp_pct       = round(total_hospital / max(total_all, 1) * 100, 1)
most_common_short = most_common.replace(" and Sexual Offences","").replace("& Weapons","").strip()

# Non-hospital specific metrics
non_hosp_data      = data[~hospital_mask]
avg_non_hosp_month = round(total_non_hosp / max(n_months, 1), 1)
most_common_nh     = non_hosp_data.groupby("Crime Type")["Count"].sum().idxmax() if not non_hosp_data.empty else "N/A"
most_common_nh_short = most_common_nh.replace(" and Sexual Offences","").replace("& Weapons","").strip()
monthly_non_hosp   = non_hosp_data.groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
high_crime_month_nh = monthly_non_hosp.idxmax() if not monthly_non_hosp.empty else "N/A"
high_crime_month_nh_val = int(monthly_non_hosp.max()) if not monthly_non_hosp.empty else 0

# ╔══════════════════════════════════════════════════════════════╗
# ║  PAGE 1: DASHBOARD                                          ║
# ╚══════════════════════════════════════════════════════════════╝
if page == "📊 Dashboard":
    st.markdown(f"## 📊 {current_year_label} Crime Dashboard")

    # ── KPI row ──
    # % change vs previous year (only meaningful if prev data loaded)
    if data_prev is not None:
        prev_total_kpi = int(data_prev["Count"].sum())
        pct_change = round((total_all - prev_total_kpi) / max(prev_total_kpi, 1) * 100, 1)
        pct_change_str = f"{'+' if pct_change > 0 else ''}{pct_change}%"
        pct_color = "red" if pct_change > 0 else "green"
    else:
        pct_change_str = "Upload prev. year"
        pct_color = "amber"

    kpi_cards = [
        ("Total Crimes YTD",             total_all,               "blue"),
        ("Non-Hospital Total",            total_non_hosp,          "green"),
        ("Non-Hospital High Crime Month", f"{high_crime_month_nh} ({high_crime_month_nh_val})", "red"),
        ("Most Common (Non-Hospital)",    most_common_nh_short,    "purple"),
        ("Avg Non-Hospital / Month",      avg_non_hosp_month,      "cyan"),
        ("% Change vs Previous Year",     pct_change_str,          pct_color),
    ]

    st.markdown(
        '<div class="kpi-row">' +
        "".join(kpi(lbl, val, col) for lbl, val, col in kpi_cards) +
        '</div>', unsafe_allow_html=True)

    # Per-card download buttons — one column per card
    dl_cols = st.columns(len(kpi_cards))
    for col, (lbl, val, clr) in zip(dl_cols, kpi_cards):
        with col:
            _dl_kpi_png(lbl, val, clr)

    # ── Combined summary table ──
    st.markdown('<div class="section-hdr">📊 Crime Summary — Non-Hospital &amp; Hospital Breakdown</div>', unsafe_allow_html=True)
    combined_rows, combined_cols = _build_combined_table(data, months_active)
    fig_combined = _render_combined_table(combined_rows, combined_cols, months_active)
    st.plotly_chart(fig_combined, use_container_width=True)
    dc1,dc2 = st.columns(2)
    with dc1: _dl_png(fig_combined, "combined_table")
    with dc2:
        csv_rows = []
        for r in combined_rows:
            rd = {"Crime Type": r["label"].replace("<b>","").replace("</b>","")}
            for ci,cn in enumerate(combined_cols): rd[cn]=r["vals"][ci]
            rd["Row Type"]=r["type"]; csv_rows.append(rd)
        _dl_csv(pd.DataFrame(csv_rows), "combined_table")

    # ── Standalone tables ──
    st.markdown('<div class="section-hdr">🏘️ Non-Hospital Crimes</div>', unsafe_allow_html=True)
    piv_nh = _build_standalone_pivot(data, months_active, False)
    fig_nh = _render_standalone_table(piv_nh, "🏘️  NON-HOSPITAL CRIMES", is_primary=True)
    st.plotly_chart(fig_nh, use_container_width=True)
    n1,n2=st.columns(2)
    with n1: _dl_png(fig_nh, "nh_table")
    with n2: _dl_csv(piv_nh.reset_index().rename(columns={"index":"Crime Type"}), "nh_table")

    st.markdown('<div class="section-hdr">🏥 Hospital Crimes</div>', unsafe_allow_html=True)
    piv_h = _build_standalone_pivot(data, months_active, True)
    fig_h = _render_standalone_table(piv_h, "🏥  HOSPITAL CRIMES", is_primary=False)
    st.plotly_chart(fig_h, use_container_width=True)
    h1,h2=st.columns(2)
    with h1: _dl_png(fig_h, "h_table")
    with h2: _dl_csv(piv_h.reset_index().rename(columns={"index":"Crime Type"}), "h_table")

    # ── Monthly trend ──
    st.markdown('<div class="section-hdr">📈 Monthly Crime Trend</div>', unsafe_allow_html=True)
    monthly      = data.groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
    monthly_hosp = data[hospital_mask].groupby("Month", observed=True)["Count"].sum().reindex(months_active).fillna(0)
    monthly_non  = monthly - monthly_hosp
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=monthly.index.tolist(), y=monthly.values, name="All Crimes", line=dict(color="#2563eb",width=3), mode="lines+markers"))
    fig_trend.add_trace(go.Scatter(x=monthly_hosp.index.tolist(), y=monthly_hosp.values, name="Hospital", line=dict(color="#dc2626",width=2,dash="dot"), mode="lines+markers"))
    fig_trend.add_trace(go.Scatter(x=monthly_non.index.tolist(), y=monthly_non.values, name="Non-Hospital", line=dict(color="#16a34a",width=2,dash="dash"), mode="lines+markers"))
    fig_trend.update_layout(title="Total Crimes by Month")
    _style(fig_trend); _add_labels(fig_trend)
    st.plotly_chart(fig_trend, use_container_width=True)
    _dl_png(fig_trend, "monthly_trend")

    # ── Crime type breakdown ──
    st.markdown('<div class="section-hdr">🧩 Crime Type Breakdown</div>', unsafe_allow_html=True)
    by_type = data.groupby("Crime Type")["Count"].sum().sort_values(ascending=False).reset_index()
    ca,cb = st.columns(2)
    with ca:
        fig_bar = px.bar(by_type, x="Crime Type", y="Count", color="Crime Type", color_discrete_sequence=PAL, title="Crimes by Type (YTD)")
        fig_bar.update_layout(showlegend=False, xaxis_tickangle=-35)
        _style(fig_bar); _add_labels(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True); _dl_png(fig_bar, "type_bar")
    with cb:
        fig_pie = px.pie(by_type, names="Crime Type", values="Count", color_discrete_sequence=PAL, title="Crime Type Distribution", hole=0.45)
        _style(fig_pie); _add_labels(fig_pie)
        st.plotly_chart(fig_pie, use_container_width=True); _dl_png(fig_pie, "type_pie")
    _dl_csv(by_type, "type_summary")

    # ── Crime type deep dive ──
    st.markdown('<div class="section-hdr">🔬 Crime Type Deep Dive</div>', unsafe_allow_html=True)
    sel_ct = st.selectbox("Select a crime type:", sorted(data["Crime Type"].unique()), key="ct_dd")
    ct_data = data[data["Crime Type"]==sel_ct]
    ct_monthly = ct_data.groupby("Month",observed=True)["Count"].sum().reindex(months_active).fillna(0)
    ct_hosp = ct_data[ct_data["is_hospital"]].groupby("Month",observed=True)["Count"].sum().reindex(months_active).fillna(0)
    ct_roads = ct_data[~ct_data["is_hospital"]].groupby("Road")["Count"].sum().sort_values(ascending=False).head(10).reset_index()
    c1,c2 = st.columns(2)
    with c1:
        fig_ct = go.Figure()
        fig_ct.add_trace(go.Bar(x=ct_monthly.index.tolist(), y=ct_monthly.values, name="All", marker_color="#3b82f6"))
        fig_ct.add_trace(go.Bar(x=ct_hosp.index.tolist(), y=ct_hosp.values, name="Hospital", marker_color="#dc2626"))
        fig_ct.update_layout(title=f"{sel_ct} — Monthly", barmode="group")
        _style(fig_ct); _add_labels(fig_ct)
        st.plotly_chart(fig_ct, use_container_width=True); _dl_png(fig_ct, "dd_monthly")
    with c2:
        if not ct_roads.empty:
            fig_cr = px.bar(ct_roads, x="Count", y="Road", orientation="h", color_discrete_sequence=["#7c3aed"], title=f"{sel_ct} — Top Roads")
            _style(fig_cr); _add_labels(fig_cr)
            st.plotly_chart(fig_cr, use_container_width=True); _dl_png(fig_cr, "dd_roads")
        else: st.info("No non-hospital incidents.")
    ct_t=int(ct_data["Count"].sum()); ct_ht=int(ct_data[ct_data["is_hospital"]]["Count"].sum())
    st.markdown('<div class="kpi-row">'+kpi(f"Total {sel_ct.split(' and ')[0]}",ct_t,"blue")+kpi("Hospital",ct_ht,"red")+kpi("Non-Hospital",ct_t-ct_ht,"green")+kpi("% of All Crime",f"{round(ct_t/max(total_all,1)*100,1)}%","amber")+'</div>',unsafe_allow_html=True)

    # ── Hospital analysis ──
    st.markdown('<div class="section-hdr">🏥 Hospital Crime Analysis</div>', unsafe_allow_html=True)
    hosp_data = data[hospital_mask]
    if not hosp_data.empty:
        hc1,hc2=st.columns(2)
        with hc1:
            hbt = hosp_data.groupby("Crime Type")["Count"].sum().sort_values(ascending=False).reset_index()
            fig_hbt = px.bar(hbt, x="Crime Type", y="Count", color="Crime Type", color_discrete_sequence=PAL, title="Hospital Crimes by Type")
            fig_hbt.update_layout(showlegend=False, xaxis_tickangle=-35)
            _style(fig_hbt); _add_labels(fig_hbt)
            st.plotly_chart(fig_hbt, use_container_width=True); _dl_png(fig_hbt, "hosp_type")
        with hc2:
            hm = hosp_data.groupby("Month",observed=True)["Count"].sum().reindex(months_active).fillna(0)
            fig_hm = go.Figure(go.Bar(x=hm.index.tolist(), y=hm.values, marker_color="#dc2626"))
            fig_hm.update_layout(title="Hospital — Monthly")
            _style(fig_hm); _add_labels(fig_hm)
            st.plotly_chart(fig_hm, use_container_width=True); _dl_png(fig_hm, "hosp_monthly")

    # ── Road-specific analysis ──
    st.markdown('<div class="section-hdr">🛣️ Road-Specific Analysis</div>', unsafe_allow_html=True)
    non_hosp = data[~hospital_mask]
    sel_rd = st.selectbox("Select a road:", sorted(non_hosp["Road"].unique()), key="rd_sel")
    rd_data = non_hosp[non_hosp["Road"]==sel_rd]
    if not rd_data.empty:
        r1,r2=st.columns(2)
        with r1:
            rd_m=rd_data.groupby("Month",observed=True)["Count"].sum().reindex(months_active).fillna(0)
            fig_rd=go.Figure(go.Bar(x=rd_m.index.tolist(),y=rd_m.values,marker_color="#0891b2"))
            fig_rd.update_layout(title=f"{sel_rd} — Monthly")
            _style(fig_rd); _add_labels(fig_rd)
            st.plotly_chart(fig_rd,use_container_width=True); _dl_png(fig_rd,"road_monthly")
        with r2:
            rd_t=rd_data.groupby("Crime Type")["Count"].sum().sort_values(ascending=False).reset_index()
            fig_rdt=px.bar(rd_t,x="Count",y="Crime Type",orientation="h",color_discrete_sequence=["#0891b2"],title=f"{sel_rd} — Crime Types")
            _style(fig_rdt); _add_labels(fig_rdt)
            st.plotly_chart(fig_rdt,use_container_width=True); _dl_png(fig_rdt,"road_types")
        rd_tot=int(rd_data["Count"].sum()); rd_pct=round(rd_tot/max(total_non_hosp,1)*100,1)
        st.markdown('<div class="kpi-row">'+kpi(f"Total on {sel_rd}",rd_tot,"cyan")+kpi("% of Non-Hospital",f"{rd_pct}%","amber")+kpi("Active Months",int((rd_m>0).sum()),"purple")+'</div>',unsafe_allow_html=True)
    else: st.info("No recorded crimes on this road.")

    # ── Top 10 hotspots ──
    st.markdown('<div class="section-hdr">🔥 Top 10 Crime Hotspots</div>', unsafe_allow_html=True)
    hotspots = non_hosp.groupby("Road")["Count"].sum().sort_values(ascending=False).head(10).reset_index().rename(columns={"Count":"Total Crimes"})
    hsc1,hsc2=st.columns([3,2])
    with hsc1:
        fig_hot=px.bar(hotspots,x="Total Crimes",y="Road",orientation="h",color="Total Crimes",color_continuous_scale="YlOrRd",title="Top 10 Roads (excl. Hospital)")
        fig_hot.update_layout(coloraxis_showscale=False,yaxis=dict(autorange="reversed"))
        _style(fig_hot,420); _add_labels(fig_hot)
        st.plotly_chart(fig_hot,use_container_width=True); _dl_png(fig_hot,"top10")
    with hsc2:
        st.dataframe(hotspots.set_index("Road"),use_container_width=True,height=400); _dl_csv(hotspots,"top10")

    # ── Heatmap ──
    st.markdown('<div class="section-hdr">🗓️ Crime Type × Month Heatmap</div>', unsafe_allow_html=True)
    pivot = data.groupby(["Crime Type","Month"],observed=True)["Count"].sum().unstack(fill_value=0).reindex(columns=months_active,fill_value=0)
    fig_hm = px.imshow(pivot.values, x=months_active, y=pivot.index.tolist(), color_continuous_scale="Blues", aspect="auto", title="Crime Intensity Heatmap", labels=dict(color="Crimes"))
    _style(fig_hm, 450)
    st.plotly_chart(fig_hm, use_container_width=True); _dl_png(fig_hm, "heatmap")

    # ── Anomaly detection ──
    st.markdown('<div class="section-hdr">⚠️ Anomaly Detection — Unusual Spikes</div>', unsafe_allow_html=True)
    st.caption("Flagged when monthly count > 1.5 std deviations above the mean for that crime type.")
    anomalies = []
    for ct in data["Crime Type"].unique():
        s=data[data["Crime Type"]==ct].groupby("Month",observed=True)["Count"].sum().reindex(months_active).fillna(0)
        m_,s_=s.mean(),s.std()
        if s_==0: continue
        th=m_+1.5*s_
        for mo,val in s.items():
            if val>th: anomalies.append({"Month":mo,"Crime Type":ct,"Count":int(val),"Mean":round(m_,1),"Threshold":round(th,1),"Std Devs Above Mean":round((val-m_)/s_,2)})
    if anomalies:
        adf=pd.DataFrame(anomalies).sort_values("Std Devs Above Mean",ascending=False)
        a1,a2=st.columns([3,2])
        with a1:
            fig_an=px.scatter(adf,x="Month",y="Crime Type",size="Count",color="Std Devs Above Mean",color_continuous_scale="YlOrRd",title="Detected Anomalies",size_max=35)
            _style(fig_an,400); st.plotly_chart(fig_an,use_container_width=True); _dl_png(fig_an,"anomalies")
        with a2: st.dataframe(adf.reset_index(drop=True),use_container_width=True,height=350); _dl_csv(adf,"anomalies")
        w=adf.iloc[0]
        st.warning(f"**Largest spike:** {w['Crime Type']} in **{w['Month']}** with **{w['Count']} incidents** ({w['Std Devs Above Mean']}σ above mean of {w['Mean']}).")
    else: st.success("No significant anomalies detected.")

    # ── Raw data ──
    with st.expander("📋 View / Download Full Data Table"):
        wide=(data.pivot_table(index=["Road","Month"],columns="Crime Type",values="Count",aggfunc="sum").fillna(0).astype(int))
        wide["Total"]=wide.sum(axis=1); wide=wide.reset_index()
        st.dataframe(wide,use_container_width=True,height=400); _dl_csv(wide,"raw_data")

# ╔══════════════════════════════════════════════════════════════╗
# ║  PAGE 2: YEAR-ON-YEAR COMPARISON                            ║
# ╚══════════════════════════════════════════════════════════════╝
elif page == "📅 Year-on-Year" and data_prev is not None:
    st.markdown(f"## 📅 Year-on-Year Comparison — {prev_year_label} vs {current_year_label}")

    all_months_yoy = sorted(set(months_active)|set(months_active_prev), key=lambda m:MONTH_ORDER.index(m))
    hosp_mask_prev = data_prev["is_hospital"]

    def _mt(df, months): return df.groupby("Month",observed=True)["Count"].sum().reindex(months).fillna(0)
    def _mtf(df, ih, months): return df[df["is_hospital"]==ih].groupby("Month",observed=True)["Count"].sum().reindex(months).fillna(0)

    prev_total    = int(data_prev["Count"].sum())
    prev_hospital = int(data_prev.loc[hosp_mask_prev,"Count"].sum())
    prev_non_hosp = prev_total - prev_hospital
    prev_n_months = len(months_active_prev)
    prev_avg      = round(prev_total / max(prev_n_months,1), 1)

    def _delta(curr, prev):
        if prev==0: return "+∞" if curr>0 else "–"
        pct=round((curr-prev)/prev*100,1); return f"{'+' if pct>0 else ''}{pct}%"
    def _dcol(curr, prev): return "green" if curr<=prev else "red"

    def kpi_yoy(label, curr, prev):
        d=_delta(curr,prev); c=_dcol(curr,prev)
        return (f'<div class="kpi-card kpi-{c}"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{curr}</div>'
                f'<div style="font-size:.75rem;color:#9ca3af;margin-top:4px;">{prev_year_label}: {prev} ({d})</div></div>')

    prev_non_hosp_data   = data_prev[~data_prev["is_hospital"]]
    prev_avg_nh          = round(prev_non_hosp - 0, 1)  # placeholder; recompute properly
    prev_avg_nh          = round((prev_total - prev_hospital) / max(prev_n_months, 1), 1)
    prev_most_common_nh  = prev_non_hosp_data.groupby("Crime Type")["Count"].sum().idxmax() if not prev_non_hosp_data.empty else "N/A"
    prev_most_common_nh_short = prev_most_common_nh.replace(" and Sexual Offences","").replace("& Weapons","").strip()
    prev_monthly_nh      = prev_non_hosp_data.groupby("Month", observed=True)["Count"].sum().reindex(months_active_prev).fillna(0)
    prev_high_month_nh   = prev_monthly_nh.idxmax() if not prev_monthly_nh.empty else "N/A"
    prev_high_val_nh     = int(prev_monthly_nh.max()) if not prev_monthly_nh.empty else 0

    pct_change_total = round((total_all - prev_total) / max(prev_total, 1) * 100, 1)
    pct_str = f"{'+' if pct_change_total > 0 else ''}{pct_change_total}%"
    pct_col = "red" if pct_change_total > 0 else "green"

    st.markdown(
        '<div class="kpi-row">'
        + kpi_yoy("Total Crimes YTD", total_all, prev_total)
        + kpi_yoy("Non-Hospital Total", total_non_hosp, prev_non_hosp)
        + kpi(f"Non-Hospital High Crime Month", f"{high_crime_month_nh} ({high_crime_month_nh_val})<br><small style='color:#9ca3af'>{prev_year_label}: {prev_high_month_nh} ({prev_high_val_nh})</small>", "red")
        + kpi(f"Most Common (Non-Hospital)", f"{most_common_nh_short}<br><small style='color:#9ca3af'>{prev_year_label}: {prev_most_common_nh_short}</small>", "purple")
        + kpi_yoy("Avg Non-Hospital / Month", avg_non_hosp_month, prev_avg_nh)
        + kpi("% Change vs Previous Year", pct_str, pct_col)
        + '</div>', unsafe_allow_html=True)

    # ── Monthly overlay ──
    st.markdown('<div class="section-hdr">📈 Monthly Trend — Year-on-Year</div>', unsafe_allow_html=True)
    cm=_mt(data,all_months_yoy); pm=_mt(data_prev,all_months_yoy)
    fig_yoy=go.Figure()
    fig_yoy.add_trace(go.Scatter(x=all_months_yoy,y=cm.values,name=current_year_label,mode="lines+markers",line=dict(color="#3b82f6",width=3)))
    fig_yoy.add_trace(go.Scatter(x=all_months_yoy,y=pm.values,name=prev_year_label,mode="lines+markers",line=dict(color="#94a3b8",width=2,dash="dash")))
    fig_yoy.update_layout(title="All Crimes — Monthly Overlay")
    _style(fig_yoy); _add_labels(fig_yoy)
    st.plotly_chart(fig_yoy,use_container_width=True); _dl_png(fig_yoy,"yoy_trend")

    # ── NH & Hospital side by side ──
    yc1,yc2=st.columns(2)
    with yc1:
        cnh=_mtf(data,False,all_months_yoy); pnh=_mtf(data_prev,False,all_months_yoy)
        fig_nhy=go.Figure()
        fig_nhy.add_trace(go.Bar(x=all_months_yoy,y=cnh.values,name=current_year_label,marker_color="#3b82f6"))
        fig_nhy.add_trace(go.Bar(x=all_months_yoy,y=pnh.values,name=prev_year_label,marker_color="#94a3b8"))
        fig_nhy.update_layout(title="Non-Hospital — YoY",barmode="group")
        _style(fig_nhy); _add_labels(fig_nhy)
        st.plotly_chart(fig_nhy,use_container_width=True); _dl_png(fig_nhy,"yoy_nh")
    with yc2:
        ch_=_mtf(data,True,all_months_yoy); ph=_mtf(data_prev,True,all_months_yoy)
        fig_hy=go.Figure()
        fig_hy.add_trace(go.Bar(x=all_months_yoy,y=ch_.values,name=current_year_label,marker_color="#dc2626"))
        fig_hy.add_trace(go.Bar(x=all_months_yoy,y=ph.values,name=prev_year_label,marker_color="#94a3b8"))
        fig_hy.update_layout(title="Hospital — YoY",barmode="group")
        _style(fig_hy); _add_labels(fig_hy)
        st.plotly_chart(fig_hy,use_container_width=True); _dl_png(fig_hy,"yoy_h")

    # ── Crime type comparison ──
    st.markdown('<div class="section-hdr">🧩 Crime Type Comparison</div>', unsafe_allow_html=True)
    cbt=data.groupby("Crime Type")["Count"].sum(); pbt=data_prev.groupby("Crime Type")["Count"].sum()
    all_ct=sorted(set(cbt.index)|set(pbt.index))
    comp_rows=[]
    for ct in all_ct:
        cv_=int(cbt.get(ct,0)); pv_=int(pbt.get(ct,0))
        comp_rows.append({"Crime Type":ct,current_year_label:cv_,prev_year_label:pv_,"Change":cv_-pv_,"Change %":_delta(cv_,pv_)})
    comp_df=pd.DataFrame(comp_rows).sort_values(current_year_label,ascending=False)
    comp_df=pd.concat([comp_df,pd.DataFrame([{"Crime Type":"TOTAL",current_year_label:total_all,prev_year_label:prev_total,"Change":total_all-prev_total,"Change %":_delta(total_all,prev_total)}])],ignore_index=True)

    tc1,tc2=st.columns([3,2])
    with tc1:
        pltdf=comp_df[comp_df["Crime Type"]!="TOTAL"].melt(id_vars="Crime Type",value_vars=[current_year_label,prev_year_label],var_name="Year",value_name="Crimes")
        fig_cb=px.bar(pltdf,x="Crime Type",y="Crimes",color="Year",barmode="group",color_discrete_map={current_year_label:"#3b82f6",prev_year_label:"#94a3b8"},title="Crime Type — YoY")
        fig_cb.update_layout(xaxis_tickangle=-35)
        _style(fig_cb,420); _add_labels(fig_cb)
        st.plotly_chart(fig_cb,use_container_width=True); _dl_png(fig_cb,"yoy_type_bar")
    with tc2:
        st.dataframe(comp_df,use_container_width=True,height=420); _dl_csv(comp_df,"yoy_type_table")

    # ── Hotspot comparison ──
    st.markdown('<div class="section-hdr">🔥 Hotspot Comparison — Top Roads</div>', unsafe_allow_html=True)
    cr=data[~data["is_hospital"]].groupby("Road")["Count"].sum()
    pr=data_prev[~data_prev["is_hospital"]].groupby("Road")["Count"].sum()
    tu=sorted(set(cr.sort_values(ascending=False).head(10).index)|set(pr.sort_values(ascending=False).head(10).index),key=lambda r:cr.get(r,0)+pr.get(r,0),reverse=True)[:15]
    hs_rows=[{"Road":rd,current_year_label:int(cr.get(rd,0)),prev_year_label:int(pr.get(rd,0)),"Change":int(cr.get(rd,0))-int(pr.get(rd,0)),"Change %":_delta(int(cr.get(rd,0)),int(pr.get(rd,0)))} for rd in tu]
    hs_df=pd.DataFrame(hs_rows)
    hsc1,hsc2=st.columns([3,2])
    with hsc1:
        hsm=hs_df.melt(id_vars="Road",value_vars=[current_year_label,prev_year_label],var_name="Year",value_name="Crimes")
        fig_hs=px.bar(hsm,x="Crimes",y="Road",color="Year",orientation="h",barmode="group",color_discrete_map={current_year_label:"#3b82f6",prev_year_label:"#94a3b8"},title="Road Hotspots — YoY")
        _style(fig_hs,480); _add_labels(fig_hs)
        st.plotly_chart(fig_hs,use_container_width=True); _dl_png(fig_hs,"yoy_hotspots")
    with hsc2:
        st.dataframe(hs_df,use_container_width=True,height=480); _dl_csv(hs_df,"yoy_hotspots")

    # ── Summary callout ──
    oc=total_all-prev_total; d="risen" if oc>0 else "fallen" if oc<0 else "remained the same"
    ico="🔴" if oc>0 else "🟢" if oc<0 else "⚪"
    nhc=total_non_hosp-prev_non_hosp; nhd="up" if nhc>0 else "down" if nhc<0 else "flat"
    hc_=total_hospital-prev_hospital; hd="up" if hc_>0 else "down" if hc_<0 else "flat"
    st.info(f"{ico} **Overall crime has {d}** from **{prev_total}** ({prev_year_label}) to **{total_all}** ({current_year_label}) — **{_delta(total_all,prev_total)}**.\n\n"
            f"Non-hospital: **{nhd}** ({prev_non_hosp} → {total_non_hosp}, {_delta(total_non_hosp,prev_non_hosp)}). "
            f"Hospital: **{hd}** ({prev_hospital} → {total_hospital}, {_delta(total_hospital,prev_hospital)}).")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.caption("Crime Stats Analyser · Charts downloadable as PNG · Upload previous year to unlock Year-on-Year page")
