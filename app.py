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
        if "total_volumes" in data:
            vols = pd.DataFrame(data["total_volumes"], columns=["ts","volume"])
            vols["time"] = pd.to_datetime(vols["ts"], unit="ms")
            df = df.merge(vols[["time","volume"]], on="time", how="left")
        else:
            df["volume"] = np.random.randint(100, 1000, len(df))
        return df[["time", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        st.error(f"CoinGecko 数据获取失败: {e}")
        return pd.DataFrame()

def get_binance_data(symbol="BTCUSDT", interval="1d", limit=200):
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        resp = requests.get(url, params=params)
        data = resp.json()
        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
        return df[["time", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        st.error(f"Binance 数据获取失败: {e}")
        return pd.DataFrame()

def get_okx_data(symbol="BTC-USDT", bar="1D", limit=200):
    try:
        url = "https://www.okx.com/api/v5/market/candles"
        params = {"instId": symbol.upper(), "bar": bar, "limit": limit}
        resp = requests.get(url, params=params)
        data = resp.json()
        df = pd.DataFrame(data["data"], columns=[
            "time","open","high","low","close","volume","volCcy","volCcyQuote","confirm"
        ])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
        return df[["time","open","high","low","close","volume"]].sort_values("time")
    except Exception as e:
        st.error(f"OKX 公共行情数据获取失败: {e}")
        return pd.DataFrame()

# ================================
# 技术指标
# ================================
def add_indicators(df, macd_fast=12, macd_slow=26, macd_signal=9, rsi_period=14):
    if df.empty: return df
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()
    df["EMA200"] = df["close"].ewm(span=200).mean()
    # MACD
    exp1 = df["close"].ewm(span=macd_fast).mean()
    exp2 = df["close"].ewm(span=macd_slow).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=macd_signal).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    # RSI
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(rsi_period).mean()
    avg_loss = pd.Series(loss).rolling(rsi_period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# ================================
# 策略建议
# ================================
def strategy_suggestion(df, show_rsi, show_macd, show_volume):
    if df.empty: return "暂无数据"
    suggestions = []
    latest = df.iloc[-1]

    # 价格位置
    min_p, max_p = df["close"].min(), df["close"].max()
    pos = (latest["close"] - min_p) / (max_p - min_p + 1e-9) * 100
    suggestions.append(f"当前价格位于历史区间的 {pos:.1f}% 位置")

    # 支撑阻力
    recent = df.tail(20)
    support, resist = recent["low"].min(), recent["high"].max()
    suggestions.append(f"支撑位 ~ {support:.2f}，阻力位 ~ {resist:.2f}")

    if show_rsi:
        if latest["RSI"] > 70: suggestions.append("RSI 超买，注意风险")
        elif latest["RSI"] < 30: suggestions.append("RSI 超卖，可能反弹")

    if show_macd:
        if latest["MACD"] > latest["Signal"]: suggestions.append("MACD 金叉 → 偏多")
        else: suggestions.append("MACD 死叉 → 偏空")

    if show_volume:
        avg_vol = df["volume"].tail(20).mean()
        if latest["volume"] > 1.5*avg_vol:
            suggestions.append("成交量放大 → 可能趋势延续")

    return " | ".join(suggestions)

# ================================
# 主程序
# ================================
st.set_page_config(layout="wide", page_title="传奇量化终端")

st.sidebar.header("⚙️ 功能面板")

# 功能 1 数据源
source = st.sidebar.selectbox("数据源选择", [
    "CoinGecko API", "Binance 公共API", "OKX 公共API", "OKX API", "TokenInsight API"
])
if source in ["OKX API", "TokenInsight API"]:
    api_url = st.sidebar.text_input("请输入API地址")

# 功能 2 个标
symbol = st.sidebar.text_input("个标（如 ethereum, BTCUSDT, BTC-USDT 等）", "ethereum")

# 功能 3 周期
interval = st.sidebar.selectbox("选择周期", ["1d","1h","15m","4h"])

# 功能 4 市场类型
market_type = st.sidebar.selectbox("市场类型", ["加密货币", "A股", "美股"])

# 根据市场自动设置参数
if market_type == "加密货币":
    macd_fast, macd_slow, macd_signal, rsi_period = 12, 26, 9, 14
elif market_type == "A股":
    macd_fast, macd_slow, macd_signal, rsi_period = 8, 17, 9, 6
else:  # 美股
    macd_fast, macd_slow, macd_signal, rsi_period = 12, 26, 9, 14

# 功能 5 技术指标开关
st.sidebar.subheader("📊 技术指标")
show_ma20 = st.sidebar.checkbox("显示 MA20", True)
show_ma50 = st.sidebar.checkbox("显示 MA50", True)
show_ema200 = st.sidebar.checkbox("显示 EMA200", True)

# 功能 6 副图开关
st.sidebar.subheader("📉 副图选择")
show_volume = st.sidebar.checkbox("显示 成交量", True)
show_rsi = st.sidebar.checkbox("显示 RSI", True)
show_macd = st.sidebar.checkbox("显示 MACD", True)

# 功能 7 副图显示模式
merge_mode = st.sidebar.radio("副图显示模式", ["分离模式", "合并模式"], index=0)

# ================================
# 主视图
# ================================
st.title("📈 传奇量化交易终端 - 精英版")

if source == "CoinGecko API":
    df = get_coingecko_data(symbol, days="180", interval=interval)
elif source == "Binance 公共API":
    df = get_binance_data(symbol if "USDT" in symbol.upper() else symbol.upper()+"USDT", interval)
elif source == "OKX 公共API":
    df = get_okx_data(symbol if "-" in symbol else symbol.upper()+"-USDT", 
                      "1H" if interval=="1h" else ("15m" if interval=="15m" else "1D"))
elif source == "OKX API":
    st.warning("OKX API 模式需用户手动对接，这里仅做占位")
    df = pd.DataFrame()
else:
    st.warning("TokenInsight API 模式需用户手动对接，这里仅做占位")
    df = pd.DataFrame()

df = add_indicators(df, macd_fast, macd_slow, macd_signal, rsi_period)

if not df.empty:
    # 主图
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df["time"], open=df["open"], high=df["high"],
                                 low=df["low"], close=df["close"], name="K线"))
    if show_ma20: fig.add_trace(go.Scatter(x=df["time"], y=df["MA20"], name="MA20"))
    if show_ma50: fig.add_trace(go.Scatter(x=df["time"], y=df["MA50"], name="MA50"))
    if show_ema200: fig.add_trace(go.Scatter(x=df["time"], y=df["EMA200"], name="EMA200"))
    fig.update_layout(title=f"{symbol.upper()} K线", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)

    # 副图处理
    if merge_mode == "分离模式":
        if show_volume:
            fig_vol = go.Figure()
            colors = ["green" if df["close"].iloc[i] > df["open"].iloc[i] else "red" for i in range(len(df))]
            fig_vol.add_trace(go.Bar(x=df["time"], y=df["volume"], marker_color=colors, name="Volume"))
            st.plotly_chart(fig_vol, use_container_width=True, height=250)
        if show_rsi:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI"))
            fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
            fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
            st.plotly_chart(fig_rsi, use_container_width=True, height=250)
        if show_macd:
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD"))
            fig_macd.add_trace(go.Scatter(x=df["time"], y=df["Signal"], name="Signal"))
            fig_macd.add_trace(go.Bar(x=df["time"], y=df["Hist"], name="Hist"))
            st.plotly_chart(fig_macd, use_container_width=True, height=250)

    elif merge_mode == "合并模式":
        fig_merge = go.Figure()
        if show_volume:
            colors = ["green" if df["close"].iloc[i] > df["open"].iloc[i] else "red" for i in range(len(df))]
            fig_merge.add_trace(go.Bar(x=df["time"], y=df["volume"], marker_color=colors, name="Volume"))
        if show_rsi:
            fig_merge.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI"))
        if show_macd:
            fig_merge.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD"))
            fig_merge.add_trace(go.Scatter(x=df["time"], y=df["Signal"], name="Signal"))
        fig_merge.update_layout(title="合并副图", height=400)
        st.plotly_chart(fig_merge, use_container_width=True)

    # 实时策略卡片
    st.subheader("📌 实时策略建议")
    st.info(strategy_suggestion(df, show_rsi, show_macd, show_volume))

else:
    st.warning("未获取到行情数据，请检查数据源或输入的标的。")
