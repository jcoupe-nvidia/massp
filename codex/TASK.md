# Task Brief for Codex

You will be given docs/paper.pdf.

Deliverables:
1) docs/equations.md: verbatim transcription of Eq. (1)-(11) with page numbers.
2) docs/notation_map.md: symbol table mapping paper notation to code identifiers.
3) A working cuOpt implementation of WAES + WS baseline:
   - src/instance.py
   - src/build_waes.py
   - src/build_ws.py
   - src/solve.py
   - src/audit.py
   - src/extract_solution.py
4) data/toy instance files and a runnable smoke test.

Constraints:
- Follow codex/RULES.md strictly.
- Use cuOpt LP/MILP Python API for modeling and solving.
- Every constraint must be auditable post-solve.

