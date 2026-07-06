# Perovskite Benchmark Pipeline

Standardized benchmark workflow for perovskite crystal structures using CRYSTAL (pcrystal) and FLEUR engines.

## Pipeline overview

```
MPDS API (structure retrieval)
  → AiiDA MPDSStructureWorkChain (geometry opt → phonons → elastic constants)
    → yascheduler (dispatch to remote compute node)
      → remote execution (Pcrystal / fleur_MPI)
        → results parsed back into AiiDA
          → BenchmarkReport JSON
```

## Prerequisites

1. **Environment variables**:
   ```bash
   export MPDS_KEY=<your MPDS API key>
   export YASCHEDULER_CONF_PATH=/path/to/yascheduler.conf
   ```
   `HOME` must also be set (for AiiDA to find `~/.aiida/` config and templates).

2. **AiiDA profile**: a configured `default` profile with:
   - Computer `yascheduler` (SSH transport, yascheduler scheduler)
   - Codes `Pcrystal@yascheduler` and `fleur@yascheduler`
   - Basis set family `MPDSBSL_NEUTRAL_6TH` uploaded
   - Calc templates installed at `~/.aiida/mpds_aiida/`
   - AiiDA daemon running (`verdi daemon start`)

3. **yascheduler**: daemon running, at least one compute node registered with `Pcrystal` and `fleur_MPI` engines deployed.

4. **Remote compute node**: `inpgen` binary on PATH (for FLEUR benchmarks).

## Usage

### Single benchmark

```bash
mpds-benchmark SrTiO3/221 --engine pcrystal --output report.json
```

### Engine comparison

```bash
mpds-benchmark MgO/225 --engine both --output report.json
```

### Multiple phases

```bash
mpds-benchmark MgO/225 SrTiO3/221 LaMnO3/167 --engine pcrystal --output reports.json
```

### Custom template

```bash
mpds-benchmark SrTiO3/221 --engine pcrystal --template custom.yml
```

### Via absolidix backend API

```bash
mpds-benchmark SrTiO3/221 --absolidix-url http://localhost:7050
```

## CLI options

| Option | Default | Description |
|---|---|---|
| `phases` | (required) | One or more `formula/sg` identifiers |
| `--engine` | `pcrystal` | Engine: `pcrystal`, `fleur`, or `both` |
| `--template` | engine-specific | Override benchmark template YAML |
| `--output`, `-o` | stdout | Output JSON file path |
| `--timeout` | `7200` | Timeout per benchmark in seconds |
| `--absolidix-url` | none | Absolidix backend URL for API-mode |

## Report JSON schema

```json
[
  {
    "formula": "SrTiO3",
    "sg": 221,
    "engine": "pcrystal",
    "engine_version": "23 1.0.1",
    "wall_time_s": 2530.0,
    "scf_cycles": [11, 8, 5, 5, 7],
    "total_energy_ev": -30086.09,
    "phonon_modes_gamma": [0.0, 0.0, 0.0, 143.6, 143.6, 143.6, 252.8, 252.8, 252.8, 264.2, 264.2, 264.2, 574.9, 574.9, 574.9],
    "elastic_constants": {
      "bulk_modulus": 204.14,
      "shear_modulus": 133.44,
      "young_modulus": 328.69,
      "poisson_ratio": 0.232
    },
    "status": "finished",
    "error": null,
    "task_id": null,
    "workchain_pk": 217,
    "timestamp": "2026-07-05T10:38:28+00:00"
  }
]
```

### Field descriptions

| Field | Type | Description |
|---|---|---|
| `formula` | string | Chemical formula (e.g. `SrTiO3`) |
| `sg` | int | Space group number |
| `engine` | string | Engine used (`pcrystal` or `fleur`) |
| `engine_version` | string | Engine version string from output |
| `wall_time_s` | float | Total wall time in seconds |
| `scf_cycles` | list[int] | Number of SCF cycles per calculation step |
| `total_energy_ev` | float | Total energy in eV from geometry optimization |
| `phonon_modes_gamma` | list[float] | Phonon frequencies at Gamma point (cm⁻¹) |
| `elastic_constants` | dict | Bulk/shear/Young moduli (GPa) + Poisson ratio |
| `status` | string | `finished`, `failed`, `timeout`, `submitted`, `running` |
| `error` | string\|null | Error message if failed |
| `task_id` | int\|null | yascheduler task ID (if available) |
| `workchain_pk` | int\|null | AiiDA WorkChain node PK |
| `timestamp` | string | ISO timestamp of report creation |

## Interpreting results

- **Wall time**: includes all AiiDA overhead (MPDS query, workchain scheduling, yascheduler dispatch, remote execution, result retrieval). For engine comparison, run both on the same formula/sg.
- **SCF cycles**: the list shows cycles per calculation step (optimise → phonons → elastic). More cycles = slower convergence.
- **Phonon modes at Gamma**: 3 acoustic modes (should be ~0) + optical modes. The number depends on atoms in the primitive cell (3N total).
- **Elastic constants**: bulk/shear/Young moduli in GPa. Compare against experimental or DFT reference values.

## Benchmark templates

Two version-controlled templates pin the calculation settings:

- `benchmark_pcrystal.yml`: PBE0 hybrid, SHRINK 8 16, TOLDEE 9, basis family MPDSBSL_NEUTRAL_6TH
- `benchmark_fleur.yml`: PBE-GGA, kmax=2.5, 2×2×2 k-mesh, standard FLAPW MT radii

Override with `--template` to customize settings (e.g. for metallic perovskites).