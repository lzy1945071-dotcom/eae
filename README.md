# Legend Quant Terminal Elite v3 FIX9

更新内容：
- ✅ 修复 CoinGecko：/ohlc 失败自动回退到 /market_chart 并聚合为OHLC，保证免API也能出K线
- ✅ 左侧功能栏③：新增“顶级交易员常用指标”勾选与参数输入（MA/EMA 列表、MACD、RSI、BOLL、ATR、Stochastic、OBV）
- ✅ 主视图：所有指标可在图例点击显示/隐藏，参数变化实时联动
- ✅ 保留：实时策略建议卡片、简易回测统计、风控面板、组合风险暴露

运行：
```bash
pip install -r requirements.txt
streamlit run app.py
```
