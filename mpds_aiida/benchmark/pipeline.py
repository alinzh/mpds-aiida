"""Benchmark pipeline core: MPDS -> AiiDA -> yascheduler -> results."""

from __future__ import annotations

import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .report import BenchmarkReport


TEMPLATE_DIR = Path(os.getenv("HOME") or "/tmp") / ".aiida" / "mpds_aiida"

ENGINE_TEMPLATES = {
    "pcrystal": "benchmark_pcrystal.yml",
    "fleur": "benchmark_fleur.yml",
}


def validate_env() -> None:
    """Validate required environment variables. Exit with code 3 if missing."""
    missing = []
    if not os.getenv("MPDS_KEY"):
        missing.append("MPDS_KEY")
    if not os.getenv("YASCHEDULER_CONF_PATH"):
        missing.append("YASCHEDULER_CONF_PATH")
    if missing:
        for var in missing:
            print(f"ERROR: {var} environment variable is not set", file=sys.stderr)
        sys.exit(3)


def load_template(engine: str, template_override: Optional[str] = None) -> dict:
    """Load a benchmark YAML template."""
    import yaml

    template_name = template_override or ENGINE_TEMPLATES.get(engine)
    if not template_name:
        raise ValueError(f"Unknown engine: {engine}")

    template_loc = TEMPLATE_DIR / template_name
    if not template_loc.exists():
        template_loc = Path(template_name)

    assert template_loc.exists(), f"Template not found: {template_loc}"

    with open(template_loc) as f:
        return yaml.load(f.read(), Loader=yaml.SafeLoader)


def run_benchmark(
    formula: str,
    sg: int,
    engine: str = "pcrystal",
    template_override: Optional[str] = None,
    timeout: int = 7200,
) -> BenchmarkReport:
    """
    Run a single benchmark for the given formula/sg with the specified engine.

    Returns a BenchmarkReport.
    """
    validate_env()

    from aiida import load_profile
    from aiida.plugins import DataFactory
    from aiida.engine import submit
    from aiida.orm import load_node
    from mpds_aiida.workflows.crystal_mpds import MPDSStructureWorkChain

    load_profile()

    report = BenchmarkReport(formula=formula, sg=sg, engine=engine, status="running")

    template = load_template(engine, template_override)

    inputs = MPDSStructureWorkChain.get_builder()
    inputs.metadata = dict(label=f"{formula}/{sg}")
    inputs.mpds_query = DataFactory("dict")(dict={"formulae": formula, "sgs": sg})

    try:
        wc = submit(MPDSStructureWorkChain, **inputs)
    except Exception as e:
        report.status = "failed"
        report.error = f"Submit failed: {e}"
        return report

    report.workchain_pk = wc.pk
    report.status = "submitted"
    print(f"Submitted WorkChain {wc.pk} for {formula}/{sg} ({engine})")

    start_time = time.time()
    deadline = start_time + timeout

    while True:
        time.sleep(30)
        elapsed = time.time() - start_time

        node = load_node(wc.pk)
        state = node.process_state

        if state is not None and state.is_terminated:
            report.wall_time_s = elapsed
            if node.exit_status == 0:
                report.status = "finished"
                _extract_results(node, report)
            else:
                report.status = "failed"
                report.error = f"WorkChain exited with code {node.exit_status}"
                _extract_last_log(node, report)
            break

        if time.time() > deadline:
            report.status = "timeout"
            report.wall_time_s = elapsed
            report.error = f"Workchain did not terminate within {timeout}s"
            break

        print(f"  [{elapsed:.0f}s] WorkChain {wc.pk} state: {state}")

    return report


def _extract_results(node, report: BenchmarkReport) -> None:
    """Extract results from a finished workchain into the report."""
    try:
        opt = node.base.links.get_outgoing().get_node_by_label(
            "output_parameters__optimise"
        )
        d = opt.get_dict()
        report.total_energy_ev = d.get("energy")
        report.scf_cycles = d.get("scf_cycles", [])
        report.engine_version = d.get("creator_version")
    except Exception:
        pass

    try:
        ph = node.base.links.get_outgoing().get_node_by_label(
            "output_parameters__phonons"
        )
        d = ph.get_dict()
        modes = d.get("phonons", {})
        freqs = modes.get("modes_freqs", {})
        gamma = freqs.get("0 0 0", [])
        report.phonon_modes_gamma = [float(x) for x in gamma]
    except Exception:
        pass

    try:
        el = node.base.links.get_outgoing().get_node_by_label(
            "output_parameters__elastic_constants"
        )
        d = el.get_dict()
        report.elastic_constants = d.get("elastic")
    except Exception:
        pass


def _extract_last_log(node, report: BenchmarkReport) -> None:
    """Extract the last log message from a failed workchain."""
    try:
        from aiida.orm import Log

        logs = Log.objects.find(attrs={"dbnode_id": node.pk})
        if logs:
            report.error = logs[-1].message[:500]
    except Exception:
        pass


def run_benchmark_both(
    formula: str,
    sg: int,
    template_override: Optional[str] = None,
    timeout: int = 7200,
) -> list[BenchmarkReport]:
    """Run benchmark with both pcrystal and fleur engines, return reports list."""
    reports = []
    for engine in ("pcrystal", "fleur"):
        print(f"\n=== Running {engine} benchmark for {formula}/{sg} ===")
        report = run_benchmark(formula, sg, engine, template_override, timeout)
        reports.append(report)

    print_comparison_table(reports)
    return reports


def print_comparison_table(reports: list[BenchmarkReport]) -> None:
    """Print a side-by-side comparison table to stdout."""
    if not reports:
        return

    print("\n" + "=" * 70)
    print("Benchmark comparison")
    print("=" * 70)
    header = f"{'Engine':<12} {'Status':<10} {'Wall (s)':<10} {'Energy (eV)':<16} {'Bulk (GPa)':<10}"
    print(header)
    print("-" * 70)
    for r in reports:
        energy = f"{r.total_energy_ev:.2f}" if r.total_energy_ev else "-"
        bulk = (
            f"{r.elastic_constants['bulk_modulus']:.1f}"
            if r.elastic_constants and "bulk_modulus" in r.elastic_constants
            else "-"
        )
        wall = f"{r.wall_time_s:.0f}" if r.wall_time_s else "-"
        print(f"{r.engine:<12} {r.status:<10} {wall:<10} {energy:<16} {bulk:<10}")
    print("=" * 70)