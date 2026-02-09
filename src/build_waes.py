"""Build WAES MILP as server payload data for cuOpt self-hosted service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

from src.instance import InstanceData


XKey = Tuple[int, int, int, int]  # (a, i, j, k)
YIKey = Tuple[int, int, int, int]  # (t, i, j, a)
YSKey = Tuple[int, int]  # (t, j)
Bound = Union[float, str]


@dataclass
class WAESModel:
    """MILP payload + variable index maps."""

    # Variable data
    variable_names: List[str]
    variable_types: List[str]
    objective_coeffs: List[float]
    variable_lb: List[Bound]
    variable_ub: List[Bound]

    # Constraint matrix and bounds (CSR row format)
    csr_offsets: List[int]
    csr_indices: List[int]
    csr_values: List[float]
    constraint_lb: List[Bound]
    constraint_ub: List[Bound]

    # Maps from symbolic decision variable keys to flat variable index
    x_aijk: Dict[XKey, int]
    y_tija: Dict[YIKey, int]
    y_tj: Dict[YSKey, int]

    ws_mode: bool

    def to_server_payload(self, solver_config: Dict[str, object]) -> Dict[str, object]:
        """Create `/cuopt/request` LP/MILP JSON payload."""
        payload: Dict[str, object] = {
            "csr_constraint_matrix": {
                "offsets": self.csr_offsets,
                "indices": self.csr_indices,
                "values": self.csr_values,
            },
            "constraint_bounds": {
                "upper_bounds": self.constraint_ub,
                "lower_bounds": self.constraint_lb,
            },
            "objective_data": {
                "coefficients": self.objective_coeffs,
                "scalability_factor": 1.0,
                "offset": 0.0,
            },
            "variable_bounds": {
                "upper_bounds": self.variable_ub,
                "lower_bounds": self.variable_lb,
            },
            "maximize": False,
            "variable_names": self.variable_names,
            "variable_types": self.variable_types,
        }
        if solver_config:
            payload["solver_config"] = solver_config
        return payload


def _until_a1(instance: InstanceData, i_or_k: int, a: int, ws_mode: bool) -> int:
    v_a = 0 if ws_mode else int(instance.v[a])
    return min(i_or_k + v_a, instance.n)


def _until_a2(instance: InstanceData, i_or_k: int, a: int, ws_mode: bool) -> int:
    if ws_mode:
        # WS baseline: no postponement allowed.
        return i_or_k
    r_a = int(instance.r[a])
    if r_a <= 0:
        return i_or_k
    # Keep index bounds valid even when i_or_k > r_a.
    return max(i_or_k, min(r_a, instance.n))


def build_waes_model(instance: InstanceData, ws_mode: bool = False) -> WAESModel:
    """Build WAES model (or WS baseline when `ws_mode=True`) as sparse MILP data."""
    variable_names: List[str] = []
    variable_types: List[str] = []
    objective_coeffs: List[float] = []
    variable_lb: List[Bound] = []
    variable_ub: List[Bound] = []

    x_aijk: Dict[XKey, int] = {}
    y_tija: Dict[YIKey, int] = {}
    y_tj: Dict[YSKey, int] = {}

    def add_var(name: str, obj: float, lb: Bound, ub: Bound, vtype: str) -> int:
        idx = len(variable_names)
        variable_names.append(name)
        objective_coeffs.append(float(obj))
        variable_lb.append(lb)
        variable_ub.append(ub)
        variable_types.append(vtype)
        return idx

    # Eq. (11), p. 12: integer variable creation.
    for a in instance.A:
        for i in instance.N:
            for j in instance.M:
                for k in instance.N:
                    key = (a, i, j, k)
                    x_aijk[key] = add_var(
                        name=f"x_a{a}_i{i}_j{j}_k{k}",
                        obj=0.0,
                        lb=0.0,
                        ub=float(instance.q),
                        vtype="I",
                    )

    for t in instance.T:
        for i in instance.N:
            for j in instance.M:
                for a in instance.A:
                    key = (t, i, j, a)
                    y_tija[key] = add_var(
                        name=f"y_t{t}_i{i}_j{j}_a{a}",
                        obj=0.0,
                        lb=0.0,
                        ub=float(instance.q),
                        vtype="I",
                    )

    for t in instance.T:
        for j in instance.M:
            key = (t, j)
            y_tj[key] = add_var(
                name=f"y_t{t}_j{j}",
                # Eq. (1), p. 11: minimize workforce cost.
                obj=instance.c[t] * instance.shift_cost_multiplier[j],
                lb=0.0,
                ub=float(instance.q),
                vtype="I",
            )

    csr_offsets: List[int] = [0]
    csr_indices: List[int] = []
    csr_values: List[float] = []
    constraint_lb: List[Bound] = []
    constraint_ub: List[Bound] = []

    def add_row(coeffs: Dict[int, float], lb: Bound, ub: Bound) -> None:
        for var_idx, coeff in sorted(coeffs.items()):
            if abs(coeff) <= 1e-12:
                continue
            csr_indices.append(var_idx)
            csr_values.append(float(coeff))
        csr_offsets.append(len(csr_indices))
        constraint_lb.append(lb)
        constraint_ub.append(ub)

    set_BA1 = set(instance.B) & set(instance.A1)
    set_BA2 = set(instance.B) & set(instance.A2)
    set_CA1 = set(instance.C) & set(instance.A1)
    set_CA2 = set(instance.C) & set(instance.A2)

    # Eq. (2), p. 11: independent A1 demand is fully met in allowed window.
    for i in instance.N:
        for a in sorted(set_BA1):
            until = _until_a1(instance, i, a, ws_mode)
            row: Dict[int, float] = {}
            for j in instance.M:
                for k in range(i, until + 1):
                    idx = x_aijk[(a, i, j, k)]
                    row[idx] = row.get(idx, 0.0) + float(instance.b[(k, j)])
            rhs = float(instance.d[(a, i)])
            add_row(row, lb=rhs, ub=rhs)

    # Eq. (3), p. 11: independent A2 demand is fully met by r_a.
    for i in instance.N:
        for a in sorted(set_BA2):
            until = _until_a2(instance, i, a, ws_mode)
            row = {}
            for j in instance.M:
                for k in range(i, until + 1):
                    idx = x_aijk[(a, i, j, k)]
                    row[idx] = row.get(idx, 0.0) + float(instance.b[(k, j)])
            rhs = float(instance.d[(a, i)])
            add_row(row, lb=rhs, ub=rhs)

    # Eq. (4), p. 11: dependent A1 demand lower-bounded by dependency expression.
    for k in instance.N:
        for a in sorted(set_CA1):
            until = _until_a1(instance, k, a, ws_mode)
            row = {}
            for j in instance.M:
                for kp in range(k, until + 1):
                    idx = x_aijk[(a, k, j, kp)]
                    row[idx] = row.get(idx, 0.0) + float(instance.b[(kp, j)])

            for a_parent in instance.Ga[a]:
                coeff = float(instance.s[(a, a_parent)])
                for j in instance.M:
                    for i in instance.N:
                        idx = x_aijk[(a_parent, i, j, k)]
                        row[idx] = row.get(idx, 0.0) - coeff

            add_row(row, lb=0.0, ub="inf")

    # Eq. (5), p. 11: dependent A2 demand lower-bounded by dependency expression.
    for k in instance.N:
        for a in sorted(set_CA2):
            until = _until_a2(instance, k, a, ws_mode)
            row = {}
            for j in instance.M:
                for kp in range(k, until + 1):
                    idx = x_aijk[(a, k, j, kp)]
                    row[idx] = row.get(idx, 0.0) + float(instance.b[(kp, j)])

            for a_parent in instance.Ga[a]:
                coeff = float(instance.s[(a, a_parent)])
                for j in instance.M:
                    for i in instance.N:
                        idx = x_aijk[(a_parent, i, j, k)]
                        row[idx] = row.get(idx, 0.0) - coeff

            add_row(row, lb=0.0, ub="inf")

    # Eq. (6), p. 11: interval-k execution cannot exceed interval-k activity staffing.
    for k in instance.N:
        for j in instance.M:
            for a in instance.A:
                row = {}
                for i in range(1, k + 1):
                    idx = x_aijk[(a, i, j, k)]
                    row[idx] = row.get(idx, 0.0) + 1.0
                for t in instance.Ta[a]:
                    idx = y_tija[(t, k, j, a)]
                    row[idx] = row.get(idx, 0.0) - 1.0
                add_row(row, lb="ninf", ub=0.0)

    # Eq. (7), p. 11: per-profile interval assignments are bounded by shift assignment.
    for i in instance.N:
        for j in instance.M:
            for t in instance.T:
                row = {}
                for a in instance.Ht[t]:
                    idx = y_tija[(t, i, j, a)]
                    row[idx] = row.get(idx, 0.0) + 1.0
                idx_shift = y_tj[(t, j)]
                row[idx_shift] = row.get(idx_shift, 0.0) - 1.0
                add_row(row, lb="ninf", ub=0.0)

    # Eq. (8), p. 11: active workers per interval are capped by q.
    for i in instance.N:
        row = {}
        for t in instance.T:
            for j in instance.M:
                for a in instance.A:
                    idx = y_tija[(t, i, j, a)]
                    row[idx] = row.get(idx, 0.0) + 1.0
        add_row(row, lb="ninf", ub=float(instance.q))

    # Eq. (9), p. 11: full-time break-window load enforces p-interval break.
    for t in instance.T:
        for j in instance.M1:
            row = {}
            for i in instance.Oj[j]:
                for a in instance.Ht[t]:
                    idx = y_tija[(t, i, j, a)]
                    row[idx] = row.get(idx, 0.0) + 1.0
            idx_shift = y_tj[(t, j)]
            row[idx_shift] = row.get(idx_shift, 0.0) - float(instance.f - instance.p)
            add_row(row, lb="ninf", ub=0.0)

    # Eq. (10), p. 11: part-time share cap.
    row = {}
    for j in instance.M2:
        for t in instance.T:
            idx = y_tj[(t, j)]
            row[idx] = row.get(idx, 0.0) + 1.0
    for j in instance.M:
        for t in instance.T:
            idx = y_tj[(t, j)]
            row[idx] = row.get(idx, 0.0) - float(instance.w)
    add_row(row, lb="ninf", ub=0.0)

    return WAESModel(
        variable_names=variable_names,
        variable_types=variable_types,
        objective_coeffs=objective_coeffs,
        variable_lb=variable_lb,
        variable_ub=variable_ub,
        csr_offsets=csr_offsets,
        csr_indices=csr_indices,
        csr_values=csr_values,
        constraint_lb=constraint_lb,
        constraint_ub=constraint_ub,
        x_aijk=x_aijk,
        y_tija=y_tija,
        y_tj=y_tj,
        ws_mode=ws_mode,
    )
