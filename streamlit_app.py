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
    from data_provider.base import DataFetcherManager
    from src.market_analyzer import MarketAnalyzer
    from src.analyzer import GeminiAnalyzer
except ImportError as e:
    st.error(f"导入模块失败: {e}")
    st.stop()

# 3. 页面配置
st.set_page_config(
    page_title="中盛铭AI智能选股系统",
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
    .source-tag {
        font-size: 0.8em;
        padding: 2px 8px;
        border-radius: 10px;
        background-color: #e8f5e9;
        color: #2e7d32;
        margin-left: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 中盛铭AI智能选股系统")

# 4. 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    # API Key 配置
    st.subheader("🔑 API 密钥")
    gemini_key = st.text_input(
        "Gemini API Key", 
        type="password", 
        value=os.getenv("GEMINI_API_KEY", ""),
        help="用于 AI 深度诊断"
    )
    
    # 股票列表配置
    st.subheader("📋 股票列表")
    default_stocks = os.getenv("STOCK_LIST", "600519,300750,002594")
    stock_list_input = st.text_area(
        "自选股列表 (逗号分隔)", 
        value=default_stocks,
        height=100
    )
    
    st.markdown("---")
    analyze_btn = st.button("🚀 开始全量分析", use_container_width=True)
    
    st.info("""
    **数据源说明：**
    系统当前由 **Baostock (证券宝)** 独家驱动。
    Baostock 提供极其稳定的 A 股历史及指数数据。
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
        # 使用管理器来处理数据源 (当前仅包含 Baostock)
        fetcher_manager = DataFetcherManager()
        trend_analyzer = StockTrendAnalyzer()
        ai_analyzer = GeminiAnalyzer()
        market_analyzer = MarketAnalyzer(analyzer=ai_analyzer)
        
        stocks = [s.strip() for s in stock_list_input.split(",") if s.strip()]
        
        # --- 第一部分：大盘分析 ---
        st.subheader("🌍 市场大盘复盘")
        with st.spinner("正在从 Baostock 获取大盘数据..."):
            try:
                market_overview = market_analyzer.get_market_overview()
                
                # 指数展示
                if market_overview.indices:
                    cols = st.columns(len(market_overview.indices))
                    for i, idx in enumerate(market_overview.indices):
                        cols[i].metric(
                            idx.name, 
                            f"{idx.current:.2f}", 
                            delta=f"{idx.change_pct:.2f}%"
                        )
                
                # 统计展示
                st.markdown("#### 📊 市场统计 (估算)")
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("上涨家数", f"约 {market_overview.up_count} ⬆️")
                m_col2.metric("下跌家数", f"约 {market_overview.down_count} ⬇️")
                m_col3.metric("全市场成交额", f"约 {market_overview.total_amount:.2f} 亿")
                        
            except Exception as e:
                st.error(f"大盘分析执行失败: {e}")

        # --- 第二部分：个股分析 ---
        st.markdown("---")
        st.subheader("🔍 个股深度诊断")
        
        for code in stocks:
            with st.container():
                # 1. 获取数据
                with st.spinner(f"正在从 Baostock 获取 {code} 数据..."):
                    try:
                        df, source_name = fetcher_manager.get_daily_data(code, days=60)
                        
                        if df is None or df.empty:
                            st.warning(f"未能获取到 {code} 的历史数据，请检查代码是否正确。")
                            continue
                            
                        st.write(f"### 📊 股票代码: {code} <span class='source-tag'>来源: {source_name}</span>", unsafe_allow_html=True)
                        
                        # 创建标签页
                        tab1, tab2 = st.tabs(["📈 技术面分析", "🤖 AI 深度诊断"])
                        
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
    st.info("👋 欢迎使用 中盛铭AI智能选股系统！请在左侧配置 API Key 并点击开始分析。")
    
    # 展示一些预设的分析理念
    with st.expander("📖 查看本系统的交易理念"):
        st.markdown("""
        1. **严进策略**：不追高，偏离 MA5 超过 5% 坚决不买。
        2. **趋势交易**：只做 MA5 > MA10 > MA20 的多头排列股票。
        3. **效率优先**：关注筹码结构，寻找获利盘适中、筹码集中的标的。
        4. **回踩买入**：偏好在缩量回踩均线支撑时介入。
        """)

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Gemini AI & Baostock")
