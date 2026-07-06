## Context

The current perovskite benchmark workflow was assembled manually during this session across four disconnected pieces:

1. **MPDS retrieval** (`/data/perovskites/fetch_perovskites.py`) — queries the MPDS API for perovskite structures by arity+lattice criteria, parses formulae, and compares against the `dft.mpds.io` list.
2. **AiiDA submission** (`/data/mpds-aiida/scripts/aiida_submit_phase.py`) — submits `MPDSStructureWorkChain` for a given `formula/sg` pair, which runs geometry optimization → phonons → elastic constants via CRYSTAL.
3. **yascheduler dispatch** (`/data/perovskites/yac/yascheduler.conf` + daemon) — receives AiiDA jobs via `yasubmit` and executes them on remote host `167.233.228.79` with `Pcrystal`/`fleur_MPI`.
4. **Performance measurement** — done manually by timing `mpirun` runs and reading CRYSTAL/FLEUR OUTPUT files.

There is no single entry point, no structured output, and no engine comparison report. The FLEUR benchmark input was created ad-hoc from scratch with no reusable template.

## Goals / Non-Goals

**Goals:**
- One-command benchmark: `mpds-benchmark SrTiO3/221` runs the full pipeline and emits a JSON report.
- Support both pcrystal and fleur engines with documented, version-controlled benchmark templates.
- Structured `BenchmarkReport` output capturing wall time, SCF cycles, energies, phonon modes, elastic constants, and engine version — suitable for programmatic comparison.
- Reusable across any perovskite composition available in MPDS.
- Optional absolidix-backend integration (trigger via HTTP API instead of CLI).

**Non-Goals:**
- Replacing the existing `MPDSStructureWorkChain` — the benchmark pipeline wraps it, does not modify it.
- Auto-scaling compute nodes or cloud provisioning — relies on the existing yascheduler node pool.
- GUI/dashboard — the report is JSON for downstream tools (absolidix, notebooks, etc.).
- Re-implementing the FLEUR input generator — uses the existing `inpgen` binary on the remote.

## Decisions

### 1. Package location: `mpds_aiida/benchmark/`

The benchmark code lives inside the existing `mpds_aiida` package rather than a separate repo, because it depends on `mpds_aiida.workflows` and `mpds_aiida.common` and shares the same AiiDA/yascheduler environment. This avoids a circular dependency.

### 2. CLI entry point: `mpds-benchmark`

Registered in `pyproject.toml` under `[project.scripts]` as `mpds-benchmark = "mpds_aiida.benchmark.cli:main"`. Accepts positional `formula/sg` pairs (one or more), `--engine` flag (`pcrystal`|`fleur`|`both`), `--output` path for the JSON report, and `--absolidix-url` to optionally route through the backend API.

### 3. Benchmark templates: `calc_templates/benchmark_pcrystal.yml` and `calc_templates/benchmark_fleur.yml`

Two new YAML templates alongside the existing `nonmetallic.yml`/`metallic.yml`. They pin the benchmark settings (PBE0 + SHRINK 8 16 for pcrystal; PBE + kmax=2.5 + 2×2×2 k-mesh for fleur) so results are reproducible. The pipeline selects the template based on `--engine`.

### 4. Report model: `BenchmarkReport` (dataclass)

Fields: `formula`, `sg`, `engine`, `engine_version`, `wall_time_s`, `scf_cycles`, `total_energy_ev`, `phonon_modes_gamma`, `elastic_constants`, `status`, `error`, `task_id`, `workchain_pk`. Serialized to JSON. Multiple reports can be aggregated into a comparison table.

### 5. Pipeline orchestration: synchronous wrapper around `submit()`

The pipeline uses `aiida.engine.submit` to launch the `MPDSStructureWorkChain`, then polls `verdi process show` (via the AiiDA ORM `load_node`) until the workchain reaches a terminal state, collecting timing from `ctime`/`mtime`. This avoids needing a long-running async daemon and keeps the CLI simple.

### 6. FLEUR benchmark input: generated via `inpgen` on the remote

For FLEUR, the pipeline writes an `inp.txt` (inpgen input) with the standardized settings, runs `inpgen` on the remote node via SSH to produce `inp.xml`/`kpts.xml`/`sym.xml`, then submits through yascheduler. This mirrors how the manual benchmark was done.

## Risks / Trade-offs

- **Polling overhead**: the CLI polls AiiDA process state every ~30s. For long phonon calculations (~1h) this is negligible, but for many concurrent benchmarks it adds DB load. Acceptable for the benchmark use case (low concurrency).
- **FLEUR setup time**: FLEUR's FLAPW basis initialization for heavy elements (Sr) takes ~7 min even for a small cell. This is inherent to the engine, not the pipeline. The report captures wall time including setup so comparisons are fair.
- **Template rigidity**: pinned benchmark templates may not suit all perovskite chemistries (e.g., metallic perovskites need different CRYSTAL settings). The `--template` flag allows overriding with a custom YAML, defaulting to the benchmark templates.
- **Remote `inpgen` dependency**: FLEUR benchmark requires `inpgen` on the remote. If unavailable, the pipeline reports a clear error rather than failing silently.