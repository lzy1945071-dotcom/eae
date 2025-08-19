import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------
# 数据获取函数
# ---------------------------

def get_data(source, symbol, interval, api_url=None):
    if source == "CoinGecko":
        # 默认日线，回退到 market_chart
        url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
        params = {"vs_currency": "usd", "days": "90", "interval": "daily"}
        r = requests.get(url, params=params)
        data = r.json()
        prices = data.get("prices", [])
        df = pd.DataFrame(prices, columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df["Open"] = df["price"]
        df["High"] = df["price"]
        df["Low"] = df["price"]
        df["Close"] = df["price"]
        df["Volume"] = [v[1] for v in data.get("total_volumes", [[0,0]])]
        return df[["time", "Open", "High", "Low", "Close", "Volume"]]

    elif source == "TokenInsight":
        # 占位，示例用 CoinGecko 数据代替
        return get_data("CoinGecko", symbol, interval)

    elif source == "OKX API":
        if not api_url:
            st.warning("请输入 OKX API 地址")
            return pd.DataFrame()
        try:
            r = requests.get(api_url)
            data = r.json()
            # TODO: 按 OKX K线接口格式解析
            return pd.DataFrame()
        except:
            return pd.DataFrame()

    elif source == "TokenInsight API":
        if not api_url:
            st.warning("请输入 TokenInsight API 地址")
            return pd.DataFrame()
        try:
            r = requests.get(api_url)
            data = r.json()
            return pd.DataFrame()
        except:
            return pd.DataFrame()

    elif source == "美股":
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo", interval=interval)
        df.reset_index(inplace=True)
        df.rename(columns={"Datetime": "time"}, inplace=True)
        return df[["time", "Open", "High", "Low", "Close", "Volume"]]

    elif source == "A股":
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo", interval=interval)
        df.reset_index(inplace=True)
        df.rename(columns={"Datetime": "time"}, inplace=True)
        return df[["time", "Open", "High", "Low", "Close", "Volume"]]

    else:
        return pd.DataFrame()

# ---------------------------
# 技术指标
# ---------------------------

def add_ma(df, window=20):
    df[f"MA{window}"] = df["Close"].rolling(window=window).mean()
    return df

def add_rsi(df, window=14):
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    df[f"RSI{window}"] = 100 - (100 / (1 + rs))
    return df

def add_macd(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    return df

# ---------------------------
# 策略建议
# ---------------------------

def strategy_suggestion(df):
    current_price = df["Close"].iloc[-1]
    min_p, max_p = df["Close"].min(), df["Close"].max()
    pct = (current_price - min_p) / (max_p - min_p + 1e-6) * 100

    # 支撑/阻力：简单取分位数
    support = df["Close"].quantile(0.2)
    resistance = df["Close"].quantile(0.8)

    if pct < 30:
        suggestion = "当前价格处于历史低位区间，适合买入/加仓"
    elif pct > 70:
        suggestion = "当前价格处于历史高位区间，谨慎，考虑止盈/减仓"
    else:
        suggestion = "价格在中位区间，观望或轻仓操作"

    return {
        "current_price": current_price,
        "position": f"{pct:.2f}%",
        "support": support,
        "resistance": resistance,
        "suggestion": suggestion,
    }

# ---------------------------
# Streamlit 界面
# ---------------------------

st.set_page_config(layout="wide")
st.title("📊 Legend Quant Terminal Elite")

# 功能① 数据源选择
source = st.sidebar.selectbox("① 选择数据源", 
    ["CoinGecko", "TokenInsight", "OKX API", "TokenInsight API", "美股", "A股"])
api_url = None
if source in ["OKX API", "TokenInsight API"]:
    api_url = st.sidebar.text_input("请输入 API 地址")

# 功能② 个标 / 组合标
symbol = st.sidebar.text_input("② 输入个标 (股票代码/币种ID)", "eth")
portfolio = st.sidebar.text_input("② 输入组合标 (可选)", "")

# 功能③ 周期
interval = st.sidebar.selectbox("③ 选择周期", 
    ["1m", "15m", "1h", "4h", "1d", "1wk", "1mo"], index=4)

# 功能④ 技术指标推荐参数
if source in ["CoinGecko", "TokenInsight", "OKX API", "TokenInsight API"]:
    st.sidebar.markdown("💡 加密货币参数建议: MA20/60, RSI14, BOLL(20,2), MACD(12,26,9)")
elif source == "美股":
    st.sidebar.markdown("💡 美股参数建议: MA50/200, RSI14, BOLL(20,2), MACD(12,26,9)")
elif source == "A股":
    st.sidebar.markdown("💡 A股参数建议: MA5/10/20, RSI6/12/24, BOLL(20,2), MACD(12,26,9)")

# ---------------------------
# 数据展示
# ---------------------------
df = get_data(source, symbol, interval, api_url=api_url)

if not df.empty:
    # 加指标
    df = add_ma(df, 20)
    df = add_rsi(df, 14)
    df = add_macd(df)

    # 绘图
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.05)

    # K线
    fig.add_trace(go.Candlestick(x=df["time"], open=df["Open"], high=df["High"],
                                 low=df["Low"], close=df["Close"], name="K线"),
                  row=1, col=1)
    # 成交量
    fig.add_trace(go.Bar(x=df["time"], y=df["Volume"], name="成交量", marker_color="lightblue"),
                  row=2, col=1)
    # 移动平均线
    fig.add_trace(go.Scatter(x=df["time"], y=df["MA20"], mode="lines", name="MA20"),
                  row=1, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_white")

    st.plotly_chart(fig, use_container_width=True)

    # 策略建议
    suggestion = strategy_suggestion(df)
    st.subheader("📌 实时策略建议")
    st.write(f"**当前价**: {suggestion['current_price']:.2f}")
    st.write(f"**历史区间位置**: {suggestion['position']}")
    st.write(f"**支撑位**: {suggestion['support']:.2f}")
    st.write(f"**阻力位**: {suggestion['resistance']:.2f}")
    st.success(suggestion["suggestion"])
else:
    st.warning("未能获取数据，请检查数据源或代码。")
