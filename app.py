import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime
import ta

# ---------------------------
# 数据获取函数
# ---------------------------
def get_coingecko_data(symbol="bitcoin", currency="usd", days="90", interval="1d"):
    """从 Coingecko 获取 K 线数据"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
        params = {"vs_currency": currency, "days": days, "interval": interval}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        prices = pd.DataFrame(data["prices"], columns=["time", "price"])
        prices["time"] = pd.to_datetime(prices["time"], unit="ms")
        ohlc = prices.resample("1D", on="time").agg({"price": ["first", "max", "min", "last"]})
        ohlc.columns = ["open", "high", "low", "close"]
        return ohlc.reset_index()
    except Exception as e:
        st.error(f"获取 CoinGecko 数据失败: {e}")
        return pd.DataFrame()

# ---------------------------
# 技术指标计算
# ---------------------------
def add_indicators(df, rsi_window=14, macd_params=(12, 26, 9)):
    if df.empty: 
        return df
    df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=rsi_window).rsi()
    macd = ta.trend.MACD(df["close"], window_slow=macd_params[1], window_fast=macd_params[0], window_sign=macd_params[2])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()
    return df

# ---------------------------
# 实时策略建议
# ---------------------------
def strategy_card(df):
    if df.empty: 
        return "⚠️ 无数据"
    current = df["close"].iloc[-1]
    low, high = df["close"].min(), df["close"].max()
    pct = (current - low) / (high - low) * 100 if high > low else 0
    support = df["low"].tail(20).min()
    resistance = df["high"].tail(20).max()

    suggestion = "🔵 低位 → 可逢低布局" if pct < 30 else "🟡 中位 → 观望为主" if pct < 70 else "🔴 高位 → 谨慎追高"

    card = f"""
    ### 📊 实时策略建议
    - 当前价格: {current:.2f}
    - 历史区间百分位: {pct:.1f}%
    - 支撑位区间: {support:.2f}
    - 压力位区间: {resistance:.2f}
    - 策略提示: **{suggestion}**
    """
    return card

# ---------------------------
# 主程序
# ---------------------------
st.set_page_config(layout="wide", page_title="Legend Quant Terminal")

# ---------------------------
# 侧边栏
# ---------------------------
st.sidebar.header("⚙️ 功能设置")

# 1. 数据源
source = st.sidebar.selectbox("数据来源", ["CoinGecko (免API)", "OKX API", "TokenInsight API"])
if source in ["OKX API", "TokenInsight API"]:
    api_url = st.sidebar.text_input("请输入 API 地址")
else:
    api_url = None

# 2. 个标选择
symbol = st.sidebar.text_input("个标 (CoinGecko ID，如 bitcoin, ethereum)", "ethereum")

# 3. 技术指标参数
st.sidebar.subheader("📈 技术指标参数")
rsi_window = st.sidebar.number_input("RSI 窗口", 5, 50, 14)
macd_fast = st.sidebar.number_input("MACD 快线", 5, 50, 12)
macd_slow = st.sidebar.number_input("MACD 慢线", 10, 100, 26)
macd_signal = st.sidebar.number_input("MACD 信号线", 5, 50, 9)

# 4. 风控参数
st.sidebar.subheader("🛡 风控参数")
currency_unit = st.sidebar.selectbox("资金计量单位", ["USD", "USDT", "CNY", "BTC", "ETH"])
total_capital = st.sidebar.number_input("账户总资金", min_value=1.0, value=10000.0, step=100.0)
risk_pct = st.sidebar.slider("单笔风险占比 (%)", 0.1, 5.0, 1.0)

# ---------------------------
# 获取数据
# ---------------------------
data = get_coingecko_data(symbol=symbol, currency="usd", days="90", interval="1d")
data = add_indicators(data, rsi_window, (macd_fast, macd_slow, macd_signal))

# ---------------------------
# 主视图
# ---------------------------
st.title("💹 Legend Quant Terminal (精英版)")

if not data.empty:
    fig = go.Figure()

    # K线图
    fig.add_trace(go.Candlestick(
        x=data["time"], open=data["open"], high=data["high"], low=data["low"], close=data["close"],
        name="K线"
    ))

    # 成交量
    fig.add_trace(go.Bar(
        x=data["time"], y=(data["close"]-data["open"]),
        marker_color=np.where(data["close"] > data["open"], "green", "red"),
        name="成交量", yaxis="y2", opacity=0.3
    ))

    fig.update_layout(
        title=f"{symbol.upper()} K线图 (含指标)",
        yaxis_title="价格",
        yaxis2=dict(overlaying="y", side="right", showgrid=False),
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=700
    )

    st.plotly_chart(fig, use_container_width=True)

    # MACD 副图
    fig_macd = go.Figure()
    fig_macd.add_trace(go.Bar(x=data["time"], y=data["MACD_hist"], name="MACD Hist",
                              marker_color=np.where(data["MACD_hist"]>=0, "green", "red")))
    fig_macd.add_trace(go.Scatter(x=data["time"], y=data["MACD"], mode="lines", name="MACD"))
    fig_macd.add_trace(go.Scatter(x=data["time"], y=data["MACD_signal"], mode="lines", name="Signal"))

    fig_macd.update_layout(title="MACD 指标", template="plotly_dark", height=300)
    st.plotly_chart(fig_macd, use_container_width=True)

    # 实时策略建议
    st.markdown(strategy_card(data))
else:
    st.warning("未能获取行情数据，请检查数据源/API 设置。")
