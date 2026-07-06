## Why

The perovskite benchmark workflow currently exists as ad-hoc scripts and manual steps spread across multiple projects (`/data/perovskites/fetch_perovskites.py`, `/data/mpds-aiida/scripts/aiida_submit_phase.py`, the yascheduler config, and the absolidix backend). There is no single, documented, reusable pipeline that takes a perovskite composition from MPDS, runs a standardized CRYSTAL/FLEUR benchmark via AiiDA+yascheduler on a remote compute node, and reports comparable performance results. This makes it hard to reproduce benchmarks, compare engines systematically, and onboard new perovskite studies.

## What Changes

- Add a standardized `perovskite_benchmark` Python package under `mpds_aiida` that encapsulates the full pipeline: MPDS query → structure retrieval → AiiDA workchain submission → yascheduler dispatch → remote execution → result collection → performance report.
- Add a CLI entry point `mpds-benchmark` that accepts a formula/spacegroup (or a list) and runs the benchmark pipeline end-to-end, writing a structured JSON report.
- Add configurable benchmark templates for pcrystal (PBE0 phonon+elastic) and fleur (PBE SCF) so the two engines can be compared on the same system with documented, reproducible settings.
- Add a `BenchmarkReport` data class that captures wall time, SCF cycles, energy, phonon modes, elastic constants, and engine metadata — enabling direct apples-to-apples comparison.
- Add documentation (`scripts/README_benchmark.md`) describing how to run benchmarks, required environment variables, and interpretation of results.
- Add integration with the absolidix backend's `/calculations/supported` endpoint so benchmarks can optionally be triggered through the absolidix API rather than only via CLI.

## Capabilities

### New Capabilities

- `perovskite-benchmark`: End-to-end benchmark pipeline for perovskite crystal structures, covering MPDS retrieval, AiiDA workflow submission, yascheduler dispatch, remote execution, and structured performance reporting for pcrystal and fleur engines.

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- **New code**: `mpds_aiida/benchmark/` package (pipeline orchestrator, report model, CLI), `mpds_aiida/calc_templates/benchmark_*.yml` templates.
- **Existing code**: no breaking changes; the new package imports from `mpds_aiida.workflows` and `mpds_aiida.common` but does not alter them.
- **Dependencies**: relies on the already-installed `mpds_client`, `aiida-core`, `yascheduler`, and `ase`. No new third-party deps.
- **Systems**: interacts with the running yascheduler daemon (via `Yascheduler` client), AiiDA daemon (via `verdi`/`submit`), and optionally the absolidix backend (HTTP).
- **Environment**: requires `MPDS_KEY`, `YASCHEDULER_CONF_PATH`, and `HOME` to be set (as already established in the current deployment).