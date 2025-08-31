# app.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Crypto Swing Signals", layout="wide")
st.title("Crypto Swing Signals (OKX API)")

# --------------------------
# 下拉选择或手动输入币种
# --------------------------
default_symbol = "BTC-USDT"
crypto_options = ["BTC-USDT", "ETH-USDT", "LTC-USDT", "SOL-USDT", "BNB-USDT"]
symbol = st.selectbox("Select a cryptocurrency:", crypto_options)
symbol_custom = st.text_input("Or enter custom symbol:", "")
if symbol_custom.strip():
    symbol = symbol_custom.strip().upper()

# --------------------------
# 下拉选择K线周期
# --------------------------
interval_options = ["1m","5m","15m","30m","1h","4h","1d"]
interval = st.selectbox("Select K-line interval:", interval_options, index=2)  # 默认15m

# --------------------------
# 函数：获取OKX K线数据
# --------------------------
def fetch_okx_klines(symbol, interval="15m", limit=500):
    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={interval}&limit={limit}"
    r = requests.get(url)
    data = r.json()
    if data['code'] != '0':
        st.error("Failed to fetch data. Please check your symbol.")
        return None
    df = pd.DataFrame(data['data'])
    df = df.iloc[:, :6]  # 只取前6列
    df.columns = ['ts','Open','High','Low','Close','Volume']
    df[['Open','High','Low','Close','Volume']] = df[['Open','High','Low','Close','Volume']].astype(float)
    df['Date'] = pd.to_datetime(df['ts'], unit='ms')
    df.sort_values('Date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

# --------------------------
# 加载数据并计算信号
# --------------------------
if st.button("Load Data"):
    df = fetch_okx_klines(symbol, interval)
    if df is not None and len(df) > 0:
        # 技术指标
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        df['Std20'] = df['Close'].rolling(20).std()
        df['Upper'] = df['MA20'] + 2*df['Std20']
        df['Lower'] = df['MA20'] - 2*df['Std20']
        df['ATR'] = df['High'].rolling(14).max() - df['Low'].rolling(14).min()

        # 多期限均线 + 布林带信号
        signals = []
        for i in range(len(df)):
            if i < 50:
                signals.append(0)
                continue
            if df['MA5'][i] > df['MA20'][i] and df['Close'][i] > df['Lower'][i]:
                signals.append(1)  # Buy
            elif df['MA5'][i] < df['MA20'][i] and df['Close'][i] < df['Upper'][i]:
                signals.append(-1) # Sell
            else:
                signals.append(0)
        df['Signal'] = signals

        # 止盈止损
        df['Stop_Loss'] = df['Close'] - df['ATR']
        df['Take_Profit'] = df['Close'] + 2*df['ATR']

        # 显示表格
        st.subheader("Last 50 Signals")
        st.dataframe(df[['Date','Close','Signal','Stop_Loss','Take_Profit']].tail(50))

        # K线图 + 信号标注
        fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                                             open=df['Open'], high=df['High'],
                                             low=df['Low'], close=df['Close'],
                                             name=symbol)])
        buy_signals = df[df['Signal']==1]
        sell_signals = df[df['Signal']==-1]
        fig.add_trace(go.Scatter(x=buy_signals['Date'], y=buy_signals['Close'],
                                 mode='markers', marker_symbol='triangle-up',
                                 marker_color='green', marker_size=10,
                                 name='Buy Signal'))
        fig.add_trace(go.Scatter(x=sell_signals['Date'], y=sell_signals['Close'],
                                 mode='markers', marker_symbol='triangle-down',
                                 marker_color='red', marker_size=10,
                                 name='Sell Signal'))
        st.plotly_chart(fig, use_container_width=True)
