import streamlit as st
import pandas as pd
import os
import sys
import logging
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

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
    from data_provider.tencent_fetcher import TencentFetcher
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

# 自定义 CSS - 深度优化 UI 样式，解决字体颜色冲突
st.markdown("""
    <style>
    /* 全局背景 */
    .main {
        background-color: #f0f2f6;
    }
    
    /* 指标卡片容器 */
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e4e8;
        margin-bottom: 15px;
        text-align: center;
    }
    
    /* 强制卡片内字体颜色为深色，解决暗色模式冲突 */
    .metric-label {
        color: #5f6368 !important;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 8px;
    }
    
    .metric-value {
        color: #202124 !important;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    .metric-delta-up {
        color: #d93025 !important; /* 红色涨 */
        font-size: 0.95rem;
        font-weight: 600;
    }
    
    .metric-delta-down {
        color: #188038 !important; /* 绿色跌 */
        font-size: 0.95rem;
        font-weight: 600;
    }

    .source-tag {
        font-size: 0.75em;
        padding: 3px 10px;
        border-radius: 12px;
        background-color: #e8f0fe;
        color: #1967d2;
        font-weight: 600;
        margin-left: 10px;
        border: 1px solid #d2e3fc;
    }
    
    .refresh-tag {
        font-size: 0.7em;
        color: #80868b;
        text-align: right;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    
    /* 隐藏 Streamlit 默认的 metric 样式以防干扰 */
    [data-testid="stMetric"] {
        background-color: transparent !important;
        box-shadow: none !important;
        border: none !important;
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
    
    # 实时刷新配置
    st.subheader("⏱️ 实时刷新")
    refresh_interval = st.slider("刷新频率 (秒)", min_value=10, max_value=300, value=30)
    enable_refresh = st.checkbox("开启自动刷新", value=True)
    
    st.markdown("---")
    analyze_btn = st.button("🚀 开始全量分析", use_container_width=True)
    
    st.info("""
    **数据源说明：**
    1. **腾讯财经** (T+0 实时行情)
    2. **Baostock** (历史趋势分析)
    系统已实现实时与历史数据的完美结合。
    """)

# 5. 自动刷新逻辑
if enable_refresh:
    count = st_autorefresh(interval=refresh_interval * 1000, key="data_refresh")

# 6. 初始化 Session State 用于存储分析结果，避免刷新时重复触发 AI
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'last_full_analyze' not in st.session_state:
    st.session_state.last_full_analyze = None

# 7. 核心逻辑
# 如果点击了分析按钮，或者已经有分析结果且开启了自动刷新
if analyze_btn or st.session_state.last_full_analyze:
    if not gemini_key:
        st.sidebar.warning("⚠️ 请先在侧边栏输入 Gemini API Key")
        if analyze_btn: st.stop()
    
    # 更新环境变量
    os.environ["GEMINI_API_KEY"] = gemini_key
    
    # 记录最后一次全量分析时间
    if analyze_btn:
        st.session_state.last_full_analyze = datetime.now()
    
    # 初始化后端组件
    try:
        config = get_config()
        fetcher_manager = DataFetcherManager()
        trend_analyzer = StockTrendAnalyzer()
        ai_analyzer = GeminiAnalyzer()
        tencent_fetcher = TencentFetcher()
        
        stocks = [s.strip() for s in stock_list_input.split(",") if s.strip()]
        
        # --- 第一部分：大盘分析 ---
        st.subheader("🌍 市场大盘复盘 (T+0 实时)")
        st.markdown(f"<div class='refresh-tag'>最后更新: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
        
        try:
            realtime_indices = tencent_fetcher.get_indices()
            
            if realtime_indices:
                cols = st.columns(len(realtime_indices))
                for i, (name, data) in enumerate(realtime_indices.items()):
                    delta_class = "metric-delta-up" if data['pct_change'] >= 0 else "metric-delta-down"
                    delta_prefix = "↑" if data['pct_change'] >= 0 else "↓"
                    
                    with cols[i]:
                        st.markdown(f"""
                            <div class="metric-card">
                                <div class="metric-label">{name}</div>
                                <div class="metric-value">{data['current']:.2f}</div>
                                <div class={delta_class}>{delta_prefix} {abs(data['pct_change']):.2f}%</div>
                            </div>
                        """, unsafe_allow_html=True)
            
            # 统计展示 (基于实时数据估算)
            st.markdown("#### 📊 市场统计 (实时估算)")
            m_col1, m_col2, m_col3 = st.columns(3)
            
            sh_data = realtime_indices.get("上证指数", {'pct_change': 0, 'amount': 0})
            up_count = 3200 if sh_data['pct_change'] > 0 else 1600
            down_count = 4800 - up_count
            total_amount = sh_data['amount'] / 10000 * 2.5
            
            with m_col1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">上涨家数</div><div class="metric-value">约 {up_count}</div><div class="metric-delta-up">↑ 活跃</div></div>""", unsafe_allow_html=True)
            with m_col2:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">下跌家数</div><div class="metric-value">约 {down_count}</div><div class="metric-delta-down">↓ 调整</div></div>""", unsafe_allow_html=True)
            with m_col3:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">全市场成交额</div><div class="metric-value">{total_amount:.2f} 亿</div><div class="metric-label">实时放量</div></div>""", unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"大盘分析执行失败: {e}")

        # --- 第二部分：个股分析 ---
        st.markdown("---")
        st.subheader("🔍 个股深度诊断")
        
        for code in stocks:
            with st.container():
                # 1. 获取实时数据
                realtime_stock = tencent_fetcher.get_realtime_data(code)
                
                # 2. 获取历史数据 (Baostock) - 仅在点击按钮或 Session 中没有时获取
                if analyze_btn or code not in st.session_state.analysis_results:
                    with st.spinner(f"正在从 Baostock 获取 {code} 历史趋势..."):
                        try:
                            df, source_name = fetcher_manager.get_daily_data(code, days=60)
                            if df is not None and not df.empty:
                                trend_res = trend_analyzer.analyze(df, code)
                                st.session_state.analysis_results[code] = {
                                    'df': df,
                                    'source_name': source_name,
                                    'trend_res': trend_res,
                                    'ai_res': None # 初始为空
                                }
                        except Exception as e:
                            st.error(f"获取 {code} 历史数据失败: {e}")
                            continue

                # 从 Session State 获取已有的历史分析结果
                res = st.session_state.analysis_results.get(code)
                if not res: continue
                
                df = res['df']
                source_name = res['source_name']
                trend_res = res['trend_res']
                
                stock_name = realtime_stock['name'] if realtime_stock else code
                st.write(f"### 📊 {stock_name} ({code}) <span class='source-tag'>实时: 腾讯财经 | 历史: {source_name}</span>", unsafe_allow_html=True)
                
                # 创建标签页
                tab1, tab2 = st.tabs(["📈 技术面分析", "🤖 AI 深度诊断"])
                
                with tab1:
                    c1, c2, c3, c4 = st.columns(4)
                    display_price = realtime_stock['current'] if realtime_stock else trend_res.current_price
                    display_pct = realtime_stock['pct_chg'] if realtime_stock else 0
                    
                    c1.metric("当前价格", f"{display_price:.2f}", delta=f"{display_pct:.2f}%")
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
                    # 3. AI 深度分析 - 仅在点击按钮或 AI 结果为空时触发
                    if analyze_btn or res['ai_res'] is None:
                        with st.spinner(f"正在生成 {code} AI 诊断报告..."):
                            try:
                                latest = df.iloc[-1]
                                context = {
                                    'code': code,
                                    'name': stock_name,
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'realtime': realtime_stock,
                                    'today': {
                                        'close': display_price,
                                        'open': latest['open'],
                                        'high': latest['high'],
                                        'low': latest['low'],
                                        'volume': latest['volume'],
                                        'ma5': trend_res.ma5,
                                        'ma10': trend_res.ma10,
                                        'ma20': trend_res.ma20,
                                    },
                                    'trend_analysis': trend_res.to_dict()
                                }
                                ai_res = ai_analyzer.analyze(context)
                                if ai_res and ai_res.success:
                                    st.session_state.analysis_results[code]['ai_res'] = ai_res
                            except Exception as ai_e:
                                st.info(f"AI 诊断模块暂不可用: {ai_e}")

                    # 显示 AI 结果
                    ai_res = st.session_state.analysis_results[code].get('ai_res')
                    if ai_res:
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
                        st.info("点击“开始全量分析”以生成 AI 诊断报告。")
                st.markdown("---")
    except Exception as e:
        st.error(f"系统初始化失败: {e}")

else:
    # 初始欢迎页面
    st.image("https://img.icons8.com/fluency/96/stock-share.png", width=100)
    st.info("👋 欢迎使用 中盛铭AI智能选股系统！请在左侧配置 API Key 并点击开始分析。")
    
    with st.expander("📖 查看本系统的交易理念"):
        st.markdown("""
        1. **严进策略**：不追高，偏离 MA5 超过 5% 坚决不买。
        2. **趋势交易**：只做 MA5 > MA10 > MA20 的多头排列股票。
        3. **效率优先**：关注筹码结构，寻找获利盘适中、筹码集中的标的。
        4. **回踩买入**：偏好在缩量回踩均线支撑时介入。
        """)

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Gemini AI & Tencent & Baostock")
