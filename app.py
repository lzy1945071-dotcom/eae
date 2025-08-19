# app.py — Legend Quant Terminal Elite v3 FIX11
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import ta
from io import StringIO
from datetime import timedelta

st.set_page_config(page_title="Legend Quant Terminal Elite v3 FIX11", layout="wide")
st.title("💎 Legend Quant Terminal Elite v3 FIX11")

# ========================= Sidebar: ① 数据来源与标的 =========================
st.sidebar.header("① 数据来源与标的")
source = st.sidebar.selectbox(
    "数据来源",
    [
        "OKX 公共行情（免API）",
        "CoinGecko（免API）",
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

# 标的与周期
if source in ["CoinGecko（免API）", "TokenInsight API 模式（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（CoinGecko coin_id）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标（可多选，默认留空）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], default=[])
    interval = st.sidebar.selectbox("K线周期（映射）", ["1d","1w","1M","max"], index=0)
elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（OKX InstId）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标（可多选，默认留空）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1m","3m","5m","15m","30m","1H","2H","4H","6H","12H","1D","1W","1M"], index=10)
else:
    symbol = st.sidebar.selectbox("个标（美股/A股）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], index=0)
    combo_symbols = st.sidebar.multiselect("组合标（可多选，默认留空）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1d","1wk","1mo"], index=0)

# ========================= Sidebar: ③ 指标与参数 =========================
st.sidebar.header("③ 指标与参数（顶级交易员常用）")
use_ma = st.sidebar.checkbox("MA（简单均线）", True)
ma_periods_text = st.sidebar.text_input("MA 周期（逗号分隔）", value="20,50")
use_ema = st.sidebar.checkbox("EMA（指数均线）", True)
ema_periods_text = st.sidebar.text_input("EMA 周期（逗号分隔）", value="200")
use_boll = st.sidebar.checkbox("布林带（BOLL）", True)
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
**加密货币**：MACD 12/26/9；RSI 14；BOLL 20 ± 2σ；MA 20/50；EMA 200  
**美股**：MACD 12/26/9；RSI 14；MA 50/200  
**A股**：MACD 10/30/9；RSI 14；MA 5/10/30
''')

# ========================= Sidebar: ⑤ 风控参数 =========================
st.sidebar.header("⑤ 风控参数")
account_value = st.sidebar.number_input("账户总资金", min_value=1.0, value=100000.0, step=1.0)
risk_pct = st.sidebar.slider("单笔风险（%）", 0.1, 2.0, 0.5, 0.1)
leverage = st.sidebar.slider("杠杆倍数", 1, 10, 1, 1)
daily_loss_limit = st.sidebar.number_input("每日亏损阈值（%）", min_value=0.5, value=2.0, step=0.5)
weekly_loss_limit = st.sidebar.number_input("每周亏损阈值（%）", min_value=1.0, value=5.0, step=0.5)

# ========================= Sidebar: 刷新设置 =========================
st.sidebar.header("⑥ 刷新设置")
refresh_button = st.sidebar.button("🔄 手动刷新K线")
refresh_sec = st.sidebar.number_input("自动刷新间隔（秒）", min_value=0, value=0, step=1)

# ========================= 数据加载函数 =========================
def _cg_days_from_interval(sel: str) -> str:
    if sel.startswith("1d"): return "180"
    if sel.startswith("1w"): return "365"
    if sel.startswith("1M"): return "365"
    if sel.startswith("max"): return "max"
    return "180"

@st.cache_data(ttl=900)
def load_coingecko_ohlc_robust(coin_id: str, interval_sel: str):
    days = _cg_days_from_interval(interval_sel)
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        r = requests.get(url, params={"vs_currency": "usd", "days": days}, timeout=20)
        if r.status_code == 200:
            arr = r.json()
            if isinstance(arr, list) and len(arr) > 0:
                rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in arr]
                return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close"]).set_index("Date")
    except Exception: pass
    return pd.DataFrame()

@st.cache_data(ttl=900)
def load_okx_public(instId: str, bar: str, base_url: str = ""):
    url = (base_url.rstrip('/') if base_url else "https://www.okx.com") + "/api/v5/market/candles"
    params = {"instId": instId, "bar": bar, "limit": "1000"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data: return pd.DataFrame()
    rows = []
    for a in reversed(data):
        ts = int(a[0]); o=float(a[1]); h=float(a[2]); l=float(a[3]); c=float(a[4]); v=float(a[5])
        rows.append((pd.to_datetime(ts, unit="ms"), o,h,l,c,v))
    return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")

@st.cache_data(ttl=900)
def load_yf(symbol: str, interval_sel: str):
    interval_map = {"1d":"1d","1wk":"1wk","1mo":"1mo"}
    interval = interval_map.get(interval_sel, "1d")
    df = yf.download(symbol, period="5y", interval=interval, progress=False, auto_adjust=False)
    if not df.empty:
        df = df[["Open","High","Low","Close","Volume"]].dropna()
    return df

def load_router(source, symbol, interval_sel, api_base=""):
    if source == "CoinGecko（免API）":
        return load_coingecko_ohlc_robust(symbol, interval_sel)
    elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
        return load_okx_public(symbol, interval_sel, base_url=api_base if "OKX API" in source else "")
    else:
        return load_yf(symbol, interval_sel)

# ========================= 获取数据并计算指标 =========================
df = load_router(source, symbol, interval, api_base)

if df.empty or not set(["Open","High","Low","Close"]).issubset(df.columns):
    st.error("数据为空或字段缺失，请更换数据源/周期")
    st.stop()

def parse_int_list(text):
    try: return [int(x.strip()) for x in text.split(",") if x.strip()]
    except Exception: return []

def add_indicators(df):
    out = df.copy()
    close, high, low = out["Close"], out["High"], out["Low"]
    if "Volume" not in out.columns: out["Volume"] = np.nan
    if use_ma:
        for p in parse_int_list(ma_periods_text): out[f"MA{p}"] = close.rolling(p).mean()
    if use_ema:
        for p in parse_int_list(ema_periods_text): out[f"EMA{p}"] = ta.trend.EMAIndicator(close, window=p).ema_indicator()
    if use_boll:
        boll = ta.volatility.BollingerBands(close, window=int(boll_window), window_dev=float(boll_std))
        out["BOLL_M"], out["BOLL_U"], out["BOLL_L"] = boll.bollinger_mavg(), boll.bollinger_hband(), boll.bollinger_lband()
    if use_macd:
        macd_ind = ta.trend.MACD(close, window_slow=int(macd_slow), window_fast=int(macd_fast), window_sign=int(macd_sig))
        out["MACD"], out["MACD_signal"], out["MACD_hist"] = macd_ind.macd(), macd_ind.macd_signal(), macd_ind.macd_diff()
    if use_rsi: out["RSI"] = ta.momentum.RSIIndicator(close, window=int(rsi_window)).rsi()
    if use_atr: out["ATR"] = ta.volatility.AverageTrueRange(high, low, close, window=int(atr_window)).average_true_range()
    return out

dfi = add_indicators(df).dropna(how="all")

# ========================= TradingView 风格图表 =========================
st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=dfi.index, open=dfi["Open"], high=dfi["High"], low=dfi["Low"], close=dfi["Close"], name="K线"))
# MA/EMA/BOLL 绘制
if use_ma:
    for p in parse_int_list(ma_periods_text):
        col = f"MA{p}"
        if col in dfi.columns: fig.add_trace(go.Scatter(x=dfi.index, y=dfi[col], mode="lines", name=col))
if use_ema:
    for p in parse_int_list(ema_periods_text):
        col = f"EMA{p}"
        if col in dfi.columns: fig.add_trace(go.Scatter(x=dfi.index, y=dfi[col], mode="lines", name=col))
if use_boll:
    for col,nm in [("BOLL_U","BOLL 上轨"),("BOLL_M","BOLL 中轨"),("BOLL_L","BOLL 下轨")]:
        if col in dfi.columns: fig.add_trace(go.Scatter(x=dfi.index, y=dfi[col], mode="lines", name=nm))

st.plotly_chart(fig, use_container_width=True)

# ========================= 策略组合 =========================
st.markdown("---")
st.subheader("🧩 策略组合构件")

strategy_options = [
    "MA 多头（金叉做多）", "MA 空头（死叉做空）",
    "MACD 金叉做多", "MACD 死叉做空",
    "RSI 超卖做多", "RSI 超买做空",
    "BOLL 下轨反弹做多", "BOLL 上轨回落做空"
]
selected_strategies = st.multiselect("选择组合策略（可多选）", strategy_options, default=["MA 多头（金叉做多）","MACD 金叉做多"])

def backtest_with_details(df, strategies):
    df = df.copy().dropna()
    sig = np.zeros(len(df))
    for strat in strategies:
        if strat=="MA 多头（金叉做多）" and "MA20" in df.columns and "MA50" in df.columns:
            sig = np.where(df["MA20"]>df["MA50"], 1, sig)
        if strat=="MA 空头（死叉做空）" and "MA20" in df.columns and "MA50" in df.columns:
            sig = np.where(df["MA20"]<df["MA50"], -1, sig)
        if strat=="MACD 金叉做多" and "MACD" in df.columns:
            sig = np.where(df["MACD"]>df["MACD_signal"], 1, sig)
        if strat=="MACD 死叉做空" and "MACD" in df.columns:
            sig = np.where(df["MACD"]<df["MACD_signal"], -1, sig)
        if strat=="RSI 超卖做多" and "RSI" in df.columns:
            sig = np.where(df["RSI"]<30, 1, sig)
        if strat=="RSI 超买做空" and "RSI" in df.columns:
            sig = np.where(df["RSI"]>70, -1, sig)
        if strat=="BOLL 下轨反弹做多" and "BOLL_L" in df.columns:
            sig = np.where(df["Close"]<=df["BOLL_L"], 1, sig)
        if strat=="BOLL 上轨回落做空" and "BOLL_U" in df.columns:
            sig = np.where(df["Close"]>=df["BOLL_U"], -1, sig)

    df["sig"] = sig
    df["ret"] = df["Close"].pct_change().fillna(0)
    pos = pd.Series(sig, index=df.index).replace(0, np.nan).ffill().fillna(0)
    strat_ret = pos * df["ret"]
    equity = (1+strat_ret).cumprod()

    # 交易明细
    trades = []
    entry_side, entry_price, entry_time = None,None,None
    for i in range(len(df)):
        if pos.iloc[i]!=0 and entry_side is None:
            entry_side = pos.iloc[i]
            entry_price = df["Close"].iloc[i]
            entry_time = df.index[i]
        elif pos.iloc[i]==0 and entry_side is not None:
            exit_price = df["Close"].iloc[i]
            exit_time = df.index[i]
            pnl = (exit_price/entry_price-1)*entry_side
            trades.append([entry_time, exit_time, "多" if entry_side>0 else "空", entry_price, exit_price, pnl, (exit_time-entry_time).days])
            entry_side=None
    trades_df = pd.DataFrame(trades, columns=["进场时间","出场时间","方向","进场价","出场价","收益率","持有天数"])
    return equity, trades_df

equity, trades_df = backtest_with_details(dfi, selected_strategies)

st.subheader("📋 交易明细")
if not trades_df.empty:
    st.dataframe(trades_df, use_container_width=True)
    csv = trades_df.to_csv(index=False)
    st.download_button("下载交易明细 CSV", csv, file_name="trades.csv", mime="text/csv")
else:
    st.info("暂无交易记录。")
