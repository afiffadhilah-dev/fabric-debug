"""
Generate timing report for interview sessions from Langfuse.

Fetches trace and observation data from Langfuse to produce a breakdown of:
- Per-node execution times
- LLM call durations and tokens
- Hierarchical view of processes within each node

Candidate ID is automatically fetched from Langfuse trace metadata.

Usage:
    python scripts/langfuse_timing_report.py <session_id>
    python scripts/langfuse_timing_report.py <session_id> --output report.txt
    python scripts/langfuse_timing_report.py <session_id> --stdout

By default, saves to: docs/simulate-and-generete-report/timing-report/langfuse-{local|staging}-{session_id}.txt

Examples:
    python scripts/langfuse_timing_report.py abc123-def456
    python scripts/langfuse_timing_report.py abc123-def456 --stdout
    python scripts/langfuse_timing_report.py abc123-def456 -o custom_report.txt
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from langfuse import Langfuse


def build_observation_tree(observations: list) -> dict:
    """
    Build a tree structure from observations using parent_observation_id.

    Returns:
        dict mapping observation_id to its children
    """
    # Create lookup and children map
    obs_by_id = {obs.id: obs for obs in observations}
    children_map = {}  # parent_id -> [children]
    root_observations = []

    for obs in observations:
        parent_id = obs.parent_observation_id
        if parent_id is None:
            root_observations.append(obs)
        else:
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(obs)

    return {
        "roots": root_observations,
        "children": children_map,
        "by_id": obs_by_id,
    }


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds is None:
        return "N/A"
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}µs"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


def format_tokens(obs) -> str:
    """Format token info for LLM calls."""
    if not obs.usage_details:
        return ""
    input_t = obs.usage_details.get("input", 0)
    output_t = obs.usage_details.get("output", 0)
    total_t = obs.usage_details.get("total", 0)
    return f"[{input_t:,} → {output_t:,} = {total_t:,} tokens]"


def get_timing_report(session_id: str) -> dict:
    """
    Fetch timing breakdown for an interview session from Langfuse.
    Tries dev environment first, falls back to staging if no traces found.
    """
    # Try dev environment first
    langfuse = Langfuse()
    traces = langfuse.api.trace.list(session_id=session_id, limit=100)
    env_used = "dev"

    # If no traces found, try staging environment
    if not traces.data:
        stg_public_key = os.environ.get("LANGFUSE_PUBLIC_KEY_STG")
        stg_secret_key = os.environ.get("LANGFUSE_SECRET_KEY_STG")

        if stg_public_key and stg_secret_key:
            print("No traces in dev, trying staging environment...")
            langfuse = Langfuse(
                public_key=stg_public_key.strip(),
                secret_key=stg_secret_key.strip(),
            )
            traces = langfuse.api.trace.list(session_id=session_id, limit=100)
            env_used = "staging"

    # If no traces found, try production environment
    if not traces.data:
        prod_public_key = os.environ.get("LANGFUSE_PUBLIC_KEY_PROD")
        prod_secret_key = os.environ.get("LANGFUSE_SECRET_KEY_PROD")

        if prod_public_key and prod_secret_key:
            print("No traces in staging, trying production environment...")
            langfuse = Langfuse(
                public_key=prod_public_key.strip(),
                secret_key=prod_secret_key.strip(),
            )
            traces = langfuse.api.trace.list(session_id=session_id, limit=100)
            env_used = "production"

    if not traces.data:
        return {"error": f"No traces found for session_id: {session_id} (checked dev, staging, and production)"}

    print(f"Found {len(traces.data)} traces in {env_used} environment")

    # Extract candidate_id from first trace's user_id
    candidate_id = None
    if traces.data:
        first_trace = traces.data[0]
        candidate_id = getattr(first_trace, 'user_id', None)

    report = {
        "session_id": session_id,
        "environment": env_used,
        "candidate_id": candidate_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "traces_count": len(traces.data),
        "total_duration_s": 0,
        "total_cost_usd": 0,
        "total_tokens": {"input": 0, "output": 0, "total": 0},
        "nodes_summary": {},
        "llm_summary": {},
        "traces": [],
    }

    for trace in traces.data:
        full_trace = langfuse.api.trace.get(trace.id)

        trace_data = {
            "trace_id": trace.id,
            "name": trace.name or "LangGraph",
            "duration_s": full_trace.latency or 0,
            "cost_usd": full_trace.total_cost or 0,
            "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
            "observations": full_trace.observations or [],
        }

        report["total_duration_s"] += trace_data["duration_s"]
        report["total_cost_usd"] += trace_data["cost_usd"]

        # Aggregate tokens, node stats, and LLM stats
        for obs in full_trace.observations or []:
            if obs.type == "GENERATION":
                # Aggregate tokens
                if obs.usage_details:
                    report["total_tokens"]["input"] += obs.usage_details.get("input", 0)
                    report["total_tokens"]["output"] += obs.usage_details.get("output", 0)
                    report["total_tokens"]["total"] += obs.usage_details.get("total", 0)

                # Aggregate LLM calls by model
                model_name = obs.model or "unknown"
                if model_name not in report["llm_summary"]:
                    report["llm_summary"][model_name] = {
                        "count": 0,
                        "total_duration_s": 0,
                        "total_cost_usd": 0,
                        "total_tokens": 0,
                    }
                report["llm_summary"][model_name]["count"] += 1
                report["llm_summary"][model_name]["total_duration_s"] += obs.latency or 0
                report["llm_summary"][model_name]["total_cost_usd"] += obs.calculated_total_cost or 0
                if obs.usage_details:
                    report["llm_summary"][model_name]["total_tokens"] += obs.usage_details.get("total", 0)

            # Treat non-GENERATION observations as nodes (SPAN, EVENT, or other types)
            if obs.type != "GENERATION":
                node_name = obs.name or "unknown"
                if node_name not in report["nodes_summary"]:
                    report["nodes_summary"][node_name] = {
                        "count": 0,
                        "total_duration_s": 0,
                        "durations": [],
                    }
                duration = obs.latency or 0
                report["nodes_summary"][node_name]["count"] += 1
                report["nodes_summary"][node_name]["total_duration_s"] += duration
                report["nodes_summary"][node_name]["durations"].append(duration)

        report["traces"].append(trace_data)

    # Calculate avg/min/max for nodes
    for node_name, stats in report["nodes_summary"].items():
        durations = stats["durations"]
        if durations:
            stats["avg_duration_s"] = sum(durations) / len(durations)
            stats["min_duration_s"] = min(durations)
            stats["max_duration_s"] = max(durations)
        del stats["durations"]  # Clean up

    return report


def generate_text_report(report: dict) -> str:
    """Generate a text report with summary and detailed breakdown."""
    if "error" in report:
        return f"Error: {report['error']}"

    lines = []
    w = lines.append  # shorthand for writing lines

    # Header
    w("=" * 80)
    w("  LANGFUSE TIMING REPORT")
    w("=" * 80)
    w(f"  Session ID:     {report['session_id']}")
    w(f"  Environment:    {report.get('environment', 'unknown')}")
    if report.get('candidate_id'):
        w(f"  Candidate ID:   {report['candidate_id']}")
    w(f"  Generated:      {report['generated_at']}")
    w(f"  Traces Count:   {report['traces_count']}")
    w("=" * 80)

    # ============ SUMMARY SECTION ============
    w("")
    w("=" * 80)
    w("  SUMMARY")
    w("=" * 80)

    w("")
    w(f"  Total Duration:   {format_duration(report['total_duration_s'])}")
    w(f"  Total Cost:       ${report['total_cost_usd']:.6f}")
    w(f"  Total Tokens:     {report['total_tokens']['total']:,}")
    w(f"    - Input:        {report['total_tokens']['input']:,}")
    w(f"    - Output:       {report['total_tokens']['output']:,}")

    # Nodes summary table
    if report["nodes_summary"]:
        w("")
        w("  NODES TIMING SUMMARY:")
        w(f"  {'Node':<30} {'Count':>6} {'Total':>10} {'Avg':>10} {'Min':>10} {'Max':>10}")
        w("  " + "-" * 78)

        sorted_nodes = sorted(
            report["nodes_summary"].items(),
            key=lambda x: x[1]["total_duration_s"],
            reverse=True
        )

        for node_name, stats in sorted_nodes:
            w(
                f"  {node_name:<30} "
                f"{stats['count']:>6} "
                f"{format_duration(stats['total_duration_s']):>10} "
                f"{format_duration(stats['avg_duration_s']):>10} "
                f"{format_duration(stats['min_duration_s']):>10} "
                f"{format_duration(stats['max_duration_s']):>10}"
            )

    # LLM calls summary table
    if report.get("llm_summary"):
        w("")
        w("  LLM CALLS SUMMARY:")
        w(f"  {'Model':<40} {'Count':>6} {'Duration':>10} {'Cost':>12} {'Tokens':>10}")
        w("  " + "-" * 80)

        sorted_llm = sorted(
            report["llm_summary"].items(),
            key=lambda x: x[1]["total_duration_s"],
            reverse=True
        )

        for model_name, stats in sorted_llm:
            w(
                f"  {model_name:<40} "
                f"{stats['count']:>6} "
                f"{format_duration(stats['total_duration_s']):>10} "
                f"${stats['total_cost_usd']:>11.6f} "
                f"{stats['total_tokens']:>10,}"
            )

    # ============ DETAILED BREAKDOWN SECTION ============
    w("")
    w("=" * 80)
    w("  DETAILED BREAKDOWN (Time Focus)")
    w("=" * 80)

    for i, trace_data in enumerate(report["traces"], 1):
        w("")
        w(f"  TRACE {i}: {trace_data['name']}")
        w(f"  ID: {trace_data['trace_id']}")
        w(f"  Timestamp: {trace_data['timestamp']}")
        w(f"  Total Duration: {format_duration(trace_data['duration_s'])}")
        w("  " + "-" * 76)

        observations = trace_data["observations"]
        if not observations:
            w("    (no observations)")
            continue

        # Build tree structure
        tree = build_observation_tree(observations)

        def print_observation(obs, indent=2):
            """Recursively print observation and its children."""
            prefix = "  " * indent
            duration = format_duration(obs.latency)

            if obs.type == "GENERATION":
                # LLM call - show duration and tokens
                tokens = format_tokens(obs)
                model = obs.model or "unknown"
                w(f"{prefix}├─ {obs.name} ({model})")
                w(f"{prefix}│    Duration: {duration}  {tokens}")
            elif obs.type == "SPAN":
                # Node/span - show duration
                w(f"{prefix}├─ {obs.name}")
                w(f"{prefix}│    Duration: {duration}")
            else:
                # Other types
                w(f"{prefix}├─ {obs.name} [{obs.type}]")
                w(f"{prefix}│    Duration: {duration}")

            # Print children
            children = tree["children"].get(obs.id, [])
            # Sort children by start_time if available
            children_sorted = sorted(
                children,
                key=lambda x: x.start_time if x.start_time else datetime.min.replace(tzinfo=timezone.utc)
            )
            for child in children_sorted:
                print_observation(child, indent + 1)

        # Print root observations (those without parent)
        roots = sorted(
            tree["roots"],
            key=lambda x: x.start_time if x.start_time else datetime.min.replace(tzinfo=timezone.utc)
        )

        for root_obs in roots:
            print_observation(root_obs)

    w("")
    w("=" * 80)
    w("  END OF REPORT")
    w("=" * 80)

    return "\n".join(lines)


def get_default_output_path(session_id: str, environment: str = "local") -> str:
    """Generate default output path: docs/simulate-and-generete-report/timing-report/langfuse-{env}-{session_id}.txt"""
    # Get the project root (parent of scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / "docs" / "simulate-and-generete-report" / "timing-report"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Map environment names: dev -> local, staging -> staging
    env_name = "local" if environment == "dev" else environment
    filename = f"langfuse-{env_name}-{session_id}.txt"

    return str(output_dir / filename)


def main():
    parser = argparse.ArgumentParser(
        description="Generate timing report for interview sessions from Langfuse"
    )
    parser.add_argument(
        "session_id",
        help="Interview session ID to fetch timing data for"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Write report to specified file (default: docs/simulate-and-generete-report/timing-report/langfuse-{env}-{session_id}.txt)"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of saving to file"
    )

    args = parser.parse_args()

    try:
        print(f"Fetching data from Langfuse for session: {args.session_id}...")
        report = get_timing_report(args.session_id)

        text_report = generate_text_report(report)

        if args.stdout:
            print(text_report)
        else:
            environment = report.get("environment", "local")
            output_path = args.output if args.output else get_default_output_path(args.session_id, environment)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text_report)
            print(f"Report written to: {output_path}")

    except Exception as e:
        print(f"Error fetching timing data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
