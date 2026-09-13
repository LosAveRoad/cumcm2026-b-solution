"""White-box ±1° bearing-wedge geometry for CUMCM 2026 B Q1–Q2.

East = 0°, counterclockwise positive. Angles in degrees unless noted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

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


def axis_crossing_psi_deg(r: float, t: float, r_g: float) -> float:
    """Crossing angle on the LOB: cos ψ = (r_G − r) / hypot(r_G − r, t)."""
    if abs(t) < 1e-15:
        if r_g > r:
            return 0.0
        if r_g < r:
            return 180.0
        return 0.0
    c = (r_g - r) / math.hypot(r_g - r, t)
    c = max(-1.0, min(1.0, c))
    return math.degrees(math.acos(c))


def axis_psi_ge45_offset(r: float, r_lo: float, r_hi: float) -> float:
    """|t| such that every axis G with r_G ∈ [r_lo, r_hi] has ψ ≥ 45°.

    On the axis, cos ψ = (r_G − r) / hypot(r_G − r, t). For r_G ≤ r the angle is
    already obtuse (ψ ≥ 90° ≥ 45°). The residual of ψ ≥ 45° is therefore only
    the far side r_G > r, which needs |t| ≥ max(0, r_hi − r). At r = 800 m,
    r_hi = 1500 m this is |t| ≥ 700 m: ψ(1500) = 45°, ψ(5) ≈ 138.64° > 135°.
    """
    del r_lo
    return max(0.0, r_hi - r)


def axis_psi_band_offset(r: float, r_lo: float, r_hi: float) -> float:
    """|t| such that every axis G with r_G ∈ [r_lo, r_hi] has ψ ∈ [45°, 135°].

    Equivalent to |r − r_G| ≤ |t| for all such r_G, hence
    |t| ≥ max(|r − r_lo|, |r_hi − r|). At r = 800 m this is |t| ≥ 795 m.
    This is not the residual of the one-sided predicate ψ ≥ 45°.
    """
    return max(abs(r - r_lo), abs(r_hi - r))


def axis_psi_cover_offset(r: float, r_lo: float, r_hi: float) -> float:
    """[45°, 135°] covering |t|. Not the one-sided ψ ≥ 45° residual."""
    return axis_psi_band_offset(r, r_lo, r_hi)


def wedge_far_corner_point(
    s1: Point,
    theta_deg: float,
    r_g: float,
    err_deg: float = ERR_DEG,
    *,
    t_sign: float = 1.0,
) -> Point:
    """Far corner of the ±err_deg wedge on the same side as sign(t)."""
    alpha = err_deg if t_sign >= 0.0 else -err_deg
    rad = math.radians(theta_deg + alpha)
    return (s1[0] + r_g * math.cos(rad), s1[1] + r_g * math.sin(rad))


def policy_offaxis_far_psi_deg(
    *,
    r: float = 800.0,
    t: float = 700.0,
    r_g: float = 1500.0,
    err_deg: float = ERR_DEG,
) -> float:
    """Crossing angle at the far ±err_deg corner for S2 = S1 + r u + t v.

    The axis lemma gives ψ(r_g)=45° at |t|=r_g−r. This corner is the named
    residual of applying that lemma to the 2° wedge: along each ray from S1,
    ψ = atan2(L sin β, r_G − L cos β) decreases in r_G, so the far end is
    worse than the near end; the same-side corner has smaller β than the
    axis. Not a covering of the wedge.
    """
    s1 = (0.0, 0.0)
    s2 = second_station_point(s1, 0.0, r, t)
    g = wedge_far_corner_point(s1, 0.0, r_g, err_deg, t_sign=t)
    return crossing_angle_deg(s1, s2, g)


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
