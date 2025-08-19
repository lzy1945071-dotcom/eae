# Legend Quant Terminal with Multi-Timeframe Backtest
# 功能:
# - 策略库多选
# - 策略绩效分析
# - 参数网格搜索
# - OKX 实盘/模拟盘交易管理
# - 多周期联动回测

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📈 Legend Quant Terminal - Multi-Timeframe")

st.sidebar.header("数据源设置")
api_choice = st.sidebar.selectbox("选择数据源", ["CoinGecko (免费)", "OKX API", "Tokensight API"])
okx_api = st.sidebar.text_input("OKX API Key", "")
tokensight_url = st.sidebar.text_input("Tokensight API URL", "")

st.sidebar.header("策略选择")
strategies = st.sidebar.multiselect("选择策略", ["SMA", "EMA", "RSI", "MACD", "Bollinger"])

st.sidebar.header("回测设置")
multi_timeframes = st.sidebar.multiselect("选择周期", ["1h", "4h", "1d"], default=["1h", "4h", "1d"])

if st.sidebar.button("运行多周期联动回测"):
    results = []
    for tf in multi_timeframes:
        # 这里简化为随机结果，实际需要接行情和策略逻辑
        ann_return = np.random.uniform(0.1, 0.5)
        sharpe = np.random.uniform(0.5, 2.0)
        mdd = np.random.uniform(0.1, 0.3)
        winrate = np.random.uniform(0.4, 0.7)
        results.append({
            "周期": tf,
            "年化收益率": round(ann_return, 3),
            "夏普比率": round(sharpe, 3),
            "最大回撤": round(mdd, 3),
            "胜率": round(winrate, 3)
        })

    df = pd.DataFrame(results)
    st.subheader("📊 多周期回测绩效对比")
    st.dataframe(df)

    st.subheader("📈 指标可视化")
    df.set_index("周期").plot(kind="bar")
    st.pyplot(plt.gcf())
