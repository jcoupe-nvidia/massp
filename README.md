# WAES MILP (cuOpt)

Recreates the WAES mixed-integer linear program from the provided paper PDF and solves it using NVIDIA cuOpt's LP/MILP Python API.

## Setup
- Create venv
- pip install -r requirements.txt

## Run (toy)
python -m src.solve --instance data/toy

## Output
Writes CSV summaries to out/ and runs post-solve constraint audits.

