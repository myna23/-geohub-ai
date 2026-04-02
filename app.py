"""
Zambia GeoHub AI Platform — Streamlit App
==========================================
Run locally:
    streamlit run app.py

Features:
  Tab 1 — AI Chatbot     : Q&A with edit prompt + PDF/Word download per response
  Tab 2 — Report Generator: full dataset reports
  Tab 3 — Dataset Summarizer: plain-language summaries
  Floating widget        : pop-up chat bubble for Hub embedding
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
# Floating chat widget CSS + JS (for Hub embedding)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Floating chat button */
#zmb-chat-btn {
    position: fixed;
    bottom: 28px;
    right: 28px;
    width: 58px;
    height: 58px;
    border-radius: 50%;
    background: #1d3557;
    color: white;
    font-size: 26px;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
}
#zmb-chat-btn:hover { background: #457b9d; }

/* Floating chat panel */
#zmb-chat-panel {
    position: fixed;
    bottom: 100px;
    right: 28px;
    width: 380px;
    height: 520px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    z-index: 9998;
    display: none;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #e0e0e0;
}
#zmb-chat-panel.open { display: flex; }

#zmb-chat-header {
    background: #1d3557;
    color: white;
    padding: 14px 18px;
    font-weight: 600;
    font-size: 15px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
#zmb-chat-close {
    cursor: pointer;
    font-size: 20px;
    background: none;
    border: none;
    color: white;
}
#zmb-chat-body {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    font-size: 13px;
    background: #f8fbfd;
}
#zmb-chat-footer {
    padding: 10px;
    border-top: 1px solid #eee;
    display: flex;
    gap: 8px;
    background: white;
}
#zmb-chat-input {
    flex: 1;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    outline: none;
}
#zmb-chat-send {
    background: #1d3557;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    cursor: pointer;
    font-size: 13px;
}
#zmb-chat-send:hover { background: #457b9d; }
.zmb-msg-user {
    background: #1d3557;
    color: white;
    border-radius: 12px 12px 2px 12px;
    padding: 8px 12px;
    margin: 6px 0 6px 30px;
    font-size: 13px;
}
.zmb-msg-ai {
    background: white;
    border: 1px solid #dde;
    border-radius: 12px 12px 12px 2px;
    padding: 8px 12px;
    margin: 6px 30px 6px 0;
    font-size: 13px;
}
</style>

<button id="zmb-chat-btn" title="Ask the Zambia GeoHub AI">🗺️</button>

<div id="zmb-chat-panel">
  <div id="zmb-chat-header">
    <span>Zambia GeoHub AI</span>
    <button id="zmb-chat-close">✕</button>
  </div>
  <div id="zmb-chat-body">
    <div class="zmb-msg-ai">Hi! Ask me anything about Zambia's geospatial data — health facilities, roads, districts, water, and more.</div>
  </div>
  <div id="zmb-chat-footer">
    <input id="zmb-chat-input" type="text" placeholder="Ask about Zambia data..." />
    <button id="zmb-chat-send">Send</button>
  </div>
</div>

<script>
const btn = document.getElementById('zmb-chat-btn');
const panel = document.getElementById('zmb-chat-panel');
const closeBtn = document.getElementById('zmb-chat-close');
const input = document.getElementById('zmb-chat-input');
const sendBtn = document.getElementById('zmb-chat-send');
const body = document.getElementById('zmb-chat-body');

btn.onclick = () => panel.classList.toggle('open');
closeBtn.onclick = () => panel.classList.remove('open');

function addMsg(text, role) {
    const div = document.createElement('div');
    div.className = role === 'user' ? 'zmb-msg-user' : 'zmb-msg-ai';
    div.innerText = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}

sendBtn.onclick = () => {
    const q = input.value.trim();
    if (!q) return;
    addMsg(q, 'user');
    input.value = '';
    addMsg('Searching Zambia GeoHub data...', 'ai');
    // Note: full AI response handled in main Streamlit tab
    // This widget is a visual preview for Hub embedding
    // For full AI: open the main tab or use the full app URL
    setTimeout(() => {
        body.lastChild.innerText = 'For a full AI response with maps and reports, use the chat tab above or open the full app.';
    }, 1200);
};

input.addEventListener('keydown', e => { if (e.key === 'Enter') sendBtn.click(); });
</script>
""", unsafe_allow_html=True)

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
def get_hub():
    return HubClient()

@st.cache_resource(show_spinner=False)
def get_claude():
    return ClaudeClient()

@st.cache_resource(show_spinner=False)
def get_report_builder():
    return ReportBuilder()

hub = get_hub()
claude = get_claude()
builder = get_report_builder()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
defaults = {
    "chat_messages": [],       # [{role, content, question, datasets, geojson}]
    "chat_last_map": None,
    "chat_edit_idx": None,     # index of message being edited
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
# TAB 1 — AI CHATBOT  (with edit prompt + report download per response)
# ===========================================================================
with tab1:
    st.markdown("### Ask anything about Zambia's GeoHub data")
    st.caption("Ask about health facilities, roads, districts, water, schools, and more.")

    def run_query(question: str):
        """Run a question through the AI and append results to chat history."""
        with st.spinner("Searching GeoHub datasets..."):
            try:
                datasets = hub.search_datasets(question, max_results=5)
            except Exception as e:
                datasets = []
                st.warning(f"Hub search failed: {e}")

        sample_features = []
        geojson = None
        folium_map = None

        if datasets:
            top = datasets[0]
            try:
                with st.spinner(f"Loading '{top['name']}' data..."):
                    geojson = hub.fetch_geojson(top["url"], max_features=max_features)
                    sample_features = geojson_to_sample_rows(geojson, n=5)
                    folium_map = make_folium_map(geojson, top["name"])
            except Exception as e:
                st.warning(f"Could not load dataset: {e}")

        system = chatbot_system_prompt()
        user_p = chatbot_user_prompt(question, datasets, sample_features, all_catalog=hub.get_catalog())

        with st.chat_message("assistant"):
            try:
                response_text = st.write_stream(claude.stream(system, user_p, max_tokens=1500))
            except Exception as e:
                response_text = f"AI error: {e}"
                st.error(response_text)

            if datasets:
                with st.expander("Datasets searched"):
                    for ds in datasets:
                        st.markdown(f"- **{ds['name']}** — {ds['description'][:120]}")

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": response_text,
            "question": question,
            "datasets": datasets,
            "geojson": geojson,
        })

        if folium_map:
            st.session_state.chat_last_map = folium_map

    # Render existing messages
    for i, msg in enumerate(st.session_state.chat_messages):
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

                # --- Edit prompt button ---
                col_edit, col_rpt, col_blank = st.columns([1, 1, 4])
                with col_edit:
                    if st.button("✏️ Edit prompt", key=f"edit_{i}"):
                        st.session_state.chat_edit_idx = i - 1  # point to user msg before this
                        st.rerun()
                with col_rpt:
                    # Generate report from this response's dataset
                    if msg.get("datasets") and msg.get("geojson"):
                        if st.button("📄 Get Report", key=f"rpt_{i}"):
                            ds = msg["datasets"][0]
                            gj = msg["geojson"]
                            stats = summarize_geojson(gj)
                            samples = geojson_to_sample_rows(gj, n=10)
                            with st.spinner("Generating report..."):
                                rpt_text = claude.ask(
                                    system=report_system_prompt(),
                                    user=report_prompt(ds["name"], ds["description"], ds["fields"], stats, samples),
                                    max_tokens=3000,
                                )
                                docx_bytes = builder.to_docx(ds["name"], rpt_text, ds)
                                pdf_bytes = builder.to_pdf(ds["name"], rpt_text, ds)

                            st.markdown("**Download report:**")
                            c1, c2 = st.columns(2)
                            c1.download_button(
                                "⬇️ Word (.docx)", docx_bytes,
                                file_name=f"{ds['name'].replace(' ','_')}_report.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"docx_{i}", use_container_width=True,
                            )
                            c2.download_button(
                                "⬇️ PDF", pdf_bytes,
                                file_name=f"{ds['name'].replace(' ','_')}_report.pdf",
                                mime="application/pdf",
                                key=f"pdf_{i}", use_container_width=True,
                            )

                # Show map for this message
                if msg.get("geojson"):
                    m = make_folium_map(msg["geojson"], msg["datasets"][0]["name"] if msg.get("datasets") else "")
                    st_folium(m, width=720, height=340, returned_objects=[], key=f"map_{i}")

    # --- Edit prompt area ---
    edit_idx = st.session_state.get("chat_edit_idx")
    if edit_idx is not None and edit_idx < len(st.session_state.chat_messages):
        original_q = st.session_state.chat_messages[edit_idx]["content"]
        st.markdown("---")
        st.markdown("**Edit your prompt:**")
        edited = st.text_area("Edit prompt", value=original_q, key="edit_text_area", height=80)
        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("Submit edit", type="primary"):
                # Remove everything from the edited message onwards
                st.session_state.chat_messages = st.session_state.chat_messages[:edit_idx]
                st.session_state.chat_edit_idx = None
                # Add edited user message
                st.session_state.chat_messages.append({"role": "user", "content": edited})
                run_query(edited)
                st.rerun()
        with col_b:
            if st.button("Cancel"):
                st.session_state.chat_edit_idx = None
                st.rerun()
    else:
        # Normal chat input
        if question := st.chat_input("Ask about Zambia's GeoHub data..."):
            with st.chat_message("user"):
                st.markdown(question)
            st.session_state.chat_messages.append({"role": "user", "content": question})
            run_query(question)
            st.rerun()

    if st.session_state.chat_messages:
        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.chat_messages = []
            st.session_state.chat_last_map = None
            st.session_state.chat_edit_idx = None
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
        selected_name = st.selectbox("Select a dataset", list(options.keys()), key="report_selectbox")
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
                st.info("Dataset exceeds transfer limit — report is based on a sample.")

            with st.spinner("Generating AI report (~15 seconds)..."):
                try:
                    rpt_text = claude.ask(
                        system=report_system_prompt(),
                        user=report_prompt(ds["name"], ds["description"], ds["fields"], stats, samples),
                        max_tokens=3000,
                    )
                    st.session_state.report_content = rpt_text
                except Exception as e:
                    st.error(f"AI generation failed: {e}")
                    st.stop()

            with st.spinner("Building Word and PDF files..."):
                try:
                    st.session_state.report_docx = builder.to_docx(ds["name"], rpt_text, ds)
                    st.session_state.report_pdf = builder.to_pdf(ds["name"], rpt_text, ds)
                except Exception as e:
                    st.error(f"Document build failed: {e}")
                    st.stop()

    if st.session_state.report_content:
        ds = st.session_state.report_selected
        st.markdown("---")
        st.markdown(f"#### Report: {ds['name']}")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇️ Download Word (.docx)", st.session_state.report_docx,
                file_name=f"{ds['name'].replace(' ', '_')}_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with col_dl2:
            st.download_button(
                "⬇️ Download PDF", st.session_state.report_pdf,
                file_name=f"{ds['name'].replace(' ', '_')}_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with st.expander("Preview report content", expanded=True):
            st.markdown(st.session_state.report_content)

        if st.session_state.report_geojson:
            st.markdown("**Dataset map preview**")
            m = make_folium_map(st.session_state.report_geojson, ds["name"])
            st_folium(m, width=750, height=380, returned_objects=[])

# ===========================================================================
# TAB 3 — DATASET SUMMARIZER
# ===========================================================================
with tab3:
    st.markdown("### Summarise any GeoHub dataset in plain language")
    st.caption("Get an instant plain-English summary — no GIS knowledge needed.")

    col_s, col_b = st.columns([4, 1])
    with col_s:
        sum_query = st.text_input(
            "Search for a dataset to summarise",
            placeholder="e.g. zambia schools, water access points, districts",
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
        selected_name = st.selectbox("Choose dataset", list(options.keys()), key="sum_selectbox")
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
                        user=summarizer_prompt(ds["name"], ds["description"], ds["fields"], samples, stats["feature_count"]),
                        max_tokens=1024,
                    )
                    st.session_state.sum_content = summary
                except Exception as e:
                    st.error(f"AI summary failed: {e}")
                    st.stop()

    if st.session_state.sum_content:
        ds = st.session_state.sum_selected
        stats = st.session_state.sum_stats

        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Features loaded", f"{stats['feature_count']:,}")
        m2.metric("Geometry type", stats["geometry_type"].replace("esriGeometry", ""))
        m3.metric("Fields", len(stats["fields"]))
        m4.metric("Numeric fields", len(stats.get("numeric_stats", {})))

        if stats.get("exceeded_limit"):
            st.warning("Transfer limit reached — stats based on a partial sample.")

        st.markdown(f"#### Summary: {ds['name']}")
        st.markdown(st.session_state.sum_content)

        st.download_button(
            "⬇️ Download Summary (.txt)", st.session_state.sum_content,
            file_name=f"{ds['name'].replace(' ', '_')}_summary.txt",
            mime="text/plain",
        )

        if ds.get("fields"):
            with st.expander("Field Reference"):
                import pandas as pd
                field_df = pd.DataFrame([
                    {"Field name": f["name"], "Label": f["alias"], "Type": f["type"]}
                    for f in ds["fields"]
                ])
                st.dataframe(field_df, use_container_width=True)

        if st.session_state.sum_geojson:
            st.markdown("**Spatial preview**")
            folium_m = make_folium_map(st.session_state.sum_geojson, ds["name"])
            st_folium(folium_m, width=750, height=380, returned_objects=[])
