import streamlit as st
import pandas as pd
import os
from datetime import datetime
from src.config import get_config
from src.stock_analyzer import StockTrendAnalyzer
from data_provider.efinance_fetcher import EFinanceFetcher
from src.market_analyzer import MarketAnalyzer
from src.analyzer import AIAnalyzer

st.set_page_config(page_title="A股自选股智能分析系统", layout="wide")

st.title("📈 A股自选股智能分析系统")

# 侧边栏配置
st.sidebar.header("配置参数")
stock_list_input = st.sidebar.text_input("自选股列表 (逗号分隔)", value="600519,300750,002594")
gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))

if st.sidebar.button("开始分析"):
    if not gemini_api_key:
        st.error("请输入 Gemini API Key")
    else:
        # 更新环境变量以供后端使用
        os.environ["GEMINI_API_KEY"] = gemini_api_key
        os.environ["STOCK_LIST"] = stock_list_input
        
        # 初始化组件
        config = get_config()
        fetcher = EFinanceFetcher()
        analyzer = StockTrendAnalyzer()
        ai_analyzer = AIAnalyzer()
        market_analyzer = MarketAnalyzer(analyzer=ai_analyzer)
        
        stocks = [s.strip() for s in stock_list_input.split(",") if s.strip()]
        
        # 1. 大盘分析
        with st.spinner("正在进行大盘复盘..."):
            try:
                market_overview = market_analyzer.get_market_overview()
                st.subheader("🌍 大盘概览")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("上涨家数", market_overview.up_count)
                col2.metric("下跌家数", market_overview.down_count)
                col3.metric("涨停家_数", market_overview.limit_up_count)
                col4.metric("成交额 (亿)", f"{market_overview.total_amount:.2f}")
            except Exception as e:
                st.error(f"大盘分析失败: {e}")

        # 2. 个股分析
        st.subheader("🔍 个股趋势分析")
        for code in stocks:
            with st.expander(f"股票代码: {code}", expanded=True):
                with st.spinner(f"正在分析 {code}..."):
                    try:
                        # 获取数据
                        df = fetcher.fetch_daily(code, days=60)
                        if df is not None and not df.empty:
                            # 趋势分析
                            result = analyzer.analyze(df, code)
                            
                            # 显示结果
                            c1, c2, c3 = st.columns(3)
                            c1.write(f"**当前价格:** {result.current_price}")
                            c2.write(f"**趋势状态:** {result.trend_status.value}")
                            c3.write(f"**建议信号:** {result.buy_signal.value}")
                            
                            st.write("**分析理由:**")
                            for reason in result.signal_reasons:
                                st.write(f"- {reason}")
                                
                            if result.risk_factors:
                                st.write("**风险提示:**")
                                for risk in result.risk_factors:
                                    st.write(f"- {risk}")
                        else:
                            st.warning(f"未能获取到 {code} 的数据")
                    except Exception as e:
                        st.error(f"分析 {code} 时出错: {e}")

st.sidebar.markdown("---")
st.sidebar.info("本系统基于趋势交易理念，分析结果仅供参考，不构成投资建议。")
