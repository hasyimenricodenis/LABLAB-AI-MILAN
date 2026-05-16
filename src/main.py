"""CLI entry point for the public-health multi-agent workflow."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

from src.workflows.public_health_workflow import PublicHealthWorkflow


ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_records(path: Path) -> List[Dict[str, Any]]:
    df = pd.read_csv(path)
    df = df.where(pd.notna(df), "")
    return df.to_dict(orient="records")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the public-health multi-agent workflow.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "agents.yaml",
        help="Path to agents.yaml configuration.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / "src" / "data" / "public_health_sample.csv",
        help="Path to input CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write full JSON output (workflow result).",
    )
    parser.add_argument(
        "--no-narrative",
        action="store_true",
        help="Skip the LLM narrative briefing step.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose agent logging.",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")

    config = load_config(args.config)
    records = load_records(args.data)

    workflow = PublicHealthWorkflow(config=config, enable_narrative=not args.no_narrative)
    output = workflow.run(raw_records=records)

    print("=== Workflow Trace ===")
    print(f"trace_id: {output['audit']['trace_id']}")
    for entry in output["audit"]["entries"]:
        print(
            f"  - {entry['agent']:<16} in={entry['input_count']:>3} "
            f"out={entry['output_count']:>3} {entry['duration_ms']:>4}ms  notes={entry['notes']}"
        )

    print("\n=== Citizen Service Actions ===")
    for item in output["citizen_actions"]:
        print(
            f"  [{item['service_priority'].upper():<6}] {item['report_id']} | "
            f"{item['district']} | {item['suspected_condition']} | "
            f"risk={item['risk_score']} | {item['recommended_action']}"
        )

    print("\n=== Citizen Messages ===")
    for msg in output["messages"]:
        print(f"  ({msg['language']}) [{msg['priority']}] {msg['report_id']}: {msg['text']}")

    if output["briefing"]:
        print("\n=== Daily Briefing ===")
        print(output["briefing"])

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nFull result written to {args.output}")


if __name__ == "__main__":
    main()
