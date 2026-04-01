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
        "You are a geospatial analyst assistant for Zambia's national GeoHub platform. "
        "You help government planners, NGO officers, and researchers understand Zambia's "
        "geographic data — covering health, infrastructure, agriculture, population, water, "
        "land cover, and administrative boundaries.\n\n"
        "When answering:\n"
        "- Ground your answer in the provided dataset samples.\n"
        "- Be factual and concise (3–5 sentences unless a list is clearer).\n"
        "- Cite the dataset name(s) you used.\n"
        "- Note data limitations (e.g. sample size, date of data) when relevant.\n"
        "- If the data is insufficient to answer confidently, say so clearly."
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
        "You are a geospatial data analyst writing summaries for non-technical readers "
        "in Zambia's government and NGO sector. "
        "Your summaries must be clear, jargon-free, and actionable."
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
        "You are a professional GIS report writer producing formal reports for "
        "Zambia government stakeholders and international development partners. "
        "Your reports are clear, structured, evidence-based, and professionally toned."
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
