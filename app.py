# app.py — Legend Quant Terminal Elite v3 FIX10 (TV风格 + 多指标 + 实时策略增强)
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
    输出：用于展示的 DataFrame，统一包含：RSI、MACD、KDJ、StochRSI、ADX/DMI、CCI、MFI、OBV、EMA200、VWAP、布林带
    - 信号文本自动追加（利多）/（利空）/（中性）
    - 布林带规则：突破上轨（利多）、跌破下轨（利空）、中轨附近/带内震荡（中性）
    - 实时价位行置顶，移除ATR和Basis，并加入利多/利空指标计数
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

    # 临时列表用于构建除最新价之外的所有行
    temp_rows = []

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
        temp_rows.append(["RSI", fmt(rsi,1), "RSI="+fmt(rsi,1), sig + "；" + expl])

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
        temp_rows.append(["MACD", f"DIFF={fmt(macd,3)}, DEA={fmt(macd_sig,3)}, Hist={fmt(macd_hist,3)}", "交叉/柱体", sig + "；" + expl])

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
        temp_rows.append(["KDJ", f"K={fmt(k,1)}, D={fmt(d,1)}, J={fmt(j,1)}", "交叉/区间", f"{cross}；{level}"])

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
        temp_rows.append(["StochRSI", f"%K={fmt(srsi_k,1)}, %D={fmt(srsi_d,1)}", "交叉/区间", f"{cross}；{zone}"])

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
        temp_rows.append(["ADX/DMI", f"ADX={fmt(adx,1)}, +DI={fmt(dip,1)}, -DI={fmt(din,1)}", "强度/方向", f"{trend}；{dir_sig}"])

    # ----- CCI -----
    cci = last.get("CCI", np.nan)
    if not np.isnan(cci):
        if cci > 100:
            sig = "强势（利多）"
        elif cci < -100:
            sig = "弱势（利空）"
        else:
            sig = "中性"
        temp_rows.append(["CCI", fmt(cci,1), "区间", sig])

    # ----- MFI -----
    mfi = last.get("MFI", np.nan)
    if not np.isnan(mfi):
        if mfi >= 80:
            sig = "超买（利空）"
        elif mfi <= 20:
            sig = "超卖（利多）"
        else:
            sig = "中性"
        temp_rows.append(["MFI", fmt(mfi,1), "资金流/区间", sig])

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
        temp_rows.append(["OBV", fmt(obv,0), "方向", sig])

    # ----- ATR -----
    # 移除ATR行
    # atr = last.get("ATR", np.nan)
    # if not np.isnan(atr):
    #     # 相对均值
    #     atr_mean = float(dfi["ATR"].dropna().rolling(100).mean().iloc[-1]) if "ATR" in dfi.columns and dfi["ATR"].notna().any() else np.nan
    #     if not np.isnan(atr_mean):
    #         if atr > atr_mean:
    #             sig = "波动放大（利空）"
    #         elif atr < atr_mean:
    #             sig = "波动收敛（利多）"
    #         else:
    #             sig = "中性"
    #         desc = f"ATR={fmt(atr,3)} / 均值≈{fmt(atr_mean,3)}"
    #     else:
    #         sig = "中性"
    #         desc = f"ATR={fmt(atr,3)}"
    #     temp_rows.append(["ATR", desc, "波动", sig])

    # ----- EMA200 -----
    ema200 = last.get("EMA200", np.nan) if "EMA200" in dfi.columns else np.nan
    if not np.isnan(price) and not np.isnan(ema200):
        if price > ema200:
            sig = "价格在上方（利多）"
        elif price < ema200:
            sig = "价格在下方（利空）"
        else:
            sig = "中性"
        temp_rows.append(["EMA200", fmt(ema200,2), "上/下方", sig])

    # ----- VWAP -----
    vwap = last.get("VWAP", np.nan)
    if not np.isnan(vwap) and not np.isnan(price):
        if price > vwap:
            sig = "价格在上方（利多）"
        elif price < vwap:
            sig = "价格在下方（利空）"
        else:
            sig = "中性"
        temp_rows.append(["VWAP", fmt(vwap,2), "上/下方", sig])

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
        temp_rows.append(["布林带", f"上={fmt(bu,2)}, 中={fmt(bm,2)}, 下={fmt(bl,2)}", "轨道/价位", f"{sig}；{expl}"])

    # 统计利多/利空指标数量
    bullish_count = 0
    bearish_count = 0
    bull_keys = ["做多", "利多", "金叉", "上穿", "上破", "突破", "之上", "在上方"]
    bear_keys = ["做空", "利空", "死叉", "下穿", "下破", "跌破", "之下", "在下方", "超买"]
    for row in temp_rows:
        label = row[0]
        desc = row[3]
        if any(k in label for k in bull_keys) or any(k in desc for k in bull_keys):
            bullish_count += 1
        if any(k in label for k in bear_keys) or any(k in desc for k in bear_keys):
            bearish_count += 1
    
    # 构建最终的rows列表
    final_rows = [["最新价", fmt(price, 2), f"{bullish_count}/{bearish_count}", "市场最新价"]] + temp_rows
    
    df_view = pd.DataFrame(final_rows, columns=["指标","数值/关键","信号","说明"])
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
        go.Candlestick(
            x=dfi.index,
            open=dfi["Open"],
            high=dfi["High"],
            low=dfi["Low"],
            close=dfi["Close"],
            name="K线",
            increasing=dict(line=dict(color='darkgreen'), fillcolor='darkgreen'),
            decreasing=dict(line=dict(color='darkred'), fillcolor='darkred')
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
                    visible="legendonly" # 默认隐藏
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
                    visible="legendonly" # 默认隐藏
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
                    visible="legendonly" # 默认隐藏
                ))

    # 添加支撑阻力线 - 默认隐藏
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=support,
        mode="lines",
        name="支撑",
        line=dict(color="#00cc96", dash="dash"),
        yaxis="y",
        visible="legendonly" # 默认隐藏
    ))
    fig.add_trace(go.Scatter(
        x=dfi.index,
        y=resistance,
        mode="lines",
        name="阻力",
        line=dict(color="#ef553b", dash="dash"),
        yaxis="y",
        visible="legendonly" # 默认隐藏
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
            visible="legendonly" # 默认隐藏
        ))
    if not sell_signals.empty:
        sell_points = dfi.loc[sell_signals.index]
        fig.add_trace(go.Scatter(
            x=sell_points.index,
            y=sell_points["High"] * 1.01,
            mode="markers",
            name="卖出信号",
            marker=dict(symbol="triangle-down", size=10, color="#ef553b"),
            visible="legendonly" # 默认隐藏
        ))

    # 更新布局
    fig.update_layout(
        title=f"{symbol} K线图",
        yaxis_title="价格",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        template="plotly_dark",
        height=800,
        margin=dict(t=50, b=50, l=50, r=50),
        xaxis_tickformat='%m-%d %H:%M',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 添加成交量副图
    fig_vol = px.bar(dfi, x=dfi.index, y=dfi["Volume"], labels={"x":"日期", "y":"成交量"})
    fig_vol.update_layout(
        title_text="成交量",
        title_x=0.5,
        template="plotly_dark",
        height=200,
        margin=dict(t=20, b=20, l=50, r=50),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="成交量"
    )
    
    # 添加其他副图
    sub_plots = []
    if use_macd and "MACD" in dfi.columns:
        sub_plots.append(go.Bar(
            x=dfi.index,
            y=dfi["MACD_hist"],
            name="MACD Hist",
            marker_color=["#00cc96" if h > 0 else "#ef553b" for h in dfi["MACD_hist"]],
            yaxis="y2"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=dfi["MACD"],
            name="MACD",
            line=dict(color="#1f77b4"),
            yaxis="y2"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=dfi["MACD_signal"],
            name="MACD Signal",
            line=dict(color="#ff7f0e"),
            yaxis="y2"
        ))
    if use_rsi and "RSI" in dfi.columns:
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=dfi["RSI"],
            name="RSI",
            line=dict(color="#9467bd"),
            yaxis="y3"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=[70] * len(dfi),
            mode="lines",
            line=dict(color="#d62728", dash="dot"),
            name="RSI超买",
            showlegend=False,
            yaxis="y3"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=[30] * len(dfi),
            mode="lines",
            line=dict(color="#2ca02c", dash="dot"),
            name="RSI超卖",
            showlegend=False,
            yaxis="y3"
        ))
    if use_kdj and "KDJ_K" in dfi.columns:
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=dfi["KDJ_K"],
            name="K",
            line=dict(color="cyan"),
            yaxis="y4"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=dfi["KDJ_D"],
            name="D",
            line=dict(color="magenta"),
            yaxis="y4"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=dfi["KDJ_J"],
            name="J",
            line=dict(color="yellow"),
            yaxis="y4"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=[80] * len(dfi),
            mode="lines",
            line=dict(color="gray", dash="dot"),
            name="KDJ超买",
            showlegend=False,
            yaxis="y4"
        ))
        sub_plots.append(go.Scatter(
            x=dfi.index,
            y=[20] * len(dfi),
            mode="lines",
            line=dict(color="gray", dash="dot"),
            name="KDJ超卖",
            showlegend=False,
            yaxis="y4"
        ))
    
    if sub_plots:
        fig_sub = go.Figure(data=sub_plots)
        fig_sub.update_layout(
            template="plotly_dark",
            height=200,
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            margin=dict(t=20, b=20, l=50, r=50),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis_title=None,
            yaxis=dict(domain=[0.0, 1.0]),
            yaxis2=dict(overlaying="y", side="right", showgrid=False, title="MACD"),
            yaxis3=dict(overlaying="y", side="right", showgrid=False, title="RSI"),
            yaxis4=dict(overlaying="y", side="right", showgrid=False, title="KDJ")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.plotly_chart(fig_vol, use_container_width=True)
        st.plotly_chart(fig_sub, use_container_width=True)
    else:
        st.plotly_chart(fig, use_container_width=True)
        st.plotly_chart(fig_vol, use_container_width=True)
    
    st.markdown("---")
    
    # ========================= 最新策略建议 =========================
    st.subheader("💡 实时策略建议")
    
    bull_count = sum(1 for _, row in signals.iloc[-1:].iterrows() if "Buy" in row.values)
    bear_count = sum(1 for _, row in signals.iloc[-1:].iterrows() if "Sell" in row.values)
    
    if bull_count > bear_count:
        st.info("💡 综合判断：市场可能偏向多头，但请谨慎关注风险。")
    elif bear_count > bull_count:
        st.info("💡 综合判断：市场可能偏向空头，但请谨慎关注风险。")
    else:
        st.warning("💡 综合判断：市场多空势均力敌，或趋势不明显。")
        
    df_view = build_indicator_signal_table(dfi)
    st.dataframe(df_view, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # ========================= 实时风险计算 =========================
    st.subheader("⚠️ 实时风险风控计算")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("最新价", f"{dfi.iloc[-1]['Close']:.2f}")
    with c2:
        if use_atr and "ATR" in dfi.columns and not dfi["ATR"].isnull().iloc[-1]:
            st.metric("ATR (止损参考)", f"{dfi.iloc[-1]['ATR']:.4f}")
        else:
            st.metric("ATR (止损参考)", "未加载/缺失")
    
    price = dfi.iloc[-1]["Close"]
    
    # 风险计算
    position_size = 0.0
    if use_atr and "ATR" in dfi.columns and not dfi["ATR"].isnull().iloc[-1]:
        atr_value = dfi.iloc[-1]["ATR"]
        # 风险资金 = 账户总资金 * 单笔风险率
        risk_capital = account_value * (risk_pct / 100)
        # 每份头寸价值 = 止损点位 * 杠杆
        position_value_per_unit = atr_value * leverage
        if position_value_per_unit > 0:
            position_size = (risk_capital / position_value_per_unit)
    
    c3, c4, c5 = st.columns(3)
    c3.metric("风险资金", f"USDT {account_value * risk_pct / 100:.2f}")
    c4.metric("建议头寸（无杠杆）", f"USDT {position_size:.2f}" if position_size > 0 else "N/A")
    c5.metric("建议持仓数量", f" {position_size/price:.4f}" if position_size > 0 else "N/A")
    
    
    st.markdown("---")
    st.caption("免责声明：本工具仅供技术分析与学习交流使用，不构成任何投资建议。市场有风险，投资需谨慎。")
    st.caption("Powered by Streamlit, Plotly, Ta, Yfinance")

elif page_clean == "策略":
    # ========================= 回测模块 =========================
    st.subheader("📊 策略回测")
    st.warning("🚧 回测模块正在开发中。当前仅为简易模拟，请勿作为实盘依据。")
    
    # 回测参数选择
    st.markdown("##### 构件选择")
    col1, col2 = st.columns(2)
    with col1:
        use_ma_cross = st.checkbox("MA 金叉/死叉", value=True)
        use_macd_cross = st.checkbox("MACD 金叉/死叉", value=True)
        use_rsi_os = st.checkbox("RSI 超买/超卖", value=False)
    with col2:
        use_kdj_cross = st.checkbox("KDJ 金叉/死叉", value=False)
        use_kdj_os = st.checkbox("KDJ 超买/超卖", value=False)
        use_boll_break = st.checkbox("布林带突破", value=False)
    
    @st.cache_data(ttl=900, hash_funcs={"_thread.RLock": lambda _: None})
    def backtest_combo(df):
        """简易多构件组合回测"""
        temp_df = df.copy()
        
        # 确保存在K线数据
        if not all(c in temp_df.columns for c in ["Open", "High", "Low", "Close"]):
            return None
        
        # 综合信号
        signals = pd.Series(0, index=temp_df.index)
        
        if use_ma_cross and "MA20" in temp_df.columns and "MA50" in temp_df.columns:
            ma_cross_buy = (temp_df["MA20"] > temp_df["MA50"]) & (temp_df["MA20"].shift(1) <= temp_df["MA50"].shift(1))
            ma_cross_sell = (temp_df["MA20"] < temp_df["MA50"]) & (temp_df["MA20"].shift(1) >= temp_df["MA50"].shift(1))
            signals = signals.mask(ma_cross_buy, 1).mask(ma_cross_sell, -1)
            
        if use_macd_cross and "MACD" in temp_df.columns and "MACD_signal" in temp_df.columns:
            macd_cross_buy = (temp_df["MACD"] > temp_df["MACD_signal"]) & (temp_df["MACD"].shift(1) <= temp_df["MACD_signal"].shift(1))
            macd_cross_sell = (temp_df["MACD"] < temp_df["MACD_signal"]) & (temp_df["MACD"].shift(1) >= temp_df["MACD_signal"].shift(1))
            signals = signals.mask(macd_cross_buy, 1).mask(macd_cross_sell, -1)
            
        if use_rsi_os and "RSI" in temp_df.columns:
            rsi_buy = temp_df["RSI"] < 30
            rsi_sell = temp_df["RSI"] > 70
            signals = signals.mask(rsi_buy, 1).mask(rsi_sell, -1)
        
        if use_kdj_cross and "KDJ_K" in temp_df.columns and "KDJ_D" in temp_df.columns:
            kdj_cross_buy = (temp_df["KDJ_K"] > temp_df["KDJ_D"]) & (temp_df["KDJ_K"].shift(1) <= temp_df["KDJ_D"].shift(1))
            kdj_cross_sell = (temp_df["KDJ_K"] < temp_df["KDJ_D"]) & (temp_df["KDJ_K"].shift(1) >= temp_df["KDJ_D"].shift(1))
            signals = signals.mask(kdj_cross_buy, 1).mask(kdj_cross_sell, -1)
            
        if use_kdj_os and "KDJ_K" in temp_df.columns:
            kdj_buy = temp_df["KDJ_K"] < 20
            kdj_sell = temp_df["KDJ_K"] > 80
            signals = signals.mask(kdj_buy, 1).mask(kdj_sell, -1)
            
        if use_boll_break and "BOLL_U" in temp_df.columns and "BOLL_L" in temp_df.columns:
            boll_buy = temp_df["Close"] < temp_df["BOLL_L"]
            boll_sell = temp_df["Close"] > temp_df["BOLL_U"]
            signals = signals.mask(boll_buy, 1).mask(boll_sell, -1)
        
        if signals.empty or signals.sum() == 0:
            return None
        
        # 简单回测逻辑
        equity = pd.Series(1.0, index=temp_df.index)
        pos = 0  # 仓位
        trades = []
        
        for i in range(1, len(temp_df)):
            change = (temp_df["Close"].iloc[i] - temp_df["Close"].iloc[i-1]) / temp_df["Close"].iloc[i-1]
            equity.iloc[i] = equity.iloc[i-1] * (1 + pos * change)
            
            # 交易信号
            if signals.iloc[i] == 1 and pos <= 0: # 买入
                if pos < 0:
                    trades.append({"type": "exit_short", "price": temp_df["Close"].iloc[i], "date": temp_df.index[i]})
                trades.append({"type": "enter_long", "price": temp_df["Close"].iloc[i], "date": temp_df.index[i]})
                pos = 1
            elif signals.iloc[i] == -1 and pos >= 0: # 卖出
                if pos > 0:
                    trades.append({"type": "exit_long", "price": temp_df["Close"].iloc[i], "date": temp_df.index[i]})
                trades.append({"type": "enter_short", "price": temp_df["Close"].iloc[i], "date": temp_df.index[i]})
                pos = -1
        
        # 最后一笔平仓
        if pos != 0:
             trades.append({"type": "close_pos", "price": temp_df["Close"].iloc[-1], "date": temp_df.index[-1]})
        
        # 结果分析
        win_trades = [t for t in trades if t["type"] in ["exit_long", "exit_short"]]
        
        if len(win_trades) > 0:
            wins = sum(1 for t in win_trades if t["type"] == "exit_long" and t["price"] > trades[trades.index(t)-1]["price"])
            wins += sum(1 for t in win_trades if t["type"] == "exit_short" and t["price"] < trades[trades.index(t)-1]["price"])
            win_rate = wins / len(win_trades)
        else:
            win_rate = 0.0
            
        total_return = equity.iloc[-1] - 1.0
        mdd = (equity.cummax() - equity) / equity.cummax()
        mdd = mdd.max()
        
        bars_per_year = len(temp_df) / ((temp_df.index[-1] - temp_df.index[0]).days / 365.25) if len(temp_df)>1 else 1.0
        
        if equity.std() > 0:
            sharpe = (equity.iloc[-1] - 1.0) / equity.std()
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
        fig_c.add_trace(go.Scatter(x=res["equity"].index, y=res["equity"], mode="lines", name="净值曲线", line=dict(color="cyan")))
        fig_c.update_layout(title="净值曲线", xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig_c, use_container_width=True)
