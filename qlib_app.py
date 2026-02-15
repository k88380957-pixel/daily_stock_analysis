# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Qlib Streamlit Analysis App
Instruction:
1. Install dependencies: pip install pyqlib streamlit plotly pandas
2. Run the app: streamlit run qlib_app.py
"""
import itertools
import pandas as pd
import streamlit as st
import qlib
from qlib.contrib.report import analysis_model, analysis_position
from qlib.utils.exceptions import LoadObjectError
from qlib.workflow import R

def _max_width_():
    max_width_str = f"max-width: 2000px;"
    st.markdown(
        f"""
        <style>
        .reportview-container .main .block-container{{
            {max_width_str}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

@st.cache_resource
def _init():
    qlib.init()

_init()
_max_width_()

st.title("📊 Qlib 量化投资分析面板")

experiments = R.list_experiments()
exp_names = list(experiments.keys())

if not exp_names:
    st.warning("未找到实验数据。请先运行 Qlib 训练脚本生成实验记录。")
    st.info("您可以参考 Qlib 官方文档运行示例策略：`qrun examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml`")
else:
    selected_exp_name = st.sidebar.selectbox("请选择实验 (Experiment)", exp_names)
    recorders = R.list_recorders(experiment_name=selected_exp_name)
    recorder_names = list(recorders.keys())
    
    if not recorder_names:
        st.sidebar.error("该实验下没有记录器 (Recorder)。")
    else:
        selected_recoder_name = st.sidebar.selectbox("请选择记录器 (Recorder)", recorder_names)
        selected_recoder = recorders[selected_recoder_name]

        @st.cache_data
        def get_recorder_artifacts(_recorder):
            artifacts = dict()
            artifacts["params"] = _recorder.list_params()
            artifacts["metrics"] = _recorder.list_metrics()
            artifacts["tags"] = _recorder.list_tags()
            
            try:
                artifacts["report_normal_df"] = _recorder.load_object("portfolio_analysis/report_normal.pkl")
            except LoadObjectError:
                pass
            
            try:
                artifacts["analysis_df"] = _recorder.load_object("portfolio_analysis/port_analysis.pkl")
            except LoadObjectError:
                pass
            
            try:
                pred_df = _recorder.load_object("pred.pkl")
                label_df = _recorder.load_object("label.pkl")
                label_df.columns = ["label"]
                artifacts["pred_label"] = pd.concat([label_df, pred_df], axis=1, sort=True).reindex(label_df.index)
            except LoadObjectError:
                pass
            
            try:
                artifacts["positions"] = _recorder.load_object("portfolio_analysis/positions_normal.pkl")
            except LoadObjectError:
                pass
            
            return artifacts

        loaded_artifacts = get_recorder_artifacts(selected_recoder)
        
        st.header("📋 实验元数据")
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.subheader("参数 (Params)")
            st.json(loaded_artifacts.get("params"))
        with col_meta2:
            st.subheader("指标 (Metrics)")
            st.json(loaded_artifacts.get("metrics"))

        st.header("📈 策略表现分析")
        
        report_normal_df = loaded_artifacts.get("report_normal_df")
        analysis_df = loaded_artifacts.get("analysis_df")
        
        if report_normal_df is not None:
            st.subheader("累积收益与回撤")
            for fig in analysis_position.report_graph(report_normal_df, show_notebook=False):
                st.plotly_chart(fig, use_container_width=True)
        
        if analysis_df is not None:
            st.subheader("风险分析")
            for fig in analysis_position.risk_analysis_graph(analysis_df, report_normal_df, show_notebook=False):
                st.plotly_chart(fig, use_container_width=True)

        st.header("🎯 模型预测分析")
        pred_label = loaded_artifacts.get("pred_label")
        if pred_label is not None:
            st.subheader("IC 序列与分布")
            for fig in analysis_position.score_ic_graph(pred_label, show_notebook=False):
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("模型性能分位数分析")
            for fig in analysis_model.model_performance_graph(pred_label, show_notebook=False):
                st.plotly_chart(fig, use_container_width=True)

        st.header("💼 持仓细节")
        positions = loaded_artifacts.get("positions")
        if positions:
            dates = list(positions.keys())
            date = st.select_slider("选择日期查看持仓", options=dates)
            position_at_date = pd.DataFrame(positions[date])
            st.write(f"日期: {date}")
            st.dataframe(position_at_date.style.background_gradient("Reds"))
