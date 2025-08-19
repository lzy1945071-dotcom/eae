
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import ta

st.set_page_config(page_title="Legend Quant Terminal Elite v3 FIX8", layout="wide")
st.title("💎 Legend Quant Terminal Elite v3 FIX8")

# ---------------------- Sidebar: Data & UI ----------------------
st.sidebar.header("① 数据来源与标的")
source = st.sidebar.selectbox("数据来源", ["CoinGecko（免API）", "OKX 公共行情（免API）", "Yahoo Finance"], index=0)

if source == "CoinGecko（免API）":
    symbol = st.sidebar.selectbox("个标（CoinGecko coin_id）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标（CoinGecko coin_id 可多选）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], default=["bitcoin","ethereum"])
    interval = st.sidebar.selectbox(
        "K线周期",
        ["1d（映射）","1w（映射）","1M（映射）","max（映射）"],
        index=0,
        help="CoinGecko OHLC 仅支持 1/7/14/30/90/180/365/max 天范围的固定K线。若/ohlc不可用将自动回退到/market_chart并聚合。"
    )
elif source == "OKX 公共行情（免API）":
    symbol = st.sidebar.selectbox("个标（OKX InstId）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标（OKX InstId 可多选）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], default=["BTC-USDT","ETH-USDT"])
    interval = st.sidebar.selectbox("K线周期", ["1m","5m","15m","30m","1H","4H","12H","1D","1W","1M"], index=5)
else:
    symbol = st.sidebar.selectbox("个标（美股/A股）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], index=0)
    combo_symbols = st.sidebar.multiselect("组合标（可多选）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], default=["AAPL","MSFT"])
    interval = st.sidebar.selectbox("K线周期", ["1d","1wk","1mo"], index=0, help="yfinance 限制可用周期。")

st.sidebar.header("② 指标开关")
show_ma = st.sidebar.checkbox("移动平均线 (MA20/50)", True)
show_boll = st.sidebar.checkbox("布林带 (20, 2σ)", False)
show_macd = st.sidebar.checkbox("MACD", True)
show_rsi = st.sidebar.checkbox("RSI", True)

st.sidebar.header("③ 指标参数推荐说明")
st.sidebar.markdown('''
**加密货币**：  
- MACD：(**8, 21, 5**)  
- RSI：超买≈**90**，超卖≈**73**（更宽容）  
- MA：**20/50**  
- BOLL：**20 ± 2σ**  

**美股**：  
- MACD：**12, 26, 9**（经典）  
- RSI：超买**70** / 超卖**30**  
- MA：**50/200** 长趋势  
- BOLL：**20 ± 2σ**  

**A股**：  
- MACD：**10, 30, 9**  
- RSI：超买**80** / 超卖**20**  
- MA：**5/10/30**  
''')

st.sidebar.header("④ 风控面板（参数）")
account_value = st.sidebar.number_input("账户总资金", min_value=1000.0, value=100000.0, step=1000.0)
risk_pct = st.sidebar.slider("单笔风险（%）", 0.1, 2.0, 0.5, 0.1)
leverage = st.sidebar.slider("杠杆倍数", 1, 10, 1, 1)
daily_loss_limit = st.sidebar.number_input("每日亏损阈值（%）", min_value=0.5, value=2.0, step=0.5)
weekly_loss_limit = st.sidebar.number_input("每周亏损阈值（%）", min_value=1.0, value=5.0, step=0.5)
trade_loss_limit = st.sidebar.number_input("单笔最大亏损阈值（%）", min_value=0.5, value=1.5, step=0.5)

# ---------------------- Data Loaders ----------------------
def _cg_days_from_interval(sel: str) -> str:
    if sel.startswith("1d"):
        return "180"
    if sel.startswith("1w"):
        return "365"
    if sel.startswith("1M"):
        return "365"
    if sel.startswith("max"):
        return "max"
    return "180"

@st.cache_data(ttl=900)
def load_coingecko_ohlc_robust(coin_id: str, interval_sel: str):
    days = _cg_days_from_interval(interval_sel)
    # 1) Try /ohlc
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        r = requests.get(url, params={"vs_currency": "usd", "days": days}, timeout=20)
        if r.status_code == 200:
            arr = r.json()
            if isinstance(arr, list) and len(arr) > 0:
                rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in arr]
                df = pd.DataFrame(rows, columns=["Date","Open","High","Low","Close"]).set_index("Date")
                return df
    except Exception:
        pass
    # 2) Fallback to market_chart (prices) -> daily OHLC via resample
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency":"usd", "days": days if days != "max" else "365"}
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        prices = data.get("prices", [])
        if prices:
            s = pd.Series(
                [float(p[1]) for p in prices],
                index=pd.to_datetime([int(p[0]) for p in prices], unit="ms"),
                name="price"
            ).sort_index()
            ohlc = s.resample("1D").agg(["first","max","min","last"]).dropna()
            ohlc.columns = ["Open","High","Low","Close"]
            return ohlc
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=900)
def load_okx_public(instId: str, bar: str):
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": instId, "bar": bar, "limit": "800"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return pd.DataFrame()
    rows = []
    for a in reversed(data):  # OKX 返回最新在前，反转为时间升序
        ts = int(a[0]); o=float(a[1]); h=float(a[2]); l=float(a[3]); c=float(a[4]); v=float(a[5])
        rows.append((pd.to_datetime(ts, unit="ms"), o,h,l,c,v))
    df = pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")
    return df

@st.cache_data(ttl=900)
def load_yf(symbol: str, interval_sel: str):
    interval_map = {"1d":"1d","1wk":"1wk","1mo":"1mo"}
    interval = interval_map.get(interval_sel, "1d")
    df = yf.download(symbol, period="5y", interval=interval, progress=False, auto_adjust=False)
    if not df.empty:
        df = df[["Open","High","Low","Close","Volume"]].dropna()
    return df

def load_router(source, symbol, interval_sel):
    if source == "CoinGecko（免API）":
        return load_coingecko_ohlc_robust(symbol, interval_sel)
    elif source == "OKX 公共行情（免API）":
        return load_okx_public(symbol, interval_sel)
    else:
        return load_yf(symbol, interval_sel)

df = load_router(source, symbol, interval)

if df.empty or not set(["Open","High","Low","Close"]).issubset(df.columns):
    st.error("数据为空或字段缺失：请更换数据源/周期或稍后重试（CoinGecko 可能限流）。")
    st.stop()

# ---------------------- Indicators ----------------------
def add_indicators(df):
    out = df.copy()
    close = out["Close"]
    out["MA20"] = close.rolling(20).mean()
    out["MA50"] = close.rolling(50).mean()
    mb = close.rolling(20).mean()
    std = close.rolling(20).std()
    out["BOLL_U"] = mb + 2*std
    out["BOLL_L"] = mb - 2*std
    if source in ["CoinGecko（免API）", "OKX 公共行情（免API）"]:
        fast, slow, sig = 8, 21, 5
    else:
        fast, slow, sig = 12, 26, 9
    macd_ind = ta.trend.MACD(close, window_slow=slow, window_fast=fast, window_sign=sig)
    out["MACD"] = macd_ind.macd()
    out["MACD_signal"] = macd_ind.macd_signal()
    out["MACD_hist"] = macd_ind.macd_diff()
    out["RSI"] = ta.momentum.RSIIndicator(close, window=14).rsi()
    out["ATR"] = ta.volatility.AverageTrueRange(high=out["High"], low=out["Low"], close=out["Close"], window=14).average_true_range()
    return out

dfi = add_indicators(df)

# ---------------------- Chart ----------------------
st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=dfi.index, open=dfi["Open"], high=dfi["High"], low=dfi["Low"], close=dfi["Close"], name="K线"))
if show_ma:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA20"], name="MA20", mode="lines"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA50"], name="MA50", mode="lines"))
if show_boll:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["BOLL_U"], name="BOLL 上轨", mode="lines"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["BOLL_L"], name="BOLL 下轨", mode="lines"))
if show_macd:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD"], name="MACD", mode="lines", yaxis="y2"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD_signal"], name="MACD信号", mode="lines", yaxis="y2"))
if show_rsi:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["RSI"], name="RSI", mode="lines", yaxis="y3"))
fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=720,
    hovermode="x unified",
    yaxis_domain=[0.25, 1.0],
    yaxis2=dict(domain=[0.13,0.24], showgrid=False, title="MACD"),
    yaxis3=dict(domain=[0.0,0.12], showgrid=False, title="RSI", range=[0,100])
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------- Strategy Suggestion ----------------------
st.markdown("---")
st.subheader("🧭 实时策略建议（非投资建议）")
last = dfi.dropna().iloc[-1]
price = float(last["Close"])
score = 0; reasons = []
if last["MA20"] > last["MA50"] and price > last["MA20"]:
    score += 2; reasons.append("MA20>MA50 且价在MA20上，多头趋势")
elif last["MA20"] < last["MA50"] and price < last["MA20"]:
    score -= 2; reasons.append("MA20<MA50 且价在MA20下，空头趋势")
if last["MACD"] > last["MACD_signal"] and last["MACD_hist"] > 0:
    score += 2; reasons.append("MACD 金叉且柱为正")
elif last["MACD"] < last["MACD_signal"] and last["MACD_hist"] < 0:
    score -= 2; reasons.append("MACD 死叉且柱为负")
if last["RSI"] >= 70:
    score -= 1; reasons.append("RSI 过热")
elif last["RSI"] <= 30:
    score += 1; reasons.append("RSI 超卖")
decision = "观望"
if score >= 3: decision = "买入/加仓"
elif score <= -2: decision = "减仓/离场"
atr = float(last["ATR"]) if not np.isnan(last["ATR"]) else float(dfi["Close"].pct_change().rolling(14).std().iloc[-1]*price)
tp = price + 2.0*atr if decision != "减仓/离场" else price - 2.0*atr
sl = price - 1.2*atr if decision != "减仓/离场" else price + 1.2*atr
c1,c2,c3,c4 = st.columns(4)
c1.metric("最新价", f"{price:,.4f}")
c2.metric("建议", decision)
c3.metric("评分", str(score))
c4.metric("ATR", f"{atr:,.4f}")
st.write("**依据**：", "；".join(reasons) if reasons else "信号不明确，建议观望。")
st.info(f"建议止损：**{sl:,.4f}** ｜ 建议止盈：**{tp:,.4f}**")

# ---------------------- Simple Backtest & Stats ----------------------
def simple_backtest(df):
    df = df.dropna().copy()
    sig = np.where((df["MA20"]>df["MA50"]) & (df["MACD"]>df["MACD_signal"]), 1,
                   np.where((df["MA20"]<df["MA50"]) & (df["MACD"]<df["MACD_signal"]), -1, 0))
    df["sig"] = sig
    ret = df["Close"].pct_change().fillna(0.0).values
    pos = pd.Series(sig, index=df.index).replace(0, np.nan).ffill().fillna(0).values
    strat_ret = pos * ret
    equity = (1+pd.Series(strat_ret, index=df.index)).cumprod()
    pnl = []
    last_side = 0; entry_price = None
    for side,p in zip(pos, df["Close"].values):
        if side!=0 and last_side==0:
            entry_price = p; last_side = side
        elif side==0 and last_side!=0 and entry_price is not None:
            pnl.append((p/entry_price-1)*last_side); last_side=0; entry_price=None
    pnl = pd.Series(pnl) if len(pnl)>0 else pd.Series(dtype=float)
    win_rate = float((pnl>0).mean()) if len(pnl)>0 else 0.0
    roll_max = equity.cummax(); mdd = float(((roll_max - equity)/roll_max).max()) if len(equity)>0 else 0.0
    return equity, pnl, win_rate, mdd, pd.Series(strat_ret, index=df.index)

equity, pnl, win_rate, mdd, strat_ret = simple_backtest(dfi)

st.markdown("---")
st.subheader("📈 组合策略胜率统计面板")
c1, c2, c3 = st.columns(3)
c1.metric("历史胜率", f"{win_rate*100:.2f}%")
c2.metric("最大回撤", f"{mdd*100:.2f}%")
total_ret = equity.iloc[-1]/equity.iloc[0]-1 if len(equity)>1 else 0.0
c3.metric("累计收益", f"{total_ret*100:.2f}%")
fig_eq = go.Figure()
fig_eq.add_trace(go.Scatter(x=equity.index, y=equity.values, mode="lines", name="策略净值"))
fig_eq.update_layout(height=280, xaxis_rangeslider_visible=False)
st.plotly_chart(fig_eq, use_container_width=True)
if len(pnl)>0:
    fig_hist = px.histogram(pnl, nbins=20, title="单笔收益分布")
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("暂无可统计的交易样本。")

# ---------------------- Risk Panel: Position & Exposure ----------------------
st.markdown("---")
st.subheader("🛡️ 风控面板（结果）")
last_close = price
atr_for_pos = atr if atr and atr>0 else (dfi["Close"].pct_change().rolling(14).std().iloc[-1]*last_close)
stop_distance = atr_for_pos / max(last_close, 1e-9)
risk_amount = account_value * (risk_pct/100.0)
position_value = risk_amount / max(stop_distance, 1e-6) / max(leverage,1)
position_value = min(position_value, account_value * 1.0)
position_size = position_value / max(last_close, 1e-9)
rc1, rc2, rc3 = st.columns(3)
rc1.metric("建议持仓名义价值", f"{position_value:,.2f}")
rc2.metric("建议仓位数量", f"{position_size:,.6f}")
rc3.metric("单笔风险金额", f"{risk_amount:,.2f}")
recent_dd = (equity.cummax()-equity)/equity.cummax()
curr_dd = float(recent_dd.iloc[-1]) if len(recent_dd)>0 else 0.0
alerts = []
if curr_dd*100 >= daily_loss_limit: alerts.append(f"当前回撤 {curr_dd*100:.2f}% ≥ 每日亏损阈值 {daily_loss_limit:.2f}%")
if curr_dd*100 >= weekly_loss_limit: alerts.append(f"当前回撤 {curr_dd*100:.2f}% ≥ 每周亏损阈值 {weekly_loss_limit:.2f}%")
if alerts:
    st.error("⚠️ 风险警示：\n- " + "\n- ".join(alerts))
else:
    st.success("风险状态：正常")

st.subheader("📊 组合风险暴露建议（波动率配比）")
def get_close_series(sym):
    try:
        if source == "CoinGecko（免API）":
            d = load_coingecko_ohlc_robust(sym, interval)
        elif source == "OKX 公共行情（免API）":
            d = load_okx_public(sym, interval)
        else:
            d = load_yf(sym, interval)
        return d["Close"].rename(sym) if not d.empty else None
    except Exception:
        return None

series_list = []
for s in combo_symbols:
    se = get_close_series(s)
    if se is not None and not se.empty:
        series_list.append(se)
if series_list:
    closes = pd.concat(series_list, axis=1).dropna()
    vols = closes.pct_change().rolling(30).std().iloc[-1].replace(0, np.nan)
    inv_vol = 1.0/vols
    weights = inv_vol/np.nansum(inv_vol)
    w_df = pd.DataFrame({"symbol": weights.index, "weight": weights.values})
    fig_pie = px.pie(w_df, names="symbol", values="weight", title="建议权重（低波动更高权重）")
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("组合标数据不足，无法计算风险暴露建议。")
