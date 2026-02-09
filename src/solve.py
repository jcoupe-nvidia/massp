"""CLI entrypoint: build, solve on cuOpt server, audit, and export solutions."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Sequence
import copy

import yaml

from src.audit import run_audits
from src.build_waes import WAESModel, build_waes_model
from src.build_ws import build_ws_model
from src.cuopt_server import ServerConfig, solve_milp_payload
from src.extract_solution import write_solution_csvs
from src.instance import InstanceData, load_instance
from src.solution_types import SolvedValues

ALLOWED_SOLVER_CONFIG_KEYS = {
    "time_limit",
    "num_cpu_threads",
    "num_gpus",
    "infeasibility_detection",
    "pdlp_solver_mode",
    "method",
    "iteration_limit",
    "mip_scaling",
    "mip_heuristics_only",
    "augmented",
    "folding",
    "dualize",
    "ordering",
    "barrier_dual_initial_point",
    "eliminate_dense_columns",
    "cudss_deterministic",
    "crossover",
    "presolve",
    "dual_postsolve",
    "log_to_console",
    "strict_infeasibility",
    "user_problem_file",
    "per_constraint_residual",
    "save_best_primal_so_far",
    "first_primal_feasible",
    "log_file",
    "solution_file",
    "solver_mode",
    "heuristics_only",
    "tolerances",
}

ALLOWED_TOLERANCE_KEYS = {
    "optimality",
    "absolute_primal_tolerance",
    "absolute_dual_tolerance",
    "absolute_gap_tolerance",
    "relative_primal_tolerance",
    "relative_dual_tolerance",
    "relative_gap_tolerance",
    "primal_infeasible_tolerance",
    "dual_infeasible_tolerance",
    "mip_integrality_tolerance",
    "mip_absolute_gap",
    "mip_relative_gap",
    "mip_absolute_tolerance",
    "mip_relative_tolerance",
    # Deprecated aliases still accepted by server schema.
    "absolute_primal",
    "absolute_dual",
    "absolute_gap",
    "relative_primal",
    "relative_dual",
    "relative_gap",
    "primal_infeasible",
    "dual_infeasible",
    "integrality_tolerance",
    "absolute_mip_gap",
    "relative_mip_gap",
}


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(dst)
    for key, value in src.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _load_yaml_config(path: Path, required: bool) -> Dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Config file not found: {path}")
        return {}

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return raw


def _solver_config_from_yaml(config: Dict[str, Any]) -> Dict[str, Any]:
    solver = config.get("solver", {})
    if not isinstance(solver, dict):
        raise ValueError("`solver` section in config must be a mapping.")

    cfg: Dict[str, Any] = {}

    solver_config = solver.get("solver_config", {})
    if solver_config:
        if not isinstance(solver_config, dict):
            raise ValueError("`solver.solver_config` must be a mapping.")
        cfg = _deep_merge(cfg, solver_config)

    if "time_limit" in solver and solver["time_limit"] is not None:
        cfg["time_limit"] = int(solver["time_limit"])

    tolerances = solver.get("tolerances", {})
    if tolerances:
        if not isinstance(tolerances, dict):
            raise ValueError("`solver.tolerances` must be a mapping.")
        cfg["tolerances"] = _deep_merge(cfg.get("tolerances", {}), tolerances)

    parameters = solver.get("parameters", {})
    if parameters:
        if not isinstance(parameters, dict):
            raise ValueError("`solver.parameters` must be a mapping.")
        cfg = _deep_merge(cfg, parameters)

    raw = solver.get("raw", {})
    if raw:
        if not isinstance(raw, dict):
            raise ValueError("`solver.raw` must be a mapping.")
        cfg = _deep_merge(cfg, raw)

    return cfg


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _validate_solver_config(cfg: Dict[str, Any]) -> None:
    unknown = sorted(k for k in cfg.keys() if k not in ALLOWED_SOLVER_CONFIG_KEYS)
    if unknown:
        raise ValueError(
            "Unsupported solver_config keys in resolved config: "
            f"{unknown}. Check cuOpt server docs (/cuopt/docs)."
        )
    tolerances = cfg.get("tolerances", {})
    if tolerances is None:
        return
    if not isinstance(tolerances, dict):
        raise ValueError("solver_config.tolerances must be a mapping.")
    unknown_tol = sorted(k for k in tolerances.keys() if k not in ALLOWED_TOLERANCE_KEYS)
    if unknown_tol:
        raise ValueError(
            "Unsupported tolerances keys in resolved config: "
            f"{unknown_tol}. Check cuOpt server docs (/cuopt/docs)."
        )


def _build_mode(instance: InstanceData, mode: str) -> WAESModel:
    if mode == "waes":
        return build_waes_model(instance=instance, ws_mode=False)
    if mode == "ws":
        return build_ws_model(instance=instance)
    raise ValueError(f"Unsupported mode: {mode}")


def _solution_vector_from_response(model: WAESModel, solution: Dict[str, Any]) -> List[float]:
    n_vars = len(model.variable_names)
    primal = solution.get("primal_solution")
    if isinstance(primal, Sequence) and not isinstance(primal, (str, bytes)):
        if len(primal) != n_vars:
            raise RuntimeError(
                f"primal_solution length mismatch: expected {n_vars}, got {len(primal)}."
            )
        return [float(v) for v in primal]

    vars_map = solution.get("vars")
    if isinstance(vars_map, dict):
        vec = [0.0] * n_vars
        for idx, name in enumerate(model.variable_names):
            vec[idx] = float(vars_map.get(name, 0.0))
        return vec

    raise RuntimeError("cuOpt response did not contain `primal_solution` or `vars`.")


def _collect_solution(model: WAESModel, mode: str, solver_response: Dict[str, Any]) -> SolvedValues:
    status = str(solver_response.get("status", "UNKNOWN"))
    if status.lower().startswith("infeasible"):
        raise RuntimeError(f"Solver status is infeasible for mode={mode}: {solver_response}")

    solution = solver_response.get("solution")
    if not isinstance(solution, dict):
        raise RuntimeError(f"Solver response missing solution payload: {solver_response}")

    vector = _solution_vector_from_response(model=model, solution=solution)
    objective = float(
        solution.get(
            "primal_objective",
            solution.get("objective", 0.0),
        )
    )

    x_vals = {key: vector[idx] for key, idx in model.x_aijk.items()}
    y_interval_vals = {key: vector[idx] for key, idx in model.y_tija.items()}
    y_shift_vals = {key: vector[idx] for key, idx in model.y_tj.items()}
    milp_stats = solution.get("milp_statistics", {})

    return SolvedValues(
        mode=mode,
        objective=objective,
        x_aijk=x_vals,
        y_tija=y_interval_vals,
        y_tj=y_shift_vals,
        status=status,
        solver_time=_optional_float(solution.get("solver_time")),
        mip_gap=_optional_float(milp_stats.get("mip_gap")),
        solution_bound=_optional_float(milp_stats.get("solution_bound")),
    )


def _run_one_mode(
    instance: InstanceData,
    mode: str,
    out_dir: Path,
    audit_tol: float,
    solver_cfg: Dict[str, Any],
    server_cfg: ServerConfig,
) -> SolvedValues:
    model = _build_mode(instance, mode)
    payload = model.to_server_payload(solver_config=solver_cfg)
    solver_response = solve_milp_payload(payload=payload, server=server_cfg)
    solved = _collect_solution(model=model, mode=mode, solver_response=solver_response)

    audit = run_audits(instance=instance, solved=solved, ws_mode=(mode == "ws"), tol=audit_tol)
    if not audit.passed:
        preview = "\n".join(
            f" - {issue.equation}: {issue.detail}, violation={issue.violation:.6g}"
            for issue in audit.issues[:20]
        )
        raise RuntimeError(
            f"Audit failed for mode={mode} with {len(audit.issues)} violations.\n{preview}"
        )

    mode_out = out_dir / mode
    write_solution_csvs(instance=instance, solved=solved, out_dir=mode_out)
    return solved


def _assert_expected_objectives(instance: InstanceData, solved_by_mode: Dict[str, SolvedValues]) -> None:
    if not instance.paper_expected_objective:
        return
    tol = instance.paper_objective_tolerance
    for mode, solved in solved_by_mode.items():
        if solved.status.lower() != "optimal":
            # For MILP, feasible incumbents can vary across runs; only enforce
            # paper objective checks on proven optimal solves.
            continue
        if mode not in instance.paper_expected_objective:
            continue
        expected = instance.paper_expected_objective[mode]
        gap = abs(solved.objective - expected)
        if gap > tol:
            raise RuntimeError(
                f"Objective mismatch for mode={mode}: got {solved.objective:.4f}, "
                f"expected {expected:.4f}, tolerance {tol:.4f}."
            )


def _assert_waes_vs_ws(solved_by_mode: Dict[str, SolvedValues], tol: float) -> None:
    if "waes" not in solved_by_mode or "ws" not in solved_by_mode:
        return
    waes_obj = solved_by_mode["waes"].objective
    ws_obj = solved_by_mode["ws"].objective
    if waes_obj - ws_obj > tol:
        raise RuntimeError(
            f"Expected WAES <= WS, but got WAES={waes_obj:.4f} and WS={ws_obj:.4f}."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve MASSP WAES/WS with cuOpt self-hosted server.")
    parser.add_argument(
        "--config",
        type=str,
        default="cuopt-config.yaml",
        help="YAML config file for server and solver parameters.",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Ignore config file and use CLI/default values only.",
    )
    parser.add_argument("--instance", type=str, default="data/toy", help="Instance dir or .json path.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=("waes", "ws", "both"),
        default="both",
        help="Solve WAES, WS, or both.",
    )
    parser.add_argument("--outdir", type=str, default="out", help="Output directory.")
    parser.add_argument("--audit-tol", type=float, default=1e-4, help="Audit tolerance.")
    parser.add_argument("--server-ip", type=str, default=None, help="cuOpt server IP.")
    parser.add_argument("--server-port", type=int, default=None, help="cuOpt server port.")
    parser.add_argument("--time-limit", type=int, default=None, help="Server solver time limit.")
    parser.add_argument(
        "--mip-relative-gap",
        type=float,
        default=None,
        help="Optional solver tolerance (mip_relative_gap).",
    )
    parser.add_argument(
        "--polling-timeout",
        type=int,
        default=None,
        help="cuOpt client polling timeout in seconds (default: time-limit + 30, min 60).",
    )
    parser.add_argument(
        "--repoll-tries",
        type=int,
        default=None,
        help="Maximum async repoll attempts.",
    )
    parser.add_argument(
        "--repoll-interval",
        type=float,
        default=None,
        help="Seconds between repoll attempts once only reqId is returned.",
    )
    parser.add_argument(
        "--skip-paper-objective-check",
        action="store_true",
        help="Skip checking solved objective against paper reference values if provided in instance.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instance = load_instance(args.instance)
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config_path = Path(args.config)
    config_required = not args.no_config and args.config != "cuopt-config.yaml"
    config = {} if args.no_config else _load_yaml_config(config_path, required=config_required)

    solver_cfg = _solver_config_from_yaml(config)
    if "time_limit" not in solver_cfg:
        solver_cfg["time_limit"] = 20
    if args.time_limit is not None:
        solver_cfg["time_limit"] = int(args.time_limit)
    if args.mip_relative_gap is not None:
        tolerances = solver_cfg.get("tolerances", {})
        if not isinstance(tolerances, dict):
            raise ValueError("solver_config.tolerances must be a mapping.")
        tolerances["mip_relative_gap"] = float(args.mip_relative_gap)
        solver_cfg["tolerances"] = tolerances
    _validate_solver_config(solver_cfg)

    server = config.get("server", {})
    if server and not isinstance(server, dict):
        raise ValueError("`server` section in config must be a mapping.")

    time_limit_for_polling = int(solver_cfg.get("time_limit", 20))
    configured_polling_timeout = None if not isinstance(server, dict) else server.get("polling_timeout")
    resolved_polling_timeout = (
        int(args.polling_timeout)
        if args.polling_timeout is not None
        else (
            int(configured_polling_timeout)
            if configured_polling_timeout is not None
            else max(time_limit_for_polling + 30, 60)
        )
    )

    server_cfg = ServerConfig(
        ip=(
            args.server_ip
            if args.server_ip is not None
            else str(server.get("ip", "127.0.0.1"))
        ),
        port=(
            int(args.server_port)
            if args.server_port is not None
            else int(server.get("port", 5000))
        ),
        polling_timeout=resolved_polling_timeout,
        repoll_tries=(
            int(args.repoll_tries)
            if args.repoll_tries is not None
            else int(server.get("repoll_tries", 120))
        ),
        repoll_interval=(
            float(args.repoll_interval)
            if args.repoll_interval is not None
            else float(server.get("repoll_interval", 1.0))
        ),
    )

    modes: List[str]
    if args.mode == "both":
        modes = ["waes", "ws"]
    else:
        modes = [args.mode]

    solved_by_mode: Dict[str, SolvedValues] = {}
    for mode in modes:
        solved_by_mode[mode] = _run_one_mode(
            instance=instance,
            mode=mode,
            out_dir=out_dir,
            audit_tol=args.audit_tol,
            solver_cfg=solver_cfg,
            server_cfg=server_cfg,
        )

    _assert_waes_vs_ws(solved_by_mode=solved_by_mode, tol=args.audit_tol)
    if not args.skip_paper_objective_check:
        _assert_expected_objectives(instance=instance, solved_by_mode=solved_by_mode)

    for mode in modes:
        solved = solved_by_mode[mode]
        extras: List[str] = []
        if solved.solver_time is not None:
            extras.append(f"solver_time={solved.solver_time:.3f}s")
        if solved.mip_gap is not None:
            extras.append(f"mip_gap={solved.mip_gap:.6f}")
        if solved.solution_bound is not None:
            extras.append(f"bound={solved.solution_bound:.4f}")
        extra_text = (" " + " ".join(extras)) if extras else ""
        print(
            f"[{mode}] objective={solved.objective:.4f} status={solved.status} "
            f"{extra_text} out={out_dir / mode}"
        )


if __name__ == "__main__":
    main()
