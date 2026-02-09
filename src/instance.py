"""Instance loading and validation for MASSP WAES/WS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict, Iterable, List, Mapping, Tuple


Index2 = Tuple[int, int]
Index4 = Tuple[int, int, int, int]


@dataclass(frozen=True)
class InstanceData:
    """Canonical in-memory representation of a MASSP instance."""

    name: str
    n: int
    N: Tuple[int, ...]
    M1: Tuple[int, ...]
    M2: Tuple[int, ...]
    M: Tuple[int, ...]
    A: Tuple[int, ...]
    B: Tuple[int, ...]
    C: Tuple[int, ...]
    A1: Tuple[int, ...]
    A2: Tuple[int, ...]
    T: Tuple[int, ...]
    Ga: Dict[int, Tuple[int, ...]]
    d: Dict[Index2, float]
    s: Dict[Index2, float]
    v: Dict[int, int]
    r: Dict[int, int]
    Ta: Dict[int, Tuple[int, ...]]
    Ht: Dict[int, Tuple[int, ...]]
    c: Dict[int, float]
    q: int
    p: int
    f: int
    Oj: Dict[int, Tuple[int, ...]]
    w: float
    b: Dict[Index2, int]
    shift_start: Dict[int, int]
    shift_length: Dict[int, int]
    shift_cost_multiplier: Dict[int, float]
    paper_expected_objective: Dict[str, float]
    paper_objective_tolerance: float


def _to_sorted_tuple(values: Iterable[int]) -> Tuple[int, ...]:
    return tuple(sorted(int(v) for v in values))


def _parse_nested_float(raw: Mapping[str, Mapping[str, object]]) -> Dict[Index2, float]:
    out: Dict[Index2, float] = {}
    for k1, inner in raw.items():
        for k2, value in inner.items():
            out[(int(k1), int(k2))] = float(value)
    return out


def _compute_b_matrix(
    N: Tuple[int, ...],
    M: Tuple[int, ...],
    shift_start: Dict[int, int],
    shift_length: Dict[int, int],
) -> Dict[Index2, int]:
    n = max(N)
    b: Dict[Index2, int] = {}
    for j in M:
        start = shift_start[j]
        length = shift_length[j]
        end = min(n, start + length - 1)
        for k in N:
            b[(k, j)] = 1 if start <= k <= end else 0
    return b


def _compute_break_windows(
    M1: Tuple[int, ...],
    shift_start: Dict[int, int],
    break_window_relative: Tuple[int, ...],
    N: Tuple[int, ...],
) -> Dict[int, Tuple[int, ...]]:
    n_set = set(N)
    Oj: Dict[int, Tuple[int, ...]] = {}
    for j in M1:
        start = shift_start[j]
        Oj[j] = tuple(
            start + rel - 1
            for rel in break_window_relative
            if (start + rel - 1) in n_set
        )
    return Oj


def load_instance(instance_path: str | Path) -> InstanceData:
    """Load an instance from `instance.json` or a direct json file path."""
    path = Path(instance_path)
    if path.is_dir():
        path = path / "instance.json"
    if not path.exists():
        raise FileNotFoundError(f"Instance file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    name = str(raw.get("name", path.stem))
    n = int(raw["n"])
    N = _to_sorted_tuple(raw.get("N", range(1, n + 1)))
    M1 = _to_sorted_tuple(raw["M1"])
    M2 = _to_sorted_tuple(raw["M2"])
    M = _to_sorted_tuple(list(M1) + list(M2))
    A = _to_sorted_tuple(raw["A"])
    B = _to_sorted_tuple(raw["B"])
    C = _to_sorted_tuple(raw["C"])
    A1 = _to_sorted_tuple(raw["A1"])
    A2 = _to_sorted_tuple(raw["A2"])
    T = _to_sorted_tuple(raw["T"])

    shift_start = {int(k): int(v) for k, v in raw["shift_start"].items()}
    shift_length = {int(k): int(v) for k, v in raw["shift_length"].items()}
    b = _compute_b_matrix(N, M, shift_start, shift_length)

    if "Oj" in raw:
        Oj = {int(k): tuple(int(x) for x in v) for k, v in raw["Oj"].items()}
    else:
        rel = tuple(int(x) for x in raw["break_window_relative"])
        Oj = _compute_break_windows(M1, shift_start, rel, N)

    if "shift_cost_multiplier" in raw:
        shift_cost_multiplier = {int(k): float(v) for k, v in raw["shift_cost_multiplier"].items()}
    else:
        part_time_factor = float(raw.get("part_time_cost_factor", 1.0))
        shift_cost_multiplier = {
            j: (part_time_factor if j in set(M2) else 1.0)
            for j in M
        }

    Ga = {
        int(a): tuple(int(x) for x in parents)
        for a, parents in raw.get("Ga", {}).items()
    }
    d = _parse_nested_float(raw["demand"])
    s = _parse_nested_float(raw.get("s", {}))
    v = {int(k): int(val) for k, val in raw["v"].items()}
    r = {int(k): int(val) for k, val in raw["r"].items()}
    Ta = {
        int(a): tuple(int(t) for t in profiles)
        for a, profiles in raw["Ta"].items()
    }
    Ht = {
        int(t): tuple(int(a) for a in acts)
        for t, acts in raw["Ht"].items()
    }
    c = {int(t): float(cost) for t, cost in raw["c"].items()}

    paper_expected_objective = {
        str(k).lower(): float(v)
        for k, v in raw.get("paper_expected_objective", {}).items()
    }
    paper_objective_tolerance = float(raw.get("paper_objective_tolerance", 1.0))

    instance = InstanceData(
        name=name,
        n=n,
        N=N,
        M1=M1,
        M2=M2,
        M=M,
        A=A,
        B=B,
        C=C,
        A1=A1,
        A2=A2,
        T=T,
        Ga=Ga,
        d=d,
        s=s,
        v=v,
        r=r,
        Ta=Ta,
        Ht=Ht,
        c=c,
        q=int(raw["q"]),
        p=int(raw["p"]),
        f=int(raw["f"]),
        Oj=Oj,
        w=float(raw["w"]),
        b=b,
        shift_start=shift_start,
        shift_length=shift_length,
        shift_cost_multiplier=shift_cost_multiplier,
        paper_expected_objective=paper_expected_objective,
        paper_objective_tolerance=paper_objective_tolerance,
    )
    validate_instance(instance)
    return instance


def validate_instance(instance: InstanceData) -> None:
    """Validate shape/index coverage and basic consistency."""
    errors: List[str] = []

    set_M1 = set(instance.M1)
    set_M2 = set(instance.M2)
    set_M = set(instance.M)
    set_A = set(instance.A)
    set_B = set(instance.B)
    set_C = set(instance.C)
    set_A1 = set(instance.A1)
    set_A2 = set(instance.A2)
    set_T = set(instance.T)
    set_N = set(instance.N)

    if set_M1 & set_M2:
        errors.append("M1 and M2 must be disjoint.")
    if set_M != (set_M1 | set_M2):
        errors.append("M must equal M1 union M2.")
    if set_B & set_C:
        errors.append("B and C must be disjoint.")
    if set_A != (set_B | set_C):
        errors.append("A must equal B union C.")
    if set_A1 & set_A2:
        errors.append("A1 and A2 must be disjoint.")
    if set_A != (set_A1 | set_A2):
        errors.append("A must equal A1 union A2.")
    if tuple(instance.N) != tuple(range(1, instance.n + 1)):
        errors.append("N must be exactly {1, ..., n} for this implementation.")

    for j in instance.M:
        if j not in instance.shift_start:
            errors.append(f"Missing shift_start for j={j}.")
        if j not in instance.shift_length:
            errors.append(f"Missing shift_length for j={j}.")
        if j not in instance.shift_cost_multiplier:
            errors.append(f"Missing shift_cost_multiplier for j={j}.")
        for k in instance.N:
            if (k, j) not in instance.b:
                errors.append(f"Missing b[(k={k}, j={j})].")
            elif instance.b[(k, j)] not in (0, 1):
                errors.append(f"b[(k={k}, j={j})] must be 0/1.")

    for a in instance.B:
        for i in instance.N:
            if (a, i) not in instance.d:
                errors.append(f"Missing demand d[(a={a}, i={i})] for independent activity.")

    for a in instance.C:
        if a not in instance.Ga:
            errors.append(f"Missing Ga for dependent activity a={a}.")
            continue
        for a_parent in instance.Ga[a]:
            if (a, a_parent) not in instance.s:
                errors.append(f"Missing s[(a={a}, a_parent={a_parent})].")

    for a in instance.A1:
        if a not in instance.v:
            errors.append(f"Missing v[a] for a={a} in A1.")
    for a in instance.A2:
        if a not in instance.r:
            errors.append(f"Missing r[a] for a={a} in A2.")

    for a in instance.A:
        if a not in instance.Ta or not instance.Ta[a]:
            errors.append(f"Missing/empty Ta[a] for a={a}.")
    for t in instance.T:
        if t not in instance.Ht or not instance.Ht[t]:
            errors.append(f"Missing/empty Ht[t] for t={t}.")
        if t not in instance.c:
            errors.append(f"Missing cost c[t] for t={t}.")

    for a in instance.A:
        for t in instance.Ta.get(a, ()):
            if t not in set_T:
                errors.append(f"Ta[{a}] has unknown profile t={t}.")
            if a not in set(instance.Ht.get(t, ())):
                errors.append(f"Inconsistent Ta/Ht: a={a} includes t={t}, but Ht[{t}] missing a.")

    for t in instance.T:
        for a in instance.Ht.get(t, ()):
            if a not in set_A:
                errors.append(f"Ht[{t}] includes unknown activity a={a}.")
            if t not in set(instance.Ta.get(a, ())):
                errors.append(f"Inconsistent Ht/Ta: Ht[{t}] includes a={a}, but Ta[{a}] missing t.")

    for j in instance.M1:
        if j not in instance.Oj:
            errors.append(f"Missing Oj[j] for full-time shift j={j}.")
            continue
        if len(instance.Oj[j]) != instance.f:
            errors.append(f"Oj[{j}] should have exactly f={instance.f} intervals.")
        for i in instance.Oj[j]:
            if i not in set_N:
                errors.append(f"Oj[{j}] contains i={i} outside N.")

    if not (0.0 <= instance.w <= 1.0):
        errors.append("w must be in [0, 1].")
    if instance.q <= 0:
        errors.append("q must be positive.")
    if instance.p < 0:
        errors.append("p must be nonnegative.")
    if instance.f <= 0:
        errors.append("f must be positive.")

    if errors:
        raise ValueError("Invalid instance:\n - " + "\n - ".join(errors))
