## ADDED Requirements

### Requirement: Benchmark pipeline entry point

The `mpds-benchmark` CLI shall accept one or more perovskite identifiers in `formula/sg` format (e.g. `SrTiO3/221`), run the full benchmark pipeline for each, and emit a structured JSON report.

#### Scenario: Single perovskite benchmark
- **WHEN** the user runs `mpds-benchmark SrTiO3/221 --engine pcrystal --output report.json`
- **THEN** the pipeline retrieves the SrTiO3 structure from MPDS, submits an AiiDA `MPDSStructureWorkChain` with the pcrystal benchmark template, waits for completion, and writes a `BenchmarkReport` JSON to `report.json` containing wall time, SCF cycles, total energy, phonon modes, and elastic constants.

#### Scenario: Engine comparison
- **WHEN** the user runs `mpds-benchmark MgO/225 --engine both --output report.json`
- **THEN** the pipeline runs the benchmark with both pcrystal and fleur engines, produces two `BenchmarkReport` entries in the JSON array, and prints a comparison table to stdout showing wall time and key results side by side.

#### Scenario: Default engine
- **WHEN** the user runs `mpds-benchmark MgO/225` without `--engine`
- **THEN** the pipeline defaults to `pcrystal`.

### Requirement: MPDS structure retrieval

The pipeline shall query the MPDS API for the requested `formula/sg` pair and retrieve the non-disordered crystalline structure with the smallest number of atoms (matching the existing `MPDSStructureWorkChain.get_geometry` behavior).

#### Scenario: Structure found
- **WHEN** MPDS returns one or more structures for `MgO/225`
- **THEN** the pipeline selects the one with the minimal atom count and median cell vectors, and passes it to the AiiDA workchain.

#### Scenario: No structure found
- **WHEN** MPDS returns no hits for the given `formula/sg`
- **THEN** the pipeline writes a report with `status: "no_structure"` and `error: "MPDS returned no hits"` and exits with code 1.

### Requirement: Benchmark templates

The pipeline shall use version-controlled YAML templates that pin the calculation settings for reproducible benchmarks.

#### Scenario: pcrystal benchmark template
- **WHEN** the engine is `pcrystal`
- **THEN** the pipeline loads `calc_templates/benchmark_pcrystal.yml` which configures PBE0 hybrid functional, SHRINK 8 16, TOLDEE 9, and the MPDSBSL_NEUTRAL_6TH basis family.

#### Scenario: fleur benchmark template
- **WHEN** the engine is `fleur`
- **THEN** the pipeline loads `calc_templates/benchmark_fleur.yml` which configures PBE-GGA, kmax=2.5, 2×2×2 k-mesh, and the standard FLAPW MT radii for Sr/Ti/O.

#### Scenario: Custom template override
- **WHEN** the user passes `--template custom.yml`
- **THEN** the pipeline loads the specified template instead of the default benchmark template.

### Requirement: AiiDA workchain submission and monitoring

The pipeline shall submit the `MPDSStructureWorkChain` via `aiida.engine.submit` and poll the process state until termination.

#### Scenario: Successful workchain
- **WHEN** the workchain reaches `Finished [0]`
- **THEN** the pipeline collects the `output_parameters__optimise`, `output_parameters__phonons`, and `output_parameters__elastic_constants` outputs and populates the report.

#### Scenario: Failed workchain
- **WHEN** the workchain reaches `Excepted` or `Finished` with non-zero exit code
- **THEN** the pipeline populates `status: "failed"`, captures the exit code and last log message into `error`, and exits with code 1.

#### Scenario: Workchain timeout
- **WHEN** the workchain has not terminated within `--timeout` seconds (default 7200)
- **THEN** the pipeline marks the report as `status: "timeout"` and exits with code 2.

### Requirement: BenchmarkReport data model

The report shall be a structured JSON object capturing all data needed for engine comparison.

#### Scenario: Report fields
- **WHEN** a benchmark completes successfully
- **THEN** the report JSON contains: `formula`, `sg`, `engine`, `engine_version`, `wall_time_s`, `scf_cycles` (list), `total_energy_ev`, `phonon_modes_gamma` (list of floats in cm⁻¹), `elastic_constants` (dict with `bulk_modulus`, `shear_modulus`, `young_modulus`, `poisson_ratio`), `status`, `task_id` (yascheduler), `workchain_pk` (AiiDA), `timestamp`.

#### Scenario: Multiple reports
- **WHEN** multiple perovskites or engines are benchmarked
- **THEN** the output JSON is an array of `BenchmarkReport` objects.

### Requirement: Absolidix backend integration (optional)

The pipeline may optionally trigger benchmarks through the absolidix backend API instead of directly via AiiDA.

#### Scenario: Absolidix API mode
- **WHEN** the user passes `--absolidix-url http://localhost:7050`
- **THEN** the pipeline submits the calculation via the backend's `/calculations/create` endpoint and polls `/calculations/status` instead of using AiiDA `submit` directly.

#### Scenario: No absolidix
- **WHEN** `--absolidix-url` is not provided
- **THEN** the pipeline uses AiiDA directly (default behavior).

### Requirement: Environment validation

The pipeline shall validate required environment variables before starting and fail fast with a clear message if any are missing.

#### Scenario: Missing MPDS_KEY
- **WHEN** `MPDS_KEY` is not set
- **THEN** the pipeline prints `ERROR: MPDS_KEY environment variable is not set` and exits with code 3.

#### Scenario: Missing YASCHEDULER_CONF_PATH
- **WHEN** `YASCHEDULER_CONF_PATH` is not set
- **THEN** the pipeline prints `ERROR: YASCHEDULER_CONF_PATH environment variable is not set` and exits with code 3.