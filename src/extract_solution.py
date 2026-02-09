"""Solution extraction and CSV writers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from src.instance import InstanceData
from src.solution_types import SolvedValues


def _positive(value: float, eps: float = 1e-9) -> bool:
    return value > eps


def build_schedule_frame(instance: InstanceData, solved: SolvedValues) -> pd.DataFrame:
    """Detailed assignment schedule by profile/shift/interval/activity."""
    import pandas as pd

    rows: List[Dict[str, float]] = []
    for (t, i, j, a), value in solved.y_tija.items():
        if not _positive(value):
            continue
        rows.append(
            {
                "mode": solved.mode,
                "profile": t,
                "interval": i,
                "shift": j,
                "activity": a,
                "workers": value,
            }
        )
    return pd.DataFrame(rows).sort_values(
        by=["interval", "shift", "profile", "activity"], ignore_index=True
    )


def build_staffing_frame(instance: InstanceData, solved: SolvedValues) -> pd.DataFrame:
    """Aggregate staffing by interval/activity."""
    import pandas as pd

    rows: List[Dict[str, float]] = []
    for i in instance.N:
        for a in instance.A:
            workers = sum(
                solved.y_tija[(t, i, j, a)]
                for t in instance.T
                for j in instance.M
            )
            rows.append(
                {
                    "mode": solved.mode,
                    "interval": i,
                    "activity": a,
                    "workers": workers,
                }
            )
    return pd.DataFrame(rows).sort_values(by=["interval", "activity"], ignore_index=True)


def build_flows_frame(instance: InstanceData, solved: SolvedValues) -> pd.DataFrame:
    """Demand-fulfillment flows from demand interval i to execution interval k."""
    import pandas as pd

    rows: List[Dict[str, float]] = []
    for a in instance.A:
        for i in instance.N:
            for k in instance.N:
                workers = sum(
                    solved.x_aijk[(a, i, j, k)] * instance.b[(k, j)]
                    for j in instance.M
                )
                if not _positive(workers):
                    continue
                rows.append(
                    {
                        "mode": solved.mode,
                        "activity": a,
                        "demand_interval": i,
                        "execution_interval": k,
                        "workers": workers,
                    }
                )
    return pd.DataFrame(rows).sort_values(
        by=["activity", "demand_interval", "execution_interval"], ignore_index=True
    )


def write_solution_csvs(instance: InstanceData, solved: SolvedValues, out_dir: Path) -> None:
    """Write required output CSVs to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    build_schedule_frame(instance, solved).to_csv(out_dir / "schedule.csv", index=False)
    build_staffing_frame(instance, solved).to_csv(
        out_dir / "staffing_by_interval_activity.csv", index=False
    )
    build_flows_frame(instance, solved).to_csv(
        out_dir / "demand_fulfillment_flows.csv", index=False
    )
