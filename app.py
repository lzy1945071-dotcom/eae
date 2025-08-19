
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
import requests
import ta
from datetime import datetime

st.set_page_config(layout="wide", page_title="Legend Quant Terminal Elite v3-fix")
st.title("💎 Legend Quant Terminal Elite v3-fix")

# ================= Sidebar =================
with st.sidebar:
    st.header("① 数据来源（免API优先）")
    data_source = st.selectbox("数据源", ["CoinGecko（免API）", "TokenInsight（无API自动回退）", "OKX 公共行情（免API）", "OKX API（需Key）"], index=0)
    api_key = st.text_input("API Key（仅当选择 OKX API 或 TokenInsight 需填）", type="password")

    st.header("② 标的与计价")
    symbol = st.text_input("个标（CoinGecko: coin_id；OKX: InstId；股票: 如 AAPL）", value="bitcoin")
    combo_symbols = st.text_area("组合标的（逗号分隔）", value="bitcoin,ethereum")
    quote_ccy = st.selectbox("计价货币", ["usd","usdt","cny","eur","btc"], index=0)

    st.header("③ 周期与长度")
    period = st.selectbox("历史区间", ["30d","90d","180d","365d","max"], index=2)
    okx_bar = st.selectbox("OKX K线周期", ["1m","5m","15m","1H","4H","1D","1W","1M"], index=5)

    st.header("📈 指标显示（图层开关）")
    show_sma = st.checkbox("SMA", True)
    sma_fast = st.number_input("SMA 快", 2, 300, 20)
    sma_slow = st.number_input("SMA 慢", 3, 600, 60)
    show_ema = st.checkbox("EMA", False)
    ema_fast = st.number_input("EMA 快", 2, 200, 12)
    ema_slow = st.number_input("EMA 慢", 3, 400, 26)
    show_boll = st.checkbox("布林带", False)
    boll_win = st.number_input("布林窗口", 5, 100, 20)
    show_macd = st.checkbox("MACD", True)
    macd_sig = st.number_input("MACD 信号线", 3, 20, 9)
    show_rsi = st.checkbox("RSI", True)
    rsi_win = st.number_input("RSI 窗口", 2, 60, 14)
    rsi_buy = st.number_input("RSI 超卖<=买入", 1, 99, 30)
    rsi_sell = st.number_input("RSI 超买>=卖出", 40, 99, 70)

    combine_mode = st.selectbox("信号合成", ["任一触发（OR）", "多数投票（Majority）", "全体一致（AND）"], index=1)

    st.header("💼 回测参数")
    initial_cash = st.number_input("初始资金", min_value=100.0, value=10000.0, step=100.0)
    fee_bps = st.number_input("手续费（基点）", 0, 200, 10)
    slip_bps = st.number_input("滑点（基点）", 0, 200, 5)

# ================= Data Loaders =================
@st.cache_data(ttl=1200)
def load_coingecko_ohlc(coin_id: str, vs: str, days: str):
    days_map = {"30d":"30", "90d":"90", "180d":"180", "365d":"365", "max":"max"}
    days_val = days_map.get(days, "180")
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": vs, "days": days_val}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    arr = r.json()
    if not isinstance(arr, list) or len(arr)==0:
        raise RuntimeError("CoinGecko 无返回")
    rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in arr]
    df = pd.DataFrame(rows, columns=["Date","Open","High","Low","Close"]).set_index("Date")
    return df

@st.cache_data(ttl=1200)
def load_okx_public(instId: str, bar: str="1D", limit: int=1000):
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": instId, "bar": bar, "limit": str(limit)}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    arr = r.json().get("data", [])
    if not arr:
        raise RuntimeError("OKX 公共行情无返回")
    rows = []
    for a in reversed(arr):
        ts = int(a[0]); o=float(a[1]); h=float(a[2]); l=float(a[3]); c=float(a[4])
        rows.append((pd.to_datetime(ts, unit="ms"), o,h,l,c))
    df = pd.DataFrame(rows, columns=["Date","Open","High","Low","Close"]).set_index("Date")
    return df

@st.cache_data(ttl=1200)
def load_tokeninsight_free_like(symbol: str, vs: str, days: str):
    # 占位说明：TokenInsight 官方无免API OHLC端点，默认回退到 CoinGecko
    df = load_coingecko_ohlc(symbol, vs, days)
    return df

COIN_ID_MAP = {
    "btc":"bitcoin", "btc-usd":"bitcoin", "btc-usdt":"bitcoin", "xbt":"bitcoin",
    "eth":"ethereum", "eth-usd":"ethereum", "eth-usdt":"ethereum",
    "sol":"solana", "sol-usdt":"solana", "sol-usd":"solana",
    "ada":"cardano", "ada-usdt":"cardano",
    "doge":"dogecoin", "xrp":"ripple", "dot":"polkadot", "ltc":"litecoin"
}
def normalize_coin_id(s: str):
    sid = s.strip().lower()
    return COIN_ID_MAP.get(sid, sid)

def load_data_router(source: str, symbol: str, vs: str, period: str, okx_bar: str):
    if source == "CoinGecko（免API）":
        coin_id = normalize_coin_id(symbol)
        return load_coingecko_ohlc(coin_id, vs, period)
    elif source == "OKX 公共行情（免API）":
        return load_okx_public(symbol, okx_bar)
    elif source == "OKX API（需Key）":
        if not api_key:
            st.info("未填写 OKX API，已使用 OKX 公共行情代替。")
            return load_okx_public(symbol, okx_bar)
        else:
            return load_okx_public(symbol, okx_bar)
    else:
        if not api_key:
            st.info("TokenInsight 未提供 API Key，自动回退到 CoinGecko 免API数据。")
            coin_id = normalize_coin_id(symbol)
            return load_tokeninsight_free_like(coin_id, vs, period)
        else:
            try:
                df = load_tokeninsight_free_like(normalize_coin_id(symbol), vs, period)
                return df
            except Exception:
                coin_id = normalize_coin_id(symbol)
                return load_coingecko_ohlc(coin_id, vs, period)

# ================= Indicators & Signals =================
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
    atr = ta.volatility.AverageTrueRange(high=out["High"], low=out["Low"], close=out["Close"], window=14)
    out["ATR"] = atr.average_true_range()
    return out

def gen_signals(df):
    s_cols = []
    if show_sma and {"SMA_fast","SMA_slow"} <= set(df.columns):
        s = np.where(df["SMA_fast"] > df["SMA_slow"], 1, -1)
        df["SIG_SMA"] = s; s_cols.append("SIG_SMA")
    if show_ema and {"EMA_fast","EMA_slow"} <= set(df.columns):
        s = np.where(df["EMA_fast"] > df["EMA_slow"], 1, -1)
        df["SIG_EMA"] = s; s_cols.append("SIG_EMA")
    if show_macd and {"MACD","MACD_signal"} <= set(df.columns):
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
    daily = pd.Series(strat_ret, index=df.index)
    ann = (equity.iloc[-1]/equity.iloc[0])**(252/max(1,len(equity))) - 1 if len(equity)>1 else 0
    vol = daily.std()*np.sqrt(252) if len(daily)>1 else 0.0
    sharpe = (daily.mean()*252)/(vol+1e-12) if vol>0 else 0.0
    roll_max = equity.cummax(); mdd = ((roll_max - equity)/roll_max).max() if len(equity)>1 else 0.0
    stats = {"累计收益率": float(equity.iloc[-1]/equity.iloc[0]-1) if len(equity)>1 else 0.0,
             "年化收益率": float(ann),
             "年化波动率": float(vol),
             "夏普比率": float(sharpe),
             "最大回撤": float(mdd),
             "最终净值": float(equity.iloc[-1])}
    return equity, buyhold, pd.Series(pos, index=df.index), stats

# ================= Main =================
try:
    df = load_data_router(data_source, symbol, quote_ccy, period, okx_bar)
except Exception as e:
    st.error(f"拉取数据失败：{e}")
    st.stop()

if df.empty or not {"Open","High","Low","Close"} <= set(df.columns):
    st.error("数据为空或缺少OHLC，请检查数据源与标的格式。CoinGecko需要 coin_id（如 bitcoin、ethereum）；OKX 需 InstId（如 BTC-USDT）。")
    st.stop()

dfi = add_indicators(df)
dfi = gen_signals(dfi)
equity, buyhold, pos, stats = backtest(dfi)

st.subheader(f"🕯️ 主视图 K线图（{symbol} / {data_source}）— 侧栏勾选或点图例开关图层")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=dfi.index, open=dfi["Open"], high=dfi["High"], low=dfi["Low"], close=dfi["Close"], name="K线"))
if show_sma and "SMA_fast" in dfi.columns:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["SMA_fast"], name=f"SMA{sma_fast}", opacity=0.9))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["SMA_slow"], name=f"SMA{sma_slow}", opacity=0.6))
if show_ema and "EMA_fast" in dfi.columns:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["EMA_fast"], name=f"EMA{ema_fast}", opacity=0.6))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["EMA_slow"], name=f"EMA{ema_slow}", opacity=0.6))
if show_boll and "BOLL_H" in dfi.columns:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["BOLL_H"], name="BOLL 上轨", line=dict(dash="dot")))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["BOLL_L"], name="BOLL 下轨", line=dict(dash="dot")))
# markers
buys = dfi.index[(pos.shift(1)<=0) & (pos>0)]
sells = dfi.index[(pos.shift(1)>=0) & (pos<0)]
fig.add_trace(go.Scatter(x=buys, y=dfi.loc[buys,"Close"], mode="markers", name="买入", marker=dict(symbol="triangle-up", size=10)))
fig.add_trace(go.Scatter(x=sells, y=dfi.loc[sells,"Close"], mode="markers", name="卖出", marker=dict(symbol="triangle-down", size=10)))
fig.update_layout(xaxis_rangeslider_visible=False, height=720, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
c1,c2 = st.columns([1,1])
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

report = pd.DataFrame({"date": equity.index, "equity": equity.values, "buyhold": buyhold.values, "pos": pos.values, "close": dfi["Close"].values})
st.download_button("📥 下载回测报告（CSV）", data=report.to_csv(index=False).encode("utf-8"), file_name=f"{symbol}_backtest.csv", mime="text/csv")

# ============ Realtime Recommendation ============
st.markdown("---")
st.subheader("🧭 实时交易建议（非投资建议）")
last_close = float(dfi["Close"].iloc[-1])
row = dfi.iloc[-1]
atr = float(dfi["ATR"].iloc[-1]) if "ATR" in dfi.columns and not np.isnan(dfi["ATR"].iloc[-1]) else float(dfi["Close"].pct_change().rolling(14).std().iloc[-1] * last_close)

score = 0; reasons = []
if show_sma and {"SMA_fast","SMA_slow"} <= set(dfi.columns):
    if row["SMA_fast"] > row["SMA_slow"] and last_close > row["SMA_fast"]:
        score += 2; reasons.append("多头排列且价在均线上")
    elif row["SMA_fast"] < row["SMA_slow"] and last_close < row["SMA_fast"]:
        score -= 2; reasons.append("空头排列且价在均线下")
if show_macd and {"MACD","MACD_signal","MACD_hist"} <= set(dfi.columns):
    if row["MACD"] > row["MACD_signal"] and row["MACD_hist"] > 0:
        score += 2; reasons.append("MACD 金叉且柱正")
    elif row["MACD"] < row["MACD_signal"] and row["MACD_hist"] < 0:
        score -= 2; reasons.append("MACD 死叉且柱负")
if show_rsi and "RSI" in dfi.columns:
    if 45 <= row["RSI"] <= 70:
        score += 1; reasons.append("RSI 偏强但未过热")
    elif row["RSI"] >= rsi_sell:
        score -= 1; reasons.append("RSI 过热")
    elif row["RSI"] <= rsi_buy:
        score += 1; reasons.append("RSI 超卖")

decision = "观望"
if score >= 3:
    decision = "考虑买入/加仓"
elif score <= -2:
    decision = "考虑减仓/离场"

tp_mult, sl_mult = 2.0, 1.2
if decision.startswith("考虑买入"):
    sl = last_close - sl_mult*atr; tp = last_close + tp_mult*atr
elif decision.startswith("考虑减仓"):
    sl = last_close + sl_mult*atr; tp = last_close - tp_mult*atr
else:
    sl = last_close - 1.0*atr; tp = last_close + 1.8*atr

a,b,c = st.columns(3)
a.metric("最新价", f"{last_close:,.4f}")
b.metric("建议", decision)
c.metric("评分", f"{score}")
st.write("**理由：** " + ("；".join(reasons) if reasons else "指标不足，建议观望。"))
st.info(f"建议止损：**{sl:,.4f}** ｜ 建议止盈：**{tp:,.4f}**  （ATR≈{atr:,.4f}）")
