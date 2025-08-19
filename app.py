import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Legend Quant Terminal", layout="wide")

# ---------------------
# 数据获取函数
# ---------------------
def get_coingecko_ohlc(symbol="bitcoin", vs_currency="usd", days=30):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/ohlc?vs_currency={vs_currency}&days={days}"
    r = requests.get(url)
    if r.status_code == 200 and len(r.json()) > 0:
        df = pd.DataFrame(r.json(), columns=["time","open","high","low","close"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return df

    # fallback: market_chart
    url2 = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart?vs_currency={vs_currency}&days={days}"
    r2 = requests.get(url2)
    if r2.status_code == 200:
        data = r2.json()
        prices = data.get("prices", [])
        if not prices:
            return pd.DataFrame()
        df = pd.DataFrame(prices, columns=["time","price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df.set_index("time").resample("1D").agg({"price":["first","max","min","last"]})
        df.columns = ["open","high","low","close"]
        df = df.reset_index()
        return df
    return pd.DataFrame()

def get_okx_kline(symbol="BTC-USDT", interval="1D", limit=200):
    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={interval}&limit={limit}"
    r = requests.get(url)
    if r.status_code != 200:
        return pd.DataFrame()
    data = r.json().get("data", [])
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=["ts","open","high","low","close","vol","volCcy","volCcyQuote","confirm"])
    df["time"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
    df = df.sort_values("time")
    df = df[["time","open","high","low","close","vol"]].astype({"open":float,"high":float,"low":float,"close":float,"vol":float})
    return df

# ---------------------
# 指标函数
# ---------------------
def add_ma(df, period=20):
    df[f"MA{period}"] = df["close"].rolling(period).mean()
    return df

def add_rsi(df, period=14):
    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(period).mean()
    ma_down = down.rolling(period).mean()
    rs = ma_up / ma_down
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def add_bollinger(df, period=20, num_std=2):
    df["MA"] = df["close"].rolling(period).mean()
    df["STD"] = df["close"].rolling(period).std()
    df["Upper"] = df["MA"] + num_std * df["STD"]
    df["Lower"] = df["MA"] - num_std * df["STD"]
    return df

def add_macd(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df

# ---------------------
# 实时策略建议
# ---------------------
def strategy_suggestion(df):
    if df.empty:
        return "无数据", {}
    current = df["close"].iloc[-1]
    low, high = df["low"].min(), df["high"].max()
    pct = (current - low) / (high - low + 1e-9) * 100

    recent = df.tail(20)
    support = recent["low"].min()
    resistance = recent["high"].max()

    if pct < 30:
        advice = "价格处于低位区间，适合逐步建仓。"
    elif pct > 70:
        advice = "价格处于高位区间，需谨慎，适合部分止盈。"
    else:
        advice = "价格处于中位区间，可持有观察或轻仓操作。"

    info = {
        "当前价": round(current, 2),
        "区间低位": round(low, 2),
        "区间高位": round(high, 2),
        "历史区间百分位": f"{pct:.1f}%",
        "支撑位": round(support, 2),
        "压力位": round(resistance, 2)
    }
    return advice, info

# ---------------------
# 绘图 TradingView 风格
# ---------------------
def make_tradingview_chart(df, ma_period, boll_period, macd_params):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.02, row_heights=[0.55,0.2,0.25])

    # --- 主K线图
    fig.add_trace(go.Candlestick(
        x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线", increasing_line_color="red", decreasing_line_color="green"
    ), row=1, col=1)

    if ma_period:
        fig.add_trace(go.Scatter(x=df["time"], y=df[f"MA{ma_period}"], mode="lines", name=f"MA{ma_period}"), row=1, col=1)

    if boll_period:
        fig.add_trace(go.Scatter(x=df["time"], y=df["Upper"], line=dict(color="gray", dash="dot"), name="上轨"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["Lower"], line=dict(color="gray", dash="dot"), name="下轨"), row=1, col=1)

    # --- 成交量
    if "vol" in df.columns:
        colors = ["red" if row.close > row.open else "green" for row in df.itertuples()]
        fig.add_trace(go.Bar(x=df["time"], y=df["vol"], marker_color=colors, name="成交量"), row=2, col=1)

    # --- MACD
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], line=dict(color="blue"), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["Signal"], line=dict(color="orange"), name="Signal"), row=3, col=1)
        fig.add_trace(go.Bar(x=df["time"], y=df["Hist"], marker_color=np.where(df["Hist"]>=0,"red","green"), name="Hist"), row=3, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, height=900, 
                      showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# ---------------------
# UI
# ---------------------
st.sidebar.title("⚙️ 功能面板")

# 数据源选择
data_source = st.sidebar.selectbox("功能① 数据源", [
    "CoinGecko (免API)",
    "TokenInsight (免API)",
    "OKX API",
    "TokenInsight API"
])

api_url = None
if data_source in ["OKX API","TokenInsight API"]:
    api_url = st.sidebar.text_input("请输入 API 地址")

# 个标/组合标
single_symbol = st.sidebar.text_input("功能② 个标", value="BTC")
portfolio_symbol = st.sidebar.text_input("功能② 组合标", value="")

# 周期
interval = st.sidebar.selectbox("功能③ 周期", [
    "1m","15m","1h","4h","1d","1w","1M"
], index=4)

# 技术指标选择
indicators = st.sidebar.multiselect("功能③ 技术指标", [
    "MA","RSI","Bollinger","MACD"
])

if "MA" in indicators:
    ma_period = st.sidebar.number_input("MA 周期", min_value=5, max_value=200, value=20)
else:
    ma_period = None

if "RSI" in indicators:
    rsi_period = st.sidebar.number_input("RSI 周期", min_value=5, max_value=50, value=14)
else:
    rsi_period = None

if "Bollinger" in indicators:
    boll_period = st.sidebar.number_input("Bollinger 周期", min_value=10, max_value=50, value=20)
    boll_std = st.sidebar.number_input("Bollinger STD 倍数", min_value=1, max_value=4, value=2)
else:
    boll_period = None
    boll_std = None

if "MACD" in indicators:
    macd_fast = st.sidebar.number_input("MACD 快线", min_value=5, max_value=30, value=12)
    macd_slow = st.sidebar.number_input("MACD 慢线", min_value=10, max_value=60, value=26)
    macd_signal = st.sidebar.number_input("MACD 信号线", min_value=5, max_value=20, value=9)
    macd_params = (macd_fast, macd_slow, macd_signal)
else:
    macd_params = None

st.title("📊 Legend Quant Terminal")

if single_symbol:
    st.subheader(f"个标行情 - {single_symbol}")

    if data_source.startswith("CoinGecko"):
        df = get_coingecko_ohlc(symbol=single_symbol.lower(), days=90)
    elif data_source.startswith("OKX"):
        df = get_okx_kline(symbol=f"{single_symbol}-USDT", interval=interval)
    else:
        df = get_coingecko_ohlc(symbol=single_symbol.lower(), days=90)

    if not df.empty:
        if ma_period:
            df = add_ma(df, ma_period)
        if rsi_period:
            df = add_rsi(df, rsi_period)
        if boll_period:
            df = add_bollinger(df, boll_period, boll_std)
        if macd_params:
            df = add_macd(df, *macd_params)

        fig = make_tradingview_chart(df, ma_period, boll_period, macd_params)
        st.plotly_chart(fig, use_container_width=True)

        # RSI 独立展示
        if rsi_period:
            st.subheader("RSI 指标")
            st.line_chart(df.set_index("time")["RSI"])

        # 实时策略卡片
        st.subheader("📌 实时策略建议")
        advice, info = strategy_suggestion(df)
        st.info(advice)
        st.json(info)
    else:
        st.warning("未能获取数据")
