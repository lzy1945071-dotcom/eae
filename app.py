# app.py — Legend Quant Terminal Elite v3 FIX12
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
import ta

st.set_page_config(page_title="Legend Quant Terminal Elite v3 FIX12", layout="wide")
st.title("💎 Legend Quant Terminal Elite v3 FIX12")

# ========================= Sidebar: ① 数据来源与标的 =========================
st.sidebar.header("① 数据来源与标的")
source = st.sidebar.selectbox(
    "数据来源",
    [
        "CoinGecko（免API）",
        "OKX 公共行情（免API）",
        "Binance 公共行情（免API）",
        "OKX API（可填API基址）",
        "TokenInsight API 模式（可填API基址）",
        "Yahoo Finance（美股/A股）",
    ],
    index=0
)

api_base = ""
api_key = ""
api_secret = ""
api_passphrase = ""

if source in ["OKX API（可填API基址）", "TokenInsight API 模式（可填API基址）"]:
    st.sidebar.markdown("**API 连接设置**")
    api_base = st.sidebar.text_input("API 基址（留空用默认公共接口）", value="")
    if source == "OKX API（可填API基址）":
        with st.sidebar.expander("（可选）OKX API 认证信息"):
            api_key = st.text_input("OKX-API-KEY", value="", type="password")
            api_secret = st.text_input("OKX-API-SECRET", value="", type="password")
            api_passphrase = st.text_input("OKX-API-PASSPHRASE", value="", type="password")

# 标的选择
if source in ["CoinGecko（免API）", "TokenInsight API 模式（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（CoinGecko coin_id）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标（可多选，默认留空）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], default=[])
    interval = st.sidebar.selectbox("K线周期（映射）", ["1d","1w","1M","max"], index=0)
elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（OKX InstId）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1m","3m","5m","15m","30m","1H","2H","4H","6H","12H","1D","1W","1M"], index=10)
elif source == "Binance 公共行情（免API）":
    symbol = st.sidebar.selectbox("个标（Binance Symbol）", ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"], index=0)
    combo_symbols = st.sidebar.multiselect("组合标", ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1m","3m","5m","15m","30m","1h","2h","4h","6h","12h","1d","1w","1M"], index=11)
else:
    symbol = st.sidebar.selectbox("个标（美股/A股）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], index=0)
    combo_symbols = st.sidebar.multiselect("组合标", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1d","1wk","1mo"], index=0)

# ========================= Sidebar: ③ 指标与参数 =========================
st.sidebar.header("③ 指标与参数（顶级交易员常用）")
use_ma = st.sidebar.checkbox("MA（简单均线）", True)
ma_periods_text = st.sidebar.text_input("MA 周期（逗号分隔）", value="20,50")
use_ema = st.sidebar.checkbox("EMA（指数均线）", False)
ema_periods_text = st.sidebar.text_input("EMA 周期（逗号分隔）", value="200")
use_boll = st.sidebar.checkbox("布林带（BOLL）", False)
boll_window = st.sidebar.number_input("BOLL 窗口", min_value=5, value=20, step=1)
boll_std = st.sidebar.number_input("BOLL 标准差倍数", min_value=1.0, value=2.0, step=0.5)
use_macd = st.sidebar.checkbox("MACD（副图）", True)
macd_fast = st.sidebar.number_input("MACD 快线", min_value=2, value=12, step=1)
macd_slow = st.sidebar.number_input("MACD 慢线", min_value=5, value=26, step=1)
macd_sig = st.sidebar.number_input("MACD 信号线", min_value=2, value=9, step=1)
use_rsi = st.sidebar.checkbox("RSI（副图）", True)
rsi_window = st.sidebar.number_input("RSI 窗口", min_value=5, value=14, step=1)
use_atr = st.sidebar.checkbox("ATR（用于风险/止盈止损）", True)
atr_window = st.sidebar.number_input("ATR 窗口", min_value=5, value=14, step=1)

# ========================= Sidebar: ④ 参数推荐 =========================
st.sidebar.header("④ 参数推荐（说明）")
st.sidebar.markdown('''
**加密货币**：MACD **12/26/9**；RSI **14**；BOLL **20 ± 2σ**；MA **20/50**；EMA **200**  
**美股**：MACD **12/26/9**；RSI **14**；MA **50/200**  
**A股**：MACD **10/30/9**；RSI **14**；MA **5/10/30**
''')

# ========================= Sidebar: ⑤ 风控参数 =========================
st.sidebar.header("⑤ 风控参数")
account_value = st.sidebar.number_input("账户总资金", min_value=1.0, value=1000.0, step=5.0)
risk_pct = st.sidebar.slider("单笔风险（%）", 0.1, 2.0, 0.5, 0.1)
leverage = st.sidebar.slider("杠杆倍数", 1, 10, 1, 1)
daily_loss_limit = st.sidebar.number_input("每日亏损阈值（%）", min_value=0.5, value=2.0, step=0.5)
weekly_loss_limit = st.sidebar.number_input("每周亏损阈值（%）", min_value=1.0, value=5.0, step=0.5)

# ========================= Data Loaders =========================
@st.cache_data(ttl=900)
def load_coingecko_ohlc_robust(symbol: str, interval: str):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/ohlc"
    params = {"vs_currency": "usd", "days": "max"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data: return pd.DataFrame()
    rows = [(pd.to_datetime(x[0], unit="ms"), x[1],x[2],x[3],x[4],0.0) for x in data]
    return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")

@st.cache_data(ttl=900)
def load_tokeninsight_ohlc(api_base: str, symbol: str, interval: str):
    if not api_base:
        return pd.DataFrame()
    url = f"{api_base}/ohlc?symbol={symbol}&interval={interval}"
    r = requests.get(url, timeout=20)
    if r.status_code != 200: return pd.DataFrame()
    data = r.json().get("data", [])
    if not data: return pd.DataFrame()
    rows = [(pd.to_datetime(d["ts"], unit="ms"), d["o"],d["h"],d["l"],d["c"],d.get("v",0)) for d in data]
    return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")

@st.cache_data(ttl=900)
def load_okx_public(symbol: str, interval: str, base_url: str=""):
    base = base_url if base_url else "https://www.okx.com"
    url = f"{base}/api/v5/market/candles?instId={symbol}&bar={interval}&limit=1000"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data: return pd.DataFrame()
    rows = []
    for k in data:
        ts = int(k[0])
        o,h,l,c,v = map(float, k[1:6])
        rows.append((pd.to_datetime(ts, unit="ms"), o,h,l,c,v))
    return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")

@st.cache_data(ttl=900)
def load_binance_public(symbol: str, interval: str):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": 1000}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data: return pd.DataFrame()
    rows = []
    for k in data:
        ts = int(k[0]); o,h,l,c,v = map(float, k[1:6])
        rows.append((pd.to_datetime(ts, unit="ms"), o,h,l,c,v))
    return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")

@st.cache_data(ttl=900)
def load_yf(symbol: str, interval: str):
    df = yf.download(symbol, period="max", interval=interval)
    if df.empty: return pd.DataFrame()
    return df.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close","Volume":"Volume"})

def load_router(source, symbol, interval_sel, api_base=""):
    if source == "CoinGecko（免API）":
        return load_coingecko_ohlc_robust(symbol, interval_sel)
    elif source == "TokenInsight API 模式（可填API基址）":
        return load_tokeninsight_ohlc(api_base, symbol, interval_sel)
    elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
        base = api_base if source == "OKX API（可填API基址）" else ""
        return load_okx_public(symbol, interval_sel, base_url=base)
    elif source == "Binance 公共行情（免API）":
        return load_binance_public(symbol, interval_sel)
    else:
        return load_yf(symbol, interval_sel)

df = load_router(source, symbol, interval, api_base)

# ========================= TradingView 风格图表 =========================
if not df.empty:
    st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="K线"
    ))

    # 成交量
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", yaxis="y2", opacity=0.3))

    # MA
    if use_ma:
        for p in [int(x) for x in ma_periods_text.split(",") if x.strip().isdigit()]:
            df[f"MA{p}"] = df["Close"].rolling(p).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df[f"MA{p}"], mode="lines", name=f"MA{p}"))

    # EMA
    if use_ema:
        for p in [int(x) for x in ema_periods_text.split(",") if x.strip().isdigit()]:
            df[f"EMA{p}"] = df["Close"].ewm(span=p).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df[f"EMA{p}"], mode="lines", name=f"EMA{p}"))

    # BOLL
    if use_boll:
        ma = df["Close"].rolling(boll_window).mean()
        std = df["Close"].rolling(boll_window).std()
        up, down = ma + boll_std*std, ma - boll_std*std
        fig.add_trace(go.Scatter(x=df.index, y=up, mode="lines", name="BOLL上轨"))
        fig.add_trace(go.Scatter(x=df.index, y=ma, mode="lines", name="BOLL中轨"))
        fig.add_trace(go.Scatter(x=df.index, y=down, mode="lines", name="BOLL下轨"))

    # MACD
    if use_macd:
        macd = ta.trend.MACD(df["Close"], macd_fast, macd_slow, macd_sig)
        fig.add_trace(go.Bar(x=df.index, y=macd.macd_diff(), name="MACD Histogram", yaxis="y3"))
        fig.add_trace(go.Scatter(x=df.index, y=macd.macd(), mode="lines", name="MACD", yaxis="y3"))
        fig.add_trace(go.Scatter(x=df.index, y=macd.macd_signal(), mode="lines", name="Signal", yaxis="y3"))

    # RSI
    if use_rsi:
        rsi = ta.momentum.RSIIndicator(df["Close"], rsi_window).rsi()
        fig.add_trace(go.Scatter(x=df.index, y=rsi, mode="lines", name="RSI", yaxis="y4"))

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=900,
        hovermode="x unified",
        dragmode="pan",
        newshape=dict(line_color="cyan"),
        yaxis=dict(domain=[0.58, 1.0], title="价格", fixedrange=False),
        yaxis2=dict(domain=[0.45, 0.57], title="成交量", showgrid=False),
        yaxis3=dict(domain=[0.25, 0.44], title="MACD", showgrid=False),
        yaxis4=dict(domain=[0.0, 0.24], title="RSI", showgrid=False, range=[0,100]),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("❌ 数据加载失败，请检查数据源/参数")
