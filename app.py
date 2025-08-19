import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

# ================================
# 数据获取
# ================================
def get_coingecko_data(symbol="ethereum", vs_currency="usd", days="90", interval="1d"):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
        params = {"vs_currency": vs_currency, "days": days, "interval": interval}
        resp = requests.get(url, params=params)
        data = resp.json()
        prices = pd.DataFrame(data["prices"], columns=["ts", "price"])
        prices["time"] = pd.to_datetime(prices["ts"], unit="ms")
        df = prices.copy()
        df["open"] = df["price"]
        df["high"] = df["price"]
        df["low"] = df["price"]
        df["close"] = df["price"]
        # 构造成交量
        if "total_volumes" in data:
            vols = pd.DataFrame(data["total_volumes"], columns=["ts","volume"])
            vols["time"] = pd.to_datetime(vols["ts"], unit="ms")
            df = df.merge(vols[["time","volume"]], on="time", how="left")
        else:
            df["volume"] = np.random.randint(100, 1000, len(df))
        return df[["time", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        st.error(f"数据获取失败: {e}")
        return pd.DataFrame()

# ================================
# 技术指标
# ================================
def add_indicators(df):
    if df.empty: 
        return df
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()
    df["EMA200"] = df["close"].ewm(span=200).mean()
    # MACD
    exp1 = df["close"].ewm(span=12).mean()
    exp2 = df["close"].ewm(span=26).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    # RSI
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(14).mean()
    avg_loss = pd.Series(loss).rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# ================================
# 主程序
# ================================
st.set_page_config(layout="wide", page_title="传奇量化终端")

st.sidebar.header("⚙️ 功能面板")

# 功能 1 数据源
source = st.sidebar.selectbox("数据源选择", ["CoinGecko API", "OKX API", "TokenInsight API"])
if source in ["OKX API", "TokenInsight API"]:
    api_url = st.sidebar.text_input("请输入API地址")

# 功能 2 个标
symbol = st.sidebar.text_input("个标（如 ethereum, bitcoin, btcusdt 等）", "ethereum")

# 功能 3 周期
interval = st.sidebar.selectbox("选择周期", ["1d","1h","15m","4h"])

# 功能 4 技术指标开关
st.sidebar.subheader("📊 技术指标")
show_ma20 = st.sidebar.checkbox("显示 MA20", True)
show_ma50 = st.sidebar.checkbox("显示 MA50", True)
show_ema200 = st.sidebar.checkbox("显示 EMA200", True)
show_rsi = st.sidebar.checkbox("显示 RSI 副图", True)
show_macd = st.sidebar.checkbox("显示 MACD 副图", True)
show_volume = st.sidebar.checkbox("显示 成交量 副图", True)

# ================================
# 主视图
# ================================
st.title("📈 传奇量化交易终端 - 精英版")

df = get_coingecko_data(symbol, days="180", interval=interval)
df = add_indicators(df)

if not df.empty:
    # 绘制主图 K线 + 指标
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df["time"], open=df["open"], high=df["high"],
                                 low=df["low"], close=df["close"], name="K线"))

    if show_ma20:
        fig.add_trace(go.Scatter(x=df["time"], y=df["MA20"], name="MA20"))
    if show_ma50:
        fig.add_trace(go.Scatter(x=df["time"], y=df["MA50"], name="MA50"))
    if show_ema200:
        fig.add_trace(go.Scatter(x=df["time"], y=df["EMA200"], name="EMA200"))

    # 开启交互绘图工具
    fig.update_layout(
        title=f"{symbol.upper()} K线",
        xaxis_rangeslider_visible=False,
        height=600,
        dragmode="drawline",  # 可以改成 drawrect / drawopenpath 等
        newshape=dict(line_color="red")
    )
    st.plotly_chart(fig, use_container_width=True)

    # 成交量副图
    if show_volume:
        fig_vol = go.Figure()
        colors = ["green" if df["close"].iloc[i] > df["open"].iloc[i] else "red" for i in range(len(df))]
        fig_vol.add_trace(go.Bar(x=df["time"], y=df["volume"], marker_color=colors, name="Volume"))
        fig_vol.update_layout(title="成交量", height=250)
        st.plotly_chart(fig_vol, use_container_width=True)

    # RSI 副图
    if show_rsi:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI"))
        fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
        fig_rsi.update_layout(title="RSI 指标", height=250)
        st.plotly_chart(fig_rsi, use_container_width=True)

    # MACD 副图
    if show_macd:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD"))
        fig_macd.add_trace(go.Scatter(x=df["time"], y=df["Signal"], name="Signal"))
        fig_macd.add_trace(go.Bar(x=df["time"], y=df["Hist"], name="Hist"))
        fig_macd.update_layout(title="MACD 指标", height=250)
        st.plotly_chart(fig_macd, use_container_width=True)

else:
    st.warning("未获取到行情数据，请检查数据源或代码。")
