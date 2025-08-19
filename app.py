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
        return df[["time", "open", "high", "low", "close"]]
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
# 简单回测策略
# ================================
def backtest_strategies(df, strategies):
    results = []
    if df.empty:
        return pd.DataFrame()
    for strat in strategies:
        trades, win, loss = 0, 0, 0
        for i in range(1, len(df)):
            # 趋势跟随
            if strat == "趋势跟随" and df["MA50"].iloc[i-1] < df["EMA200"].iloc[i-1] and df["MA50"].iloc[i] > df["EMA200"].iloc[i]:
                ret = (df["close"].iloc[i] - df["close"].iloc[i-1]) / df["close"].iloc[i-1]
                trades += 1
                win += ret > 0
                loss += ret <= 0
            # 动量突破
            if strat == "动量突破" and df["close"].iloc[i] > df["close"].rolling(20).max().iloc[i-1] and df["RSI"].iloc[i] > 70:
                ret = (df["close"].iloc[i] - df["close"].iloc[i-1]) / df["close"].iloc[i-1]
                trades += 1
                win += ret > 0
                loss += ret <= 0
            # 反转捕捉
            if strat == "反转捕捉" and df["RSI"].iloc[i-1] < 30 and df["MACD"].iloc[i-1] < 0 and df["MACD"].iloc[i] > df["Signal"].iloc[i]:
                ret = (df["close"].iloc[i] - df["close"].iloc[i-1]) / df["close"].iloc[i-1]
                trades += 1
                win += ret > 0
                loss += ret <= 0
            # 波动率突破
            if strat == "波动率突破" and (df["high"].iloc[i-1]-df["low"].iloc[i-1]) > df["close"].rolling(20).std().iloc[i-1]*2:
                ret = (df["close"].iloc[i] - df["close"].iloc[i-1]) / df["close"].iloc[i-1]
                trades += 1
                win += ret > 0
                loss += ret <= 0
        if trades > 0:
            results.append({
                "策略": strat,
                "胜率": f"{(win/trades)*100:.1f}%",
                "交易次数": trades,
                "平均收益": f"{((df['close'].pct_change().mean())*100):.2f}%"
            })
    return pd.DataFrame(results)

# ================================
# 主程序
# ================================
st.set_page_config(layout="wide", page_title="传奇量化终端")

st.sidebar.header("⚙️ 功能面板")

# 功能 1 数据源
source = st.sidebar.selectbox("数据源选择", ["CoinGecko API", "OKX API", "TokenInsight API"])
if source in ["OKX API", "TokenInsight API"]:
    api_url = st.sidebar.text_input("请输入API地址")

# 功能 2 个标 / 组合标
symbol = st.sidebar.text_input("个标（如 ethereum, bitcoin, btcusdt 等）", "ethereum")
combo_symbols = st.sidebar.text_area("组合标（用逗号分隔）")

# 功能 3 技术指标
st.sidebar.subheader("📊 技术指标")
default_indicators = ["MA20", "MA50", "EMA200", "MACD", "RSI"]
selected_indicators = st.sidebar.multiselect(
    "选择显示的指标", 
    ["MA20", "MA50", "EMA200", "MACD", "RSI"],
    default=default_indicators
)

# 功能 4 周期
interval = st.sidebar.selectbox("选择周期", ["1d","1h","15m","4h"])

# 功能 5 组合策略
st.sidebar.subheader("🧩 组合策略")
selected_strategies = st.sidebar.multiselect(
    "选择策略组合", 
    ["趋势跟随", "动量突破", "反转捕捉", "波动率突破"]
)

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
    if "MA20" in selected_indicators:
        fig.add_trace(go.Scatter(x=df["time"], y=df["MA20"], name="MA20"))
    if "MA50" in selected_indicators:
        fig.add_trace(go.Scatter(x=df["time"], y=df["MA50"], name="MA50"))
    if "EMA200" in selected_indicators:
        fig.add_trace(go.Scatter(x=df["time"], y=df["EMA200"], name="EMA200"))

    fig.update_layout(title=f"{symbol.upper()} K线", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)

    # RSI 副图
    if "RSI" in selected_indicators:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI"))
        fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
        fig_rsi.update_layout(title="RSI 指标", height=250)
        st.plotly_chart(fig_rsi, use_container_width=True)

    # MACD 副图
    if "MACD" in selected_indicators:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD"))
        fig_macd.add_trace(go.Scatter(x=df["time"], y=df["Signal"], name="Signal"))
        fig_macd.add_trace(go.Bar(x=df["time"], y=df["Hist"], name="Hist"))
        fig_macd.update_layout(title="MACD 指标", height=250)
        st.plotly_chart(fig_macd, use_container_width=True)

    # 组合策略回测结果
    if selected_strategies:
        st.subheader("📊 组合策略回测结果")
        results = backtest_strategies(df, selected_strategies)
        st.dataframe(results)
else:
    st.warning("未获取到行情数据，请检查数据源或代码。")
