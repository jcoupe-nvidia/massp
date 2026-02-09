"""Helpers for solving LP/MILP payloads with cuOpt self-hosted server."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Dict


@dataclass(frozen=True)
class ServerConfig:
    ip: str = "127.0.0.1"
    port: int = 5000
    polling_timeout: int = 20
    repoll_tries: int = 120
    repoll_interval: float = 1.0


def _load_client(server: ServerConfig) -> Any:
    try:
        from cuopt_sh_client import CuOptServiceSelfHostClient
    except Exception as exc:
        raise ImportError(
            "cuopt_sh_client is not installed. Install `cuopt-sh-client` in this environment."
        ) from exc

    return CuOptServiceSelfHostClient(
        ip=server.ip,
        port=str(server.port),
        polling_timeout=server.polling_timeout,
        timeout_exception=False,
    )


def _extract_solver_response(response: Dict[str, Any]) -> Dict[str, Any]:
    if "response" not in response:
        raise RuntimeError(f"Unexpected cuOpt response shape: missing `response` key: {response}")
    wrapped = response["response"]
    if "solver_response" not in wrapped:
        raise RuntimeError(
            f"Unexpected cuOpt response shape: missing `solver_response` key: {response}"
        )
    return wrapped["solver_response"]


def solve_milp_payload(payload: Dict[str, Any], server: ServerConfig) -> Dict[str, Any]:
    """Send MILP payload to cuOpt server and return `solver_response` dict."""
    client = _load_client(server)
    response = client.get_LP_solve(payload, response_type="dict")

    # Async flow may return only a request id; repoll until final response is available.
    tries = 0
    while "response" not in response:
        if "reqId" not in response:
            raise RuntimeError(f"Unexpected async cuOpt response shape: {response}")
        if tries >= server.repoll_tries:
            raise TimeoutError(f"Exceeded repoll limit ({server.repoll_tries}) for reqId={response['reqId']}")
        response = client.repoll(response["reqId"], response_type="dict")
        tries += 1
        # Small delay to avoid tight polling loops when server is busy.
        time.sleep(server.repoll_interval)

    return _extract_solver_response(response)
