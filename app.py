import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# ========================= 基础函数 =========================

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    short_ema = data['Close'].ewm(span=short_window, adjust=False).mean()
    long_ema = data['Close'].ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    return macd, signal

def calculate_bollinger_bands(data, window=20, num_std=2):
    rolling_mean = data['Close'].rolling(window=window).mean()
    rolling_std = data['Close'].rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return rolling_mean, upper_band, lower_band

def calculate_adx(data, period=14):
    df = data.copy()
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['DMplus'] = np.where((df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']), 
                             df['High'] - df['High'].shift(1), 0)
    df['DMplus'] = np.where(df['DMplus'] < 0, 0, df['DMplus'])
    df['DMminus'] = np.where((df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)), 
                              df['Low'].shift(1) - df['Low'], 0)
    df['DMminus'] = np.where(df['DMminus'] < 0, 0, df['DMminus'])
    TRn = df['TR'].rolling(window=period).sum()
    DMplusN = df['DMplus'].rolling(window=period).sum()
    DMminusN = df['DMminus'].rolling(window=period).sum()
    DIplus = 100 * (DMplusN / TRn)
    DIminus = 100 * (DMminusN / TRn)
    DX = (abs(DIplus - DIminus) / (DIplus + DIminus)) * 100
    ADX = DX.rolling(window=period).mean()
    return ADX, DIplus, DIminus

def calculate_fibonacci_levels(data, lookback=100):
    recent = data.tail(lookback)
    high, low = recent['High'].max(), recent['Low'].min()
    diff = high - low
    levels = {
        "0.236": high - diff * 0.236,
        "0.382": high - diff * 0.382,
        "0.5": high - diff * 0.5,
        "0.618": high - diff * 0.618,
        "0.786": high - diff * 0.786
    }
    return levels

# ========================= Streamlit App =========================

st.set_page_config(page_title="量化分析工具", layout="wide")
st.sidebar.title("📊 量化分析工具")

page = st.sidebar.radio("选择页面", ["数据", "指标", "策略"])

ticker = st.sidebar.text_input("输入股票代码", "AAPL")
start_date = st.sidebar.date_input("开始日期", datetime.date(2020, 1, 1))
end_date = st.sidebar.date_input("结束日期", datetime.date.today())

df = yf.download(ticker, start=start_date, end=end_date)
if df.empty:
    st.error("下载数据失败，请检查代码或日期范围")
    st.stop()

dfi = df.copy()
dfi['MA20'] = dfi['Close'].rolling(window=20).mean()
dfi['MA50'] = dfi['Close'].rolling(window=50).mean()
dfi['RSI'] = calculate_rsi(dfi)
dfi['MACD'], dfi['MACD_signal'] = calculate_macd(dfi)
dfi['BB_mid'], dfi['BB_upper'], dfi['BB_lower'] = calculate_bollinger_bands(dfi)
dfi['ADX'], dfi['DI+'], dfi['DI-'] = calculate_adx(dfi)

# ========================= 页面：数据 =========================

if page == "数据":
    st.subheader("📈 股票数据")
    st.dataframe(dfi.tail(200))

# ========================= 页面：指标 =========================

elif page == "指标":
    st.subheader("📊 技术指标")
    st.line_chart(dfi[['Close', 'MA20', 'MA50']])
    st.line_chart(dfi[['RSI']])
    st.line_chart(dfi[['MACD', 'MACD_signal']])
    st.line_chart(dfi[['BB_upper', 'BB_mid', 'BB_lower']])
    st.line_chart(dfi[['ADX']])

# ========================= 页面：策略 =========================

elif page == "策略":
    st.subheader("📌 策略分析")
    last = dfi.iloc[-1]
    price = last['Close']
    ma20, ma50 = last['MA20'], last['MA50']
    st.metric("当前价格", f"{price:.2f}")
    st.metric("MA20", f"{ma20:.2f}")
    st.metric("MA50", f"{ma50:.2f}")

    # --- ADX ---
    adx_strength = last['ADX']
    trend_desc = "震荡/弱趋势"
    if adx_strength > 25:
        trend_desc = "趋势显著"
    elif adx_strength > 20:
        trend_desc = "趋势初步形成"
    st.metric("ADX", f"{adx_strength:.2f}", trend_desc)

    # --- 斐波那契 ---
    fib_levels = calculate_fibonacci_levels(dfi, 100)
    st.markdown("**🔢 斐波那契回调位：**")
    st.write(fib_levels)

    # --- 做多 / 做空评分 ---
    long_score, short_score = 0, 0
    if ma20 > ma50:
        long_score += 1
    else:
        short_score += 1
    if last['MACD'] > last['MACD_signal']:
        long_score += 1
    else:
        short_score += 1
    if last['RSI'] < 30:
        long_score += 1
    elif last['RSI'] > 70:
        short_score += 1
    if adx_strength > 25:
        if ma20 > ma50:
            long_score += 1
        else:
            short_score += 1
    st.metric("做多评分", long_score)
    st.metric("做空评分", short_score)

    # --- 诱多 / 诱空概率 ---
    bull_trap_prob, bear_trap_prob = 0, 0
    if last['RSI'] > 70 and ma20 < ma50:
        bull_trap_prob = 70
    if last['RSI'] < 30 and ma20 > ma50:
        bear_trap_prob = 65
    st.metric("诱多概率", f"{bull_trap_prob:.1f}%")
    st.metric("诱空概率", f"{bear_trap_prob:.1f}%")

    # --- 买入 / 卖出建议 ---
    advice = "观望"
    reasons_all = []
    if long_score > short_score and bull_trap_prob < 50:
        advice = "建议买入/做多"
        reasons_all.append("综合指标偏多")
    elif short_score > long_score and bear_trap_prob < 50:
        advice = "建议卖出/做空"
        reasons_all.append("综合指标偏空")
    else:
        advice = "观望为主"
        reasons_all.append("信号矛盾或陷阱概率高")

    reasons_all.append(f"ADX显示：{trend_desc}")
    nearest = min(fib_levels.items(), key=lambda x: abs(x[1]-price))
    reasons_all.append(f"斐波那契参考：接近 {nearest[0]} 回调位 {nearest[1]:.2f}")

    st.subheader("📌 综合建议")
    st.success(f"{advice} ｜ 理由：{'；'.join(reasons_all)}")
