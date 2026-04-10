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
            "  persona-test --persona persona.md --url http://localhost:3000 "
            '--objectives "login, browse dashboard" --manifest manifest.json '
            "--max-steps 30 --timeout 90\n"
            "  persona-test --persona persona.md --url http://localhost:3000 "
            '--objectives "checkout flow" --app-domains "localhost:3000,api.myapp.com" '
            "--no-capture-network\n"
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

    # --- New flags (Phase 2) ---
    parser.add_argument(
        "--manifest", default="",
        help=(
            "Path to manifest.json file (used by navigator for page navigation, "
            "auth flow, and verification tasks)"
        ),
    )
    parser.add_argument(
        "--capture-network",
        dest="capture_network",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Enable or disable HAR recording (default: from config, currently enabled). "
            "Use --no-capture-network to disable."
        ),
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Max browser-use agent steps before stopping (default: from config, 50)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Max seconds for navigator session (default: from config, 120)",
    )
    parser.add_argument(
        "--app-domains",
        type=str,
        default="",
        help=(
            "Comma-separated list of domains to include in HAR filtering "
            "(default: all domains). Example: localhost:3000,api.myapp.com"
        ),
    )
    parser.add_argument(
        "--codeintel",
        default="",
        help="Path to codeintel.json for scoring pipeline (enables full pipeline mode)",
    )
    parser.add_argument(
        "--rubric",
        default="",
        help="Path to consumer rubric.md for scoring pipeline (enables full pipeline mode)",
    )

    args = parser.parse_args()

    # Early validation — fail fast with clear errors
    if not Path(args.persona).exists():
        print(json.dumps({
            "status": "SKIP",
            "error": f"Persona file not found: {args.persona}",
            "reason": "missing_persona",
        }))
        sys.exit(0)

    if args.codeintel and not Path(args.codeintel).exists():
        print(json.dumps({
            "status": "SKIP",
            "error": f"Codeintel file not found: {args.codeintel}",
            "reason": "missing_codeintel",
        }))
        sys.exit(0)

    if args.rubric and not Path(args.rubric).exists():
        print(json.dumps({
            "status": "SKIP",
            "error": f"Rubric file not found: {args.rubric}",
            "reason": "missing_rubric",
        }))
        sys.exit(0)

    # Load config
    config = load_config(args.config or None)

    # Override config with explicit CLI args
    if args.capture_network is not None:
        config.browser.capture_network = args.capture_network
    if args.max_steps is not None:
        config.browser.max_steps = args.max_steps
    if args.timeout is not None:
        config.browser.timeout_seconds = args.timeout

    # Parse app_domains from comma-separated string to list
    domains = args.app_domains.split(",") if args.app_domains else []

    # Load form data if provided
    form_data = ""
    if args.form_data and Path(args.form_data).exists():
        form_data = Path(args.form_data).read_text(encoding="utf-8")

    # Run test — full pipeline or navigator-only
    if args.codeintel and args.rubric:
        # Full pipeline: navigator → scorers → reconciler
        from .pipeline import run_pipeline_sync

        report = run_pipeline_sync(
            persona_path=args.persona,
            url=args.url,
            objectives=args.objectives,
            config=config,
            codeintel_path=args.codeintel,
            rubric_path=args.rubric,
            scope=args.scope,
            task_id=args.task_id,
            form_data=form_data,
            manifest_path=args.manifest,
            screenshots_dir=args.screenshots_dir,
            record_video_dir=args.record_video,
            app_domains=domains,
        )
    else:
        # Navigator only (backward compat)
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
            manifest_path=args.manifest,
            app_domains=domains,
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
