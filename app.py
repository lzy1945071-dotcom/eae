import time
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="加密货币量化分析小工具（免费API）", layout="wide")

st.title("🧪 加密货币量化分析小工具（CoinGecko 免费API）")

with st.sidebar:
    st.header("参数设置")
    coin = st.selectbox(
        "选择币种（CoinGecko）",
        options=[
            "bitcoin","ethereum","binancecoin","solana","ripple","cardano",
            "dogecoin","polkadot","tron","litecoin","chainlink","uniswap",
            "avalanche-2","matic-network","near","internet-computer","aptos",
            "arbitrum","optimism","monero","stellar","theta-token"
        ],
        index=0
    )
    vs = st.selectbox("计价货币", ["usd","eur","cny"], index=0)
    days = st.select_slider("回看天数（日线）", options=[30,60,90,180,365,730,1460,3650], value=365)
    sma_fast = st.number_input("SMA 快速线（天）", min_value=2, max_value=200, value=20, step=1)
    sma_slow = st.number_input("SMA 慢速线（天）", min_value=5, max_value=400, value=60, step=1)
    rsi_period = st.number_input("RSI 周期", min_value=2, max_value=60, value=14, step=1)
    initial_cash = st.number_input("初始资金", min_value=100.0, value=10000.0, step=100.0)
    slippage_bps = st.number_input("滑点（基点，1%=100bp）", min_value=0, max_value=200, value=10, step=1)
    st.caption("数据源：CoinGecko 免费公开接口，无需 API Key。")

@st.cache_data(ttl=3600)
def load_history(coin_id: str, vs_currency: str, days: int) -> pd.DataFrame:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": "daily"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    prices = data.get("prices", [])
    if not prices:
        raise RuntimeError("未获取到价格数据")
    df = pd.DataFrame(prices, columns=["ts", "price"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms").dt.date
    df = df.drop(columns=["ts"]).set_index("date")
    return df

def compute_indicators(df: pd.DataFrame, sma_fast: int, sma_slow: int, rsi_period: int):
    out = df.copy()
    out["SMA_fast"] = out["price"].rolling(sma_fast).mean()
    out["SMA_slow"] = out["price"].rolling(sma_slow).mean()
    # RSI
    delta = out["price"].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain, index=out.index).rolling(rsi_period).mean()
    roll_down = pd.Series(loss, index=out.index).rolling(rsi_period).mean()
    rs = roll_up / (roll_down + 1e-9)
    out["RSI"] = 100 - (100 / (1 + rs))
    return out

def backtest_sma_cross(df: pd.DataFrame, init_cash: float, slippage_bps: int):
    bt = df.dropna(subset=["SMA_fast","SMA_slow"]).copy()
    bt["signal"] = np.where(bt["SMA_fast"] > bt["SMA_slow"], 1, 0)  # 1=持有, 0=空仓
    bt["signal_shift"] = bt["signal"].shift(1).fillna(0)
    # 交易点：signal 变化
    trade_mask = bt["signal"] != bt["signal_shift"]
    # 收益率（日度）
    ret = bt["price"].pct_change().fillna(0.0)
    # 交易成本（双边）
    cost = (slippage_bps / 10000.0)
    # 策略收益：只有持有时获得市场收益；在换手当日扣成本
    strat_ret = ret * bt["signal_shift"] - cost * trade_mask.astype(float)
    bt["strategy_equity"] = (1 + strat_ret).cumprod() * init_cash
    bt["buy_hold_equity"] = (1 + ret).cumprod() * init_cash
    stats = {
        "最终净值(策略)": float(bt["strategy_equity"].iloc[-1]),
        "最终净值(买入持有)": float(bt["buy_hold_equity"].iloc[-1]),
        "超额收益": float(bt["strategy_equity"].iloc[-1] - bt["buy_hold_equity"].iloc[-1]),
        "年化波动(策略)": float(bt["strategy_equity"].pct_change().std() * np.sqrt(252)),
        "最大回撤(策略)": float((bt["strategy_equity"].cummax() - bt["strategy_equity"]).max() / bt["strategy_equity"].cummax().max()),
    }
    return bt, stats

try:
    df = load_history(coin, vs, days)
    df = compute_indicators(df, sma_fast, sma_slow, rsi_period)
    bt, stats = backtest_sma_cross(df, initial_cash, slippage_bps)
    st.subheader("价格与均线")
    fig1 = px.line(df.reset_index(), x="date", y=["price","SMA_fast","SMA_slow"])
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("RSI 指标")
    fig2 = px.line(df.reset_index(), x="date", y=["RSI"])
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("回测净值（初始资金 = {:.2f} {}）".format(initial_cash, vs.upper()))
    fig3 = px.line(bt.reset_index(), x="date", y=["strategy_equity","buy_hold_equity"])
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("关键统计")
    c1, c2, c3 = st.columns(3)
    c1.metric("策略最终净值", f"{stats['最终净值(策略)']:.2f} {vs.upper()}")
    c2.metric("买入持有最终净值", f"{stats['最终净值(买入持有)']:.2f} {vs.upper()}")
    c3.metric("超额收益", f"{stats['超额收益']:.2f} {vs.upper()}")

    c4, c5 = st.columns(2)
    c4.metric("年化波动(近似)", f"{stats['年化波动(策略)']:.2%}")
    c5.metric("最大回撤(策略)", f"{stats['最大回撤(策略)']:.2%}")

    st.caption("⚠️ 仅供教育与演示，非投资建议；历史不代表未来。API 限频可能导致偶发错误，稍后重试。")

except Exception as e:
    st.error(f"加载或计算失败：{e}")
    st.stop()