"""Orthogonal wedge-chase searcher for Q3 (omni) and Q4 (mixed)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from jianmo.b_sim.geometry import q3_omni_scouts, q4_certainty_scouts

from geom import (
    ARENA_R,
    ERR_DEG,
    R_CLEAR,
    R_EFF_MAX,
    R_EFF_MIN,
    R_NEAR,
    ang_dist_deg,
    bearing_deg,
    bearing_vec,
    crossing_angle_deg,
    diametral_circle_covers_any,
    hypot,
    in_wedge,
    intersect_wedges,
    left_normal,
    polygon_unbounded,
    second_station_point,
    smallest_enclosing_circle,
)

R_DESIGN = 800.0
# Axis ψ≥45° covering offset at r=800 m: |t| ≥ 1500−800 = 700 m. Not a rounding of the
# 70-sample quantile |t|≈690.9 m, and not the [45°,135°] covering |t|≥795 m.
# Off-axis far corner of the 2° wedge is a named residual, not a covering of the wedge.
T_DESIGN = 700.0
MAX_ACTIONS = 900
MAX_CHASE_ITERS = 10
# Omni: G ∈ Ω ⊆ disk(C, R_sec) is heard at the SEC centre iff R_sec ≤ R_eff.
# Mixed sources may still be back-lobe silent there; that path returns 'open'.
R_CENTER_HEAR = R_EFF_MIN
# 18 m hex after centre no_signal. Not a covering of an 80 m disk.
R_HEX_ATTEMPT = 80.0
# Centerline 20 m disk covers the 2° wedge iff r tan(1°) ≤ 20.
# 20 / tan(1°) = 1145.9155902616465 m. A 9-net covering scout has
# r ≤ ρ ≈ 956.05 m < this bound, so ray /clear is a covering there.
R_RAY_CLEAR = R_CLEAR / math.tan(math.radians(ERR_DEG))
# TSP waypoint along a first LOB. Not a range estimate used as a theorem.
R_HAT_LOB = 550.0
# Clarke–Wright / cheapest-insertion gates (metres of extra walk).
# On-the-way 1-bearing: must sit on the covering polyline. A 240 m extra
# still lets a 15° origin ray in; full LOB-home then rebuilds a star.
ON_WAY_EXTRA = 56.0
# Certified SEC (R_sec≤20 / near): insert iff CW savings beat covering-first
# and the detour is not a star. Uncertified 2-bearing SEC centres are tighter.
CERT_EXTRA_MAX = 720.0
SEC_EXTRA_MAX = 380.0
MOW_EXTRA_MAX = 520.0
NEARBY_CERT_M = 280.0
# One-sided linear steps (Beck ray search). 5 d/Δ + Δ/5 is smallest near 110–150 m.
LOB_STEP0 = 70.0
LOB_STEP = 120.0
MAX_LOB_STEPS = 16
# Transverse Alpern amplitude: R_EFF_MAX tan(1°) ≈ 26.18 m. Not a triangulation baseline.
LOB_LATERALS = (18.0, -18.0, 26.0, -26.0, 12.0, -12.0, 34.0, -34.0)
# Shared D-optimal second station for many 2° wedges (Bishop–Fidan was per source).
# Prior ranges along a first LOB for expected log-det FIM / Cauchy–Schwarz info.
DOPT_PRIOR_R = (250.0, 450.0, 650.0, 850.0, 1100.0)
DOPT_FAN_GAP_DEG = 45.0
DOPT_FAN_MAX_WIDTH = 75.0
DOPT_MIN_COLLAPSE = 2
DOPT_MAX_WALK = 920.0
# Dedicated cut must sit on a covering edge (extra≈0). A 560 m extra plus
# an immediate SEC tour rebuilt the polar star (~20 km on the twin).
DOPT_MAX_EXTRA = 120.0
DOPT_SNAP_M = 120.0
# Collapse: two 2° wedges with ψ and range give R_sec ≲ r tan(1°)/sin ψ.
DOPT_COLLAPSE_RSEC = 28.0
DOPT_COLLAPSE_PSI = 28.0


def ring_points(n: int, radius: float, *, phase_rad: float = 0.0) -> list[tuple[float, float]]:
    return [
        (
            radius * math.cos(phase_rad + 2.0 * math.pi * k / n),
            radius * math.sin(phase_rad + 2.0 * math.pi * k / n),
        )
        for k in range(n)
    ]


def q3_scouts() -> list[tuple[float, float]]:
    return q3_omni_scouts()


# Problem 3: N ∈ [10, 16]. After 16 distinct hearings the remaining silent
# channels are empty; leftover 9-net travel is not a covering obligation.
N_Q3_MAX = 16
# Closed 1000 m hearing disk. Residual of a silent channel is the arena
# minus the union of discovery stations' disks.
R_HEAR = R_EFF_MIN
# Membership slack only: a critical point just inside K is not dropped by
# float. This is not a skip license. Skip iff the computed covering radius
# U ≤ R_HEAR. ρ(K) ≤ ρ(K⁺) does not turn ρ(K⁺) ≤ R_HEAR+ε into ρ(K) ≤ R_HEAR.
_RHO_IN_K = 1e-9
# Ulp only, so a self-covered disk with ρ = 1000 + 1 ulp can be dropped.
# Must stay ≪ 5e-7 (hexagon counterexample that forbids 1e-6 skip slack).
_RHO_ULP = 1e-9


def _unique_sites(
    sites: list[tuple[float, float]], *, tol: float = 1e-6
) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for s in sites:
        if any(hypot(s, t) <= tol for t in out):
            continue
        out.append((float(s[0]), float(s[1])))
    return out


def _circumcenter(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> tuple[float, float] | None:
    bx, by = b[0] - a[0], b[1] - a[1]
    cx, cy = c[0] - a[0], c[1] - a[1]
    d = 2.0 * (bx * cy - by * cx)
    if abs(d) < 1e-18:
        return None
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    ux = (cy * b2 - by * c2) / d
    uy = (bx * c2 - cx * b2) / d
    return (a[0] + ux, a[1] + uy)


def _circle_circle_intersections(
    c0: tuple[float, float],
    r0: float,
    c1: tuple[float, float],
    r1: float,
) -> list[tuple[float, float]]:
    d = hypot(c1, c0)
    if d < 1e-15:
        return []
    if d > r0 + r1 + 1e-9 or d < abs(r0 - r1) - 1e-9:
        return []
    a = (r0 * r0 - r1 * r1 + d * d) / (2.0 * d)
    h2 = r0 * r0 - a * a
    if h2 < -1e-6:
        return []
    h = math.sqrt(max(0.0, h2))
    ux, uy = (c1[0] - c0[0]) / d, (c1[1] - c0[1]) / d
    mx, my = c0[0] + a * ux, c0[1] + a * uy
    if h < 1e-12:
        return [(mx, my)]
    vx, vy = -uy, ux
    return [(mx + h * vx, my + h * vy), (mx - h * vx, my - h * vy)]


def _bisector_circle_intersections(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    r: float,
) -> list[tuple[float, float]]:
    mx, my = 0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1e-15:
        return []
    nx, ny = -dy / length, dx / length
    fx, fy = mx - c[0], my - c[1]
    qb = 2.0 * (nx * fx + ny * fy)
    qc = fx * fx + fy * fy - r * r
    disc = qb * qb - 4.0 * qc
    if disc < -1e-6:
        return []
    sdisc = math.sqrt(max(0.0, disc))
    out: list[tuple[float, float]] = []
    for t in ((-qb + sdisc) * 0.5, (-qb - sdisc) * 0.5):
        out.append((mx + t * nx, my + t * ny))
    return out


def _in_disks(
    p: tuple[float, float],
    disks: list[tuple[tuple[float, float], float]],
    *,
    slack: float = _RHO_IN_K,
) -> bool:
    return all(hypot(p, c) <= r + slack for c, r in disks)


def _ds(p: tuple[float, float], sites: list[tuple[float, float]]) -> float:
    return min(hypot(p, s) for s in sites)


def _k_disks(
    center: tuple[float, float], radius: float
) -> list[tuple[tuple[float, float], float]]:
    return [(center, radius), ((0.0, 0.0), ARENA_R)]


def covering_radius_on_disks(
    sites: list[tuple[float, float]],
    disks: list[tuple[tuple[float, float], float]],
) -> tuple[float, tuple[float, float] | None]:
    """Covering radius of finite sites on K = ∩ closed disks.

    ρ = max_{p ∈ K} min_s ||p − s||. Empty sites ⇒ +∞ (K treated nonempty
    for the 9-net disks used here). Critical points of d_S on compact convex
    K are Voronoi vertices in K, Voronoi-edge ∩ ∂K, radial extrema of each
    site on each circular arc of ∂K, and vertices of ∂K. Extra boundary
    samples can only raise the estimate; a missed maximizer underestimates
    ρ, so skip stays U ≤ R_HEAR and uncertain cells are kept. On a Voronoi
    edge interior, d_S^2 is a strictly convex quadratic. Concentric
    site/circle: ||p−s|| is constant on that circle.
    """
    sites = _unique_sites(sites)
    if not disks:
        return 0.0, None
    if not sites:
        c0, r0 = disks[0]
        p0 = c0
        if not _in_disks(p0, disks):
            p0 = (0.0, 0.0)
            if not _in_disks(p0, disks):
                p0 = None
        return float("inf"), p0

    cands: list[tuple[float, float]] = []
    n = len(sites)

    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                cc = _circumcenter(sites[i], sites[j], sites[k])
                if cc is not None and _in_disks(cc, disks):
                    cands.append(cc)

    for i in range(n):
        for j in range(i + 1, n):
            for c, r in disks:
                for p in _bisector_circle_intersections(sites[i], sites[j], c, r):
                    if _in_disks(p, disks):
                        cands.append(p)

    for s in sites:
        for c, r in disks:
            dc = hypot(c, s)
            if dc < 1e-15:
                # ||p − s|| is constant r on this circle; one point suffices
                # for the value, endpoints of Voronoi arcs are already above.
                p_const = (c[0] + r, c[1])
                if _in_disks(p_const, disks):
                    cands.append(p_const)
                continue
            ux, uy = (c[0] - s[0]) / dc, (c[1] - s[1]) / dc
            p_far = (c[0] + r * ux, c[1] + r * uy)
            if _in_disks(p_far, disks):
                cands.append(p_far)

    for i in range(len(disks)):
        for j in range(i + 1, len(disks)):
            (c0, r0), (c1, r1) = disks[i], disks[j]
            for p in _circle_circle_intersections(c0, r0, c1, r1):
                if _in_disks(p, disks):
                    cands.append(p)
        c, r = disks[i]
        if _in_disks(c, disks):
            cands.append(c)

    # Boundary samples: skip-veto / estimate floor, not the completeness argument.
    for c, r in disks:
        n_ang = 72
        for k in range(n_ang):
            ang = 2.0 * math.pi * k / n_ang
            p = (c[0] + r * math.cos(ang), c[1] + r * math.sin(ang))
            if _in_disks(p, disks):
                cands.append(p)

    cands = [p for p in cands if _in_disks(p, disks)]
    if not cands:
        return float("inf"), None

    best_p = cands[0]
    best = _ds(best_p, sites)
    for p in cands[1:]:
        d = _ds(p, sites)
        if d > best:
            best = d
            best_p = p
    return best, best_p


def continuum_residual_radius(
    sites: list[tuple[float, float]],
    *,
    center: tuple[float, float] = (0.0, 0.0),
    radius: float = ARENA_R,
) -> tuple[float, tuple[float, float] | None]:
    """Covering radius of sites on disk(center, radius) ∩ arena."""
    if radius >= ARENA_R - 1e-12 and hypot(center) <= 1e-12:
        disks: list[tuple[tuple[float, float], float]] = [((0.0, 0.0), ARENA_R)]
    else:
        disks = _k_disks(center, radius)
    return covering_radius_on_disks(sites, disks)


def continuum_residual_nonempty(
    sites: list[tuple[float, float]], *, r_hear: float = R_HEAR
) -> bool:
    rho, _w = continuum_residual_radius(sites)
    return rho > r_hear + _RHO_ULP


def scout_meets_residual(
    scout: tuple[float, float],
    sites: list[tuple[float, float]],
    *,
    r_hear: float = R_HEAR,
) -> bool:
    """True iff disk(scout, r_hear) ∩ arena meets the continuum residual."""
    rho, _w = continuum_residual_radius(sites, center=scout, radius=r_hear)
    return rho > r_hear + _RHO_ULP


def pose_covers_scout(
    pose: tuple[float, float],
    scout: tuple[float, float],
    sites: list[tuple[float, float]],
    *,
    r_hear: float = R_HEAR,
) -> bool:
    """True iff disk(scout, r_hear) ∩ arena ⊆ ∪_{S∪{pose}} disk(·, r_hear)."""
    extra = list(sites)
    extra.append(pose)
    rho, _w = continuum_residual_radius(extra, center=scout, radius=r_hear)
    return rho <= r_hear + _RHO_ULP


def q4_scouts() -> list[tuple[float, float]]:
    # Discovery certificate: triangular lattice, covering radius ρ=s/√3<500 m.
    # For every source g and heading u, q=g+500u has a lattice point p with
    # ||p-q||≤ρ, hence ||p-g||≤a+ρ<1000 and (p-g)·u≥a-ρ>0. Time layer:
    # nearest remaining silent-channel scout; fallback is the remaining lattice.
    return q4_certainty_scouts()


def clamp_xy(x: float, y: float, limit: float = 1.9e6) -> tuple[float, float]:
    return (max(-limit, min(limit, x)), max(-limit, min(limit, y)))


def clip_to_arena(p: tuple[float, float], limit: float = ARENA_R) -> tuple[float, float]:
    r = hypot(p)
    if r <= limit or r < 1e-15:
        return p
    s = limit / r
    return (p[0] * s, p[1] * s)


def dist_point_to_segment(
    p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 < 1e-18:
        return hypot(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def tsp_visit_order(
    origin: tuple[float, float], pts: list[tuple[float, float]]
) -> list[int]:
    """Open TSP: origin → each point once. Exact Held–Karp for n≤11, else NN+2-opt."""
    n = len(pts)
    if n == 0:
        return []
    if n == 1:
        return [0]
    if n <= 11:
        return _tsp_held_karp(origin, pts)
    return _tsp_nn_2opt(origin, pts)


def _tsp_held_karp(origin: tuple[float, float], pts: list[tuple[float, float]]) -> list[int]:
    n = len(pts)
    inf = 1e18
    d0 = [hypot(p, origin) for p in pts]
    dist = [[hypot(pts[i], pts[j]) for j in range(n)] for i in range(n)]
    size = 1 << n
    dp = [[inf] * n for _ in range(size)]
    parent = [[-1] * n for _ in range(size)]
    for i in range(n):
        dp[1 << i][i] = d0[i]
    for mask in range(size):
        for j in range(n):
            if not mask & (1 << j):
                continue
            prev = mask ^ (1 << j)
            if prev == 0:
                continue
            best = dp[mask][j]
            best_i = -1
            for i in range(n):
                if not prev & (1 << i):
                    continue
                cand = dp[prev][i] + dist[i][j]
                if cand < best:
                    best = cand
                    best_i = i
            if best_i >= 0:
                dp[mask][j] = best
                parent[mask][j] = best_i
    full = size - 1
    j = min(range(n), key=lambda k: dp[full][k])
    order: list[int] = []
    mask = full
    while j >= 0:
        order.append(j)
        nxt = parent[mask][j]
        mask ^= 1 << j
        j = nxt
    order.reverse()
    return order


def _tsp_nn_2opt(origin: tuple[float, float], pts: list[tuple[float, float]]) -> list[int]:
    n = len(pts)
    remaining = set(range(n))
    order: list[int] = []
    here = origin
    while remaining:
        nxt = min(remaining, key=lambda i: hypot(pts[i], here))
        remaining.remove(nxt)
        order.append(nxt)
        here = pts[nxt]

    def length(seq: list[int]) -> float:
        acc = hypot(pts[seq[0]], origin)
        for a, b in zip(seq, seq[1:]):
            acc += hypot(pts[a], pts[b])
        return acc

    improved = True
    while improved:
        improved = False
        for i in range(n - 1):
            for k in range(i + 1, n):
                cand = order[:i] + list(reversed(order[i : k + 1])) + order[k + 1 :]
                if length(cand) + 1e-9 < length(order):
                    order = cand
                    improved = True
                    break
            if improved:
                break
    return order


@dataclass
class Fix:
    x: float
    y: float
    kind: str
    svd_deg: float | None


@dataclass
class Searcher:
    client: Any
    mixed: bool = False
    log_path: Path | None = None
    max_actions: int = MAX_ACTIONS
    seq: int = 0
    x: float = 0.0
    y: float = 0.0
    radio: int = 1
    actions: int = 0
    cleared: set[int] = field(default_factory=set)
    fixes: dict[int, list[Fix]] = field(default_factory=dict)
    no_signal_scouts: dict[int, int] = field(default_factory=dict)
    no_signal_pts: dict[int, list[tuple[float, float]]] = field(default_factory=dict)
    tried_pts: dict[int, list[tuple[float, float]]] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    last_virtual: float = 0.0
    remaining_real_s: float = 1200.0
    remaining_scouts: list[tuple[float, float]] = field(default_factory=list)
    discovery_stations: list[tuple[float, float]] = field(default_factory=list)
    n_path_scans: int = 0
    n_net_visits: int = 0
    n_savings_inserts: int = 0
    n_dopt_visits: int = 0
    n_dopt_collapses: int = 0
    _dopt_done: set[int] = field(default_factory=set)
    _dopt_tried: list[tuple[float, float]] = field(default_factory=list)
    _dopt_plan: tuple[tuple[float, float], tuple[int, ...]] | None = None
    _rho_cache: dict[tuple, tuple[float, tuple[float, float] | None]] = field(default_factory=dict)

    def _rid(self, prefix: str) -> str:
        self.seq += 1
        return f"{prefix}-{self.seq}"

    def _record(self, path: str, payload: dict[str, Any], body: dict[str, Any]) -> None:
        row = {"path": path, "request": payload, "response": body}
        self.trace.append(row)
        if body.get("accepted") and "virtual_time_s" in body:
            self.last_virtual = float(body["virtual_time_s"])
        if self.log_path is not None:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _too_many(self) -> bool:
        return self.actions >= self.max_actions

    def enter(self) -> dict[str, Any]:
        rid = self._rid("enter")
        body = self.client.enter(rid)
        self.actions += 1
        self._record("/enter", {"request_id": rid}, body)
        if body.get("accepted"):
            self.remaining_real_s = float(body.get("remaining_real_duration_s") or 1200)
            self.x, self.y, self.radio = 0.0, 0.0, 1
        return body

    def exit(self) -> dict[str, Any]:
        rid = self._rid("exit")
        body = self.client.exit(rid)
        self.actions += 1
        self._record("/exit", {"request_id": rid}, body)
        return body

    def measure_at(self, x: float, y: float, channel: int) -> dict[str, Any]:
        x, y = clamp_xy(x, y)
        rid = self._rid("m")
        body = self.client.measure(rid, x, y, int(channel))
        self.actions += 1
        self._record("/measure", {"request_id": rid, "x": x, "y": y, "channel": channel}, body)
        if body.get("accepted"):
            self.x, self.y = x, y
            self.radio = int(channel)
            self._ingest(int(channel), body, x, y)
            self.tried_pts.setdefault(int(channel), []).append((x, y))
        return body

    def clear_at(self, x: float, y: float, channel: int) -> dict[str, Any]:
        x, y = clamp_xy(x, y)
        rid = self._rid("c")
        body = self.client.clear(rid, x, y, int(channel))
        self.actions += 1
        self._record("/clear", {"request_id": rid, "x": x, "y": y, "channel": channel}, body)
        if body.get("accepted"):
            self.x, self.y = x, y
            if body.get("clear_result") == "success":
                self.cleared.add(int(channel))
                self.fixes.pop(int(channel), None)
        return body

    def _ingest(self, channel: int, body: dict[str, Any], x: float, y: float) -> None:
        kind = body.get("measure_result")
        if kind == "near":
            self.fixes.setdefault(channel, []).append(Fix(x, y, "near", None))
        elif kind == "direction":
            svd = float(body["svd_deg"])
            self.fixes.setdefault(channel, []).append(Fix(x, y, "direction", svd))
        elif kind == "no_signal":
            self.no_signal_scouts[channel] = self.no_signal_scouts.get(channel, 0) + 1
            self.no_signal_pts.setdefault(channel, []).append((x, y))

    def remaining_channels(self) -> list[int]:
        return [c for c in range(1, 21) if c not in self.cleared]

    def _order_channels(self, channels: list[int]) -> list[int]:
        # Prefer current radio to avoid a 1 s switch, then numeric order.
        return sorted(channels, key=lambda c: (0 if c == self.radio else 1, c))

    def _poly_for(self, channel: int) -> list[tuple[float, float]]:
        dirs = [fx for fx in self.fixes.get(channel, []) if fx.kind == "direction" and fx.svd_deg is not None]
        if len(dirs) < 1:
            return []
        stations = [(fx.x, fx.y) for fx in dirs]
        bearings = [float(fx.svd_deg) for fx in dirs]
        balls = [R_EFF_MAX] * len(dirs)
        poly = intersect_wedges(stations, bearings, err_deg=ERR_DEG, clip_arena=True, range_balls=balls)
        if polygon_unbounded(poly) or len(poly) < 3:
            poly = intersect_wedges(stations, bearings, err_deg=ERR_DEG, clip_arena=True)
        return poly

    def _choose_offset(self, s: tuple[float, float], theta: float) -> tuple[float, float]:
        a = second_station_point(s, theta, R_DESIGN, T_DESIGN)
        b = second_station_point(s, theta, R_DESIGN, -T_DESIGN)
        # Prefer the candidate closer to the current robot and not far outside the arena.
        def score(p: tuple[float, float]) -> float:
            outside = max(0.0, hypot(p) - ARENA_R)
            return hypot(p, (self.x, self.y)) + 2.0 * outside

        return a if score(a) <= score(b) else b

    def _reflect_across_lob(self, fx: Fix, p: tuple[float, float]) -> tuple[float, float]:
        s = (fx.x, fx.y)
        u = bearing_vec(float(fx.svd_deg))
        v = left_normal(u)
        d = (p[0] - s[0], p[1] - s[1])
        r = d[0] * u[0] + d[1] * u[1]
        t = d[0] * v[0] + d[1] * v[1]
        return clip_to_arena(second_station_point(s, float(fx.svd_deg), r, -t))

    def _defer_second_to_scout(self, channel: int) -> bool:
        """True iff a remaining 9-net scout can still take a free second bearing."""
        for scout in self.remaining_scouts:
            if self._incidental_second_useful(scout, channel):
                return True
        return False

    def _travel_optimal_second(self, fx: Fix, channel: int) -> tuple[float, float]:
        """Nearest second station that can bound Ω, not the Q2 (800, 700) cover.

        Bishop–Fidan: 90° at G is CRLB-optimal. Travel-optimal is a short
        (r, t) on the way to G_hat whose two-wedge R_sec is small enough
        that the SEC remeasure finishes the 20 m certificate. (800, 700)
        is the fallback covering point, scored last because hypot=1063 m.
        """
        s = (fx.x, fx.y)
        theta = float(fx.svd_deg)
        u = bearing_vec(theta)
        here = (self.x, self.y)
        g_hats = [
            clip_to_arena((s[0] + r * u[0], s[1] + r * u[1]))
            for r in (250.0, 450.0, 650.0, 850.0, 1050.0)
        ]
        cands: list[tuple[float, float]] = []
        for r in (200.0, 350.0, 500.0, 650.0, 800.0):
            for t in (70.0, -70.0, 120.0, -120.0):
                cands.append(clip_to_arena(second_station_point(s, theta, r, t)))
        for t in (160.0, -160.0, 240.0, -240.0):
            cands.append(clip_to_arena(second_station_point(s, theta, 0.0, t)))
        cands.append(clip_to_arena(second_station_point(s, theta, R_DESIGN, T_DESIGN)))
        cands.append(clip_to_arena(second_station_point(s, theta, R_DESIGN, -T_DESIGN)))

        best: tuple[float, float] | None = None
        best_score = 1e18
        for p in cands:
            if hypot(p, s) < 50.0:
                continue
            if self._already_tried(channel, p[0], p[1], tol=40.0):
                continue
            walk = hypot(p, here)
            outside = max(0.0, hypot(p) - ARENA_R)
            rsecs: list[float] = []
            two_steps: list[float] = []
            heard = 0
            for g in g_hats:
                d2 = hypot(p, g)
                two_steps.append(walk + d2)
                if d2 <= R_EFF_MIN + 50.0:
                    heard += 1
                th2 = bearing_deg(g, p)
                poly = intersect_wedges(
                    [s, p],
                    [theta, th2],
                    err_deg=ERR_DEG,
                    clip_arena=True,
                    range_balls=[R_EFF_MAX, R_EFF_MAX],
                )
                if len(poly) >= 3:
                    rsecs.append(smallest_enclosing_circle(poly).radius)
            hear_frac = heard / max(1, len(g_hats))
            rsec_p = sorted(rsecs)[len(rsecs) // 2] if rsecs else 800.0
            two_step = sorted(two_steps)[len(two_steps) // 2] if two_steps else walk + 800.0
            # Two-step travel (S2 then G_hat), not one-step walk. A nearby
            # poor-ψ lateral plus a long SEC hop is how (800,700) wasted a km.
            score = two_step + 2.0 * outside + 0.2 * rsec_p + 250.0 * (1.0 - hear_frac)
            if score < best_score:
                best_score = score
                best = p
        if best is None:
            return self._choose_offset(s, theta)
        return best

    def _already_tried(self, channel: int, x: float, y: float, *, tol: float = 20.0) -> bool:
        for px, py in self.tried_pts.get(int(channel), []):
            if hypot((x, y), (px, py)) <= tol:
                return True
        return False

    def _measure_new(self, x: float, y: float, channel: int) -> dict[str, Any] | None:
        if self._too_many() or channel in self.cleared:
            return None
        if self._already_tried(channel, x, y):
            return None
        return self.measure_at(x, y, channel)

    def _silent_channels(self) -> list[int]:
        return [c for c in self.remaining_channels() if c not in self.fixes]

    def _sector_preserving_second(self, channel: int, fx: Fix) -> bool:
        """Short along-track + lateral second station, with a lobe hypothesis.

        P(t)=S+t v stays in the closed 180° lobe for all t iff v ⊥ H
        (exact LOB and H parallel to S-G). A finite |t| otherwise leaves
        the lobe; on no_signal flip the 180° side immediately.
        """
        theta = float(fx.svd_deg)
        s = (fx.x, fx.y)
        # Exterior first-hit: G is inward along the LOB; keep the second station
        # on the outer half-plane. Interior first-hit: short along-track + lateral.
        if hypot(s) >= ARENA_R - 1e-6:
            plan = [
                (80.0, 450.0),
                (80.0, -450.0),
                (0.0, 550.0),
                (0.0, -550.0),
                (160.0, 300.0),
                (160.0, -300.0),
                (250.0, 0.0),
            ]
        else:
            plan = [
                (150.0, 400.0),
                (150.0, -400.0),
                (60.0, 500.0),
                (60.0, -500.0),
                (250.0, 200.0),
                (250.0, -200.0),
                (100.0, 0.0),
            ]
        first = sorted(
            plan[:2],
            key=lambda rt: hypot(second_station_point(s, theta, rt[0], rt[1]), (self.x, self.y)),
        )
        progressed = False
        for r, t in first + plan[2:]:
            p = second_station_point(s, theta, r, t)
            body = self._measure_new(p[0], p[1], channel)
            if body is None:
                continue
            progressed = True
            kind = body.get("measure_result")
            if kind == "near":
                self.clear_at(p[0], p[1], channel)
                return True
            if kind == "direction":
                return True
            # no_signal: this (r,t) left the lobe or the range; flip side.
        return progressed

    def _lateral_break_collinear(self, channel: int, fx: Fix) -> bool:
        theta = float(fx.svd_deg)
        s = (fx.x, fx.y)
        progressed = False
        for t in (500.0, -500.0, 350.0, -350.0, 700.0, -700.0):
            p = second_station_point(s, theta, 0.0, t)
            body = self._measure_new(p[0], p[1], channel)
            if body is None:
                continue
            progressed = True
            kind = body.get("measure_result")
            if kind == "near":
                self.clear_at(p[0], p[1], channel)
                return True
            if kind == "direction":
                svd = body.get("svd_deg")
                if svd is not None and ang_dist_deg(float(svd), theta) >= 8.0:
                    return True
        return progressed

    def _lobe_home(self, channel: int, fx: Fix) -> None:
        u = bearing_vec(float(fx.svd_deg))
        last_hit = (fx.x, fx.y)
        for dist in (120.0, 250.0, 400.0, 600.0, 850.0, 1100.0):
            if self._too_many() or channel in self.cleared:
                return
            p = (fx.x + dist * u[0], fx.y + dist * u[1])
            body = self._measure_new(p[0], p[1], channel)
            if body is None:
                continue
            kind = body.get("measure_result")
            if kind == "near":
                self.clear_at(p[0], p[1], channel)
                return
            if kind == "direction":
                last_hit = p
                continue
            mid = ((last_hit[0] + p[0]) * 0.5, (last_hit[1] + p[1]) * 0.5)
            self.clear_at(mid[0], mid[1], channel)
            if channel in self.cleared:
                return
            self.clear_at(last_hit[0], last_hit[1], channel)
            return
        if channel not in self.cleared:
            self.clear_at(last_hit[0], last_hit[1], channel)

    def _try_poly_clear(self, channel: int) -> str:
        """Return 'cleared', 'retry', or 'open'.

        Certified clearance is R_sec ≤ 20 m (or a covering diametral disk of
        radius ≤ 20 m) at that centre. If 20 < R_sec ≤ R_CENTER_HEAR, remeasure
        at the SEC centre: an omni source in Ω must be heard. Direction folds
        a new wedge and returns 'retry'; near clears. no_signal is a mixed /
        clip mismatch: the 18 m hex is attempted only when R_sec ≤ 80 m and
        does not cover that disk. If the polygon is still larger than
        R_CENTER_HEAR, return 'open' so the caller adds a station. Force-clear
        at the SEC centre when R_sec > 20 m is not this function's job.
        """
        poly = self._poly_for(channel)
        if len(poly) < 3:
            return "open"
        sec = smallest_enclosing_circle(poly)
        dinfo = diametral_circle_covers_any(poly)
        if sec.radius <= R_CLEAR + 1e-6:
            self.clear_at(sec.center[0], sec.center[1], channel)
            return "cleared" if channel in self.cleared else "open"
        if dinfo["covers"] and 0.5 * float(dinfo["diameter"]) <= R_CLEAR + 1e-6:
            self.clear_at(float(dinfo["center_x"]), float(dinfo["center_y"]), channel)
            return "cleared" if channel in self.cleared else "open"
        if sec.radius <= R_CENTER_HEAR + 1e-6:
            body = self.measure_at(sec.center[0], sec.center[1], channel)
            if body.get("measure_result") == "near":
                self.clear_at(sec.center[0], sec.center[1], channel)
                return "cleared" if channel in self.cleared else "open"
            if body.get("measure_result") == "direction":
                return "retry"
            if sec.radius <= R_HEX_ATTEMPT + 1e-6:
                self.clear_at(sec.center[0], sec.center[1], channel)
                if channel in self.cleared:
                    return "cleared"
                for k in range(6):
                    ang = 2.0 * math.pi * k / 6.0
                    px = sec.center[0] + 18.0 * math.cos(ang)
                    py = sec.center[1] + 18.0 * math.sin(ang)
                    self.clear_at(px, py, channel)
                    if channel in self.cleared or self._too_many():
                        return "cleared" if channel in self.cleared else "open"
            return "open"
        return "open"

    def _take_second_station(self, channel: int, fx: Fix) -> dict[str, Any] | None:
        """Walk to a travel-optimal second station; flip side on no_signal."""
        s2 = self._travel_optimal_second(fx, channel)
        body = self._measure_new(s2[0], s2[1], channel)
        if body is None:
            # Already tried that point; fall back to the Q2 covering hop.
            s2 = self._choose_offset((fx.x, fx.y), float(fx.svd_deg))
            body = self._measure_new(s2[0], s2[1], channel)
            if body is None:
                return None
        if body.get("measure_result") == "no_signal":
            other = self._reflect_across_lob(fx, s2)
            if hypot(other, s2) > 1.0:
                flipped = self._measure_new(other[0], other[1], channel)
                if flipped is not None:
                    body = flipped
            if body.get("measure_result") == "no_signal":
                u = bearing_vec(float(fx.svd_deg))
                for dist in (400.0, 700.0, 1000.0):
                    hx = fx.x + dist * u[0]
                    hy = fx.y + dist * u[1]
                    along = self._measure_new(hx, hy, channel)
                    if along is None:
                        continue
                    body = along
                    if along.get("measure_result") != "no_signal":
                        break
        return body

    def _ray_foot(
        self,
        s: tuple[float, float],
        u: tuple[float, float],
        *,
        r_min: float = 0.0,
        r_max: float = R_EFF_MAX,
    ) -> tuple[tuple[float, float], float]:
        here = (self.x, self.y)
        r = (here[0] - s[0]) * u[0] + (here[1] - s[1]) * u[1]
        r = max(r_min, min(r_max, r))
        p = clip_to_arena((s[0] + r * u[0], s[1] + r * u[1]))
        return p, r

    def _lob_home(self, channel: int, join: tuple[float, float] | None = None) -> None:
        """One-sided expanding search along the latest omni LOB.

        A first omni bearing at S puts G in the 2° wedge. The geodesic from
        S to G is the ray, not a perpendicular station. Clearance is still
        the 20 m disk: centerline covers the wedge when r ≤ R_RAY_CLEAR;
        otherwise a 1-D Alpern search on the transverse of amplitude
        r tan(1°) ≤ 26.2 m covers the sliver.

        `join` is the clustered-TSP waypoint on the ray (typically S +
        R_HAT_LOB u). Homing starts there so the tour does not collapse
        to a star through S.
        """
        if channel in self.cleared or self._too_many():
            return
        fixes = list(self.fixes.get(channel, []))
        near = [fx for fx in fixes if fx.kind == "near"]
        if near:
            self.clear_at(near[-1].x, near[-1].y, channel)
            return
        dirs = [fx for fx in fixes if fx.kind == "direction" and fx.svd_deg is not None]
        if not dirs:
            return
        if len(dirs) >= 2:
            status = self._try_poly_clear(channel)
            if status == "cleared":
                return
            if status == "retry":
                dirs = [
                    fx
                    for fx in self.fixes.get(channel, [])
                    if fx.kind == "direction" and fx.svd_deg is not None
                ]
                if not dirs:
                    return
        fx = dirs[-1]
        if join is not None:
            body = self._measure_new(join[0], join[1], channel)
            if body is not None:
                keep, last, theta = self._lob_consume(
                    channel, (fx.x, fx.y), join, body, float(fx.svd_deg)
                )
                if not keep:
                    self._path_sensor_scan(waypoint=True)
                    return
                # Path-as-sensor: this LOB waypoint is a 1000 m disk.
                self._path_sensor_scan(waypoint=True)
                dirs2 = [
                    fx2
                    for fx2 in self.fixes.get(channel, [])
                    if fx2.kind == "direction" and fx2.svd_deg is not None
                ]
                if len(dirs2) >= 2:
                    status = self._try_poly_clear(channel)
                    if channel in self.cleared:
                        self._path_sensor_scan(waypoint=True)
                        return
                    if status == "retry":
                        dirs2 = [
                            fx2
                            for fx2 in self.fixes.get(channel, [])
                            if fx2.kind == "direction" and fx2.svd_deg is not None
                        ]
                        if dirs2:
                            last = (dirs2[-1].x, dirs2[-1].y)
                            theta = float(dirs2[-1].svd_deg)
                self._lob_expand(channel, Fix(last[0], last[1], "direction", theta), skip_join=True)
                self._path_sensor_scan(waypoint=True)
                return
        self._lob_expand(channel, fx)
        self._path_sensor_scan(waypoint=True)

    def _lob_expand(self, channel: int, fx: Fix, *, skip_join: bool = False) -> None:
        s = (fx.x, fx.y)
        theta = float(fx.svd_deg)
        u = bearing_vec(theta)
        last = s
        if not skip_join:
            foot, r_foot = self._ray_foot(s, u)
            if r_foot >= 15.0:
                if hypot((self.x, self.y), foot) > 8.0:
                    body = self._measure_new(foot[0], foot[1], channel)
                    if body is not None:
                        keep, last, theta = self._lob_consume(channel, last, foot, body, theta)
                        if not keep:
                            return
                    else:
                        last = foot
                else:
                    last = foot
        s0 = s
        step = LOB_STEP0
        for _ in range(MAX_LOB_STEPS):
            if self._too_many() or channel in self.cleared:
                return
            u = bearing_vec(theta)
            raw = (last[0] + step * u[0], last[1] + step * u[1])
            if hypot(raw) > ARENA_R - 1.0 or hypot(raw, s0) > R_EFF_MAX + 80.0:
                self.clear_at(last[0], last[1], channel)
                if channel not in self.cleared:
                    self._lob_laterals(channel, last, theta)
                return
            p = clip_to_arena(raw)
            if hypot(p, last) < 8.0:
                self._lob_laterals(channel, last, theta)
                return
            body = self._measure_new(p[0], p[1], channel)
            if body is None:
                step = min(200.0, step * 1.3)
                continue
            keep, last, theta = self._lob_consume(channel, last, p, body, theta)
            if not keep:
                return
            step = min(LOB_STEP, max(LOB_STEP0, step * 1.2))
        if channel not in self.cleared:
            self.clear_at(last[0], last[1], channel)
            if channel not in self.cleared:
                self._lob_laterals(channel, last, theta)

    def _lob_consume(
        self,
        channel: int,
        last: tuple[float, float],
        p: tuple[float, float],
        body: dict[str, Any],
        theta: float,
    ) -> tuple[bool, tuple[float, float], float]:
        """Forward along the ray? Else localize the pass and stop."""
        kind = body.get("measure_result")
        if kind == "near":
            self.clear_at(p[0], p[1], channel)
            return False, p, theta
        if kind == "no_signal":
            self._lob_after_pass(channel, last, p, theta, svd_at_b=None)
            return False, last, theta
        if kind == "direction":
            svd = float(body["svd_deg"])
            travel = bearing_deg(p, last) if hypot(p, last) > 1e-6 else theta
            turn = ang_dist_deg(svd, travel)
            if turn >= 75.0:
                self._lob_after_pass(channel, last, p, theta, svd_at_b=svd)
                return False, p, svd
            return True, p, svd
        return True, last, theta

    def _lob_after_pass(
        self,
        channel: int,
        a: tuple[float, float],
        b: tuple[float, float],
        theta_forward: float,
        svd_at_b: float | None,
    ) -> None:
        """Binary search the last forward–pass interval, then 20 m clears.

        G's projection on the ray lies between the last forward hearing and
        the first flipped / no_signal station. Midpoint /clear of a 120 m
        interval can still sit 27 m past G; shrinking the interval first
        is the 1-D search.
        """
        if channel in self.cleared or self._too_many():
            return
        lo, hi = a, b
        last_fwd = a
        last_theta = theta_forward
        for _ in range(8):
            if channel in self.cleared or self._too_many():
                return
            if hypot(lo, hi) <= 22.0:
                break
            mid = ((lo[0] + hi[0]) * 0.5, (lo[1] + hi[1]) * 0.5)
            body = self._measure_new(mid[0], mid[1], channel)
            if body is None:
                hi = mid
                continue
            kind = body.get("measure_result")
            if kind == "near":
                self.clear_at(mid[0], mid[1], channel)
                return
            if kind == "no_signal":
                hi = mid
                continue
            svd = float(body["svd_deg"])
            turn = ang_dist_deg(svd, theta_forward)
            if turn >= 75.0:
                hi = mid
                if svd_at_b is None:
                    svd_at_b = svd
            else:
                lo = mid
                last_fwd = mid
                last_theta = svd
        mid = ((lo[0] + hi[0]) * 0.5, (lo[1] + hi[1]) * 0.5)
        for q in (mid, last_fwd, lo, hi):
            self.clear_at(q[0], q[1], channel)
            if channel in self.cleared or self._too_many():
                return
        self._lob_terminal(
            channel,
            last_fwd,
            last_theta,
            budget_m=max(36.0, hypot(lo, hi) + 24.0),
        )
        if channel not in self.cleared:
            self._lob_laterals(channel, mid, last_theta)

    def _lob_terminal(
        self,
        channel: int,
        origin: tuple[float, float],
        theta: float,
        *,
        budget_m: float = 180.0,
    ) -> None:
        """Short pursuit along a bearing that already points at G."""
        if channel in self.cleared or self._too_many():
            return
        last = origin
        walked = 0.0
        step = 18.0
        u = bearing_vec(theta)
        while walked < budget_m and not self._too_many() and channel not in self.cleared:
            p = clip_to_arena((last[0] + step * u[0], last[1] + step * u[1]))
            if hypot(p, last) < 4.0:
                break
            body = self._measure_new(p[0], p[1], channel)
            if body is None:
                self.clear_at(p[0], p[1], channel)
                if channel in self.cleared:
                    return
                last = p
                walked += step
                continue
            kind = body.get("measure_result")
            if kind == "near":
                self.clear_at(p[0], p[1], channel)
                return
            if kind == "direction":
                svd = float(body["svd_deg"])
                travel = bearing_deg(p, last) if hypot(p, last) > 1e-6 else theta
                turn = ang_dist_deg(svd, travel)
                if turn >= 45.0 or hypot(p, last) <= 22.0:
                    self.clear_at(p[0], p[1], channel)
                    if channel in self.cleared:
                        return
                if turn >= 75.0:
                    self._lob_laterals(channel, last, theta)
                    return
                last = p
                theta = svd
                u = bearing_vec(theta)
                walked += step
                continue
            self.clear_at(last[0], last[1], channel)
            if channel not in self.cleared:
                self._lob_laterals(channel, last, theta)
            return
        if channel not in self.cleared:
            self.clear_at(last[0], last[1], channel)

    def _lob_laterals(self, channel: int, p: tuple[float, float], theta: float) -> None:
        """1-D expanding search on the left-normal. Amplitude ≤ R_EFF_MAX tan(1°)."""
        if channel in self.cleared or self._too_many():
            return
        self.clear_at(p[0], p[1], channel)
        if channel in self.cleared:
            return
        for t in LOB_LATERALS:
            if self._too_many() or channel in self.cleared:
                return
            q = second_station_point(p, theta, 0.0, t)
            if hypot(q) > ARENA_R + 1e-6:
                continue
            if hypot(q, p) < 4.0:
                continue
            body = self._measure_new(q[0], q[1], channel)
            if body is not None and body.get("measure_result") == "near":
                self.clear_at(q[0], q[1], channel)
                return
            self.clear_at(q[0], q[1], channel)
            if channel in self.cleared:
                return
            if body is not None and body.get("measure_result") == "direction":
                svd = float(body["svd_deg"])
                if ang_dist_deg(svd, theta) >= 8.0:
                    u = bearing_vec(svd)
                    r = clip_to_arena((q[0] + 18.0 * u[0], q[1] + 18.0 * u[1]))
                    self.clear_at(r[0], r[1], channel)
                    if channel in self.cleared:
                        return

    def _chase_omni(self, channel: int) -> None:
        """Omni chase is LOB homing. No perpendicular triangulation station.

        One bearing: Beck one-sided search along the measured ray until near,
        a 20 m clear, or a bearing flip. Two or more bearings: fold Ω and
        /clear if R_sec ≤ 20 m; otherwise still home along the latest LOB.
        (800, 700) is not this path. After MAX_CHASE_ITERS the last-hit
        /clear is an action-budget last resort, not the covering certificate.
        """
        if self._too_many() or channel in self.cleared:
            return
        fixes = list(self.fixes.get(channel, []))
        if not fixes:
            return
        near = [fx for fx in fixes if fx.kind == "near"]
        if near:
            self.clear_at(near[-1].x, near[-1].y, channel)
            return
        dirs = [fx for fx in fixes if fx.kind == "direction" and fx.svd_deg is not None]
        if not dirs:
            return
        self._lob_home(channel)
        if channel in self.cleared or self._too_many():
            return
        dirs = [fx for fx in self.fixes.get(channel, []) if fx.kind == "direction" and fx.svd_deg is not None]
        if dirs:
            last = dirs[-1]
            u = bearing_vec(float(last.svd_deg))
            self.clear_at(last.x + 15.0 * u[0], last.y + 15.0 * u[1], channel)

    def _chase_mixed(self, channel: int) -> None:
        """Mixed chase. Clearance certificate is still R_sec ≤ 20 m.

        One bearing: sector-preserving short along-track + lateral, flip side
        on no_signal. Two nearly collinear bearings: pure lateral. Otherwise
        fold Ω; if _try_poly_clear returns open, take another sector-preserving
        station from the latest LOB rather than force-clearing a large Ω.
        Along-track homing is the last geometric means inside the lobe, not
        the covering certificate. After MAX_CHASE_ITERS the SEC-centre /clear
        is an action-budget last resort.
        """
        for _ in range(MAX_CHASE_ITERS):
            if self._too_many() or channel in self.cleared:
                return
            fixes = list(self.fixes.get(channel, []))
            if not fixes:
                return
            near = [fx for fx in fixes if fx.kind == "near"]
            if near:
                self.clear_at(near[-1].x, near[-1].y, channel)
                return
            dirs = [fx for fx in fixes if fx.kind == "direction" and fx.svd_deg is not None]
            if not dirs:
                return
            if len(dirs) == 1:
                moved = self._sector_preserving_second(channel, dirs[0])
                if channel in self.cleared:
                    return
                if not moved:
                    self._lobe_home(channel, dirs[0])
                    return
                continue
            if ang_dist_deg(float(dirs[-1].svd_deg), float(dirs[-2].svd_deg)) < 8.0:
                moved = self._lateral_break_collinear(channel, dirs[-1])
                if channel in self.cleared:
                    return
                if not moved:
                    self._lobe_home(channel, dirs[-1])
                    return
                continue
            status = self._try_poly_clear(channel)
            if status == "cleared":
                return
            if status == "retry":
                continue
            moved = self._sector_preserving_second(channel, dirs[-1])
            if channel in self.cleared:
                return
            if not moved:
                self._lobe_home(channel, dirs[-1])
                return
        poly = self._poly_for(channel)
        if len(poly) >= 3:
            sec = smallest_enclosing_circle(poly)
            self.clear_at(sec.center[0], sec.center[1], channel)
            if channel in self.cleared:
                return
            if sec.radius <= 80.0:
                self._optical_grid_clear(sec.center, sec.radius, channel)
                if channel in self.cleared:
                    return
        dirs = [fx for fx in self.fixes.get(channel, []) if fx.kind == "direction" and fx.svd_deg is not None]
        if dirs:
            self._lobe_home(channel, dirs[-1])

    def chase(self, channel: int) -> None:
        if self.mixed:
            self._chase_mixed(channel)
            return
        self._chase_omni(channel)

    def _exterior_first(self, pt: tuple[float, float]) -> None:
        """Silent remaining channels at a lattice scout.

        A single no_signal does not kill the channel. Discovery certificate
        is the covering lattice; nearest remaining is the time layer.
        """
        silent = self._silent_channels()
        self.scan_point(pt, silent)

    def scan_point(
        self,
        pt: tuple[float, float],
        channels: list[int] | None = None,
        *,
        chase: bool = True,
    ) -> None:
        if channels is None:
            channels = self.remaining_channels()
            if self.mixed:
                # Silent-channel lattice: interior no_signal does not kill
                # the channel; remaining lattice points are spent on radios
                # that still have no bearing.
                channels = [c for c in channels if c not in self.fixes]
        chs = self._order_channels(channels)
        for ch in chs:
            if self._too_many():
                return
            if ch in self.cleared:
                continue
            body = self.measure_at(pt[0], pt[1], ch)
            if ch in self.cleared:
                continue
            # near ⇒ G is already at this waypoint; /clear costs 5 s and no walk.
            if body.get("measure_result") == "near":
                self.clear_at(pt[0], pt[1], ch)
                continue
            if chase and ch in self.fixes and ch not in self.cleared:
                self.chase(ch)

    def _optical_grid_clear(
        self, center: tuple[float, float], radius: float, channel: int
    ) -> None:
        """25 m squares: circumradius 25/√2≈17.68<20, so a hit in the cell is a clear."""
        step = 25.0
        if radius > 80.0 or self._too_many():
            return
        n = int(math.ceil(2.0 * radius / step)) + 1
        x0, y0 = center[0] - radius, center[1] - radius
        for i in range(n):
            for j in range(n):
                if self._too_many() or channel in self.cleared:
                    return
                x, y = x0 + (i + 0.5) * step, y0 + (j + 0.5) * step
                if hypot((x, y), center) > radius + step / math.sqrt(2.0):
                    continue
                self.clear_at(x, y, channel)

    def _nearest_index(self, pts: list[tuple[float, float]]) -> int:
        here = (self.x, self.y)
        return min(range(len(pts)), key=lambda i: hypot(pts[i], here))

    def _n_found(self) -> int:
        return len(set(self.fixes.keys()) | set(self.cleared))

    def _mark_discovery(self, pt: tuple[float, float]) -> None:
        for prev in self.discovery_stations:
            if hypot(pt, prev) <= 1.0:
                return
        self.discovery_stations.append(pt)
        self._rho_cache.clear()

    def _rho(
        self,
        sites: list[tuple[float, float]],
        *,
        center: tuple[float, float] = (0.0, 0.0),
        radius: float = ARENA_R,
    ) -> tuple[float, tuple[float, float] | None]:
        key = (
            tuple((round(s[0], 6), round(s[1], 6)) for s in sites),
            (round(center[0], 6), round(center[1], 6)),
            round(radius, 6),
        )
        hit = self._rho_cache.get(key)
        if hit is not None:
            return hit
        val = continuum_residual_radius(sites, center=center, radius=radius)
        self._rho_cache[key] = val
        return val

    def _continuum_residual_nonempty(self) -> bool:
        rho, _w = self._rho(self.discovery_stations)
        return rho > R_HEAR + _RHO_ULP

    def _scout_meets_residual(self, scout: tuple[float, float]) -> bool:
        rho, _w = self._rho(self.discovery_stations, center=scout, radius=R_HEAR)
        return rho > R_HEAR + _RHO_ULP

    def _pose_meets_residual(self, pt: tuple[float, float]) -> bool:
        rho, _w = self._rho(self.discovery_stations, center=pt, radius=R_HEAR)
        return rho > R_HEAR + _RHO_ULP

    def _pose_covers_scout(self, pt: tuple[float, float], scout: tuple[float, float]) -> bool:
        sites = list(self.discovery_stations)
        sites.append(pt)
        rho, _w = self._rho(sites, center=scout, radius=R_HEAR)
        return rho <= R_HEAR + _RHO_ULP

    def _scout_leftover_witness(
        self, scout: tuple[float, float]
    ) -> tuple[float, tuple[float, float] | None]:
        return self._rho(self.discovery_stations, center=scout, radius=R_HEAR)

    def _prune_scouts(self) -> None:
        """Drop a 9-net scout iff its 1000 m disk misses the continuum residual.

        Residual is arena minus ∪ disk(S, 1000) over discovery stations that
        actually scanned leftover silent channels. Empty finite samples are
        not this test. The 9-net is also finished when every remaining live
        channel has a bearing, or when N=16 hearings have used the problem
        bound.
        """
        if self._n_found() >= N_Q3_MAX or not self._silent_channels():
            self.remaining_scouts = []
            return
        if not self._continuum_residual_nonempty():
            self.remaining_scouts = []
            return
        kept: list[tuple[float, float]] = []
        for scout in self.remaining_scouts:
            if self._scout_meets_residual(scout):
                kept.append(scout)
        self.remaining_scouts = kept

    def _certificate_fallback_scouts(self) -> None:
        """Restore unused 9-net points that still meet the continuum residual."""
        if not self._silent_channels() or self._n_found() >= N_Q3_MAX:
            return
        if not self._continuum_residual_nonempty():
            return
        have = list(self.remaining_scouts)
        for scout in q3_scouts():
            if any(hypot(scout, h) <= 1e-6 for h in have):
                continue
            if self._scout_meets_residual(scout):
                self.remaining_scouts.append(scout)

    def _covering_waypoint(self, scout: tuple[float, float]) -> tuple[float, float]:
        """Nearest cheap pose that continuum-covers this scout's leftover.

        disk(scout, 1000) ∩ arena is always covered by the scout center, so
        the scout is the certified fallback. Other candidates (here, the
        here→scout segment, the here→witness ray) are a time layer: they
        are used only when pose_covers_scout is true.
        """
        here = (self.x, self.y)
        if self._pose_covers_scout(here, scout):
            return here
        rho, witness = self._scout_leftover_witness(scout)
        cands: list[tuple[float, float]] = [scout]
        if hypot(here, scout) >= 1e-9:
            for i in range(25):
                t = i / 24.0
                cands.append(
                    clip_to_arena(
                        (
                            here[0] + t * (scout[0] - here[0]),
                            here[1] + t * (scout[1] - here[1]),
                        )
                    )
                )
        if witness is not None and rho > R_HEAR + _RHO_ULP:
            d = hypot(here, witness)
            if d <= R_HEAR + 1e-9:
                cands.append(here)
            elif d > 1e-9:
                t_enter = (d - R_HEAR) / d
                cands.append(
                    clip_to_arena(
                        (
                            here[0] + t_enter * (witness[0] - here[0]),
                            here[1] + t_enter * (witness[1] - here[1]),
                        )
                    )
                )
                for t in (0.35, 0.55, 0.75, 0.9, 1.0):
                    cands.append(
                        clip_to_arena(
                            (
                                here[0] + t * (witness[0] - here[0]),
                                here[1] + t * (witness[1] - here[1]),
                            )
                        )
                    )
        # Time layer: a 1-bearing LOB sample or 2-bearing SEC that already
        # continuum-covers this cell can replace the ring centre.
        for ch, s, theta in self._one_bearing_items(set()):
            u = bearing_vec(theta)
            for r in (450.0, 700.0, 950.0, 1200.0):
                cands.append(clip_to_arena((s[0] + r * u[0], s[1] + r * u[1])))
            post = self._posterior_centroid(ch)
            if post is not None:
                cands.append(post)
        for ch in list(self.fixes.keys()):
            if ch in self.cleared:
                continue
            poly = self._poly_for(ch)
            if len(poly) >= 3:
                cands.append(smallest_enclosing_circle(poly).center)
        best = scout
        best_d = hypot(scout, here)
        seen: list[tuple[float, float]] = []
        for p in cands:
            if hypot(p) > ARENA_R + 1e-6:
                continue
            if any(hypot(p, q) <= 8.0 for q in seen):
                continue
            seen.append(p)
            if not self._pose_covers_scout(p, scout):
                continue
            d = hypot(p, here)
            if d < best_d - 1e-9:
                best_d = d
                best = p
        return best

    def _covering_goals(self) -> list[tuple[float, float]]:
        self._prune_scouts()
        if not self.remaining_scouts:
            self._certificate_fallback_scouts()
        if not self.remaining_scouts:
            return []
        wps: list[tuple[float, float]] = []
        for scout in self.remaining_scouts:
            wp = self._covering_waypoint(scout)
            if any(hypot(wp, prev) <= 20.0 for prev in wps):
                continue
            wps.append(wp)
        return wps

    def _pose_mows_covering(self, pt: tuple[float, float]) -> bool:
        """True iff disk(pt, 1000) finishes some leftover 9-net cell."""
        if not self._pose_meets_residual(pt):
            return False
        for scout in q3_scouts():
            if self._scout_meets_residual(scout) and self._pose_covers_scout(pt, scout):
                return True
        return False

    def _worth_cover_here(self, *, waypoint: bool = False) -> bool:
        """Silent scan if this 1000 m disk finishes a leftover covering cell.

        Path-as-sensor is a time layer: a nibble that does not finish a
        9-net cell is 5 s × n_silent with no covering drop. The cell stays
        a covering goal until a scanned pose continuum-covers it. Cheap
        leftover (≤3 silent) at a waypoint is allowed.
        """
        silent = self._silent_channels()
        if not silent or self._n_found() >= N_Q3_MAX:
            return False
        here = (self.x, self.y)
        if not self._pose_meets_residual(here):
            return False
        if self._pose_mows_covering(here):
            return True
        return bool(waypoint and len(silent) <= 3)

    def _incidental_here(self) -> None:
        """Free second bearings at the current pose (5 s, no extra walk)."""
        here = (self.x, self.y)
        for ch in list(self.fixes.keys()):
            if self._too_many() or ch in self.cleared:
                continue
            if not self._incidental_second_useful(here, ch):
                continue
            body = self._measure_new(here[0], here[1], ch)
            if body is None:
                continue
            if body.get("measure_result") == "near":
                self.clear_at(here[0], here[1], ch)

    def _path_sensor_scan(self, *, waypoint: bool = False) -> None:
        """Scan remaining silent radios at the current /measure pose.

        Residual is the continuum set arena \\ ∪ disk(S, 1000) around every
        pose that actually scanned leftover silent channels. A leftover
        9-net cell is dropped only when that continuum set misses the cell.
        """
        if self._too_many():
            return
        if not self._worth_cover_here(waypoint=waypoint):
            self._prune_scouts()
            return
        self.n_path_scans += 1
        self._batch_scan_scout((self.x, self.y))
        self._prune_scouts()

    def _maybe_cover_here(self) -> None:
        if self._too_many():
            return
        if not self._worth_cover_here(waypoint=False):
            return
        self._batch_scan_scout((self.x, self.y))
        self._prune_scouts()

    def _one_bearing_items(
        self, deferred: set[int]
    ) -> list[tuple[int, tuple[float, float], float]]:
        """Pending 1-bearing channels not yet given a shared D-opt station."""
        out: list[tuple[int, tuple[float, float], float]] = []
        for ch in list(self.fixes.keys()):
            if ch in self.cleared or ch in deferred or ch in self._dopt_done:
                continue
            dirs = [
                fx
                for fx in self.fixes.get(ch, [])
                if fx.kind == "direction" and fx.svd_deg is not None
            ]
            if len(dirs) != 1:
                continue
            fx = dirs[0]
            out.append((int(ch), (fx.x, fx.y), float(fx.svd_deg)))
        return out

    def _wedge_prior(
        self, s: tuple[float, float], theta: float
    ) -> list[tuple[float, float]]:
        u = bearing_vec(theta)
        pts: list[tuple[float, float]] = []
        for r in DOPT_PRIOR_R:
            p = clip_to_arena((s[0] + r * u[0], s[1] + r * u[1]))
            if hypot(p, s) < 40.0:
                continue
            if hypot(p, s) > R_EFF_MAX + 1e-6:
                continue
            pts.append(p)
        return pts

    def _fan_clusters(
        self, items: list[tuple[int, tuple[float, float], float]]
    ) -> list[list[tuple[int, tuple[float, float], float]]]:
        """Group 1-bearings by first station, then split on angular gaps > 80°."""
        if not items:
            return []
        groups: list[list[tuple[int, tuple[float, float], float]]] = []
        for item in items:
            placed = False
            for group in groups:
                if hypot(item[1], group[0][1]) <= 50.0:
                    group.append(item)
                    placed = True
                    break
            if not placed:
                groups.append([item])
        clusters: list[list[tuple[int, tuple[float, float], float]]] = []
        for group in groups:
            if len(group) < 2:
                continue
            n = len(group)
            indexed = sorted(range(n), key=lambda i: group[i][2] % 360.0)
            thetas = [group[i][2] % 360.0 for i in indexed]
            gaps: list[tuple[float, int]] = []
            for k in range(n):
                a = thetas[k]
                b = thetas[(k + 1) % n] + (360.0 if k == n - 1 else 0.0)
                gaps.append((b - a, k))
            _lg, lk = max(gaps)
            order = [indexed[(lk + 1 + j) % n] for j in range(n)]
            cur = [group[order[0]]]
            for j in range(1, n):
                th_prev = group[order[j - 1]][2] % 360.0
                th = group[order[j]][2] % 360.0
                gap = (th - th_prev) % 360.0
                if gap > DOPT_FAN_GAP_DEG:
                    if len(cur) >= 2:
                        clusters.append(cur)
                    cur = []
                cur.append(group[order[j]])
            if len(cur) >= 2:
                clusters.append(cur)
        tight: list[list[tuple[int, tuple[float, float], float]]] = []
        for cl in clusters:
            tight.extend(self._split_wide_fan(cl))
        return tight

    def _split_wide_fan(
        self, cluster: list[tuple[int, tuple[float, float], float]]
    ) -> list[list[tuple[int, tuple[float, float], float]]]:
        """A shared station cannot triangulate a 360° fan. Cap width at 75°."""
        if len(cluster) < 2:
            return []
        ordered = sorted(cluster, key=lambda it: it[2] % 360.0)
        # Linearise at the largest internal gap so width is last-first.
        n = len(ordered)
        gaps = []
        for i in range(n):
            a = ordered[i][2] % 360.0
            b = ordered[(i + 1) % n][2] % 360.0
            gap = (b - a) % 360.0
            gaps.append(gap)
        lk = max(range(n), key=lambda i: gaps[i])
        seq = [ordered[(lk + 1 + j) % n] for j in range(n)]
        width = (seq[-1][2] - seq[0][2]) % 360.0
        if width <= DOPT_FAN_MAX_WIDTH:
            return [seq]
        out: list[list[tuple[int, tuple[float, float], float]]] = []
        start = 0
        for i in range(1, n):
            w = (seq[i][2] - seq[start][2]) % 360.0
            if w > DOPT_FAN_MAX_WIDTH:
                chunk = seq[start:i]
                if len(chunk) >= 2:
                    out.append(chunk)
                start = i
        chunk = seq[start:]
        if len(chunk) >= 2:
            out.append(chunk)
        return out

    def _bisector_deg(self, thetas: list[float]) -> float:
        sx = sum(math.cos(math.radians(t)) for t in thetas)
        sy = sum(math.sin(math.radians(t)) for t in thetas)
        if abs(sx) < 1e-15 and abs(sy) < 1e-15:
            return thetas[0]
        return math.degrees(math.atan2(sy, sx))

    def _dopt_score_point(
        self,
        p: tuple[float, float],
        items: list[tuple[int, tuple[float, float], float]],
    ) -> tuple[float, int, int]:
        """Expected summed log-det FIM, n_collapse, n_hear against 1-bearing priors.

        det(FIM_S+FIM_P) ∝ sin²ψ / (r_S² r_P²) for AOA. A source collapses when
        a conservative R_sec ≈ r_S tan(1°)/sinψ is already near the 20 m disk.
        """
        if hypot(p) > ARENA_R + 1e-6:
            return (-1e9, 0, 0)
        info = 0.0
        n_col = 0
        n_hear = 0
        for _ch, s, theta in items:
            if hypot(p, s) < 160.0:
                continue
            samples = self._wedge_prior(s, theta)
            if not samples:
                continue
            acc = 0.0
            col = 0
            hear = 0
            for g in samples:
                rp = hypot(p, g)
                rs = hypot(s, g)
                if rp > R_HEAR + 40.0:
                    continue
                hear += 1
                psi = crossing_angle_deg(s, p, g)
                spsi = math.sin(math.radians(psi))
                if spsi < 0.08:
                    continue
                acc += (
                    2.0 * math.log(spsi)
                    - 2.0 * math.log(max(rs, 30.0))
                    - 2.0 * math.log(max(rp, 30.0))
                )
                rsec = rs * math.tan(math.radians(ERR_DEG)) / spsi
                if rsec <= DOPT_COLLAPSE_RSEC and psi >= DOPT_COLLAPSE_PSI:
                    col += 1
            n = float(len(samples))
            info += acc / n
            if col / n >= 0.45:
                n_col += 1
            if hear / n >= 0.4:
                n_hear += 1
        return (info, n_col, n_hear)

    def _cluster_dopt_candidates(
        self, cluster: list[tuple[int, tuple[float, float], float]]
    ) -> list[tuple[float, float]]:
        s = cluster[0][1]
        thetas = [item[2] for item in cluster]
        theta_b = self._bisector_deg(thetas)
        u = bearing_vec(theta_b)
        nrm = left_normal(u)
        cands: list[tuple[float, float]] = []
        for r in (200.0, 450.0, 700.0):
            for t in (350.0, -350.0, 520.0, -520.0, 680.0, -680.0):
                cands.append(clip_to_arena(second_station_point(s, theta_b, r, t)))
        ghats = [
            clip_to_arena((s[0] + R_HAT_LOB * bearing_vec(th)[0], s[1] + R_HAT_LOB * bearing_vec(th)[1]))
            for th in thetas
        ]
        cx = sum(p[0] for p in ghats) / len(ghats)
        cy = sum(p[1] for p in ghats) / len(ghats)
        for t in (400.0, -400.0, 580.0, -580.0, 720.0, -720.0):
            cands.append(clip_to_arena((cx + t * nrm[0], cy + t * nrm[1])))
        return cands

    def _snap_dopt(
        self, p: tuple[float, float], covering: list[tuple[float, float]]
    ) -> tuple[float, float]:
        """Keep a covering-cell offset. Only snap when essentially the same pose."""
        if not covering:
            return p
        best = min(covering, key=lambda q: hypot(p, q))
        if hypot(p, best) <= 40.0:
            return best
        return p

    def _covers_any_remaining_cell(self, p: tuple[float, float]) -> bool:
        for scout in self.remaining_scouts:
            if self._scout_meets_residual(scout) and self._pose_covers_scout(p, scout):
                return True
        return False

    def _covering_cell_poses(self, scout: tuple[float, float]) -> list[tuple[float, float]]:
        """Poses in a scout's 1000 m neighbourhood that still cover its leftover.

        Inward radial pull is TSPN-covering but collinear with origin-heard
        rays. Lateral offsets keep the covering disk and raise crossing angle.
        Time layer only: a pose is kept iff it continuum-covers the cell.
        """
        poses: list[tuple[float, float]] = [scout]
        poses.append(self._covering_waypoint(scout))
        rs = hypot(scout)
        if rs > 1.0:
            u = (scout[0] / rs, scout[1] / rs)
        else:
            u = (1.0, 0.0)
        nrm = left_normal(u)
        for along in (-220.0, -80.0, 80.0, 220.0):
            for t in (0.0, 160.0, -160.0, 260.0, -260.0, 340.0, -340.0):
                p = clip_to_arena(
                    (scout[0] + along * u[0] + t * nrm[0], scout[1] + along * u[1] + t * nrm[1])
                )
                if hypot(p, scout) < 50.0:
                    continue
                if self._pose_covers_scout(p, scout):
                    poses.append(p)
        return poses

    def _dopt_accept(
        self,
        p: tuple[float, float],
        n_col: int,
        n_hear: int,
        covering: list[tuple[float, float]],
        here: tuple[float, float],
    ) -> bool:
        is_cover = any(hypot(p, c) <= DOPT_SNAP_M for c in covering) or self._covers_any_remaining_cell(
            p
        )
        if is_cover:
            return n_col >= DOPT_MIN_COLLAPSE or (n_col >= 1 and n_hear >= 2)
        if n_col < DOPT_MIN_COLLAPSE:
            return False
        if not covering:
            return hypot(p, here) <= DOPT_MAX_WALK
        sk = [covering[i] for i in tsp_visit_order(here, covering)]
        extra, _savings = self._cheapest_insertion_extra(p, sk, here)
        if self._pose_mows_covering(p) and extra <= MOW_EXTRA_MAX + 1e-6:
            return True
        # One interior cut for a 3+ ray fan is the covering-tax plus one
        # station, not k laterals. Extra 280 m is still less than a ring hop.
        if n_col >= 3 and extra <= 280.0:
            return hypot(p, here) <= DOPT_MAX_WALK + 1e-6
        if extra > DOPT_MAX_EXTRA + 1e-6:
            return False
        return hypot(p, here) <= DOPT_MAX_WALK + 1e-6

    def _select_dopt_city(
        self, deferred: set[int], covering: list[tuple[float, float]]
    ) -> tuple[tuple[float, float], tuple[int, ...]] | None:
        """One next pose maximising summed log-det FIM for pending 2° wedges.

        Prefers a remaining covering waypoint (incidental second on the
        covering path). A dedicated cut is taken only when ≥2 rays are
        expected to collapse and the extra vs the covering skeleton is
        not a per-source star.
        """
        items = self._one_bearing_items(deferred)
        if len(items) < DOPT_MIN_COLLAPSE:
            self._dopt_plan = None
            return None
        here = (self.x, self.y)
        cands: list[tuple[float, float]] = []
        for wp in covering:
            cands.append(wp)
        for scout in self.remaining_scouts:
            cands.extend(self._covering_cell_poses(scout))
        for cluster in self._fan_clusters(items):
            ncol_gate = 3 if len(cluster) >= 3 else DOPT_MIN_COLLAPSE
            for p in self._cluster_dopt_candidates(cluster):
                if self._dopt_accept(p, ncol_gate, len(cluster), covering, here):
                    cands.append(p)
        uniq: list[tuple[float, float]] = []
        for p in cands:
            if hypot(p) > ARENA_R + 1e-6:
                continue
            if any(hypot(p, q) <= 40.0 for q in uniq):
                continue
            if any(hypot(p, d) <= 40.0 for d in self.discovery_stations):
                continue
            if any(hypot(p, t) <= 40.0 for t in self._dopt_tried):
                continue
            uniq.append(p)
        best: tuple[float, float] | None = None
        best_score = -1e18
        best_col = 0
        for raw in uniq:
            p = self._snap_dopt(raw, covering)
            info, n_col, n_hear = self._dopt_score_point(p, items)
            if not self._dopt_accept(p, n_col, n_hear, covering, here):
                continue
            walk = hypot(p, here)
            mows = self._pose_mows_covering(p) or self._covers_any_remaining_cell(p)
            is_cover = any(hypot(p, c) <= 40.0 for c in covering) or mows
            score = (
                420.0 * n_col
                + 18.0 * info
                + 40.0 * n_hear
                - walk
                + (280.0 if mows else 0.0)
                + (90.0 if is_cover else 0.0)
            )
            if score > best_score:
                best_score = score
                best = p
                best_col = n_col
        if best is None or best_col < DOPT_MIN_COLLAPSE:
            self._dopt_plan = None
            return None
        helped: list[int] = []
        for ch, s, th in items:
            _info, n_col_i, n_hear_i = self._dopt_score_point(best, [(ch, s, th)])
            if n_col_i >= 1 or n_hear_i >= 1:
                helped.append(ch)
        if len(helped) < DOPT_MIN_COLLAPSE:
            self._dopt_plan = None
            return None
        channels = tuple(helped)
        self._dopt_plan = (best, channels)
        return self._dopt_plan

    def _visit_dopt_station(self, pt: tuple[float, float]) -> None:
        """Measure every pending 1-bearing at one shared pose.

        Do not walk each collapsed SEC from here: that rebuilds a star
        through the D-opt waypoint. Certified centres join the covering
        TSP via savings-rule / nearby-clear, same as a free incidental.
        """
        plan = self._dopt_plan
        channels: list[int] = []
        if plan is not None and hypot(pt, plan[0]) <= 90.0:
            channels = [c for c in plan[1] if c not in self.cleared]
        if not channels:
            channels = [ch for ch, _s, _th in self._one_bearing_items(set())]
        self._dopt_plan = None
        self._dopt_tried.append(pt)
        if not channels:
            return
        for ch in self._order_channels(channels):
            if self._too_many() or ch in self.cleared:
                continue
            body = self._measure_new(pt[0], pt[1], ch)
            if body is None:
                continue
            if body.get("measure_result") == "no_signal":
                # This pose cannot hear G; a later covering scout may.
                continue
            self._dopt_done.add(ch)
            if body.get("measure_result") == "near":
                self.clear_at(pt[0], pt[1], ch)
        for ch in channels:
            if ch in self.cleared:
                continue
            dirs = [
                fx
                for fx in self.fixes.get(ch, [])
                if fx.kind == "direction" and fx.svd_deg is not None
            ]
            if len(dirs) < 2:
                continue
            poly = self._poly_for(ch)
            if len(poly) < 3:
                continue
            sec = smallest_enclosing_circle(poly)
            if sec.radius <= DOPT_COLLAPSE_RSEC:
                self.n_dopt_collapses += 1

    def _run_omni(self) -> None:
        """Q3: covering skeleton + one D-optimal station for many rays.

        After a scout hears k channels, the next pose maximises summed
        log-det FIM for those 2° wedges (Bayesian AOA placement). Several
        SECs collapse at that waypoint; certified centres join the covering
        TSP. Incidental later-scout seconds stay on the covering path.
        Far 1-bearings that a shared station misses wait for one service TSP.
        """
        self.remaining_scouts = list(q3_scouts())
        self.discovery_stations = []
        self.n_path_scans = 0
        self.n_net_visits = 0
        self.n_savings_inserts = 0
        self.n_dopt_visits = 0
        self.n_dopt_collapses = 0
        self.no_signal_pts = {}
        self._dopt_done = set()
        self._dopt_tried = []
        self._dopt_plan = None
        self._rho_cache = {}
        deferred: set[int] = set()
        while not self._too_many():
            self._maybe_cover_here()
            covering_left = bool(self._covering_goals())
            blocked = deferred if covering_left else set()
            goal = self._next_clustered_goal(self.remaining_scouts, blocked)
            if goal is None:
                break
            kind, pt, ch = goal
            if kind == "scout":
                self.n_net_visits += 1
                self._pickup_on_edge(pt, blocked)
                self._batch_scan_scout(pt)
                self._prune_scouts()
                self._service_certified_nearby(max_walk=NEARBY_CERT_M)
                self._incidental_here()
                deferred.clear()
            elif kind == "dopt":
                self.n_dopt_visits += 1
                self._pickup_on_edge(pt, blocked)
                self._visit_dopt_station(pt)
                if (
                    self._covers_any_remaining_cell(pt)
                    or self._worth_cover_here(waypoint=True)
                    or any(hypot(pt, s) <= 40.0 for s in list(self.remaining_scouts))
                ):
                    self.n_net_visits += 1
                    self._batch_scan_scout(pt)
                    self._prune_scouts()
                else:
                    self._path_sensor_scan(waypoint=True)
                self._incidental_here()
                self._service_certified_nearby(max_walk=NEARBY_CERT_M)
            elif kind == "lob":
                if covering_left:
                    self.n_savings_inserts += 1
                self._lob_home(ch, join=pt)
                self._path_sensor_scan(waypoint=True)
                self._incidental_here()
                self._service_certified_nearby(max_walk=NEARBY_CERT_M)
                if ch not in self.cleared:
                    deferred.add(ch)
            else:
                if covering_left:
                    self.n_savings_inserts += 1
                status = self._try_poly_clear(ch)
                if ch in self.cleared:
                    self._path_sensor_scan(waypoint=True)
                    self._incidental_here()
                    self._service_certified_nearby(max_walk=NEARBY_CERT_M)
                    continue
                if status == "retry":
                    continue
                self._lob_home(ch)
                self._path_sensor_scan(waypoint=True)
                self._incidental_here()
                self._service_certified_nearby(max_walk=NEARBY_CERT_M)
                if ch not in self.cleared:
                    deferred.add(ch)
        self._service_pending_tsp()
        self._chase_open_fixes()

    def _visit_short_second(self, channel: int, pt: tuple[float, float]) -> None:
        if channel in self.cleared or self._too_many():
            return
        body = self._measure_new(pt[0], pt[1], channel)
        if body is None:
            dirs = [
                fx
                for fx in self.fixes.get(channel, [])
                if fx.kind == "direction" and fx.svd_deg is not None
            ]
            if len(dirs) == 1:
                self._take_second_station(channel, dirs[0])
            return
        if body.get("measure_result") == "near":
            self.clear_at(pt[0], pt[1], channel)
            return
        if body.get("measure_result") == "no_signal":
            dirs = [
                fx
                for fx in self.fixes.get(channel, [])
                if fx.kind == "direction" and fx.svd_deg is not None
            ]
            if dirs:
                other = self._reflect_across_lob(dirs[0], pt)
                flipped = self._measure_new(other[0], other[1], channel)
                if flipped is not None and flipped.get("measure_result") == "near":
                    self.clear_at(other[0], other[1], channel)
                    return
        dirs = [
            fx
            for fx in self.fixes.get(channel, [])
            if fx.kind == "direction" and fx.svd_deg is not None
        ]
        if len(dirs) >= 2:
            status = self._try_poly_clear(channel)
            if status == "cleared":
                return
            self._service_certified_nearby(max_walk=200.0)

    def _batch_scan_scout(self, pt: tuple[float, float]) -> None:
        """Scan leftover silent channels at a pose that meets continuum residual.

        A pose is marked a discovery station only if silent channels were
        actually measured there. Finite witness lists are not used to skip
        a silent scan. A 1-bearing incidental second is taken only if this
        covering waypoint can hear G with a non-collinear baseline.
        """
        silent = self._silent_channels()
        if silent and self.discovery_stations and not self._pose_meets_residual(pt):
            silent = []
        if silent:
            self.scan_point(pt, silent, chase=False)
            self._mark_discovery(pt)
        for ch in list(self.fixes.keys()):
            if self._too_many() or ch in self.cleared:
                continue
            dirs = [
                fx
                for fx in self.fixes.get(ch, [])
                if fx.kind == "direction" and fx.svd_deg is not None
            ]
            if len(dirs) != 1:
                continue
            if not self._incidental_second_useful(pt, ch):
                continue
            body = self._measure_new(pt[0], pt[1], ch)
            if body is None:
                continue
            if body.get("measure_result") == "near":
                self.clear_at(pt[0], pt[1], ch)

    def _incidental_second_useful(self, pt: tuple[float, float], channel: int) -> bool:
        """True iff measuring at `pt` can add a non-collinear bearing with no extra walk."""
        if self._already_tried(channel, pt[0], pt[1], tol=30.0):
            return False
        dirs = [
            fx
            for fx in self.fixes.get(channel, [])
            if fx.kind == "direction" and fx.svd_deg is not None
        ]
        if not dirs:
            return False
        if any(hypot(pt, (fx.x, fx.y)) < 180.0 for fx in dirs):
            return False
        if len(dirs) >= 2:
            poly = self._poly_for(channel)
            if len(poly) < 3:
                return True
            sec = smallest_enclosing_circle(poly)
            if sec.radius <= R_CLEAR + 1e-6:
                return False
            # A later scout is a free extra station (5 s, no walk). Keep
            # taking bearings while R_sec > 20 m and the scout can hear G.
            return hypot(pt, sec.center) <= R_EFF_MIN
        fx = dirs[0]
        s = (fx.x, fx.y)
        u = bearing_vec(float(fx.svd_deg))
        far = (s[0] + R_EFF_MAX * u[0], s[1] + R_EFF_MAX * u[1])
        if dist_point_to_segment(pt, s, far) > R_EFF_MIN + 50.0:
            return False
        g_hat = clip_to_arena((s[0] + 550.0 * u[0], s[1] + 550.0 * u[1]))
        return crossing_angle_deg(s, pt, g_hat) >= 12.0

    def _service_certified_nearby(self, max_walk: float) -> None:
        here = (self.x, self.y)
        for ch in list(self.fixes.keys()):
            if self._too_many() or ch in self.cleared:
                continue
            poly = self._poly_for(ch)
            if len(poly) < 3:
                continue
            sec = smallest_enclosing_circle(poly)
            dinfo = diametral_circle_covers_any(poly)
            if dinfo["covers"] and 0.5 * float(dinfo["diameter"]) <= R_CLEAR + 1e-6:
                cx = float(dinfo["center_x"])
                cy = float(dinfo["center_y"])
                if hypot(here, (cx, cy)) <= max_walk:
                    self.clear_at(cx, cy, ch)
                    continue
            if sec.radius <= R_CLEAR + 1e-6 and hypot(here, sec.center) <= max_walk:
                self.clear_at(sec.center[0], sec.center[1], ch)

    def _posterior_feasible(self, channel: int, p: tuple[float, float]) -> bool:
        if hypot(p) > ARENA_R + 1e-6:
            return False
        dirs = [
            fx
            for fx in self.fixes.get(channel, [])
            if fx.kind == "direction" and fx.svd_deg is not None
        ]
        for fx in dirs:
            s = (fx.x, fx.y)
            if hypot(p, s) > R_EFF_MAX + 1e-6:
                return False
            if not in_wedge(p, s, float(fx.svd_deg), err_deg=ERR_DEG):
                return False
        for q in self.no_signal_pts.get(channel, []):
            if hypot(p, q) <= R_HEAR + 1e-6:
                return False
        return True

    def _posterior_samples(self, channel: int) -> list[tuple[float, float]]:
        dirs = [
            fx
            for fx in self.fixes.get(channel, [])
            if fx.kind == "direction" and fx.svd_deg is not None
        ]
        if not dirs:
            return []
        fx = dirs[0]
        s = (fx.x, fx.y)
        theta = float(fx.svd_deg)
        u = bearing_vec(theta)
        nrm = left_normal(u)
        pts: list[tuple[float, float]] = []
        for i in range(1, 25):
            r = (float(i) / 24.0) * R_EFF_MAX
            half = r * math.tan(math.radians(ERR_DEG))
            for t in (0.0, 0.55 * half, -0.55 * half):
                p = clip_to_arena((s[0] + r * u[0] + t * nrm[0], s[1] + r * u[1] + t * nrm[1]))
                if hypot(p, s) < 8.0:
                    continue
                if self._posterior_feasible(channel, p):
                    pts.append(p)
        return pts

    def _posterior_centroid(self, channel: int) -> tuple[float, float] | None:
        pts = self._posterior_samples(channel)
        if not pts:
            return None
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        c = clip_to_arena((cx, cy))
        if self._posterior_feasible(channel, c):
            return c
        return min(pts, key=lambda p: hypot(p, c))

    def _estimate_service_point(self, channel: int) -> tuple[float, float]:
        fixes = self.fixes.get(channel, [])
        near = [fx for fx in fixes if fx.kind == "near"]
        if near:
            return (near[-1].x, near[-1].y)
        dirs = [fx for fx in fixes if fx.kind == "direction" and fx.svd_deg is not None]
        if len(dirs) >= 2:
            poly = self._poly_for(channel)
            if len(poly) >= 3:
                return smallest_enclosing_circle(poly).center
        if dirs:
            fx = dirs[-1]
            u = bearing_vec(float(fx.svd_deg))
            return clip_to_arena((fx.x + R_HAT_LOB * u[0], fx.y + R_HAT_LOB * u[1]))
        return (self.x, self.y)

    def _edge_aligned_lob(self, channel: int, a: tuple[float, float], b: tuple[float, float]) -> bool:
        """True iff this 1-bearing points along a→b, so a probe stays on the skeleton."""
        dirs = [
            fx
            for fx in self.fixes.get(channel, [])
            if fx.kind == "direction" and fx.svd_deg is not None
        ]
        if not dirs:
            return False
        u = bearing_vec(float(dirs[-1].svd_deg))
        dx, dy = b[0] - a[0], b[1] - a[1]
        elen = math.hypot(dx, dy)
        if elen < 30.0:
            return False
        return (u[0] * dx + u[1] * dy) / elen >= math.cos(math.radians(8.0))

    def _pickup_on_edge(
        self, dst: tuple[float, float], blocked: set[int]
    ) -> None:
        """Clarke–Wright extra≈0: probe 1-bearings whose LOB is this covering edge."""
        here = (self.x, self.y)
        for kind, p, ch in self._ready_service(blocked):
            if self._too_many() or ch in self.cleared:
                continue
            extra = hypot(p, here) + hypot(p, dst) - hypot(here, dst)
            if extra > ON_WAY_EXTRA + 1e-6:
                continue
            if kind == "lob" and not self._edge_aligned_lob(ch, here, dst):
                continue
            self.n_savings_inserts += 1
            if kind == "lob":
                body = self._measure_new(p[0], p[1], ch)
                if body is None:
                    continue
                kind_m = body.get("measure_result")
                if kind_m == "near":
                    self.clear_at(p[0], p[1], ch)
                    self._path_sensor_scan(waypoint=True)
                elif kind_m == "no_signal":
                    mid = ((here[0] + p[0]) * 0.5, (here[1] + p[1]) * 0.5)
                    self.clear_at(mid[0], mid[1], ch)
                    if ch in self.cleared:
                        self._path_sensor_scan(waypoint=True)
            else:
                status = self._try_poly_clear(ch)
                if ch in self.cleared:
                    self._path_sensor_scan(waypoint=True)
                elif status == "retry":
                    pass
            here = (self.x, self.y)

    def _is_certified(self, channel: int) -> bool:
        fixes = self.fixes.get(channel, [])
        if any(fx.kind == "near" for fx in fixes):
            return True
        poly = self._poly_for(channel)
        if len(poly) < 3:
            return False
        sec = smallest_enclosing_circle(poly)
        if sec.radius <= R_CLEAR + 1e-6:
            return True
        dinfo = diametral_circle_covers_any(poly)
        return bool(dinfo["covers"]) and 0.5 * float(dinfo["diameter"]) <= R_CLEAR + 1e-6

    def _covering_skeleton(
        self, origin: tuple[float, float], covering_pts: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        if not covering_pts:
            return []
        order = tsp_visit_order(origin, covering_pts)
        return [covering_pts[i] for i in order]

    def _cheapest_insertion_extra(
        self,
        p: tuple[float, float],
        skeleton: list[tuple[float, float]],
        origin: tuple[float, float],
    ) -> tuple[float, float]:
        """Cheapest-insertion extra onto origin→skeleton, and CW savings vs defer.

        savings = d(skeleton_end, p) − extra. Positive means inserting p into
        a covering edge is shorter than finishing the covering tour then
        walking from its end to p (Clarke–Wright vs covering-first).
        """
        if not skeleton:
            return 0.0, 0.0
        nodes = [origin] + skeleton
        extra_append = hypot(p, skeleton[-1])
        best_extra = extra_append
        for a, b in zip(nodes, nodes[1:]):
            extra = hypot(p, a) + hypot(p, b) - hypot(a, b)
            if extra < best_extra:
                best_extra = extra
        return best_extra, extra_append - best_extra

    def _savings_accept(
        self,
        kind: str,
        p: tuple[float, float],
        extra: float,
        savings: float,
        certified: bool,
    ) -> bool:
        on_way = extra <= ON_WAY_EXTRA + 1e-6
        mows = extra <= MOW_EXTRA_MAX + 1e-6 and self._pose_mows_covering(p)
        if kind == "lob":
            # 1-bearing is not a point city. TSP-insert only when the join
            # mows leftover residual; on-edge probes are `_pickup_on_edge`.
            return mows
        if extra > CERT_EXTRA_MAX + 1e-6:
            return mows
        return on_way or mows or savings > 1.0

    def _ready_service(
        self, deferred: set[int]
    ) -> list[tuple[str, tuple[float, float], int]]:
        out: list[tuple[str, tuple[float, float], int]] = []
        for ch in list(self.fixes.keys()):
            if ch in self.cleared or ch in deferred:
                continue
            fixes = self.fixes.get(ch, [])
            n_near = sum(1 for fx in fixes if fx.kind == "near")
            n_dir = sum(1 for fx in fixes if fx.kind == "direction" and fx.svd_deg is not None)
            if n_near:
                out.append(("svc", self._estimate_service_point(ch), ch))
            elif n_dir >= 2:
                out.append(("svc", self._estimate_service_point(ch), ch))
            elif n_dir == 1:
                out.append(("lob", self._estimate_service_point(ch), ch))
        return out

    def _next_clustered_goal(
        self,
        remaining_scouts: list[tuple[float, float]],
        deferred: set[int],
    ) -> tuple[str, tuple[float, float], int | None] | None:
        """Covering-skeleton TSP plus savings-gated online-TSP inserts.

        2-bearing / certified SECs join the remaining covering tour. A
        1-bearing joins only if it is already near, mows leftover covering,
        or covering is finished. Far 1-bearings wait for one service TSP.
        On-edge extra≈0 1-bearings are `_pickup_on_edge`, not TSP cities.
        """
        del remaining_scouts
        covering = [("scout", wp, None) for wp in self._covering_goals()]
        service = self._ready_service(deferred)
        here = (self.x, self.y)
        covering_left = bool(covering)
        pts: list[tuple[float, float]] = []
        meta: list[tuple[str, tuple[float, float], int | None]] = []
        for item in covering:
            pts.append(item[1])
            meta.append(item)
        cover_pts = [item[1] for item in covering]
        dopt = self._select_dopt_city(deferred, cover_pts)
        if dopt is not None:
            dp, _chs = dopt
            kept_pts: list[tuple[float, float]] = []
            kept_meta: list[tuple[str, tuple[float, float], int | None]] = []
            for p, m in zip(pts, meta):
                if m[0] == "scout":
                    skip = hypot(p, dp) <= 40.0
                    if not skip:
                        for scout in self.remaining_scouts:
                            if self._pose_covers_scout(dp, scout) and (
                                self._pose_covers_scout(p, scout) or hypot(p, scout) <= 40.0
                            ):
                                skip = True
                                break
                    if skip:
                        continue
                kept_pts.append(p)
                kept_meta.append(m)
            pts = kept_pts
            meta = kept_meta
            pts.append(dp)
            meta.append(("dopt", dp, None))
        for kind, p, ch in service:
            if kind != "lob":
                pts.append(p)
                meta.append((kind, p, ch))
                continue
            dirs_ch = [
                fx
                for fx in self.fixes.get(ch, [])
                if fx.kind == "direction" and fx.svd_deg is not None
            ]
            heard_off_origin = bool(dirs_ch) and hypot((dirs_ch[0].x, dirs_ch[0].y)) > 200.0
            on_way = hypot(p, here) <= 420.0
            if (not covering_left) or on_way or (
                heard_off_origin and self._pose_mows_covering(p)
            ):
                pts.append(p)
                meta.append((kind, p, ch))
        if not pts:
            return None
        order = tsp_visit_order(here, pts)
        chosen = meta[order[0]]
        if dopt is not None:
            dp, _chs = dopt
            extra_first = hypot(dp, here) - hypot(pts[order[0]], here)
            is_cover = any(hypot(dp, c) <= DOPT_SNAP_M for c in cover_pts) or self._covers_any_remaining_cell(
                dp
            )
            # From the origin every ring is 1000 m, so extra≈0 and the
            # information-best scout is first. Mid-tour, do not jump across
            # the octagon to the other cluster's scout (that is a star).
            if extra_first <= 80.0 or (is_cover and extra_first <= 220.0):
                return ("dopt", dp, None)
        return chosen

    def _service_pending_tsp(self) -> None:
        failed: set[int] = set()
        while not self._too_many():
            pending = [
                c
                for c in self.remaining_channels()
                if c in self.fixes and c not in self.cleared and c not in failed
            ]
            if not pending:
                return
            pts = []
            for c in pending:
                post = self._posterior_centroid(c)
                pts.append(post if post is not None else self._estimate_service_point(c))
            order = tsp_visit_order((self.x, self.y), pts)
            ch = pending[order[0]]
            if self.mixed:
                self.chase(ch)
            else:
                self._lob_home(ch, join=pts[order[0]])
            if ch not in self.cleared:
                failed.add(ch)

    def walk_m(self) -> float:
        last: tuple[float, float] | None = None
        dist = 0.0
        for row in self.trace:
            if row.get("path") not in {"/measure", "/clear"}:
                continue
            req = row["request"]
            xy = (float(req["x"]), float(req["y"]))
            if last is not None:
                dist += hypot(xy, last)
            last = xy
        return dist

    def _chase_open_fixes(self) -> None:
        for ch in list(self.fixes.keys()):
            if ch not in self.cleared and not self._too_many():
                self.chase(ch)

    def _run_mixed(self) -> None:
        remaining = list(q4_scouts())
        while remaining and not self._too_many():
            if not self._silent_channels():
                break
            scout = remaining.pop(self._nearest_index(remaining))
            self._exterior_first(scout)
            self._chase_open_fixes()
        self._chase_open_fixes()

    def search_after_enter(self) -> None:
        if self.mixed:
            self._run_mixed()
        else:
            self._run_omni()

    def run(self) -> dict[str, Any]:
        enter_body = self.enter()
        if not enter_body.get("accepted"):
            return {
                "ok": False,
                "reason": "enter_rejected",
                "enter": enter_body,
                "cleared": sorted(self.cleared),
                "virtual_time_s": self.last_virtual,
            }
        self.search_after_enter()
        exit_body = self.exit()
        return {
            "ok": True,
            "cleared": sorted(self.cleared),
            "n_cleared": len(self.cleared),
            "n_actions": self.actions,
            "virtual_time_s": self.last_virtual,
            "exit": exit_body,
            "remaining_unfixed": [c for c in self.remaining_channels() if c not in self.fixes],
        }
