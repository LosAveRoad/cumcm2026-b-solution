"""White-box ±1° bearing-wedge geometry for CUMCM 2026 B Q1–Q2.

East = 0°, counterclockwise positive. Angles in degrees unless noted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from jianmo.b_sim.geometry import (  # noqa: F401  # Q3/Q4 covering certificates
    directional_certainty_params,
    exact_lob_crosses_into_backlobe,
    heading_cover_max_gap_deg,
    in_closed_lobe,
    lateral_stays_in_lobe_for_all_t,
    optical_grid_covers,
    q3_omni_covering_radius,
    q4_certainty_scouts,
    q4_fill1850_collinear_outward,
    q4_omni_covering_radius,
    q4_staggered_covering_radius,
    q4_staggered_scouts,
    q4_twosided_failure_witness,
    scouts_within,
    triangular_covering_radius,
    two_sided_max_angle_deg,
)

Point = tuple[float, float]
EPS_ANG = 1e-12
EPS_LEN = 1e-9

ARENA_R = 1800.0
R_EFF_MIN = 1000.0
R_EFF_MAX = 1500.0
R_CLEAR = 20.0
R_NEAR = 5.0
ERR_DEG = 1.0
SPEED_MPS = 5.0


def closed_lobe_dot(station: Point, source: Point, heading_deg: float) -> float:
    """(S-G)·u_H. Nonnegative iff S is in the closed 180° lobe of G."""
    ux, uy = math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg))
    return (station[0] - source[0]) * ux + (station[1] - source[1]) * uy


def wrap_deg(d: float) -> float:
    return (d + 180.0) % 360.0 - 180.0


def ang_dist_deg(a: float, b: float) -> float:
    return abs(wrap_deg(a - b))


def bearing_deg(p: Point, s: Point) -> float:
    return math.degrees(math.atan2(p[1] - s[1], p[0] - s[0]))


def bearing_vec(deg: float) -> Point:
    rad = math.radians(deg)
    return (math.cos(rad), math.sin(rad))


def vadd(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def vsub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def smul(s: float, a: Point) -> Point:
    return (s * a[0], s * a[1])


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def hypot(a: Point, b: Point | None = None) -> float:
    if b is None:
        return math.hypot(a[0], a[1])
    return math.hypot(a[0] - b[0], a[1] - b[1])


def left_normal(u: Point) -> Point:
    return (-u[1], u[0])


def in_wedge(p: Point, station: Point, theta_deg: float, err_deg: float = ERR_DEG, *, atol: float = 1e-9) -> bool:
    dx = p[0] - station[0]
    dy = p[1] - station[1]
    if dx * dx + dy * dy <= atol * atol:
        return True
    return ang_dist_deg(math.degrees(math.atan2(dy, dx)), theta_deg) <= err_deg + atol


def wedge_halfplanes(station: Point, theta_deg: float, err_deg: float = ERR_DEG) -> list[tuple[Point, float]]:
    """Inward half-planes n·x >= c for the 2*err_deg forward wedge."""
    planes: list[tuple[Point, float]] = []
    phi_left = theta_deg + err_deg
    phi_right = theta_deg - err_deg
    n_left = (math.sin(math.radians(phi_left)), -math.cos(math.radians(phi_left)))
    n_right = (-math.sin(math.radians(phi_right)), math.cos(math.radians(phi_right)))
    for n in (n_left, n_right):
        planes.append((n, dot(n, station)))
    return planes


def _intersect_segment_plane(a: Point, b: Point, n: Point, c: float) -> Point:
    da = dot(n, a) - c
    db = dot(n, b) - c
    denom = da - db
    if abs(denom) < 1e-18:
        return b
    t = da / denom
    t = min(1.0, max(0.0, t))
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def clip_convex(poly: Sequence[Point], planes: Sequence[tuple[Point, float]], *, atol: float = 1e-12) -> list[Point]:
    """Sutherland–Hodgman: keep n·x >= c. Input assumed convex CCW."""
    out = list(poly)
    for n, c in planes:
        if len(out) < 3:
            return []
        nxt: list[Point] = []
        for i, a in enumerate(out):
            b = out[(i + 1) % len(out)]
            da = dot(n, a) - c
            db = dot(n, b) - c
            a_in = da >= -atol
            b_in = db >= -atol
            if a_in and b_in:
                nxt.append(b)
            elif a_in and not b_in:
                nxt.append(_intersect_segment_plane(a, b, n, c))
            elif (not a_in) and b_in:
                nxt.append(_intersect_segment_plane(a, b, n, c))
                nxt.append(b)
        out = _dedup_poly(nxt)
    return out


def _dedup_poly(pts: Sequence[Point], *, atol: float = 1e-9) -> list[Point]:
    if not pts:
        return []
    cleaned: list[Point] = []
    for p in pts:
        if not cleaned or hypot(p, cleaned[-1]) > atol:
            cleaned.append(p)
    if len(cleaned) >= 2 and hypot(cleaned[0], cleaned[-1]) <= atol:
        cleaned.pop()
    return cleaned


def box_polygon(half: float) -> list[Point]:
    return [(-half, -half), (half, -half), (half, half), (-half, half)]


def regular_polygon(center: Point, radius: float, n: int = 96) -> list[Point]:
    cx, cy = center
    return [
        (cx + radius * math.cos(2.0 * math.pi * k / n), cy + radius * math.sin(2.0 * math.pi * k / n))
        for k in range(n)
    ]


def intersect_wedges(
    stations: Sequence[Point],
    bearings_deg: Sequence[float],
    *,
    err_deg: float = ERR_DEG,
    clip_arena: bool = False,
    range_balls: Sequence[float] | None = None,
    start_half: float = 1.0e6,
    arena_r: float = ARENA_R,
    arena_sides: int = 96,
    ball_sides: int = 64,
) -> list[Point]:
    if len(stations) != len(bearings_deg):
        raise ValueError("stations and bearings length mismatch")
    poly = box_polygon(start_half)
    planes: list[tuple[Point, float]] = []
    for s, th in zip(stations, bearings_deg):
        planes.extend(wedge_halfplanes(s, th, err_deg))
    poly = clip_convex(poly, planes)
    if clip_arena:
        poly = clip_convex(poly, _outward_polygon_planes(regular_polygon((0.0, 0.0), arena_r, arena_sides)))
    if range_balls is not None:
        if len(range_balls) != len(stations):
            raise ValueError("range_balls length mismatch")
        for s, rad in zip(stations, range_balls):
            if rad <= 0:
                continue
            poly = clip_convex(poly, _outward_polygon_planes(regular_polygon(s, rad, ball_sides)))
    return poly


def _outward_polygon_planes(poly: Sequence[Point]) -> list[tuple[Point, float]]:
    """Inward half-planes of a CCW polygon (n points to the left of each edge)."""
    planes: list[tuple[Point, float]] = []
    m = len(poly)
    for i in range(m):
        a = poly[i]
        b = poly[(i + 1) % m]
        edge = vsub(b, a)
        n = left_normal(edge)  # inward for CCW
        ln = hypot(n)
        if ln < 1e-18:
            continue
        n = (n[0] / ln, n[1] / ln)
        planes.append((n, dot(n, a)))
    return planes


def polygon_unbounded(poly: Sequence[Point], *, start_half: float = 1.0e6, tol: float = 1.0) -> bool:
    if len(poly) < 3:
        return True
    lim = start_half - tol
    return any(abs(p[0]) >= lim or abs(p[1]) >= lim for p in poly)


def polygon_area(poly: Sequence[Point]) -> float:
    if len(poly) < 3:
        return 0.0
    acc = 0.0
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        acc += p[0] * q[1] - p[1] * q[0]
    return 0.5 * acc


def ensure_ccw(poly: Sequence[Point]) -> list[Point]:
    pts = list(poly)
    if polygon_area(pts) < 0:
        pts.reverse()
    return pts


def set_diameter_points(points: Sequence[Point]) -> tuple[float, Point, Point]:
    if len(points) < 2:
        raise ValueError("need at least two points")
    best = -1.0
    pair = (points[0], points[1])
    for i, p in enumerate(points):
        for q in points[i + 1 :]:
            d = hypot(p, q)
            if d > best:
                best = d
                pair = (p, q)
    return best, pair[0], pair[1]


def diametral_pairs(points: Sequence[Point], *, atol: float = 1e-8) -> list[tuple[Point, Point, float]]:
    if len(points) < 2:
        return []
    dmax, _, _ = set_diameter_points(points)
    pairs: list[tuple[Point, Point, float]] = []
    for i, p in enumerate(points):
        for q in points[i + 1 :]:
            d = hypot(p, q)
            if d >= dmax - atol:
                pairs.append((p, q, d))
    return pairs


def disk_covers(points: Sequence[Point], center: Point, radius: float, *, atol: float = 1e-8) -> bool:
    return all(hypot(p, center) <= radius + atol for p in points)


def diametral_circle_covers_any(points: Sequence[Point], *, atol: float = 1e-8) -> dict[str, float | bool | int]:
    """True iff some diametral pair's diameter-circle covers the vertex set."""
    dmax, a0, b0 = set_diameter_points(points)
    covers = False
    used = (a0, b0)
    for a, b, _d in diametral_pairs(points, atol=atol):
        c = (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
        if disk_covers(points, c, 0.5 * dmax, atol=atol):
            covers = True
            used = (a, b)
            break
    c = (0.5 * (used[0][0] + used[1][0]), 0.5 * (used[0][1] + used[1][1]))
    return {
        "diameter": dmax,
        "radius": 0.5 * dmax,
        "covers": covers,
        "center_x": c[0],
        "center_y": c[1],
        "n_diametral_pairs": len(diametral_pairs(points, atol=atol)),
    }


@dataclass
class Circle:
    center: Point
    radius: float


def _circumscribed_circle(a: Point, b: Point, c: Point) -> Circle | None:
    d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-18:
        return None
    a2 = a[0] * a[0] + a[1] * a[1]
    b2 = b[0] * b[0] + b[1] * b[1]
    c2 = c[0] * c[0] + c[1] * c[1]
    ux = (a2 * (b[1] - c[1]) + b2 * (c[1] - a[1]) + c2 * (a[1] - b[1])) / d
    uy = (a2 * (c[0] - b[0]) + b2 * (a[0] - c[0]) + c2 * (b[0] - a[0])) / d
    cen = (ux, uy)
    return Circle(cen, hypot(cen, a))


def smallest_enclosing_circle(points: Sequence[Point], *, atol: float = 1e-9) -> Circle:
    pts = list(points)
    if not pts:
        raise ValueError("empty")
    if len(pts) == 1:
        return Circle(pts[0], 0.0)
    best: Circle | None = None

    def consider(circ: Circle) -> None:
        nonlocal best
        if disk_covers(pts, circ.center, circ.radius, atol=atol):
            if best is None or circ.radius < best.radius - 1e-15:
                best = circ

    for i, p in enumerate(pts):
        for q in pts[i + 1 :]:
            consider(Circle((0.5 * (p[0] + q[0]), 0.5 * (p[1] + q[1])), 0.5 * hypot(p, q)))
    for i, p in enumerate(pts):
        for j in range(i + 1, len(pts)):
            for k in range(j + 1, len(pts)):
                circ = _circumscribed_circle(p, pts[j], pts[k])
                if circ is not None:
                    consider(circ)
    if best is None:
        d, a, b = set_diameter_points(pts)
        best = Circle((0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])), 0.5 * d)
    return best


def sec_covers_via_jung(points: Sequence[Point], *, atol: float = 1e-8) -> dict[str, float | bool]:
    d, _, _ = set_diameter_points(points)
    sec = smallest_enclosing_circle(points, atol=atol)
    return {
        "diameter": d,
        "sec_radius": sec.radius,
        "sec_center_x": sec.center[0],
        "sec_center_y": sec.center[1],
        "covers": bool(2.0 * sec.radius <= d + atol),
        "jung_ratio": (sec.radius / d) if d > 0 else 0.0,
    }


def intersect_two_lines(p1: Point, b1_deg: float, p2: Point, b2_deg: float) -> tuple[Point, float, float] | None:
    d1 = bearing_vec(b1_deg)
    d2 = bearing_vec(b2_deg)
    det = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(det) < 1e-15:
        return None
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    t = (dx * d2[1] - dy * d2[0]) / det
    s = (dx * d1[1] - dy * d1[0]) / det
    hit = (p1[0] + t * d1[0], p1[1] + t * d1[1])
    return hit, t, s


def two_station_quad_filtered(
    station_a: Point,
    bearing_a_deg: float,
    station_b: Point,
    bearing_b_deg: float,
    *,
    err_deg: float = ERR_DEG,
) -> list[Point]:
    """Four mixed-boundary intersections that lie in both forward wedges."""
    pts: list[Point] = []
    for e1 in (err_deg, -err_deg):
        for e2 in (err_deg, -err_deg):
            hit = intersect_two_lines(station_a, bearing_a_deg + e1, station_b, bearing_b_deg + e2)
            if hit is None:
                continue
            p, t, s = hit
            if t < -1e-9 or s < -1e-9:
                continue
            if in_wedge(p, station_a, bearing_a_deg, err_deg) and in_wedge(p, station_b, bearing_b_deg, err_deg):
                pts.append(p)
    return ensure_ccw(_convex_hull(pts)) if len(pts) >= 3 else _dedup_poly(pts)


def _convex_hull(points: Sequence[Point]) -> list[Point]:
    pts = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(pts) <= 2:
        return list(pts)

    def cross(o: Point, a: Point, b: Point) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[Point] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def centroid(poly: Sequence[Point]) -> Point:
    if not poly:
        return (0.0, 0.0)
    a = polygon_area(poly)
    if abs(a) < 1e-18:
        return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
    cx = cy = 0.0
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        cr = p[0] * q[1] - p[1] * q[0]
        cx += (p[0] + q[0]) * cr
        cy += (p[1] + q[1]) * cr
    return (cx / (6.0 * a), cy / (6.0 * a))


def crossing_angle_deg(s1: Point, s2: Point, g: Point) -> float:
    """Angle at G between S1 and S2, in (0, 180]."""
    u = vsub(s1, g)
    v = vsub(s2, g)
    nu = hypot(u)
    nv = hypot(v)
    if nu < 1e-15 or nv < 1e-15:
        return 0.0
    c = max(-1.0, min(1.0, dot(u, v) / (nu * nv)))
    return math.degrees(math.acos(c))


def second_station_point(s1: Point, theta_deg: float, r: float, t: float) -> Point:
    u = bearing_vec(theta_deg)
    v = left_normal(u)
    return (s1[0] + r * u[0] + t * v[0], s1[1] + r * u[1] + t * v[1])


def sample_first_wedge(
    s1: Point,
    theta_deg: float,
    *,
    err_deg: float = ERR_DEG,
    r_min: float = R_NEAR + 1e-6,
    r_max: float = R_EFF_MAX,
    arena_r: float = ARENA_R,
    n_r: int = 16,
    n_phi: int = 5,
) -> list[Point]:
    pts: list[Point] = []
    for i in range(n_r):
        r = r_min + (r_max - r_min) * (i + 0.5) / n_r
        for j in range(n_phi):
            phi = theta_deg - err_deg + (2.0 * err_deg) * (j + 0.5) / n_phi
            p = (s1[0] + r * math.cos(math.radians(phi)), s1[1] + r * math.sin(math.radians(phi)))
            if hypot(p) <= arena_r + 1e-9:
                pts.append(p)
    return pts


def posterior_polygon(
    s1: Point,
    theta1: float,
    s2: Point,
    theta2: float,
    *,
    err_deg: float = ERR_DEG,
    clip_arena: bool = True,
    use_range_balls: bool = True,
) -> list[Point]:
    balls = [R_EFF_MAX, R_EFF_MAX] if use_range_balls else None
    poly = intersect_wedges(
        [s1, s2],
        [theta1, theta2],
        err_deg=err_deg,
        clip_arena=clip_arena,
        range_balls=balls,
    )
    return poly


def measured_bearing(true_deg: float, error_deg: float) -> float:
    return (true_deg + error_deg) % 360.0


def equilateral_counterexample(side: float = 80.0, center: Point = (0.0, 400.0)) -> dict:
    """Three exterior stations whose 2° wedges intersect in an equilateral triangle.

    For each side AB, the station sits on the outward perpendicular bisector so
    that angle ASB = 2°. Intersection of the three cones is the triangle.
    Jung: R_sec = side/sqrt(3) > side/2, diametral circle does not cover.
    """
    h = side * math.sqrt(3.0) / 2.0
    cx, cy = center
    a = (cx, cy + 2.0 * h / 3.0)
    b = (cx - side / 2.0, cy - h / 3.0)
    c = (cx + side / 2.0, cy - h / 3.0)
    verts = [a, b, c]
    dist_mid = (side / 2.0) / math.tan(math.radians(ERR_DEG))
    stations: list[Point] = []
    bearings: list[float] = []
    sides = [(a, b, c), (b, c, a), (c, a, b)]
    for p, q, opp in sides:
        mid = (0.5 * (p[0] + q[0]), 0.5 * (p[1] + q[1]))
        outward = vsub(mid, opp)
        nrm = hypot(outward)
        u = (outward[0] / nrm, outward[1] / nrm)
        s = (mid[0] + dist_mid * u[0], mid[1] + dist_mid * u[1])
        th = bearing_deg(mid, s)
        stations.append(s)
        bearings.append(th)
    poly = intersect_wedges(stations, bearings, err_deg=ERR_DEG, clip_arena=False)
    return {
        "side": side,
        "triangle": verts,
        "stations": stations,
        "bearings_deg": bearings,
        "polygon": poly,
        "dist_mid": dist_mid,
    }


def helper_quad_points(station_a: Point, ba: float, station_b: Point, bb: float, err_deg: float = ERR_DEG) -> list[Point]:
    from jianmo.b_sim import intersection_quad

    try:
        return list(intersection_quad(station_a, ba, station_b, bb, err_deg=err_deg))
    except ValueError:
        return []


def q4_fill_scouts(*, fill_r: float = 1850.0, n_ring: int = 8) -> list[Point]:
    """Inner-spoke fill at 1850 m. Collinear outward case, not a covering theorem."""
    return [
        (
            fill_r * math.cos(2.0 * math.pi * k / n_ring),
            fill_r * math.sin(2.0 * math.pi * k / n_ring),
        )
        for k in range(n_ring)
    ]


def q4_operational_scouts(
    *,
    inner_r: float = 950.0,
    outer_r: float = 2100.0,
    fill_r: float = 1850.0,
    n_ring: int = 8,
) -> list[Point]:
    """Abandoned staggered 17+fill net. Not the Q4 discovery scheme."""
    return list(q4_staggered_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring)) + q4_fill_scouts(
        fill_r=fill_r, n_ring=n_ring
    )


def _positive_quadratic_roots(b: float, const: float) -> list[float]:
    disc = b * b - 4.0 * const
    if disc < 0.0:
        return []
    root = math.sqrt(disc)
    return [x for x in (0.5 * (-b - root), 0.5 * (-b + root)) if x > 0.0]


def q4_heading_cover_leftover(
    *,
    r: float = 1000.0,
    r_eff: float = 1000.0,
    inner_r: float = 950.0,
    fill_r: float = 1850.0,
    outer_r: float = 2100.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """Named leftover witness G_L of the abandoned 17+8 net.

    G_L = r ∠ (180°/n) on an inner-ring bisector. Default r = R_eff puts G_L
    on the origin-disk boundary. Origin + two adjacent inner scouts are in
    range; spoke-fill and the co-bisector outer are not. γ(G_L)>180°, so this
    point is in leftover {G:γ(G)>180°} ∩ K_0.

    The bisector leftover interval is (apothem, r_F), where r_F is the spoke
    fill's enter radius. Only (apothem, R_eff] lies in K_0 = C_0 \\ T_0,
    because C_0 ⊆ D(O, R_eff). The open shell (R_eff, r_F) is leftover
    outside ∪K_k: O is out of range, fill and outer are not yet in range,
    N={I_0,I_1}, and G sits outside the chord. Do not write that interval as
    a slice of K_0, and do not write leftover ⊆ ∪K_k from a disk sample
    (uniform samples miss a ~3 m shell).

    Leftover ≠ K_k: G_S=(R_eff,0) is in K_0 and heading-covered. Leftover ⊆
    complement(octagon) by the octagon lemma. G_★ = 1200∠22.5° is not
    leftover. 1-scout of origin+inner is nonempty; ρ < R_eff only gives #N ≥ 1.
    """
    alpha = math.pi / n_ring
    point = (r * math.cos(alpha), r * math.sin(alpha))
    net = q4_operational_scouts(inner_r=inner_r, outer_r=outer_r, fill_r=fill_r, n_ring=n_ring)
    near = scouts_within(point, net, r_eff)
    gamma = heading_cover_max_gap_deg(point, net, r_eff)
    pair = two_sided_max_angle_deg(point, net, r_eff)
    fill0 = (fill_r, 0.0)
    outer_bis = (outer_r * math.cos(alpha), outer_r * math.sin(alpha))
    worst_h = 180.0 / n_ring
    r_lo = inner_r * math.cos(alpha)
    fill_roots = _positive_quadratic_roots(-2.0 * fill_r * math.cos(alpha), fill_r * fill_r - r_eff * r_eff)
    r_hi = min(fill_roots) if fill_roots else float("nan")
    covering = q4_staggered_covering_radius(inner_r=inner_r, n_ring=n_ring, r_eff=r_eff)
    gstar = (1200.0 * math.cos(alpha), 1200.0 * math.sin(alpha))
    stagger = list(q4_staggered_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring))
    gamma_star = heading_cover_max_gap_deg(gstar, stagger, r_eff)
    pair_star = two_sided_max_angle_deg(gstar, stagger, r_eff)
    return {
        "x": point[0],
        "y": point[1],
        "r_m": r,
        "angle_deg": worst_h,
        "n_scouts_in_range": float(len(near)),
        "gamma_deg": float(gamma),
        "pair_angle_deg": float(pair),
        "worst_heading_deg": worst_h,
        "all_near_backlobe_at_worst_h": bool(
            all(closed_lobe_dot(s, point, worst_h) < 0.0 for s in near)
        ),
        "fill_distance_m": hypot(fill0, point),
        "outer_bisector_distance_m": hypot(outer_bis, point),
        "heading_covered": bool(gamma <= 180.0 + 1e-9),
        "one_scout_vacuous": False,
        "covering_radius_m": float(covering["covering_radius_m"]),
        "rho_lt_reff": bool(float(covering["covering_radius_m"]) <= r_eff + 1e-12),
        "bisector_leftover_r_lo_m": float(r_lo),
        "bisector_leftover_r_hi_m": float(r_hi),
        "in_bisector_leftover": bool(r_lo < r < r_hi),
        "cap_slice_r_hi_m": float(r_eff),
        "shell_r_lo_m": float(r_eff),
        "shell_r_hi_m": float(r_hi),
        "in_cap_slice": bool(r_lo < r <= r_eff + 1e-12),
        "in_shell_outside_cap": bool(r_eff < r < r_hi),
        "gstar_gamma_deg": float(gamma_star),
        "gstar_pair_angle_deg": float(pair_star),
        "gstar_heading_covered": bool(gamma_star <= 180.0 + 1e-9),
        "gstar_two_sided": bool(pair_star >= 90.0 - 1e-9),
    }


def q4_staggered_fill1850_collinear_outward(
    r_source: float,
    *,
    inner_r: float = 950.0,
    fill_r: float = 1850.0,
    outer_r: float = 2100.0,
    r_eff: float = 1000.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """Collinear +radial source on an inner spoke of the staggered net.

    Hypothesis: G=(r,0), H=+x, R_eff as given. Inner@inner_r is behind for
    r>inner_r. Staggered outers sit at phase π/n, so they are not on this
    spoke; they enter range iff r is in the law-of-cosines interval against
    R_eff. Fill@fill_r on the spoke is in the forward half-plane for r<fill_r
    and in range iff fill_r−r ≤ R_eff. Other headings are outside this
    proposition. Not a covering theorem.
    """
    source = (r_source, 0.0)
    heading = 0.0
    inner = (inner_r, 0.0)
    fill = (fill_r, 0.0)
    alpha = math.pi / n_ring
    outer = (outer_r * math.cos(alpha), outer_r * math.sin(alpha))

    def row(station: Point) -> dict[str, float | bool]:
        dist = hypot(station, source)
        lobe = in_closed_lobe(station, source, heading)
        return {
            "distance_m": dist,
            "in_lobe": lobe,
            "in_range": bool(dist <= r_eff + 1e-12),
            "hears": bool(lobe and dist <= r_eff + 1e-12),
        }

    inner_row, fill_row, outer_row = row(inner), row(fill), row(outer)
    outer_roots = _positive_quadratic_roots(
        -2.0 * outer_r * math.cos(alpha), outer_r * outer_r - r_eff * r_eff
    )
    r_outer_lo = min(outer_roots) if outer_roots else float("nan")
    return {
        "r_source_m": r_source,
        "inner_hears": inner_row["hears"],
        "fill_hears": fill_row["hears"],
        "outer_hears": outer_row["hears"],
        "inner_in_lobe": inner_row["in_lobe"],
        "fill_in_lobe": fill_row["in_lobe"],
        "outer_in_lobe": outer_row["in_lobe"],
        "inner_distance_m": inner_row["distance_m"],
        "fill_distance_m": fill_row["distance_m"],
        "outer_distance_m": outer_row["distance_m"],
        "staggered_outer_enter_m": float(r_outer_lo),
        "in_stated_interval": bool(inner_r < r_source < r_outer_lo),
    }


def point_in_convex_hull(point: Point, pts: Sequence[Point], *, eps: float = 1e-9) -> bool:
    """Closed convex hull membership in the plane."""
    if not pts:
        return False
    uniq: list[Point] = []
    for q in pts:
        if all(hypot(q, u) > eps for u in uniq):
            uniq.append(q)
    if any(hypot(point, q) <= eps for q in uniq):
        return True
    if len(uniq) == 1:
        return False
    if len(uniq) == 2:
        a, b = uniq
        ab = (b[0] - a[0], b[1] - a[1])
        ap = (point[0] - a[0], point[1] - a[1])
        cross = ab[0] * ap[1] - ab[1] * ap[0]
        if abs(cross) > 1e-6:
            return False
        dot_ab = ab[0] * ap[0] + ab[1] * ap[1]
        return -eps <= dot_ab <= ab[0] * ab[0] + ab[1] * ab[1] + eps

    def cross(o: Point, a: Point, b: Point) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    pts_sorted = sorted(uniq)
    lower: list[Point] = []
    upper: list[Point] = []
    for q in pts_sorted:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in reversed(pts_sorted):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    hull = lower[:-1] + upper[:-1]
    pos = neg = False
    for i, a in enumerate(hull):
        b = hull[(i + 1) % len(hull)]
        c = cross(a, b, point)
        if c > eps:
            pos = True
        if c < -eps:
            neg = True
    return not (pos and neg)


def heading_cover_iff_in_conv(
    point: Point,
    scouts: Sequence[Point],
    r_eff: float,
    *,
    atol: float = 1e-9,
) -> dict[str, float | bool]:
    """γ(G)≤180° iff G is coincident with a scout or G ∈ conv(N(G))."""
    near = scouts_within(point, scouts, r_eff, atol=atol)
    gamma = heading_cover_max_gap_deg(point, scouts, r_eff, atol=atol)
    in_conv = point_in_convex_hull(point, near, eps=max(atol, 1e-9))
    heading = bool(gamma <= 180.0 + 1e-9)
    return {
        "gamma_deg": float(gamma),
        "n_neighbors": float(len(near)),
        "in_conv": bool(in_conv),
        "heading_covered": heading,
        "iff_agrees": bool(heading == in_conv),
    }


def q4_heading_cover_cap(
    *,
    r_eff: float = 1000.0,
    inner_r: float = 950.0,
    fill_r: float = 1850.0,
    outer_r: float = 2100.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """Octagon lemma plus leftover witness G_L in K_0. Leftover ≠ K_k.

    Octagon lemma: each triangle T_k=conv({S0,I_k,I_{k+1}}) has sides
    ≤ inner_r < R_eff, so T_k ⊂ C_k := D(S0,R)∩D(I_k,R)∩D(I_{k+1},R)
    and every G∈T_k is heading-covered. Union of T_k is the regular
    octagon with vertices I_k (apothem inner_r cos(π/n)). Leftover
    {γ>180°} ⊆ complement(octagon).

    Cap K_k = C_k \\ T_k is where leftover *can* occur if N(G) is exactly
    the three vertices. Leftover ≠ K_k by two named points: G_L ∈ leftover
    ∩ K_0, and G_S=(R_eff,0) ∈ K_0 with γ≤180°. Leftover ⊈ ∪K_k: the
    bisector shell (R_eff, r_F) is leftover with O out of range. Fill@1850
    does not close G_L. ρ < R_eff does not empty the 1-scout set of
    origin+inner. D(O,R_eff) ∩ sector_k ⊆ C_k, so D(O,R_eff)\\octagon ⊆ ∪K_k;
    that inclusion does not cover the shell.
    """
    alpha = math.pi / n_ring
    apothem = inner_r * math.cos(alpha)
    chord = 2.0 * inner_r * math.sin(alpha)
    triangle_max_side = max(inner_r, chord)
    octagon_heading_ok = bool(triangle_max_side <= r_eff + 1e-12)
    theta_star = math.degrees(math.acos(max(-1.0, min(1.0, fill_r / (2.0 * r_eff)))))
    sector_deg = 180.0 / n_ring
    sliver_lo = theta_star
    sliver_hi = 2.0 * sector_deg - theta_star
    sliver_nonempty = bool(fill_r > 2.0 * r_eff * math.cos(alpha) + 1e-12)
    gl_ang = sector_deg
    gl_in_sliver = bool(sliver_lo < gl_ang < sliver_hi)
    leftover = q4_heading_cover_leftover(
        r=r_eff, r_eff=r_eff, inner_r=inner_r, fill_r=fill_r, outer_r=outer_r, n_ring=n_ring
    )
    net = q4_operational_scouts(inner_r=inner_r, outer_r=outer_r, fill_r=fill_r, n_ring=n_ring)
    gl = (float(leftover["x"]), float(leftover["y"]))
    iff = heading_cover_iff_in_conv(gl, net, r_eff)
    i0 = (inner_r, 0.0)
    i1 = (inner_r * math.cos(2.0 * alpha), inner_r * math.sin(2.0 * alpha))
    s0 = (0.0, 0.0)
    gl_in_triangle = point_in_convex_hull(gl, [s0, i0, i1])
    gl_in_three_disks = bool(
        hypot(gl, s0) <= r_eff + 1e-12
        and hypot(gl, i0) <= r_eff + 1e-12
        and hypot(gl, i1) <= r_eff + 1e-12
    )
    spoke = q4_spoke_cap_heading_witness(
        r_eff=r_eff, inner_r=inner_r, fill_r=fill_r, outer_r=outer_r, n_ring=n_ring
    )
    shell = q4_shell_leftover_witness(
        r_eff=r_eff, inner_r=inner_r, fill_r=fill_r, outer_r=outer_r, n_ring=n_ring
    )
    sector = q4_sector_disk_subset_ck(r_eff=r_eff, inner_r=inner_r, n_ring=n_ring)
    gl_in_cap = bool(gl_in_three_disks and not gl_in_triangle)
    gl_leftover = bool(leftover["gamma_deg"] > 180.0)
    gs_in_cap_heading = bool(spoke["in_cap"] and spoke["heading_covered"])
    shell_leftover_out = bool(shell["leftover"] and not shell["in_cap"])
    return {
        "octagon_apothem_m": float(apothem),
        "inner_chord_m": float(chord),
        "triangle_max_side_m": float(triangle_max_side),
        "octagon_heading_covered": octagon_heading_ok,
        "origin_circle_theta_star_deg": float(theta_star),
        "origin_circle_sliver_lo_deg": float(sliver_lo),
        "origin_circle_sliver_hi_deg": float(sliver_hi),
        "origin_circle_sliver_nonempty": sliver_nonempty,
        "gl_in_origin_circle_sliver": gl_in_sliver,
        "gl_in_triangle": bool(gl_in_triangle),
        "gl_in_three_disks": gl_in_three_disks,
        "gl_in_cap": gl_in_cap,
        "gl_gamma_deg": float(leftover["gamma_deg"]),
        "gl_heading_covered": bool(leftover["heading_covered"]),
        "gl_fill_distance_m": float(leftover["fill_distance_m"]),
        "gl_outer_distance_m": float(leftover["outer_bisector_distance_m"]),
        "gl_iff_agrees": bool(iff["iff_agrees"]),
        "gstar_heading_covered": bool(leftover["gstar_heading_covered"]),
        "covering_radius_m": float(leftover["covering_radius_m"]),
        "one_scout_vacuous": False,
        "gs_in_cap": bool(spoke["in_cap"]),
        "gs_heading_covered": bool(spoke["heading_covered"]),
        "gs_gamma_deg": float(spoke["gamma_deg"]),
        "gs_fill_distance_m": float(spoke["fill_distance_m"]),
        "shell_r_m": float(shell["r_m"]),
        "shell_gamma_deg": float(shell["gamma_deg"]),
        "shell_in_cap": bool(shell["in_cap"]),
        "shell_heading_covered": bool(shell["heading_covered"]),
        "shell_n_scouts": float(shell["n_scouts"]),
        "shell_r_lo_m": float(shell["shell_r_lo_m"]),
        "shell_r_hi_m": float(shell["shell_r_hi_m"]),
        "sector_disk_max_inner_dist_m": float(sector["max_inner_dist_m"]),
        "sector_disk_subset_ck": bool(sector["subset_ck"]),
        "leftover_equals_cap": False,
        "leftover_subseteq_cap": False,
        "leftover_neq_cap_named": bool(gl_leftover and gl_in_cap and gs_in_cap_heading),
        "leftover_outside_cap_named": bool(shell_leftover_out),
        "gl_is_leftover_witness": bool(gl_leftover and gl_in_cap),
    }


def q4_spoke_cap_heading_witness(
    *,
    r_eff: float = 1000.0,
    inner_r: float = 950.0,
    fill_r: float = 1850.0,
    outer_r: float = 2100.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """Named point G_S=(R_eff, 0) ∈ K_0 with γ≤180°. Proves leftover ≠ K_0.

    T_0=conv{O,I_0,I_1} has maximum x-coordinate inner_r, so G_S is outside
    T_0. Distances to O, I_0, I_1 are R_eff, R_eff−inner_r, and the 45°
    law-of-cosines value, all ≤ R_eff, hence G_S ∈ C_0 \\ T_0 = K_0. Spoke
    fill at (fill_r, 0) is in range (fill_r−R_eff ≤ R_eff when fill_r ≤ 2 R_eff)
    and G_S lies on the segment I_0 Fill, so G_S ∈ conv(N(G_S)).
    """
    gs = (r_eff, 0.0)
    net = q4_operational_scouts(inner_r=inner_r, outer_r=outer_r, fill_r=fill_r, n_ring=n_ring)
    mem = q4_cap_membership(gs, inner_r=inner_r, n_ring=n_ring, r_eff=r_eff)
    iff = heading_cover_iff_in_conv(gs, net, r_eff)
    fill0 = (fill_r, 0.0)
    i0 = (inner_r, 0.0)
    return {
        "x": gs[0],
        "y": gs[1],
        "in_cap": bool(mem["in_k0"]),
        "in_octagon": bool(mem["in_octagon"]),
        "heading_covered": bool(iff["heading_covered"]),
        "in_conv": bool(iff["in_conv"]),
        "gamma_deg": float(iff["gamma_deg"]),
        "n_scouts": float(iff["n_neighbors"]),
        "fill_distance_m": hypot(gs, fill0),
        "inner0_distance_m": hypot(gs, i0),
        "on_spoke_segment": bool(inner_r <= gs[0] <= fill_r + 1e-12),
        "iff_agrees": bool(iff["iff_agrees"]),
    }


def q4_shell_leftover_witness(
    *,
    r_eff: float = 1000.0,
    inner_r: float = 950.0,
    fill_r: float = 1850.0,
    outer_r: float = 2100.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """Named leftover point in the bisector shell (R_eff, r_F), outside ∪K_k.

    r_F is the smaller positive root of ||r∠(π/n) − (fill_r, 0)|| = R_eff.
    Midpoint r_M = (R_eff + r_F)/2. At that point O is out of range, so the
    point cannot lie in any C_k ⊆ D(O, R_eff). Adjacent inners are in range;
    fill and the co-bisector outer are not. N has two points, G is outside
    their chord, γ>180°. This is the named remainder of leftover ⊆ ∪K_k.
    """
    alpha = math.pi / n_ring
    fill_roots = _positive_quadratic_roots(-2.0 * fill_r * math.cos(alpha), fill_r * fill_r - r_eff * r_eff)
    r_f = min(fill_roots) if fill_roots else float("nan")
    r_m = 0.5 * (r_eff + r_f)
    point = (r_m * math.cos(alpha), r_m * math.sin(alpha))
    net = q4_operational_scouts(inner_r=inner_r, outer_r=outer_r, fill_r=fill_r, n_ring=n_ring)
    mem = q4_cap_membership(point, inner_r=inner_r, n_ring=n_ring, r_eff=r_eff)
    iff = heading_cover_iff_in_conv(point, net, r_eff)
    fill0 = (fill_r, 0.0)
    outer_bis = (outer_r * math.cos(alpha), outer_r * math.sin(alpha))
    origin_dist = hypot(point)
    return {
        "x": point[0],
        "y": point[1],
        "r_m": float(r_m),
        "angle_deg": 180.0 / n_ring,
        "shell_r_lo_m": float(r_eff),
        "shell_r_hi_m": float(r_f),
        "in_open_shell": bool(r_eff < r_m < r_f),
        "origin_distance_m": float(origin_dist),
        "origin_in_range": bool(origin_dist <= r_eff + 1e-12),
        "in_cap": bool(mem["in_some_cap"]),
        "in_octagon": bool(mem["in_octagon"]),
        "heading_covered": bool(iff["heading_covered"]),
        "leftover": bool(not iff["heading_covered"]),
        "in_conv": bool(iff["in_conv"]),
        "gamma_deg": float(iff["gamma_deg"]),
        "n_scouts": float(iff["n_neighbors"]),
        "fill_distance_m": hypot(point, fill0),
        "outer_bisector_distance_m": hypot(point, outer_bis),
        "iff_agrees": bool(iff["iff_agrees"]),
    }


def q4_sector_disk_subset_ck(
    *,
    r_eff: float = 1000.0,
    inner_r: float = 950.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """D(O, R_eff) ∩ sector_k ⊆ C_k. Analytic max to I_k, I_{k+1} is inner_r.

    On the closed sector θ∈[0, 2π/n], r∈[0, R_eff], ||G−I_0||² = r²+inner_r²
    − 2 r inner_r cos θ. For fixed r this is max at max θ. On θ=2π/n the
    r-derivative 2(r − inner_r cos(2π/n)) vanishes at r = inner_r cos(2π/n)
    < R_eff, a minimum, so the maximum on the rectangle is at r=0 and equals
    inner_r. Symmetric for I_1. Hence max = inner_r < R_eff, the sector disk
    sits in C_0, and D(O, R_eff)\\octagon ⊆ ∪K_k. The bisector shell r>R_eff
    is outside this inclusion.
    """
    alpha = math.pi / n_ring
    max_at_origin = inner_r
    i0 = (inner_r, 0.0)
    i1 = (inner_r * math.cos(2.0 * alpha), inner_r * math.sin(2.0 * alpha))
    far_corner = (r_eff * math.cos(alpha), r_eff * math.sin(alpha))
    far_spoke = (r_eff, 0.0)
    d_origin_i0 = hypot((0.0, 0.0), i0)
    d_corner_i0 = hypot(far_corner, i0)
    d_spoke_i1 = hypot(far_spoke, i1)
    max_inner = max(d_origin_i0, d_corner_i0, d_spoke_i1, max_at_origin)
    return {
        "max_inner_dist_m": float(max_at_origin),
        "origin_to_inner_m": float(d_origin_i0),
        "gl_to_inner_m": float(d_corner_i0),
        "spoke_to_adjacent_inner_m": float(d_spoke_i1),
        "checked_boundary_max_m": float(max_inner),
        "inner_r_m": float(inner_r),
        "subset_ck": bool(max_at_origin <= r_eff + 1e-12 and max_inner <= r_eff + 1e-12),
        "covers_shell": False,
    }


def q4_bisector_fill_scouts(*, fill_r: float = 1500.0, n_ring: int = 8) -> list[Point]:
    """Comparison only: fill on inner-ring bisectors. Not the chosen net."""
    phase = math.pi / n_ring
    return [
        (fill_r * math.cos(phase + 2.0 * math.pi * k / n_ring), fill_r * math.sin(phase + 2.0 * math.pi * k / n_ring))
        for k in range(n_ring)
    ]


def q4_inner9_scouts(*, inner_r: float = 950.0, n_ring: int = 8) -> list[Point]:
    """Origin plus inner n-ring. Omni covering net of the Q4 staggered design."""
    return [(0.0, 0.0)] + [
        (inner_r * math.cos(2.0 * math.pi * k / n_ring), inner_r * math.sin(2.0 * math.pi * k / n_ring))
        for k in range(n_ring)
    ]


def q3_nine_disk_origin_check(
    *,
    ring_r: float = 1000.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """Origin of the Q3 9-disk: min to the 8-ring is 1000 > ρ; min to the 9-net is 0."""
    from jianmo.b_sim.geometry import q3_omni_scouts as _q3_scouts

    net = list(_q3_scouts(ring_r=ring_r, n_ring=n_ring))
    origin = (0.0, 0.0)
    ring = [s for s in net if hypot(s) > 1e-9]
    d_ring = min(hypot(origin, s) for s in ring)
    d9 = min(hypot(origin, s) for s in net)
    cert = q3_omni_covering_radius(ring_r=ring_r, n_ring=n_ring)
    rho = float(cert["covering_radius_m"])
    return {
        "n_net": float(len(net)),
        "n_ring": float(len(ring)),
        "origin_min_to_ring_m": float(d_ring),
        "origin_min_to_nine_m": float(d9),
        "covering_radius_m": rho,
        "eight_ring_min_at_origin_le_rho": bool(d_ring <= rho + 1e-12),
        "nine_disk_min_at_origin_le_rho": bool(d9 <= rho + 1e-12),
    }


def q4_spoke_i1_exit_r(*, inner_r: float = 950.0, r_eff: float = 1000.0) -> float:
    """Spoke radius where ||G−I_1|| = R_eff for G=(r,0). Closed 1-scout needs r larger."""
    b = -2.0 * inner_r * math.cos(math.pi / 4.0)
    const = inner_r * inner_r - r_eff * r_eff
    disc = b * b - 4.0 * const
    roots = [0.5 * (-b - math.sqrt(disc)), 0.5 * (-b + math.sqrt(disc))]
    pos = [x for x in roots if x > 0.0]
    return max(pos)


def q4_one_scout_witness(
    *,
    inner_r: float = 950.0,
    outer_r: float = 2100.0,
    r_eff: float = 1000.0,
    n_ring: int = 8,
) -> dict[str, float | bool]:
    """Origin+inner 1-scout is nonempty: G=(1800,0) has N={I_0}, γ=360°.

    ρ < R_eff only gives #N ≥ 1. The staggered outer ring covers this spoke
    residual (distance 815.76 m at the arena end, 961.36 m at the I_1-exit
    limit), so 17-net 1-scout emptiness is an outer-ring statement, not the
    omni covering lemma.
    """
    g1 = (1800.0, 0.0)
    inner = q4_inner9_scouts(inner_r=inner_r, n_ring=n_ring)
    stagger = list(q4_staggered_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring))
    op = q4_operational_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring)
    near9 = scouts_within(g1, inner, r_eff)
    near17 = scouts_within(g1, stagger, r_eff)
    near_op = scouts_within(g1, op, r_eff)
    covering = q4_staggered_covering_radius(inner_r=inner_r, n_ring=n_ring, r_eff=r_eff)
    r_exit = q4_spoke_i1_exit_r(inner_r=inner_r, r_eff=r_eff)
    alpha = math.pi / n_ring
    outer0 = (outer_r * math.cos(alpha), outer_r * math.sin(alpha))
    p_exit = (r_exit, 0.0)
    d_exit = hypot(p_exit, outer0)
    d_arena = hypot(g1, outer0)
    rho = float(covering["covering_radius_m"])
    return {
        "x": g1[0],
        "y": g1[1],
        "n_inner9": float(len(near9)),
        "gamma_inner9_deg": float(heading_cover_max_gap_deg(g1, inner, r_eff)),
        "one_scout_on_inner9": bool(len(near9) == 1),
        "inner9_one_scout_empty": False,
        "rho_m": rho,
        "rho_lt_reff": bool(rho <= r_eff + 1e-12),
        "rho_lt_reff_implies_one_scout_empty": False,
        "n_stagger17": float(len(near17)),
        "n_operational": float(len(near_op)),
        "gamma_operational_deg": float(heading_cover_max_gap_deg(g1, op, r_eff)),
        "d_inner0_m": hypot(g1, (inner_r, 0.0)),
        "spoke_i1_exit_r_m": float(r_exit),
        "spoke_exit_outer_dist_m": float(d_exit),
        "spoke_arena_outer_dist_m": float(d_arena),
        "stagger_hears_g1": bool(len(near17) >= 2),
        "outer_covers_spoke_onescout_limit": bool(d_exit <= r_eff + 1e-12 and d_arena <= r_eff + 1e-12),
    }


def q4_polar_one_scout_check(
    *,
    n_r: int = 24,
    n_th: int = 111,
    arena_r: float = 1800.0,
    r_eff: float = 1000.0,
    inner_r: float = 950.0,
    outer_r: float = 2100.0,
    n_ring: int = 8,
) -> dict[str, float]:
    """Polar grid check of #N=1. Not a covering theorem.

    Radii r = arena_r * k / n_r for k=1..n_r, angles 2π j / n_th.
    Origin+inner 1-scout is nonempty on this grid; 17-net and 17+8 are empty
    on this grid because the outer ring covers the inner 1-scout residual.
    """
    inner = q4_inner9_scouts(inner_r=inner_r, n_ring=n_ring)
    stagger = list(q4_staggered_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring))
    op = q4_operational_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring)
    n_pts = 0
    n1_inner = n1_stagger = n1_op = 0
    r_min = float("inf")
    r_max = 0.0
    for i in range(1, n_r + 1):
        rr = arena_r * i / n_r
        for j in range(n_th):
            th = 2.0 * math.pi * j / n_th
            p = (rr * math.cos(th), rr * math.sin(th))
            n_pts += 1
            if len(scouts_within(p, inner, r_eff)) == 1:
                n1_inner += 1
                r_min = min(r_min, rr)
                r_max = max(r_max, rr)
            if len(scouts_within(p, stagger, r_eff)) == 1:
                n1_stagger += 1
            if len(scouts_within(p, op, r_eff)) == 1:
                n1_op += 1
    return {
        "n_points": float(n_pts),
        "inner9_one_scout_n": float(n1_inner),
        "stagger17_one_scout_n": float(n1_stagger),
        "operational_one_scout_n": float(n1_op),
        "inner9_one_scout_r_lo_m": float(r_min if n1_inner else float("nan")),
        "inner9_one_scout_r_hi_m": float(r_max if n1_inner else float("nan")),
        "is_theorem": 0.0,
    }


def q4_cap_membership(
    point: Point,
    *,
    inner_r: float = 950.0,
    n_ring: int = 8,
    r_eff: float = 1000.0,
) -> dict[str, bool]:
    """Octagon / K_k membership. Leftover ⊆ complement(octagon); leftover ≠ K_k."""
    s0 = (0.0, 0.0)
    in_oct = False
    in_any_k = False
    in_k0 = False
    for k in range(n_ring):
        a0 = 2.0 * math.pi * k / n_ring
        a1 = 2.0 * math.pi * ((k + 1) % n_ring) / n_ring
        ia = (inner_r * math.cos(a0), inner_r * math.sin(a0))
        ib = (inner_r * math.cos(a1), inner_r * math.sin(a1))
        tri = point_in_convex_hull(point, [s0, ia, ib])
        ck = bool(
            hypot(point, s0) <= r_eff + 1e-12
            and hypot(point, ia) <= r_eff + 1e-12
            and hypot(point, ib) <= r_eff + 1e-12
        )
        if tri:
            in_oct = True
        if ck and not tri:
            in_any_k = True
            if k == 0:
                in_k0 = True
    return {"in_octagon": in_oct, "in_some_cap": in_any_k, "in_k0": in_k0}


def q4_lattice_hears(
    source: Point,
    heading_deg: float,
    scouts: Sequence[Point] | None = None,
    *,
    r_eff: float = 1000.0,
) -> bool:
    """Closed-lobe detection at some scout: ||S-G||≤R_eff and (S-G)·u_H≥0."""
    net = list(scouts) if scouts is not None else list(q4_certainty_scouts())
    for station in net:
        if hypot(station, source) <= r_eff + 1e-12 and in_closed_lobe(station, source, heading_deg):
            return True
    return False


def q4_optical_grid_certificate(*, step: float = 25.0, r_clear: float = 20.0) -> dict[str, float | bool]:
    """Square cells of side `step`: circumradius step/√2. Covers iff that radius < 20 m."""
    rho = step / math.sqrt(2.0)
    return {
        "step_m": float(step),
        "cell_circumradius_m": float(rho),
        "covers": bool(rho < r_clear - 1e-12),
        "optical_grid_covers_fn": bool(optical_grid_covers(step, r_clear=r_clear)),
    }


def q4_lattice_certainty() -> dict[str, float | bool]:
    """Closed-form Q4 discovery certificate (triangular lattice, not a cover fraction)."""
    row = directional_certainty_params()
    pts = q4_certainty_scouts()
    spacing = float(row["spacing_m"])
    shift_a = float(row["shift_a_m"])
    rho = float(row["covering_radius_m"])
    circ = (spacing / 2.0, spacing * math.sqrt(3.0) / 6.0)
    s_max = 0.5 * 1000.0 * math.sqrt(3.0)
    s900 = directional_certainty_params(spacing=900.0)
    optical = q4_optical_grid_certificate(step=25.0)
    return {
        "spacing_m": spacing,
        "shift_a_m": shift_a,
        "covering_radius_m": rho,
        "q_disk_radius_m": float(row["q_disk_radius_m"]),
        "lattice_disk_radius_m": float(row["lattice_disk_radius_m"]),
        "n_points": float(len(pts)),
        "a_plus_rho_m": float(row["a_plus_rho_m"]),
        "a_minus_rho_m": float(row["a_minus_rho_m"]),
        "range_ok": bool(row["range_ok"]),
        "halfplane_ok": bool(row["halfplane_ok"]),
        "exists_a": bool(row["exists_a"]),
        "triangle_circumradius_m": float(math.hypot(circ[0], circ[1])),
        "s_max_m": float(s_max),
        "s_design_lt_s_max": bool(spacing < s_max - 1e-12),
        "s900_covering_radius_m": float(s900["covering_radius_m"]),
        "s900_exists_a": bool(s900["exists_a"]),
        "optical_step_m": float(optical["step_m"]),
        "optical_cell_circumradius_m": float(optical["cell_circumradius_m"]),
        "optical_covers": bool(optical["covers"]),
        "formula_rho": float(triangular_covering_radius(spacing)),
    }


def q4_lattice_grid_check(
    *,
    n_r: int = 8,
    n_th: int = 16,
    n_h: int = 12,
    arena_r: float = 1800.0,
    r_eff: float = 1000.0,
) -> dict[str, float]:
    """Polar×heading grid check of the lattice detection lemma. Not the covering model."""
    scouts = q4_certainty_scouts()
    cert = q4_lattice_certainty()
    rho = float(cert["covering_radius_m"])
    shift_a = float(cert["shift_a_m"])
    n_pts = 0
    n_fail = 0
    max_q = 0.0
    for i in range(1, n_r + 1):
        rr = arena_r * i / n_r
        for j in range(n_th):
            th = 2.0 * math.pi * j / n_th
            source = (rr * math.cos(th), rr * math.sin(th))
            for k in range(n_h):
                heading = 360.0 * k / n_h
                n_pts += 1
                urad = math.radians(heading)
                q = (source[0] + shift_a * math.cos(urad), source[1] + shift_a * math.sin(urad))
                nearest = min(math.hypot(s[0] - q[0], s[1] - q[1]) for s in scouts)
                if nearest > max_q:
                    max_q = nearest
                if nearest > rho + 1e-6 or not q4_lattice_hears(source, heading, scouts, r_eff=r_eff):
                    n_fail += 1
    return {
        "n_points": float(n_pts),
        "n_fail": float(n_fail),
        "max_q_nearest_m": float(max_q),
        "rho_m": rho,
        "all_heard": 1.0 if n_fail == 0 else 0.0,
        "q_nearest_le_rho": 1.0 if max_q <= rho + 1e-6 else 0.0,
        "is_theorem": 0.0,
    }
