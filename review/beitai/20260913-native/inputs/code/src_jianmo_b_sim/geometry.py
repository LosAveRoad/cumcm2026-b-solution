"""White-box intersection localization for CUMCM 2026 B Q1–Q2.

East is 0°, counterclockwise positive. Wedge half-angle defaults to 1°.
"""

from __future__ import annotations

import math
from typing import Sequence

Point = tuple[float, float]


def bearing_vec(deg: float) -> Point:
    rad = math.radians(deg)
    return (math.cos(rad), math.sin(rad))


def _intersect_rays(p1: Point, b1_deg: float, p2: Point, b2_deg: float) -> Point | None:
    d1 = bearing_vec(b1_deg)
    d2 = bearing_vec(b2_deg)
    det = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(det) < 1e-15:
        return None
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    t = (dx * d2[1] - dy * d2[0]) / det
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])


def intersection_quad(
    station_a: Point,
    bearing_a_deg: float,
    station_b: Point,
    bearing_b_deg: float,
    *,
    err_deg: float = 1.0,
) -> list[Point]:
    """Four vertices of the ±err_deg bearing-wedge intersection (交会四边形)."""
    pts: list[Point] = []
    for e1 in (err_deg, -err_deg):
        for e2 in (err_deg, -err_deg):
            hit = _intersect_rays(station_a, bearing_a_deg + e1, station_b, bearing_b_deg + e2)
            if hit is None:
                raise ValueError("bearing rays are parallel; no bounded intersection")
            pts.append(hit)
    return pts


def set_diameter(points: Sequence[Point]) -> tuple[float, Point, Point]:
    if len(points) < 2:
        raise ValueError("need at least two points")
    best = -1.0
    pair = (points[0], points[1])
    for i, p in enumerate(points):
        for q in points[i + 1 :]:
            d = math.hypot(p[0] - q[0], p[1] - q[1])
            if d > best:
                best = d
                pair = (p, q)
    return best, pair[0], pair[1]


def diametral_circle_covers(points: Sequence[Point], *, atol: float = 1e-9) -> dict[str, float | bool]:
    """Circle with a diametral pair as diameter: does it cover the intersection set?"""
    diam, a, b = set_diameter(points)
    cx = 0.5 * (a[0] + b[0])
    cy = 0.5 * (a[1] + b[1])
    radius = 0.5 * diam
    covers = True
    for p in points:
        if math.hypot(p[0] - cx, p[1] - cy) > radius + atol:
            covers = False
            break
    return {"diameter": diam, "radius": radius, "covers": covers, "center_x": cx, "center_y": cy}


ARENA_R = 1800.0
R_EFF_MIN = 1000.0
R_CLEAR = 20.0
Q3_RING_R = 1000.0
Q3_N_RING = 8
Q4_INNER_R = 900.0
Q4_OUTER_R = 2100.0
Q4_FILL_R = 1850.0
Q4_N_RING = 8
Q4_STAGGER_INNER_R = 950.0
Q4_STAGGER_OUTER_R = 2100.0
DIR_SHIFT_A = 500.0
DIR_LATTICE_S = 850.0


def _hypot(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def ring_points(n: int, radius: float, *, phase_rad: float = 0.0) -> list[Point]:
    return [
        (
            radius * math.cos(phase_rad + 2.0 * math.pi * k / n),
            radius * math.sin(phase_rad + 2.0 * math.pi * k / n),
        )
        for k in range(n)
    ]


def q3_omni_scouts(*, ring_r: float = Q3_RING_R, n_ring: int = Q3_N_RING) -> list[Point]:
    return [(0.0, 0.0)] + ring_points(n_ring, ring_r)


def q4_omni_scouts(
    *,
    inner_r: float = Q4_INNER_R,
    outer_r: float = Q4_OUTER_R,
    n_ring: int = Q4_N_RING,
    stagger: bool = False,
) -> list[Point]:
    phase = math.pi / n_ring if stagger else 0.0
    return [(0.0, 0.0)] + ring_points(n_ring, inner_r) + ring_points(n_ring, outer_r, phase_rad=phase)


def q4_staggered_scouts(
    *,
    inner_r: float = Q4_STAGGER_INNER_R,
    outer_r: float = Q4_STAGGER_OUTER_R,
    n_ring: int = Q4_N_RING,
) -> list[Point]:
    return q4_omni_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring, stagger=True)


def arena_boundary_bisector_point(arena_r: float, n_ring: int) -> Point:
    alpha = math.pi / n_ring
    return (arena_r * math.cos(alpha), arena_r * math.sin(alpha))


def ring_boundary_covering_radius(arena_r: float, ring_r: float, n_ring: int) -> float:
    alpha = math.pi / n_ring
    return math.sqrt(arena_r**2 + ring_r**2 - 2.0 * arena_r * ring_r * math.cos(alpha))


def q3_omni_covering_radius(
    *,
    arena_r: float = ARENA_R,
    ring_r: float = Q3_RING_R,
    n_ring: int = Q3_N_RING,
    r_eff: float = R_EFF_MIN,
) -> dict[str, float | bool]:
    worst = arena_boundary_bisector_point(arena_r, n_ring)
    rho = ring_boundary_covering_radius(arena_r, ring_r, n_ring)
    origin_d = math.hypot(worst[0], worst[1])
    return {
        "covers": bool(rho <= r_eff + 1e-12),
        "covering_radius_m": rho,
        "worst_x": worst[0],
        "worst_y": worst[1],
        "worst_angle_deg": math.degrees(math.pi / n_ring),
        "origin_covers_worst": bool(origin_d <= r_eff + 1e-12),
    }


def q4_staggered_covering_radius(
    *,
    arena_r: float = ARENA_R,
    inner_r: float = Q4_STAGGER_INNER_R,
    n_ring: int = Q4_N_RING,
    r_eff: float = R_EFF_MIN,
) -> dict[str, float | bool]:
    info = q3_omni_covering_radius(arena_r=arena_r, ring_r=inner_r, n_ring=n_ring, r_eff=r_eff)
    info["outer_required_for_omni"] = False
    return info


def q4_omni_covering_radius(
    *,
    arena_r: float = ARENA_R,
    inner_r: float = Q4_INNER_R,
    outer_r: float = Q4_OUTER_R,
    n_ring: int = Q4_N_RING,
    r_eff: float = R_EFF_MIN,
) -> dict[str, float | bool]:
    scouts = q4_omni_scouts(inner_r=inner_r, outer_r=outer_r, n_ring=n_ring, stagger=False)
    alpha = math.pi / n_ring
    rho_max = 0.0
    worst = (0.0, 0.0)
    # Rotational symmetry: worst omni distance of the aligned 17-net is on a bisector.
    r = 0.0
    while r <= arena_r + 1e-12:
        p = (r * math.cos(alpha), r * math.sin(alpha))
        dmin = min(_hypot(p, s) for s in scouts)
        if dmin > rho_max:
            rho_max = dmin
            worst = p
        r += 0.01
    return {
        "covers": bool(rho_max <= r_eff + 1e-9),
        "covering_radius_m": rho_max,
        "worst_x": worst[0],
        "worst_y": worst[1],
    }


def scouts_within(point: Point, scouts: Sequence[Point], r_eff: float, *, atol: float = 1e-9) -> list[Point]:
    return [s for s in scouts if _hypot(point, s) <= r_eff + atol]


def angular_separation_deg(p: Point, a: Point, b: Point) -> float:
    ax, ay = a[0] - p[0], a[1] - p[1]
    bx, by = b[0] - p[0], b[1] - p[1]
    na, nb = math.hypot(ax, ay), math.hypot(bx, by)
    if na < 1e-15 or nb < 1e-15:
        return 0.0
    c = max(-1.0, min(1.0, (ax * bx + ay * by) / (na * nb)))
    return math.degrees(math.acos(c))


def two_sided_max_angle_deg(point: Point, scouts: Sequence[Point], r_eff: float, *, atol: float = 1e-9) -> float:
    near = scouts_within(point, scouts, r_eff, atol=atol)
    best = 0.0
    for i, a in enumerate(near):
        for b in near[i + 1 :]:
            best = max(best, angular_separation_deg(point, a, b))
    return best


def two_sided_covered(point: Point, scouts: Sequence[Point], r_eff: float, *, min_deg: float = 90.0) -> bool:
    return two_sided_max_angle_deg(point, scouts, r_eff) + 1e-12 >= min_deg


def heading_cover_max_gap_deg(point: Point, scouts: Sequence[Point], r_eff: float, *, atol: float = 1e-9) -> float:
    near = scouts_within(point, scouts, r_eff, atol=atol)
    if any(_hypot(point, s) <= atol for s in near):
        return 0.0
    if len(near) <= 1:
        return 360.0
    raw = sorted(math.atan2(s[1] - point[1], s[0] - point[0]) for s in near)
    angs: list[float] = []
    for a in raw:
        if not angs or min((a - angs[-1]) % (2.0 * math.pi), (angs[-1] - a) % (2.0 * math.pi)) > 1e-12:
            angs.append(a)
    if len(angs) == 1:
        return 360.0
    max_gap = 0.0
    for i, a in enumerate(angs):
        b = angs[(i + 1) % len(angs)]
        gap = (b - a) % (2.0 * math.pi)
        if gap <= 1e-15:
            gap = 2.0 * math.pi
        max_gap = max(max_gap, math.degrees(gap))
    return max_gap


def q4_twosided_bisector_gap(
    *,
    inner_r: float = Q4_INNER_R,
    r_eff: float = R_EFF_MIN,
    n_ring: int = Q4_N_RING,
) -> dict[str, float]:
    """Radius interval on each 22.5° bisector where only two inner scouts are in range with pair angle <90°."""
    alpha = math.pi / n_ring
    # Two adjacent inners at ±alpha from the bisector, distance r_eff:
    # law of cosines on radii r, inner_r, angle alpha.
    # Solve r such that dist to inner = r_eff, and origin out of range (r>r_eff).
    # dist^2 = r^2 + inner^2 - 2 r inner cos(alpha)
    # At pair angle 90 the geometry is numerical in tests: 86.13° at r=1200.
    def dist_inner(r: float) -> float:
        return math.sqrt(r * r + inner_r * inner_r - 2.0 * r * inner_r * math.cos(alpha))

    # Bracket where origin out, two inners in, pair < 90
    lo, hi = None, None
    for i in range(500, 1801):
        r = float(i)
        if r <= r_eff + 1e-9:
            continue
        d = dist_inner(r)
        p = (r * math.cos(alpha), r * math.sin(alpha))
        i0 = (inner_r, 0.0)
        i1 = (inner_r * math.cos(2 * alpha), inner_r * math.sin(2 * alpha))
        if d <= r_eff + 1e-9:
            ang = angular_separation_deg(p, i0, i1)
            if ang < 90.0 - 1e-9:
                if lo is None:
                    lo = r
                hi = r
    return {"gap_r_lo_m": float(lo or 0.0), "gap_r_hi_m": float(hi or 0.0)}


def q4_twosided_failure_witness(
    *,
    r: float = 1200.0,
    inner_r: float = Q4_INNER_R,
    r_eff: float = R_EFF_MIN,
    arena_r: float = ARENA_R,
    n_ring: int = Q4_N_RING,
) -> dict[str, float | bool]:
    alpha = math.pi / n_ring
    point = (r * math.cos(alpha), r * math.sin(alpha))
    scouts = q4_omni_scouts(inner_r=inner_r, n_ring=n_ring, stagger=False)
    near = scouts_within(point, scouts, r_eff)
    ang = two_sided_max_angle_deg(point, scouts, r_eff)
    gap = q4_twosided_bisector_gap(inner_r=inner_r, r_eff=r_eff, n_ring=n_ring)
    omni = min(_hypot(point, s) for s in scouts) <= r_eff + 1e-9
    return {
        "x": point[0],
        "y": point[1],
        "in_arena": bool(math.hypot(*point) <= arena_r + 1e-9),
        "omni_covered": bool(omni),
        "two_sided": bool(ang + 1e-12 >= 90.0),
        "in_gap": bool(gap["gap_r_lo_m"] < r < gap["gap_r_hi_m"]),
        "n_scouts_in_range": float(len(near)),
        "max_pair_angle_deg": ang,
        "gap_r_lo_m": gap["gap_r_lo_m"],
        "gap_r_hi_m": gap["gap_r_hi_m"],
    }


def in_closed_lobe(station: Point, source: Point, heading_deg: float, *, atol: float = 1e-9) -> bool:
    ux, uy = math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg))
    dx, dy = station[0] - source[0], station[1] - source[1]
    return dx * ux + dy * uy >= -atol


def exact_lob_point(station: Point, source: Point, dist: float) -> Point:
    dx, dy = source[0] - station[0], source[1] - station[1]
    n = math.hypot(dx, dy)
    if n < 1e-15:
        return station
    return (station[0] + dist * dx / n, station[1] + dist * dy / n)


def exact_lob_crosses_into_backlobe(station: Point, source: Point, heading_deg: float, dist: float) -> bool:
    p = exact_lob_point(station, source, dist)
    return not in_closed_lobe(p, source, heading_deg)


def lateral_unit(station: Point, source: Point) -> Point:
    dx, dy = source[0] - station[0], source[1] - station[1]
    n = math.hypot(dx, dy)
    if n < 1e-15:
        return (0.0, 1.0)
    return (-dy / n, dx / n)


def lateral_point(station: Point, source: Point, t: float) -> Point:
    vx, vy = lateral_unit(station, source)
    return (station[0] + t * vx, station[1] + t * vy)


def lateral_stays_in_lobe_for_all_t(
    station: Point, source: Point, heading_deg: float, *, atol: float = 1e-9
) -> bool:
    if not in_closed_lobe(station, source, heading_deg, atol=atol):
        return False
    vx, vy = lateral_unit(station, source)
    ux, uy = math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg))
    return abs(vx * ux + vy * uy) <= atol


def q4_fill1850_collinear_outward(
    r_source: float,
    *,
    inner_r: float = Q4_INNER_R,
    fill_r: float = Q4_FILL_R,
    outer_r: float = Q4_OUTER_R,
    r_eff: float = R_EFF_MIN,
) -> dict[str, float | bool]:
    source = (r_source, 0.0)
    heading = 0.0

    def row(station: Point) -> dict[str, float | bool]:
        dist = _hypot(station, source)
        lobe = in_closed_lobe(station, source, heading)
        return {
            "distance_m": dist,
            "in_lobe": lobe,
            "in_range": bool(dist <= r_eff + 1e-12),
            "hears": bool(lobe and dist <= r_eff + 1e-12),
        }

    inner_row, fill_row, outer_row = row((inner_r, 0.0)), row((fill_r, 0.0)), row((outer_r, 0.0))
    lo, hi = inner_r, outer_r - r_eff
    return {
        "in_stated_interval": bool(lo < r_source < hi),
        "inner_hears": inner_row["hears"],
        "inner_in_lobe": inner_row["in_lobe"],
        "outer_in_lobe": outer_row["in_lobe"],
        "outer_hears": outer_row["hears"],
        "fill_hears": fill_row["hears"],
    }


def triangular_covering_radius(spacing: float) -> float:
    return spacing / math.sqrt(3.0)


def triangular_lattice_points(spacing: float, radius: float) -> list[Point]:
    vx, vy = spacing, 0.0
    wx, wy = spacing / 2.0, spacing * math.sqrt(3.0) / 2.0
    n_max = int(math.ceil(radius / (spacing * math.sqrt(3.0) / 2.0))) + 2
    m_max = int(math.ceil(radius / spacing)) + 2
    pts: list[Point] = []
    for n in range(-n_max, n_max + 1):
        for m in range(-m_max, m_max + 1):
            x = m * vx + n * wx
            y = m * vy + n * wy
            if x * x + y * y <= radius * radius + 1e-9:
                pts.append((x, y))
    pts.sort(key=lambda p: (round(p[0], 9), round(p[1], 9)))
    return pts


def directional_certainty_params(
    *,
    spacing: float = DIR_LATTICE_S,
    shift_a: float = DIR_SHIFT_A,
    r_eff: float = R_EFF_MIN,
    arena_r: float = ARENA_R,
) -> dict[str, float | int | bool]:
    rho = triangular_covering_radius(spacing)
    q_radius = arena_r + shift_a
    cover_radius = q_radius + rho
    pts = triangular_lattice_points(spacing, cover_radius)
    return {
        "spacing_m": spacing,
        "shift_a_m": shift_a,
        "covering_radius_m": rho,
        "q_disk_radius_m": q_radius,
        "lattice_disk_radius_m": cover_radius,
        "n_points": len(pts),
        "a_plus_rho_m": shift_a + rho,
        "a_minus_rho_m": shift_a - rho,
        "range_ok": bool(shift_a + rho < r_eff - 1e-12),
        "halfplane_ok": bool(shift_a - rho > 1e-12),
        "exists_a": bool(rho < r_eff / 2.0 - 1e-12),
    }


def q4_certainty_scouts(
    *,
    spacing: float = DIR_LATTICE_S,
    shift_a: float = DIR_SHIFT_A,
    r_eff: float = R_EFF_MIN,
    arena_r: float = ARENA_R,
) -> list[Point]:
    rho = triangular_covering_radius(spacing)
    return triangular_lattice_points(spacing, arena_r + shift_a + rho)


def optical_grid_step(*, r_clear: float = R_CLEAR) -> float:
    return math.floor((r_clear * math.sqrt(2.0) - 1e-6) * 10) / 10.0


def optical_grid_covers(step: float, r_clear: float = R_CLEAR) -> bool:
    return step / math.sqrt(2.0) < r_clear - 1e-12

