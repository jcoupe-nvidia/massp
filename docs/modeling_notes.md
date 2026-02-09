# Modeling Notes

## Ambiguities in the Paper PDF

1. Eq. (6) uses `sum_{i=1}^k x_{aijk} <= sum_{t in T_a} y_{tija}` and leaves `i` free on the RHS.
Interpretation used in code:
`sum_{i=1}^k x_{aijk} <= sum_{t in T_a} y_{tkja}`.
Rationale: this is the only index-consistent form for interval-capacity in execution interval `k`.

2. Eq. (10) appears in print as:
`sum_{j in M} sum_{t in T} y_{tj} <= w * sum_{j in M2} sum_{t in T} y_{tj}`.
This conflicts with the textual definition of `w` as part-time share.
Interpretation used in code:
`sum_{j in M2} sum_{t in T} y_{tj} <= w * sum_{j in M} sum_{t in T} y_{tj}`.

3. Eq. (3)/(5) use `until = r_a` and Section 4.1 then sets WS baseline with `r_1 = 0`.
With `N = {1,...,n}`, a literal `until = 0` is invalid.
Interpretation used in code for WS mode:
`until = i`, i.e., same-interval fulfillment only (no postponement).

## Cost Handling

- Paper objective uses `c_t`, while Section 4.1 states part-time cost is half of full-time cost.
- Code keeps `c_t` as base full-time profile cost and multiplies by shift factor:
  - `1.0` for `j in M1`
  - `0.5` for `j in M2`

