import streamlit as st
import pandas as pd
import os
import sys
import logging
from datetime import datetime

# 1. 修复导入路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. 导入项目组件
try:
    from src.config import get_config
    from src.stock_analyzer import StockTrendAnalyzer
    from data_provider.efinance_fetcher import EfinanceFetcher
    from src.market_analyzer import MarketAnalyzer
    from src.analyzer import GeminiAnalyzer
except ImportError as e:
    st.error(f"导入模块失败: {e}")
    st.stop()

# 3. 页面配置
st.set_page_config(
    page_title="A股自选股智能分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 A股自选股智能分析系统")

# 4. 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    # API Key 配置
    gemini_key = st.text_input(
        "Gemini API Key", 
        type="password", 
        value=os.getenv("GEMINI_API_KEY", ""),
        help="从 Google AI Studio 获取"
    )
    
    # 股票列表配置
    default_stocks = os.getenv("STOCK_LIST", "600519,300750,002594")
    stock_list_input = st.text_area(
        "自选股列表 (逗号分隔)", 
        value=default_stocks,
        height=100
    )
    
    st.markdown("---")
    analyze_btn = st.button("🚀 开始全量分析", use_container_width=True)
    
    st.info("""
    **使用说明：**
    1. 输入您的 Gemini API Key。
    2. 输入股票代码（如 600519）。
    3. 点击开始分析。
    """)

# 5. 核心逻辑
if analyze_btn:
    if not gemini_key:
        st.warning("⚠️ 请先在侧边栏输入 Gemini API Key")
        st.stop()
    
    # 更新环境变量
    os.environ["GEMINI_API_KEY"] = gemini_key
    
    # 初始化后端组件
    try:
        config = get_config()
        fetcher = EfinanceFetcher()
        trend_analyzer = StockTrendAnalyzer()
        ai_analyzer = GeminiAnalyzer()
        market_analyzer = MarketAnalyzer(analyzer=ai_analyzer)
        
        stocks = [s.strip() for s in stock_list_input.split(",") if s.strip()]
        
        # --- 第一部分：大盘分析 ---
        st.subheader("🌍 市场大盘复盘")
        with st.spinner("正在获取大盘实时数据及新闻..."):
            try:
                market_overview = market_analyzer.get_market_overview()
                
                # 指标展示
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                m_col1.metric("上涨家数", f"{market_overview.up_count} ⬆️", delta_color="normal")
                m_col2.metric("下跌家数", f"{market_overview.down_count} ⬇️", delta_color="inverse")
                m_col3.metric("涨停家数", f"{market_overview.limit_up_count} 🔥")
                m_col4.metric("两市成交额", f"{market_overview.total_amount:.2f} 亿")
                
                # 板块信息
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    st.write("**📈 领涨板块**")
                    top_sectors_df = pd.DataFrame(market_overview.top_sectors)
                    if not top_sectors_df.empty:
                        st.table(top_sectors_df)
                with b_col2:
                    st.write("**📉 领跌板块**")
                    bottom_sectors_df = pd.DataFrame(market_overview.bottom_sectors)
                    if not bottom_sectors_df.empty:
                        st.table(bottom_sectors_df)
                        
            except Exception as e:
                st.error(f"大盘分析执行失败: {e}")

        # --- 第二部分：个股分析 ---
        st.markdown("---")
        st.subheader("🔍 个股深度诊断")
        
        for code in stocks:
            with st.container():
                st.write(f"### 📊 股票代码: {code}")
                
                # 创建三栏布局：技术面、AI诊断、决策建议
                tab1, tab2 = st.tabs(["📈 技术面分析", "🤖 AI 深度诊断"])
                
                with st.spinner(f"正在深度分析 {code}..."):
                    try:
                        # 1. 获取数据
                        df = fetcher.get_daily_data(code, days=60)
                        if df is None or df.empty:
                            st.warning(f"未能获取到 {code} 的历史数据，请检查代码是否正确。")
                            continue
                            
                        # 2. 技术面趋势分析
                        trend_res = trend_analyzer.analyze(df, code)
                        
                        with tab1:
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("当前价格", trend_res.current_price)
                            c2.metric("MA5 乖离率", f"{trend_res.bias_ma5:.2f}%")
                            c3.metric("趋势状态", trend_res.trend_status.value)
                            c4.metric("建议信号", trend_res.buy_signal.value)
                            
                            st.write("**技术面要点：**")
                            for reason in trend_res.signal_reasons:
                                st.write(f"- {reason}")
                            if trend_res.risk_factors:
                                st.write("**风险提示：**")
                                for risk in trend_res.risk_factors:
                                    st.write(f"⚠️ {risk}")

                        with tab2:
                            # 3. AI 深度分析
                            try:
                                # 构造 AI 分析所需的上下文
                                latest = df.iloc[-1]
                                context = {
                                    'code': code,
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'today': {
                                        'close': latest['close'],
                                        'open': latest['open'],
                                        'high': latest['high'],
                                        'low': latest['low'],
                                        'volume': latest['volume'],
                                        'amount': latest.get('amount', 0),
                                        'pct_chg': latest.get('pct_chg', 0),
                                        'ma5': trend_res.ma5,
                                        'ma10': trend_res.ma10,
                                        'ma20': trend_res.ma20,
                                    },
                                    'trend_analysis': trend_res.to_dict()
                                }
                                
                                ai_res = ai_analyzer.analyze(context)
                                
                                if ai_res and ai_res.success:
                                    st.success(f"**AI 核心结论：** {ai_res.get_core_conclusion()}")
                                    
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        st.write("**💡 操作建议：**", ai_res.operation_advice)
                                        st.write("**🎯 狙击点位：**")
                                        for k, v in ai_res.get_sniper_points().items():
                                            st.write(f"- {k}: {v}")
                                    with col_b:
                                        st.write("**🛡️ 风险警报：**")
                                        for alert in ai_res.get_risk_alerts():
                                            st.write(f"- {alert}")
                                            
                                    with st.expander("查看完整 AI 分析报告"):
                                        st.markdown(ai_res.analysis_summary)
                                else:
                                    st.info("AI 分析正在生成中或当前 API 额度受限...")
                            except Exception as ai_e:
                                st.info(f"AI 诊断模块暂不可用 (可能由于 API 限制): {ai_e}")
                                
                    except Exception as e:
                        st.error(f"分析 {code} 时发生异常: {e}")
                st.markdown("---")
    except Exception as e:
        st.error(f"系统初始化失败: {e}")

else:
    # 初始欢迎页面
    st.image("https://img.icons8.com/fluency/96/stock-share.png", width=100)
    st.info("👋 欢迎使用 A股智能分析系统！请在左侧配置 API Key 并点击开始分析。")
    
    # 展示一些预设的分析理念
    with st.expander("📖 查看本系统的交易理念"):
        st.markdown("""
        1. **严进策略**：不追高，偏离 MA5 超过 5% 坚决不买。
        2. **趋势交易**：只做 MA5 > MA10 > MA20 的多头排列股票。
        3. **效率优先**：关注筹码结构，寻找获利盘适中、筹码集中的标的。
        4. **回踩买入**：偏好在缩量回踩均线支撑时介入。
        """)

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Gemini AI & Streamlit")
