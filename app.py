import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import ta
from itertools import product
from datetime import datetime
import math

# yfinance for stocks
try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception:
    YF_AVAILABLE = False

# Optional OKX SDK (only needed for trading panel)
try:
    from okx.Trade import TradeAPI
    OKX_AVAILABLE = True
except Exception:
    OKX_AVAILABLE = False

st.set_page_config(page_title="Legend Quant Terminal Elite (All-in-One v2)", layout="wide")
st.title("💎 Legend Quant Terminal Elite — 一体化量化终端 v2")

# ===================== Sidebar =====================
with st.sidebar:
    st.header("数据源与标的")
    data_source = st.radio(
        "数据源",
        ["CoinGecko（免费）", "OKX 公共行情", "Tokensight（自定义URL）", "股票（A股/美股）"],
        index=0,
        help="新增 A股/美股（yfinance），OKX 支持资金费率套利面板"
    )

    # CoinGecko
    cg_universe = [
        "bitcoin","ethereum","solana","ripple","dogecoin","cardano","polkadot",
        "tron","litecoin","chainlink","uniswap","avalanche-2","matic-network","near"
    ]
    coin_multi = st.multiselect("组合标的（CoinGecko ID，可多选）", cg_universe, default=["bitcoin","ethereum"],
                                help="用于组合回测；为空则使用下方单标的")
    coin_single = st.selectbox("单标的（CoinGecko ID）", cg_universe, index=0)
    vs = st.selectbox("计价货币", ["usd","eur","cny"], index=0)

    # Tokensight
    tokensight_url = st.text_input("Tokensight 自定义URL（单标）", "")

    # OKX
    okx_inst_multi = st.text_input("OKX InstId 列表（逗号分隔）", "BTC-USDT,ETH-USDT",
                                   help="支持现货/永续/期货，如 BTC-USDT-SWAP")
    bar_choices = ["1m","3m","5m","15m","30m","1H","4H","6H","12H","1D","1W","1M"]
    main_bar = st.selectbox("主视图K线周期", bar_choices, index=9,
                            help="用于主视图蜡烛图；OKX 支持分钟~月线")

    # 股票（A股/美股）
    st.markdown("—")
    st.caption("📈 股票（A股/美股）示例：A股上交所 `.SS`（600519.SS），深交所 `.SZ`（000001.SZ）；美股如 AAPL、MSFT。")
    stock_market = st.radio("股票市场", ["A股", "美股"], index=0)
    stock_tickers = st.text_input("股票代码（逗号分隔）", "600519.SS,AAPL",
                                  help="支持多标；将用于组合回测；主视图默认取第一只")
    stock_period = st.selectbox("股票K线周期", ["1d","1h","1wk","1mo"], index=0,
                                help="yfinance 支持的周期")

    # 多周期回测
    multi_timeframes = st.multiselect("多周期联动回测", ["1m","5m","15m","1H","4H","1D"], default=["1H","4H","1D"],
                                      help="对勾选周期回测并输出绩效对比（OKX/CoinGecko）")

    st.header("📊 核心交易策略（文章优化版）")
    strat_select = st.multiselect(
        "选择核心策略（用于提示与绩效卡片）",
        ["趋势跟踪 (MACD战法)", "背离反转 (MACD/RSI)", "滚仓复利", "套利策略 (现货-永续对冲)"],
        default=["趋势跟踪 (MACD战法)", "背离反转 (MACD/RSI)"],
    )
    st.caption("悬停查看说明 ↓")
    st.checkbox("趋势跟踪 (MACD战法)", value=True,
        help="金叉+红柱放大买入；死叉+绿柱放大做空；BTC 4h 用 (8,21,5)，胜率≈68%，假信号↓25%")
    st.checkbox("背离反转 (MACD/RSI)", value=True,
        help="顶背离/底背离 + 成交量确认，成功率≈79%")
    st.checkbox("滚仓复利", value=False,
        help="盈利平仓再加码复利；参数见“资金管理”面板")
    st.checkbox("套利策略 (现货-永续对冲)", value=False,
        help="买现货+做空永续，赚资金费率；支持 OKX 资金费率监控")

    st.header("📈 技术指标（文章优化版）")
    sma_fast = st.number_input("SMA 快", 2, 200, 20)
    sma_slow = st.number_input("SMA 慢", 5, 400, 60)
    ema_fast = st.number_input("EMA 快", 2, 200, 12)
    ema_slow = st.number_input("EMA 慢", 5, 400, 26)
    macd_signal = st.number_input("MACD 信号线", 3, 20, 9)
    rsi_period = st.number_input("RSI 周期", 2, 60, 14)
    rsi_buy = st.number_input("RSI 买入阈值（超卖）", 1, 99, 30)
    rsi_sell = st.number_input("RSI 卖出阈值（超买）", 40, 99, 70)
    boll_window = st.number_input("布林带窗口", 5, 100, 20)
    enable_volume_confirm = st.checkbox("启用成交量确认", value=True,
                                        help="突破/背离时要求量能放大≥150%（无量时以波幅近似）")

    st.header("策略库（信号生成，多选）")
    strat_ma_cross = st.checkbox("均线交叉（SMA）", True)
    strat_ema_cross = st.checkbox("均线交叉（EMA）", False)
    strat_rsi = st.checkbox("RSI 超买超卖", True)
    strat_macd = st.checkbox("MACD 趋势", True)
    strat_boll = st.checkbox("布林带突破", False)
    combine_mode = st.selectbox("信号合成方式", ["任一触发（OR）", "多数投票（Majority）", "全体一致（AND）"], index=1)

    st.header("回测参数")
    initial_cash = st.number_input("初始资金", min_value=100.0, value=10000.0, step=100.0)
    fee_bps = st.number_input("手续费（基点，双边）", min_value=0, max_value=200, value=10, step=1)
    slippage_bps = st.number_input("滑点（基点）", min_value=0, max_value=200, value=5, step=1)
    max_position = st.slider("最大仓位（资金比例）", 0.1, 1.0, 1.0, step=0.1)

    st.header("资金管理：滚仓复利")
    enable_compound = st.checkbox("启用滚仓复利（动态加仓）", value=False,
                                  help="盈利出场后提高下一次目标仓位；连亏时降低仓位；限制在最大仓位之内")
    compound_win_step = st.slider("单次盈利后仓位增量", 0.0, 0.5, 0.1, 0.01)
    compound_loss_step = st.slider("单次亏损后仓位减量", 0.0, 0.5, 0.1, 0.01)
    compound_floor = st.slider("最小仓位（比例）", 0.0, 1.0, 0.2, 0.05)
    compound_cap = st.slider("最大仓位上限（比例）", 0.1, 1.0, 1.0, 0.05)

    st.header("风控面板 & 推送")
    dd_alert = st.number_input("最大回撤预警阈值（%）", min_value=1, max_value=99, value=20, step=1)
    vol_window = st.number_input("波动率窗口（日）", min_value=5, max_value=120, value=30, step=1)
    vol_alert = st.number_input("年化波动率预警阈值（%）", min_value=5, max_value=300, value=120, step=5)
    var_conf = st.selectbox("VaR 置信度", ["95%", "99%"], index=0)
    webhook_url = st.text_input("企业微信机器人 Webhook（可选）",
        help="WeCom webhook：https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...")
    test_push = st.button("🔔 发送测试推送")

    st.header("网格搜索（批量回测）")
    enable_grid = st.checkbox("启用网格搜索", value=False)
    grid_sma_fast = st.text_input("SMA 快", "10,20,30")
    grid_sma_slow = st.text_input("SMA 慢", "50,60,90")
    grid_rsi_buy = st.text_input("RSI 买", "25,30,35")
    grid_rsi_sell = st.text_input("RSI 卖", "65,70,75")
    grid_max_combo = st.number_input("最大组合数", min_value=10, max_value=3000, value=300, step=10)
    objective = st.selectbox("优化目标", ["年化收益率", "夏普比率", "最大回撤最小"], index=1)
    topn = st.slider("展示最优前 N 组", 1, 50, 10)

    st.header("OKX 交易（可选）")
    okx_api = st.text_input("OKX API Key", type="password")
    okx_secret = st.text_input("OKX Secret Key", type="password")
    okx_passphrase = st.text_input("OKX Passphrase", type="password")
    env_choice = st.radio("交易环境", ["模拟盘", "实盘"], index=0)
    enable_trading_panel = st.checkbox("启用交易面板", value=False)

# =============== Data Loaders ===============
@st.cache_data(ttl=1800)
def load_okx_candles(instId: str, bar: str, limit: int=1500) -> pd.DataFrame:
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": instId, "bar": bar, "limit": str(limit)}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    arr = data.get("data", [])
    if not arr:
        raise RuntimeError(f"OKX 无数据: {instId}")
    rows = []
    for a in reversed(arr):
        ts = int(a[0]); o=float(a[1]); h=float(a[2]); l=float(a[3]); c=float(a[4])
        rows.append((pd.to_datetime(ts, unit="ms"), o,h,l,c))
    df = pd.DataFrame(rows, columns=["date","open","high","low","close"]).set_index("date")
    df["price"] = df["close"]
    return df

@st.cache_data(ttl=1800)
def load_okx_funding(instId: str) -> dict:
    url = "https://www.okx.com/api/v5/public/funding-rate"
    params = {"instId": instId}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    js = r.json()
    arr = js.get("data", [])
    if not arr:
        return {}
    d = arr[0]
    # fundingRate is in decimal (e.g., 0.0001 per 8h)
    return {
        "fundingRate": float(d.get("fundingRate", 0.0)),
        "nextFundingRate": float(d.get("nextFundingRate", 0.0)),
        "fundingTime": d.get("fundingTime")
    }

@st.cache_data(ttl=1800)
def load_coingecko_ohlc(coin_id: str, vs_currency: str, days: int=365) -> pd.DataFrame:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": vs_currency, "days": days}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    arr = r.json()
    if not isinstance(arr, list) or len(arr) == 0:
        raise RuntimeError(f"CoinGecko OHLC 无数据: {coin_id}")
    rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in arr]
    df = pd.DataFrame(rows, columns=["date","open","high","low","close"]).set_index("date")
    df["price"] = df["close"]
    return df

@st.cache_data(ttl=1800)
def load_tokensight(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    rows = None
    if isinstance(data, list) and len(data)>0 and isinstance(data[0], (list,tuple)) and len(data[0])>=5:
        rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in data]
    elif isinstance(data, list) and len(data)>0 and isinstance(data[0], dict) and {"ts","open","high","low","close"}<=set(data[0].keys()):
        rows = [(pd.to_datetime(x["ts"], unit="ms"), float(x["open"]), float(x["high"]), float(x["low"]), float(x["close"])) for x in data]
    if rows is not None:
        df = pd.DataFrame(rows, columns=["date","open","high","low","close"]).set_index("date")
        df["price"] = df["close"]
        return df
    if isinstance(data, dict) and "data" in data:
        arr = data["data"]
        if arr and isinstance(arr[0], list):
            rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1])) for x in arr]
        else:
            rows = [(pd.to_datetime(x["ts"], unit="ms"), float(x["price"])) for x in arr]
    elif isinstance(data, list):
        rows = [(pd.to_datetime(x.get("ts") or x.get("timestamp"), unit="ms"), float(x["price"])) for x in data]
    else:
        raise RuntimeError("Tokensight 返回格式无法解析（需 OHLC 或 ts/price）")
    df = pd.DataFrame(rows, columns=["date","price"]).set_index("date").sort_index()
    for col in ["open","high","low","close"]:
        df[col] = df["price"]
    return df

@st.cache_data(ttl=1800)
def load_stock_ohlc(tickers: list, period: str = "1y", interval: str = "1d") -> dict:
    if not YF_AVAILABLE:
        raise RuntimeError("未安装 yfinance，请先 pip install yfinance")
    res = {}
    for t in tickers:
        try:
            data = yf.download(t, period=period, interval=interval, auto_adjust=False, progress=False)
            if data.empty:
                continue
            df = data.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close"})
            df = df[["open","high","low","close"]].copy()
            df["price"] = df["close"]
            res[t] = df
        except Exception:
            pass
    if not res:
        raise RuntimeError("未能下载任何股票数据（检查代码与网络）")
    return res

def get_symbol_list():
    if data_source == "OKX 公共行情":
        syms = [s.strip() for s in okx_inst_multi.split(",") if s.strip()]
        return syms if syms else ["BTC-USDT"]
    elif data_source == "Tokensight（自定义URL）":
        return ["TS-CUSTOM"]
    elif data_source == "股票（A股/美股）":
        syms = [s.strip() for s in stock_tickers.split(",") if s.strip()]
        return syms if syms else ["600519.SS"]
    else:
        syms = coin_multi if coin_multi else [coin_single]
        return syms

def load_symbol_df(symbol: str, bar: str) -> pd.DataFrame:
    if data_source == "OKX 公共行情":
        return load_okx_candles(symbol, bar)
    elif data_source == "Tokensight（自定义URL）":
        return load_tokensight(tokensight_url)
    elif data_source == "股票（A股/美股）":
        # Map streamlit bar to yfinance interval
        interval = "1d"
        if stock_period == "1h": interval = "60m"
        elif stock_period == "1wk": interval = "1wk"
        elif stock_period == "1mo": interval = "1mo"
        d = load_stock_ohlc([symbol], period="1y", interval=interval)
        return list(d.values())[0]
    else:
        return load_coingecko_ohlc(symbol, vs, 365)

# =============== Indicators & Strategy ===============
def add_indicators(df: pd.DataFrame,
                   sma_fast:int, sma_slow:int, ema_fast:int, ema_slow:int,
                   rsi_period:int, boll_window:int, macd_signal:int) -> pd.DataFrame:
    out = df.copy()
    price = out["price"]
    out["SMA_fast"] = ta.trend.sma_indicator(price, window=sma_fast)
    out["SMA_slow"] = ta.trend.sma_indicator(price, window=sma_slow)
    out["EMA_fast"] = ta.trend.ema_indicator(price, window=ema_fast)
    out["EMA_slow"] = ta.trend.ema_indicator(price, window=ema_slow)
    out["RSI"] = ta.momentum.rsi(price, window=rsi_period)
    macd = ta.trend.MACD(price, window_slow=ema_slow, window_fast=ema_fast, window_sign=macd_signal)
    out["MACD"] = macd.macd()
    out["MACD_signal"] = macd.macd_signal()
    out["MACD_diff"] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(price, window=boll_window)
    out["BOLL_H"] = bb.bollinger_hband(); out["BOLL_L"] = bb.bollinger_lband()
    rng = (out["high"] - out["low"]).abs() / out["close"].replace(0,np.nan)
    out["RANGE_PCT"] = rng.fillna(0)
    return out

def volume_confirm_mask(df: pd.DataFrame):
    thresh = df["RANGE_PCT"].rolling(50, min_periods=10).quantile(0.75)
    return df["RANGE_PCT"] > thresh

def strategy_signals(df: pd.DataFrame, flags: dict, thresholds: dict, enable_vol: bool=False) -> pd.DataFrame:
    sig = pd.DataFrame(index=df.index)
    vol_ok = volume_confirm_mask(df) if enable_vol else pd.Series(True, index=df.index)
    if flags.get("SMA", False):
        sig["SMA_cross"] = np.where(df["SMA_fast"] > df["SMA_slow"], 1, -1)
    if flags.get("EMA", False):
        sig["EMA_cross"] = np.where(df["EMA_fast"] > df["EMA_slow"], 1, -1)
    if flags.get("RSI", False):
        s = np.zeros(len(df))
        s[(df["RSI"] <= thresholds["rsi_buy"]) & vol_ok] = 1
        s[(df["RSI"] >= thresholds["rsi_sell"]) & vol_ok] = -1
        sig["RSI"] = s
    if flags.get("MACD", False):
        cross_up = (df["MACD"].shift(1) <= df["MACD_signal"].shift(1)) & (df["MACD"] > df["MACD_signal"])
        cross_dn = (df["MACD"].shift(1) >= df["MACD_signal"].shift(1)) & (df["MACD"] < df["MACD_signal"])
        hist_up = df["MACD_diff"] > df["MACD_diff"].shift(1)
        hist_dn = df["MACD_diff"] < df["MACD_diff"].shift(1)
        s = np.zeros(len(df))
        s[cross_up & hist_up & vol_ok] = 1
        s[cross_dn & hist_dn & vol_ok] = -1
        sig["MACD"] = s
    if flags.get("BOLL", False):
        s = np.zeros(len(df))
        s[(df["price"] > df["BOLL_H"]) & vol_ok] = 1
        s[(df["price"] < df["BOLL_L"]) & vol_ok] = -1
        sig["BOLL"] = s
    if sig.shape[1] == 0:
        sig["DUMMY"] = 0
    return sig

def combine_signals(sig: pd.DataFrame, mode: str) -> pd.Series:
    s = sig.copy().fillna(0)
    if mode.startswith("任一"):
        any_long = (s == 1).any(axis=1)
        all_short = (s == -1).all(axis=1)
        return pd.Series(np.where(any_long, 1, np.where(all_short, -1, 0)), index=s.index)
    elif mode.startswith("多数"):
        vote = s.sum(axis=1)
        return pd.Series(np.where(vote > 0, 1, np.where(vote < 0, -1, 0)), index=s.index)
    else:
        all_long = (s == 1).all(axis=1)
        all_short = (s == -1).all(axis=1)
        return pd.Series(np.where(all_long, 1, np.where(all_short, -1, 0)), index=s.index)

def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 14):
    res = pd.DataFrame(index=df.index, columns=["bull_div", "bear_div"], dtype=bool).fillna(False)
    price = df["price"]; rsi = df["RSI"]
    for i in range(lookback, len(df)-lookback):
        px_win = price.iloc[i-lookback:i+1]
        rsi_win = rsi.iloc[i-lookback:i+1]
        if price.iloc[i] == px_win.max() and rsi.iloc[i] < rsi_win.max()*0.995:
            res.iloc[i, res.columns.get_loc("bear_div")] = True
        if price.iloc[i] == px_win.min() and rsi.iloc[i] > rsi_win.min()*1.005:
            res.iloc[i, res.columns.get_loc("bull_div")] = True
    return res

# =============== Backtest & Money Management ===============
def backtest(df: pd.DataFrame, signal: pd.Series, init_cash: float, fee_bps: int, slippage_bps: int, max_pos: float,
             enable_compound=False, win_step=0.1, loss_step=0.1, floor=0.2, cap=1.0):
    bt = df.copy()
    bt["signal"] = pd.Series(signal, index=bt.index).fillna(0).astype(int)
    bt["ret"] = bt["price"].pct_change().fillna(0.0)

    # Dynamic position via rolling compounding
    pos = np.zeros(len(bt))
    target = min(max_pos, max(floor, min(cap, max_pos)))
    last_pos = 0.0
    entry_px = None
    cost = (fee_bps + slippage_bps)/10000.0
    for i in range(1, len(bt)):
        sig = bt["signal"].iloc[i]
        price = bt["price"].iloc[i]
        prev_price = bt["price"].iloc[i-1]
        # exit on flat/flip
        if last_pos > 0 and sig <= 0:
            # close long, compute trade result
            pnl = (price - entry_px) / entry_px - cost
            if enable_compound:
                if pnl > 0:
                    target = min(cap, target + win_step)
                elif pnl < 0:
                    target = max(floor, target - loss_step)
            last_pos = 0.0; entry_px=None
        elif last_pos < 0 and sig >= 0:
            pnl = (entry_px - price) / entry_px - cost
            if enable_compound:
                if pnl > 0:
                    target = min(cap, target + win_step)
                elif pnl < 0:
                    target = max(floor, target - loss_step)
            last_pos = 0.0; entry_px=None

        # enter/update
        if sig > 0:
            last_pos = target
            if entry_px is None:
                entry_px = price
        elif sig < 0:
            last_pos = -target
            if entry_px is None:
                entry_px = price
        else:
            last_pos = 0.0
            entry_px = entry_px  # hold until next signal to compute pnl

        pos[i] = last_pos

    bt["pos"] = pd.Series(pos, index=bt.index)
    turn = pd.Series(np.abs(np.diff(np.concatenate([[0], pos]))), index=bt.index)
    bt["strategy_ret"] = bt["pos"]*bt["ret"] - turn*cost
    bt["equity"] = (1+bt["strategy_ret"]).cumprod()*init_cash
    bt["buyhold"] = (1+bt["ret"]).cumprod()*init_cash

    # Trades for stats
    trades = []
    in_pos = 0; entry_px=None; entry_time=None; dirn=0
    for i in range(1, len(bt)):
        if bt["pos"].iloc[i-1] == 0 and bt["pos"].iloc[i] > 0:
            in_pos = 1; dirn=1; entry_px = bt["price"].iloc[i]; entry_time = bt.index[i]
            trades.append({"time": entry_time, "price": entry_px, "side": "BUY"})
        elif bt["pos"].iloc[i-1] == 0 and bt["pos"].iloc[i] < 0:
            in_pos = 1; dirn=-1; entry_px = bt["price"].iloc[i]; entry_time = bt.index[i]
            trades.append({"time": entry_time, "price": entry_px, "side": "SELL"})
        elif in_pos == 1 and ((dirn==1 and bt["pos"].iloc[i] <= 0) or (dirn==-1 and bt["pos"].iloc[i] >= 0)):
            exit_px = bt["price"].iloc[i]; exit_time = bt.index[i]
            ret = (exit_px - entry_px)/entry_px - cost if dirn==1 else (entry_px - exit_px)/entry_px - cost
            trades.append({"time": exit_time, "price": exit_px, "side": "FLAT", "pnl": ret})
            in_pos = 0

    eq = bt["equity"]; daily_ret = bt["strategy_ret"]
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (252/max(1,len(eq))) - 1 if len(eq) > 1 else 0.0
    vol = daily_ret.std()*np.sqrt(252)
    sharpe = (daily_ret.mean()*252)/(vol+1e-12)
    downside = daily_ret[daily_ret<0].std()*np.sqrt(252)
    sortino = (daily_ret.mean()*252)/(downside+1e-12)
    roll_max = eq.cummax(); max_dd = ((roll_max-eq)/roll_max).max()
    closed = [t for t in trades if t.get("side")=="FLAT"]
    wins = [t for t in closed if t.get("pnl",0)>0]
    win_rate = len(wins)/len(closed) if closed else 0.0
    pnl_list = [t.get("pnl",0) for t in closed]
    profit = sum([x for x in pnl_list if x>0]); loss = -sum([x for x in pnl_list if x<0])
    profit_factor = (profit/(loss+1e-12)) if loss>0 else np.inf

    stats = {
        "累计收益率": float(eq.iloc[-1]/eq.iloc[0]-1),
        "年化收益率": float(cagr),
        "年化波动率": float(vol),
        "夏普比率": float(sharpe),
        "索提诺比率": float(sortino),
        "最大回撤": float(max_dd),
        "胜率": float(win_rate),
        "盈亏比(Profit Factor)": float(profit_factor),
        "交易次数": int(len(closed)),
        "最终净值": float(eq.iloc[-1])
    }
    return bt, stats, pd.DataFrame(trades)

def portfolio_backtest(symbols, bar):
    data_map = {}
    for sym in symbols:
        df = load_symbol_df(sym, bar)
        data_map[sym] = df
    idx = None
    for df in data_map.values():
        idx = df.index if idx is None else idx.intersection(df.index)
    for k in list(data_map.keys()):
        data_map[k] = data_map[k].loc[idx].copy()

    per_stats = []
    per_equity = {}
    per_rets = {}
    for sym, df in data_map.items():
        df_ind = add_indicators(df, sma_fast, sma_slow, ema_fast, ema_slow, rsi_period, boll_window, macd_signal)
        flags = {"SMA": strat_ma_cross, "EMA": strat_ema_cross, "RSI": strat_rsi, "MACD": strat_macd, "BOLL": strat_boll}
        thresholds = {"rsi_buy": rsi_buy, "rsi_sell": rsi_sell}
        sigs = strategy_signals(df_ind, flags, thresholds, enable_volume_confirm)
        comb = combine_signals(sigs, combine_mode)
        bt, stats, _ = backtest(df_ind, comb, initial_cash, fee_bps, slippage_bps, max_position,
                                enable_compound, compound_win_step, compound_loss_step, compound_floor, compound_cap)
        per_stats.append(dict(标的=sym, **stats))
        per_equity[sym] = bt["equity"]
        per_rets[sym] = bt["strategy_ret"]

    stats_df = pd.DataFrame(per_stats)
    w = np.ones(len(symbols))/len(symbols)
    rets_df = pd.DataFrame(per_rets)
    port_ret = (rets_df * w).sum(axis=1)
    port_equity = (1+port_ret).cumprod()*initial_cash
    eq = port_equity
    daily_ret = port_ret
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (252/len(eq)) - 1 if len(eq) > 1 else 0.0
    vol = daily_ret.std()*np.sqrt(252)
    sharpe = (daily_ret.mean()*252)/(vol+1e-12)
    roll_max = eq.cummax(); max_dd = ((roll_max-eq)/roll_max).max()
    stats_port = {
        "累计收益率": float(eq.iloc[-1]/eq.iloc[0]-1),
        "年化收益率": float(cagr),
        "年化波动率": float(vol),
        "夏普比率": float(sharpe),
        "最大回撤": float(max_dd),
        "最终净值": float(eq.iloc[-1])
    }
    return stats_df, port_equity, stats_port, per_equity

def risk_metrics(equity: pd.Series, ret: pd.Series, vol_window: int = 30, var_q: float = 0.95):
    roll_max = equity.cummax()
    drawdown = equity/roll_max - 1.0
    ann_vol = ret.rolling(vol_window).std() * np.sqrt(252)
    if len(ret) > 0:
        var = -ret.rolling(vol_window).apply(lambda x: np.percentile(x, (1-var_q)*100)).dropna()
        var_series = var
    else:
        var_series = pd.Series(dtype=float)
    return drawdown, ann_vol, var_series

def wecom_push(webhook_url: str, text: str):
    try:
        payload = {"msgtype":"text","text":{"content": text[:2000]}}
        r = requests.post(webhook_url, json=payload, timeout=10)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

def combo_performance_card(strats, indicators):
    n = len(strats) + len(indicators)
    if n >= 4 or (("背离反转 (MACD/RSI)" in strats) and ("MACD" in indicators) and ("RSI" in indicators)):
        return {"胜率": "≈79%", "信号准确率": "≈89%", "风险降低": "≈35%", "建议": "背离+成交量+趋势过滤效果最佳"}
    if ("MACD" in indicators and "RSI" in indicators) or ("趋势跟踪 (MACD战法)" in strats and ("RSI" in indicators or "移动平均线 (MA)" in indicators)):
        return {"胜率": "≈73%", "信号准确率": "≈86%", "风险降低": "≈42%", "建议": "MA 多头排列 + MACD 零轴上金叉"}
    if n == 2:
        return {"胜率": "≈65%", "信号准确率": "≈75%", "风险降低": "≈20%", "建议": "加入趋势过滤或量能确认"}
    if n == 1:
        return {"胜率": "≈58%", "信号准确率": "≈67%", "风险降低": "≈21%", "建议": "建议至少使用两类指标"}
    return None

# =============== Main ===============
symbols = get_symbol_list()
main_symbol = symbols[0]

# 主视图：K 线 + 指标 + 买卖点 + 背离标注
try:
    df_main = load_symbol_df(main_symbol, main_bar)
    df_ind = add_indicators(df_main, sma_fast, sma_slow, ema_fast, ema_slow, rsi_period, boll_window, macd_signal)
    flags = {"SMA": strat_ma_cross, "EMA": strat_ema_cross, "RSI": strat_rsi, "MACD": strat_macd, "BOLL": strat_boll}
    thresholds = {"rsi_buy": rsi_buy, "rsi_sell": rsi_sell}
    sigs = strategy_signals(df_ind, flags, thresholds, enable_volume_confirm)
    combined = combine_signals(sigs, combine_mode)
    bt_single, stats_single, trades_df = backtest(
        df_ind, combined, initial_cash, fee_bps, slippage_bps, max_position,
        enable_compound, compound_win_step, compound_loss_step, compound_floor, compound_cap
    )

    st.subheader(f"🕯️ 主视图K线图（{main_symbol}）")
    if {"open","high","low","close"} <= set(df_main.columns):
        fig_k = go.Figure(data=[go.Candlestick(x=df_main.index,
                                               open=df_main["open"], high=df_main["high"],
                                               low=df_main["low"], close=df_main["close"],
                                               name="K线")])
    else:
        fig_k = go.Figure(data=[go.Scatter(x=df_main.index, y=df_main["price"], name="价格")])
    # Overlays
    fig_k.add_trace(go.Scatter(x=df_ind.index, y=df_ind["SMA_fast"], name=f"SMA{sma_fast}", opacity=0.7))
    fig_k.add_trace(go.Scatter(x=df_ind.index, y=df_ind["SMA_slow"], name=f"SMA{sma_slow}", opacity=0.7))
    fig_k.add_trace(go.Scatter(x=df_ind.index, y=df_ind["EMA_fast"], name=f"EMA{ema_fast}", opacity=0.5))
    fig_k.add_trace(go.Scatter(x=df_ind.index, y=df_ind["EMA_slow"], name=f"EMA{ema_slow}", opacity=0.5))
    fig_k.add_trace(go.Scatter(x=df_ind.index, y=df_ind["BOLL_H"], name="BOLL_H", line=dict(dash="dot")))
    fig_k.add_trace(go.Scatter(x=df_ind.index, y=df_ind["BOLL_L"], name="BOLL_L", line=dict(dash="dot")))
    # Buy/Sell markers
    pos = bt_single["pos"].fillna(0)
    buys = df_main.index[(pos.shift(1) <= 0) & (pos > 0)]
    sells = df_main.index[(pos.shift(1) > 0) & (pos <= 0)]
    fig_k.add_trace(go.Scatter(x=buys, y=df_main.loc[buys, "price"], mode="markers", name="买入",
                               marker=dict(symbol="triangle-up", size=10)))
    fig_k.add_trace(go.Scatter(x=sells, y=df_main.loc[sells, "price"], mode="markers", name="卖出",
                               marker=dict(symbol="triangle-down", size=10)))

    div = detect_rsi_divergence(df_ind)
    bull_idx = div.index[div["bull_div"]]
    bear_idx = div.index[div["bear_div"]]
    if len(bull_idx)>0:
        fig_k.add_trace(go.Scatter(x=bull_idx, y=df_main.loc[bull_idx, "price"], mode="markers+text", name="底背离",
                                   text=["底背离"]*len(bull_idx), textposition="top center"))
    if len(bear_idx)>0:
        fig_k.add_trace(go.Scatter(x=bear_idx, y=df_main.loc[bear_idx, "price"], mode="markers+text", name="顶背离",
                                   text=["顶背离"]*len(bear_idx), textposition="bottom center"))

    fig_k.update_layout(hovermode="x unified",
                        xaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor", showline=True),
                        yaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor"),
                        hoverlabel=dict(bgcolor="white"))
    st.plotly_chart(fig_k, use_container_width=True)

    # 组合胜率表现卡片
    perf = combo_performance_card(
        strat_select,
        ["MACD" if strat_macd else "", "RSI" if strat_rsi else "",
         "移动平均线 (MA)" if (strat_ma_cross or strat_ema_cross) else "",
         "成交量 (Volume)" if enable_volume_confirm else ""]
    )
    st.subheader("📈 组合胜率表现（估算）")
    if perf:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("胜率", perf["胜率"]); c2.metric("信号准确率", perf["信号准确率"])
        c3.metric("风险降低", perf["风险降低"]); c4.write(perf["建议"])
    else:
        st.caption("选择策略与指标后，将显示估算表现。")

    st.subheader("📋 单标绩效指标")
    st.json(stats_single)

    st.subheader("💰 净值曲线（单标）")
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=bt_single.index, y=bt_single["equity"], name="策略净值"))
    fig_eq.add_trace(go.Scatter(x=bt_single.index, y=bt_single["buyhold"], name="买入持有"))
    st.plotly_chart(fig_eq, use_container_width=True)

except Exception as e:
    st.error(f"主视图失败：{e}")

# =============== Portfolio Backtest ===============
st.markdown("---")
st.subheader("📦 多标的组合回测（等权）")
if st.button("▶️ 运行组合回测"):
    try:
        stats_df, port_equity, stats_port, per_equity = portfolio_backtest(symbols, main_bar)
        st.write("🔎 逐标绩效："); st.dataframe(stats_df)
        st.write("🏆 组合绩效："); st.json(stats_port)
        figp = go.Figure()
        figp.add_trace(go.Scatter(x=port_equity.index, y=port_equity.values, name="组合净值"))
        for sym, eq in per_equity.items():
            figp.add_trace(go.Scatter(x=eq.index, y=eq.values, name=f"{sym}"))
        st.plotly_chart(figp, use_container_width=True)
    except Exception as e:
        st.error(f"组合回测失败：{e}")

# =============== Risk Panel ===============
st.markdown("---")
st.subheader("🛡 风控面板（回撤/波动/VaR） + 企业微信推送")
try:
    eq = bt_single["equity"]; ret = bt_single["strategy_ret"]
    var_q = 0.95 if var_conf == "95%" else 0.99
    dd_series, ann_vol_series, var_series = risk_metrics(eq, ret, vol_window, var_q)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("当前回撤", f"{(1 - eq.iloc[-1]/eq.cummax().iloc[-1])*100:.2f}%")
    with c2:
        st.metric(f"{vol_window}日年化波动", f"{ann_vol_series.iloc[-1]*100:.2f}%")
    with c3:
        st.metric(f"{var_conf} 1日VaR", f"{(var_series.iloc[-1]*100 if len(var_series)>0 else 0):.2f}%")

    fig_risk = go.Figure()
    fig_risk.add_trace(go.Scatter(x=dd_series.index, y=dd_series.values*100, name="回撤(%)"))
    fig_risk.add_trace(go.Scatter(x=ann_vol_series.index, y=ann_vol_series.values*100, name="年化波动(%)"))
    if len(var_series)>0:
        fig_risk.add_trace(go.Scatter(x=var_series.index, y=var_series.values*100, name=f"VaR {var_conf}(%)"))
    st.plotly_chart(fig_risk, use_container_width=True)

    alerts = []
    curr_dd = 1 - eq.iloc[-1]/eq.cummax().iloc[-1]
    if curr_dd*100 >= dd_alert: alerts.append(f"⚠️ 回撤达 {curr_dd*100:.2f}% ≥ 阈值 {dd_alert}%")
    if len(ann_vol_series)>0 and ann_vol_series.iloc[-1]*100 >= vol_alert:
        alerts.append(f"⚠️ 年化波动 {ann_vol_series.iloc[-1]*100:.2f}% ≥ 阈值 {vol_alert}%")

    if alerts:
        st.warning(" | ".join(alerts))
        if webhook_url:
            text = "📣 风控告警：\n" + "\n".join(alerts) + f"\n时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            code, resp = wecom_push(webhook_url, text)
            if code == 200: st.success("已推送到企业微信机器人")
            else: st.error(f"推送失败：{resp}")
    if test_push and webhook_url:
        code, resp = wecom_push(webhook_url, "✅ 这是来自 Legend Quant 的测试通知")
        if code == 200: st.success("测试推送成功")
        else: st.error(f"测试推送失败：{resp}")
except Exception as e:
    st.error(f"风控面板失败：{e}")

# =============== Multi-timeframe Backtest ===============
st.markdown("---")
st.subheader("🔁 多周期联动回测绩效对比")
def multi_tf_backtest(tf_list):
    rows = []; curves = {}
    for bar in tf_list:
        try:
            df_tf = load_symbol_df(symbols[0], bar if data_source=="OKX 公共行情" else main_bar)
            df_tf = add_indicators(df_tf, sma_fast, sma_slow, ema_fast, ema_slow, rsi_period, boll_window, macd_signal)
            flags = {"SMA": strat_ma_cross, "EMA": strat_ema_cross, "RSI": strat_rsi, "MACD": strat_macd, "BOLL": strat_boll}
            thresholds = {"rsi_buy": rsi_buy, "rsi_sell": rsi_sell}
            sigs_tf = strategy_signals(df_tf, flags, thresholds, enable_volume_confirm)
            comb_tf = combine_signals(sigs_tf, combine_mode)
            bt_tf, stats_tf, _ = backtest(df_tf, comb_tf, initial_cash, fee_bps, slippage_bps, max_position,
                                          enable_compound, compound_win_step, compound_loss_step, compound_floor, compound_cap)
            row = {"周期": bar}; row.update(stats_tf); rows.append(row)
            curves[bar] = bt_tf["equity"]
        except Exception as ex:
            rows.append({"周期": bar, "错误": str(ex)})
    return pd.DataFrame(rows), curves

if st.button("▶️ 运行多周期联动回测"):
    res_df, curves = multi_tf_backtest(multi_timeframes)
    st.dataframe(res_df)
    if curves:
        fig3 = go.Figure()
        for bar, eq in curves.items():
            fig3.add_trace(go.Scatter(x=eq.index, y=eq.values, name=str(bar)))
        st.plotly_chart(fig3, use_container_width=True)

# =============== Grid Search ===============
st.markdown("---")
st.subheader("🧪 参数网格搜索")
def parse_list(s):
    try: return [int(x.strip()) for x in s.split(",") if x.strip()]
    except Exception: return []

if enable_grid:
    sma_fast_list = parse_list(grid_sma_fast)
    sma_slow_list = parse_list(grid_sma_slow)
    rsi_buy_list = parse_list(grid_rsi_buy)
    rsi_sell_list = parse_list(grid_rsi_sell)

    combos = list(product(sma_fast_list, sma_slow_list, rsi_buy_list, rsi_sell_list))
    if len(combos) == 0:
        st.warning("请至少填写一种参数组合")
    else:
        if len(combos) > grid_max_combo:
            st.warning(f"组合数 {len(combos)} 超过上限 {grid_max_combo}，仅取前 {grid_max_combo} 组")
            combos = combos[:grid_max_combo]

        result_rows = []; curves_grid = {}
        progress = st.progress(0.0)
        for i, (sf, ss, rb, rs) in enumerate(combos, start=1):
            try:
                df_g = add_indicators(df_main, sf, ss, ema_fast, ema_slow, rsi_period, boll_window, macd_signal)
                flags_g = {"SMA": strat_ma_cross, "EMA": strat_ema_cross, "RSI": strat_rsi, "MACD": strat_macd, "BOLL": strat_boll}
                th_g = {"rsi_buy": rb, "rsi_sell": rs}
                sigs_g = strategy_signals(df_g, flags_g, th_g, enable_volume_confirm)
                comb_g = combine_signals(sigs_g, combine_mode)
                bt_g, stats_g, _ = backtest(df_g, comb_g, initial_cash, fee_bps, slippage_bps, max_position,
                                            enable_compound, compound_win_step, compound_loss_step, compound_floor, compound_cap)
                row = {"SMA快": sf, "SMA慢": ss, "RSI买": rb, "RSI卖": rs}; row.update(stats_g)
                result_rows.append(row); curves_grid[(sf,ss,rb,rs)] = bt_g["equity"]
            except Exception as e:
                row = {"SMA快": sf, "SMA慢": ss, "RSI买": rb, "RSI卖": rs, "错误": str(e)}
                result_rows.append(row)
            progress.progress(i/len(combos))

        res_df = pd.DataFrame(result_rows)
        if not res_df.empty and "错误" not in res_df.columns:
            if objective == "年化收益率": res_df = res_df.sort_values("年化收益率", ascending=False)
            elif objective == "夏普比率": res_df = res_df.sort_values("夏普比率", ascending=False)
            else: res_df = res_df.sort_values("最大回撤", ascending=True)

        st.subheader("📋 网格搜索结果表"); st.dataframe(res_df)
        if not res_df.empty:
            csv_bytes = res_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 下载批量回测报告（CSV）", data=csv_bytes, file_name="grid_search_report.csv", mime="text/csv")
        if not res_df.empty and "错误" not in res_df.columns:
            st.subheader(f"🏆 最优前 {topn} 组净值曲线对比")
            top_params = res_df.head(topn)[["SMA快","SMA慢","RSI买","RSI卖"]].to_records(index=False)
            fig4 = go.Figure()
            for param in top_params:
                key = tuple(int(x) for x in param)
                eq = curves_grid.get(key)
                if eq is not None:
                    label = f"SF{key[0]} SS{key[1]} RB{key[2]} RS{key[3]}"
                    fig4.add_trace(go.Scatter(x=eq.index, y=eq.values, name=label))
            st.plotly_chart(fig4, use_container_width=True)
else:
    st.caption("未启用网格搜索。")

# =============== Arbitrage Panel ===============
st.markdown("---")
st.subheader("🤝 资金费率套利监控（OKX 永续）")
if data_source == "OKX 公共行情":
    inst_list = [s.strip() for s in okx_inst_multi.split(",") if s.strip()]
    rows = []
    for inst in inst_list:
        if not inst.endswith("-SWAP"):
            swap = inst.split("-")[0] + "-" + inst.split("-")[1] + "-SWAP"
        else:
            swap = inst
        try:
            info = load_okx_funding(swap)
            fr = info.get("fundingRate", 0.0)   # per 8h
            ann = ((1+fr)**(24/8*365) - 1) if fr != 0 else 0.0
            rows.append({"InstId": swap, "资金费率(8h)": fr, "年化(约)": ann, "下次结算": info.get("fundingTime","")})
        except Exception as e:
            rows.append({"InstId": swap, "错误": str(e)})
    if rows:
        df_fr = pd.DataFrame(rows)
        st.dataframe(df_fr)
        thr = st.slider("套利阈值：年化大于（%）才提示", 0.0, 100.0, 15.0, 0.5)
        tips = []
        for _, r in df_fr.iterrows():
            if "年化(约)" in r and isinstance(r["年化(约)"], (int,float)) and r["年化(约)"]*100 >= thr:
                tips.append(f"{r['InstId']}: 年化≈{r['年化(约)']*100:.2f}% → 建议 买现货 + 做空永续（正费率）")
        if tips:
            st.success(" | ".join(tips))
        else:
            st.info("当前无显著套利机会（高于阈值）。")
else:
    st.caption("切换到 OKX 数据源以查看资金费率套利监控。")

# =============== Trading Panel (Optional) ===============
st.markdown("---")
st.subheader("⚡ OKX 交易面板（可选）")
def okx_flag():
    return "1" if env_choice == "模拟盘" else "0"
def trade_api():
    if not OKX_AVAILABLE:
        st.error("未安装 okx SDK，请先 pip install okx")
        return None
    return TradeAPI(okx_api, okx_secret, okx_passphrase, False, okx_flag())

if enable_trading_panel:
    if okx_api and okx_secret and okx_passphrase:
        api = trade_api()
        if api:
            side = st.selectbox("方向", ["buy","sell"], index=0)
            tdMode = st.selectbox("交易模式", ["cash","cross","isolated"], index=0)
            qty = st.number_input("数量", min_value=0.0001, step=0.0001, value=0.001)
            ordType = st.selectbox("订单类型", ["market","limit"], index=0)
            px = st.number_input("限价价格", min_value=0.1, step=0.1) if ordType=="limit" else None
            inst_for_trade = st.text_input("下单 InstId", value=symbols[0] if data_source=="OKX 公共行情" else "BTC-USDT")
            c1,c2,c3 = st.columns(3)
            if c1.button("🚀 提交订单"):
                try:
                    res = api.place_order(instId=inst_for_trade, tdMode=tdMode, side=side,
                                          ordType=ordType, sz=str(qty), px=str(px) if px else None)
                    st.success(res)
                except Exception as e:
                    st.error(str(e))
            ordId = c2.text_input("订单ID（撤单/查询）", "")
            if c2.button("❌ 撤单"):
                try:
                    res = api.cancel_order(instId=inst_for_trade, ordId=ordId)
                    st.info(res)
                except Exception as e:
                    st.error(str(e))
            if c3.button("🔍 查询订单"):
                try:
                    res = api.get_orders(instId=inst_for_trade, state="live")
                    st.write(res)
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("在侧边栏输入 OKX API/Secret/Passphrase 并勾选“启用交易面板”。")
else:
    st.caption("未启用交易面板。")