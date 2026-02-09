# Notation Map (Paper -> Code)

## Sets

| Paper | Meaning | Code identifier |
|---|---|---|
| \(N\) | Intervals of workday | `instance.N` |
| \(M\) | All shifts | `instance.M` |
| \(M_1\) | Full-time shifts | `instance.M1` |
| \(M_2\) | Part-time shifts | `instance.M2` |
| \(A\) | All activities | `instance.A` |
| \(B\) | Independent activities | `instance.B` |
| \(C\) | Dependent activities | `instance.C` |
| \(G_a\) | Activities that activity `a` depends on | `instance.Ga[a]` |
| \(A_1\) | Activities with window deadline | `instance.A1` |
| \(A_2\) | Activities with interval deadline | `instance.A2` |
| \(T\) | Worker profiles | `instance.T` |
| \(T_a\) | Profiles allowed for activity `a` | `instance.Ta[a]` |
| \(H_t\) | Activities allowed for profile `t` | `instance.Ht[t]` |

## Parameters

| Paper | Meaning | Code identifier |
|---|---|---|
| \(n\) | Last interval index in workday | `instance.n` |
| \(b_{kj}\) | Interval `k` is in shift `j` | `instance.b[(k, j)]` |
| \(d_{ai}\) | Worker demand for activity `a` in interval `i` | `instance.d[(a, i)]` |
| \(s_{a,a'}\) | Dependence percentage of `a` on `a'` (fraction) | `instance.s[(a, a_parent)]` |
| \(v_a\) | Window length deadline for `a in A1` | `instance.v[a]` |
| \(r_a\) | Deadline interval parameter for `a in A2` | `instance.r[a]` |
| \(c_t\) | Cost of profile `t` (full-time base) | `instance.c[t]` |
| \(q\) | Max active workers per interval | `instance.q` |
| \(p\) | Break duration | `instance.p` |
| \(f\) | Break window duration | `instance.f` |
| \(O_j\) | Break-eligible intervals for full-time shift `j` | `instance.Oj[j]` |
| \(w\) | Part-time worker share limit | `instance.w` |

## Decision Variables

| Paper | Meaning | Code identifier |
|---|---|---|
| \(y_{tj}\) | Workers of profile `t` assigned to shift `j` | `model.y_tj[(t, j)]` |
| \(y_{tija}\) | Workers of profile `t` in interval `i`, shift `j`, activity `a` | `model.y_tija[(t, i, j, a)]` |
| \(x_{aijk}\) | Flow from demand interval `i` to execution interval `k` in shift `j`, activity `a` | `model.x_aijk[(a, i, j, k)]` |

## Mode Flags

| Concept | Code identifier |
|---|---|
| WAES (deadlines enabled) | `ws_mode = False` |
| WS baseline (AES disabled; deadlines forced to zero) | `ws_mode = True` |

