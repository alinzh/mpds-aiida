"""Benchmark report data model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BenchmarkReport:
    """Structured report capturing all data needed for engine comparison."""

    formula: str
    sg: int
    engine: str
    engine_version: Optional[str] = None
    wall_time_s: Optional[float] = None
    scf_cycles: list[int] = field(default_factory=list)
    total_energy_ev: Optional[float] = None
    phonon_modes_gamma: list[float] = field(default_factory=list)
    elastic_constants: Optional[dict] = None
    status: str = "pending"
    error: Optional[str] = None
    task_id: Optional[int] = None
    workchain_pk: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "BenchmarkReport":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, s: str) -> "BenchmarkReport":
        return cls.from_dict(json.loads(s))