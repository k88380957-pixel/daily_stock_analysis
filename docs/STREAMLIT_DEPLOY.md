# 🚀 Streamlit Cloud 部署指南

本指南将指导您如何将 **A股自选股智能分析系统** 部署到 Streamlit Cloud。

## 1. 准备工作

1.  **GitHub 仓库**: 确保您的代码已推送到 GitHub 仓库（例如 `k88380957-pixel/daily_stock_analysis`）。
2.  **Streamlit 账户**: 访问 [Streamlit Cloud](https://share.streamlit.io/) 并使用 GitHub 账号登录。

## 2. 部署步骤

### 第一步：创建新应用
1.  在 Streamlit Cloud 控制面板点击 **"Create app"**。
2.  选择 **"I have an app"**。
3.  选择您的仓库 `daily_stock_analysis`。
4.  **Main file path** 填写 `streamlit_app.py`。
5.  点击 **"Deploy!"**。

### 第二步：配置环境变量 (Secrets)
由于系统需要 API Key 才能运行，您需要在 Streamlit 中配置 Secrets：
1.  在部署后的应用页面，点击右下角的 **"Settings"**。
2.  选择 **"Secrets"** 选项卡。
3.  将以下内容复制并修改后填入：

```toml
GEMINI_API_KEY = "您的_Gemini_API_Key"
TAVILY_API_KEYS = "您的_Tavily_API_Key"
STOCK_LIST = "600519,300750,002594"
```

4.  点击 **"Save"**。

## 3. 注意事项

*   **API 限制**: 如果使用免费版 Gemini，请注意请求频率限制。
*   **数据源**: 系统默认使用 `efinance` 获取数据，在云端部署时通常不需要额外配置代理。
*   **自定义**: 您可以修改 `streamlit_app.py` 来增加更多可视化图表（如 K 线图）。

## 4. 常见问题

*   **部署失败**: 检查 `requirements.txt` 是否包含所有必要的库。
*   **分析无结果**: 确保 `GEMINI_API_KEY` 配置正确，且股票代码格式正确（如 `600519`）。
