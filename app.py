# app.py — Legend Quant Terminal Elite v3 FIX11 (TV风格 + 多指标 + 实时策略增强 + 移动端优化)
import streamlit as st
def _append_icon(row):
    label = str(row["指标/条件"])
    desc = str(row["说明"])
    bull_keys = ["做多", "利多", "金叉", "上穿", "上破", "突破", "之上", "在上方"]
    bear_keys = ["做空", "利空", "死叉", "下穿", "下破", "跌破", "之下", "在下方", "超买"]
    neutral_keys = ["震荡", "中性", "中轨", "持平", "带内"]
    if any(k in label for k in bull_keys) or any(k in desc for k in bull_keys):
        return f"{desc} 🟢"
    if any(k in label for k in bear_keys) or any(k in desc for k in bear_keys):
        return f"{desc} 🔴"
    if any(k in label for k in neutral_keys) or any(k in desc for k in neutral_keys):
        return f"{desc} ⚪"
    return desc
# ====================== 新增：实时策略指标信息表格（始终包含所有指标） ======================
def build_indicator_signal_table(dfi):
    """
    输入：dfi（包含各类技术指标列的 DataFrame），要求包含最后一行（最新）
    输出：用于展示的 DataFrame，统一包含：RSI、MACD、KDJ、StochRSI、ADX/DMI、CCI、MFI、OBV、ATR、EMA200、VWAP、布林带
    - 信号文本自动追加（利多）/（利空）/（中性）
    - 布林带规则：突破上轨（利多）、跌破下轨（利空）、中轨附近/带内震荡（中性）
    """
    import numpy as np
    import pandas as pd
    if dfi is None or len(dfi) == 0:
        return pd.DataFrame(columns=["指标","数值/关键","信号","说明"])
    last = dfi.iloc[-1]
    price = float(last.get("Close", np.nan))
    def fmt(x, nd=2):
        try:
            if x is None or (isinstance(x, float) and np.isnan(x)):
                return ""
            return f"{float(x):.{nd}f}"
        except Exception:
            return str(x)
    rows = []
    # ----- RSI -----
    rsi = last.get("RSI", np.nan)
    if not np.isnan(rsi):
        if rsi >= 70:
            sig = "超买（利空）"
            expl = "RSI≥70，警惕回撤或高位震荡"
        elif rsi <= 30:
            sig = "超卖（利多）"
            expl = "RSI≤30，存在反弹机会"
        else:
            sig = "中性"
            expl = "RSI位于30-70区间，震荡为主"
        rows.append(["RSI", fmt(rsi,1), "RSI="+fmt(rsi,1), sig + "；" + expl])
    # ----- MACD -----
    macd = last.get("MACD", np.nan)
    macd_sig = last.get("MACD_signal", np.nan)
    macd_hist = last.get("MACD_hist", np.nan)
    if not any(np.isnan(x) for x in [macd, macd_sig, macd_hist]):
        if macd > macd_sig and macd_hist > 0:
            sig = "金叉（利多）"
            expl = "MACD在信号线上方且柱体为正，动能偏强"
        elif macd < macd_sig and macd_hist < 0:
            sig = "死叉（利空）"
            expl = "MACD在信号线下方且柱体为负，动能偏弱"
        else:
            sig = "中性"
            expl = "多空动能分歧，谨慎看待"
        rows.append(["MACD", f"DIFF={fmt(macd,3)}, DEA={fmt(macd_sig,3)}, Hist={fmt(macd_hist,3)}", "交叉/柱体", sig + "；" + expl])
    # ----- KDJ -----
    k = last.get("KDJ_K", np.nan)
    d = last.get("KDJ_D", np.nan)
    j = last.get("KDJ_J", np.nan)
    if not np.isnan(k) and not np.isnan(d):
        if k > d:
            cross = "金叉（利多）"
        elif k < d:
            cross = "死叉（利空）"
        else:
            cross = "中性"
        level = "超买" if max(k,d) >= 80 else ("超卖" if min(k,d) <= 20 else "中性")
        if level == "超买":
            level += "（利空）"
        elif level == "超卖":
            level += "（利多）"
        rows.append(["KDJ", f"K={fmt(k,1)}, D={fmt(d,1)}, J={fmt(j,1)}", "交叉/区间", f"{cross}；{level}"])
    # ----- StochRSI -----
    srsi_k = last.get("StochRSI_K", np.nan)
    srsi_d = last.get("StochRSI_D", np.nan)
    if not np.isnan(srsi_k) and not np.isnan(srsi_d):
        if srsi_k > srsi_d:
            cross = "金叉（利多）"
        elif srsi_k < srsi_d:
            cross = "死叉（利空）"
        else:
            cross = "中性"
        zone = "超买" if max(srsi_k, srsi_d) >= 80 else ("超卖" if min(srsi_k, srsi_d) <= 20 else "中性")
        if zone == "超买":
            zone += "（利空）"
        elif zone == "超卖":
            zone += "（利多）"
        rows.append(["StochRSI", f"%K={fmt(srsi_k,1)}, %D={fmt(srsi_d,1)}", "交叉/区间", f"{cross}；{zone}"])
    # ----- ADX / DMI -----
    adx = last.get("ADX", np.nan)
    dip = last.get("DIP", np.nan)
    din = last.get("DIN", np.nan)
    if not any(np.isnan(x) for x in [adx, dip, din]):
        trend = "趋势强（>25）" if adx >= 25 else "趋势弱（<25）"
        if dip > din:
            dir_sig = "多头占优（利多）"
        elif dip < din:
            dir_sig = "空头占优（利空）"
        else:
            dir_sig = "中性"
        rows.append(["ADX/DMI", f"ADX={fmt(adx,1)}, +DI={fmt(dip,1)}, -DI={fmt(din,1)}", "强度/方向", f"{trend}；{dir_sig}"])
    # ----- CCI -----
    cci = last.get("CCI", np.nan)
    if not np.isnan(cci):
        if cci > 100:
            sig = "强势（利多）"
        elif cci < -100:
            sig = "弱势（利空）"
        else:
            sig = "中性"
        rows.append(["CCI", fmt(cci,1), "区间", sig])
    # ----- MFI -----
    mfi = last.get("MFI", np.nan)
    if not np.isnan(mfi):
        if mfi >= 80:
            sig = "超买（利空）"
        elif mfi <= 20:
            sig = "超卖（利多）"
        else:
            sig = "中性"
        rows.append(["MFI", fmt(mfi,1), "资金流/区间", sig])
    # ----- OBV -----
    obv = last.get("OBV", np.nan)
    if not np.isnan(obv):
        # 方向以最近几根 OBV 斜率近似判断
        try:
            obv_series = dfi["OBV"].dropna().iloc[-5:]
            slope = float(obv_series.diff().mean())
            if slope > 0:
                sig = "上升（利多）"
            elif slope < 0:
                sig = "下降（利空）"
            else:
                sig = "中性"
        except Exception:
            sig = "中性"
        rows.append(["OBV", fmt(obv,0), "方向", sig])
    # ----- ATR -----
    atr = last.get("ATR", np.nan)
    if not np.isnan(atr):
        # 相对均值
        atr_mean = float(dfi["ATR"].dropna().rolling(100).mean().iloc[-1]) if "ATR" in dfi.columns and dfi["ATR"].notna().any() else np.nan
        if not np.isnan(atr_mean):
            if atr > atr_mean:
                sig = "波动放大（利空）"
            elif atr < atr_mean:
                sig = "波动收敛（利多）"
            else:
                sig = "中性"
            desc = f"ATR={fmt(atr,3)} / 均值≈{fmt(atr_mean,3)}"
        else:
            sig = "中性"
            desc = f"ATR={fmt(atr,3)}"
        rows.append(["ATR", desc, "波动", sig])
    # ----- EMA200 -----
    ema200 = last.get("EMA200", np.nan) if "EMA200" in dfi.columns else np.nan
    if not np.isnan(price) and not np.isnan(ema200):
        if price > ema200:
            sig = "价格在上方（利多）"
        elif price < ema200:
            sig = "价格在下方（利空）"
        else:
            sig = "中性"
        rows.append(["EMA200", fmt(ema200,2), "上/下方", sig])
    # ----- VWAP -----
    vwap = last.get("VWAP", np.nan)
    if not np.isnan(vwap) and not np.isnan(price):
        if price > vwap:
            sig = "价格在上方（利多）"
        elif price < vwap:
            sig = "价格在下方（利空）"
        else:
            sig = "中性"
        rows.append(["VWAP", fmt(vwap,2), "上/下方", sig])
    # ----- 布林带（BOLL） -----
    bu = last.get("BOLL_U", np.nan)
    bm = last.get("BOLL_M", np.nan)
    bl = last.get("BOLL_L", np.nan)
    if not any(np.isnan(x) for x in [bu, bm, bl]) and not np.isnan(price):
        if price > bu:
            sig = "突破上轨（利多）"
            expl = "可能延续强势，但注意乖离"
        elif price < bl:
            sig = "跌破下轨（利空）"
            expl = "可能延续弱势，但注意超跌反抽"
        elif abs(price - bm) / bm <= 0.01:
            sig = "中轨附近（中性）"
            expl = "围绕中轨震荡，方向不明"
        else:
            sig = "带内震荡（中性）"
            expl = "位于布林带内，上下空间均有限"
        rows.append(["布林带", f"上={fmt(bu,2)}, 中={fmt(bm,2)}, 下={fmt(bl,2)}", "轨道/价位", f"{sig}；{expl}"])
    df_view = pd.DataFrame(rows, columns=["指标","数值/关键","信号","说明"])
    return df_view
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
st.set_page_config(page_title="Legend Quant Terminal Elite v3 FIX11", layout="wide")
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
st.title("💎 Legend Quant Terminal Elite v3 FIX11")
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
    # This is a placeholder for where st_autorefresh would be called if it were a real library function
    # For a real implementation, you might need a community component like streamlit-autorefresh
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
        # 修复 VWAP 计算
        typical_price = (high + low + close) / 3
        # VWAP is typically calculated on an intraday basis, so a rolling sum is a common approximation for longer periods
        # For simplicity, a cumulative sum is used here, which is more accurate for a fixed period from the start of the data
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
        # 计算KDJ指标
        low_min = low.rolling(window=int(kdj_window)).min()
        high_max = high.rolling(window=int(kdj_window)).max()
        rsv = (close - low_min) / (high_max - low_min) * 100
        out["KDJ_K"] = rsv.ewm(com=int(kdj_smooth_k)-1).mean()
        out["KDJ_D"] = out["KDJ_K"].ewm(com=int(kdj_smooth_d)-1).mean()
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
    # ========================= TradingView 风格图表 =========================
    st.subheader(f"🕯️ K线（{symbol} / {source} / {interval}）")
    fig = go.Figure()
    # --- Build hovertext for candlestick (keep original precision) ---
    try:
        # choose volume column
        volume_col = None
        for _cand in ["Volume","volume","vol","Vol","amt"]:
            if _cand in dfi.columns:
                volume_col = _cand
                break
        if volume_col is None:
            dfi["_VolumeForHover"] = 0.0
            volume_col = "_VolumeForHover"
        # Signal column optional
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
        # fallback: minimal hovertext
        dfi["hovertext"] = "Time: " + dfi.index.astype(str)
    # --- Determine volume column for hover ---
    volume_col = None
    for cand in ["Volume", "volume", "vol", "Vol", "amt"]:
        if cand in dfi.columns:
            volume_col = cand
            break
    if volume_col is None:
        dfi["_VolumeForHover"] = 0.0
        volume_col = "_VolumeForHover"
    fig.add_trace(
        go.Candlestick(x=dfi.index,
            open=dfi["Open"],
            high=dfi["High"],
            low=dfi["Low"],
            close=dfi["Close"],
            name="K线",
            )
    )
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
    # 添加成交量 - 默认显示 (修改颜色为更深的实体)
    vol_colors = np.where(dfi["Close"] >= dfi["Open"], "#26A69A", "#EF5350")
    if "Volume" in dfi.columns and not dfi["Volume"].isna().all():
        fig.add_trace(go.Bar(
            x=dfi.index, 
            y=dfi["Volume"], 
            name="成交量", 
            yaxis="y2", 
            marker_color=vol_colors
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
            line=dict(color="#ff7f0e")# 默认隐藏
        ))
        fig.add_trace(go.Scatter(
            x=dfi.index, 
            y=dfi["KDJ_D"], 
            name="KDJ_D", 
            yaxis="y5", 
            mode="lines",
            line=dict(color="#1f77b4")# 默认隐藏
        ))
        fig.add_trace(go.Scatter(
            x=dfi.index, 
            y=dfi["KDJ_J"], 
            name="KDJ_J", 
            yaxis="y5", 
            mode="lines",
            line=dict(color="#2ca02c")# 默认隐藏
        ))
        # 添加KDJ超买超卖线
        fig.add_hline(y=80, line_dash="dash", line_color="red", yref="y5", opacity=0.5)
        fig.add_hline(y=20, line_dash="dash", line_color="green", yref="y5", opacity=0.5)
    # 更新图表布局
    # ===== 斐波那契回撤（默认隐藏，图例中点击开启；组点击=全显/全隐） =====
    # 侧边栏设置：自动/手动 以及lookback
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
    # 始终添加（legendonly）以便在图例点击开启
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
    # 组点击行为：点击一个成员即可全显/全隐
    fig.update_layout(legend=dict(groupclick="togglegroup"))
    fig.update_layout(
        hovermode='x unified',
        xaxis=dict(showspikes=True, spikemode='across', spikesnap='cursor', showline=True),
        yaxis=dict(showspikes=True, spikemode='across', spikesnap='cursor', showline=True),
        xaxis_rangeslider_visible=False,
        height=1000,
        dragmode="pan", # 确保拖动模式是平移
        # --- 关键优化：添加 uirevision 以保持交互状态 ---
        uirevision='constant', # <-- 这是关键优化点
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
    # --- 优化后的 st.plotly_chart 调用 ---
    st.plotly_chart(
        fig,
        use_container_width=True,
        # --- 关键：优化移动端交互的 config ---
        config={
            "scrollZoom": True,        # 启用滚轮/双指缩放
            "displayModeBar": True,    # 显示模式栏（可选，但有时有用）
            "displaylogo": False,      # 隐藏 Plotly logo
            # --- 可选：进一步定制模式栏 ---
            # "modeBarButtonsToAdd": ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
             # "modeBarButtonsToRemove": ['zoomIn2d', 'zoomOut2d'], # 移除特定按钮
        }
    )
if page_clean == "策略":
    # ========================= 实时策略建议（增强版） =========================
    st.markdown("---")
    st.subheader("🧭 实时策略建议（非投资建议）")
    # === 新增：做多/做空评分 + ADX趋势强度 + 斐波那契盈亏比 + 诱多/诱空概率 + 指标打勾清单 ===
    # 取最新一根K线数据
    last = dfi.iloc[-1]
    price = float(last["Close"])
    high = float(last["High"])
    low = float(last["Low"])
    # ---------- 指标快照（安全获取） ----------
    def g(col, default=np.nan):
        return float(last[col]) if col in dfi.columns and not np.isnan(last[col]) else default
    snap = {
        "MA20": g("MA20"), "MA50": g("MA50"), "EMA200": g("EMA200"),
        "MACD": g("MACD"), "MACD_signal": g("MACD_signal"), "MACD_hist": g("MACD_hist"),
        "RSI": g("RSI"), "ATR": g("ATR"), "VWAP": g("VWAP"),
        "ADX": g("ADX"), "DIP": g("DIP"), "DIN": g("DIN"),
        "BOLL_U": g("BOLL_U"), "BOLL_L": g("BOLL_L"),
        "KDJ_K": g("KDJ_K"), "KDJ_D": g("KDJ_D"), "KDJ_J": g("KDJ_J"),
        "MFI": g("MFI") if "MFI" in dfi.columns else np.nan,
        "CCI": g("CCI") if "CCI" in dfi.columns else np.nan,
        "PSAR": g("PSAR") if "PSAR" in dfi.columns else np.nan,
    }
    # ---------- 做多/做空评分（0-100） ----------
    long_score = 0.0
    short_score = 0.0
    weights = {
        "trend": 30, "momentum": 30, "overbought_oversold": 15, "volatility": 10, "volume": 10, "extras": 5
    }
    # 趋势（MA/EMA + DI方向）
    trend_up = 0
    if not np.isnan(snap["MA20"]) and not np.isnan(snap["MA50"]) and snap["MA20"] > snap["MA50"]:
        trend_up += 1
    if not np.isnan(snap["EMA200"]) and price > snap["EMA200"]:
        trend_up += 1
    di_up = 1 if (not np.isnan(snap["DIP"]) and not np.isnan(snap["DIN"]) and snap["DIP"] > snap["DIN"]) else 0
    adx_str = 1 if (not np.isnan(snap["ADX"]) and snap["ADX"] >= 20) else 0  # ADX阈值：20认为有趋势
    trend_up_score = (trend_up + di_up + adx_str) / 4.0  # 0~1
    trend_dn_score = (1 - (trend_up)) / 2.0 + (1 if di_up==0 else 0)/2.0  # 粗略反向
    # 动能（MACD、KDJ交叉）
    mom_up = 0
    if not np.isnan(snap["MACD"]) and not np.isnan(snap["MACD_signal"]) and snap["MACD"] > snap["MACD_signal"]:
        mom_up += 1
    if not np.isnan(snap["KDJ_K"]) and not np.isnan(snap["KDJ_D"]) and snap["KDJ_K"] > snap["KDJ_D"]:
        mom_up += 1
    mom_up_score = mom_up / 2.0
    mom_dn_score = 1 - mom_up_score
    # 超买超卖（RSI/KDJ）
    obos_up = 0
    if not np.isnan(snap["RSI"]):
        if snap["RSI"] < 30: obos_up += 1
        if snap["RSI"] > 70: obos_up -= 1
    if not np.isnan(snap["KDJ_K"]):
        if snap["KDJ_K"] < 20: obos_up += 1
        if snap["KDJ_K"] > 80: obos_up -= 1
    obos_up_score = (obos_up + 2) / 4.0  # 0~1，中性=0.5
    obos_dn_score = 1 - obos_up_score
    # 波动（ATR占价比例，越高越不利开仓）
    atrp = snap["ATR"]/price if not np.isnan(snap["ATR"]) and price>0 else 0.01
    vol_score = max(0.0, 1.0 - min(1.0, atrp*10))  # ATR占比>10% 则接近0分
    # 量能（MFI/OBV不可用则忽略，这里仅用MFI中性55以下偏多，55以上偏空）
    volu_up_score = 0.5
    if not np.isnan(snap["MFI"]):
        if snap["MFI"] < 45: volu_up_score = 0.7
        elif snap["MFI"] > 55: volu_up_score = 0.3
    # 其它（CCI偏离、价格位于布林）
    extras_up = 0.5
    if not np.isnan(snap["BOLL_U"]) and price < snap["BOLL_U"]: extras_up += 0.1
    if not np.isnan(snap["BOLL_L"]) and price < snap["BOLL_L"]: extras_up += 0.1  # 下轨外偏反转
    extras_up = min(1.0, max(0.0, extras_up))
    extras_dn = 1 - extras_up
    long_score = (
        weights["trend"]*trend_up_score +
        weights["momentum"]*mom_up_score +
        weights["overbought_oversold"]*obos_up_score +
        weights["volatility"]*vol_score +
        weights["volume"]*volu_up_score +
        weights["extras"]*extras_up
    ) / sum(weights.values()) * 100.0
    short_score = (
        weights["trend"]*trend_dn_score +
        weights["momentum"]*mom_dn_score +
        weights["overbought_oversold"]*obos_dn_score +
        weights["volatility"]*vol_score +
        weights["volume"]*(1-volu_up_score) +
        weights["extras"]*extras_dn
    ) / sum(weights.values()) * 100.0
    # ---------- 诱多/诱空概率（启发式） ----------
    # 条件示例：
    # 诱多（Bull Trap）：价格突破上轨或前高但ADX<18 & MACD背离（hist走弱）；
    # 诱空（Bear Trap）：价格跌破下轨或前低但ADX<18 & 动能反弹。
    def sigmoid(x): 
        return 1/(1+np.exp(-x))
    adx_weak = (not np.isnan(snap["ADX"]) and snap["ADX"] < 18)
    upper_break = (not np.isnan(snap["BOLL_U"]) and price > snap["BOLL_U"])
    lower_break = (not np.isnan(snap["BOLL_L"]) and price < snap["BOLL_L"])
    macd_weak = (not np.isnan(snap["MACD_hist"]) and len(dfi)>3 and
                 (dfi["MACD_hist"].iloc[-1] < dfi["MACD_hist"].iloc[-2]) )
    kdj_overbought = (not np.isnan(snap["KDJ_K"]) and snap["KDJ_K"]>80)
    kdj_oversold = (not np.isnan(snap["KDJ_K"]) and snap["KDJ_K"]<20)
    bull_trap_score = 0
    if upper_break: bull_trap_score += 1
    if adx_weak: bull_trap_score += 1
    if macd_weak: bull_trap_score += 1
    if kdj_overbought: bull_trap_score += 0.5
    bull_trap_prob = min(0.98, sigmoid(bull_trap_score - 1.5)) * 100
    bear_trap_score = 0
    if lower_break: bear_trap_score += 1
    if adx_weak: bear_trap_score += 1
    if not np.isnan(snap["MACD_hist"]) and dfi["MACD_hist"].iloc[-1] > dfi["MACD_hist"].iloc[-2]: 
        bear_trap_score += 1
    if kdj_oversold: bear_trap_score += 0.5
    bear_trap_prob = min(0.98, sigmoid(bear_trap_score - 1.5)) * 100
    # ---------- UI：四宫格指标 ----------
    # === 从"全指标信号表格"获取利多/利空指标数量 ===
    try:
        _ind_table_for_counts = build_indicator_signal_table(dfi)
        _sig_series = _ind_table_for_counts['说明'].astype(str)
        bull_count = int(_sig_series.str.contains('利多').sum())
        bear_count = int(_sig_series.str.contains('利空').sum())
    except Exception:
        bull_count, bear_count = 0, 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("做多评分", f"{long_score:.0f}/100")
    c2.metric("做空评分", f"{short_score:.0f}/100")
    c3.metric("诱多概率", f"{bull_trap_prob:.1f}%")
    c4.metric("诱空概率", f"{bear_trap_prob:.1f}%")
    # 挪到顶部的计算和显示部分
    last = dfi.dropna().iloc[-1]
    price = float(last["Close"])
    # 1) 趋势/动能评分
    score = 0; reasons = []
    ma20 = dfi["MA20"].iloc[-1] if "MA20" in dfi.columns else np.nan
    ma50 = dfi["MA50"].iloc[-1] if "MA50" in dfi.columns else np.nan
    if not np.isnan(ma20) and not np.isnan(ma50):
        if ma20 > ma50 and price > ma20:
            score += 2; reasons.append("MA20>MA50 且价在MA20上，多头趋势 🟢")
        elif ma20 < ma50 and price < ma20:
            score -= 2; reasons.append("MA20<MA50 且价在MA20下，空头趋势 🔴")
    if use_macd and all(c in dfi.columns for c in ["MACD","MACD_signal","MACD_hist"]):
        if last["MACD"] > last["MACD_signal"] and last["MACD_hist"] > 0:
            score += 2; reasons.append("MACD 金叉且柱为正 🟢")
        elif last["MACD"] < last["MACD_signal"] and last["MACD_hist"] < 0:
            score -= 2; reasons.append("MACD 死叉且柱为负 🔴")
    if use_rsi and "RSI" in dfi.columns:
        if last["RSI"] >= 70:
            score -= 1; reasons.append("RSI 过热（≥70）🔴")
        elif last["RSI"] <= 30:
            score += 1; reasons.append("RSI 超卖（≤30）🟢")
    # KDJ信号评分
    if use_kdj and all(c in dfi.columns for c in ["KDJ_K","KDJ_D"]):
        if last["KDJ_K"] > last["KDJ_D"] and last["KDJ_K"] < 30:
            score += 1; reasons.append("KDJ 金叉且处于超卖区 🟢")
        elif last["KDJ_K"] < last["KDJ_D"] and last["KDJ_K"] > 70:
            score -= 1; reasons.append("KDJ 死叉且处于超买区 🔴")
    decision = "观望 ⚪"
    if score >= 3: decision = "买入/加仓 🟢"
    elif score <= -2: decision = "减仓/离场 🔴"
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
    tp = price + 2.0*atr_val if "减仓" not in decision else price - 2.0*atr_val
    sl = price - 1.2*atr_val if "减仓" not in decision else price + 1.2*atr_val
    hint = "区间中位；按信号执行为主。"
    if pct_rank <= 25:
        hint = "低位区间（≤25%）→ 倾向逢低布局，关注止损与量能确认。"
    elif pct_rank >= 75:
        hint = "高位区间（≥75%）→ 谨慎追高，关注回撤与量能衰减。"
    c1.metric("最新价", f"{price:,.4f}")
    c2.metric("建议", decision)
    c3.metric("利多信号", bull_count)
    c4.metric("利空信号", bear_count)
    # --- 修正后的 st.info 调用 ---
    st.info(
        f"价格百分位：**{pct_rank:.1f}%**｜"
        f"支撑区：**{support_zone[0]:,.4f} ~ {support_zone[1]:,.4f}**｜"
        f"压力区：**{resist_zone[0]:,.4f} ~ {resist_zone[1]:,.4f}**｜"
        f"建议止损：**{sl:,.4f}** ｜ 建议止盈：**{tp:,.4f}**\n\n"  # 修正：移除异常的引号，添加换行
        f"提示：{hint}"
    )
    # === 实时策略指标信息表格（固定全指标，不依赖侧边栏开关） ===
    try:
        ind_table = build_indicator_signal_table(dfi)
        st.subheader("实时策略指标表格（全指标）")
        st.dataframe(ind_table, use_container_width=True)
    except Exception as e:
        st.info(f"指标表格生成遇到问题：{e}")
    st.caption("评分系统基于当前价相对多项指标的位置与信号，仅供参考，非投资建议。")
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
    st.plotly_chart(fig_eq, use_container_width=True, config={'scrollZoom': True, 'responsive': True, 'displaylogo': False})
    if len(pnl)>0:
        st.plotly_chart(px.histogram(pnl, nbins=20, title="单笔收益分布", config={'scrollZoom': True, 'responsive': True, 'displaylogo': False}), use_container_width=True)
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
