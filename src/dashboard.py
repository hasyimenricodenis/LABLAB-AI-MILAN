"""Streamlit human-in-the-loop dashboard for the public-health workflow.

Run with:
    streamlit run src/dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import yaml

from src.workflows.public_health_workflow import PublicHealthWorkflow

DEFAULT_CONFIG = ROOT / "config" / "agents.yaml"
DEFAULT_DATA = ROOT / "src" / "data" / "public_health_sample.csv"


@st.cache_data(show_spinner=False)
def load_config(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def records_from_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df = df.where(pd.notna(df), "")
    return df.to_dict(orient="records")


def render_actions(actions: List[Dict[str, Any]]) -> None:
    if not actions:
        st.info("No actions to review.")
        return

    df = pd.DataFrame(actions)
    df["approve"] = df["service_priority"] != "high"
    edited = st.data_editor(
        df,
        column_config={
            "approve": st.column_config.CheckboxColumn(
                "Approve (officer)", help="Uncheck high-priority cases to escalate."
            ),
            "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100),
        },
        hide_index=True,
        use_container_width=True,
        key="actions_editor",
    )
    escalated = edited[~edited["approve"]]
    st.metric("Cases pending officer review", len(escalated))


def render_messages(messages: List[Dict[str, Any]]) -> None:
    if not messages:
        st.info("No citizen messages produced.")
        return
    df = pd.DataFrame(messages)
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_audit(audit: Dict[str, Any]) -> None:
    st.caption(f"trace_id: `{audit['trace_id']}`")
    entries = audit["entries"]
    if not entries:
        st.info("No audit entries.")
        return
    df = pd.DataFrame(entries)
    df["notes"] = df["notes"].apply(lambda n: ", ".join(f"{k}={v}" for k, v in n.items()))
    st.dataframe(
        df[["agent", "duration_ms", "input_count", "output_count", "notes"]],
        hide_index=True,
        use_container_width=True,
    )


def _bar_df(rows, label_col: str) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=[label_col, "count"])
    total = max(df["count"].max(), 1)
    df["share"] = (df["count"] / total).round(3)
    return df


def render_trends(trends: Dict[str, Any]) -> None:
    if not trends:
        return
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top districts")
        if trends.get("top_districts"):
            st.dataframe(
                _bar_df(trends["top_districts"], "district"),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "share": st.column_config.ProgressColumn(
                        "share", min_value=0, max_value=1, format="%.2f"
                    ),
                },
            )
    with col2:
        st.subheader("Top conditions")
        if trends.get("top_conditions"):
            st.dataframe(
                _bar_df(trends["top_conditions"], "condition"),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "share": st.column_config.ProgressColumn(
                        "share", min_value=0, max_value=1, format="%.2f"
                    ),
                },
            )
    st.subheader("Priority distribution")
    if trends.get("priority_distribution"):
        priority = trends["priority_distribution"]
        cols = st.columns(len(priority))
        for col, (name, count) in zip(cols, priority.items()):
            col.metric(name.upper(), count)


def main() -> None:
    st.set_page_config(
        page_title="Jakarta Public Health Agents",
        page_icon=":hospital:",
        layout="wide",
    )
    st.title("Jakarta Public Health · Autonomous Agents")
    st.caption("Built for LabLab AI Milan — Jakarta-powered, globally minded.")

    with st.sidebar:
        st.header("Configuration")
        config = load_config(DEFAULT_CONFIG)
        enable_narrative = st.toggle(
            "Enable LLM briefing", value=True, help="Requires ANTHROPIC_API_KEY; falls back to template otherwise."
        )
        uploaded = st.file_uploader("Upload custom CSV", type=["csv"])
        st.markdown("---")
        st.markdown("**Pipeline**")
        st.markdown("ingestion → quality → privacy → insight → citizen_service → messaging → narrative")

    if uploaded is not None:
        df_raw = pd.read_csv(uploaded)
    else:
        df_raw = pd.read_csv(DEFAULT_DATA)

    st.subheader("Raw input")
    st.dataframe(df_raw, hide_index=True, use_container_width=True)

    if st.button("Run workflow", type="primary"):
        with st.spinner("Running multi-agent workflow..."):
            workflow = PublicHealthWorkflow(config=config, enable_narrative=enable_narrative)
            output = workflow.run(raw_records=records_from_dataframe(df_raw))
        st.session_state["output"] = output

    output = st.session_state.get("output")
    if not output:
        st.info("Click **Run workflow** to process the records.")
        return

    tabs = st.tabs(["Actions", "Messages", "Briefing", "Trends", "Audit"])

    with tabs[0]:
        st.subheader("Citizen-service actions")
        render_actions(output["citizen_actions"])
        st.download_button(
            "Download actions (CSV)",
            data=pd.DataFrame(output["citizen_actions"]).to_csv(index=False).encode("utf-8"),
            file_name="actions.csv",
        )

    with tabs[1]:
        st.subheader("Citizen messages")
        render_messages(output["messages"])
        st.download_button(
            "Download messages (CSV)",
            data=pd.DataFrame(output["messages"]).to_csv(index=False).encode("utf-8"),
            file_name="messages.csv",
        )

    with tabs[2]:
        st.subheader("Daily briefing")
        if output["briefing"]:
            st.code(output["briefing"], language="markdown")
        else:
            st.info("Narrative agent disabled.")

    with tabs[3]:
        render_trends(output["trends"])

    with tabs[4]:
        st.subheader("Audit trail")
        render_audit(output["audit"])


if __name__ == "__main__":
    main()
