"""CLI entry point for persona browser testing."""

import argparse
import json
import sys
from pathlib import Path

from .agent import run_sync
from .config import load_config


def main():
    parser = argparse.ArgumentParser(
        description="Persona Browser Agent — AI-driven browser testing as simulated personas",
        epilog=(
            "Examples:\n"
            "  persona-test --persona persona.md --url http://localhost:3000 "
            '--objectives "find signup, fill form, submit"\n'
            "  persona-test --persona micro-persona.md --url http://localhost:5173 "
            '--objectives "search for product, add to cart" --scope gate\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--persona", required=True,
        help="Path to persona or micro-persona .md file",
    )
    parser.add_argument(
        "--url", required=True,
        help="URL of running application (e.g., http://localhost:3000)",
    )
    parser.add_argument(
        "--objectives", required=True,
        help="Comma-separated objectives to test as the persona",
    )
    parser.add_argument(
        "--output", default="",
        help="Path to write JSON report (default: stdout)",
    )
    parser.add_argument(
        "--config", default="",
        help="Path to config.yaml (default: auto-detect)",
    )
    parser.add_argument(
        "--scope", choices=["task", "gate"], default="task",
        help="Test scope: task (narrow) or gate (full app walkthrough)",
    )
    parser.add_argument(
        "--task-id", default="",
        help="Task ID for per-task tests (e.g., T01)",
    )
    parser.add_argument(
        "--form-data", default="",
        help="Path to file with realistic form data for the persona",
    )
    parser.add_argument(
        "--screenshots-dir", default="",
        help="Directory for screenshots (overrides config)",
    )
    parser.add_argument(
        "--record-video", default="",
        help="Directory for video recordings (overrides config)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config or None)

    # Load form data if provided
    form_data = ""
    if args.form_data and Path(args.form_data).exists():
        form_data = Path(args.form_data).read_text(encoding="utf-8")

    # Run test
    report = run_sync(
        persona_path=args.persona,
        url=args.url,
        objectives=args.objectives,
        config=config,
        scope=args.scope,
        task_id=args.task_id,
        form_data=form_data,
        screenshots_dir=args.screenshots_dir,
        record_video_dir=args.record_video,
    )

    # Output
    report_json = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report_json, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)

    # Always print to stdout (SUDD agents capture this)
    print(report_json)


if __name__ == "__main__":
    main()
