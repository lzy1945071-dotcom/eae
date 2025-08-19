import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Legend Quant Terminal", layout="wide")

# ---------------------
# 数据获取函数
# ---------------------
def get_coingecko_ohlc(symbol="bitcoin", vs_currency="usd", days=30):
    """尝试获取 CoinGecko K线数据，如果 /ohlc 失败则回退到 market_chart"""
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/ohlc?vs_currency={vs_currency}&days={days}"
    r = requests.get(url)
    if r.status_code == 200 and len(r.json()) > 0:
        df = pd.DataFrame(r.json(), columns=["time","open","high","low","close"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return df

    # fallback
    url2 = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart?vs_currency={vs_currency}&days={days}"
    r2 = requests.get(url2)
    if r2.status_code == 200:
        data = r2.json()
        prices = data.get("prices", [])
        if not prices:
            return pd.DataFrame()
        df = pd.DataFrame(prices, columns=["time","price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        # 聚合成日级别 OHLC
        df = df.set_index("time").resample("1D").agg({"price":["first","max","min","last"]})
        df.columns = ["open","high","low","close"]
        df = df.reset_index()
        return df
    return pd.DataFrame()

def get_okx_kline(symbol="BTC-USDT", interval="1D", limit=100):
    """从OKX公共API获取K线"""
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
    df = df[["time","open","high","low","close"]].astype({"open":float,"high":float,"low":float,"close":float})
    return df

# ---------------------
# UI布局 - 左侧栏
# ---------------------
st.sidebar.title("⚙️ 功能面板")

# 功能1：数据源选择
data_source = st.sidebar.selectbox("功能① 选择数据源", [
    "CoinGecko (免API)",
    "TokenInsight (免API)",
    "OKX API",
    "TokenInsight API"
])

api_url = None
if data_source in ["OKX API","TokenInsight API"]:
    api_url = st.sidebar.text_input("请输入 API 地址")

# 功能2：个标 / 组合标
single_symbol = st.sidebar.text_input("功能② 个标 (如 BTC / ETH / AAPL)", value="BTC")
portfolio_symbol = st.sidebar.text_input("功能② 组合标 (可留空，支持 BTC+ETH 等)", value="")

# 功能3：周期选择
interval = st.sidebar.selectbox("功能③ 周期选择", [
    "1m","15m","1h","4h","1d","1w","1M"
], index=4)

# 功能4：指标设置说明
with st.sidebar.expander("功能④ 技术指标说明"):
    st.markdown("""
    - **MACD**: 加密推荐 (8,21,5)，A股/美股推荐 (12,26,9)  
    - **RSI**: 加密推荐 14（超买90/超卖73），股票推荐 14（超买70/超卖30）  
    - **布林带 Bollinger**: 通用 20日，2倍标准差  
    - **MA/EMA**: 加密短周期 20/50，股票 50/200 长周期  
    - **ATR**: 常用14周期，用于波动率止损
    """)

# ---------------------
# 主视图 - 个标展示
# ---------------------
st.title("📈 Legend Quant Terminal")

if single_symbol:
    st.subheader(f"个标 K线图 - {single_symbol}")

    if data_source.startswith("CoinGecko"):
        df = get_coingecko_ohlc(symbol=single_symbol.lower(), days=90)
    elif data_source.startswith("OKX"):
        df = get_okx_kline(symbol=f"{single_symbol}-USDT", interval=interval)
    else:
        # 先用 CoinGecko 作为 TokenInsight 占位
        df = get_coingecko_ohlc(symbol=single_symbol.lower(), days=90)

    if not df.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K线"
        )])
        fig.update_layout(xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("未能获取到该标的的行情数据")

if portfolio_symbol:
    st.subheader(f"组合标分析 - {portfolio_symbol}")
    st.info("组合标功能开发中，目前支持单标展示。")
