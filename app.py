# app.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Crypto Daily Swing Signals", layout="wide")
st.title("Crypto Daily Swing Trading Signal Generator")

# --------------------------
# 用户输入：OKX币种与时间
# --------------------------
symbol = st.text_input("Enter cryptocurrency symbol (e.g., BTC-USDT, ETH-USDT):", "BTC-USDT")
start_date = st.date_input("Start date", pd.to_datetime("2023-01-01"))
end_date = st.date_input("End date", pd.to_datetime("2025-08-30"))

def fetch_okx_klines(symbol, start_date, end_date, interval="1D"):
    # OKX 公共K线接口
    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={interval}"
    
    r = requests.get(url)
    data = r.json()
    if data['code'] != '0':
        st.error("Failed to fetch data. Please check your symbol.")
        return None
    
    df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','vol','v','x','y','z'])
    df = df[['ts','o','h','l','c','vol']].astype(float)
    df['Date'] = pd.to_datetime(df['ts'], unit='ms')
    df.rename(columns={'o':'Open','h':'High','l':'Low','c':'Close','vol':'Volume'}, inplace=True)
    
    # 只取用户选择的日期范围
    df = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]
    df.reset_index(drop=True, inplace=True)
    return df

if st.button("Load Data"):
    df = fetch_okx_klines(symbol, start_date, end_date)
    if df is not None and len(df) > 0:
        # --------------------------
        # 技术指标计算
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
        # 止盈止损计算（ATR倍数）
        # --------------------------
        df['Stop_Loss'] = df['Close'] - df['ATR']
        df['Take_Profit'] = df['Close'] + 2*df['ATR']

        st.subheader("Signals Table")
        st.dataframe(df[['Date','Close','Signal','Stop_Loss','Take_Profit']].tail(50))

        # --------------------------
        # K线图 + 信号标注
        # --------------------------
        fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                                             open=df['Open'], high=df['High'],
                                             low=df['Low'], close=df['Close'],
                                             name=symbol)])
        
        buy_signals = df[df['Signal']==1]
        sell_signals = df[df['Signal']==-1]
        
        fig.add_trace(go.Scatter(x=buy_signals['Date'], y=buy_signals['Close'],
                                 mode='markers', marker_symbol='triangle-up',
                                 marker_color='green', marker_size=12,
                                 name='Buy Signal'))
        fig.add_trace(go.Scatter(x=sell_signals['Date'], y=sell_signals['Close'],
                                 mode='markers', marker_symbol='triangle-down',
                                 marker_color='red', marker_size=12,
                                 name='Sell Signal'))
        
        st.plotly_chart(fig, use_container_width=True)
