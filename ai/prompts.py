"""
Prompt template functions for the three AI features.

Each function returns either a system-prompt string or a user-prompt string
ready to pass directly to ClaudeClient.ask() / ClaudeClient.stream().
"""

import json


# ---------------------------------------------------------------------------
# Feature 1 — AI Chatbot
# ---------------------------------------------------------------------------

def chatbot_system_prompt() -> str:
    return (
        "You are an AI assistant for the Zambia GeoHub (zmb-geowb.hub.arcgis.com). "
        "You ONLY answer questions using data provided to you from the Zambia GeoHub datasets. "
        "You do NOT use any general knowledge, external sources, or information outside of what is given to you.\n\n"
        "STRICT RULES:\n"
        "- If the provided dataset samples do not contain enough information to answer the question, "
        "respond with: 'This information is not available in the current Zambia GeoHub datasets. "
        "Please check the Hub directly at zmb-geowb.hub.arcgis.com for more datasets.'\n"
        "- NEVER make up statistics, estimates, or facts not present in the data.\n"
        "- NEVER answer from general knowledge about Zambia or any other topic.\n"
        "- Always cite the exact dataset name you used to answer.\n"
        "- Be concise and factual — 3 to 5 sentences unless a list is clearer.\n"
        "- If data is a sample (not the full dataset), state that clearly."
    )


def chatbot_user_prompt(
    question: str,
    datasets: list[dict],
    sample_features: list[dict],
) -> str:
    """
    Build the user-turn prompt for the chatbot.

    datasets       : list of cleaned dataset dicts from HubClient
    sample_features: list of feature property dicts (up to 5)
    """
    dataset_context = ""
    for i, ds in enumerate(datasets[:3], 1):
        dataset_context += (
            f"\nDataset {i}: {ds['name']}\n"
            f"  Description: {ds['description'][:200]}\n"
            f"  Fields: {', '.join(f['name'] for f in ds.get('fields', [])[:15])}\n"
        )

    sample_json = json.dumps(sample_features[:5], indent=2)

    return (
        f"Question: {question}\n\n"
        f"Available datasets from the Zambia GeoHub:\n{dataset_context}\n"
        f"Sample feature data (first {len(sample_features)} records):\n"
        f"```json\n{sample_json}\n```\n\n"
        "Please answer the question using the data above. "
        "If the sample is too small to give a definitive answer, say so and explain "
        "what additional data would be needed."
    )


# ---------------------------------------------------------------------------
# Feature 2 — Dataset Summarizer
# ---------------------------------------------------------------------------

def summarizer_system_prompt() -> str:
    return (
        "You are an AI assistant for the Zambia GeoHub (zmb-geowb.hub.arcgis.com). "
        "You ONLY summarise data that is explicitly provided to you from the Zambia GeoHub. "
        "Do NOT add any general knowledge, external facts, or information not present in the provided dataset. "
        "Write clearly for non-technical readers in Zambia's government and NGO sector. "
        "If the data is insufficient to make a meaningful summary, say so honestly."
    )


def summarizer_prompt(
    dataset_name: str,
    description: str,
    fields: list[dict],
    sample_features: list[dict],
    feature_count: int,
) -> str:
    """Build the user-turn prompt for the dataset summarizer."""
    field_lines = "\n".join(
        f"  - {f['alias'] or f['name']} ({f['type']})" for f in fields[:20]
    )
    sample_json = json.dumps(sample_features[:5], indent=2)

    return (
        f"Dataset: {dataset_name}\n"
        f"Description: {description[:300]}\n"
        f"Total features loaded: {feature_count}\n\n"
        f"Fields available:\n{field_lines}\n\n"
        f"Sample records (first {len(sample_features)}):\n"
        f"```json\n{sample_json}\n```\n\n"
        "Please produce:\n"
        "1. **Overview** (2–3 sentences) — what this dataset contains and why it matters for Zambia.\n"
        "2. **Key Fields** — a short bullet list explaining the most important fields.\n"
        "3. **Notable Insights** — 2–3 observations drawn from the sample data.\n"
        "4. **Suggested Use Cases** — 3 practical ways planners or NGOs could use this data.\n\n"
        "Write for a non-GIS audience. Avoid technical jargon."
    )


# ---------------------------------------------------------------------------
# Feature 3 — Report Generator
# ---------------------------------------------------------------------------

def report_system_prompt() -> str:
    return (
        "You are an AI report writer for the Zambia GeoHub (zmb-geowb.hub.arcgis.com). "
        "You ONLY write reports based on data explicitly provided to you from the Zambia GeoHub datasets. "
        "Do NOT include any general knowledge, external statistics, or facts not present in the provided data. "
        "Every claim in the report must be traceable to the dataset provided. "
        "If data is insufficient for a section, write 'Insufficient data available in this dataset' for that section. "
        "Reports are for Zambia government stakeholders and development partners — keep them formal and evidence-based."
    )


def report_prompt(
    dataset_name: str,
    description: str,
    fields: list[dict],
    stats: dict,
    sample_features: list[dict],
) -> str:
    """
    Build the user-turn prompt for the report generator.

    stats : output of geo_utils.summarize_geojson()
    """
    field_lines = "\n".join(
        f"  - {f['alias'] or f['name']} ({f['type']})" for f in fields[:20]
    )

    numeric_summary = ""
    for field, s in list(stats.get("numeric_stats", {}).items())[:8]:
        numeric_summary += f"  - {field}: min={s['min']}, max={s['max']}, mean={s['mean']}\n"

    numeric_block = numeric_summary if numeric_summary else "  (none computed)\n"

    sample_json = json.dumps(sample_features[:10], indent=2)

    exceeded_note = ""
    if stats.get("exceeded_limit"):
        exceeded_note = (
            "\n⚠️ Note: The dataset exceeds the transfer limit — "
            "statistics are based on a sample only.\n"
        )

    return (
        f"Dataset: {dataset_name}\n"
        f"Description: {description[:400]}\n"
        f"Geometry type: {stats.get('geometry_type', 'Unknown')}\n"
        f"Features loaded: {stats.get('feature_count', 0)}{exceeded_note}\n\n"
        f"Fields:\n{field_lines}\n\n"
        f"Numeric field statistics:\n{numeric_block}\n"
        f"Sample records:\n```json\n{sample_json}\n```\n\n"
        "Generate a formal analytical report with the following sections using ## headings:\n\n"
        "## Executive Summary\n"
        "## Dataset Overview\n"
        "## Key Fields and Attributes\n"
        "## Statistical Highlights\n"
        "## Observations and Analysis\n"
        "## Data Limitations\n"
        "## Recommended Next Steps\n\n"
        "Write in professional report style. Use bullet points where appropriate. "
        "Be specific — reference field names, numbers, and districts where the data supports it. "
        "The report should be suitable for printing and sharing with senior officials."
    )
