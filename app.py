import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ========================= 工具函数 =========================
def load_yf(symbol, interval):
    period = "1y"
    if interval in ["1m", "5m", "15m", "30m", "60m"]:
        period = "7d"
    df = yf.download(symbol, period=period, interval=interval)
    df = df.dropna()
    return df

# ========================= Streamlit 界面 =========================
st.set_page_config(page_title="多功能量化分析终端", layout="wide")
st.title("📊 多功能量化分析终端 (TradingView 风格)")

# 选择数据源
st.sidebar.header("数据设置")
source = st.sidebar.selectbox("数据源", ["YahooFinance（股票/加密）"])
symbol = st.sidebar.text_input("交易对/股票代码", "AAPL")
interval = st.sidebar.selectbox("K线周期", ["1d", "1h", "30m", "15m", "5m"])

# 技术指标选择
st.sidebar.header("指标设置")
use_ma = st.sidebar.checkbox("MA 移动平均线", True)
use_macd = st.sidebar.checkbox("MACD", True)
use_rsi = st.sidebar.checkbox("RSI", True)
use_atr = st.sidebar.checkbox("ATR 波动率", True)

# 风控参数
st.sidebar.header("风控设置")
account_value = st.sidebar.number_input("账户资金 (USD)", 10000.0)
risk_pct = st.sidebar.slider("单笔风险%", 0.5, 5.0, 1.0)
leverage = st.sidebar.slider("杠杆倍数", 1, 10, 1)

# 组合标的
st.sidebar.header("组合设置")
combo_symbols = st.sidebar.text_area("组合标的 (逗号分隔)", "AAPL,MSFT,GOOG").split(",")
combo_symbols = [s.strip() for s in combo_symbols if s.strip()]

# ========================= 加载数据 =========================
df = load_yf(symbol, interval)
dfi = df.copy()

# ========================= 计算指标 =========================
if use_ma:
    dfi["MA20"] = dfi["Close"].rolling(20).mean()
    dfi["MA50"] = dfi["Close"].rolling(50).mean()
if use_macd:
    ema12 = dfi["Close"].ewm(span=12).mean()
    ema26 = dfi["Close"].ewm(span=26).mean()
    dfi["MACD"] = ema12 - ema26
    dfi["MACD_signal"] = dfi["MACD"].ewm(span=9).mean()
    dfi["MACD_hist"] = dfi["MACD"] - dfi["MACD_signal"]
if use_rsi:
    delta = dfi["Close"].diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    rs = up.rolling(14).mean() / down.rolling(14).mean()
    dfi["RSI"] = 100 - (100 / (1 + rs))
if use_atr:
    high_low = dfi["High"] - dfi["Low"]
    high_close = (dfi["High"] - dfi["Close"].shift()).abs()
    low_close = (dfi["Low"] - dfi["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    dfi["ATR"] = tr.rolling(14).mean()

# ========================= 绘制主图（含交互工具） =========================
fig = go.Figure()
fig.add_trace(go.Candlestick(x=dfi.index, open=dfi["Open"], high=dfi["High"],
                low=dfi["Low"], close=dfi["Close"], name="K线"))
if use_ma:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA20"], mode="lines", name="MA20"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA50"], mode="lines", name="MA50"))

fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=900,
    hovermode="x unified",
    dragmode="pan",
    yaxis=dict(domain=[0.58, 1.0], title="价格"),
    yaxis2=dict(domain=[0.45, 0.57], title="成交量", showgrid=False),
    yaxis3=dict(domain=[0.25, 0.44], title="MACD", showgrid=False),
    yaxis4=dict(domain=[0.0, 0.24], title="RSI", showgrid=False, range=[0,100])
)

fig.update_layout(
    modebar_add=["drawline", "drawopenpath", "drawclosedpath", "drawcircle", "drawrect", "eraseshape"]
)
fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=False), fixedrange=False),
    yaxis=dict(fixedrange=False)
)

st.plotly_chart(fig, use_container_width=True, config={
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False
})

# ========================= 实时策略建议 =========================
st.markdown("---")
st.subheader("🧭 实时策略建议（非投资建议）")

last = dfi.dropna().iloc[-1]
price = float(last["Close"])

score = 0; reasons = []
ma20 = dfi["MA20"].iloc[-1] if "MA20" in dfi.columns else np.nan
ma50 = dfi["MA50"].iloc[-1] if "MA50" in dfi.columns else np.nan
if not np.isnan(ma20) and not np.isnan(ma50):
    if ma20 > ma50 and price > ma20:
        score += 2; reasons.append("MA20>MA50 且价在MA20上，多头趋势")
    elif ma20 < ma50 and price < ma20:
        score -= 2; reasons.append("MA20<MA50 且价在MA20下，空头趋势")

if use_macd and all(c in dfi.columns for c in ["MACD","MACD_signal","MACD_hist"]):
    if last["MACD"] > last["MACD_signal"] and last["MACD_hist"] > 0:
        score += 2; reasons.append("MACD 金叉且柱为正")
    elif last["MACD"] < last["MACD_signal"] and last["MACD_hist"] < 0:
        score -= 2; reasons.append("MACD 死叉且柱为负")

if use_rsi and "RSI" in dfi.columns:
    if last["RSI"] >= 70:
        score -= 1; reasons.append("RSI 过热（≥70）")
    elif last["RSI"] <= 30:
        score += 1; reasons.append("RSI 超卖（≤30）")

decision = "观望"
if score >= 3: decision = "买入/加仓"
elif score <= -2: decision = "减仓/离场"

hist_window = min(len(dfi), 365)
recent_close = dfi["Close"].iloc[-hist_window:]
pct_rank = float((recent_close <= price).mean()) * 100 if hist_window > 1 else 50.0

N = 20
recent_high = dfi["High"].iloc[-N:]
recent_low = dfi["Low"].iloc[-N:]
support_zone = (recent_low.min(), dfi["Close"].iloc[-N:].min())
resist_zone = (dfi["Close"].iloc[-N:].max(), recent_high.max())

if use_atr and "ATR" in dfi.columns and not np.isnan(last["ATR"]):
    atr_val = float(last["ATR"])
else:
    atr_val = float(dfi["Close"].pct_change().rolling(14).std().iloc[-1] * price)

tp = price + 2.0*atr_val if decision != "减仓/离场" else price - 2.0*atr_val
sl = price - 1.2*atr_val if decision != "减仓/离场" else price + 1.2*atr_val

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

# ========================= 胜率统计 =========================
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

# ========================= 风控面板 =========================
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

# ========================= 组合风险暴露 =========================
st.subheader("📊 组合风险暴露建议（低波动高权重）")

def get_close_series(sym):
    try:
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
