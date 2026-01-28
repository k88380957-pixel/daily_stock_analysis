# 🚀 股票分析系统部署全攻略

我已经为您深度优化了代码，确保其在 **Streamlit Cloud** 上能够稳定运行。同时，考虑到 Streamlit 的一些限制，我也为您准备了备选方案。

## 方案一：Streamlit Cloud (最推荐，可视化界面)

这是目前最直观的方案，您已经尝试过。

### 1. 核心修复说明
我已经为您解决了以下关键问题：
*   **路径识别**：自动将项目根目录加入 Python 路径，解决 `ImportError`。
*   **类名修正**：修正了 `GeminiAnalyzer` 和 `EfinanceFetcher` 的调用错误。
*   **AI 逻辑适配**：重构了分析流程，使其适配 Streamlit 的交互模式。

### 2. 部署步骤
1.  登录 [Streamlit Cloud](https://share.streamlit.io/)。
2.  选择您的仓库 `daily_stock_analysis`，主文件设为 `streamlit_app.py`。
3.  **关键步骤**：在 `Settings > Secrets` 中添加：
    ```toml
    GEMINI_API_KEY = "您的API_KEY"
    STOCK_LIST = "600519,300750,002594"
    ```
4.  部署完成后，直接在网页侧边栏输入 API Key 即可开始分析。

---

## 方案二：Zeabur / Docker (最稳定，支持定时任务)

如果您需要**每日定时推送**（如发到微信/飞书），Streamlit 并不适合，建议使用仓库自带的 Docker 方案部署到 Zeabur 或自己的服务器。

### 1. Zeabur 部署 (一键部署)
1.  在 [Zeabur](https://zeabur.com/) 导入您的 GitHub 仓库。
2.  Zeabur 会自动识别 `Dockerfile` 并开始构建。
3.  在环境变量中配置 `SCHEDULE_ENABLED=true` 和 `SCHEDULE_TIME=18:00`。

### 2. 本地 Docker 运行
```bash
docker-compose up -d
```

---

## 方案三：GitHub Actions (完全免费，免服务器)

如果您只需要每天固定时间收到分析报告，这是**最省心**的办法。

1.  在 GitHub 仓库的 `Settings > Secrets and variables > Actions` 中添加 `GEMINI_API_KEY` 和 `STOCK_LIST`。
2.  启用仓库中的 `.github/workflows/daily_analysis.yml`。
3.  系统将会在每个交易日 18:00 自动运行并发送通知。

---

### 💡 建议
*   如果您想**手动查看图表**：用方案一 (Streamlit)。
*   如果您想**每天自动收报告**：用方案三 (GitHub Actions)。
