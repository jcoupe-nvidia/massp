"""Post-solve audits for all WAES/WS constraint families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.instance import InstanceData
from src.solution_types import SolvedValues


@dataclass
class AuditIssue:
    equation: str
    detail: str
    violation: float


@dataclass
class AuditReport:
    passed: bool
    tolerance: float
    issues: List[AuditIssue]


def _until_a1(instance: InstanceData, i_or_k: int, a: int, ws_mode: bool) -> int:
    v_a = 0 if ws_mode else int(instance.v[a])
    return min(i_or_k + v_a, instance.n)


def _until_a2(instance: InstanceData, i_or_k: int, a: int, ws_mode: bool) -> int:
    if ws_mode:
        return i_or_k
    r_a = int(instance.r[a])
    if r_a <= 0:
        return i_or_k
    return max(i_or_k, min(r_a, instance.n))


def run_audits(
    instance: InstanceData,
    solved: SolvedValues,
    ws_mode: bool,
    tol: float = 1e-4,
) -> AuditReport:
    """Re-check Eq. (2)-(11) numerically on solved values."""
    issues: List[AuditIssue] = []

    def check_eq(eq: str, lhs: float, rhs: float, detail: str) -> None:
        gap = abs(lhs - rhs)
        if gap > tol:
            issues.append(AuditIssue(equation=eq, detail=detail, violation=gap))

    def check_le(eq: str, lhs: float, rhs: float, detail: str) -> None:
        gap = lhs - rhs
        if gap > tol:
            issues.append(AuditIssue(equation=eq, detail=detail, violation=gap))

    def check_ge(eq: str, lhs: float, rhs: float, detail: str) -> None:
        gap = rhs - lhs
        if gap > tol:
            issues.append(AuditIssue(equation=eq, detail=detail, violation=gap))

    set_BA1 = set(instance.B) & set(instance.A1)
    set_BA2 = set(instance.B) & set(instance.A2)
    set_CA1 = set(instance.C) & set(instance.A1)
    set_CA2 = set(instance.C) & set(instance.A2)

    # Eq. (2), p. 11: independent A1 demand fulfillment in deadline window.
    for i in instance.N:
        for a in sorted(set_BA1):
            until = _until_a1(instance, i, a, ws_mode)
            lhs = sum(
                solved.x_aijk[(a, i, j, k)] * instance.b[(k, j)]
                for j in instance.M
                for k in range(i, until + 1)
            )
            rhs = instance.d[(a, i)]
            check_eq("Eq(2)", lhs, rhs, f"i={i}, a={a}")

    # Eq. (3), p. 11: independent A2 demand fulfillment by r_a.
    for i in instance.N:
        for a in sorted(set_BA2):
            until = _until_a2(instance, i, a, ws_mode)
            lhs = sum(
                solved.x_aijk[(a, i, j, k)] * instance.b[(k, j)]
                for j in instance.M
                for k in range(i, until + 1)
            )
            rhs = instance.d[(a, i)]
            check_eq("Eq(3)", lhs, rhs, f"i={i}, a={a}")

    # Eq. (4), p. 11: dependent A1 lower-bound fulfillment by dependency percentages.
    for k in instance.N:
        for a in sorted(set_CA1):
            until = _until_a1(instance, k, a, ws_mode)
            lhs = sum(
                solved.x_aijk[(a, k, j, kp)] * instance.b[(kp, j)]
                for j in instance.M
                for kp in range(k, until + 1)
            )
            rhs = sum(
                instance.s[(a, a_parent)]
                * sum(
                    solved.x_aijk[(a_parent, i, j, k)]
                    for j in instance.M
                    for i in instance.N
                )
                for a_parent in instance.Ga[a]
            )
            check_ge("Eq(4)", lhs, rhs, f"k={k}, a={a}")

    # Eq. (5), p. 11: dependent A2 lower-bound fulfillment by dependency percentages.
    for k in instance.N:
        for a in sorted(set_CA2):
            until = _until_a2(instance, k, a, ws_mode)
            lhs = sum(
                solved.x_aijk[(a, k, j, kp)] * instance.b[(kp, j)]
                for j in instance.M
                for kp in range(k, until + 1)
            )
            rhs = sum(
                instance.s[(a, a_parent)]
                * sum(
                    solved.x_aijk[(a_parent, i, j, k)]
                    for j in instance.M
                    for i in instance.N
                )
                for a_parent in instance.Ga[a]
            )
            check_ge("Eq(5)", lhs, rhs, f"k={k}, a={a}")

    # Eq. (6), p. 11: interval-k execution bounded by activity staffing in interval k.
    for k in instance.N:
        for j in instance.M:
            for a in instance.A:
                lhs = sum(solved.x_aijk[(a, i, j, k)] for i in range(1, k + 1))
                rhs = sum(solved.y_tija[(t, k, j, a)] for t in instance.Ta[a])
                check_le("Eq(6)", lhs, rhs, f"k={k}, j={j}, a={a}")

    # Eq. (7), p. 11: profile interval activity assignments bounded by shift staffing.
    for i in instance.N:
        for j in instance.M:
            for t in instance.T:
                lhs = sum(solved.y_tija[(t, i, j, a)] for a in instance.Ht[t])
                rhs = solved.y_tj[(t, j)]
                check_le("Eq(7)", lhs, rhs, f"i={i}, j={j}, t={t}")

    # Eq. (8), p. 11: max active workers per interval.
    for i in instance.N:
        lhs = sum(
            solved.y_tija[(t, i, j, a)]
            for t in instance.T
            for j in instance.M
            for a in instance.A
        )
        rhs = float(instance.q)
        check_le("Eq(8)", lhs, rhs, f"i={i}")

    # Eq. (9), p. 11: break-window load cap for full-time workers.
    for t in instance.T:
        for j in instance.M1:
            lhs = sum(
                solved.y_tija[(t, i, j, a)]
                for i in instance.Oj[j]
                for a in instance.Ht[t]
            )
            rhs = float((instance.f - instance.p) * solved.y_tj[(t, j)])
            check_le("Eq(9)", lhs, rhs, f"t={t}, j={j}")

    # Eq. (10), p. 11: part-time share cap.
    lhs = sum(solved.y_tj[(t, j)] for j in instance.M2 for t in instance.T)
    rhs = instance.w * sum(solved.y_tj[(t, j)] for j in instance.M for t in instance.T)
    check_le("Eq(10)", lhs, rhs, "part-time-share")

    # Eq. (11), p. 12: integrality of x, y_tija, y_tj.
    for key, value in solved.x_aijk.items():
        check_eq("Eq(11)", value, round(value), f"x{key}")
    for key, value in solved.y_tija.items():
        check_eq("Eq(11)", value, round(value), f"y_tija{key}")
    for key, value in solved.y_tj.items():
        check_eq("Eq(11)", value, round(value), f"y_tj{key}")

    return AuditReport(
        passed=not issues,
        tolerance=tol,
        issues=issues,
    )

