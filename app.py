# -*- coding: utf-8 -*-
import os
import math
import time
import json
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone

# ======================
# App Config
# ======================
st.set_page_config(
    page_title="Quant Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================
# Utilities
# ======================
@st.cache_data(show_spinner=False)
def fetch_okx_candles(instId: str = "BTC-USDT", bar: str = "15m", limit: int = 500) -> pd.DataFrame:
    """
    Fetch candles from OKX public market API (no API key).
    Returns DataFrame with columns: [Time, Open, High, Low, Close, Volume], indexed by Time (datetime).
    """
    url = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar={bar}&limit={limit}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        js = r.json()
        if "data" not in js or not js["data"]:
            return pd.DataFrame()
        # OKX returns newest first; reverse to ascending
        raw = js["data"][::-1]
        # OKX columns: ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm
        cols = ["Time", "Open", "High", "Low", "Close", "Volume", "VolCcy", "VolCcyQuote", "Confirm"]
        df = pd.DataFrame(raw, columns=cols)
        # cast types
        df["Time"] = pd.to_datetime(df["Time"].astype(np.int64), unit="ms", utc=True).dt.tz_convert(None)
        for c in ["Open", "High", "Low", "Close", "Volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df[["Time", "Open", "High", "Low", "Close", "Volume"]].dropna().reset_index(drop=True)
        df = df.sort_values("Time").set_index("Time")
        return df
    except Exception:
        return pd.DataFrame()

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.clip(lower=0)).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger(series: pd.Series, period=20, stds=2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    upper = mid + stds * std
    lower = mid - stds * std
    return mid, upper, lower

def kdj(df: pd.DataFrame, n=9, k=3, d=3):
    low_list = df["Low"].rolling(n).min()
    high_list = df["High"].rolling(n).max()
    rsv = (df["Close"] - low_list) / (high_list - low_list + 1e-9) * 100
    K = rsv.ewm(com=k-1, adjust=False).mean()
    D = K.ewm(com=d-1, adjust=False).mean()
    J = 3 * K - 2 * D
    return K, D, J

def ma_cross_signals(close: pd.Series, fast: int = 10, slow: int = 20) -> pd.Series:
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()
    sig = pd.Series(index=close.index, dtype=object)
    sig[(ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))] = "BUY"
    sig[(ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))] = "SELL"
    return sig

def format_float(x):
    try:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return ""
        return str(x)
    except Exception:
        return str(x)

# ======================
# Sidebar Controls
# ======================
st.sidebar.subheader("Data Source")
source = st.sidebar.selectbox(
    "Source",
    ["OKX 公共行情（免API）", "（占位）其他数据源"],
    index=0
)

instId = st.sidebar.text_input("Symbol (OKX)", value="BTC-USDT")
interval = st.sidebar.selectbox(
    "K线周期",
    ["1m","3m","5m","15m","30m","1H","2H","4H","6H","12H","1D","1W","1M"],
    index=3  # 默认15m
)
limit = st.sidebar.slider("K线数量", min_value=100, max_value=2000, value=500, step=50)

st.sidebar.subheader("Indicators")
show_ma = st.sidebar.checkbox("MA (5/10/20)", value=True)
show_ema = st.sidebar.checkbox("EMA (12/26)", value=False)
show_boll = st.sidebar.checkbox("Bollinger (20,2)", value=False)
show_signals = st.sidebar.checkbox("MA Cross Signals", value=True)

st.sidebar.subheader("Subcharts")
show_volume = st.sidebar.checkbox("Volume", value=True)
show_macd = st.sidebar.checkbox("MACD", value=True)
show_rsi = st.sidebar.checkbox("RSI (14)", value=False)
show_kdj = st.sidebar.checkbox("KDJ (9,3,3)", value=False)

st.sidebar.subheader("Backtest Params")
fee = st.sidebar.number_input("Fee (bps)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
slippage = st.sidebar.number_input("Slippage (bps)", min_value=0.0, max_value=50.0, value=2.0, step=0.5)

# ======================
# Data Loading
# ======================
if source.startswith("OKX"):
    df = fetch_okx_candles(instId=instId, bar=interval, limit=limit)
else:
    df = pd.DataFrame()

if df.empty:
    st.warning("No data fetched. Please check symbol/interval or try again.")
    st.stop()

# Ensure columns
for col in ["Open", "High", "Low", "Close", "Volume"]:
    if col not in df.columns:
        st.error(f"Missing column: {col}")
        st.stop()

dfi = df.copy()

# ======================
# Indicators / Signals
# ======================
if show_ma:
    dfi["MA5"] = dfi["Close"].rolling(5).mean()
    dfi["MA10"] = dfi["Close"].rolling(10).mean()
    dfi["MA20"] = dfi["Close"].rolling(20).mean()
else:
    dfi["MA5"] = np.nan
    dfi["MA10"] = np.nan
    dfi["MA20"] = np.nan

if show_ema:
    dfi["EMA12"] = ema(dfi["Close"], 12)
    dfi["EMA26"] = ema(dfi["Close"], 26)
else:
    dfi["EMA12"] = np.nan
    dfi["EMA26"] = np.nan

if show_boll:
    mid, up, lo = bollinger(dfi["Close"], 20, 2.0)
    dfi["BOLL_M"] = mid
    dfi["BOLL_U"] = up
    dfi["BOLL_L"] = lo
else:
    dfi["BOLL_M"] = np.nan
    dfi["BOLL_U"] = np.nan
    dfi["BOLL_L"] = np.nan

if show_macd:
    macd_line, signal_line, hist = macd(dfi["Close"])
    dfi["MACD"] = macd_line
    dfi["MACD_SIGNAL"] = signal_line
    dfi["MACD_HIST"] = hist
else:
    dfi["MACD"] = np.nan
    dfi["MACD_SIGNAL"] = np.nan
    dfi["MACD_HIST"] = np.nan

if show_rsi:
    dfi["RSI"] = rsi(dfi["Close"], 14)
else:
    dfi["RSI"] = np.nan

if show_kdj:
    K, D, J = kdj(dfi, 9, 3, 3)
    dfi["K"], dfi["D"], dfi["J"] = K, D, J
else:
    dfi["K"], dfi["D"], dfi["J"] = np.nan, np.nan, np.nan

# Signals
signals = pd.Series(index=dfi.index, dtype=object)
if show_signals:
    signals = ma_cross_signals(dfi["Close"], 10, 20)
dfi["Signal"] = signals.fillna("")

# ======================
# Hovertext (English, original precision)
# ======================
vol_col = "Volume"
_time_str = dfi.index.astype(str)
dfi["hovertext"] = (
    "Time: " + _time_str +
    "<br>Open: " + dfi["Open"].astype(str) +
    "<br>High: " + dfi["High"].astype(str) +
    "<br>Low: " + dfi["Low"].astype(str) +
    "<br>Close: " + dfi["Close"].astype(str) +
    "<br>Volume: " + dfi[vol_col].astype(str)
)
has_signal = (dfi["Signal"] != "").fillna(False)
if has_signal.any():
    dfi.loc[has_signal, "hovertext"] = dfi.loc[has_signal, "hovertext"] + "<br>Signal: " + dfi.loc[has_signal, "Signal"].astype(str)

# ======================
# Plotting
# ======================
# Rows: 1-main, 2-volume (opt), 3-MACD (opt), 4-RSI (opt), 5-KDJ (opt)
rows = 1
row_map = {"volume": None, "macd": None, "rsi": None, "kdj": None}
if show_volume: rows += 1; row_map["volume"] = rows
if show_macd: rows += 1; row_map["macd"] = rows
if show_rsi: rows += 1; row_map["rsi"] = rows
if show_kdj: rows += 1; row_map["kdj"] = rows

specs = [[{"type": "xy"}]]
for r in range(2, rows+1):
    specs.append([{"type": "xy"}])

row_heights = []
# main bigger
row_heights.append(0.5)
# distribute rest
rest_rows = rows - 1
for _ in range(rest_rows):
    row_heights.append(0.5 / max(1, rest_rows))

fig = make_subplots(
    rows=rows, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    specs=specs,
    row_heights=row_heights
)

# Main candlestick
fig.add_trace(
    go.Candlestick(
        x=dfi.index,
        open=dfi["Open"],
        high=dfi["High"],
        low=dfi["Low"],
        close=dfi["Close"],
        name="K",
        hovertext=dfi["hovertext"],
        hoverinfo="text",
        showlegend=False
    ),
    row=1, col=1
)

# Overlays on main
if show_ma:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA5"], name="MA5", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA10"], name="MA10", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA20"], name="MA20", mode="lines"), row=1, col=1)

if show_ema:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["EMA12"], name="EMA12", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["EMA26"], name="EMA26", mode="lines"), row=1, col=1)

if show_boll:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["BOLL_M"], name="BOLL_M", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["BOLL_U"], name="BOLL_U", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["BOLL_L"], name="BOLL_L", mode="lines"), row=1, col=1)

# BUY/SELL markers
if show_signals and has_signal.any():
    buys = dfi.index[dfi["Signal"] == "BUY"]
    sells = dfi.index[dfi["Signal"] == "SELL"]
    fig.add_trace(
        go.Scatter(
            x=buys, y=dfi.loc[buys, "Low"],
            mode="markers", name="BUY",
            marker=dict(symbol="triangle-up", size=10),
            hoverinfo="skip"
        ), row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=sells, y=dfi.loc[sells, "High"],
            mode="markers", name="SELL",
            marker=dict(symbol="triangle-down", size=10),
            hoverinfo="skip"
        ), row=1, col=1
    )

# Subcharts
current_row = 1
if show_volume:
    current_row += 1
    fig.add_trace(
        go.Bar(x=dfi.index, y=dfi["Volume"], name="Volume", hoverinfo="skip"),
        row=current_row, col=1
    )

if show_macd:
    current_row += 1
    fig.add_trace(go.Bar(x=dfi.index, y=dfi["MACD_HIST"], name="MACD_HIST", hoverinfo="skip"), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD"], name="MACD", mode="lines", hoverinfo="skip"), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD_SIGNAL"], name="MACD_SIGNAL", mode="lines", hoverinfo="skip"), row=current_row, col=1)

if show_rsi:
    current_row += 1
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["RSI"], name="RSI(14)", mode="lines", hoverinfo="skip"), row=current_row, col=1)
    # 70/30 lines
    fig.add_trace(go.Scatter(x=[dfi.index.min(), dfi.index.max()], y=[70, 70], mode="lines", name="RSI70", hoverinfo="skip"), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=[dfi.index.min(), dfi.index.max()], y=[30, 30], mode="lines", name="RSI30", hoverinfo="skip"), row=current_row, col=1)

if show_kdj:
    current_row += 1
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["K"], name="K", mode="lines", hoverinfo="skip"), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["D"], name="D", mode="lines", hoverinfo="skip"), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["J"], name="J", mode="lines", hoverinfo="skip"), row=current_row, col=1)

# Layout (crosshair on main only)
fig.update_layout(
    hovermode="x unified",
    margin=dict(l=10, r=10, t=30, b=10),
    height=700,
    xaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor", showline=True),
    yaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor", showline=True),
)
# Turn off spikes for secondary axes (xaxis2+, yaxis2+)
for i in range(2, rows+1):
    fig.update_layout(
        **{
            f"xaxis{i}": dict(showspikes=False),
            f"yaxis{i}": dict(showspikes=False),
        }
    )

# ======================
# Render
# ======================
st.title("Quant Dashboard")
st.caption(f"Source: OKX Public | Symbol: {instId} | Interval: {interval} | Last update: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

st.plotly_chart(fig, use_container_width=True)

# ======================
# Backtest Summary (simple)
# ======================
st.subheader("Backtest Summary (Simple MA Cross)")
bt = dfi.copy()
bt["ret"] = bt["Close"].pct_change().fillna(0.0)
bt["pos"] = 0.0
bt.loc[bt["Signal"] == "BUY", "pos"] = 1.0
bt.loc[bt["Signal"] == "SELL", "pos"] = -1.0
bt["pos"] = bt["pos"].replace(0.0, np.nan).ffill().fillna(0.0)
# apply fee+slippage on position change
chg = bt["pos"].diff().abs().fillna(0.0)
cost = (fee + slippage) / 10000.0
bt["ret_net"] = bt["pos"].shift(1).fillna(0.0) * bt["ret"] - chg * cost
cum = (1 + bt["ret_net"]).cumprod()
ann = (cum.iloc[-1] ** (365*24*60 / max(1, len(bt)))) - 1 if len(bt) > 1 else 0.0
vol = bt["ret_net"].std() * math.sqrt(len(bt)) if len(bt) > 1 else 0.0
sharpe = (bt["ret_net"].mean() / (bt["ret_net"].std() + 1e-9)) * math.sqrt(365*24*60) if len(bt) > 1 else 0.0
mdd = (cum / cum.cummax() - 1).min()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Cumulative (net)", f"{cum.iloc[-1]:.4f}x")
col2.metric("Sharpe (approx)", f"{sharpe:.2f}")
col3.metric("Max Drawdown", f"{mdd:.2%}")
col4.metric("Annualized (approx)", f"{ann:.2%}")

# ======================
# Data Table & Download
# ======================
with st.expander("Show Data Table"):
    st.dataframe(dfi[["Open","High","Low","Close","Volume","MA5","MA10","MA20","EMA12","EMA26","BOLL_M","BOLL_U","BOLL_L","MACD","MACD_SIGNAL","MACD_HIST","RSI","K","D","J","Signal"]])

csv = dfi.to_csv(index=True).encode("utf-8")
st.download_button(
    label="Download CSV",
    data=csv,
    file_name=f"{instId.replace('-','_')}_{interval}_data.csv",
    mime="text/csv",
)
