"""
Chart View — detailed technical chart for a single stock.

This page is part of Streamlit's automatic "multipage app" feature: any
.py file placed in a pages/ folder next to app.py becomes its own URL.
Clicking the "View Chart" link on the main dashboard opens this page in
a new browser tab, passing the ticker via a URL query parameter, so this
page never crowds the main dashboard.
"""

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from stock_utils import fetch_daily, macd_lines, resample_ohlc, rsi_wilder

st.set_page_config(page_title="Stock Chart", page_icon="📊", layout="wide")

# --------------------------------------------------------------------------
# Read which stock to show from the URL (?ticker=OFSS.NS&name=OFSS)
# --------------------------------------------------------------------------

params = st.query_params
ticker = params.get("ticker", "")
name = params.get("name", ticker)

if not ticker:
    st.title("📊 Stock Chart")
    st.info(
        "No stock selected. Go back to the main dashboard and click a "
        "'📊 View Chart' link next to any stock to open its chart here."
    )
    st.stop()

st.title(f"📊 {name} — Technical Chart")
st.caption(f"Ticker: {ticker} · RSI (14, Wilder's) · MACD (12,26,9) · Data via Yahoo Finance (yfinance)")

timeframe = st.radio("Timeframe", ["Daily", "Weekly", "Monthly"], horizontal=True)

with st.spinner(f"Loading {name} data..."):
    daily = fetch_daily(ticker)

if daily.empty:
    st.error(f"Could not fetch data for '{ticker}'. Check that the ticker is correct (must end in .NS for NSE).")
    st.stop()

if timeframe == "Daily":
    df = daily.tail(260)  # ~1 trading year of candles
elif timeframe == "Weekly":
    df = resample_ohlc(daily, "W-FRI").tail(156)  # ~3 years of weekly candles
else:
    df = resample_ohlc(daily, "ME").tail(60)  # ~5 years of monthly candles

if len(df) < 20:
    st.warning("Not enough history for this timeframe yet.")
    st.stop()

rsi = rsi_wilder(df["Close"])
macd_line, signal_line = macd_lines(df["Close"])
macd_hist = macd_line - signal_line

# --------------------------------------------------------------------------
# Build the 4-panel chart: Candles, Volume, MACD, RSI
# --------------------------------------------------------------------------

fig = make_subplots(
    rows=4,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.45, 0.15, 0.2, 0.2],
)

# --- Candlesticks ---
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price",
        increasing_line_color="#16a34a",
        decreasing_line_color="#dc2626",
    ),
    row=1,
    col=1,
)

# --- Volume ---
vol_colors = ["#16a34a" if c >= o else "#dc2626" for o, c in zip(df["Open"], df["Close"])]
fig.add_trace(
    go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=vol_colors, showlegend=False),
    row=2,
    col=1,
)

# --- MACD ---
hist_colors = ["#16a34a" if v >= 0 else "#dc2626" for v in macd_hist]
fig.add_trace(go.Bar(x=df.index, y=macd_hist, name="MACD Hist", marker_color=hist_colors, showlegend=False), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=macd_line, name="MACD", line=dict(color="#111827", width=1.5)), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=signal_line, name="Signal", line=dict(color="#f59e0b", width=1.5)), row=3, col=1)

# --- RSI ---
fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color="#374151", width=1.5)), row=4, col=1)
fig.add_hline(y=60, line_dash="dot", line_color="#16a34a", row=4, col=1)
fig.add_hline(y=40, line_dash="dot", line_color="#dc2626", row=4, col=1)
# Shade overbought (>60) and oversold (<40) zones, like the reference chart
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=rsi.clip(lower=60),
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(22,163,74,0.15)",
        showlegend=False,
        hoverinfo="skip",
    ),
    row=4,
    col=1,
)
fig.add_trace(
    go.Scatter(x=df.index, y=[60] * len(df), line=dict(width=0), showlegend=False, hoverinfo="skip"),
    row=4,
    col=1,
)

fig.update_layout(
    height=850,
    xaxis_rangeslider_visible=False,
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    margin=dict(l=40, r=40, t=40, b=20),
    plot_bgcolor="white",
    paper_bgcolor="white",
)
fig.update_yaxes(range=[0, 100], row=4, col=1)

# --------------------------------------------------------------------------
# Panel captions ("Volume", "MACD (12,26,9)", "RSI (14)") — placed at the
# bottom-inside edge of each panel (like a caption under the chart) rather
# than Plotly's default of putting them above each panel.
# --------------------------------------------------------------------------

panel_labels = {"yaxis2": "Volume", "yaxis3": "MACD (12,26,9)", "yaxis4": "RSI (14)"}
for axis_name, label in panel_labels.items():
    domain_bottom = fig.layout[axis_name].domain[0]
    fig.add_annotation(
        text=label,
        xref="paper",
        x=0.5,
        yref="paper",
        y=domain_bottom,
        yanchor="bottom",
        showarrow=False,
        font=dict(size=13, color="#6b7280"),
    )

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "This chart is for informational purposes only and is not investment advice. "
    "Data may be delayed ~15 minutes relative to live NSE prices."
)
