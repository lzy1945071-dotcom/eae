# app.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Crypto Daily Swing Signals", layout="wide")
st.title("BTC 15-Minute Swing Signals (OKX API)")

# --------------------------
# 默认币种和周期
# --------------------------
default_symbol = "BTC-USDT"
default_interval = "15m"

def fetch_okx_klines(symbol, interval="15m", limit=500):
    # OKX 公共K线接口
    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={interval}&limit={limit}"
    r = requests.get(url)
    data = r.json()
    if data['code'] != '0':
        st.error("Failed to fetch data. Please check your symbol.")
        return None
    df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','vol','v','x','y','z'])
    df = df[['ts','o','h','l','c','vol']].astype(float)
    df['Date'] = pd.to_datetime(df['ts'], unit='ms')
    df.rename(columns={'o':'Open','h':'High','l':'Low','c':'Close','vol':'Volume'}, inplace=True)
    df.sort_values('Date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

# --------------------------
# 加载数据
# --------------------------
df = fetch_okx_klines(default_symbol, default_interval)
if df is not None and len(df) > 0:
    # --------------------------
    # 技术指标
    # --------------------------
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    df['Std20'] = df['Close'].rolling(20).std()
    df['Upper'] = df['MA20'] + 2*df['Std20']
    df['Lower'] = df['MA20'] - 2*df['Std20']
    df['ATR'] = df['High'].rolling(14).max() - df['Low'].rolling(14).min()
    
    # --------------------------
    # 多期限均线 + 布林带信号
    # --------------------------
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

    # --------------------------
    # 止盈止损
    # --------------------------
    df['Stop_Loss'] = df['Close'] - df['ATR']
    df['Take_Profit'] = df['Close'] + 2*df['ATR']

    st.subheader("Last 50 Signals")
    st.dataframe(df[['Date','Close','Signal','Stop_Loss','Take_Profit']].tail(50))

    # --------------------------
    # K线图 + 信号标注
    # --------------------------
    fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                                         open=df['Open'], high=df['High'],
                                         low=df['Low'], close=df['Close'],
                                         name=default_symbol)])
    
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
