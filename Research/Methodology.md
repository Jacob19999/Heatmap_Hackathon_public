# Burn Equity Index (BEI) — Implementation-Ready Specification

This document is a **detailed, implementation-ready BEI specification** consistent with the revised framing: structural access and capacity at census-tract level.

---

## 1) Core BEI definition

Let $i$ index a **census tract**.

$$
\boxed{
\mathrm{BEI}_i
=
100\Big(0.25\,S_i + 0.30\,T_i + 0.20\,P_i + 0.25\,C_i\Big)
}
$$

with

- $S_i$ = specialized supply scarcity
- $T_i$ = timely access burden
- $P_i$ = pediatric access gap
- $C_i$ = structural capacity gap

and each component is scaled to $[0,1]$, where:

- $0$ = best structural access
- $1$ = worst structural access

So:

- **higher BEI = worse structural inequity in timely burn-care access**

---

## 2) Geography, sets, and notation

Let:

- $i \in \mathcal{I}$: census tracts
- $j \in \mathcal{J}$: hospitals/facilities from NIRD
- $d \in \mathcal{D} \subseteq \mathcal{J}$: definitive burn centers
- $s \in \mathcal{S} \subseteq \mathcal{J}$: stabilization-capable hospitals

Population terms:

- $\mathrm{Pop}_i$: total tract population
- $\mathrm{ChildPop}_i$: tract child population

Transport sets and scenarios:

- $m \in \mathcal{M} = \{\text{road}, \text{air}\}$: transport mode
- $\omega \in \Omega$: transport scenario, such as ground-only or conditional ground-plus-air

Travel times:

- $t_{ij}^{(\text{road})}$: road-network travel time from tract $i$ to facility $j$
- $t_{sd}^{(\text{road})}$: road-network travel time from stabilization hospital $s$ to definitive burn center $d$
- $t_{ij}^{(\text{air})}$: total air-access time from tract $i$ to facility $j$
- $t_{sd}^{(\text{air})}$: total air-access time from stabilization hospital $s$ to definitive burn center $d$

Mode feasibility:

- $\tilde t_{ij}^{(m,\omega)}$: scenario-specific feasible travel time for leg $(i,j)$ under mode $m$
- $\tilde t_{sd}^{(m,\omega)}$: scenario-specific feasible travel time for leg $(s,d)$ under mode $m$

Define feasible mode-specific time as:

$$
\tilde t_{ab}^{(m,\omega)}=
\begin{cases}
t_{ab}^{(m)}, & \text{if mode } m \text{ is allowed under scenario } \omega \\
+\infty, & \text{otherwise}
\end{cases}
$$

for any relevant origin-destination pair $(a,b)$.

Air-access decomposition:

$$
t_{ab}^{(\text{air})}
=
t_a^{\text{dispatch}}
+
t_a^{\text{ground-to-launch}}
+
t_{ab}^{\text{flight}}
+
t_b^{\text{landing-to-facility}}
+
t_{ab}^{\text{handoff}}
$$

This formulation treats air access as a **multi-stage pathway**, not just straight-line flight time. The road legs can be computed from OpenStreetMap + OSRM, while candidate airport/heliport infrastructure can be sourced from public FAA airport/heliport records for the optional air scenario.

Transfer term:

- $\tau_s$: fixed transfer penalty at stabilization hospital $s$

This $\tau_s$ is not patient-level waiting time. It is a **structural routing penalty** representing the extra burden of requiring interfacility transfer. For a first implementation, set:

$$
\tau_s = \tau
$$

for all $s$, where $\tau$ is a constant such as 30, 45, or 60 minutes, and then test sensitivity.

---

## 3) Distance-decay function

Use a transparent decay function for access contribution. A step-decay version is recommended because it is easy to explain to judges.

$$
g(t)=
\begin{cases}
1.00, & t \le 30 \\
0.60, & 30 < t \le 60 \\
0.30, & 60 < t \le 90 \\
0, & t > 90
\end{cases}
$$

This gives a primary 60-minute interpretation while still distinguishing 30-minute and 90-minute sensitivity bands.

---

## 4) Robust normalization

For any raw metric $X_i$, define robust min-max normalization using national tract percentiles:

$$
\mathrm{Norm}(X_i)
=
\min\left\{
1,\;
\max\left[
0,\;
\frac{X_i - Q_{5}(X)}{Q_{95}(X)-Q_{5}(X)}
\right]
\right\}
$$

where $Q_5(X)$ and $Q_{95}(X)$ are the 5th and 95th percentiles of the raw tract distribution.

This avoids the score being dominated by extreme outliers.

For metrics where **higher raw values are better** access, convert them into a gap by:

$$
\mathrm{Gap}(X_i)=1-\mathrm{Norm}(X_i)
$$

---

## 5) Component formulas

### A. Specialized supply scarcity ($S_i$)

This measures how scarce specialized burn-care supply is around tract $i$, using a weighted accessibility score.

#### A1. Facility capability weight

Define a supply weight $q_j^{(S)}$ for each facility:

$$
q_j^{(S)}=
\begin{cases}
1.00, & \text{ABA verified burn center} \\
0.85, & \text{state-designated burn center} \\
0.50, & \text{burn-capable non-verified center} \\
0.20, & \text{trauma-only stabilization site} \\
0, & \text{otherwise}
\end{cases}
$$

These are policy weights, not "truth," and can be varied in sensitivity analysis.

#### A2. Facility-side provider-to-population ratio

For each facility $j$, compute:

$$
R_j^{(S)}
=
\frac{q_j^{(S)}}
{\sum_{k \in \mathcal{I}} \mathrm{Pop}_k\, g(t_{kj})}
$$

This is the tract-weighted catchment burden for that facility.

#### A3. Tract-side specialized supply accessibility

$$
A_i^{(S)}
=
\sum_{j \in \mathcal{J}} R_j^{(S)}\, g(t_{ij})
$$

#### A4. Convert to scarcity score

$$
\boxed{
S_i = 1 - \mathrm{Norm}\left(A_i^{(S)}\right)
}
$$

Interpretation:

- large $A_i^{(S)}$ = strong nearby specialty supply
- large $S_i$ = scarce specialty supply

---

### B. Timely access burden ($T_i$)

This is the most important access term. It measures the burden of reaching definitive burn care under a **regionalized, tiered system**, rather than assuming every patient goes directly to a verified center.

The recommended approach is **scenario-based multimodal routing**. Publish results for at least:

- a **ground-only baseline**; and
- a **conditional ground-plus-air sensitivity scenario**

The ground-only baseline is the default because it is easiest to reproduce at national scale with free routing tools. The ground-plus-air scenario is included because prior burn-access work shows that transport mode can materially change rural access estimates.

#### B1. Direct travel time to definitive burn care

For scenario $\omega$, define direct access as:

$$
T^{\text{dir}}_{i,\omega}
=
\min_{d \in \mathcal{D}}
\left[
\min_{m \in \mathcal{M}}
\tilde t_{id}^{(m,\omega)}
\right]
$$

#### B2. Travel time to nearest stabilization-capable hospital

$$
T^{\text{stab}}_{i,\omega}
=
\min_{s \in \mathcal{S}}
\left[
\min_{m \in \mathcal{M}}
\tilde t_{is}^{(m,\omega)}
\right]
$$

#### B3. Transfer-aware definitive care path

$$
T^{\text{trans}}_{i,\omega}
=
\min_{s \in \mathcal{S},\; d \in \mathcal{D}}
\left[
\min_{m_1 \in \mathcal{M}} \tilde t_{is}^{(m_1,\omega)}
+
\tau_s
+
\min_{m_2 \in \mathcal{M}} \tilde t_{sd}^{(m_2,\omega)}
\right]
$$

This allows the first leg and second leg to use different feasible modes under the same scenario.

#### B4. System travel time

To respect regionalized care logic, define:

$$
T^{\text{sys}}_{i,\omega}
=
\min\left(T^{\text{dir}}_{i,\omega},\; T^{\text{trans}}_{i,\omega}\right)
$$

This says the system can function either by:

- direct definitive access, or
- stabilization followed by transfer

#### B5. Tier penalty

We want a second term that penalizes places that lack prompt stabilization even if a transfer pathway technically exists.

Define:

$$
\Delta_{i,\omega} = \max\left(0,\; T^{\text{stab}}_{i,\omega} - 30\right)
$$

This means:

- no penalty if a stabilization-capable hospital is within 30 minutes
- increasing penalty if even first-line stabilization is far away

#### B6. Timely access burden score

For the chosen scenario $\omega$:

$$
\boxed{
T_{i,\omega}
=
0.75\,\mathrm{Norm}\left(T^{\text{sys}}_{i,\omega}\right)
+
0.25\,\mathrm{Norm}\left(\Delta_{i,\omega}\right)
}
$$

Interpretation:

- first term = overall system burden to definitive care
- second term = penalty for weak tiered infrastructure

#### B7. Public-data implementation for road + air

A reproducible public/free implementation is:

- **Road legs**: OpenStreetMap road data plus OSRM route/table services
- **Air infrastructure**: public FAA airport / heliport records
- **Flight segment**: coordinate-based distance with an explicit scenario cruise-speed parameter
- **Dispatch / handoff**: explicit analyst-chosen scenario constants
- **Feasibility rule**: only allow air in scenarios where the origin and destination are linked to plausible launch / landing infrastructure

This keeps the air scenario accessible with public/free data while avoiding claims about real-time rotor-wing dispatch availability, weather, or operational acceptance.

---

### C. Pediatric access gap ($P_i$)

This is a separate pillar because pediatric burn access is one of the explicit challenge deliverables.

#### C1. Pediatric capability weight

Define a pediatric weight $q_j^{(P)}$:

$$
q_j^{(P)}=
\begin{cases}
1.00, & \text{pediatric burn capable and ABA verified} \\
0.85, & \text{pediatric burn capable and state-designated} \\
0.60, & \text{pediatric trauma L1/L2 plus burn-capable} \\
0.25, & \text{pediatric stabilization only} \\
0, & \text{otherwise}
\end{cases}
$$

Our research maps this from NIRD fields such as:

- `BURN_PEDS`
- `PEDS_TRAUMA_L1`
- `PEDS_TRAUMA_L2`
- `ABA_VERIFIED`
- `BC_STATE_DESIGNATED`

#### C2. Facility-side pediatric provider-to-child-population ratio

$$
R_j^{(P)}
=
\frac{q_j^{(P)}}
{\sum_{k \in \mathcal{I}} \mathrm{ChildPop}_k\, g(t_{kj})}
$$

#### C3. Tract-side pediatric accessibility

$$
A_i^{(P)}
=
\sum_{j \in \mathcal{J}} R_j^{(P)}\, g(t_{ij})
$$

#### C4. Convert to pediatric access gap

$$
\boxed{
P_i = 1 - \mathrm{Norm}\left(A_i^{(P)}\right)
}
$$

Interpretation:

- high $P_i$ = worse pediatric burn access relative to child population

---

### D. Structural capacity gap ($C_i$)

This measures structural burn-bed adequacy, not real-time open beds.

#### D1. Effective structural bed count

For each facility $j$:

$$
\mathrm{EffBeds}_j = \mathrm{BURN\_BEDS}_j \cdot u_j
$$

where:

- baseline structural scenario: $u_j = 1$
- conservative sensitivity scenario: $u_j = u$, with $u \in [0.6,0.9]$

This does **not** claim real-time occupancy truth. It is just a scenario adjustment.

#### D2. Facility-side bed-to-population ratio

$$
R_j^{(C)}
=
\frac{\mathrm{EffBeds}_j\, q_j^{(S)}}
{\sum_{k \in \mathcal{I}} \mathrm{Pop}_k\, g(t_{kj})}
$$

#### D3. Tract-side structural bed accessibility

$$
A_i^{(C)}
=
\sum_{j \in \mathcal{J}} R_j^{(C)}\, g(t_{ij})
$$

#### D4. Convert to capacity gap

$$
\boxed{
C_i = 1 - \mathrm{Norm}\left(A_i^{(C)}\right)
}
$$

Interpretation:

- high $C_i$ = poor structural access to burn-bed capacity

---

## 6) Final BEI in full expanded form

Putting it all together:

$$
\boxed{
\mathrm{BEI}_i
=
100\Big[
0.25\Big(1-\mathrm{Norm}(A_i^{(S)})\Big)
+
0.30\Big(0.75\,\mathrm{Norm}(T_{i,\omega}^{\text{sys}})+0.25\,\mathrm{Norm}(\Delta_{i,\omega})\Big)
+
0.20\Big(1-\mathrm{Norm}(A_i^{(P)})\Big)
+
0.25\Big(1-\mathrm{Norm}(A_i^{(C)})\Big)
\Big]
}
$$

where:

$$
A_i^{(S)}=\sum_{j \in \mathcal{J}}\left(
\frac{q_j^{(S)}}{\sum_{k \in \mathcal{I}}\mathrm{Pop}_k g(t_{kj})}
\right)g(t_{ij})
$$

$$
T_{i,\omega}^{\text{sys}}=
\min\left(
\min_{d\in \mathcal{D}} \min_{m\in\mathcal{M}} \tilde t_{id}^{(m,\omega)},
\min_{s\in \mathcal{S},d\in \mathcal{D}}
\left(
\min_{m_1\in\mathcal{M}} \tilde t_{is}^{(m_1,\omega)}
+
\tau_s
+
\min_{m_2\in\mathcal{M}} \tilde t_{sd}^{(m_2,\omega)}
\right)
\right)
$$

$$
\Delta_{i,\omega}=\max(0, T_{i,\omega}^{\text{stab}}-30)
\qquad\text{with}\qquad
T_{i,\omega}^{\text{stab}}=\min_{s\in \mathcal{S}} \min_{m\in\mathcal{M}} \tilde t_{is}^{(m,\omega)}
$$

$$
A_i^{(P)}=\sum_{j \in \mathcal{J}}\left(
\frac{q_j^{(P)}}{\sum_{k \in \mathcal{I}}\mathrm{ChildPop}_k g(t_{kj})}
\right)g(t_{ij})
$$

$$
A_i^{(C)}=\sum_{j \in \mathcal{J}}\left(
\frac{\mathrm{EffBeds}_j\, q_j^{(S)}}{\sum_{k \in \mathcal{I}}\mathrm{Pop}_k g(t_{kj})}
\right)g(t_{ij})
$$

---

## 7) Companion outputs to publish beside BEI

These should be reported separately so judges can see the concrete challenge outputs, not just the composite score:

$$
\mathrm{NearestBurnTime}_{i,\omega} = \min_{d\in \mathcal{D}} \min_{m\in\mathcal{M}} \tilde t_{id}^{(m,\omega)}
$$

$$
\mathrm{BedsPer100k}_i
=
100000\cdot
\frac{\sum_j \mathrm{EffBeds}_j\, g(t_{ij})}
{\mathrm{Pop}_i}
$$

$$
\mathrm{PedsAccess}_i = A_i^{(P)}
$$

$$
\mathrm{CentersPer100k}_i
=
100000\cdot
\frac{\sum_j q_j^{(S)} g(t_{ij})}
{\mathrm{Pop}_i}
$$

And for county $m$, use population-weighted rollups:

$$
\mathrm{BEI}_m
=
\frac{\sum_{i \in m}\mathrm{Pop}_i\,\mathrm{BEI}_i}
{\sum_{i \in m}\mathrm{Pop}_i}
$$

---

## 8) Need overlay kept separate from BEI

Because BEI is to remain a **structural access and capacity** measure, do not fold demand uncertainty into the core score.

If needed, define a separate priority overlay:

$$
\mathrm{NeedOverlay}_i
=
\alpha\,\mathrm{Norm}(\mathrm{Pop}_i)
+
(1-\alpha)\,\mathrm{Norm}(\mathrm{ChildPop}_i)
$$

or include a public injury proxy later.

Then create a planning layer such as:

$$
\mathrm{Priority}_i = \mathrm{BEI}_i \times \left(1+\lambda\,\mathrm{NeedOverlay}_i\right)
$$

But keep this **outside** the core BEI.

---

## 9) Recommended default parameter choices

For the first build, use:

- catchment bands: 30 / 60 / 90 minutes
- primary policy threshold: 60 minutes
- stabilization threshold in $\Delta_{i,\omega}$: 30 minutes
- transfer penalty $\tau$: 45 minutes baseline
- baseline scenario: ground-only
- multimodal sensitivity scenario: conditional ground-plus-air
- air dispatch and handoff terms: explicit scenario constants
- air flight segment: coordinate-based distance divided by a documented scenario cruise speed
- capacity utilization factor $u$: 1.0 baseline, 0.75 sensitivity
- normalization: 5th to 95th percentile winsorized min-max

---

## 10) Public/free data scope for the transport model

The model uses **challenge-provided NIRD + public/free augmentation layers**. In practice, NIRD supplies the burn-system hospital layer, while the transport and geographic enrichment stack comes from public/free sources.

The **road** portion of the transport model is feasible with public/free sources:

- OpenStreetMap road network data
- OSRM route/table services

The **air sensitivity scenario** is also feasible with public/free infrastructure data if it is framed correctly:

- public FAA airport / heliport records for launch and landing infrastructure
- tract and hospital coordinates from Census geographies / geocoding
- analyst-defined dispatch, handoff, and cruise-speed parameters

What is **not** directly observed in the free public stack is real-time rotor-wing availability, weather constraints, or live dispatch logic. For that reason, the air component should be reported as a **scenario-based sensitivity analysis**, not as a guaranteed operational travel time.

---

## 11) Plain-English interpretation

A tract gets a **high BEI** if it has:

- weak nearby specialized burn supply,
- long direct or transfer-aware travel burden,
- poor pediatric-specific access,
- weak structural access to burn-bed capacity.

A tract gets a **low BEI** if it has:

- strong nearby specialty supply,
- timely direct or regionalized transfer access,
- good pediatric access,
- strong structural bed access.

---

> Optional next steps: turn this into a **Methods section in paper style**, or into a **notebook-ready variable mapping** from NIRD + ACS + RUCA + OSRM.
