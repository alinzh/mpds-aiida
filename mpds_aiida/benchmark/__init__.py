"""
Perovskite benchmark pipeline.

Encapsulates the full workflow: MPDS retrieval -> AiiDA workchain submission ->
yascheduler dispatch -> remote execution -> structured performance reporting
for pcrystal (CRYSTAL) and fleur engines.

Usage:
    mpds-benchmark SrTiO3/221 --engine pcrystal --output report.json

See scripts/README_benchmark.md for full documentation.
"""

__version__ = "0.1.0"