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
import time

st.set_page_config(page_title="Legend Quant Terminal Elite v3 FIX10", layout="wide")

# ===== 页面切换（Sidebar 单点按钮：K线图 / 策略） =====
if 'page' not in st.session_state:
    st.session_state['page'] = "📈 K线图"

st.sidebar.markdown("### 页面切换")
page = st.sidebar.radio(
    "选择页面",
    ["📈 K线图", "📊 策略"],
    index=0,
    key="page"
)

# 去掉 emoji，只保留文字，方便后面判断
page_clean = page.replace("📈 ", "").replace("📊 ", "")

st.title("💎 Legend Quant Terminal Elite v3 FIX10")

# 初始化会话状态
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = None
if 'show_checkmark' not in st.session_state:
    st.session_state.show_checkmark = False
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0

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
    interval = st.sidebar.selectbox("K线周期", ["1m","3m","5m","15m","30m","1H","2H","4H","6H","12H","1D","1W","1M"], index=3)
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

# ========================= 添加手动刷新按钮 =========================
col1, col2, col3 = st.columns([6, 1, 2])

with col2:
    if st.button("🔄 刷新", use_container_width=True, key="refresh_button"):
        # 增加刷新计数器以强制刷新数据
        st.session_state.refresh_counter += 1
        # 更新刷新时间和显示状态
        st.session_state.last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.show_checkmark = True
        st.session_state.force_refresh = True
        # 使用兼容性更好的方法刷新页面
        st.query_params['refresh'] = refresh=st.session_state.refresh_counter

# 显示刷新确认和时间
with col3:
    if st.session_state.show_checkmark:
        st.success("✅ 数据已刷新")
        if st.session_state.last_refresh_time:
            st.caption(f"最后刷新: {st.session_state.last_refresh_time}")
    elif st.session_state.last_refresh_time:
        st.caption(f"最后刷新: {st.session_state.last_refresh_time}")

# ========================= Data Loaders =========================
def _cg_days_from_interval(sel: str) -> str:
    if sel.startswith("1d"): return "180"
    if sel.startswith("1w"): return "365"
    if sel.startswith("1M"): return "365"
    if sel.startswith("max"): return "max"
    return "180"

@st.cache_data(ttl=900, hash_funcs={"_thread.RLock": lambda _: None})
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

@st.cache_data(ttl=900, hash_funcs={"_thread.RLock": lambda _: None})
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

@st.cache_data(ttl=900, hash_funcs={"_thread.RLock": lambda _: None})
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

@st.cache_data(ttl=900, hash_funcs={"_thread.RLock": lambda _: None})
def load_yf(symbol: str, interval_sel: str):
    interval_map = {"1d":"1d","1wk":"1wk","1mo":"1mo"}
    interval = interval_map.get(interval_sel, "1d")
    df = yf.download(symbol, period="5y", interval=interval, progress=False, auto_adjust=False)
    if not df.empty:
        df = df[["Open","High","Low","Close","Volume"]].dropna()
    return df

def load_router(source, symbol, interval_sel, api_base=""):
    # 使用refresh_counter确保每次刷新都重新加载数据
    _ = st.session_state.refresh_counter  # 确保这个函数在refresh_counter变化时重新运行
    
    if source == "CoinGecko（免API）":
        return load_coingecko_ohlc_robust(symbol, interval_sel)
    elif source == "TokenInsight API 模式（可填API基址）":
        return load_tokeninsight_ohlc(api_base, symbol, interval_sel)
    elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
        base = api_base if source == "OKX API（可填API基址）" else ""
        return load_okx_public(symbol, interval_sel, base_url=base)
    else:
        return load_yf(symbol, interval_sel)

# 加载数据
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
            out[f"EMA{p}"] = close.ewm(span=p).mean()

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
        # 修复 VWAP 计算
        typical_price = (high + low + close) / 3
        vwap = (typical_price * vol).cumsum() / vol.cumsum()
        out["VWAP"] = vwap
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


if page_clean == "K线图":
    st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")

    from plotly.subplots import make_subplots

    # 创建两个子图：主图K线、副图KDJ
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05,
        subplot_titles=[f"K线图 - {symbol}", "KDJ指标"]
    )

    # 主图：K线
    fig.add_trace(
        go.Candlestick(
            x=dfi.index,
            open=dfi["Open"], high=dfi["High"],
            low=dfi["Low"], close=dfi["Close"],
            name="K线"
        ),
        row=1, col=1
    )

    # ===== 副图 KDJ =====
    if "KDJ_K" in dfi.columns:
        fig.add_trace(go.Scatter(x=dfi.index, y=dfi["KDJ_K"], mode="lines", name="K"), row=2, col=1)
    if "KDJ_D" in dfi.columns:
        fig.add_trace(go.Scatter(x=dfi.index, y=dfi["KDJ_D"], mode="lines", name="D"), row=2, col=1)
    if "KDJ_J" in dfi.columns:
        fig.add_trace(go.Scatter(x=dfi.index, y=dfi["KDJ_J"], mode="lines", name="J"), row=2, col=1)

    # ===== 手动输入斐波那契高低点 =====
    st.sidebar.subheader("⚙️ 斐波那契设置")
    high_price = st.sidebar.number_input("高点价格", min_value=0.0, value=float(dfi["High"].max()))
    low_price = st.sidebar.number_input("低点价格", min_value=0.0, value=float(dfi["Low"].min()))

    if "show_fib" not in st.session_state:
        st.session_state.show_fib = False

    toggle = st.sidebar.checkbox("绘制斐波那契", value=st.session_state.show_fib)

    if toggle:
        st.session_state.show_fib = True
        levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
        for lvl in levels:
            price = high_price - (high_price - low_price) * lvl
            fig.add_trace(
                go.Scatter(
                    x=[dfi.index[0], dfi.index[-1]],
                    y=[price, price],
                    mode="lines",
                    name=f"Fibonacci {lvl*100:.1f}%",
                    line=dict(color="blue", dash="dot")
                ),
                row=1, col=1
            )
    else:
        st.session_state.show_fib = False  # 一旦取消，就彻底清除

    st.plotly_chart(fig, use_container_width=True)
