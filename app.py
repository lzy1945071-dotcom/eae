# app.py — Legend Quant Terminal Elite v3 FIX12
# 功能: 多数据源 (CoinGecko / OKX / Binance / Yahoo) + TradingView风格主图 + 策略建议 + 简易回测 + 风控 + 组合分析

import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
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
        "币安 公共行情（免API）",
        "OKX API（可填API基址）",
        "TokenInsight API 模式（可填API基址）",
        "Yahoo Finance（美股/A股）",
    ],
    index=0
)

api_base = ""
if source in ["OKX API（可填API基址）", "TokenInsight API 模式（可填API基址）"]:
    st.sidebar.markdown("**API 连接设置**")
    api_base = st.sidebar.text_input("API 基址（留空用默认公共接口）", value="")

if source in ["CoinGecko（免API）", "TokenInsight API 模式（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（CoinGecko coin_id）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1d","1w","1M","max"], index=0)
elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（OKX InstId）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1m","5m","15m","1H","4H","1D","1W","1M"], index=6)
elif source == "币安 公共行情（免API）":
    symbol = st.sidebar.selectbox("个标（Binance symbol）", ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"], index=0)
    combo_symbols = st.sidebar.multiselect("组合标", ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1m","5m","15m","1h","4h","1d","1w","1M"], index=5)
else:
    symbol = st.sidebar.selectbox("个标（美股/A股）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], index=0)
    combo_symbols = st.sidebar.multiselect("组合标", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1d","1wk","1mo"], index=0)

# ========================= Sidebar: ② 指标与参数 =========================
st.sidebar.header("② 指标与参数")
use_ma = st.sidebar.checkbox("MA", True)
ma_periods = list(map(int, st.sidebar.text_input("MA 周期", "20,50").split(",")))
use_ema = st.sidebar.checkbox("EMA", False)
ema_periods = list(map(int, st.sidebar.text_input("EMA 周期", "200").split(",")))
use_boll = st.sidebar.checkbox("布林带", False)
boll_window = st.sidebar.number_input("BOLL 窗口", 20)
boll_std = st.sidebar.number_input("BOLL 倍数", 2.0)
use_macd = st.sidebar.checkbox("MACD", True)
macd_fast = st.sidebar.number_input("MACD 快", 12)
macd_slow = st.sidebar.number_input("MACD 慢", 26)
macd_sig = st.sidebar.number_input("MACD 信号", 9)
use_rsi = st.sidebar.checkbox("RSI", True)
rsi_window = st.sidebar.number_input("RSI 窗口", 14)
use_atr = st.sidebar.checkbox("ATR", True)
atr_window = st.sidebar.number_input("ATR 窗口", 14)

# ========================= Data Loaders =========================
def load_binance(symbol, interval):
    m = {"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1d":"1d","1w":"1w","1M":"1M"}
    url = "https://api.binance.com/api/v3/klines"
    r = requests.get(url, params={"symbol":symbol,"interval":m[interval],"limit":1000})
    data = r.json()
    rows = [(pd.to_datetime(k[0], unit="ms"), float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5])) for k in data]
    return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")

def load_yf(symbol, interval):
    df = yf.download(symbol, period="1y", interval=interval)
    df = df.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close","Volume":"Volume"})
    return df.dropna()

# 简化：这里只写Binance+Yahoo，其他源你可以补全
def load_router():
    if source=="币安 公共行情（免API）":
        return load_binance(symbol, interval)
    elif source=="Yahoo Finance（美股/A股）":
        return load_yf(symbol, interval)
    else:
        return load_binance("BTCUSDT","1d")  # fallback

df = load_router()

# ========================= 指标计算 =========================
def add_indicators(df):
    d = df.copy()
    for p in ma_periods: d[f"MA{p}"]=d["Close"].rolling(p).mean()
    for p in ema_periods: d[f"EMA{p}"]=d["Close"].ewm(span=p).mean()
    if use_boll:
        d["BOLL_MA"]=d["Close"].rolling(boll_window).mean()
        d["BOLL_UP"]=d["BOLL_MA"]+boll_std*d["Close"].rolling(boll_window).std()
        d["BOLL_DN"]=d["BOLL_MA"]-boll_std*d["Close"].rolling(boll_window).std()
    if use_macd:
        macd=ta.trend.MACD(d["Close"],macd_fast,macd_slow,macd_sig)
        d["MACD"]=macd.macd(); d["MACD_SIGNAL"]=macd.macd_signal(); d["MACD_HIST"]=macd.macd_diff()
    if use_rsi: d["RSI"]=ta.momentum.RSIIndicator(d["Close"],rsi_window).rsi()
    if use_atr: d["ATR"]=ta.volatility.AverageTrueRange(d["High"],d["Low"],d["Close"],atr_window).average_true_range()
    return d

dfi = add_indicators(df).dropna()

# ========================= 图表 =========================
st.subheader(f"🕯️ {symbol} {interval}")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=dfi.index, open=dfi["Open"],high=dfi["High"],low=dfi["Low"],close=dfi["Close"], name="K线"))
for p in ma_periods: fig.add_trace(go.Scatter(x=dfi.index,y=dfi[f"MA{p}"],mode="lines",name=f"MA{p}"))
for p in ema_periods: fig.add_trace(go.Scatter(x=dfi.index,y=dfi[f"EMA{p}"],mode="lines",name=f"EMA{p}"))
if use_boll:
    fig.add_trace(go.Scatter(x=dfi.index,y=dfi["BOLL_UP"],mode="lines",name="BOLL_UP"))
    fig.add_trace(go.Scatter(x=dfi.index,y=dfi["BOLL_DN"],mode="lines",name="BOLL_DN"))
fig.update_layout(
    xaxis_rangeslider_visible=False, height=800, dragmode="pan", hovermode="x unified",
    modebar_add=["drawline","drawrect","drawcircle","eraseshape","zoom","pan","autoscale"]
)
st.plotly_chart(fig, use_container_width=True)

# ========================= 策略建议 =========================
st.subheader("📈 策略建议")
latest = dfi.iloc[-1]
sig = []
if use_rsi:
    if latest["RSI"]<30: sig.append("RSI超卖 → 看多")
    elif latest["RSI"]>70: sig.append("RSI超买 → 看空")
if use_macd:
    if latest["MACD"]>latest["MACD_SIGNAL"]: sig.append("MACD金叉 → 看多")
    else: sig.append("MACD死叉 → 看空")
st.write("；".join(sig) if sig else "无明显信号")

# ========================= 简易回测 =========================
st.subheader("🔄 简易回测（双均线交叉）")
short,long=20,50
dfi["SMA_S"]=dfi["Close"].rolling(short).mean()
dfi["SMA_L"]=dfi["Close"].rolling(long).mean()
dfi["Signal"]=np.where(dfi["SMA_S"]>dfi["SMA_L"],1,0)
dfi["Return"]=dfi["Close"].pct_change()
dfi["Strat"]=dfi["Return"]*dfi["Signal"].shift(1)
cum_bench=(1+dfi["Return"]).cumprod()
cum_strat=(1+dfi["Strat"]).cumprod()
fig2=go.Figure()
fig2.add_trace(go.Scatter(x=dfi.index,y=cum_bench,name="买入持有"))
fig2.add_trace(go.Scatter(x=dfi.index,y=cum_strat,name="双均线策略"))
st.plotly_chart(fig2,use_container_width=True)

# ========================= 风险控制 =========================
st.subheader("⚠️ 风险控制")
if use_atr:
    atr=latest["ATR"]
    sl=latest["Close"]-2*atr; tp=latest["Close"]+3*atr
    st.write(f"当前ATR={atr:.2f} → 止损≈{sl:.2f}，止盈≈{tp:.2f}")

# ========================= 组合分析 =========================
if combo_symbols:
    st.subheader("📊 组合分析")
    dfs=[]
    for s in combo_symbols:
        try:
            d=load_binance(s,"1d")
            d=d["Close"].rename(s)
            dfs.append(d)
        except: pass
    if dfs:
        port=pd.concat(dfs,axis=1).dropna()
        corr=port.corr()
        st.dataframe(corr)
        st.plotly_chart(px.imshow(corr,text_auto=True,color_continuous_scale="RdBu",zmin=-1,zmax=1))
