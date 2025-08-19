import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta

# ========================= 页面配置 =========================
st.set_page_config(page_title="量化交易终端", layout="wide")

# ========================= 数据加载函数 =========================
@st.cache_data(ttl=600)
def load_yf(symbol, interval="1d", period="1y"):
    df = yf.download(symbol, interval=interval, period=period)
    df.index = pd.to_datetime(df.index)
    return df

# ========================= 技术指标计算 =========================
def add_indicators(df, use_macd=True, use_rsi=True, use_boll=True, use_atr=True):
    df = df.copy()
    # 均线
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    # MACD
    if use_macd:
        ema12 = df["Close"].ewm(span=12).mean()
        ema26 = df["Close"].ewm(span=26).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_signal"] = df["MACD"].ewm(span=9).mean()
        df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    # RSI
    if use_rsi:
        delta = df["Close"].diff()
        up = delta.clip(lower=0)
        down = -1*delta.clip(upper=0)
        roll_up = up.ewm(span=14).mean()
        roll_down = down.ewm(span=14).mean()
        rs = roll_up / roll_down
        df["RSI"] = 100 - (100/(1+rs))
    # BOLL
    if use_boll:
        ma20 = df["Close"].rolling(20).mean()
        std20 = df["Close"].rolling(20).std()
        df["Boll_Upper"] = ma20 + 2*std20
        df["Boll_Lower"] = ma20 - 2*std20
    # ATR
    if use_atr:
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(14).mean()
    return df

# ========================= 侧边栏参数 =========================
st.sidebar.header("参数设置")
symbol = st.sidebar.text_input("交易对（yfinance代码）", "BTC-USD")
interval = st.sidebar.selectbox("周期", ["1d","1h","5m"], index=0)
period = st.sidebar.selectbox("历史区间", ["1y","6mo","3mo","1mo"], index=0)
use_macd = st.sidebar.checkbox("显示 MACD", True)
use_rsi = st.sidebar.checkbox("显示 RSI", True)
use_boll = st.sidebar.checkbox("显示 布林带", True)
use_atr = st.sidebar.checkbox("显示 ATR", True)

st.sidebar.header("账户与风险参数")
account_value = st.sidebar.number_input("账户总资金 (USDT)", 10000.0, step=100.0)
risk_pct = st.sidebar.slider("单笔风险比例 %", 0.1, 5.0, 1.0, step=0.1)
leverage = st.sidebar.number_input("杠杆倍数", 1, 50, 1)
combo_symbols = st.sidebar.text_area("组合标的 (换行分隔)", "BTC-USD\nETH-USD").splitlines()

# ========================= 主体内容 =========================
st.title("📊 量化交易终端 (Trading Dashboard)")

df = load_yf(symbol, interval, period)
if df.empty:
    st.error("数据加载失败，请检查交易对代码。")
    st.stop()

dfi = add_indicators(df, use_macd, use_rsi, use_boll, use_atr)

# ========================= 主图绘制 =========================
fig = go.Figure()
# K线
fig.add_trace(go.Candlestick(
    x=dfi.index, open=dfi["Open"], high=dfi["High"],
    low=dfi["Low"], close=dfi["Close"], name="K线"
))
# 均线
fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA20"], line=dict(width=1), name="MA20"))
fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA50"], line=dict(width=1), name="MA50"))
fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MA200"], line=dict(width=1), name="MA200"))
# 布林带
if use_boll:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["Boll_Upper"], line=dict(width=1, dash="dot"), name="Boll上轨"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["Boll_Lower"], line=dict(width=1, dash="dot"), name="Boll下轨"))
# 成交量
fig.add_trace(go.Bar(x=dfi.index, y=dfi["Volume"], name="成交量", yaxis="y2", opacity=0.3))

# MACD
if use_macd:
    fig.add_trace(go.Bar(x=dfi.index, y=dfi["MACD_hist"], name="MACD柱", yaxis="y3"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD"], name="MACD", yaxis="y3"))
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["MACD_signal"], name="MACD信号", yaxis="y3"))

# RSI
if use_rsi:
    fig.add_trace(go.Scatter(x=dfi.index, y=dfi["RSI"], name="RSI", yaxis="y4"))

# 布局
fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=900,
    hovermode="x unified",
    dragmode="pan",
    yaxis=dict(domain=[0.58, 1.0], title="价格"),
    yaxis2=dict(domain=[0.45, 0.57], title="成交量", showgrid=False),
    yaxis3=dict(domain=[0.25, 0.44], title="MACD", showgrid=False),
    yaxis4=dict(domain=[0.0, 0.24], title="RSI", showgrid=False, range=[0,100]),
    modebar_add=["drawline","drawrect","eraseshape"],
)
st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True, "displaylogo": False})

# ========================= 实时策略建议 =========================
st.markdown("---")
st.subheader("🧭 实时策略建议（非投资建议）")
last = dfi.dropna().iloc[-1]
price = float(last["Close"])
score = 0; reasons = []
ma20 = dfi["MA20"].iloc[-1]; ma50 = dfi["MA50"].iloc[-1]
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
pct_rank = float((recent_close <= price).mean())*100 if hist_window>1 else 50
N=20
support_zone=(dfi["Low"].iloc[-N:].min(), dfi["Close"].iloc[-N:].min())
resist_zone=(dfi["Close"].iloc[-N:].max(), dfi["High"].iloc[-N:].max())
atr_val=float(last["ATR"]) if use_atr and "ATR" in dfi.columns else float(dfi["Close"].pct_change().rolling(14).std().iloc[-1]*price)
tp = price + 2*atr_val if decision!="减仓/离场" else price-2*atr_val
sl = price - 1.2*atr_val if decision!="减仓/离场" else price+1.2*atr_val
hint = "区间中位；按信号执行为主。"
if pct_rank <= 25: hint = "低位区间（≤25%）→ 倾向逢低布局。"
elif pct_rank >= 75: hint = "高位区间（≥75%）→ 谨慎追高。"

c1,c2,c3,c4 = st.columns(4)
c1.metric("最新价", f"{price:,.4f}")
c2.metric("建议", decision)
c3.metric("评分", str(score))
c4.metric("ATR", f"{atr_val:,.4f}")
st.write("**依据**：", "；".join(reasons) if reasons else "信号不明确")
st.info(
    f"价格百分位：**{pct_rank:.1f}%**｜支撑区：**{support_zone[0]:,.4f}~{support_zone[1]:,.4f}**｜压力区：**{resist_zone[0]:,.4f}~{resist_zone[1]:,.4f}**｜止损：**{sl:,.4f}**｜止盈：**{tp:,.4f}**\n\n提示：{hint}"
)

# ========================= 胜率统计 =========================
st.markdown("---")
st.subheader("📈 策略胜率与净值")
def simple_backtest(df):
    df=df.dropna().copy()
    cond_ok=all(c in df.columns for c in ["MA20","MA50","MACD","MACD_signal"])
    if cond_ok:
        long_cond=(df["MA20"]>df["MA50"])&(df["MACD"]>df["MACD_signal"])
        short_cond=(df["MA20"]<df["MA50"])&(df["MACD"]<df["MACD_signal"])
        sig=np.where(long_cond,1,np.where(short_cond,-1,0))
    else: sig=np.zeros(len(df))
    df["sig"]=sig
    ret=df["Close"].pct_change().fillna(0).values
    pos=pd.Series(sig,index=df.index).replace(0,np.nan).ffill().fillna(0).values
    strat_ret=pos*ret
    equity=(1+pd.Series(strat_ret,index=df.index)).cumprod()
    pnl=[];last_side=0;entry=None
    for side,p in zip(pos,df["Close"].values):
        if side!=0 and last_side==0: entry=p;last_side=side
        elif side==0 and last_side!=0 and entry is not None:
            pnl.append((p/entry-1)*last_side);last_side=0;entry=None
    pnl=pd.Series(pnl) if len(pnl)>0 else pd.Series(dtype=float)
    win_rate=float((pnl>0).mean()) if len(pnl)>0 else 0
    roll_max=equity.cummax();mdd=float(((roll_max-equity)/roll_max).max())
    return equity,pnl,win_rate,mdd

equity,pnl,win_rate,mdd=simple_backtest(dfi)
c1,c2,c3=st.columns(3)
c1.metric("历史胜率", f"{win_rate*100:.2f}%")
c2.metric("最大回撤", f"{mdd*100:.2f}%")
total_ret=equity.iloc[-1]/equity.iloc[0]-1 if len(equity)>1 else 0
c3.metric("累计收益", f"{total_ret*100:.2f}%")
fig_eq=go.Figure()
fig_eq.add_trace(go.Scatter(x=equity.index,y=equity.values,mode="lines",name="策略净值"))
fig_eq.update_layout(height=280,xaxis_rangeslider_visible=False)
st.plotly_chart(fig_eq,use_container_width=True)
if len(pnl)>0:
    st.plotly_chart(px.histogram(pnl,nbins=20,title="单笔收益分布"),use_container_width=True)
else:
    st.info("暂无可统计交易样本。")

# ========================= 风控面板 =========================
st.markdown("---")
st.subheader("🛡️ 风控面板（结果）")
atr_for_pos=atr_val if atr_val>0 else (dfi["Close"].pct_change().rolling(14).std().iloc[-1]*price)
stop_distance=atr_for_pos/max(price,1e-9)
risk_amount=float(account_value)*(float(risk_pct)/100)
position_value=risk_amount/max(stop_distance,1e-6)/max(int(leverage),1)
position_value=min(position_value,float(account_value))
position_size=position_value/max(price,1e-9)
rc1,rc2,rc3=st.columns(3)
rc1.metric("建议持仓名义价值", f"{position_value:,.2f}")
rc2.metric("建议仓位数量", f"{position_size:,.6f}")
rc3.metric("单笔风险金额", f"{risk_amount:,.2f}")
st.caption("仓位公式：头寸 = 账户总值 × 风险% ÷ (止损幅度 × 杠杆)")

# ========================= 组合风险暴露 =========================
st.markdown("---")
st.subheader("📊 组合风险暴露建议（低波动高权重）")
series_list=[]
for s in combo_symbols:
    try:
        d=load_yf(s,interval,period)
        series_list.append(d["Close"].rename(s))
    except: pass
if series_list:
    closes=pd.concat(series_list,axis=1).dropna()
    vols=closes.pct_change().rolling(30).std().iloc[-1].replace(0,np.nan)
    inv_vol=1.0/vols
    weights=inv_vol/np.nansum(inv_vol)
    w_df=pd.DataFrame({"symbol":weights.index,"weight":weights.values})
    st.plotly_chart(px.pie(w_df,names="symbol",values="weight",title="建议权重"),use_container_width=True)
else:
    st.info("组合标的留空或数据不足。")
