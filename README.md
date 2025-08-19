# 加密货币量化分析小工具（可一键部署）

这个仓库包含一个基于 **Streamlit** 的简单量化分析 Web 应用：
- 使用 **CoinGecko** 免费 API 获取历史日线价格（无需 API Key）
- 计算 **SMA** 均线与 **RSI** 指标
- 进行简单的 **SMA 金叉/死叉** 回测（含滑点近似）
- 交互式可视化（Plotly），直接在浏览器里运行

## 本地运行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 一键在线部署（两种完全免费的方式）

### 方式 A：Hugging Face Spaces（推荐）
1. 新建一个 Space，选择 **Streamlit** 模板（Public 免费）。
2. 上传 `app.py` 和 `requirements.txt`（可直接上传本压缩包）
3. 保存后自动构建，几分钟内即可访问。

### 方式 B：Streamlit Community Cloud
1. 将这三个文件推到你的 GitHub 仓库。
2. 去 https://share.streamlit.io 连接仓库创建应用，入口指向 `app.py`。

> 温馨提示：CoinGecko 免费接口有速率限制，若报错稍后重试即可。