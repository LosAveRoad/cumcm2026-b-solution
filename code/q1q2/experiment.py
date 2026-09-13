"""Q1–Q2 geometry experiment (synthetic stations; not contest gold).

Prints results.json with schema jianmo.metrics.v0 in the process cwd.
Also dumps tables next to this script when run from the experiment folder.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np

from geom import (
    ARENA_R,
    ERR_DEG,
    R_CLEAR,
    R_EFF_MAX,
    R_EFF_MIN,
    R_NEAR,
    axis_crossing_psi_deg,
    axis_psi_band_offset,
    axis_psi_ge45_offset,
    policy_offaxis_far_psi_deg,
    bearing_deg,
    bearing_vec,
    centroid,
    crossing_angle_deg,
    diametral_circle_covers_any,
    equilateral_counterexample,
    helper_quad_points,
    hypot,
    in_wedge,
    intersect_two_lines,
    intersect_wedges,
    left_normal,
    measured_bearing,
    polygon_area,
    polygon_unbounded,
    posterior_polygon,
    sample_first_wedge,
    sec_covers_via_jung,
    second_station_point,
    set_diameter_points,
    smallest_enclosing_circle,
    two_station_quad_filtered,
)

HERE = Path(__file__).resolve().parent
SEED = int(os.environ.get("JIANMO_SEED", "2026"))


def _dump(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(keys) + "\n")
        for row in rows:
            handle.write(",".join(_fmt(row[k]) for k in keys) + "\n")


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def example_orthogonal_cross() -> dict:
    """S1=(0,0) bearing 45°, S2=(1000,0) bearing 135°. Cross at (500,500).

    Documented synthetic example used for gated headlines. Not contest gold.
    """
    s1 = (0.0, 0.0)
    s2 = (1000.0, 0.0)
    b1 = 45.0
    b2 = 135.0
    true_g = (500.0, 500.0)
    poly = intersect_wedges([s1, s2], [b1, b2], err_deg=ERR_DEG, clip_arena=True, range_balls=[R_EFF_MAX, R_EFF_MAX])
    poly_raw = intersect_wedges([s1, s2], [b1, b2], err_deg=ERR_DEG, clip_arena=False)
    filt = two_station_quad_filtered(s1, b1, s2, b2, err_deg=ERR_DEG)
    helper_pts = helper_quad_points(s1, b1, s2, b2, ERR_DEG)
    helper_in = all(in_wedge(p, s1, b1) and in_wedge(p, s2, b2) for p in helper_pts)
    d_info = diametral_circle_covers_any(poly)
    jung = sec_covers_via_jung(poly)
    from jianmo.b_sim import diametral_circle_covers, set_diameter

    helper_diam = set_diameter(helper_pts)
    helper_cover = diametral_circle_covers(helper_pts)
    max_vertex_err = 0.0
    for p in helper_pts:
        max_vertex_err = max(max_vertex_err, min(hypot(p, q) for q in filt) if filt else math.inf)
    return {
        "s1": s1,
        "s2": s2,
        "b1": b1,
        "b2": b2,
        "true_g": true_g,
        "poly": poly,
        "poly_raw": poly_raw,
        "filtered": filt,
        "helper_pts": helper_pts,
        "helper_all_in_wedges": helper_in,
        "diameter": float(d_info["diameter"]),
        "diametral_covers": bool(d_info["covers"]),
        "sec_radius": float(jung["sec_radius"]),
        "sec_covers": bool(jung["covers"]),
        "jung_ratio": float(jung["jung_ratio"]),
        "area": abs(polygon_area(poly)),
        "n_vertices": len(poly),
        "helper_diameter": float(helper_diam[0]),
        "helper_covers": bool(helper_cover["covers"]),
        "helper_vertex_max_err_m": float(max_vertex_err),
        "centroid": centroid(poly),
        "unbounded_raw": polygon_unbounded(poly_raw),
        "true_g_in_poly": in_wedge(true_g, s1, b1) and in_wedge(true_g, s2, b2),
        "crossing_deg": crossing_angle_deg(s1, s2, true_g),
    }


def helper_behind_station_case() -> dict:
    """Stations look nearly away from each other: line hits can lie behind a station.

    Bearings 170° from (0,0) and 10° from (1000,0) are not parallel, so the
    installed helper returns four line-line intersections; some have t<0 or s<0
    and do not lie in both forward wedges.
    """
    s1 = (0.0, 0.0)
    s2 = (1000.0, 0.0)
    b1 = 170.0
    b2 = 10.0
    helper_pts = helper_quad_points(s1, b1, s2, b2, ERR_DEG)
    n_in = sum(1 for p in helper_pts if in_wedge(p, s1, b1) and in_wedge(p, s2, b2))
    ts = []
    for e1 in (ERR_DEG, -ERR_DEG):
        for e2 in (ERR_DEG, -ERR_DEG):
            hit = intersect_two_lines(s1, b1 + e1, s2, b2 + e2)
            if hit is None:
                ts.append(None)
            else:
                ts.append({"t": hit[1], "s": hit[2], "pt": hit[0]})
    filt = two_station_quad_filtered(s1, b1, s2, b2, err_deg=ERR_DEG)
    poly = intersect_wedges([s1, s2], [b1, b2], clip_arena=False)
    return {
        "helper_n": len(helper_pts),
        "helper_n_in_both_wedges": n_in,
        "filtered_n": len(filt),
        "poly_n": len(poly),
        "poly_unbounded": polygon_unbounded(poly),
        "any_negative_param": any(
            row is not None and (row["t"] < 0 or row["s"] < 0) for row in ts
        ),
    }


def monte_carlo_two_station(rng: np.random.Generator, n: int = 400) -> dict:
    covers = 0
    bounded = 0
    raw_covers = 0
    raw_bounded = 0
    helper_agree = 0
    helper_in_ok = 0
    diameters: list[float] = []
    jung_ratios: list[float] = []
    rows: list[dict] = []
    for k in range(n):
        s1 = (float(rng.uniform(-400, 400)), float(rng.uniform(-400, 400)))
        s2 = (float(rng.uniform(-400, 400)), float(rng.uniform(-400, 400)))
        if hypot(s1, s2) < 80.0:
            s2 = (s1[0] + 400.0, s1[1] + 50.0)
        g = (float(rng.uniform(-900, 900)), float(rng.uniform(-900, 900)))
        if hypot(g) > 1600:
            g = (g[0] * 0.5, g[1] * 0.5)
        e1 = float(rng.uniform(-ERR_DEG, ERR_DEG))
        e2 = float(rng.uniform(-ERR_DEG, ERR_DEG))
        b1 = measured_bearing(bearing_deg(g, s1), e1)
        b2 = measured_bearing(bearing_deg(g, s2), e2)
        poly = intersect_wedges([s1, s2], [b1, b2], clip_arena=True, range_balls=[R_EFF_MAX, R_EFF_MAX])
        poly_raw = intersect_wedges([s1, s2], [b1, b2], clip_arena=False)
        if len(poly) < 3 or polygon_unbounded(poly, start_half=1.0e6):
            continue
        bounded += 1
        dinfo = diametral_circle_covers_any(poly)
        jung = sec_covers_via_jung(poly)
        if dinfo["covers"]:
            covers += 1
        if len(poly_raw) >= 3 and not polygon_unbounded(poly_raw):
            raw_bounded += 1
            if diametral_circle_covers_any(poly_raw)["covers"]:
                raw_covers += 1
        diameters.append(float(dinfo["diameter"]))
        jung_ratios.append(float(jung["jung_ratio"]))
        try:
            hpts = helper_quad_points(s1, b1, s2, b2, ERR_DEG)
            hin = all(in_wedge(p, s1, b1) and in_wedge(p, s2, b2) for p in hpts)
            if hin:
                helper_in_ok += 1
            hcov = diametral_circle_covers_any(hpts)
            if bool(hcov["covers"]) == bool(dinfo["covers"]) and hin:
                helper_agree += 1
        except Exception:
            hpts = []
            hin = False
        rows.append(
            {
                "k": k,
                "diameter": float(dinfo["diameter"]),
                "covers": int(bool(dinfo["covers"])),
                "sec_radius": float(jung["sec_radius"]),
                "n_vertices": len(poly),
                "area": abs(polygon_area(poly)),
                "helper_in_wedges": int(bool(hin)),
            }
        )
    return {
        "n_requested": n,
        "n_bounded": bounded,
        "n_covers": covers,
        "cover_rate": (covers / bounded) if bounded else 0.0,
        "n_raw_bounded": raw_bounded,
        "raw_cover_rate": (raw_covers / raw_bounded) if raw_bounded else 0.0,
        "helper_in_wedge_rate": (helper_in_ok / bounded) if bounded else 0.0,
        "median_diameter": float(np.median(diameters)) if diameters else 0.0,
        "p90_diameter": float(np.quantile(diameters, 0.9)) if diameters else 0.0,
        "max_jung_ratio": float(max(jung_ratios)) if jung_ratios else 0.0,
        "rows": rows,
    }


def q2_grid(rng: np.random.Generator | None = None) -> dict:
    s1 = (0.0, 0.0)
    theta = 35.0
    g_samples = sample_first_wedge(s1, theta, n_r=14, n_phi=5)
    r_grid = np.linspace(400.0, 1400.0, 11)
    t_grid = np.linspace(150.0, 1000.0, 12)
    rows: list[dict] = []
    best = None
    for r in r_grid:
        for t in t_grid:
            for sign in (1.0, -1.0):
                s2 = second_station_point(s1, theta, float(r), sign * float(t))
                diams: list[float] = []
                hear1000 = 0
                hear1500 = 0
                clearable = 0
                psi_list: list[float] = []
                for g in g_samples:
                    d2 = hypot(s2, g)
                    if d2 <= R_EFF_MAX:
                        hear1500 += 1
                    if d2 <= R_EFF_MIN:
                        hear1000 += 1
                    if d2 <= R_NEAR or d2 > R_EFF_MAX:
                        continue
                    th2 = bearing_deg(g, s2)
                    poly = posterior_polygon(s1, theta, s2, th2, err_deg=ERR_DEG)
                    if len(poly) < 3:
                        continue
                    d, _, _ = set_diameter_points(poly)
                    diams.append(d)
                    psi_list.append(crossing_angle_deg(s1, s2, g))
                    jung = sec_covers_via_jung(poly)
                    if jung["covers"] and d <= 2.0 * R_CLEAR:
                        clearable += 1
                    elif (not jung["covers"]) and float(jung["sec_radius"]) <= R_CLEAR:
                        clearable += 1
                if not diams:
                    continue
                rec = {
                    "r": float(r),
                    "t": float(t),
                    "sign": int(sign),
                    "s2x": s2[0],
                    "s2y": s2[1],
                    "n_heard": len(diams),
                    "hear1000_frac": hear1000 / len(g_samples),
                    "hear1500_frac": hear1500 / len(g_samples),
                    "median_D": float(np.median(diams)),
                    "p90_D": float(np.quantile(diams, 0.9)),
                    "mean_D": float(np.mean(diams)),
                    "clearable_frac": clearable / len(g_samples),
                    "median_psi": float(np.median(psi_list)) if psi_list else 0.0,
                    "walk_from_s1": hypot(s2, s1),
                }
                rows.append(rec)
                score = rec["median_D"] + 15.0 * (1.0 - rec["hear1000_frac"]) + 0.02 * rec["walk_from_s1"]
                if rec["hear1500_frac"] >= 0.55 and rec["median_psi"] >= 40.0:
                    if best is None or score < best[0]:
                        best = (score, rec)
    cand = [
        row
        for row in rows
        if row["hear1500_frac"] >= 0.7
        and row["median_psi"] >= 45.0
        and row["p90_D"] <= 90.0
        and 350.0 <= row["t"] <= 850.0
        and 800.0 <= row["r"] <= 1300.0
    ]
    # Unique (r,t) cells (signs collapse)
    cell_area = (r_grid[1] - r_grid[0]) * (t_grid[1] - t_grid[0])
    unique_rt = {(round(row["r"], 6), round(row["t"], 6)) for row in cand}
    area = 2.0 * cell_area * len(unique_rt)  # two sides of the LOB
    # Design point: among candidate cells, minimise median posterior diameter.
    if cand:
        design = min(cand, key=lambda r: (r["median_D"], r["p90_D"], -r["clearable_frac"]))
    elif best is not None:
        design = best[1]
    else:
        design = rows[0]
    comparison = q2_same_instance_comparison(s1, theta, g_samples, design)
    return {
        "s1": s1,
        "theta": theta,
        "n_g": len(g_samples),
        "design": design,
        "candidate_n_cells": len(unique_rt),
        "candidate_area_m2": float(area),
        "candidate_r_min": min((r for r, _t in unique_rt), default=0.0),
        "candidate_r_max": max((r for r, _t in unique_rt), default=0.0),
        "candidate_t_min": min((t for _r, t in unique_rt), default=0.0),
        "candidate_t_max": max((t for _r, t in unique_rt), default=0.0),
        "comparison": comparison,
        "rows": rows,
    }


def _q2_eval_station(
    s1: tuple[float, float],
    theta: float,
    s2: tuple[float, float],
    g_samples: list,
    *,
    r_lo: float = 5.0,
    r_hi: float = 1500.0,
    r_nominal: float | None = None,
    t_nominal: float | None = None,
) -> dict:
    diams: list[float] = []
    psi_list: list[float] = []
    hear1000 = 0
    for g in g_samples:
        d2 = hypot(s2, g)
        if d2 <= R_EFF_MIN:
            hear1000 += 1
        if d2 <= R_NEAR or d2 > R_EFF_MAX:
            continue
        th2 = bearing_deg(g, s2)
        poly = posterior_polygon(s1, theta, s2, th2, err_deg=ERR_DEG)
        if len(poly) < 3:
            continue
        d, _, _ = set_diameter_points(poly)
        diams.append(d)
        psi_list.append(crossing_angle_deg(s1, s2, g))
    u = bearing_vec(theta)
    v = left_normal(u)
    dx, dy = s2[0] - s1[0], s2[1] - s1[1]
    r_proj = dx * u[0] + dy * u[1]
    t_proj = dx * v[0] + dy * v[1]
    r = float(r_nominal) if r_nominal is not None else float(r_proj)
    t = float(t_nominal) if t_nominal is not None else float(t_proj)
    t_ge45 = axis_psi_ge45_offset(r, r_lo, r_hi)
    t_band = axis_psi_band_offset(r, r_lo, r_hi)
    return {
        "r_m": float(r),
        "t_m": float(t),
        "axis_cover_t_m": float(t_band),
        "psi45_cover_t_m": float(t_ge45),
        "covers_all_axis_psi45": 1.0 if abs(t) + 1e-9 >= t_ge45 else 0.0,
        "covers_all_axis_psi_band": 1.0 if abs(t) + 1e-9 >= t_band else 0.0,
        "near_psi_deg": float(axis_crossing_psi_deg(r, t, r_lo)),
        "far_psi_deg": float(axis_crossing_psi_deg(r, t, r_hi)),
        "n_posterior": float(len(diams)),
        "median_D_m": float(np.median(diams)) if diams else 0.0,
        "p90_D_m": float(np.quantile(diams, 0.9)) if diams else 0.0,
        "median_psi_deg": float(np.median(psi_list)) if psi_list else 0.0,
        "hear1000_frac": hear1000 / len(g_samples) if g_samples else 0.0,
    }


def q2_same_instance_comparison(
    s1: tuple[float, float],
    theta: float,
    g_samples: list,
    design: dict,
    *,
    r_lo: float = 5.0,
    r_hi: float = 1500.0,
) -> dict:
    """Paired comparison on the same wedge samples. Heuristic is not the scheme.

    The quantile grid point is a 70-sample band, not an axis covering set.
    ψ≥45° on every axis G with r_G∈[r_lo,r_hi] is |t|≥r_hi−r (700 m at r=800 m).
    ψ∈[45°,135°] on that interval is |t|≥max(|r−r_lo|,|r_hi−r|) (795 m).
    The centroid perpendicular is a local heuristic on the same n_g points.
    Delivered offset is the ψ≥45° covering |t|=700 m, matching the chase.
    """
    r_des = float(design["r"])
    t_des = float(design["t"])
    t_ge45 = axis_psi_ge45_offset(r_des, r_lo, r_hi)
    t_band = axis_psi_band_offset(r_des, r_lo, r_hi)
    cx = sum(p[0] for p in g_samples) / len(g_samples)
    cy = sum(p[1] for p in g_samples) / len(g_samples)
    r_cent = hypot((cx, cy), s1)
    quantile_s2 = second_station_point(s1, theta, r_des, t_des)
    psi45_s2 = second_station_point(s1, theta, r_des, t_ge45)
    band_s2 = second_station_point(s1, theta, r_des, t_band)
    heur_s2 = second_station_point(s1, theta, r_cent, 700.0)
    quantile_row = _q2_eval_station(
        s1, theta, quantile_s2, g_samples, r_lo=r_lo, r_hi=r_hi, r_nominal=r_des, t_nominal=t_des
    )
    psi45_row = _q2_eval_station(
        s1, theta, psi45_s2, g_samples, r_lo=r_lo, r_hi=r_hi, r_nominal=r_des, t_nominal=t_ge45
    )
    band_row = _q2_eval_station(
        s1, theta, band_s2, g_samples, r_lo=r_lo, r_hi=r_hi, r_nominal=r_des, t_nominal=t_band
    )
    heur_row = _q2_eval_station(s1, theta, heur_s2, g_samples, r_lo=r_lo, r_hi=r_hi)
    return {
        "n_g": float(len(g_samples)),
        "r_lo_m": float(r_lo),
        "r_hi_m": float(r_hi),
        "design": quantile_row,
        "quantile": quantile_row,
        "psi45_cover": psi45_row,
        "axis_cover": band_row,
        "psi_band_cover": band_row,
        "centroid_perp_heuristic": heur_row,
        "design_covers_all_axis_psi45": quantile_row["covers_all_axis_psi45"],
        "axis_cover_t_m": float(t_band),
        "psi45_cover_t_m": float(t_ge45),
        "psi_band_cover_t_m": float(t_band),
        "policy_offset_m": float(t_ge45),
        "policy_covers_all_axis_psi45": psi45_row["covers_all_axis_psi45"],
        "policy_covers_all_axis_psi_band": psi45_row["covers_all_axis_psi_band"],
        "policy_far_psi_deg": psi45_row["far_psi_deg"],
        "policy_near_psi_deg": psi45_row["near_psi_deg"],
        "quantile_far_psi_deg": quantile_row["far_psi_deg"],
        "heuristic_median_D_m": heur_row["median_D_m"],
        "heuristic_p90_D_m": heur_row["p90_D_m"],
        "axis_cover_median_D_m": band_row["median_D_m"],
        "axis_cover_hear1000_frac": band_row["hear1000_frac"],
        "psi45_cover_median_D_m": psi45_row["median_D_m"],
        "psi45_cover_hear1000_frac": psi45_row["hear1000_frac"],
        "heuristic_is_scheme": 0.0,
        "quantile_is_scheme": 0.0,
        "policy_offaxis_far_psi_deg": float(
            policy_offaxis_far_psi_deg(r=r_des, t=t_ge45, r_g=r_hi, err_deg=ERR_DEG)
        ),
        "policy_covers_all_wedge_psi45": 0.0,
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    ex = example_orthogonal_cross()
    behind = helper_behind_station_case()
    eq = equilateral_counterexample(side=80.0, center=(0.0, 400.0))
    eq_poly = eq["polygon"]
    if len(eq_poly) >= 3:
        eq_d = diametral_circle_covers_any(eq_poly)
        eq_j = sec_covers_via_jung(eq_poly)
    else:
        # Fall back to the constructed triangle vertices.
        eq_d = diametral_circle_covers_any(eq["triangle"])
        eq_j = sec_covers_via_jung(eq["triangle"])
    mc = monte_carlo_two_station(rng, n=400)
    q2 = q2_grid(rng)

    # Analytic Jung numbers for the equilateral triangle of side 80.
    side = 80.0
    jung_r = side / math.sqrt(3.0)
    half_d = 0.5 * side

    design = q2["design"]
    cmp2 = q2["comparison"]
    metrics = {
        "seed": SEED,
        "q1_example_diameter_m": float(ex["diameter"]),
        "q1_example_diametral_covers": 1.0 if ex["diametral_covers"] else 0.0,
        "q1_example_sec_radius_m": float(ex["sec_radius"]),
        "q1_example_sec_covers": 1.0 if ex["sec_covers"] else 0.0,
        "q1_example_n_vertices": float(ex["n_vertices"]),
        "q1_example_area_m2": float(ex["area"]),
        "q1_example_jung_ratio": float(ex["jung_ratio"]),
        "q1_helper_vertex_max_err_m": float(ex["helper_vertex_max_err_m"]),
        "q1_helper_example_in_wedges": 1.0 if ex["helper_all_in_wedges"] else 0.0,
        "q1_helper_behind_any_negative_param": 1.0 if behind["any_negative_param"] else 0.0,
        "q1_helper_behind_in_wedge_count": float(behind["helper_n_in_both_wedges"]),
        "q1_n2_bounded_samples": float(mc["n_bounded"]),
        "q1_n2_cover_rate": float(mc["cover_rate"]),
        "q1_n2_raw_cover_rate": float(mc["raw_cover_rate"]),
        "q1_n2_raw_bounded_samples": float(mc["n_raw_bounded"]),
        "q1_n2_median_diameter_m": float(mc["median_diameter"]),
        "q1_n2_max_jung_ratio": float(mc["max_jung_ratio"]),
        "q1_n3_triangle_side_m": side,
        "q1_n3_counterexample_diameter_m": float(eq_d["diameter"]),
        "q1_n3_counterexample_sec_radius_m": float(eq_j["sec_radius"]),
        "q1_n3_counterexample_covers": 1.0 if eq_d["covers"] else 0.0,
        "q1_jung_triangle_diameter_m": side,
        "q1_jung_triangle_sec_radius_m": float(jung_r),
        "q1_jung_triangle_covers": 1.0 if diametral_circle_covers_any(eq["triangle"])["covers"] else 0.0,
        "q1_n3_jung_radius_analytic_m": float(jung_r),
        "q1_n3_half_diameter_m": float(half_d),
        "q2_design_range_m": float(design["r"]),
        "q2_design_offset_m": float(design["t"]),
        "q2_design_median_diameter_m": float(design["median_D"]),
        "q2_design_p90_diameter_m": float(design["p90_D"]),
        "q2_design_clearable_frac": float(design["clearable_frac"]),
        "q2_design_hear1000_frac": float(design["hear1000_frac"]),
        "q2_design_median_psi_deg": float(design["median_psi"]),
        "q2_candidate_area_m2": float(q2["candidate_area_m2"]),
        "q2_candidate_r_min_m": float(q2["candidate_r_min"]),
        "q2_candidate_r_max_m": float(q2["candidate_r_max"]),
        "q2_candidate_t_min_m": float(q2["candidate_t_min"]),
        "q2_candidate_t_max_m": float(q2["candidate_t_max"]),
        "q2_design_n_g": float(cmp2["n_g"]),
        "q2_axis_cover_t_m": float(cmp2["axis_cover_t_m"]),
        "q2_design_covers_all_axis_psi45": float(cmp2["design_covers_all_axis_psi45"]),
        "q2_axis_cover_median_D_m": float(cmp2["axis_cover_median_D_m"]),
        "q2_axis_cover_hear1000_frac": float(cmp2["axis_cover_hear1000_frac"]),
        "q2_heuristic_median_D_m": float(cmp2["heuristic_median_D_m"]),
        "q2_heuristic_p90_D_m": float(cmp2["heuristic_p90_D_m"]),
        "q2_heuristic_is_scheme": 0.0,
        "q2_psi45_cover_t_m": float(cmp2["psi45_cover_t_m"]),
        "q2_psi_band_cover_t_m": float(cmp2["psi_band_cover_t_m"]),
        "q2_policy_offset_m": float(cmp2["policy_offset_m"]),
        "q2_policy_covers_all_axis_psi45": float(cmp2["policy_covers_all_axis_psi45"]),
        "q2_policy_covers_all_axis_psi_band": float(cmp2["policy_covers_all_axis_psi_band"]),
        "q2_policy_far_psi_deg": float(cmp2["policy_far_psi_deg"]),
        "q2_policy_near_psi_deg": float(cmp2["policy_near_psi_deg"]),
        "q2_quantile_far_psi_deg": float(cmp2["quantile_far_psi_deg"]),
        "q2_psi45_cover_median_D_m": float(cmp2["psi45_cover_median_D_m"]),
        "q2_psi45_cover_hear1000_frac": float(cmp2["psi45_cover_hear1000_frac"]),
        "q2_quantile_is_scheme": 0.0,
        "q2_policy_offaxis_far_psi_deg": float(cmp2["policy_offaxis_far_psi_deg"]),
        "q2_policy_covers_all_wedge_psi45": 0.0,
        "clear_radius_m": R_CLEAR,
        "near_radius_m": R_NEAR,
        "arena_radius_m": ARENA_R,
        "err_deg": ERR_DEG,
    }
    payload = {
        "schema_version": "jianmo.metrics.v0",
        "metrics": metrics,
        "seed": SEED,
        "example": {
            "name": "orthogonal-cross-500",
            "stations": [list(ex["s1"]), list(ex["s2"])],
            "bearings_deg": [ex["b1"], ex["b2"]],
            "true_g": list(ex["true_g"]),
            "note": "Synthetic orthogonal cross at (500,500); not contest gold.",
        },
        "n3_counterexample": {
            "side_m": side,
            "stations": [list(p) for p in eq["stations"]],
            "bearings_deg": list(eq["bearings_deg"]),
            "n_polygon_vertices": len(eq_poly),
        },
        "q2_design": design,
        "q2_candidate_region": {
            "r_min": q2["candidate_r_min"],
            "r_max": q2["candidate_r_max"],
            "t_min": q2["candidate_t_min"],
            "t_max": q2["candidate_t_max"],
            "area_m2": q2["candidate_area_m2"],
            "parametrization": "S2 = S1 + r u_theta + t v_theta, both signs of t",
        },
        "q2_comparison_same_instances": cmp2,
    }
    Path("results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Persist dumps next to the script when not in the gate tempdir copy... always try HERE too.
    try:
        (HERE / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _dump(HERE / "q1_mc_sample.csv", mc["rows"])
        _dump(HERE / "q2_grid.csv", q2["rows"])
        _dump(
            HERE / "q1_example_vertices.csv",
            [{"i": i, "x": p[0], "y": p[1]} for i, p in enumerate(ex["poly"])],
        )
    except OSError:
        pass
    print(json.dumps({"ok": True, "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
