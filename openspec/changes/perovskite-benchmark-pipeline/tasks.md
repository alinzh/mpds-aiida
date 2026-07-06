## 1. Package scaffolding

- [x] 1.1 Create `mpds_aiida/benchmark/__init__.py` with package metadata
- [x] 1.2 Create `mpds_aiida/benchmark/report.py` with the `BenchmarkReport` dataclass (fields: formula, sg, engine, engine_version, wall_time_s, scf_cycles, total_energy_ev, phonon_modes_gamma, elastic_constants, status, error, task_id, workchain_pk, timestamp) and `to_json()`/`from_json()` methods
- [x] 1.3 Register `mpds-benchmark` CLI entry point in `pyproject.toml` under `[project.scripts]`

## 2. Benchmark templates

- [x] 2.1 Create `mpds_aiida/calc_templates/benchmark_pcrystal.yml` pinning PBE0, SHRINK 8 16, TOLDEE 9, basis_family MPDSBSL_NEUTRAL_6TH, codes Pcrystal@yascheduler
- [x] 2.2 Create `mpds_aiida/calc_templates/benchmark_fleur.yml` pinning PBE-GGA, kmax=2.5, 2×2×2 k-mesh, MT radii Sr=2.5/Ti=2.0/O=1.5, codes fleur@yascheduler

## 3. Pipeline core

- [x] 3.1 Implement `mpds_aiida/benchmark/pipeline.py` with `run_benchmark(formula, sg, engine, template, timeout)` function: validates env vars (MPDS_KEY, YASCHEDULER_CONF_PATH), loads template, submits `MPDSStructureWorkChain` via `aiida.engine.submit`, polls process state every 30s until terminal
- [x] 3.2 Implement result extraction: on `Finished [0]`, collect `output_parameters__optimise/phonons/elastic_constants` from the workchain outputs and populate a `BenchmarkReport`; on failure, capture exit code + last log message
- [x] 3.3 Implement wall-time measurement from workchain `ctime`/`mtime` and yascheduler `task_id` lookup via `yastatus`
- [x] 3.4 Implement `--engine both` mode: run pcrystal and fleur sequentially, return a list of reports, and print a comparison table to stdout

## 4. CLI

- [x] 4.1 Implement `mpds_aiida/benchmark/cli.py` with `main()` argparse: positional `phases` (one or more `formula/sg`), `--engine` (pcrystal|fleur|both, default pcrystal), `--template` (optional override), `--output` (JSON path, default stdout), `--timeout` (default 7200), `--absolidix-url` (optional)
- [x] 4.2 Add `--absolidix-url` mode: POST to `/calculations/create` and poll `/calculations/status` instead of AiiDA direct submit
- [x] 4.3 Add environment validation at CLI startup: check `MPDS_KEY` and `YASCHEDULER_CONF_PATH`, fail fast with exit code 3 if missing

## 5. Documentation

- [x] 5.1 Create `scripts/README_benchmark.md` documenting: prerequisites (env vars, AiiDA profile, yascheduler daemon, remote engines), usage examples (`mpds-benchmark SrTiO3/221`, `mpds-benchmark MgO/225 --engine both`), report JSON schema, and interpretation of results
- [x] 5.2 Add a docstring to `mpds_aiida/benchmark/__init__.py` summarizing the pipeline and linking to the README

## 6. Testing

- [x] 6.1 Add `mpds_aiida/tests/test_benchmark_report.py` testing `BenchmarkReport` serialization/deserialization (unit test, no external deps)
- [x] 6.2 Add `mpds_aiida/tests/test_benchmark_cli.py` testing CLI arg parsing and env-var validation with mocked `MPDS_KEY`/`YASCHEDULER_CONF_PATH` (unit test)
- [x] 6.3 Run existing test suite to verify no regressions: `pytest mpds_aiida/tests/ -x`