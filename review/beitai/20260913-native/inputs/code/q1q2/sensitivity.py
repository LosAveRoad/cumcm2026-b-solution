"""S4: second-station lateral offset t vs posterior diameter / one-shot clear.

Decision axis: if t is too small, crossing angle collapses and D blows up;
if t is too large, r2 grows and D exceeds 2*R_clear = 40 m, so a single /clear
at the diametral centre is no longer guaranteed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from geom import (
    R_CLEAR,
    R_EFF_MAX,
    R_EFF_MIN,
    R_NEAR,
    bearing_deg,
    crossing_angle_deg,
    hypot,
    posterior_polygon,
    sample_first_wedge,
    sec_covers_via_jung,
    second_station_point,
    set_diameter_points,
)

HERE = Path(__file__).resolve().parent
SEED = int(os.environ.get("JIANMO_SEED", "2026"))

# Fixed axial range for the sweep (Q2 design neighbourhood).
R_FIXED = 1100.0
THETA = 35.0
S1 = (0.0, 0.0)
T_GRID = [200.0, 350.0, 500.0, 650.0, 800.0, 1000.0]


def evaluate_t(t: float, g_samples: list, *, err_deg: float = 1.0, r_fixed: float = R_FIXED) -> dict:
    s2 = second_station_point(S1, THETA, r_fixed, t)
    diams: list[float] = []
    psi: list[float] = []
    clearable = 0
    hear1000 = 0
    hear1500 = 0
    for g in g_samples:
        d2 = hypot(s2, g)
        if d2 <= R_EFF_MAX:
            hear1500 += 1
        if d2 <= R_EFF_MIN:
            hear1000 += 1
        if d2 <= R_NEAR or d2 > R_EFF_MAX:
            continue
        th2 = bearing_deg(g, s2)
        poly = posterior_polygon(S1, THETA, s2, th2, err_deg=err_deg)
        if len(poly) < 3:
            continue
        d, _, _ = set_diameter_points(poly)
        diams.append(d)
        psi.append(crossing_angle_deg(S1, s2, g))
        jung = sec_covers_via_jung(poly)
        one_shot = (jung["covers"] and d <= 2.0 * R_CLEAR) or (
            (not jung["covers"]) and float(jung["sec_radius"]) <= R_CLEAR
        )
        if one_shot:
            clearable += 1
    n = len(g_samples)
    rec = {
        "t_m": t,
        "r_m": r_fixed,
        "err_deg": err_deg,
        "n_g": n,
        "n_posterior": len(diams),
        "median_D_m": float(np.median(diams)) if diams else 1.0e9,
        "p90_D_m": float(np.quantile(diams, 0.9)) if diams else 1.0e9,
        "mean_D_m": float(np.mean(diams)) if diams else 1.0e9,
        "median_psi_deg": float(np.median(psi)) if psi else 0.0,
        "hear1000_frac": hear1000 / n,
        "hear1500_frac": hear1500 / n,
        "clearable_frac": clearable / n,
        "one_shot_median": 1.0 if (diams and float(np.median(diams)) <= 2.0 * R_CLEAR) else 0.0,
    }
    return rec


def main() -> None:
    g_samples = sample_first_wedge(S1, THETA, n_r=14, n_phi=5)
    rows = [evaluate_t(t, g_samples) for t in T_GRID]
    feasible = [r for r in rows if r["hear1500_frac"] >= 0.7 and r["median_psi_deg"] >= 45.0]
    pool = feasible or rows
    best = min(pool, key=lambda r: (r["median_D_m"], -r["clearable_frac"]))
    n_one_shot = sum(int(r["one_shot_median"]) for r in rows)
    # Second axis: wedge half-angle at the Q2 design neighbourhood (t=500, r=1100).
    # This flips the one-shot-clear decision: 0.5° median D drops below 40 m, 1.5° does not.
    err_grid = [0.5, 1.0, 1.5]
    err_rows = []
    for err in err_grid:
        g_err = sample_first_wedge(S1, THETA, err_deg=err, n_r=14, n_phi=5)
        err_rows.append(evaluate_t(500.0, g_err, err_deg=err))
    err_one_shot_flags = [int(r["one_shot_median"]) for r in err_rows]
    metrics = {
        "seed": SEED,
        "axis": "second_station_lateral_offset_m",
        "n_points": float(len(T_GRID)),
        "r_fixed_m": R_FIXED,
        "t_min_m": float(min(T_GRID)),
        "t_max_m": float(max(T_GRID)),
        "best_t_m": float(best["t_m"]),
        "best_median_D_m": float(best["median_D_m"]),
        "best_p90_D_m": float(best["p90_D_m"]),
        "best_clearable_frac": float(best["clearable_frac"]),
        "best_median_psi_deg": float(best["median_psi_deg"]),
        "n_one_shot_grid": float(n_one_shot),
        "t200_median_D_m": float(rows[0]["median_D_m"]),
        "t500_median_D_m": float(rows[2]["median_D_m"]),
        "t800_median_D_m": float(rows[4]["median_D_m"]),
        "t1000_median_D_m": float(rows[-1]["median_D_m"]),
        "t200_one_shot": float(rows[0]["one_shot_median"]),
        "t500_one_shot": float(rows[2]["one_shot_median"]),
        "t1000_one_shot": float(rows[-1]["one_shot_median"]),
        "delta_median_D_t200_minus_best_m": float(rows[0]["median_D_m"] - best["median_D_m"]),
        "decision_prefers_t800_not_t200": 1.0 if best["t_m"] != 200.0 else 0.0,
        "err05_median_D_m": float(err_rows[0]["median_D_m"]),
        "err10_median_D_m": float(err_rows[1]["median_D_m"]),
        "err15_median_D_m": float(err_rows[2]["median_D_m"]),
        "err05_one_shot": float(err_rows[0]["one_shot_median"]),
        "err10_one_shot": float(err_rows[1]["one_shot_median"]),
        "err15_one_shot": float(err_rows[2]["one_shot_median"]),
        "err_one_shot_flips": 1.0 if len(set(err_one_shot_flags)) > 1 else 0.0,
        "clear_diameter_m": 2.0 * R_CLEAR,
    }
    payload = {
        "schema_version": "jianmo.metrics.v0",
        "metrics": metrics,
        "seed": SEED,
        "sweep": rows,
        "err_sweep": err_rows,
        "statement": (
            "Primary axis: lateral offset t of the second DF station at fixed axial range "
            f"{R_FIXED} m. Secondary axis: wedge half-angle 0.5/1.0/1.5 deg at t=500 m. "
            "one_shot_median=1 iff median posterior diameter <= 40 m."
        ),
    }
    Path("results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        (HERE / "results_sensitivity.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        keys = list(rows[0].keys())
        with (HERE / "sensitivity_offset.csv").open("w", encoding="utf-8") as handle:
            handle.write(",".join(keys) + "\n")
            for row in rows:
                handle.write(",".join(str(row[k]) for k in keys) + "\n")
    except OSError:
        pass
    print(json.dumps({"ok": True, "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
