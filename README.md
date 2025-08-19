# Legend Quant Terminal Elite v3 FIX8

增强点：
- 更健壮的 CoinGecko 数据源（/ohlc 失败时自动回退到 /market_chart 并聚合为OHLC）
- OKX 公共行情稳定抓取（最新在前 → 转为时间升序）
- 指标：MA20/50、BOLL(20,2)、MACD(自适应：加密 8/21/5；股票 12/26/9)、RSI(14)、ATR(14)
- 实时策略建议卡片 + 依据 + ATR 止盈/止损
- 胜率/回撤/收益曲线/收益分布
- 风控面板：仓位建议、亏损阈值预警、组合波动率配比权重

运行：
```bash
pip install -r requirements.txt
streamlit run app.py
```
