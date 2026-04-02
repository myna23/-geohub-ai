"""
Zambia GeoHub AI Platform — Streamlit Demo App
================================================
Run locally:
    streamlit run app.py

Features:
  Tab 1 — AI Chatbot     : plain-English Q&A over live GeoHub datasets
  Tab 2 — Report Generator: download Word + PDF reports from any dataset
  Tab 3 — Dataset Summarizer: plain-language summaries with metrics
"""

import streamlit as st
from streamlit_folium import st_folium

from hub.client import HubClient
from ai.claude_client import ClaudeClient
from ai.prompts import (
    chatbot_system_prompt,
    chatbot_user_prompt,
    summarizer_system_prompt,
    summarizer_prompt,
    report_system_prompt,
    report_prompt,
)
from reports.builder import ReportBuilder
from utils.geo_utils import make_folium_map, summarize_geojson, geojson_to_sample_rows

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Zambia GeoHub AI",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Zambia GeoHub AI")
    st.markdown("AI-powered analysis of Zambia's national geospatial datasets.")
    st.markdown("---")
    max_features = st.slider("Max features to load per dataset", 50, 500, 200, step=50)
    st.markdown("---")
    st.markdown("**Data source:** [zmb-geowb.hub.arcgis.com](https://zmb-geowb.hub.arcgis.com)")
    st.caption("Data may reflect a sample. Always verify against official sources.")

# ---------------------------------------------------------------------------
# Shared clients (cached)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_hub() -> HubClient:
    return HubClient()

@st.cache_resource(show_spinner=False)
def get_claude() -> ClaudeClient:
    return ClaudeClient()

@st.cache_resource(show_spinner=False)
def get_report_builder() -> ReportBuilder:
    return ReportBuilder()

hub = get_hub()
claude = get_claude()
builder = get_report_builder()

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
defaults = {
    "chat_messages": [],
    "chat_last_map": None,
    "report_search_results": [],
    "report_selected": None,
    "report_geojson": None,
    "report_content": None,
    "report_docx": None,
    "report_pdf": None,
    "sum_search_results": [],
    "sum_selected": None,
    "sum_geojson": None,
    "sum_content": None,
    "sum_stats": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["💬 AI Chatbot", "📄 Report Generator", "🔍 Dataset Summarizer"])

# ===========================================================================
# TAB 1 — AI CHATBOT
# ===========================================================================
with tab1:
    st.markdown("### Ask anything about Zambia's geography")
    st.caption(
        "Ask about roads, health facilities, population, agriculture, water, and more. "
        "The assistant searches live GeoHub datasets and answers using real data."
    )

    # Render chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Show last map if available
    if st.session_state.chat_last_map:
        st.caption("📍 Dataset map (last query)")
        st_folium(st.session_state.chat_last_map, width=750, height=380, returned_objects=[])

    # Chat input
    if question := st.chat_input("Ask about Zambia's geography, infrastructure, or data..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})

        # Search Hub + fetch data
        with st.spinner("Searching GeoHub datasets..."):
            try:
                datasets = hub.search_datasets(question, max_results=5)
            except Exception as e:
                datasets = []
                st.warning(f"Hub search failed: {e}")

        sample_features = []
        folium_map = None

        if datasets:
            top = datasets[0]
            try:
                with st.spinner(f"Loading data from '{top['name']}'..."):
                    geojson = hub.fetch_geojson(top["url"], max_features=max_features)
                    sample_features = geojson_to_sample_rows(geojson, n=5)
                    folium_map = make_folium_map(geojson, top["name"])
            except Exception as e:
                st.warning(f"Could not load dataset data: {e}")

        # Stream Claude response
        with st.chat_message("assistant"):
            system = chatbot_system_prompt()
            user_prompt = chatbot_user_prompt(question, datasets, sample_features)
            try:
                response_text = st.write_stream(
                    claude.stream(system, user_prompt, max_tokens=1500)
                )
            except Exception as e:
                response_text = f"⚠️ AI error: {e}"
                st.error(response_text)

            if datasets:
                with st.expander("📂 Datasets searched"):
                    for ds in datasets:
                        st.markdown(f"- **{ds['name']}** — {ds['description'][:120]}")

        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

        if folium_map:
            st.session_state.chat_last_map = folium_map
            st_folium(folium_map, width=750, height=380, returned_objects=[])

    # Clear chat button
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.chat_messages = []
            st.session_state.chat_last_map = None
            st.rerun()

# ===========================================================================
# TAB 2 — REPORT GENERATOR
# ===========================================================================
with tab2:
    st.markdown("### Generate a professional report from any dataset")
    st.caption("Search for a dataset, select it, and download a formatted Word or PDF report.")

    col_search, col_btn = st.columns([4, 1])
    with col_search:
        report_query = st.text_input(
            "Search for a dataset",
            placeholder="e.g. health facilities, roads, population density",
            key="report_query",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("Search", key="report_search_btn", use_container_width=True):
            if report_query.strip():
                with st.spinner("Searching GeoHub..."):
                    try:
                        results = hub.search_datasets(report_query, max_results=10)
                        st.session_state.report_search_results = results
                        st.session_state.report_content = None
                        st.session_state.report_selected = None
                    except Exception as e:
                        st.error(f"Search failed: {e}")

    if st.session_state.report_search_results:
        options = {ds["name"]: ds for ds in st.session_state.report_search_results}
        selected_name = st.selectbox(
            "Select a dataset",
            list(options.keys()),
            key="report_selectbox",
        )
        st.session_state.report_selected = options[selected_name]

        if st.button("📄 Generate Report", key="generate_report_btn", type="primary"):
            ds = st.session_state.report_selected
            with st.spinner(f"Loading '{ds['name']}' data..."):
                try:
                    geojson = hub.fetch_geojson(ds["url"], max_features=max_features)
                    st.session_state.report_geojson = geojson
                except Exception as e:
                    st.error(f"Failed to load dataset: {e}")
                    st.stop()

            geojson = st.session_state.report_geojson
            stats = summarize_geojson(geojson)
            samples = geojson_to_sample_rows(geojson, n=10)

            if stats.get("exceeded_limit"):
                st.info("ℹ️ Dataset exceeds transfer limit — report is based on a sample.")

            with st.spinner("Generating AI report (this takes ~15 seconds)..."):
                try:
                    rpt_text = claude.ask(
                        system=report_system_prompt(),
                        user=report_prompt(
                            ds["name"], ds["description"],
                            ds["fields"], stats, samples
                        ),
                        max_tokens=3000,
                    )
                    st.session_state.report_content = rpt_text
                except Exception as e:
                    st.error(f"AI generation failed: {e}")
                    st.stop()

            # Build documents
            with st.spinner("Building Word and PDF files..."):
                try:
                    st.session_state.report_docx = builder.to_docx(
                        title=ds["name"],
                        ai_content=rpt_text,
                        dataset_meta=ds,
                    )
                    st.session_state.report_pdf = builder.to_pdf(
                        title=ds["name"],
                        ai_content=rpt_text,
                        dataset_meta=ds,
                    )
                except Exception as e:
                    st.error(f"Document build failed: {e}")
                    st.stop()

    # Show results
    if st.session_state.report_content:
        ds = st.session_state.report_selected
        st.markdown("---")
        st.markdown(f"#### 📊 Report: {ds['name']}")

        # Download buttons
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="⬇️ Download Word (.docx)",
                data=st.session_state.report_docx,
                file_name=f"{ds['name'].replace(' ', '_')}_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with col_dl2:
            st.download_button(
                label="⬇️ Download PDF",
                data=st.session_state.report_pdf,
                file_name=f"{ds['name'].replace(' ', '_')}_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        # Report preview
        with st.expander("📖 Preview report content", expanded=True):
            st.markdown(st.session_state.report_content)

        # Map preview
        if st.session_state.report_geojson:
            st.markdown("**📍 Dataset map preview**")
            m = make_folium_map(st.session_state.report_geojson, ds["name"])
            st_folium(m, width=750, height=380, returned_objects=[])

# ===========================================================================
# TAB 3 — DATASET SUMMARIZER
# ===========================================================================
with tab3:
    st.markdown("### Summarise any GeoHub dataset in plain language")
    st.caption("Get an instant plain-English summary of any dataset — no GIS knowledge needed.")

    col_s, col_b = st.columns([4, 1])
    with col_s:
        sum_query = st.text_input(
            "Search for a dataset to summarise",
            placeholder="e.g. zambia schools, crop cover, water access points",
            key="sum_query",
            label_visibility="collapsed",
        )
    with col_b:
        if st.button("Search", key="sum_search_btn", use_container_width=True):
            if sum_query.strip():
                with st.spinner("Searching GeoHub..."):
                    try:
                        results = hub.search_datasets(sum_query, max_results=10)
                        st.session_state.sum_search_results = results
                        st.session_state.sum_content = None
                        st.session_state.sum_selected = None
                    except Exception as e:
                        st.error(f"Search failed: {e}")

    if st.session_state.sum_search_results:
        options = {ds["name"]: ds for ds in st.session_state.sum_search_results}
        selected_name = st.selectbox(
            "Select a dataset to summarise",
            list(options.keys()),
            key="sum_selectbox",
        )
        st.session_state.sum_selected = options[selected_name]

        if st.button("🔍 Summarise Dataset", key="summarise_btn", type="primary"):
            ds = st.session_state.sum_selected
            with st.spinner(f"Loading '{ds['name']}' data..."):
                try:
                    geojson = hub.fetch_geojson(ds["url"], max_features=max_features)
                    st.session_state.sum_geojson = geojson
                except Exception as e:
                    st.error(f"Failed to load dataset: {e}")
                    st.stop()

            geojson = st.session_state.sum_geojson
            stats = summarize_geojson(geojson)
            st.session_state.sum_stats = stats
            samples = geojson_to_sample_rows(geojson, n=5)

            with st.spinner("Generating AI summary..."):
                try:
                    summary = claude.ask(
                        system=summarizer_system_prompt(),
                        user=summarizer_prompt(
                            ds["name"], ds["description"],
                            ds["fields"], samples, stats["feature_count"]
                        ),
                        max_tokens=1024,
                    )
                    st.session_state.sum_content = summary
                except Exception as e:
                    st.error(f"AI summary failed: {e}")
                    st.stop()

    # Show results
    if st.session_state.sum_content:
        ds = st.session_state.sum_selected
        stats = st.session_state.sum_stats

        st.markdown("---")

        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Features loaded", f"{stats['feature_count']:,}")
        m2.metric("Geometry type", stats["geometry_type"].replace("esriGeometry", ""))
        m3.metric("Fields", len(stats["fields"]))
        m4.metric("Numeric fields", len(stats.get("numeric_stats", {})))

        if stats.get("exceeded_limit"):
            st.warning("⚠️ Transfer limit reached — stats based on a partial sample.")

        # Summary text
        st.markdown(f"#### 📋 Summary: {ds['name']}")
        st.markdown(st.session_state.sum_content)

        # Download summary
        st.download_button(
            label="⬇️ Download Summary (.txt)",
            data=st.session_state.sum_content,
            file_name=f"{ds['name'].replace(' ', '_')}_summary.txt",
            mime="text/plain",
        )

        # Field reference table
        if ds.get("fields"):
            with st.expander("📊 Field Reference"):
                import pandas as pd
                field_df = pd.DataFrame(
                    [
                        {"Field name": f["name"], "Label": f["alias"], "Type": f["type"]}
                        for f in ds["fields"]
                    ]
                )
                st.dataframe(field_df, use_container_width=True)

        # Map
        if st.session_state.sum_geojson:
            st.markdown("**📍 Spatial preview**")
            folium_m = make_folium_map(st.session_state.sum_geojson, ds["name"])
            st_folium(folium_m, width=750, height=380, returned_objects=[])
