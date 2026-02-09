# Codex Rules: WAES MILP (cuOpt)

## Highest priority: Fidelity to the PDF
1. The PDF equations are authoritative. If prose conflicts with math, follow the math.
2. First create/complete docs/equations.md with verbatim equations (objective + constraints), including equation numbers and page numbers.
3. Do not invent indices, sets, or bounds. Derive all index domains from the paper’s notation/table and the equations.
4. Every implemented constraint must include a comment with:
   - paper equation number
   - page number
   - one-line intent
5. No algebraic “simplification” until a verbatim implementation exists and passes audits.

## Modeling & code structure
6. Implement using NVIDIA cuOpt LP/MILP Python API (Problem, addVariable, addConstraint, setObjective, solve).
7. Keep a 1:1 mapping from paper symbols to code names in docs/notation_map.md.
8. Separate:
   - instance data & validation (src/instance.py)
   - model construction (src/build_waes.py, src/build_ws.py)
   - solving (src/solve.py)
   - post-solve audits (src/audit.py)
9. All arrays/dicts must be validated for shape and index coverage before solve.

## Verification
10. Implement audits that numerically re-check every constraint family after solve; fail loudly on violation.
11. Implement WS baseline as WAES with AES disabled (deadlines set to zero, per paper description) and verify objective relationships on the toy instance.

## Output expectations
12. Provide a runnable CLI: `python -m src.solve --instance data/toy`
13. Write results to `out/` as CSV (schedule, staffing by interval/activity, demand-fulfillment flows).

