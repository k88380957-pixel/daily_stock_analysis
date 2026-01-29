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

# 自定义 CSS - 保持优化的 UI 样式
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e4e8;
        margin-bottom: 15px;
        text-align: center;
    }
    .metric-label { color: #5f6368 !important; font-size: 0.9rem; font-weight: 500; margin-bottom: 8px; }
    .metric-value { color: #202124 !important; font-size: 1.8rem; font-weight: 700; margin-bottom: 5px; }
    .metric-delta-up { color: #d93025 !important; font-size: 0.95rem; font-weight: 600; }
    .metric-delta-down { color: #188038 !important; font-size: 0.95rem; font-weight: 600; }
    .source-tag {
        font-size: 0.75em; padding: 3px 10px; border-radius: 12px;
        background-color: #e8f0fe; color: #1967d2; font-weight: 600;
        margin-left: 10px; border: 1px solid #d2e3fc;
    }
    .refresh-tag { font-size: 0.7em; color: #80868b; text-align: right; margin-top: -10px; margin-bottom: 10px; }
    [data-testid="stMetric"] { background-color: transparent !important; box-shadow: none !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 中盛铭AI智能选股系统")

# 4. 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置中心")
    gemini_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    stock_list_input = st.text_area("自选股列表 (逗号分隔)", value=os.getenv("STOCK_LIST", "600519,300750,002594"), height=100)
    
    st.subheader("⏱️ 实时刷新")
    refresh_interval = st.slider("刷新频率 (秒)", min_value=10, max_value=300, value=30)
    enable_refresh = st.checkbox("开启自动刷新", value=True)
    
    st.markdown("---")
    # 核心：点击按钮触发全量分析
    analyze_btn = st.button("🚀 开始全量分析", use_container_width=True)
    
    st.info("**数据源：** 腾讯实时 + Baostock 历史")

# 5. 自动刷新逻辑 - 实现实时跳动
if enable_refresh:
    st_autorefresh(interval=refresh_interval * 1000, key="data_refresh")

# 6. Session State 管理 - 关键：防止自动刷新时触发 AI
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'has_analyzed' not in st.session_state:
    st.session_state.has_analyzed = False

# 7. 核心逻辑
# 只要点击过分析按钮，或者已经有分析结果，就显示内容
if analyze_btn or st.session_state.has_analyzed:
    if analyze_btn:
        st.session_state.has_analyzed = True
        
    if not gemini_key:
        st.sidebar.warning("⚠️ 请先输入 Gemini API Key")
        if analyze_btn: st.stop()
    
    os.environ["GEMINI_API_KEY"] = gemini_key
    
    try:
        fetcher_manager = DataFetcherManager()
        trend_analyzer = StockTrendAnalyzer()
        ai_analyzer = GeminiAnalyzer()
        tencent_fetcher = TencentFetcher()
        stocks = [s.strip() for s in stock_list_input.split(",") if s.strip()]
        
        # --- 第一部分：大盘分析 (实时跳动) ---
        st.subheader("🌍 市场大盘复盘 (T+0 实时)")
        st.markdown(f"<div class='refresh-tag'>最后更新: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
        
        realtime_indices = tencent_fetcher.get_indices()
        if realtime_indices:
            cols = st.columns(len(realtime_indices))
            for i, (name, data) in enumerate(realtime_indices.items()):
                delta_class = "metric-delta-up" if data['pct_change'] >= 0 else "metric-delta-down"
                delta_prefix = "↑" if data['pct_change'] >= 0 else "↓"
                with cols[i]:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">{name}</div><div class="metric-value">{data["current"]:.2f}</div><div class="{delta_class}">{delta_prefix} {abs(data["pct_change"]):.2f}%</div></div>', unsafe_allow_html=True)
        
        # --- 第二部分：个股分析 ---
        st.markdown("---")
        st.subheader("🔍 个股深度诊断")
        
        for code in stocks:
            # 1. 实时行情 (每次刷新都更新，实现跳动)
            realtime_stock = tencent_fetcher.get_realtime_data(code)
            
            # 2. 历史数据与 AI 诊断逻辑
            # 只有在手动点击按钮，或者该股票从未被分析过时，才执行耗时的历史数据获取和 AI 诊断
            is_new_stock = code not in st.session_state.analysis_results
            if analyze_btn or is_new_stock:
                with st.spinner(f"正在深度分析 {code}..."):
                    try:
                        df, source_name = fetcher_manager.get_daily_data(code, days=60)
                        if df is not None and not df.empty:
                            trend_res = trend_analyzer.analyze(df, code)
                            
                            # 只有在手动点击或结果为空时才请求 AI (严格限流)
                            ai_res = None
                            try:
                                stock_name = realtime_stock['name'] if realtime_stock else code
                                context = {
                                    'code': code, 'name': stock_name, 'date': datetime.now().strftime('%Y-%m-%d'),
                                    'realtime': realtime_stock,
                                    'today': {
                                        'close': realtime_stock['current'] if realtime_stock else df.iloc[-1]['close'],
                                        'open': df.iloc[-1]['open'], 'high': df.iloc[-1]['high'], 'low': df.iloc[-1]['low'],
                                        'volume': df.iloc[-1]['volume'], 'ma5': trend_res.ma5, 'ma10': trend_res.ma10, 'ma20': trend_res.ma20,
                                    },
                                    'trend_analysis': trend_res.to_dict()
                                }
                                ai_res = ai_analyzer.analyze(context)
                            except Exception as ai_e:
                                st.info(f"AI 诊断暂不可用 (可能已限流): {ai_e}")
                            
                            # 存入 Session 供后续自动刷新时直接使用
                            st.session_state.analysis_results[code] = {
                                'df': df, 'source_name': source_name, 'trend_res': trend_res, 'ai_res': ai_res, 'stock_name': stock_name
                            }
                    except Exception as e:
                        st.error(f"获取 {code} 数据失败: {e}")

            # 3. 渲染结果 (从 Session 获取历史/AI，从实时接口获取价格)
            res = st.session_state.analysis_results.get(code)
            if res:
                stock_name = realtime_stock['name'] if realtime_stock else res['stock_name']
                st.write(f"### 📊 {stock_name} ({code}) <span class='source-tag'>实时: 腾讯财经 | 历史: {res['source_name']}</span>", unsafe_allow_html=True)
                
                tab1, tab2 = st.tabs(["📈 技术面分析", "🤖 AI 深度诊断"])
                with tab1:
                    c1, c2, c3, c4 = st.columns(4)
                    # 价格实时跳动
                    cur_p = realtime_stock['current'] if realtime_stock else res['trend_res'].current_price
                    cur_pct = realtime_stock['pct_chg'] if realtime_stock else 0
                    c1.metric("当前价格", f"{cur_p:.2f}", delta=f"{cur_pct:.2f}%")
                    
                    # 历史指标保持稳定
                    c2.metric("MA5 乖离率", f"{res['trend_res'].bias_ma5:.2f}%")
                    c3.metric("趋势状态", res['trend_res'].trend_status.value)
                    c4.metric("建议信号", res['trend_res'].buy_signal.value)
                    for reason in res['trend_res'].signal_reasons: st.write(f"- {reason}")
                
                with tab2:
                    if res['ai_res']:
                        ai = res['ai_res']
                        st.success(f"**AI 核心结论：** {ai.get_core_conclusion()}")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write("**💡 操作建议：**", ai.operation_advice)
                            st.write("**🎯 狙击点位：**")
                            for k, v in ai.get_sniper_points().items(): st.write(f"- {k}: {v}")
                        with col_b:
                            st.write("**🛡️ 风险警报：**")
                            for alert in ai.get_risk_alerts(): st.write(f"- {alert}")
                        with st.expander("查看完整 AI 分析报告"): st.markdown(ai.analysis_summary)
                    else:
                        st.info("点击“开始全量分析”以生成 AI 诊断报告。")
                st.markdown("---")
    except Exception as e:
        st.error(f"系统错误: {e}")
else:
    st.image("https://img.icons8.com/fluency/96/stock-share.png", width=100)
    st.info("👋 欢迎使用 中盛铭AI智能选股系统！请在左侧配置 API Key 并点击开始分析。")

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Gemini AI & Tencent & Baostock")
