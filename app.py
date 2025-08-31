# app.py — Legend Quant Terminal Elite v5 (Enhanced with 5 Advanced Strategies)
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

st.set_page_config(page_title="Legend Quant Terminal Elite v5", layout="wide")

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
    # 这里是 st_autorefresh 的占位符。如需真实自动刷新，可使用社区组件 streamlit-autorefresh
    # from streamlit_autorefresh import st_autorefresh
    # st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")

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
        "Finnhub API"  # 新增Finnhub API选项
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
elif source == "Finnhub API":
    # 为Finnhub API添加API Key输入
    api_key = st.sidebar.text_input("Finnhub API Key", value="", type="password")

# 标的与周期
if source in ["CoinGecko（免API）", "TokenInsight API 模式（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（CoinGecko coin_id）", ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot"], index=1)
    interval = st.sidebar.selectbox("K线周期（映射）", ["1d","1w","1M","max"], index=0, help="CoinGecko/TokenInsight 免费接口多为日级/周级聚合，不提供细分分钟线。")
elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
    symbol = st.sidebar.selectbox("个标（OKX InstId）", ["BTC-USDT","ETH-USDT","SOL-USDT","XRP-USDT","DOGE-USDT"], index=1)
    interval = st.sidebar.selectbox("K线周期", ["1m","3m","5m","15m","30m","1H","2H","4H","6H","12H","1D","1W","1M"], index=3)
elif source == "Finnhub API":
    # Finnhub API特定的输入
    symbol = st.sidebar.text_input("个标（Finnhub symbol）", value="AAPL")
    interval = st.sidebar.selectbox("K线周期", ["1", "5", "15", "30", "60", "D", "W", "M"], index=0,
                                  help="Finnhub支持的周期：1,5,15,30,60分钟,D=日,W=周,M=月")
else:
    symbol = st.sidebar.selectbox("个标（美股/A股）", ["AAPL","TSLA","MSFT","NVDA","600519.SS","000001.SS"], index=0)
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
use_kdj = st.sidebar.checkbox("KDJ（副图）", True)
kdj_window = st.sidebar.number_input("KDJ 窗口", min_value=5, value=9, step=1)
kdj_smooth_k = st.sidebar.number_input("K值平滑", min_value=1, value=3, step=1)
kdj_smooth_d = st.sidebar.number_input("D值平滑", min_value=1, value=3, step=1)

# ===== 新增：五个高级策略指标 =====
st.sidebar.markdown("**（新增）高级策略指标**")

# 1. Comprehensive Trading Toolkit - S/R
use_sr = st.sidebar.checkbox("S/R 支撑阻力", False)
sr_len = st.sidebar.number_input("S/R 长度", min_value=5, value=30, step=1)

# 2. Machine Learning RSI
use_ml_rsi = st.sidebar.checkbox("ML RSI", False)
ml_rsi_length = st.sidebar.number_input("ML RSI 长度", min_value=5, value=14, step=1)
ml_smooth = st.sidebar.checkbox("平滑 ML RSI", True)
ml_smooth_period = st.sidebar.number_input("平滑周期", min_value=1, value=4, step=1)
ml_min_thresh = st.sidebar.number_input("聚类最小阈值", min_value=5, value=10, step=5)
ml_max_thresh = st.sidebar.number_input("聚类最大阈值", min_value=50, value=90, step=5)
ml_step = st.sidebar.number_input("聚类步长", min_value=1, value=5, step=1)

# 3. Normalised T3 Oscillator
use_norm_t3 = st.sidebar.checkbox("归一化T3振荡器", False)
norm_t3_len = st.sidebar.number_input("T3 计算周期", min_value=1, value=2, step=1)
norm_t3_vf = st.sidebar.number_input("T3 体积因子", min_value=0.1, value=0.7, step=0.1)
norm_t3_period = st.sidebar.number_input("归一化周期", min_value=5, value=50, step=5)

# 4. Parabolic RSI
use_parabolic_rsi = st.sidebar.checkbox("抛物线RSI", False)
para_rsi_length = st.sidebar.number_input("抛物线RSI 长度", min_value=5, value=14, step=1)
para_rsi_start = st.sidebar.number_input("SAR 起始值", min_value=0.01, value=0.02, step=0.01)
para_rsi_inc = st.sidebar.number_input("SAR 增量", min_value=0.01, value=0.02, step=0.01)
para_rsi_max = st.sidebar.number_input("SAR 最大值", min_value=0.05, value=0.2, step=0.01)

# 5. Zero Lag Trend (MTF)
use_zlema_trend = st.sidebar.checkbox("零滞后趋势 (MTF)", False)
zlema_length = st.sidebar.number_input("ZLEMA 长度", min_value=10, value=70, step=5)
zlema_mult = st.sidebar.number_input("波动率带乘数", min_value=0.5, value=1.2, step=0.1)
# MTF 时间框架
mtf_timeframes = ["5", "15", "60", "240", "1D"]

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
        st.query_params['refresh'] = st.session_state.refresh_counter

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

@st.cache_data(ttl=900, hash_funcs={"_thread.RLock": lambda _: None})
def load_finnhub(symbol: str, api_key: str, interval_sel: str):
    try:
        url = f"https://finnhub.io/api/v1/stock/candle"
        params = {
            "symbol": symbol,
            "resolution": interval_sel,
            "from": int(time.time()) - 365*24*60*60,  # 获取一年数据
            "to": int(time.time()),
            "token": api_key
        }
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("s") == "ok":  # Finnhub成功响应格式
            # 转换为DataFrame
            df = pd.DataFrame({
                "Date": pd.to_datetime(data["t"], unit="s"),
                "Open": data["o"],
                "High": data["h"],
                "Low": data["l"],
                "Close": data["c"],
                "Volume": data["v"]
            })
            return df.set_index("Date")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Finnhub API error: {str(e)}")
        return pd.DataFrame()

def load_router(source, symbol, interval_sel, api_base="", api_key=""):
    # 使用refresh_counter确保每次刷新都重新加载数据
    _ = st.session_state.refresh_counter  # 确保这个函数在refresh_counter变化时重新运行
    if source == "CoinGecko（免API）":
        return load_coingecko_ohlc_robust(symbol, interval_sel)
    elif source == "TokenInsight API 模式（可填API基址）":
        return load_tokeninsight_ohlc(api_base, symbol, interval_sel)
    elif source in ["OKX 公共行情（免API）", "OKX API（可填API基址）"]:
        base = api_base if source == "OKX API（可填API基址）" else ""
        return load_okx_public(symbol, interval_sel, base_url=base)
    elif source == "Finnhub API":  # 新增Finnhub支持
        return load_finnhub(symbol, api_key, interval_sel)
    else:
        return load_yf(symbol, interval_sel)

# 加载数据
df = load_router(source, symbol, interval, api_base, api_key)
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
    if use_vwap and "Volume" in out.columns and not out["Volume"].isnull().all():
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

    if use_mfi and "Volume" in out.columns and not out["Volume"].isnull().all():
        mfi = ta.volume.MFIIndicator(high=high, low=low, close=close, volume=vol, window=int(mfi_window))
        out["MFI"] = mfi.money_flow_index()

    if use_cci:
        cci = ta.trend.CCIIndicator(high=high, low=low, close=close, window=int(cci_window))
        out["CCI"] = cci.cci()

    if use_obv and "Volume" in out.columns and not out["Volume"].isnull().all():
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
        low_min = low.rolling(window=int(kdj_window)).min()
        high_max = high.rolling(window=int(kdj_window)).max()
        rsv = (close - low_min) / (high_max - low_min) * 100
        out["KDJ_K"] = rsv.ewm(com=int(kdj_smooth_k)-1).mean()
        out["KDJ_D"] = out["KDJ_K"].ewm(com=int(kdj_smooth_d)-1).mean()
        out["KDJ_J"] = 3 * out["KDJ_K"] - 2 * out["KDJ_D"]

    # ===== 新增：五个高级指标的计算 =====

    # 1. Comprehensive Trading Toolkit - S/R
    if use_sr:
        # 使用 rolling window 找到指定长度内的最高点和最低点
        pivot_high = high.rolling(window=sr_len*2+1, center=True).max()
        pivot_low = low.rolling(window=sr_len*2+1, center=True).min()
        # 只有当当前点是窗口内的极值点时才记录
        out["SR_High"] = np.where(high == pivot_high, high, np.nan)
        out["SR_Low"] = np.where(low == pivot_low, low, np.nan)

    # 2. Machine Learning RSI
    if use_ml_rsi:
        rsi = ta.momentum.RSIIndicator(close=close, window=ml_rsi_length).rsi()
        if ml_smooth:
            rsi = rsi.ewm(span=ml_smooth_period).mean()
        out["ML_RSI"] = rsi

        # 简化的聚类逻辑来确定动态阈值 (使用百分位数近似)
        recent_rsi = rsi.dropna().tail(300)  # 取最近300个点
        if len(recent_rsi) > 3:
            # 用25%和75%分位数来模拟两个聚类中心
            q25 = recent_rsi.quantile(0.25)
            q75 = recent_rsi.quantile(0.75)
            out["ML_RSI_Long_Threshold"] = q75  # 做多阈值
            out["ML_RSI_Short_Threshold"] = q25 # 做空阈值
        else:
            out["ML_RSI_Long_Threshold"] = 70
            out["ML_RSI_Short_Threshold"] = 30

    # 3. Normalised T3 Oscillator
    if use_norm_t3:
        # 计算 T3
        t3 = ta.trend.T3Indicator(close=close, length=norm_t3_len, vfactor=norm_t3_vf).t3()
        # 归一化到 [-0.5, 0.5]
        lowest_t3 = t3.rolling(window=norm_t3_period).min()
        highest_t3 = t3.rolling(window=norm_t3_period).max()
        norm_osc = (t3 - lowest_t3) / (highest_t3 - lowest_t3) - 0.5
        out["Norm_T3_Osc"] = norm_osc

    # 4. Parabolic RSI
    if use_parabolic_rsi:
        rsi_para = ta.momentum.RSIIndicator(close=close, window=para_rsi_length).rsi()
        # 实现简化版的 Parabolic SAR，输入是 RSI 值
        sar_rsi = [np.nan] * len(rsi_para)
        is_below = [True] * len(rsi_para)
        acceleration = para_rsi_start
        max_min = rsi_para.iloc[0]  # 初始极值

        for i in range(2, len(rsi_para)):
            if i == 2:
                if rsi_para.iloc[i] > rsi_para.iloc[i-1]:
                    is_below[i] = True
                    max_min = rsi_para.iloc[i]
                    sar_rsi[i] = rsi_para.iloc[i-1]
                else:
                    is_below[i] = False
                    max_min = rsi_para.iloc[i]
                    sar_rsi[i] = rsi_para.iloc[i-1]
                acceleration = para_rsi_start
            else:
                prev_sar = sar_rsi[i-1]
                # 计算下一个SAR
                next_sar = prev_sar + acceleration * (max_min - prev_sar)
                # 处理趋势反转
                if is_below[i-1]:
                    if next_sar >= rsi_para.iloc[i]:
                        is_below[i] = False
                        sar_rsi[i] = max(rsi_para.iloc[i], max_min)
                        max_min = rsi_para.iloc[i]
                        acceleration = para_rsi_start
                    else:
                        sar_rsi[i] = min(next_sar, rsi_para.iloc[i])
                        if rsi_para.iloc[i] > max_min:
                            max_min = rsi_para.iloc[i]
                            acceleration = min(acceleration + para_rsi_inc, para_rsi_max)
                        is_below[i] = True
                else:
                    if next_sar <= rsi_para.iloc[i]:
                        is_below[i] = True
                        sar_rsi[i] = min(rsi_para.iloc[i], max_min)
                        max_min = rsi_para.iloc[i]
                        acceleration = para_rsi_start
                    else:
                        sar_rsi[i] = max(next_sar, rsi_para.iloc[i])
                        if rsi_para.iloc[i] < max_min:
                            max_min = rsi_para.iloc[i]
                            acceleration = min(acceleration + para_rsi_inc, para_rsi_max)
                        is_below[i] = False
            sar_rsi[i] = max(0, min(100, sar_rsi[i]))  # 限制在0-100
        out["Parabolic_RSI"] = sar_rsi
        out["Parabolic_RSI_Is_Below"] = is_below

    # 5. Zero Lag Trend (MTF)
    if use_zlema_trend:
        lag = int((zlema_length - 1) / 2)
        zlema_src = close + (close - close.shift(lag))
        zlema = zlema_src.ewm(span=zlema_length).mean()
        # 计算波动率带
        atr_val = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=zlema_length).average_true_range()
        volatility = atr_val.rolling(window=zlema_length*3).max() * zlema_mult
        out["ZLEMA"] = zlema
        out["ZLEMA_Upper"] = zlema + volatility
        out["ZLEMA_Lower"] = zlema - volatility

        # 计算趋势
        trend = pd.Series(0, index=close.index)
        trend[close > out["ZLEMA_Upper"]] = 1
        trend[close < out["ZLEMA_Lower"]] = -1
        trend = trend.replace(0, method='ffill')  # 向后填充
        out["ZLEMA_Trend"] = trend

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
    recent_high = df["High"].rolling(window=window).max()
    recent_low = df["Low"].rolling(window=window).min()
    if "BOLL_U" in df.columns and "BOLL_L" in df.columns:
        resistance = df["BOLL_U"]
        support = df["BOLL_L"]
    else:
        resistance = recent_high
        support = recent_low
    return support, resistance

support, resistance = calculate_support_resistance(dfi)

# ========================= TradingView 风格图表 =========================
st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")
fig = go.Figure()

# --- Build hovertext for candlestick ---
try:
    volume_col = None
    for _cand in ["Volume","volume","vol","Vol","amt"]:
        if _cand in dfi.columns:
            volume_col = _cand
            break
    if volume_col is None:
        dfi["_VolumeForHover"] = 0.0
        volume_col = "_VolumeForHover"

    _has_signal = "Signal" in dfi.columns
    _time_str = dfi.index.astype(str)
    dfi["hovertext"] = (
        "Time: " + _time_str +
        "<br>Open: " + dfi["Open"].astype(str) +
        "<br>High: " + dfi["High"].astype(str) +
        "<br>Low: " + dfi["Low"].astype(str) +
        "<br>Close: " + dfi["Close"].astype(str) +
        "<br>Volume: " + dfi[volume_col].astype(str)
    )
    if _has_signal:
        dfi["hovertext"] = dfi["hovertext"] + "<br>Signal: " + dfi["Signal"].astype(str)
except Exception as _e:
    dfi["hovertext"] = "Time: " + dfi.index.astype(str)

# --- 添加K线 ---
fig.add_trace(
    go.Candlestick(x=dfi.index,
        open=dfi["Open"],
        high=dfi["High"],
        low=dfi["Low"],
        close=dfi["Close"],
        name="K线",
        text=dfi["hovertext"],
        hoverinfo="text"
    )
)

# --- 添加主图指标 ---
# MA
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
                visible="legendonly"
            ))

# EMA
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
                visible="legendonly"
            ))

# BOLL
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
                visible="legendonly"
            ))

# 支撑阻力
fig.add_trace(go.Scatter(
    x=dfi.index,
    y=support,
    mode="lines",
    name="支撑",
    line=dict(color="#00cc96", dash="dash"),
    yaxis="y",
    visible="legendonly"
))
fig.add_trace(go.Scatter(
    x=dfi.index,
    y=resistance,
    mode="lines",
    name="阻力",
    line=dict(color="#ef553b", dash="dash"),
    yaxis="y",
    visible="legendonly"
))

# 1. S/R 支撑阻力 (主图)
if use_sr and "SR_High" in dfi.columns and "SR_Low" in dfi.columns:
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["SR_High"],
        mode="markers",
        name="S/R 阻力",
        line=dict(color="#FF4136"),
        yaxis="y",
        visible="legendonly"
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["SR_Low"],
        mode="markers",
        name="S/R 支撑",
        line=dict(color="#00CC96"),
        yaxis="y",
        visible="legendonly"
    ))

# 5. Zero Lag Trend (MTF) - 主图
if use_zlema_trend and all(c in dfi.columns for c in ["ZLEMA", "ZLEMA_Upper", "ZLEMA_Lower"]):
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["ZLEMA"],
        mode="lines",
        name="ZLEMA",
        line=dict(color="#AB63FA", width=2),
        yaxis="y"
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["ZLEMA_Upper"],
        mode="lines",
        name="ZLEMA 上带",
        line=dict(color="#EF553B", width=1, dash="dash"),
        yaxis="y",
        visible="legendonly"
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["ZLEMA_Lower"],
        mode="lines",
        name="ZLEMA 下带",
        line=dict(color="#00CC96", width=1, dash="dash"),
        yaxis="y",
        visible="legendonly"
    ))
    # 添加趋势反转信号
    bullish_signals = dfi[(dfi["ZLEMA_Trend"] == 1) & (dfi["ZLEMA_Trend"].shift(1) != 1)]
    bearish_signals = dfi[(dfi["ZLEMA_Trend"] == -1) & (dfi["ZLEMA_Trend"].shift(1) != -1)]
    if not bullish_signals.empty:
        fig.add_trace(go.Scatter(
            x=bullish_signals.index,
            y=bullish_signals["ZLEMA_Lower"],
            mode="text",
            name="ZLEMA 多头",
            text=["▲"] * len(bullish_signals),
            textfont=dict(color="#00CC96", size=14),
            yaxis="y",
            showlegend=True
        ))
    if not bearish_signals.empty:
        fig.add_trace(go.Scatter(
            x=bearish_signals.index,
            y=bearish_signals["ZLEMA_Upper"],
            mode="text",
            name="ZLEMA 空头",
            text=["▼"] * len(bearish_signals),
            textfont=dict(color="#EF553B", size=14),
            yaxis="y",
            showlegend=True
        ))

# --- 添加成交量 ---
vol_colors = np.where(dfi["Close"] >= dfi["Open"], "#26A69A", "#EF5350")
if "Volume" in dfi.columns and not dfi["Volume"].isna().all():
    fig.add_trace(go.Bar(
        x=dfi.index,
        y=dfi["Volume"],
        name="成交量",
        yaxis="y2",
        marker_color=vol_colors
    ))

# --- 添加副图指标 ---
# MACD
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

# RSI
if use_rsi and "RSI" in dfi.columns:
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["RSI"],
        name="RSI",
        yaxis="y4",
        mode="lines",
        line=dict(color="#17becf")
    ))
    fig.add_hline(y=70, line_dash="dash", line_color="red", yref="y4", opacity=0.5)
    fig.add_hline(y=30, line_dash="dash", line_color="green", yref="y4", opacity=0.5)

# KDJ
if use_kdj and all(c in dfi.columns for c in ["KDJ_K","KDJ_D","KDJ_J"]):
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["KDJ_K"],
        name="KDJ_K",
        yaxis="y5",
        mode="lines",
        line=dict(color="#ff7f0e"),
        visible="legendonly"
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["KDJ_D"],
        name="KDJ_D",
        yaxis="y5",
        mode="lines",
        line=dict(color="#1f77b4"),
        visible="legendonly"
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["KDJ_J"],
        name="KDJ_J",
        yaxis="y5",
        mode="lines",
        line=dict(color="#2ca02c"),
        visible="legendonly"
    ))
    fig.add_hline(y=80, line_dash="dash", line_color="red", yref="y5", opacity=0.5)
    fig.add_hline(y=20, line_dash="dash", line_color="green", yref="y5", opacity=0.5)

# 2. Machine Learning RSI (副图)
if use_ml_rsi and "ML_RSI" in dfi.columns:
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["ML_RSI"],
        name="ML RSI",
        yaxis="y4",
        mode="lines",
        line=dict(color="#AB63FA"),
        visible="legendonly"
    ))
    if "ML_RSI_Long_Threshold" in dfi.columns:
        fig.add_hline(y=dfi["ML_RSI_Long_Threshold"].iloc[-1], line_dash="dot", line_color="#00CC96",
                      annotation_text="Long", annotation_position="top right", yref="y4", visible="legendonly")
    if "ML_RSI_Short_Threshold" in dfi.columns:
        fig.add_hline(y=dfi["ML_RSI_Short_Threshold"].iloc[-1], line_dash="dot", line_color="#EF553B",
                      annotation_text="Short", annotation_position="bottom right", yref="y4", visible="legendonly")

# 4. Parabolic RSI (副图)
if use_parabolic_rsi and "Parabolic_RSI" in dfi.columns:
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=dfi["Parabolic_RSI"],
        name="抛物线RSI",
        yaxis="y4",
        mode="markers",
        marker=dict(symbol="circle", size=4),
        marker_color=np.where(dfi["Parabolic_RSI_Is_Below"], "#00CC96", "#EF553B"),
        visible="legendonly"
    ))

# 3. Normalised T3 Oscillator (副图)
if use_norm_t3 and "Norm_T3_Osc" in dfi.columns:
    fig.add_trace(go.Bar(
        x=dfi.index,
        y=dfi["Norm_T3_Osc"],
        name="归一化T3",
        yaxis="y6",
        marker_color=np.where(dfi["Norm_T3_Osc"] >= 0, "#00CC96", "#EF553B"),
        opacity=0.7,
        visible="legendonly"
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="white", yref="y6", opacity=0.5)

# --- 更新图表布局 ---
fig.update_layout(
    hovermode='x unified',
    xaxis=dict(showspikes=True, spikemode='across', spikesnap='cursor', showline=True),
    yaxis=dict(showspikes=True, spikemode='across', spikesnap='cursor', showline=True),
    xaxis_rangeslider_visible=False,
    height=1000,
    dragmode="pan",
    yaxis2=dict(domain=[0.45, 0.57], title="成交量", showgrid=False),
    yaxis3=dict(domain=[0.25, 0.44], title="MACD", showgrid=False),
    yaxis4=dict(domain=[0.15, 0.24], title="RSI/MLRSI", showgrid=False, range=[0,100]),
    yaxis5=dict(domain=[0.0, 0.14], title="KDJ", showgrid=False, range=[0,100]),
    yaxis6=dict(domain=[0.60, 0.72], title="归一化T3", showgrid=False, range=[-0.6, 0.6]), # 新的Y轴
    modebar_add=["drawline","drawopenpath","drawclosedpath","drawcircle","drawrect","eraseshape"],
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        groupclick="togglegroup"
    ),
    uirevision='constant'
)

# ===== 斐波那契回撤（默认隐藏，图例中点击开启；组点击=全显/全隐） =====
with st.sidebar.expander("⚙️ 斐波那契设置", expanded=False):
    use_auto_fib = st.checkbox("自动高低点（最近N根K线）", value=True, key="auto_fib")
    lookback = st.number_input("N（最近N根K线）", min_value=20, max_value=2000, value=100, step=10, key="fib_lookback")
    if not use_auto_fib:
        fib_high = st.number_input("自定义高点", min_value=0.0, value=float(dfi["High"].max()), key="fib_high")
        fib_low = st.number_input("自定义低点", min_value=0.0, value=float(dfi["Low"].min()), key="fib_low")
    else:
        sub_df = dfi.tail(int(lookback))
        fib_high = float(sub_df["High"].max())
        fib_low = float(sub_df["Low"].min())

levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
first = True
for lvl in levels:
    price = fib_high - (fib_high - fib_low) * lvl
    fig.add_trace(
        go.Scatter(
            x=[dfi.index[0], dfi.index[-1]],
            y=[price, price],
            mode="lines",
            name=f"Fibonacci {lvl*100:.1f}%",
            line=dict(dash="dot"),
            visible="legendonly",
            legendgroup="Fibonacci",
            showlegend=first,
            legendgrouptitle_text="Fibonacci"
        ),
        # 主图轴
    )
    first = False

# ===== 添加MTF信号表格 =====
if use_zlema_trend and st.session_state.refresh_counter > 0:
    # 这里简化处理，直接使用当前图表数据的趋势作为信号
    # 在真实应用中，这里需要从不同时间框架获取数据
    current_trend = "Bullish" if dfi["ZLEMA_Trend"].iloc[-1] == 1 else "Bearish"
    mtf_data = {
        "Time Frame": mtf_timeframes,
        "Signal": [current_trend] * len(mtf_timeframes)
    }
    mtf_df = pd.DataFrame(mtf_data)
    # 使用 Plotly 在图表上绘制表格
    fig.add_trace(go.Table(
        header=dict(values=list(mtf_df.columns),
                    fill_color='paleturquoise',
                    align='center'),
        cells=dict(values=[mtf_df[col] for col in mtf_df.columns],
                   fill_color='lavender',
                   align='center'),
        domain=dict(x=[0.75, 0.98], y=[0.8, 0.95])
    ))

# 显示图表
st.plotly_chart(fig, use_container_width=True, config={
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False
})
