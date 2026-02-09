"""Shared solution dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


XKey = Tuple[int, int, int, int]  # (a, i, j, k)
YIKey = Tuple[int, int, int, int]  # (t, i, j, a)
YSKey = Tuple[int, int]  # (t, j)


@dataclass
class SolvedValues:
    mode: str
    objective: float
    x_aijk: Dict[XKey, float]
    y_tija: Dict[YIKey, float]
    y_tj: Dict[YSKey, float]
    status: str
    solver_time: Optional[float] = None
    mip_gap: Optional[float] = None
    solution_bound: Optional[float] = None
