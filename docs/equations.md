# WAES MILP Equations (Paper Transcription)

Source: *A New Sustainable Warehouse Management Approach for Workforce and Activities Scheduling*, Section 3.4, pp. 11-12.

## Objective

**Eq. (1), p. 11**

\[
\min : \sum_{j \in M}\sum_{t \in T} c_t \cdot y_{tj}
\]

## Constraints

**Eq. (2), p. 11**

\[
\sum_{j \in M}\sum_{k=i}^{until} x_{aijk} \cdot b_{kj} = d_{ai},
\quad \forall i \in N,\ \forall a \in B \cap A_1;\ until = \min(i+v_a, n)
\]

**Eq. (3), p. 11**

\[
\sum_{j \in M}\sum_{k=i}^{until} x_{aijk} \cdot b_{kj} = d_{ai},
\quad \forall i \in N,\ \forall a \in B \cap A_2;\ until = r_a
\]

**Eq. (4), p. 11**

\[
\sum_{j \in M}\sum_{k'=k}^{until} x_{akjk'} \cdot b_{k'j}
\ge
\sum_{a' \in G_a} s_{a,a'} \cdot \sum_{j \in M}\sum_{i \in N} x_{a'ijk},
\quad \forall k \in N,\ \forall a \in C \cap A_1;\ until = \min(k+v_a, n)
\]

**Eq. (5), p. 11**

\[
\sum_{j \in M}\sum_{k'=k}^{until} x_{akjk'} \cdot b_{k'j}
\ge
\sum_{a' \in G_a} s_{a,a'} \cdot \sum_{j \in M}\sum_{i \in N} x_{a'ijk},
\quad \forall k \in N,\ \forall a \in C \cap A_2;\ until = r_a
\]

**Eq. (6), p. 11**

\[
\sum_{i=1}^{k} x_{aijk} \le \sum_{t \in T_a} y_{tija},
\quad \forall k \in N;\ \forall j \in M,\ \forall a \in A
\]

**Eq. (7), p. 11**

\[
\sum_{a \in H_t} y_{tija} \le y_{tj},
\quad \forall i \in N,\ \forall j \in M,\ \forall t \in T
\]

**Eq. (8), p. 11**

\[
\sum_{t \in T}\sum_{j \in M}\sum_{a \in A} y_{tija} \le q,
\quad \forall i \in N
\]

**Eq. (9), p. 11**

\[
\sum_{\forall i \in O_j}\sum_{a \in H_t} y_{tija} \le (f-p)\cdot y_{tj},
\quad \forall t \in T,\ \forall j \in M_1
\]

**Eq. (10), p. 11**

\[
\sum_{j \in M}\sum_{t \in T} y_{tj}
\le
w \cdot \sum_{j \in M_2}\sum_{t \in T} y_{tj}
\]

## Variable Domain

**Eq. (11), p. 12**

\[
\text{integer}: x_{aijk},\ y_{tija},\ y_{tj},
\quad \forall i \in N,\ \forall j \in M,\ \forall a \in A,\ \forall t \in T,\ \forall k \in N
\]

