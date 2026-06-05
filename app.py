import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
from datetime import datetime, timedelta

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sales Analytics Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background-color: #060d1a; color: #e2e8f0; }
[data-testid="stSidebar"] { background-color: #0a1628; border-right: 1px solid #1a2744; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.metric-card {
    background: linear-gradient(145deg, #0d1f3c, #0a1628);
    border: 1px solid #1a2744;
    border-radius: 14px;
    padding: 18px 16px;
    text-align: center;
    margin-bottom: 8px;
}
.metric-label { color: #4a6080; font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 6px; }
.metric-value { font-size: 24px; font-weight: 700; font-family: 'Space Mono', monospace; }
.profit-card {
    background: linear-gradient(145deg, #0a2a1a, #061a10);
    border: 1px solid #1a4a2a;
    border-radius: 14px; padding: 18px 16px; text-align: center; margin-bottom: 8px;
}
.loss-card {
    background: linear-gradient(145deg, #2a0a0a, #1a0606);
    border: 1px solid #4a1a1a;
    border-radius: 14px; padding: 18px 16px; text-align: center; margin-bottom: 8px;
}
.holiday-card {
    background: linear-gradient(145deg, #1a1a0a, #12120a);
    border: 1px solid #3a3a1a;
    border-radius: 14px; padding: 14px 16px; margin-bottom: 8px;
}
.forecast-box {
    background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(56,189,248,0.08));
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 12px; padding: 14px 16px; text-align: center; margin: 6px 0;
}
.section-header {
    font-size: 16px; font-weight: 700; color: #e2e8f0;
    margin: 20px 0 12px 0; padding-bottom: 8px;
    border-bottom: 1px solid #1a2744;
}
.report-block {
    background: #0d1f3c; border: 1px solid #1a2744;
    border-radius: 12px; padding: 16px; margin-bottom: 12px;
}
h1, h2, h3 { color: #e2e8f0 !important; }
.stTabs [data-baseweb="tab"] { color: #4a6080; font-weight: 600; font-size: 13px; }
.stTabs [aria-selected="true"] { color: #38bdf8 !important; border-bottom-color: #38bdf8 !important; }
div[data-testid="stFileUploader"] { background: #0d1f3c; border: 2px dashed #1a2744; border-radius: 14px; padding: 10px; }
div[data-testid="stFileUploader"]:hover { border-color: #38bdf8; }
.stSelectbox label, .stSlider label, .stMultiSelect label, .stCheckbox label { color: #94a3b8 !important; font-size: 13px !important; }
.stButton > button { background: linear-gradient(135deg, #38bdf8, #6366f1); color: #060d1a; border: none; border-radius: 8px; font-weight: 700; padding: 8px 20px; }
.stButton > button:hover { opacity: 0.85; }
.stDataFrame { background: #0d1f3c !important; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

PL = dict(
    paper_bgcolor="#060d1a", plot_bgcolor="#0d1f3c",
    font=dict(color="#94a3b8", family="DM Sans"),
    xaxis=dict(gridcolor="#1a2744", linecolor="#1a2744", tickfont=dict(size=11)),
    yaxis=dict(gridcolor="#1a2744", linecolor="#1a2744", tickfont=dict(size=11)),
    legend=dict(bgcolor="#0d1f3c", bordercolor="#1a2744", borderwidth=1),
    margin=dict(l=10, r=10, t=44, b=10),
)

# Indian Public Holidays (static list — expand as needed)
INDIAN_HOLIDAYS = {
    "Republic Day": "01-26", "Holi": "03-14", "Good Friday": "04-18",
    "Ram Navami": "04-06", "Eid ul-Fitr": "04-10", "Ambedkar Jayanti": "04-14",
    "Labour Day": "05-01", "Eid ul-Adha": "06-17", "Independence Day": "08-15",
    "Janmashtami": "08-16", "Ganesh Chaturthi": "08-27", "Gandhi Jayanti": "10-02",
    "Dussehra": "10-12", "Diwali": "10-20", "Bhai Dooj": "10-23",
    "Guru Nanak Jayanti": "11-15", "Christmas": "12-25", "New Year": "01-01",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_file(f):
    try:
        name = f.name.lower()
        if name.endswith(".csv"):
            return pd.read_csv(f)
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(f)
    except Exception as e:
        st.error(f"Load error: {e}")
    return None

def moving_avg(s, w):
    return s.rolling(window=w, min_periods=1).mean()

def linear_trend(s):
    x = np.arange(len(s))
    c = np.polyfit(x, s.values, 1)
    return np.polyval(c, x), c

def forecast_vals(c, n, fp):
    return np.polyval(c, np.arange(n, n + fp))

def calc_stats(s):
    v = s.dropna()
    g = ((v.iloc[-1] - v.iloc[0]) / abs(v.iloc[0])) * 100 if len(v) > 1 and v.iloc[0] != 0 else 0
    return {"Total Sales": v.sum(), "Avg Sales": v.mean(), "Peak Sales": v.max(),
            "Min Sales": v.min(), "Std Dev": v.std(), "Growth %": g}

def detect_date_col(df):
    for c in df.columns:
        try:
            pd.to_datetime(df[c], infer_datetime_format=True, errors="raise")
            return c
        except Exception:
            continue
    return None

def weekly_report(df, date_col, sales_col, cost_col=None):
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    d["Week"] = d[date_col].dt.to_period("W").astype(str)
    agg = {sales_col: "sum"}
    if cost_col:
        agg[cost_col] = "sum"
    r = d.groupby("Week").agg(agg).reset_index()
    if cost_col:
        r["Profit"] = r[sales_col] - r[cost_col]
        r["Profit %"] = (r["Profit"] / r[sales_col] * 100).round(2)
        r["Status"] = r["Profit"].apply(lambda x: "✅ Profit" if x >= 0 else "❌ Loss")
    return r

def monthly_report(df, date_col, sales_col, cost_col=None):
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    d["Month"] = d[date_col].dt.to_period("M").astype(str)
    agg = {sales_col: "sum"}
    if cost_col:
        agg[cost_col] = "sum"
    r = d.groupby("Month").agg(agg).reset_index()
    if cost_col:
        r["Profit"] = r[sales_col] - r[cost_col]
        r["Profit %"] = (r["Profit"] / r[sales_col] * 100).round(2)
        r["Status"] = r["Profit"].apply(lambda x: "✅ Profit" if x >= 0 else "❌ Loss")
    return r

def holiday_sales(df, date_col, sales_col):
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    d["md"] = d[date_col].dt.strftime("%m-%d")
    results = []
    for name, md in INDIAN_HOLIDAYS.items():
        match = d[d["md"] == md]
        if not match.empty:
            results.append({
                "Holiday": name,
                "Date": md,
                "Sales": match[sales_col].sum(),
                "Rows": len(match),
            })
    return pd.DataFrame(results) if results else None

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Sales Analytics Pro")
    st.markdown("---")
    uploaded = st.file_uploader("📂 Upload Dataset", type=["csv", "xlsx", "xls"],
                                 help="CSV or Excel with Date, Sales, Cost columns")
    st.markdown("---")
    st.markdown("#### ⚙️ Column Settings")

    df_raw = None
    date_col = sales_col = cost_col = label_col = value_col = None
    ma_window = 3
    forecast_periods = 3

    if uploaded:
        df_raw = load_file(uploaded)
        if df_raw is not None:
            cols = df_raw.columns.tolist()
            num_cols = df_raw.select_dtypes(include=np.number).columns.tolist()

            auto_date = detect_date_col(df_raw)
            date_col = st.selectbox("📅 Date Column", ["(none)"] + cols,
                                     index=cols.index(auto_date) + 1 if auto_date else 0)
            if date_col == "(none)":
                date_col = None

            label_col = st.selectbox("🏷️ Label Column", cols, index=0)
            value_col = st.selectbox("💰 Sales Column", num_cols if num_cols else cols, index=0)
            cost_col_opt = st.selectbox("🧾 Cost Column (optional)", ["(none)"] + num_cols, index=0)
            cost_col = None if cost_col_opt == "(none)" else cost_col_opt

            st.markdown("---")
            ma_window = st.slider("Moving Avg Window", 2, min(10, len(df_raw)), 3)
            forecast_periods = st.slider("Forecast Periods", 1, 24, 6)

    st.markdown("---")
    st.markdown("<div style='color:#1a2744;font-size:11px;text-align:center'>Sales Analytics Pro · Streamlit</div>",
                unsafe_allow_html=True)

# ─── Main ─────────────────────────────────────────────────────────────────────
st.markdown("# 📊 Sales Analytics & Forecasting")

if df_raw is None:
    c1, c2, c3, c4 = st.columns(4)
    for col, icon, title, sub, color in zip(
        [c1, c2, c3, c4],
        ["📂", "⚙️", "📈", "🔮"],
        ["Upload File", "Configure", "Analyze", "Forecast"],
        ["CSV / Excel", "Date · Sales · Cost", "Reports & P&L", "Future Estimation"],
        ["#38bdf8", "#818cf8", "#34d399", "#fb923c"]
    ):
        with col:
            st.markdown(f"""<div class='metric-card'>
                <div style='font-size:30px'>{icon}</div>
                <div style='color:{color};font-weight:700;margin-top:8px'>{title}</div>
                <div style='color:#4a6080;font-size:12px;margin-top:4px'>{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📋 Recommended CSV Format")
    sample = pd.DataFrame({
        "Date": ["2024-01-01","2024-01-08","2024-01-15","2024-01-22","2024-01-29"],
        "Sales": [45000, 52000, 48000, 61000, 57000],
        "Cost":  [30000, 34000, 31000, 40000, 37000],
        "Region": ["South","South","South","South","South"],
    })
    st.dataframe(sample, use_container_width=True)
    st.stop()

# ── Prepare base series ───────────────────────────────────────────────────────
sales_series = pd.to_numeric(df_raw[value_col], errors="coerce").fillna(0).reset_index(drop=True)
labels_series = df_raw[label_col].astype(str).reset_index(drop=True)

cost_series = None
if cost_col:
    cost_series = pd.to_numeric(df_raw[cost_col], errors="coerce").fillna(0).reset_index(drop=True)

profit_series = (sales_series - cost_series) if cost_series is not None else None

ma = moving_avg(sales_series, ma_window)
trend_line, coeffs = linear_trend(sales_series)
f_vals = forecast_vals(coeffs, len(sales_series), forecast_periods)
f_labels = [f"P+{i+1}" for i in range(forecast_periods)]
stats = calc_stats(sales_series)

# ── Confidence Interval for forecast ─────────────────────────────────────────
residuals = sales_series.values - trend_line
std_res = np.std(residuals)
f_upper = f_vals + 1.64 * std_res  # 90% CI
f_lower = f_vals - 1.64 * std_res

# ── KPI Row ───────────────────────────────────────────────────────────────────
kpi_cols = st.columns(6)
kpi_color = {"Total Sales":"#38bdf8","Avg Sales":"#818cf8","Peak Sales":"#34d399",
             "Min Sales":"#fb923c","Std Dev":"#64748b",
             "Growth %": "#34d399" if stats["Growth %"] >= 0 else "#f87171"}
for col_ui, (k, v) in zip(kpi_cols, stats.items()):
    u = "%" if k == "Growth %" else ""
    with col_ui:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>{k}</div>
            <div class='metric-value' style='color:{kpi_color[k]}'>{v:,.1f}{u}</div>
        </div>""", unsafe_allow_html=True)

if profit_series is not None:
    total_profit = profit_series.sum()
    total_cost = cost_series.sum()
    profit_pct = (total_profit / sales_series.sum() * 100) if sales_series.sum() else 0
    profit_periods = (profit_series >= 0).sum()
    loss_periods = (profit_series < 0).sum()
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        card_cls = "profit-card" if total_profit >= 0 else "loss-card"
        emoji = "✅" if total_profit >= 0 else "❌"
        st.markdown(f"""<div class='{card_cls}'>
            <div class='metric-label'>Net Profit/Loss</div>
            <div class='metric-value' style='color:{"#34d399" if total_profit>=0 else "#f87171"}'>{emoji} {total_profit:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with p2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Cost</div>
            <div class='metric-value' style='color:#fb923c'>{total_cost:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with p3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Profit Margin</div>
            <div class='metric-value' style='color:#34d399'>{profit_pct:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with p4:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Profit / Loss Periods</div>
            <div class='metric-value' style='color:#94a3b8;font-size:18px'>✅{profit_periods} / ❌{loss_periods}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_list = ["📊 Overview", "📅 Weekly Report", "🗓️ Monthly Report",
            "🎉 Holiday Sales", "💰 Profit & Loss", "🔮 Forecast", "📋 Data"]
tabs = st.tabs(tab_list)

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels_series, y=sales_series, mode="lines+markers",
        name="Actual Sales", line=dict(color="#38bdf8", width=2.5),
        marker=dict(size=5), fill="tozeroy", fillcolor="rgba(56,189,248,0.07)"))
    fig.add_trace(go.Scatter(x=labels_series, y=ma, mode="lines",
        name=f"MA({ma_window})", line=dict(color="#34d399", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=labels_series, y=trend_line, mode="lines",
        name="Trend", line=dict(color="#818cf8", width=1.5, dash="dash")))
    fig.update_layout(title="Sales Overview · Moving Average · Trend", **PL, height=400)
    st.plotly_chart(fig, use_container_width=True)

    if profit_series is not None:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=labels_series, y=sales_series, name="Sales",
            marker_color="#38bdf8", opacity=0.75))
        fig2.add_trace(go.Bar(x=labels_series, y=cost_series, name="Cost",
            marker_color="#fb923c", opacity=0.75))
        fig2.add_trace(go.Scatter(x=labels_series, y=profit_series, mode="lines+markers",
            name="Profit/Loss", line=dict(color="#34d399", width=2),
            marker=dict(color=["#34d399" if v >= 0 else "#f87171" for v in profit_series], size=7)))
        fig2.update_layout(title="Sales vs Cost vs Profit", barmode="group", **PL, height=360)
        st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — WEEKLY REPORT
# ════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("<div class='section-header'>📅 Weekly Sales Report</div>", unsafe_allow_html=True)
    if date_col is None:
        st.warning("⚠️ Please select a Date Column in the sidebar to enable Weekly Report.")
    else:
        w_df = weekly_report(df_raw, date_col, value_col, cost_col)
        if w_df.empty:
            st.info("No data after date parsing.")
        else:
            # Chart
            fig = go.Figure()
            fig.add_trace(go.Bar(x=w_df["Week"], y=w_df[value_col],
                name="Weekly Sales", marker_color="#38bdf8", opacity=0.8))
            if cost_col and "Profit" in w_df.columns:
                colors = ["#34d399" if v >= 0 else "#f87171" for v in w_df["Profit"]]
                fig.add_trace(go.Bar(x=w_df["Week"], y=w_df["Profit"],
                    name="Profit/Loss", marker_color=colors, opacity=0.9))
            fig.update_layout(title="Weekly Sales & Profit/Loss", barmode="group", **PL, height=380)
            st.plotly_chart(fig, use_container_width=True)

            # Best / Worst week
            best_w = w_df.loc[w_df[value_col].idxmax()]
            worst_w = w_df.loc[w_df[value_col].idxmin()]
            bw1, bw2 = st.columns(2)
            with bw1:
                st.markdown(f"""<div class='profit-card'>
                    <div class='metric-label'>🏆 Best Week</div>
                    <div style='color:#34d399;font-weight:700;font-size:15px'>{best_w['Week']}</div>
                    <div class='metric-value' style='color:#34d399'>{best_w[value_col]:,.0f}</div>
                </div>""", unsafe_allow_html=True)
            with bw2:
                st.markdown(f"""<div class='loss-card'>
                    <div class='metric-label'>📉 Worst Week</div>
                    <div style='color:#f87171;font-weight:700;font-size:15px'>{worst_w['Week']}</div>
                    <div class='metric-value' style='color:#f87171'>{worst_w[value_col]:,.0f}</div>
                </div>""", unsafe_allow_html=True)

            st.dataframe(w_df, use_container_width=True)
            buf = io.BytesIO()
            w_df.to_excel(buf, index=False, engine="openpyxl")
            st.download_button("⬇️ Download Weekly Report", buf.getvalue(),
                               "weekly_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — MONTHLY REPORT
# ════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<div class='section-header'>🗓️ Monthly Sales Report</div>", unsafe_allow_html=True)
    if date_col is None:
        st.warning("⚠️ Please select a Date Column in the sidebar to enable Monthly Report.")
    else:
        m_df = monthly_report(df_raw, date_col, value_col, cost_col)
        if m_df.empty:
            st.info("No data after date parsing.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=m_df["Month"], y=m_df[value_col],
                name="Monthly Sales", marker_color="#818cf8", opacity=0.85))
            if cost_col and "Profit" in m_df.columns:
                colors = ["#34d399" if v >= 0 else "#f87171" for v in m_df["Profit"]]
                fig.add_trace(go.Bar(x=m_df["Month"], y=m_df["Profit"],
                    name="Profit/Loss", marker_color=colors, opacity=0.9))
            fig.update_layout(title="Monthly Sales & Profit/Loss", barmode="group", **PL, height=380)
            st.plotly_chart(fig, use_container_width=True)

            # MoM Growth
            m_df["MoM Growth %"] = m_df[value_col].pct_change().mul(100).round(2)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=m_df["Month"], y=m_df["MoM Growth %"],
                marker_color=["#34d399" if (v or 0) >= 0 else "#f87171" for v in m_df["MoM Growth %"]],
                name="MoM Growth %"))
            fig2.update_layout(title="Month-over-Month Growth %", **PL, height=280)
            st.plotly_chart(fig2, use_container_width=True)

            best_m = m_df.loc[m_df[value_col].idxmax()]
            worst_m = m_df.loc[m_df[value_col].idxmin()]
            bm1, bm2 = st.columns(2)
            with bm1:
                st.markdown(f"""<div class='profit-card'>
                    <div class='metric-label'>🏆 Best Month</div>
                    <div style='color:#34d399;font-weight:700'>{best_m['Month']}</div>
                    <div class='metric-value' style='color:#34d399'>{best_m[value_col]:,.0f}</div>
                </div>""", unsafe_allow_html=True)
            wit
