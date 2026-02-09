# Plan: Recreate WAES MILP and solve with cuOpt

## Phase 0 — Project setup
- Create Python package structure under src/
- Add requirements and a minimal CLI entry in src/solve.py

## Phase 1 — Paper transcription (no coding yet)
1) Populate docs/equations.md:
   - Objective (Eq. 1)
   - Constraints (Eq. 2–11)
   - Variable domains (integrality/binary)
   - Include page numbers
2) Populate docs/notation_map.md:
   - set symbols and meanings
   - parameter symbols and meanings
   - decision variable symbols → Python identifiers + index sets
3) Populate docs/modeling_notes.md:
   - list any ambiguity encountered (e.g., break window indexing)
   - record the chosen interpretation ONLY if the PDF is ambiguous

## Phase 2 — Data model
4) Implement src/instance.py with:
   - explicit index sets (T, S, A, P, etc.)
   - parameters stored as dicts keyed by tuples
   - validate_instance() ensuring complete coverage of required indices

## Phase 3 — Build WAES in cuOpt
5) Implement src/build_waes.py:
   - create cuOpt Problem()
   - create variables (continuous/integer/binary) with correct bounds
   - set objective per Eq. (1)
   - add constraints in numeric order (Eq. 2..11)
   - keep comments with equation+page
6) Implement src/audit.py:
   - re-check each constraint family on the solved values

## Phase 4 — WS baseline
7) Implement src/build_ws.py:
   - reuse WAES builder but force AES off (deadlines=0 or equivalent)
8) Add tests and a regression:
   - toy instance solves
   - audits pass
   - WAES objective <= WS objective on at least one configured scenario (when applicable)

## Phase 5 — Reporting
9) Implement src/extract_solution.py:
   - map cuOpt solution to pandas frames
   - write CSV summaries

