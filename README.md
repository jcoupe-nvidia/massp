# WAES MILP (cuOpt)

Recreates the WAES mixed-integer linear program from the provided paper PDF and solves it by sending a MILP payload to a self-hosted NVIDIA cuOpt server.

## Setup
- Create Python 3.10 venv
- pip install -r requirements.txt
- Ensure cuOpt server is reachable (default configured here: `127.0.0.1:5000`)
- Edit `cuopt-config.yaml` to tune server and solver settings.

## Run (toy)
python -m src.solve --instance data/toy

## Run (explicit server)
python -m src.solve --instance data/toy --server-ip 127.0.0.1 --server-port 5000

## Config File
`cuopt-config.yaml` supports:

- `server.ip`
- `server.port`
- `server.polling_timeout`
- `server.repoll_tries`
- `server.repoll_interval`
- `solver.time_limit`
- `solver.tolerances` (e.g. `mip_relative_gap`)
- `solver.parameters` (pass-through cuOpt settings)
- `solver.solver_config` or `solver.raw` for direct advanced payload merges

CLI flags override config values.

`solver.parameters` and `solver.tolerances` are validated against the cuOpt LP/MILP server schema (invalid keys fail fast before submit).

## Output
Writes CSV summaries to out/ and runs post-solve constraint audits.

## Smoke Test (CLI script)
bash scripts/smoke.sh

`scripts/smoke.sh` uses `/home/nvidia/cuopt_venv/bin/python` by default and falls back to `python` if unavailable.
