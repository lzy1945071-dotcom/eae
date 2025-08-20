# app.py — Legend Quant Terminal Elite v3 FIX10 (TV风格 + 多指标 + 实时策略增强)
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import ta
import math
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Legend Quant Terminal Elite v3 FIX10", layout="wide")
st.title("💎 Legend Quant Terminal Elite v3 FIX10")

# 初始化会话状态
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = None
if 'show_checkmark' not in st.session_state:
    st.session_state.show_checkmark = False

# ========================= 添加自动刷新功能 =========================
st.sidebar.header("🔄 刷新")
auto_refresh = st.sidebar.checkbox("启用自动刷新", value=False)
if auto_refresh:
    refresh_interval = st.sidebar.number_input("自动刷新间隔(秒)", min_value=1, value=60, step=1)
    st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")

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

# ========================= 添加手动刷新按钮 =========================
col1, col2, col3 = st.columns([6, 1, 2])
with col2:
    if st.button("🔄 刷新", use_container_width=True, key="refresh_button"):
        # 清除缓存以强制刷新数据
        st.cache_data.clear()
        # 更新刷新时间和显示状态
        st.session_state.last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.show_checkmark = True
        # 刷新页面
        st.rerun()

# 显示刷新确认和时间
with col3:
    if st.session_state.show_checkmark:
        st.success("✅ 数据已刷新")
        if st.session_state.last_refresh_time:
            st.caption(f"最后刷新: {st.session_state.last_refresh_time}")
    elif st.session_state.last_refresh_time:
        st.caption(f"最后刷新: {st.session_state.last_refresh_time}")

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

# 标的与周期
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

use_ma = st.sidebar.checkbox("MA（简单均线）", True)
ma_periods_text = st.sidebar.text_input("MA 周期（逗号分隔）", value="20,50")
use_ema = st.sidebar.checkbox("EMA（指数均线）", True)
ema_periods_text = st.sidebar.text_input("EMA 周期（逗号分隔）", value="200")
use_boll = st.sidebar.checkbox("布林带（BOLL）", False)
boll_window = st.sidebar.number_input("BOLL 窗口", min_value=5, value=20, step=1)
boll_std = st.sidebar.number_input("BOLL 标准差倍数", min_value=1.0, value=2.0, step=0.5)
use_macd = st.sidebar.checkbox("MACD（副图）", True)
macd_fast = st.sidebar.number_input("MACD 快线", min_value=2, value=12, step=1)
macd_slow = st.sidebar.number_input("MACD 慢线", min_value=5, value=26, step=1)
macd_sig = st.sidebar.number_input("MACD 信号线", min_value=2, value=9, step=1)
use_rsi = st.sidebar.checkbox("RSI（副图）", True)
rsi_window = st.sidebar.number_input("RSI 窗口", min_value=5, value=14, step=1)
use_atr = st.sidebar.checkbox("ATR（用于风险/止盈止损）", True)
atr_window = st.sidebar.number_input("ATR 窗口", min_value=5, value=14, step=1)

# ===== 新增：更多常用指标 =====
st.sidebar.markdown("**（新增）更多常用指标**")
use_vwap = st.sidebar.checkbox("VWAP（成交量加权均价）", True)
use_adx = st.sidebar.checkbox("ADX（趋势强度）", True)
adx_window = st.sidebar.number_input("ADX 窗口", min_value=5, value=14, step=1)
use_stoch = st.sidebar.checkbox("Stochastic 随机指标（副图）", False)
stoch_k = st.sidebar.number_input("%K 窗口", min_value=3, value=14, step=1)
stoch_d = st.sidebar.number_input("%D 平滑", min_value=1, value=3, step=1)
stoch_smooth = st.sidebar.number_input("平滑窗口", min_value=1, value=3, step=1)
use_stochrsi = st.sidebar.checkbox("StochRSI（副图）", False)
stochrsi_window = st.sidebar.number_input("StochRSI 窗口", min_value=5, value=14, step=1)
use_mfi = st.sidebar.checkbox("MFI 资金流量（副图）", False)
mfi_window = st.sidebar.number_input("MFI 窗口", min_value=5, value=14, step=1)
use_cci = st.sidebar.checkbox("CCI（副图）", False)
cci_window = st.sidebar.number_input("CCI 窗口", min_value=5, value=20, step=1)
use_obv = st.sidebar.checkbox("OBV 能量潮（副图）", False)
use_psar = st.sidebar.checkbox("PSAR 抛物线转向", False)
psar_step = st.sidebar.number_input("PSAR 步长", min_value=0.001, value=0.02, step=0.001, format="%.3f")
psar_max_step = st.sidebar.number_input("PSAR 最大步长", min_value=0.01, value=0.2, step=0.01, format="%.2f")

# ===== 新增：KDJ指标 =====
use_kdj = st.sidebar.checkbox("KDJ（副图）", False)
kdj_window = st.sidebar.number_input("KDJ 窗口", min_value=5, value=9, step=1)
kdj_smooth_k = st.sidebar.number_input("K值平滑", min_value=1, value=3, step=1)
kdj_smooth_d = st.sidebar.number_input("D值平滑", min_value=1, value=3, step=1)

# ========================= Sidebar: ④ 参数推荐（说明） =========================
st.sidebar.header("④ 参数推荐（说明）")
st.sidebar.markdown('''
**加密货币**：
- MACD: **12/26/9**
- RSI: **14**（阈：90/73更宽容）
- KDJ: **9,3,3**（超买>80，超卖<20）
- BOLL: **20 ± 2σ**
- MA: **20/50**
- EMA: **200**
- VWAP: 日内/跨周期观测
- ADX: **14**（>25趋势显著）

**美股**：
- MACD: **12/26/9**
- RSI: **14**（阈：70/30）
- KDJ: **9,3,3**（超买>80，超卖<20）
- MA: **50/200**
- ADX: **14**（>25趋势显著）
- VWAP: 日内交易重要参考

**A股**：
- MACD: **10/30/9**
- RSI: **14**（阈：80/20）
- KDJ: **9,3,3**（超买>80，超卖<20）
- MA: **5/10/30**
- BOLL: **20 ± 2σ**
- VWAP: 主力资金参考
''')

# ========================= Sidebar: ⑤ 风控参数 =========================
st.sidebar.header("⑤ 风控参数")
account_value = st.sidebar.number_input("账户总资金", min_value=1.0, value=1000.0, step=10.0)
risk_pct = st.sidebar.slider("单笔风险（%）", 0.1, 2.0, 0.5, 0.1)
leverage = st.sidebar.slider("杠杆倍数", 1, 10, 1, 1)
daily_loss_limit = st.sidebar.number_input("每日亏损阈值（%）", min_value=0.5, value=2.0, step=0.5)
weekly_loss_limit = st.sidebar.number_input("每周亏损阈值（%）", min_value=1.0, value=5.0, step=0.5)

# ========================= Data Loaders =========================
def _cg_days_from_interval(sel: str) -> str:
    if sel.startswith("1d"): return "180"
    if sel.startswith("1w"): return "365"
    if sel.startswith("1M"): return "365"
    if sel.startswith("max"): return "max"
    return "180"

@st.cache_data(ttl=900)
def load_coingecko_ohlc_robust(coin_id: str, interval_sel: str):
    days = _cg_days_from_interval(interval_sel)
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        r = requests.get(url, params={"vs_currency": "usd", "days": days}, timeout=20)
        if r.status_code == 200:
            arr = r.json()
            if isinstance(arr, list) and len(arr) > 0:
                rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in arr]
                return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close"]).set_index("Date")
    except Exception:
        pass
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
    if not api_base_url:
        return load_coingecko_ohlc_robust(coin_id, interval_sel)
    try:
        url = f"{api_base_url.rstrip('/')}/ohlc"
        r = requests.get(url, params={"symbol": coin_id, "period": "1d"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            rows = [(pd.to_datetime(x[0], unit="ms"), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in data]
            return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close"]).set_index("Date")
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
    if not data: return pd.DataFrame()
    rows = []
    for a in reversed(data):
        ts = int(a[0]); o=float(a[1]); h=float(a[2]); l=float(a[3]); c=float(a[4]); v=float(a[5])
        rows.append((pd.to_datetime(ts, unit="ms"), o,h,l,c,v))
    return pd.DataFrame(rows, columns=["Date","Open","High","Low","Close","Volume"]).set_index("Date")

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
    close, high, low = out["Close"], out["High"], out["Low"]
    vol = out["Volume"] if "Volume" in out.columns else pd.Series(np.nan, index=out.index, name="Volume")
    if "Volume" not in out.columns: out["Volume"] = np.nan

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
        out["BOLL_M"], out["BOLL_U"], out["BOLL_L"] = boll.bollinger_mavg(), boll.bollinger_hband(), boll.bollinger_lband()

    # MACD
    if use_macd:
        macd_ind = ta.trend.MACD(close, window_slow=int(macd_slow), window_fast=int(macd_fast), window_sign=int(macd_sig))
        out["MACD"], out["MACD_signal"], out["MACD_hist"] = macd_ind.macd(), macd_ind.macd_signal(), macd_ind.macd_diff()

    # RSI
    if use_rsi: out["RSI"] = ta.momentum.RSIIndicator(close, window=int(rsi_window)).rsi()

    # ATR
    if use_atr: out["ATR"] = ta.volatility.AverageTrueRange(high, low, close, window=int(atr_window)).average_true_range()

    # ===== 新增指标 =====
    if use_vwap:
        vwap = ta.volume.VolumeWeightedAveragePrice(high=high, low=low, close=close, volume=vol, window=14)
        out["VWAP"] = vwap.volume_weighted_average_price()
    if use_adx:
        adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close, window=int(adx_window))
        out["ADX"] = adx_ind.adx()
        out["DIP"] = adx_ind.adx_pos()
        out["DIN"] = adx_ind.adx_neg()
    if use_stoch:
        stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=int(stoch_k), smooth_window=int(stoch_smooth))
        out["STOCH_K"] = stoch.stoch()
        out["STOCH_D"] = stoch.stoch_signal() if hasattr(stoch, "stoch_signal") else out["STOCH_K"].rolling(int(stoch_d)).mean()
    if use_stochrsi:
        srsi = ta.momentum.StochRSIIndicator(close=close, window=int(stochrsi_window))
        out["StochRSI_K"] = srsi.stochrsi_k()
        out["StochRSI_D"] = srsi.stochrsi_d()
    if use_mfi:
        mfi = ta.volume.MFIIndicator(high=high, low=low, close=close, volume=vol, window=int(mfi_window))
        out["MFI"] = mfi.money_flow_index()
    if use_cci:
        cci = ta.trend.CCIIndicator(high=high, low=low, close=close, window=int(cci_window))
        out["CCI"] = cci.cci()
    if use_obv:
        obv = ta.volume.OnBalanceVolumeIndicator(close=close, volume=vol)
        out["OBV"] = obv.on_balance_volume()
    if use_psar:
        try:
            ps = ta.trend.PSARIndicator(high=high, low=low, close=close, step=float(psar_step), max_step=float(psar_max_step))
            out["PSAR"] = ps.psar()
        except Exception:
            out["PSAR"] = np.nan
            
    # ===== 新增KDJ指标 =====
    if use_kdj:
        # 计算KDJ指标
        low_min = low.rolling(window=int(kdj_window)).min()
        high_max = high.rolling(window=int(kdj_window)).max()
        rsv = (close - low_min) / (high_max - low_min) * 100
        out["KDJ_K"] = rsv.rolling(window=int(kdj_smooth_k)).mean()
        out["KDJ_D"] = out["KDJ_K"].rolling(window=int(kdj_smooth_d)).mean()
        out["KDJ_J"] = 3 * out["KDJ_K"] - 2 * out["KDJ_D"]

    return out

dfi = add_indicators(df).dropna(how="all")

# ========================= 信号检测函数 =========================
def detect_signals(df):
    """检测各种交易信号"""
    signals = pd.DataFrame(index=df.index)
    
    # MA交叉信号
    if "MA20" in df.columns and "MA50" in df.columns:
        signals["MA_Cross"] = np.where(
            (df["MA20"] > df["MA50"]) & (df["MA20"].shift(1) <= df["MA50"].shift(1)), 
            "Buy", 
            np.where(
                (df["MA20"] < df["MA50"]) & (df["MA20"].shift(1) >= df["MA50"].shift(1)), 
                "Sell", 
                None
            )
        )
    
    # MACD信号
    if all(c in df.columns for c in ["MACD","MACD_signal"]):
        signals["MACD_Cross"] = np.where(
            (df["MACD"] > df["MACD_signal"]) & (df["MACD"].shift(1) <= df["MACD_signal"].shift(1)), 
            "Buy", 
            np.where(
                (df["MACD"] < df["MACD_signal"]) & (df["MACD"].shift(1) >= df["MACD_signal"].shift(1)), 
                "Sell", 
                None
            )
        )
    
    # RSI超买超卖信号
    if "RSI" in df.columns:
        signals["RSI_Overbought"] = np.where(df["RSI"] > 70, "Sell", None)
        signals["RSI_Oversold"] = np.where(df["RSI"] < 30, "Buy", None)
    
    # KDJ信号
    if all(c in df.columns for c in ["KDJ_K","KDJ_D"]):
        signals["KDJ_Cross"] = np.where(
            (df["KDJ_K"] > df["KDJ_D"]) & (df["KDJ_K"].shift(1) <= df["KDJ_D"].shift(1)), 
            "Buy", 
            np.where(
                (df["KDJ_K"] < df["KDJ_D"]) & (df["KDJ_K"].shift(1) >= df["KDJ_D"].shift(1)), 
                "Sell", 
                None
            )
        )
        signals["KDJ_Overbought"] = np.where(df["KDJ_K"] > 80, "Sell", None)
        signals["KDJ_Oversold"] = np.where(df["KDJ_K"] < 20, "Buy", None)
    
    return signals

# 检测信号
signals = detect_signals(dfi)

# ========================= 支撑阻力计算 =========================
def calculate_support_resistance(df, window=20):
    """计算支撑和阻力位"""
    # 近期高点和低点
    recent_high = df["High"].rolling(window=window).max()
    recent_low = df["Low"].rolling(window=window).min()
    
    # 使用布林带作为动态支撑阻力
    if "BOLL_U" in df.columns and "BOLL_L" in df.columns:
        resistance = df["BOLL_U"]
        support = df["BOLL_L"]
    else:
        # 如果没有布林带，使用近期高点和低点
        resistance = recent_high
        support = recent_low
    
    return support, resistance

support, resistance = calculate_support_resistance(dfi)

# ========================= TradingView 风格图表 =========================
st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=dfi.index, open=dfi["Open"], high=dfi["High"], low=dfi["Low"], close=dfi["Close"], name="K线",
    customdata=df[['volume']],
    hovertemplate=(
        '时间: %{x}<br>' +
        '开盘: %{open}<br>' +
        '最高: %{high}<br>' +
        '最低: %{low}<br>' +
        '收盘: %{close}<br>' +
        '成交量: %{customdata[0]}<extra></extra>'
    )
))

# 添加均线 - 默认隐藏
if use_ma:
    ma_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    for i, p in enumerate(parse_int_list(ma_periods_text)):
        col = f"MA{p}"
        if col in dfi.columns: 
            fig.add_trace(go.Scatter(
                x=dfi.index, 
                y=dfi[col], 
                mode="lines", 
                name=col, 
                yaxis="y",
                line=dict(color=ma_colors[i % len(ma_colors)]),
                visible="legendonly"  # 默认隐藏
            ))

if use_ema:
    ema_colors = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#dd4477", "#66aa00", "#b82e2e", "#316395"]
    for i, p in enumerate(parse_int_list(ema_periods_text)):
        col = f"EMA{p}"
        if col in dfi.columns: 
            fig.add_trace(go.Scatter(
                x=dfi.index, 
                y=dfi[col], 
                mode="lines", 
                name=col, 
                yaxis="y",
                line=dict(color=ema_colors[i % len(ema_colors)]),
                visible="legendonly"  # 默认隐藏
            ))

if use_boll:
    boll_colors = ["#3d9970", "#ff4136", "#85144b"]
    for i, (col, nm) in enumerate([("BOLL_U","BOLL 上轨"),("BOLL_M","BOLL 中轨"),("BOLL_L","BOLL 下轨")]):
        if col in dfi.columns: 
            fig.add_trace(go.Scatter(
                x=dfi.index, 
                y=dfi[col], 
                mode="lines", 
                name=nm, 
                yaxis="y",
                line=dict(color=boll_colors[i % len(boll_colors)]),
                visible="legendonly"  # 默认隐藏
            ))

# 添加支撑阻力线 - 默认隐藏
fig.add_trace(go.Scatter(
    x=dfi.index, 
    y=support, 
    mode="lines", 
    name="支撑", 
    line=dict(color="#00cc96", dash="dash"), 
    yaxis="y",
    visible="legendonly"  # 默认隐藏
))
fig.add_trace(go.Scatter(
    x=dfi.index, 
    y=resistance, 
    mode="lines", 
    name="阻力", 
    line=dict(color="#ef553b", dash="dash"), 
    yaxis="y",
    visible="legendonly"  # 默认隐藏
))

# 添加买卖信号 - 默认隐藏
buy_signals = signals[signals.isin(["Buy"]).any(axis=1)]
sell_signals = signals[signals.isin(["Sell"]).any(axis=1)]

if not buy_signals.empty:
    buy_points = dfi.loc[buy_signals.index]
    fig.add_trace(go.Scatter(
        x=buy_points.index, 
        y=buy_points["Low"] * 0.99, 
        mode="markers", 
        name="买入信号",
        marker=dict(symbol="triangle-up", size=10, color="#00cc96"),
        visible="legendonly"  # 默认隐藏
    ))

if not sell_signals.empty:
    sell_points = dfi.loc[sell_signals.index]
    fig.add_trace(go.Scatter(
        x=sell_points.index, 
        y=sell_points["High"] * 1.01, 
        mode="markers", 
        name="卖出信号",
        marker=dict(symbol="triangle-down", size=10, color="#ef553b"),
        visible="legendonly"  # 默认隐藏
    ))

# 添加成交量 - 默认显示
vol_colors = np.where(dfi["Close"] >= dfi["Open"], "rgba(38,166,91,0.7)", "rgba(239,83,80,0.7)")
if "Volume" in dfi.columns and not dfi["Volume"].isna().all():
    fig.add_trace(go.Bar(
        x=dfi.index, 
        y=dfi["Volume"], 
        name="成交量", 
        yaxis="y2", 
        marker_color=vol_colors,
        opacity=0.7
    ))

# 添加MACD副图 - 默认显示
if use_macd and all(c in dfi.columns for c in ["MACD","MACD_signal","MACD_hist"]):
    fig.add_trace(go.Scatter(
        x=dfi.index, 
        y=dfi["MACD"], 
        name="MACD", 
        yaxis="y3", 
        mode="lines",
        line=dict(color="#3366cc")
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index, 
        y=dfi["MACD_signal"], 
        name="Signal", 
        yaxis="y3", 
        mode="lines",
        line=dict(color="#ff9900")
    ))
    fig.add_trace(go.Bar(
        x=dfi.index, 
        y=dfi["MACD_hist"], 
        name="MACD 柱", 
        yaxis="y3", 
        opacity=0.4,
        marker_color=np.where(dfi["MACD_hist"] >= 0, "#00cc96", "#ef553b")
    ))

# 添加RSI副图 - 默认隐藏
if use_rsi and "RSI" in dfi.columns:
    fig.add_trace(go.Scatter(
        x=dfi.index, 
        y=dfi["RSI"], 
        name="RSI", 
        yaxis="y4", 
        mode="lines",
        line=dict(color="#17becf")
    ))
    # 添加RSI超买超卖线
    fig.add_hline(y=70, line_dash="dash", line_color="red", yref="y4", opacity=0.5)
    fig.add_hline(y=30, line_dash="dash", line_color="green", yref="y4", opacity=0.5)

# 添加KDJ副图 - 默认隐藏
if use_kdj and all(c in dfi.columns for c in ["KDJ_K","KDJ_D","KDJ_J"]):
    fig.add_trace(go.Scatter(
        x=dfi.index, 
        y=dfi["KDJ_K"], 
        name="KDJ_K", 
        yaxis="y5", 
        mode="lines",
        line=dict(color="#ff7f0e"),
        visible="legendonly"  # 默认隐藏
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index, 
        y=dfi["KDJ_D"], 
        name="KDJ_D", 
        yaxis="y5", 
        mode="lines",
        line=dict(color="#1f77b4"),
        visible="legendonly"  # 默认隐藏
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index, 
        y=dfi["KDJ_J"], 
        name="KDJ_J", 
        yaxis="y5", 
        mode="lines",
        line=dict(color="#2ca02c"),
        visible="legendonly"  # 默认隐藏
    ))
    # 添加KDJ超买超卖线
    fig.add_hline(y=80, line_dash="dash", line_color="red", yref="y5", opacity=0.5)
    fig.add_hline(y=20, line_dash="dash", line_color="green", yref="y5", opacity=0.5)

# 更新图表布局
fig.update_layout(
    hovermode='x unified',
    xaxis=dict(showspikes=True, spikemode='across', spikesnap='cursor', showline=True),
    yaxis=dict(showspikes=True, spikemode='across', spikesnap='cursor', showline=True),

    xaxis_rangeslider_visible=False,
    height=1000,
    hovermode="x unified",
    dragmode="pan",
    yaxis=dict(domain=[0.58, 1.0], title="价格"),
    yaxis2=dict(domain=[0.45, 0.57], title="成交量", showgrid=False),
    yaxis3=dict(domain=[0.25, 0.44], title="MACD", showgrid=False),
    yaxis4=dict(domain=[0.15, 0.24], title="RSI", showgrid=False, range=[0,100]),
    yaxis5=dict(domain=[0.0, 0.14], title="KDJ", showgrid=False, range=[0,100]),
    modebar_add=["drawline","drawopenpath","drawclosedpath","drawcircle","drawrect","eraseshape"],
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)
st.plotly_chart(fig, use_container_width=True, config={
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False
})

# ========================= 实时策略建议（增强版） =========================
st.markdown("---")
st.subheader("🧭 实时策略建议（非投资建议）")

last = dfi.dropna().iloc[-1]
price = float(last["Close"])

# 1) 趋势/动能评分
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

# KDJ信号评分
if use_kdj and all(c in dfi.columns for c in ["KDJ_K","KDJ_D"]):
    if last["KDJ_K"] > last["KDJ_D"] and last["KDJ_K"] < 30:
        score += 1; reasons.append("KDJ 金叉且处于超卖区")
    elif last["KDJ_K"] < last["KDJ_D"] and last["KDJ_K"] > 70:
        score -= 1; reasons.append("KDJ 死叉且处于超买区")

decision = "观望"
if score >= 3: decision = "买入/加仓"
elif score <= -2: decision = "减仓/离场"

# 2) 历史百分位（最近窗口）
hist_window = min(len(dfi), 365)
recent_close = dfi["Close"].iloc[-hist_window:]
pct_rank = float((recent_close <= price).mean()) * 100 if hist_window > 1 else 50.0

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

# ========================= 新增模块：多指标策略组合 & 绩效预测 =========================
st.markdown("---")
st.subheader("🧪 组合策略评估（多指标合成｜非投资建议）")

with st.expander("选择策略构件（多选）与规则"):
    blocks = [
        "MA20>MA50（趋势做多）",
        "EMA20>EMA50（趋势做多）",
        "价格>EMA200（长线多头）",
        "MACD 金叉（MACD>Signal）",
        "RSI>50（强于中位）",
        "RSI<30 反转做多",
        "突破上轨（BOLL_U）",
        "回踩下轨反弹（价> BOLL_L）",
        "ADX>25（趋势强）",
        "K线上穿VWAP",
        "STOCH 金叉（K>D & K<80）",
        "StochRSI 超卖反转（K<20→上穿）",
        "CCI<-100 反转做多",
        "OBV 上升（OBV 斜率>0）",
        "PSAR 多头（价>PSAR）",
        "KDJ 金叉（K>D & K<20）",
    ]
    chosen_blocks = st.multiselect("选择信号构件（至少一个）", options=blocks, default=[
        "MA20>MA50（趋势做多）",
        "MACD 金叉（MACD>Signal）",
        "RSI>50（强于中位）",
        "ADX>25（趋势强）",
        "K线上穿VWAP",
    ])
    logic = st.selectbox("合成逻辑", ["AND（全部满足）", "OR（任一满足）", "MAJORITY（多数满足）"], index=0)
    side = st.selectbox("交易方向", ["做多", "做空"], index=0)
    min_hold = st.number_input("最小持有期（根）", min_value=0, value=3, step=1)
    use_exit_flip = st.checkbox("反向信号退出", True)
    use_atr_stop = st.checkbox("启用 ATR 止损/止盈", True)
    atr_sl_mult = st.number_input("ATR 止损倍数", min_value=0.1, value=1.5, step=0.1)
    atr_tp_mult = st.number_input("ATR 止盈倍数", min_value=0.1, value=3.0, step=0.1)

def _block_signal(df):
    """根据所选构件返回布尔信号 DataFrame 的 'entry' 与 'exit_hint'（用于反向退出）。"""
    d = df.copy()
    e = pd.Series(False, index=d.index)

    def shift_cross_up(a, b):
        return (a > b) & (a.shift(1) <= b.shift(1))

    # 各构件
    conds = []
    if "MA20>MA50（趋势做多）" in chosen_blocks and all(c in d.columns for c in ["MA20","MA50"]):
        conds.append(d["MA20"] > d["MA50"])
    if "EMA20>EMA50（趋势做多）" in chosen_blocks and all(c in d.columns for c in ["EMA20","EMA50"]):
        conds.append(d["EMA20"] > d["EMA50"])
    if "价格>EMA200（长线多头）" in chosen_blocks and "EMA200" in d.columns:
        conds.append(d["Close"] > d["EMA200"])
    if "MACD 金叉（MACD>Signal）" in chosen_blocks and all(c in d.columns for c in ["MACD","MACD_signal"]):
        conds.append(d["MACD"] > d["MACD_signal"])
    if "RSI>50（强于中位）" in chosen_blocks and "RSI" in d.columns:
        conds.append(d["RSI"] > 50)
    if "RSI<30 反转做多" in chosen_blocks and "RSI" in d.columns:
        conds.append(shift_cross_up(50 - (d["RSI"] - 30), 0))  # 近似表示 RSI 上穿30
    if "突破上轨（BOLL_U）" in chosen_blocks and "BOLL_U" in d.columns:
        conds.append(d["Close"] > d["BOLL_U"])
    if "回踩下轨反弹（价> BOLL_L）" in chosen_blocks and "BOLL_L" in d.columns:
        conds.append(shift_cross_up(d["Close"], d["BOLL_L"]))
    if "ADX>25（趋势强）" in chosen_blocks and "ADX" in d.columns:
        conds.append(d["ADX"] > 25)
    if "K线上穿VWAP" in chosen_blocks and "VWAP" in d.columns:
        conds.append(shift_cross_up(d["Close"], d["VWAP"]))
    if "STOCH 金叉（K>D & K<80）" in chosen_blocks and all(c in d.columns for c in ["STOCH_K","STOCH_D"]):
        conds.append( (d["STOCH_K"] > d["STOCH_D"]) & (d["STOCH_K"] < 80) & (d["STOCH_D"].shift(1) >= d["STOCH_K"].shift(1)) )
    if "StochRSI 超卖反转（K<20→上穿）" in chosen_blocks and "StochRSI_K" in d.columns:
        conds.append( shift_cross_up(d["StochRSI_K"], pd.Series(20.0, index=d.index)) )
    if "CCI<-100 反转做多" in chosen_blocks and "CCI" in d.columns:
        conds.append( shift_cross_up(d["CCI"], pd.Series(-100.0, index=d.index)) )
    if "OBV 上升（OBV 斜率>0）" in chosen_blocks and "OBV" in d.columns:
        conds.append(d["OBV"].diff() > 0)
    if "PSAR 多头（价>PSAR）" in chosen_blocks and "PSAR" in d.columns:
        conds.append(d["Close"] > d["PSAR"])
    if "KDJ 金叉（K>D & K<20）" in chosen_blocks and all(c in d.columns for c in ["KDJ_K","KDJ_D"]):
        conds.append( (d["KDJ_K"] > d["KDJ_D"]) & (d["KDJ_K"] < 20) )

    if not conds:
        return e, pd.Series(False, index=d.index)  # 无选择

    if "AND" in logic:
        e = conds[0]
        for c in conds[1:]:
            e = e & c
    elif "OR" in logic:
        e = conds[0]
        for c in conds[1:]:
            e = e | c
    else:  # MAJORITY
        # 计算满足条件的数量
        cond_count = sum(1 for c in conds if c.any())
        e = cond_count > len(conds) / 2

    # 反向提示（用于可选的反向退出）
    rev = ~e
    return e.fillna(False), rev.fillna(False)

def _guess_bar_per_year(interval_sel: str):
    # 粗略推断年化换算基数
    if interval_sel in ["1m","3m","5m","15m","30m"]:
        m = {"1m":525600, "3m":175200, "5m":105120, "15m":35040, "30m":17520}
        return m.get(interval_sel, 17520)
    if interval_sel in ["1H","2H","4H","6H","12H"]:
        h = {"1H":8760, "2H":4380, "4H":2190, "6H":1460, "12H":730}
        return h.get(interval_sel, 8760)
    if interval_sel in ["1D","1d"]:
        return 365
    if interval_sel in ["1W","1w","1wk"]:
        return 52
    if interval_sel in ["1M","1mo"]:
        return 12
    return 252  # 默认交易日

def backtest_combo(df):
    d = df.copy().dropna().copy()
    if d.empty:
        return None

    entry_sig, rev_hint = _block_signal(d)
    if side == "做空":
        entry_sig = entry_sig  # 做空构建：使用相同触发，方向为-1
    entry_idx = np.where(entry_sig.values)[0]

    pos = pd.Series(0, index=d.index, dtype=float)
    in_pos = False
    side_mult = 1 if side == "做多" else -1
    entry_price = None
    entry_bar = None
    atr_series = d["ATR"] if "ATR" in d.columns else (d["Close"].pct_change().rolling(14).std()*d["Close"])

    trades = []
    for i in range(len(d)):
        if not in_pos:
            if entry_sig.iat[i]:
                in_pos = True
                entry_bar = i
                entry_price = float(d["Close"].iat[i])
                pos.iat[i] = side_mult
            # else remain 0
        else:
            pos.iat[i] = side_mult
            # 退出判定
            exit_flag = False
            if min_hold and entry_bar is not None and (i - entry_bar) < int(min_hold):
                exit_flag = False
            else:
                if use_exit_flip and rev_hint.iat[i]:
                    exit_flag = True
                if use_atr_stop and (not np.isnan(atr_series.iat[i])):
                    atrv = float(atr_series.iat[i])
                    sl = entry_price - side_mult*atr_sl_mult*atrv
                    tp = entry_price + side_mult*atr_tp_mult*atrv
                    price_i = float(d["Close"].iat[i])
                    if (side_mult==1 and (price_i<=sl or price_i>=tp)) or (side_mult==-1 and (price_i>=sl or price_i<=tp)):
                        exit_flag = True
            if exit_flag:
                exit_price = float(d["Close"].iat[i])
                ret = (exit_price/entry_price-1.0)*side_mult
                trades.append(ret)
                in_pos = False
                entry_price = None
                entry_bar = None
                pos.iat[i] = 0

    # 若最后仍持仓，以最后收盘结算
    if in_pos and entry_price is not None:
        exit_price = float(d["Close"].iat[-1])
        ret = (exit_price/entry_price-1.0)*side_mult
        trades.append(ret)

    ret_series = d["Close"].pct_change().fillna(0.0)
    strat_ret = ret_series * pos.shift(1).fillna(0.0)
    equity = (1+strat_ret).cumprod()

    # 统计指标
    trades = pd.Series(trades, dtype=float)
    win_rate = float((trades>0).mean()) if len(trades)>0 else 0.0
    total_return = float(equity.iat[-1]/equity.iat[0]-1.0) if len(equity)>1 else 0.0
    roll_max = equity.cummax()
    mdd = float(((roll_max - equity)/roll_max).max()) if len(equity)>0 else 0.0

    # 年化与 Sharpe
    bars_per_year = _guess_bar_per_year(interval)
    avg_ret = strat_ret.mean()
    vol_ret = strat_ret.std()
    if vol_ret and vol_ret>0:
        sharpe = (avg_ret/vol_ret) * math.sqrt(bars_per_year)
    else:
        sharpe = 0.0
    cagr = (equity.iat[-1] ** (bars_per_year/max(1, len(equity))) - 1.0) if len(equity)>1 else 0.0

    return {
        "equity": equity,
        "pos": pos,
        "trades": trades,
        "win_rate": win_rate,
        "total_return": total_return,
        "mdd": mdd,
        "sharpe": sharpe,
        "cagr": cagr,
        "trades_count": int(len(trades))
    }

res = backtest_combo(dfi)
if res is None:
    st.warning("所选构件不足以生成信号，请至少选择一个构件，并确保相关指标已在左侧勾选。")
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("胜率", f"{res['win_rate']*100:.2f}%")
    c2.metric("累计收益", f"{res['total_return']*100:.2f}%")
    c3.metric("最大回撤", f"{res['mdd']*100:.2f}%")
    c4.metric("Sharpe", f"{res['sharpe']:.2f}")
    c5.metric("交易次数", str(res['trades_count']))
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=res["equity"].index, y=res["equity"].values, mode="lines", name="组合策略净值"))
    fig_c.update_layout(height=320, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_c, use_container_width=True)
    if len(res["trades"])>0:
        st.plotly_chart(px.histogram(res["trades"], nbins=20, title="单笔收益分布（组合策略）"), use_container_width=True)
    else:
        st.info("组合策略暂无闭合交易样本。")
