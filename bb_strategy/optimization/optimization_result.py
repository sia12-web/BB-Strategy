"""OptimizationResult dataclass with JSON serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class OptimizationResult:
    """Aggregated output from a single pair's optimization run."""

    pair: str
    best_params: dict[str, Any]
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    out_of_sample_win_rate: float
    out_of_sample_profit_factor: float
    total_combinations_tested: int
    in_sample_trades: int
    out_of_sample_trades: int
    passed_validation: bool
    rejection_reason: Optional[str] = None

    def to_dict(self) -> dict:
        """Flat dict safe for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, d: dict) -> "OptimizationResult":
        return cls(**d)

    @classmethod
    def from_json(cls, s: str) -> "OptimizationResult":
        return cls.from_dict(json.loads(s))
