
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import ta

st.set_page_config(layout="wide", page_title="Legend Quant Terminal Elite v3+")
st.title("💎 Legend Quant Terminal Elite v3+")

# ---------------- Sidebar ----------------
st.sidebar.header("⚙️ 数据配置（统一入口）")
data_source = st.sidebar.selectbox("数据来源", ["CoinGecko（示例-走YF代理）", "TokenInsight（示例-占位）", "OKX API（示例-占位）"])
api_key = st.sidebar.text_input("API Key（TokenInsight/OKX 可选）", type="password")

asset_type = st.sidebar.selectbox("标的类型", ["加密货币", "美股", "A股"])
default_symbol = "BTC-USD" if asset_type=="加密货币" else ("AAPL" if asset_type=="美股" else "600519.SS")
symbol = st.sidebar.text_input("个标代码/币种", value=default_symbol, help="例：BTC-USD / AAPL / 600519.SS")
combo_symbols = st.sidebar.text_area("组合标的 (逗号分隔)", value="BTC-USD,ETH-USD")
quote_currency = st.sidebar.selectbox("计价货币", ["USDT", "USD", "CNY", "BTC"])

st.sidebar.header("🕒 周期与长度")
period = st.sidebar.selectbox("历史区间", ["3mo","6mo","1y","2y","5y"], index=1)
interval = st.sidebar.selectbox("K线周期", ["1d","1h","1wk","1mo"], index=0)

st.sidebar.header("📈 指标与策略")
show_sma = st.sidebar.checkbox("SMA", True)
sma_fast = st.sidebar.number_input("SMA 快", 2, 300, 20)
sma_slow = st.sidebar.number_input("SMA 慢", 3, 600, 60)
show_ema = st.sidebar.checkbox("EMA", False)
ema_fast = st.sidebar.number_input("EMA 快", 2, 200, 12)
ema_slow = st.sidebar.number_input("EMA 慢", 3, 400, 26)
show_boll = st.sidebar.checkbox("布林带", False)
boll_win = st.sidebar.number_input("布林窗口", 5, 100, 20)
show_macd = st.sidebar.checkbox("MACD", True)
macd_sig = st.sidebar.number_input("MACD 信号线", 3, 20, 9)
show_rsi = st.sidebar.checkbox("RSI", True)
rsi_win = st.sidebar.number_input("RSI 窗口", 2, 60, 14)
rsi_buy = st.sidebar.number_input("RSI 超卖<=买入", 1, 99, 30)
rsi_sell = st.sidebar.number_input("RSI 超买>=卖出", 40, 99, 70)

combine_mode = st.sidebar.selectbox("信号合成", ["任一触发（OR）", "多数投票（Majority）", "全体一致（AND）"], index=1)

st.sidebar.header("💼 回测参数")
initial_cash = st.sidebar.number_input("初始资金", min_value=100.0, value=10000.0, step=100.0)
fee_bps = st.sidebar.number_input("手续费（基点）", min_value=0, max_value=200, value=10)
slip_bps = st.sidebar.number_input("滑点（基点）", min_value=0, max_value=200, value=5)
max_pos = st.sidebar.slider("最大仓位（比例）", 0.1, 1.0, 1.0, 0.1)

# ---------------- Data Fetch ----------------
@st.cache_data(ttl=900)
def fetch_yf(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
    return df.dropna()

def load_data(symbol):
    # 这里统一用 yfinance 拉取演示数据（股票/加密都可），API 位以后对接真实源
    return fetch_yf(symbol, period, interval)

df = load_data(symbol)

# ---------------- Indicators & Signals ----------------
def add_indicators(df):
    out = df.copy()
    close = out["Close"]
    if show_sma:
        out["SMA_fast"] = close.rolling(sma_fast).mean()
        out["SMA_slow"] = close.rolling(sma_slow).mean()
    if show_ema:
        out["EMA_fast"] = close.ewm(span=ema_fast).mean()
        out["EMA_slow"] = close.ewm(span=ema_slow).mean()
    if show_boll:
        ma = close.rolling(boll_win).mean()
        std = close.rolling(boll_win).std()
        out["BOLL_H"] = ma + 2*std
        out["BOLL_L"] = ma - 2*std
    if show_macd:
        macd_ind = ta.trend.MACD(close, window_slow=ema_slow, window_fast=ema_fast, window_sign=macd_sig)
        out["MACD"] = macd_ind.macd()
        out["MACD_signal"] = macd_ind.macd_signal()
        out["MACD_hist"] = macd_ind.macd_diff()
    if show_rsi:
        rsi = ta.momentum.RSIIndicator(close, window=rsi_win)
        out["RSI"] = rsi.rsi()
    # ATR for SL/TP
    atr = ta.volatility.AverageTrueRange(high=out["High"], low=out["Low"], close=out["Close"], window=14)
    out["ATR"] = atr.average_true_range()
    return out

def gen_signals(df):
    s_cols = []
    if show_sma and "SMA_fast" in df.columns and "SMA_slow" in df.columns:
        s = np.where(df["SMA_fast"] > df["SMA_slow"], 1, -1)
        df["SIG_SMA"] = s; s_cols.append("SIG_SMA")
    if show_ema and "EMA_fast" in df.columns and "EMA_slow" in df.columns:
        s = np.where(df["EMA_fast"] > df["EMA_slow"], 1, -1)
        df["SIG_EMA"] = s; s_cols.append("SIG_EMA")
    if show_macd and "MACD" in df.columns:
        cross_up = (df["MACD"].shift(1) <= df["MACD_signal"].shift(1)) & (df["MACD"] > df["MACD_signal"])
        cross_dn = (df["MACD"].shift(1) >= df["MACD_signal"].shift(1)) & (df["MACD"] < df["MACD_signal"])
        s = np.zeros(len(df)); s[cross_up] = 1; s[cross_dn] = -1
        df["SIG_MACD"] = s; s_cols.append("SIG_MACD")
    if show_rsi and "RSI" in df.columns:
        s = np.zeros(len(df)); s[df["RSI"] <= rsi_buy] = 1; s[df["RSI"] >= rsi_sell] = -1
        df["SIG_RSI"] = s; s_cols.append("SIG_RSI")
    if show_boll and "BOLL_H" in df.columns:
        s = np.zeros(len(df)); s[df["Close"] > df["BOLL_H"]] = -1; s[df["Close"] < df["BOLL_L"]] = 1
        df["SIG_BOLL"] = s; s_cols.append("SIG_BOLL")

    if not s_cols:
        df["SIG_COMB"] = 0
        return df

    S = df[s_cols].fillna(0)
    if combine_mode.startswith("任一"):
        long_any = (S==1).any(axis=1); short_any = (S==-1).any(axis=1)
        comb = np.where(long_any & ~short_any, 1, np.where(short_any & ~long_any, -1, 0))
    elif combine_mode.startswith("多数"):
        vote = S.sum(axis=1)
        comb = np.where(vote>0, 1, np.where(vote<0, -1, 0))
    else:
        all_long = (S==1).all(axis=1); all_short = (S==-1).all(axis=1)
        comb = np.where(all_long, 1, np.where(all_short, -1, 0))

    df["SIG_COMB"] = comb
    return df

def backtest(df):
    price = df["Close"]
    sig = df["SIG_COMB"].fillna(0).astype(int).values
    ret = price.pct_change().fillna(0).values
    cost = (fee_bps+slip_bps)/10000.0
    pos = np.zeros(len(sig))
    last_sig = 0
    for i in range(1, len(sig)):
        if sig[i] != 0:
            last_sig = sig[i]
        else:
            last_sig = 0
        pos[i] = last_sig
    turn = np.abs(np.diff(np.concatenate([[0], pos])))
    strat_ret = pos*ret - turn*cost
    equity = (1+pd.Series(strat_ret, index=df.index)).cumprod()*initial_cash
    buyhold = (1+pd.Series(ret, index=df.index)).cumprod()*initial_cash
    # stats
    daily = pd.Series(strat_ret, index=df.index)
    ann = (equity.iloc[-1]/equity.iloc[0])**(252/len(equity)) - 1 if len(equity)>1 else 0
    vol = daily.std()*np.sqrt(252)
    sharpe = (daily.mean()*252)/(vol+1e-12)
    roll_max = equity.cummax()
    mdd = ((roll_max - equity)/roll_max).max()
    stats = {
        "累计收益率": float(equity.iloc[-1]/equity.iloc[0]-1),
        "年化收益率": float(ann),
        "年化波动率": float(vol),
        "夏普比率": float(sharpe),
        "最大回撤": float(mdd),
        "最终净值": float(equity.iloc[-1])
    }
    return equity, buyhold, pd.Series(pos, index=df.index), stats

# ---------------- Main View: Chart ----------------
if df.empty:
    st.error("未获取到数据，请检查代码/网络/交易代码。")
    st.stop()

dfi = add_indicators(df)
dfi = gen_signals(dfi)
equity, buyhold, pos, stats = backtest(dfi)

st.subheader(f"🕯️ 主视图 K线图（{symbol}） — 点击图例可显示/隐藏图层")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=dfi.index, open=dfi['Open'], high=dfi['High'], low=dfi['Low'], close=dfi['Close'], name="K线"))
if show_sma:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi['SMA_fast'], name=f"SMA{sma_fast}", opacity=0.8))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi['SMA_slow'], name=f"SMA{sma_slow}", opacity=0.6))
if show_ema:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi['EMA_fast'], name=f"EMA{ema_fast}", opacity=0.6))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi['EMA_slow'], name=f"EMA{ema_slow}", opacity=0.6))
if show_boll:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi['BOLL_H'], name="BOLL 上轨", line=dict(dash="dot")))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi['BOLL_L'], name="BOLL 下轨", line=dict(dash="dot")))

# Buy/Sell markers based on position change
buys = dfi.index[(pos.shift(1)<=0) & (pos>0)]
sells = dfi.index[(pos.shift(1)>=0) & (pos<0)]
fig.add_trace(go.Scatter(x=buys, y=dfi.loc[buys, "Close"], mode="markers", name="买入", marker=dict(symbol="triangle-up", size=10)))
fig.add_trace(go.Scatter(x=sells, y=dfi.loc[sells, "Close"], mode="markers", name="卖出", marker=dict(symbol="triangle-down", size=10)))

fig.update_layout(xaxis_rangeslider_visible=False, height=700, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ---------------- Backtest Report in Main View ----------------
st.markdown("---")
c1, c2 = st.columns([1,1])
with c1:
    st.subheader("📋 回测绩效")
    st.json(stats)
with c2:
    st.subheader("💰 净值曲线")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=equity.index, y=equity.values, name="策略净值"))
    fig2.add_trace(go.Scatter(x=buyhold.index, y=buyhold.values, name="买入持有"))
    fig2.update_layout(height=350, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig2, use_container_width=True)

# 可下载CSV报告
report = pd.DataFrame({
    "date": equity.index,
    "equity": equity.values,
    "buyhold": buyhold.values,
    "pos": pos.values,
    "close": dfi["Close"].values
})
csv_bytes = report.to_csv(index=False).encode("utf-8")
st.download_button("📥 下载回测净值与持仓报告（CSV）", data=csv_bytes, file_name=f"{symbol.replace(':','_')}_backtest_report.csv", mime="text/csv")

# ---------------- Realtime Recommendation ----------------
st.markdown("---")
st.subheader("🧭 实时交易建议（非投资建议）")

last_close = float(dfi["Close"].iloc[-1])
row = dfi.iloc[-1]
atr = float(dfi["ATR"].iloc[-1]) if not np.isnan(dfi["ATR"].iloc[-1]) else np.nan

score = 0
reasons = []

# Trend - MA
if show_sma and "SMA_fast" in dfi.columns and "SMA_slow" in dfi.columns:
    if row["SMA_fast"] > row["SMA_slow"] and last_close > row["SMA_fast"]:
        score += 2; reasons.append("价格在均线之上，多头排列")
    elif row["SMA_fast"] < row["SMA_slow"] and last_close < row["SMA_fast"]:
        score -= 2; reasons.append("价格在均线之下，空头排列")

# MACD momentum
if show_macd and "MACD" in dfi.columns:
    if row["MACD"] > row["MACD_signal"] and row["MACD_hist"] > 0:
        score += 2; reasons.append("MACD 金叉且柱体为正")
    elif row["MACD"] < row["MACD_signal"] and row["MACD_hist"] < 0:
        score -= 2; reasons.append("MACD 死叉且柱体为负")

# RSI regime
if show_rsi and "RSI" in dfi.columns:
    if 45 <= row["RSI"] <= 70:
        score += 1; reasons.append("RSI 偏强但未过热")
    elif row["RSI"] >= rsi_sell:
        score -= 1; reasons.append("RSI 过热，警惕回撤")
    elif row["RSI"] <= rsi_buy:
        score += 1; reasons.append("RSI 超卖，反弹概率提升")

# Bollinger squeeze/breakout
if show_boll and "BOLL_H" in dfi.columns:
    if last_close > row["BOLL_H"]:
        score += 1; reasons.append("价格上破布林上轨，趋势延续可能")
    elif last_close < row["BOLL_L"]:
        score -= 1; reasons.append("价格跌破布林下轨，弱势")

decision = "观望"
if score >= 3:
    decision = "考虑买入/加仓"
elif score <= -2:
    decision = "考虑减仓/离场"

# TP/SL suggestion via ATR
# default multipliers
tp_mult = 2.0
sl_mult = 1.2
if np.isnan(atr) or atr == 0:
    # fallback: use recent volatility
    atr = float(dfi["Close"].pct_change().rolling(14).std().iloc[-1] * last_close)

if decision.startswith("考虑买入"):
    sl = last_close - sl_mult*atr
    tp = last_close + tp_mult*atr
elif decision.startswith("考虑减仓"):
    # for short bias
    sl = last_close + sl_mult*atr
    tp = last_close - tp_mult*atr
else:
    # neutral: propose tight risk box
    sl = last_close - 1.0*atr
    tp = last_close + 1.8*atr

colA, colB, colC = st.columns(3)
colA.metric("最新价", f"{last_close:,.4f}")
colB.metric("建议", decision)
colC.metric("评分", f"{score}")

st.write("**理由：** " + "；".join(reasons) if reasons else "指标不足，建议观望。")

st.info(f"建议止损：**{sl:,.4f}**   ｜   建议止盈：**{tp:,.4f}**  （基于 ATR≈{atr:,.4f}）")

