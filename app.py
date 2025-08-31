# app.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Crypto Daily Swing Signals", layout="wide")
st.title("Crypto Daily Swing Trading Signal Generator")

# --------------------------
# 用户输入：币种与历史数据
# --------------------------
symbol = st.text_input("Enter cryptocurrency symbol (e.g., BTC-USD, ETH-USD):", "BTC-USD")
start_date = st.date_input("Start date", pd.to_datetime("2023-01-01"))
end_date = st.date_input("End date", pd.to_datetime("2025-08-30"))

if st.button("Load Data"):
    df = yf.download(symbol, start=start_date, end=end_date)
    df.reset_index(inplace=True)
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
            signals.append(1)  # Buy signal
        elif df['MA5'][i] < df['MA20'][i] and df['Close'][i] < df['Upper'][i]:
            signals.append(-1) # Sell signal
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
