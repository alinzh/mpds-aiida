"""mpds-benchmark CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .pipeline import run_benchmark, run_benchmark_both, validate_env
from .report import BenchmarkReport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mpds-benchmark",
        description="Run perovskite crystal structure benchmarks (MPDS -> AiiDA -> yascheduler -> report).",
    )
    parser.add_argument(
        "phases",
        nargs="+",
        help="Perovskite identifiers in formula/sg format (e.g. SrTiO3/221 MgO/225)",
    )
    parser.add_argument(
        "--engine",
        choices=["pcrystal", "fleur", "both"],
        default="pcrystal",
        help="Simulation engine to use (default: pcrystal)",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Override benchmark template YAML file (default: engine-specific benchmark template)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output JSON file path (default: stdout)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=7200,
        help="Timeout in seconds per benchmark (default: 7200)",
    )
    parser.add_argument(
        "--absolidix-url",
        default=None,
        help="Absolidix backend URL for API-mode submission (e.g. http://localhost:7050)",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    validate_env()

    all_reports: list[BenchmarkReport] = []

    for phase in args.phases:
        parts = phase.split("/")
        if len(parts) < 2:
            print(f"ERROR: invalid phase format '{phase}', expected formula/sg", file=sys.stderr)
            return 1
        formula = parts[0]
        try:
            sg = int(parts[1])
        except ValueError:
            print(f"ERROR: invalid spacegroup '{parts[1]}' in '{phase}'", file=sys.stderr)
            return 1

        if args.absolidix_url:
            report = run_benchmark_absolidix(
                formula, sg, args.engine, args.absolidix_url, args.timeout
            )
            all_reports.append(report)
        elif args.engine == "both":
            reports = run_benchmark_both(formula, sg, args.template, args.timeout)
            all_reports.extend(reports)
        else:
            report = run_benchmark(formula, sg, args.engine, args.template, args.timeout)
            all_reports.append(report)

    output_json = json.dumps(
        [r.to_dict() for r in all_reports], indent=2
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Report written to {args.output}")
    else:
        print(output_json)

    has_failure = any(r.status in ("failed", "timeout", "no_structure") for r in all_reports)
    return 1 if has_failure else 0


def run_benchmark_absolidix(
    formula: str,
    sg: int,
    engine: str,
    absolidix_url: str,
    timeout: int,
) -> BenchmarkReport:
    """Submit benchmark via absolidix backend API and poll for results."""
    import urllib.request
    import urllib.parse
    import time

    report = BenchmarkReport(formula=formula, sg=sg, engine=engine, status="submitted")

    create_url = f"{absolidix_url}/calculations/create"
    payload = json.dumps({
        "engine": engine,
        "formulae": formula,
        "sgs": sg,
    }).encode()

    try:
        req = urllib.request.Request(
            create_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            report.task_id = result.get("task_id")
    except Exception as e:
        report.status = "failed"
        report.error = f"Absolidix API error: {e}"
        return report

    status_url = f"{absolidix_url}/calculations/status"
    start_time = time.time()

    while True:
        time.sleep(30)
        elapsed = time.time() - start_time

        try:
            payload = json.dumps({"task_id": report.task_id}).encode()
            req = urllib.request.Request(
                status_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
        except Exception as e:
            report.status = "failed"
            report.error = f"Status poll error: {e}"
            break

        state = result.get("status")
        if state in ("done", "error", "failed"):
            report.wall_time_s = elapsed
            if state == "done":
                report.status = "finished"
                report.total_energy_ev = result.get("energy")
                report.scf_cycles = result.get("scf_cycles", [])
                report.phonon_modes_gamma = result.get("phonon_modes_gamma", [])
                report.elastic_constants = result.get("elastic_constants")
            else:
                report.status = "failed"
                report.error = result.get("error", "unknown")
            break

        if elapsed > timeout:
            report.status = "timeout"
            report.wall_time_s = elapsed
            report.error = f"Timeout after {timeout}s"
            break

    return report


if __name__ == "__main__":
    sys.exit(main())