# app.py — Legend Quant Terminal Elite v3 FIX10 (TV风格 + MACD副图 + 实时策略增强 + API源入口)
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import ta

st.set_page_config(page_title="Legend Quant Terminal Elite v3 FIX10", layout="wide")
st.title("💎 Legend Quant Terminal Elite v3 FIX10")

# ========================= Sidebar: ① 数据来源与标的 =========================
st.sidebar.header("① 数据来源与标的")
source = st.sidebar.selectbox(
    "数据来源",
    [
         "OKX 公共行情（免API）",
        "CoinGecko（免API）",
        "OKX API（可填API基址）",
        "TokenInsight API 模式（可填API基址）",
        "Yahoo Finance（美股/A股）",
    ],
    index=0
)

api_base = ""
api_key = ""
api_secret = ""
api_passphrase = ""

if source in ["OKX API（可填API基址）", "TokenInsight API 模式（可填API基址）"]:
    st.sidebar.markdown("**API 连接设置**")
    api_base = st.sidebar.text_input("API 基址（留空用默认公共接口）", value="")
    if source == "OKX API（可填API基址）":
        with st.sidebar.expander("（可选）OKX API 认证信息"):
            api_key = st.text_input("OKX-API-KEY", value="", type="password")
            api_secret = st.text_input("OKX-API-SECRET", value="", type="password")
            api_passphrase = st.text_input("OKX-API-PASSPHRASE", value="", type="password")

# 标的与周期（首次打开默认：仅个标；组合标留空）
if source in ["CoinGecko（免API）", "TokenInsight API 模式（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（CoinGecko coin_id）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标（可多选，默认留空）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], default=[])
    interval = st.sidebar.selectbox("K线周期（映射）", ["1d","1w","1M","max"], index=0, help="CoinGecko/TokenInsight 免费接口多为日级/周级聚合，不提供细分分钟线。")
elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（OKX InstId）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], index=1)
    combo_symbols = st.sidebar.multiselect("组合标（可多选，默认留空）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1m","3m","5m","15m","30m","1H","2H","4H","6H","12H","1D","1W","1M"], index=10)
else:
    symbol = st.sidebar.selectbox("个标（美股/A股）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], index=0)
    combo_symbols = st.sidebar.multiselect("组合标（可多选，默认留空）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], default=[])
    interval = st.sidebar.selectbox("K线周期", ["1d","1wk","1mo"], index=0)

# ========================= Sidebar: ③ 指标与参数（顶级交易员常用） =========================
st.sidebar.header("③ 指标与参数（顶级交易员常用）")

# MA / EMA
use_ma = st.sidebar.checkbox("MA（简单均线）", True)
ma_periods_text = st.sidebar.text_input("MA 周期（逗号分隔）", value="20,50")
use_ema = st.sidebar.checkbox("EMA（指数均线）", False)
ema_periods_text = st.sidebar.text_input("EMA 周期（逗号分隔）", value="200")

# Bollinger
use_boll = st.sidebar.checkbox("布林带（BOLL）", False)
boll_window = st.sidebar.number_input("BOLL 窗口", min_value=5, value=20, step=1)
boll_std = st.sidebar.number_input("BOLL 标准差倍数", min_value=1.0, value=2.0, step=0.5)

# MACD（要求默认 12/26/9）
use_macd = st.sidebar.checkbox("MACD（副图）", True)
macd_fast = st.sidebar.number_input("MACD 快线", min_value=2, value=12, step=1)
macd_slow = st.sidebar.number_input("MACD 慢线", min_value=5, value=26, step=1)
macd_sig = st.sidebar.number_input("MACD 信号线", min_value=2, value=9, step=1)

# RSI（副图）
use_rsi = st.sidebar.checkbox("RSI（副图）", True)
rsi_window = st.sidebar.number_input("RSI 窗口", min_value=5, value=14, step=1)

# ATR（用于止盈止损与风控）
use_atr = st.sidebar.checkbox("ATR（用于风险/止盈止损）", True)
atr_window = st.sidebar.number_input("ATR 窗口", min_value=5, value=14, step=1)

# ========================= Sidebar: ④ 参数推荐（说明） =========================
st.sidebar.header("④ 参数推荐（说明）")
st.sidebar.markdown('''
**加密货币**：MACD **12/26/9**；RSI **14**（阈：90/73更宽容）；BOLL **20 ± 2σ**；MA **20/50**；EMA **200**  
**美股**：MACD **12/26/9**；RSI **14**（阈：70/30）；MA **50/200**  
**A股**：MACD **10/30/9**；RSI **14**（阈：80/20）；MA **5/10/30**
''')

# ========================= Sidebar: 风控参数 =========================
st.sidebar.header("⑤ 风控参数")
account_value = st.sidebar.number_input("账户总资金", min_value=1000.0, value=100000.0, step=1000.0)
risk_pct = st.sidebar.slider("单笔风险（%）", 0.1, 2.0, 0.5, 0.1)
leverage = st.sidebar.slider("杠杆倍数", 1, 10, 1, 1)
daily_loss_limit = st.sidebar.number_input("每日亏损阈值（%）", min_value=0.5, value=2.0, step=0.5)
weekly_loss_limit = st.sidebar.number_input("每周亏损阈值（%）", min_value=1.0, value=5.0, step=0.5)

# ========================= Data Loaders =========================
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
    # Try /ohlc
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
    # Fallback /market_chart -> resample to daily OHLC
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
def load_tokeninsight_ohlc(api_base_url: str, coin_id: str, interval_sel: str):
    """
    兼容 TokenInsight API 模式（占位实现）：
    - 若未填写 api_base_url 或请求失败，自动回退到 CoinGecko。
    - 如需对接正式 TI 接口，请将此函数替换为对应的 K 线 API 路由与字段解析。
    """
    if not api_base_url:
        return load_coingecko_ohlc_robust(coin_id, interval_sel)
    try:
        # 这里假设存在类似 /ohlc?symbol=xxx&period=1d 的路由，仅示例
        url = f"{api_base_url.rstrip('/')}/ohlc"
        r = requests.get(url, params={"symbol": coin_id, "period": "1d"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        # 需要根据真实字段做解析：此处示例期望 [[ts, o,h,l,c], ...]
        if isinstance(data, list) and data:
            rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in data]
            df = pd.DataFrame(rows, columns=["Date","Open","High","Low","Close"]).set_index("Date")
            return df
    except Exception:
        pass
    return load_coingecko_ohlc_robust(coin_id, interval_sel)

@st.cache_data(ttl=900)
def load_okx_public(instId: str, bar: str, base_url: str = ""):
    url = (base_url.rstrip('/') if base_url else "https://www.okx.com") + "/api/v5/market/candles"
    params = {"instId": instId, "bar": bar, "limit": "1000"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return pd.DataFrame()
    rows = []
    for a in reversed(data):  # 最新在前，反转为升序
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

def load_router(source, symbol, interval_sel, api_base=""):
    if source == "CoinGecko（免API）":
        return load_coingecko_ohlc_robust(symbol, interval_sel)
    elif source == "TokenInsight API 模式（可填API基址）":
        return load_tokeninsight_ohlc(api_base, symbol, interval_sel)
    elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
        base = api_base if source == "OKX API（可填API基址）" else ""
        return load_okx_public(symbol, interval_sel, base_url=base)
    else:
        return load_yf(symbol, interval_sel)

df = load_router(source, symbol, interval, api_base)

if df.empty or not set(["Open","High","Low","Close"]).issubset(df.columns):
    st.error("数据为空或字段缺失：请更换数据源/周期，或稍后重试（免费源可能限流）。")
    st.stop()

# ========================= Indicators =========================
def parse_int_list(text):
    try:
        lst = [int(x.strip()) for x in text.split(",") if x.strip()]
        return [x for x in lst if x > 0]
    except Exception:
        return []

def add_indicators(df):
    out = df.copy()
    close = out["Close"]
    high = out["High"]
    low = out["Low"]
    if "Volume" not in out.columns:
        out["Volume"] = np.nan

    # MA / EMA
    if use_ma:
        for p in parse_int_list(ma_periods_text):
            out[f"MA{p}"] = close.rolling(p).mean()
    if use_ema:
        for p in parse_int_list(ema_periods_text):
            out[f"EMA{p}"] = ta.trend.EMAIndicator(close=close, window=p).ema_indicator()

    # Bollinger
    if use_boll:
        boll = ta.volatility.BollingerBands(close=close, window=int(boll_window), window_dev=float(boll_std))
        out["BOLL_M"] = boll.bollinger_mavg()
        out["BOLL_U"] = boll.bollinger_hband()
        out["BOLL_L"] = boll.bollinger_lband()

    # MACD
    if use_macd:
        macd_ind = ta.trend.MACD(close, window_slow=int(macd_slow), window_fast=int(macd_fast), window_sign=int(macd_sig))
        out["MACD"] = macd_ind.macd()
        out["MACD_signal"] = macd_ind.macd_signal()
        out["MACD_hist"] = macd_ind.macd_diff()

    # RSI
    if use_rsi:
        out["RSI"] = ta.momentum.RSIIndicator(close, window=int(rsi_window)).rsi()

    # ATR
    if use_atr:
        out["ATR"] = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=int(atr_window)).average_true_range()

    return out

dfi = add_indicators(df).dropna(how="all")

# ========================= TradingView 风格图表 =========================
st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")

fig = go.Figure()

# --- 主图：K线 + 叠加指标（MA/EMA/BOLL） ---
fig.add_trace(go.Candlestick(
    x=dfi.index, open=dfi["Open"], high=dfi["High"], low=dfi["Low"], close=dfi["Close"], name="K线"
))

# 叠加：MA/EMA
if use_ma:
    for p in parse_int_list(ma_periods_text):
        col = f"MA{p}"
        if col in dfi.columns:
            fig.add_trace(go.Scatter(x=dfi.index, y=dfi[col], mode="lines", name=col, yaxis="y"))
if use_ema:
    for p in parse_int_list(ema_periods_text):
        col = f"EMA{p}"
        if col in dfi.columns:
            fig.add_trace(go.Scatter(x=dfi.index, y=dfi[col], mode="lines", name=col, yaxis="y"))

# 叠加：BOLL
if use_boll:
    for col, nm in [("BOLL_U","BOLL 上轨"), ("BOLL_M","BOLL 中轨"), ("BOLL_L","BOLL 下轨")]:
        if col in dfi.columns:
            fig.add_trace(go.Scatter(x=dfi.index, y=dfi[col], mode="lines", name=nm, yaxis="y"))

# --- 成交量副图：红涨绿跌 ---
# 颜色：收涨为绿色，收跌为红色（参考TV）
vol_colors = np.where(dfi["Close"] >= dfi["Open"], "rgba(38,166,91,0.7)", "rgba(239,83,80,0.7)")
if "Volume" in dfi.columns and not dfi["Volume"].isna().all():
    fig.add_trace(go.Bar(x=dfi.index, y=dfi["Volume"], name="成交量", yaxis="y2", marker_color=vol_colors))

# --- MACD 副图 ---
if use_macd and all(c in dfi.columns for c in ["MACD","MACD_signal","MACD_hist"]):
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD"], name="MACD", yaxis="y3", mode="lines"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD_signal"], name="Signal", yaxis="y3", mode="lines"))
    fig.add_trace(go.Bar(x=dfi.index, y=dfi["MACD_hist"], name="MACD 柱", yaxis="y3", opacity=0.4))

# --- RSI 副图 ---
if use_rsi and "RSI" in dfi.columns:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["RSI"], name="RSI", yaxis="y4", mode="lines"))

# 轴域：主图（价格）在最上；下方依次 成交量 → MACD → RSI
fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=900,
    hovermode="x unified",
    # domains: y (price), y2 (volume), y3 (macd), y4 (rsi)
    yaxis=dict(domain=[0.58, 1.0], title="价格"),
    yaxis2=dict(domain=[0.45, 0.57], title="成交量", showgrid=False),
    yaxis3=dict(domain=[0.25, 0.44], title="MACD", showgrid=False),
    yaxis4=dict(domain=[0.0, 0.24], title="RSI", showgrid=False, range=[0,100]),
)
st.plotly_chart(fig, use_container_width=True)

# ========================= 实时策略建议（增强版） =========================
st.markdown("---")
st.subheader("🧭 实时策略建议（非投资建议）")

last = dfi.dropna().iloc[-1]
price = float(last["Close"])

# 1) 趋势/动能评分
score = 0; reasons = []
# 使用 MA20/MA50 趋势（若存在）
ma20 = dfi["MA20"].iloc[-1] if "MA20" in dfi.columns else np.nan
ma50 = dfi["MA50"].iloc[-1] if "MA50" in dfi.columns else np.nan
if not np.isnan(ma20) and not np.isnan(ma50):
    if ma20 > ma50 and price > ma20:
        score += 2; reasons.append("MA20>MA50 且价在MA20上，多头趋势")
    elif ma20 < ma50 and price < ma20:
        score -= 2; reasons.append("MA20<MA50 且价在MA20下，空头趋势")

# MACD
if use_macd and all(c in dfi.columns for c in ["MACD","MACD_signal","MACD_hist"]):
    if last["MACD"] > last["MACD_signal"] and last["MACD_hist"] > 0:
        score += 2; reasons.append("MACD 金叉且柱为正")
    elif last["MACD"] < last["MACD_signal"] and last["MACD_hist"] < 0:
        score -= 2; reasons.append("MACD 死叉且柱为负")

# RSI
if use_rsi and "RSI" in dfi.columns:
    if last["RSI"] >= 70:
        score -= 1; reasons.append("RSI 过热（≥70）")
    elif last["RSI"] <= 30:
        score += 1; reasons.append("RSI 超卖（≤30）")

decision = "观望"
if score >= 3: decision = "买入/加仓"
elif score <= -2: decision = "减仓/离场"

# 2) 历史百分位（最近窗口）
hist_window = min(len(dfi), 365)  # 近一年或可用数据
recent_close = dfi["Close"].iloc[-hist_window:]
pct_rank = float((recent_close <= price).mean()) * 100 if hist_window > 1 else 50.0  # 价格在区间的百分位（0=低位,100=高位）

# 3) 支撑位/压力位（最近N根）
N = 20
recent_high = dfi["High"].iloc[-N:]
recent_low = dfi["Low"].iloc[-N:]
support_zone = (recent_low.min(), dfi["Close"].iloc[-N:].min())
resist_zone = (dfi["Close"].iloc[-N:].max(), recent_high.max())

# 4) ATR 止盈止损
if use_atr and "ATR" in dfi.columns and not np.isnan(last["ATR"]):
    atr_val = float(last["ATR"])
else:
    atr_val = float(dfi["Close"].pct_change().rolling(14).std().iloc[-1] * price)
tp = price + 2.0*atr_val if decision != "减仓/离场" else price - 2.0*atr_val
sl = price - 1.2*atr_val if decision != "减仓/离场" else price + 1.2*atr_val

# 5) 文案提示
hint = "区间中位；按信号执行为主。"
if pct_rank <= 25:
    hint = "低位区间（≤25%）→ 倾向逢低布局，关注止损与量能确认。"
elif pct_rank >= 75:
    hint = "高位区间（≥75%）→ 谨慎追高，关注回撤与量能衰减。"

c1,c2,c3,c4 = st.columns(4)
c1.metric("最新价", f"{price:,.4f}")
c2.metric("建议", decision)
c3.metric("评分", str(score))
c4.metric("ATR", f"{atr_val:,.4f}")

st.write("**依据**：", "；".join(reasons) if reasons else "信号不明确，建议观望。")
st.info(
    f"价格百分位：**{pct_rank:.1f}%**｜"
    f"支撑区：**{support_zone[0]:,.4f} ~ {support_zone[1]:,.4f}**｜"
    f"压力区：**{resist_zone[0]:,.4f} ~ {resist_zone[1]:,.4f}**｜"
    f"建议止损：**{sl:,.4f}** ｜ 建议止盈：**{tp:,.4f}**\n\n"
    f"提示：{hint}"
)

# ========================= 胜率统计（简版） =========================
def simple_backtest(df):
    df = df.dropna().copy()
    cond_ok = all(c in df.columns for c in ["MA20","MA50","MACD","MACD_signal"])
    if cond_ok:
        long_cond = (df["MA20"]>df["MA50"]) & (df["MACD"]>df["MACD_signal"])
        short_cond = (df["MA20"]<df["MA50"]) & (df["MACD"]<df["MACD_signal"])
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0))
    else:
        sig = np.zeros(len(df))
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
    return equity, pnl, win_rate, mdd

st.markdown("---")
st.subheader("📈 策略胜率与净值")
equity, pnl, win_rate, mdd = simple_backtest(dfi)
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
    st.plotly_chart(px.histogram(pnl, nbins=20, title="单笔收益分布"), use_container_width=True)
else:
    st.info("暂无可统计的交易样本。")

# ========================= 风控面板（结果） =========================
st.markdown("---")
st.subheader("🛡️ 风控面板（结果）")
atr_for_pos = atr_val if atr_val and atr_val>0 else (dfi["Close"].pct_change().rolling(14).std().iloc[-1]*price)
stop_distance = atr_for_pos / max(price, 1e-9)
risk_amount = float(account_value) * (float(risk_pct)/100.0)
position_value = risk_amount / max(stop_distance, 1e-6) / max(int(leverage),1)
position_value = min(position_value, float(account_value))
position_size = position_value / max(price, 1e-9)
rc1, rc2, rc3 = st.columns(3)
rc1.metric("建议持仓名义价值", f"{position_value:,.2f}")
rc2.metric("建议仓位数量", f"{position_size:,.6f}")
rc3.metric("单笔风险金额", f"{risk_amount:,.2f}")
st.caption("仓位公式：头寸 = 账户总值 × 单笔风险% ÷ (止损幅度 × 杠杆)")

# ========================= 组合风险暴露（按波动率配比） =========================
st.subheader("📊 组合风险暴露建议（低波动高权重）")
def get_close_series(sym):
    try:
        if source == "CoinGecko（免API）":
            d = load_coingecko_ohlc_robust(sym, interval)
        elif source == "TokenInsight API 模式（可填API基址）":
            d = load_tokeninsight_ohlc(api_base, sym, interval)
        elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
            d = load_okx_public(sym, interval, base_url=api_base if "OKX API" in source else "")
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
    st.plotly_chart(px.pie(w_df, names="symbol", values="weight", title="建议权重"), use_container_width=True)
else:
    st.info("组合标留空或数据不足。")
