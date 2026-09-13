"""Q3–Q4 scout covering geometry + rehearsal attempt (no fabricated clear-rates)."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import numpy as np

from jianmo.b_sim.geometry import (
    heading_cover_max_gap_deg,
    q3_omni_covering_radius,
    q4_omni_scouts,
    q4_staggered_covering_radius,
    q4_twosided_failure_witness,
    scouts_within,
    two_sided_max_angle_deg,
)

from geom import (
    ARENA_R,
    R_EFF_MIN,
    hypot,
    q3_nine_disk_origin_check,
    q4_bisector_fill_scouts,
    q4_cap_membership,
    q4_heading_cover_cap,
    q4_lattice_certainty,
    q4_lattice_grid_check,
    q4_one_scout_witness,
    q4_operational_scouts,
    q4_polar_one_scout_check,
    q4_sector_disk_subset_ck,
    q4_shell_leftover_witness,
    q4_spoke_cap_heading_witness,
)
from searcher import Searcher, q3_scouts, q4_scouts
from twin import TwinClient, spawn_world

HERE = Path(__file__).resolve().parent
SEED = int(os.environ.get("JIANMO_SEED", "2026"))
DATA_HASH = "sha256:50bf04217eb3e8e7d3ce8b4a84f228b46dcfd93eebae187b443adb7724b2440e"


def _load_robot_id() -> str:
    env = os.environ.get("JIANMO_B_SIM_ROBOT_ID", "").strip()
    if env:
        return env
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("JIANMO_B_SIM_ROBOT_ID="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and not val.startswith("#"):
                    return val
    return ""


def _tcp_open(url: str = "http://127.0.0.1:2026") -> bool:
    try:
        from jianmo.b_sim.client import DEFAULT_BASE_URL
        url = url or DEFAULT_BASE_URL
    except Exception:
        pass
    try:
        req = Request(url + "/enter", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=2) as resp:
            resp.read(16)
        return True
    except URLError:
        return False
    except Exception:
        # Connection reset / HTTP error still means something answered or reset.
        # Treat reset as "port bound but API not in a 演练 window".
        return False


def cover_fraction(scouts: list[tuple[float, float]], rng: np.random.Generator, *, n: int = 4000, two_sided: bool = False) -> float:
    # Uniform in disk via radius sqrt.
    u = rng.random(n)
    phi = rng.uniform(0.0, 2.0 * math.pi, n)
    r = ARENA_R * np.sqrt(u)
    xs = r * np.cos(phi)
    ys = r * np.sin(phi)
    ok = 0
    for x, y in zip(xs, ys):
        near = []
        for sx, sy in scouts:
            d = math.hypot(x - sx, y - sy)
            if d <= R_EFF_MIN:
                near.append((sx, sy))
        if not near:
            continue
        if not two_sided:
            ok += 1
            continue
        # Need two scouts within 1000 m whose directions from the point differ by >= 90°.
        good = False
        for i, (ax, ay) in enumerate(near):
            b1 = math.atan2(ay - y, ax - x)
            for bx, by in near[i + 1 :]:
                b2 = math.atan2(by - y, bx - x)
                dlt = abs((b1 - b2 + math.pi) % (2 * math.pi) - math.pi)
                if dlt >= 0.5 * math.pi - 1e-9:
                    good = True
                    break
            if good:
                break
        if good:
            ok += 1
    return ok / n


def probe_sim() -> dict:
    robot_id = _load_robot_id()
    tcp = False
    http_reset = False
    try:
        req = Request(
            "http://127.0.0.1:2026/enter",
            data=json.dumps(
                {"arena_id": "default", "robot_id": "__probe_not_a_team__", "request_id": "probe-enter-1"}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=2) as resp:
            tcp = True
            body = resp.read().decode("utf-8", errors="replace")
            return {"robot_id": robot_id, "http_open": True, "tcp": True, "body": body[:300]}
    except URLError as exc:
        return {
            "robot_id": robot_id,
            "http_open": False,
            "tcp": False,
            "error": str(getattr(exc, "reason", exc)),
        }
    except Exception as exc:
        msg = str(exc)
        http_reset = "10054" in msg or "reset" in msg.lower() or "强迫关闭" in msg
        return {
            "robot_id": robot_id,
            "http_open": False,
            "tcp": True,
            "http_reset": http_reset,
            "error": msg,
        }


def same_instance_heading_vs_twosided(
    scouts: list[tuple[float, float]],
    rng: np.random.Generator,
    *,
    n: int = 4000,
    extra: list[tuple[float, float]] | None = None,
) -> dict[str, float]:
    """Paired predicates on one disk sample. Two-sided is not the detection theorem."""
    u = rng.random(n)
    phi = rng.uniform(0.0, 2.0 * math.pi, n)
    r = ARENA_R * np.sqrt(u)
    xs = r * np.cos(phi)
    ys = r * np.sin(phi)
    n_omni = n_head = n_two = n_left = n_two_not_head = n_fixed = 0
    n_k0 = n_k0_head = n_k0_left = 0
    n_anyk = n_anyk_head = n_anyk_left = 0
    n_left_in_cap = n_left_out_cap = n_left_in_oct = n_oct = 0
    extra = extra or []
    combined = list(scouts) + list(extra)
    for x, y in zip(xs, ys):
        p = (float(x), float(y))
        gamma = heading_cover_max_gap_deg(p, scouts, R_EFF_MIN)
        pair = two_sided_max_angle_deg(p, scouts, R_EFF_MIN)
        near = scouts_within(p, scouts, R_EFF_MIN)
        mem = q4_cap_membership(p)
        if near:
            n_omni += 1
        head = gamma <= 180.0 + 1e-9
        two = pair >= 90.0 - 1e-9
        if head:
            n_head += 1
        if two:
            n_two += 1
        if two and not head:
            n_two_not_head += 1
        if mem["in_octagon"]:
            n_oct += 1
        if mem["in_k0"]:
            n_k0 += 1
            if head:
                n_k0_head += 1
            else:
                n_k0_left += 1
        if mem["in_some_cap"]:
            n_anyk += 1
            if head:
                n_anyk_head += 1
            else:
                n_anyk_left += 1
        if not head:
            n_left += 1
            if mem["in_some_cap"]:
                n_left_in_cap += 1
            else:
                n_left_out_cap += 1
            if mem["in_octagon"]:
                n_left_in_oct += 1
            if extra and heading_cover_max_gap_deg(p, combined, R_EFF_MIN) <= 180.0 + 1e-9:
                n_fixed += 1
    leftover_equals_cap = 1.0 if (n_left == n_anyk and n_left_out_cap == 0 and n_anyk_head == 0) else 0.0
    leftover_subseteq_cap = 1.0 if (n_left_out_cap == 0 and n_left > 0) else 0.0
    return {
        "n": float(n),
        "omni_frac": n_omni / n,
        "heading_frac": n_head / n,
        "twosided_frac": n_two / n,
        "leftover_n": float(n_left),
        "twosided_not_heading_n": float(n_two_not_head),
        "leftover_fixed_by_extra_n": float(n_fixed),
        "heuristic_is_scheme": 0.0,
        "k0_n": float(n_k0),
        "k0_heading_n": float(n_k0_head),
        "k0_leftover_n": float(n_k0_left),
        "cap_union_n": float(n_anyk),
        "cap_union_heading_n": float(n_anyk_head),
        "cap_union_leftover_n": float(n_anyk_left),
        "leftover_in_cap_n": float(n_left_in_cap),
        "leftover_outside_cap_n": float(n_left_out_cap),
        "leftover_in_octagon_n": float(n_left_in_oct),
        "octagon_n": float(n_oct),
        "leftover_equals_cap": leftover_equals_cap,
        "leftover_subseteq_cap_sample": leftover_subseteq_cap,
        "leftover_subseteq_cap_is_theorem": 0.0,
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    sc3 = q3_scouts()
    sc4 = q4_scouts()
    aligned = q4_omni_scouts()
    operational = q4_operational_scouts()
    cover3 = cover_fraction(sc3, rng, two_sided=False)
    # Abandoned aligned 900/2100 net: keep this key reproducible for the old gate.
    cover4 = cover_fraction(aligned, rng, two_sided=True)
    cover4_one = cover_fraction(sc4, rng, two_sided=False)
    q3_cert = q3_omni_covering_radius()
    q4_cert = q4_staggered_covering_radius()
    lattice_cert = q4_lattice_certainty()
    lattice_grid = q4_lattice_grid_check()
    cap = q4_heading_cover_cap()
    witness = q4_twosided_failure_witness()
    origin_chk = q3_nine_disk_origin_check()
    onescout = q4_one_scout_witness()
    polar1 = q4_polar_one_scout_check()
    spoke = q4_spoke_cap_heading_witness()
    shell = q4_shell_leftover_witness()
    sector = q4_sector_disk_subset_ck()
    rng_cmp = np.random.default_rng(SEED)
    cmp4 = same_instance_heading_vs_twosided(
        operational, rng_cmp, n=4000, extra=q4_bisector_fill_scouts(fill_r=1500.0)
    )
    in_gate = os.environ.get("JIANMO_GATE") == "1"
    if in_gate:
        # Gate re-runs must not talk to a live 演练/正式 window. Covering metrics only.
        probe = {"robot_id": "", "http_open": False, "skipped_in_gate": True}
        twin_rows = []
        blocker = "gate_skip_live_sim"
    else:
        probe = probe_sim()
        blocker = ""
        if not probe.get("robot_id"):
            blocker = "missing_JIANMO_B_SIM_ROBOT_ID"
        if not probe.get("http_open"):
            extra = "api_closed"
            if probe.get("http_reset"):
                extra = "api_closed_connection_reset"
            blocker = f"{blocker}+{extra}" if blocker else extra
        twin_rows = []
        for mixed, n in ((False, 12), (True, 12)):
            world = spawn_world(rng, n=n, mixed=mixed)
            n_true = len(world.jammers)
            logp = HERE / ("twin_omni.jsonl" if not mixed else "twin_mixed.jsonl")
            if logp.exists():
                logp.unlink()
            dog = Searcher(world, mixed=mixed, log_path=logp, max_actions=700)
            summary = dog.run()
            twin_rows.append(
                {
                    "mixed": int(mixed),
                    "n_true": n_true,
                    "n_cleared": summary.get("n_cleared", 0),
                    "n_actions": summary.get("n_actions", 0),
                    "virtual_time_s": summary.get("virtual_time_s", 0),
                    "ok": int(bool(summary.get("ok"))),
                }
            )

    rehearsal = {
        "attempted": False,
        "reason": blocker or "not_attempted",
        "n_cleared": None,
        "virtual_time_s": None,
    }

    metrics = {
        "seed": SEED,
        "q3_scout_n": float(len(sc3)),
        "q3_omni_cover_frac_r1000": float(cover3),
        "q3_omni_covering_radius_m": float(q3_cert["covering_radius_m"]),
        "q3_omni_covers": 1.0 if q3_cert["covers"] else 0.0,
        "q4_scout_n": float(len(aligned)),
        "q4_lattice_n": float(lattice_cert["n_points"]),
        "q4_lattice_spacing_m": float(lattice_cert["spacing_m"]),
        "q4_lattice_shift_a_m": float(lattice_cert["shift_a_m"]),
        "q4_lattice_covering_radius_m": float(lattice_cert["covering_radius_m"]),
        "q4_lattice_a_plus_rho_m": float(lattice_cert["a_plus_rho_m"]),
        "q4_lattice_a_minus_rho_m": float(lattice_cert["a_minus_rho_m"]),
        "q4_lattice_range_ok": 1.0 if lattice_cert["range_ok"] else 0.0,
        "q4_lattice_halfplane_ok": 1.0 if lattice_cert["halfplane_ok"] else 0.0,
        "q4_lattice_exists_a": 1.0 if lattice_cert["exists_a"] else 0.0,
        "q4_lattice_s_max_m": float(lattice_cert["s_max_m"]),
        "q4_lattice_s_design_lt_s_max": 1.0 if lattice_cert["s_design_lt_s_max"] else 0.0,
        "q4_lattice_s900_exists_a": 1.0 if lattice_cert["s900_exists_a"] else 0.0,
        "q4_lattice_s900_covering_radius_m": float(lattice_cert["s900_covering_radius_m"]),
        "q4_lattice_triangle_circumradius_m": float(lattice_cert["triangle_circumradius_m"]),
        "q4_lattice_grid_n": float(lattice_grid["n_points"]),
        "q4_lattice_grid_all_heard": float(lattice_grid["all_heard"]),
        "q4_lattice_grid_is_theorem": 0.0,
        "q4_optical_step_m": float(lattice_cert["optical_step_m"]),
        "q4_optical_cell_circumradius_m": float(lattice_cert["optical_cell_circumradius_m"]),
        "q4_optical_covers": 1.0 if lattice_cert["optical_covers"] else 0.0,
        "q4_omni_cover_frac_r1000": float(cover4_one),
        "q4_twosided_cover_frac_r1000": float(cover4),
        "q4_staggered_covering_radius_m": float(q4_cert["covering_radius_m"]),
        "q4_staggered_omni_covers": 1.0 if q4_cert["covers"] else 0.0,
        "q4_aligned_witness_angle_deg": float(witness["max_pair_angle_deg"]),
        "q4_aligned_witness_two_sided": 1.0 if witness["two_sided"] else 0.0,
        "q4_cap_apothem_m": float(cap["octagon_apothem_m"]),
        "q4_cap_triangle_max_side_m": float(cap["triangle_max_side_m"]),
        "q4_octagon_heading_covered": 1.0 if cap["octagon_heading_covered"] else 0.0,
        "q4_origin_circle_theta_star_deg": float(cap["origin_circle_theta_star_deg"]),
        "q4_origin_circle_sliver_lo_deg": float(cap["origin_circle_sliver_lo_deg"]),
        "q4_origin_circle_sliver_hi_deg": float(cap["origin_circle_sliver_hi_deg"]),
        "q4_origin_circle_sliver_nonempty": 1.0 if cap["origin_circle_sliver_nonempty"] else 0.0,
        "q4_gl_in_cap": 1.0 if cap["gl_in_cap"] else 0.0,
        "q4_gl_gamma_deg": float(cap["gl_gamma_deg"]),
        "q4_gl_heading_covered": 1.0 if cap["gl_heading_covered"] else 0.0,
        "q4_gl_fill_distance_m": float(cap["gl_fill_distance_m"]),
        "q4_gl_iff_agrees": 1.0 if cap["gl_iff_agrees"] else 0.0,
        "q4_gstar_heading_covered": 1.0 if cap["gstar_heading_covered"] else 0.0,
        "q4_op_heading_cover_frac": float(cmp4["heading_frac"]),
        "q4_op_twosided_cover_frac": float(cmp4["twosided_frac"]),
        "q4_op_leftover_n": float(cmp4["leftover_n"]),
        "q4_op_twosided_not_heading_n": float(cmp4["twosided_not_heading_n"]),
        "q4_op_leftover_fixed_by_bis1500_n": float(cmp4["leftover_fixed_by_extra_n"]),
        "q4_bisector_fill_heuristic_is_scheme": 0.0,
        "q3_origin_min_to_ring_m": float(origin_chk["origin_min_to_ring_m"]),
        "q3_origin_min_to_nine_m": float(origin_chk["origin_min_to_nine_m"]),
        "q3_eight_ring_min_at_origin_le_rho": 1.0 if origin_chk["eight_ring_min_at_origin_le_rho"] else 0.0,
        "q3_nine_disk_min_at_origin_le_rho": 1.0 if origin_chk["nine_disk_min_at_origin_le_rho"] else 0.0,
        "q4_g1_inner9_n_scouts": float(onescout["n_inner9"]),
        "q4_g1_inner9_gamma_deg": float(onescout["gamma_inner9_deg"]),
        "q4_inner9_one_scout_empty": 1.0 if onescout["inner9_one_scout_empty"] else 0.0,
        "q4_rho_lt_reff_implies_one_scout_empty": 0.0,
        "q4_g1_stagger_n_scouts": float(onescout["n_stagger17"]),
        "q4_spoke_exit_outer_dist_m": float(onescout["spoke_exit_outer_dist_m"]),
        "q4_spoke_arena_outer_dist_m": float(onescout["spoke_arena_outer_dist_m"]),
        "q4_polar_n": float(polar1["n_points"]),
        "q4_polar_inner9_one_scout_n": float(polar1["inner9_one_scout_n"]),
        "q4_polar_stagger_one_scout_n": float(polar1["stagger17_one_scout_n"]),
        "q4_polar_op_one_scout_n": float(polar1["operational_one_scout_n"]),
        "q4_polar_is_theorem": 0.0,
        "q4_k0_n": float(cmp4["k0_n"]),
        "q4_k0_heading_n": float(cmp4["k0_heading_n"]),
        "q4_k0_leftover_n": float(cmp4["k0_leftover_n"]),
        "q4_cap_union_n": float(cmp4["cap_union_n"]),
        "q4_cap_union_heading_n": float(cmp4["cap_union_heading_n"]),
        "q4_cap_union_leftover_n": float(cmp4["cap_union_leftover_n"]),
        "q4_leftover_in_cap_n": float(cmp4["leftover_in_cap_n"]),
        "q4_leftover_outside_cap_n": float(cmp4["leftover_outside_cap_n"]),
        "q4_leftover_in_octagon_n": float(cmp4["leftover_in_octagon_n"]),
        "q4_leftover_equals_cap": float(cmp4["leftover_equals_cap"]),
        "q4_leftover_subseteq_cap": 0.0,
        "q4_leftover_subseteq_cap_sample": float(cmp4["leftover_subseteq_cap_sample"]),
        "q4_leftover_subseteq_cap_is_theorem": 0.0,
        "q4_gs_in_cap": 1.0 if spoke["in_cap"] else 0.0,
        "q4_gs_heading_covered": 1.0 if spoke["heading_covered"] else 0.0,
        "q4_gs_gamma_deg": float(spoke["gamma_deg"]),
        "q4_shell_r_m": float(shell["r_m"]),
        "q4_shell_gamma_deg": float(shell["gamma_deg"]),
        "q4_shell_in_cap": 1.0 if shell["in_cap"] else 0.0,
        "q4_shell_heading_covered": 1.0 if shell["heading_covered"] else 0.0,
        "q4_shell_n_scouts": float(shell["n_scouts"]),
        "q4_leftover_neq_cap_named": 1.0 if cap["leftover_neq_cap_named"] else 0.0,
        "q4_leftover_outside_cap_named": 1.0 if cap["leftover_outside_cap_named"] else 0.0,
        "q4_sector_disk_max_inner_dist_m": float(sector["max_inner_dist_m"]),
        "q4_sector_disk_subset_ck": 1.0 if sector["subset_ck"] else 0.0,
        "r_eff_min_m": float(R_EFF_MIN),
        "arena_r_m": float(ARENA_R),
    }
    payload = {
        "schema_version": "jianmo.metrics.v0",
        "metrics": metrics,
        "seed": SEED,
        "probe": {k: v for k, v in probe.items() if k != "body"},
        "blocker": blocker,
        "rehearsal": rehearsal,
        "twin_smoke_not_contest": twin_rows,
        "certificates": {
            "q3_omni_covering_radius": q3_cert,
            "q4_staggered_covering_radius": q4_cert,
            "q4_lattice_certainty": lattice_cert,
            "q4_lattice_grid_check": lattice_grid,
            "q4_heading_cover_cap": cap,
            "q4_aligned_twosided_witness": witness,
            "q3_nine_disk_origin_check": origin_chk,
            "q4_one_scout_witness": onescout,
            "q4_polar_one_scout_check": polar1,
            "q4_spoke_cap_heading_witness": spoke,
            "q4_shell_leftover_witness": shell,
            "q4_sector_disk_subset_ck": sector,
        },
        "q4_comparison_same_instances": cmp4,
        "note": (
            "twin_smoke_not_contest is a statement-faithful digital twin used to "
            "debug the searcher. It is not a 演练统计 and must not be copied into "
            "the paper as 清除比例 / 平均定位清除时间. "
            "Current Q4 discovery is the triangular lattice (q4_lattice_*). "
            "q4_scout_n=17 and q4_twosided_cover_frac_r1000 are the abandoned "
            "aligned-net keys, not the detection theorem. q4_op_* leftover "
            "keys describe the abandoned staggered net; they are not the scheme. "
            "q4_lattice_grid_* is a polar×heading check of the lattice lemma, "
            "not the covering model."
        ),
    }
    Path("results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        (HERE / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (HERE / "blocker.json").write_text(
            json.dumps({"blocker": blocker, "probe": probe}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (HERE / "q4_comparison.csv").write_text(
            "predicate,value\n"
            f"heading_cover_frac,{cmp4['heading_frac']:.12g}\n"
            f"twosided_frac,{cmp4['twosided_frac']:.12g}\n"
            f"leftover_n,{cmp4['leftover_n']:.12g}\n"
            f"twosided_not_heading_n,{cmp4['twosided_not_heading_n']:.12g}\n"
            f"leftover_fixed_by_bis1500_n,{cmp4['leftover_fixed_by_extra_n']:.12g}\n"
            f"k0_n,{cmp4['k0_n']:.12g}\n"
            f"k0_heading_n,{cmp4['k0_heading_n']:.12g}\n"
            f"k0_leftover_n,{cmp4['k0_leftover_n']:.12g}\n"
            f"cap_union_n,{cmp4['cap_union_n']:.12g}\n"
            f"leftover_equals_cap,{cmp4['leftover_equals_cap']:.12g}\n"
            f"leftover_subseteq_cap_sample,{cmp4['leftover_subseteq_cap_sample']:.12g}\n"
            "leftover_subseteq_cap_is_theorem,0\n"
            "heuristic_is_scheme,0\n",
            encoding="utf-8",
        )
        (HERE / "q4_lattice.csv").write_text(
            "key,value\n"
            f"n_points,{float(lattice_cert['n_points']):.12g}\n"
            f"spacing_m,{float(lattice_cert['spacing_m']):.12g}\n"
            f"shift_a_m,{float(lattice_cert['shift_a_m']):.12g}\n"
            f"covering_radius_m,{float(lattice_cert['covering_radius_m']):.12g}\n"
            f"a_plus_rho_m,{float(lattice_cert['a_plus_rho_m']):.12g}\n"
            f"a_minus_rho_m,{float(lattice_cert['a_minus_rho_m']):.12g}\n"
            f"s_max_m,{float(lattice_cert['s_max_m']):.12g}\n"
            f"s900_covering_radius_m,{float(lattice_cert['s900_covering_radius_m']):.12g}\n"
            f"s900_exists_a,{1 if lattice_cert['s900_exists_a'] else 0}\n"
            f"range_ok,{1 if lattice_cert['range_ok'] else 0}\n"
            f"halfplane_ok,{1 if lattice_cert['halfplane_ok'] else 0}\n"
            f"optical_step_m,{float(lattice_cert['optical_step_m']):.12g}\n"
            f"optical_cell_circumradius_m,{float(lattice_cert['optical_cell_circumradius_m']):.12g}\n"
            f"optical_covers,{1 if lattice_cert['optical_covers'] else 0}\n"
            f"grid_n,{float(lattice_grid['n_points']):.12g}\n"
            f"grid_all_heard,{float(lattice_grid['all_heard']):.12g}\n"
            "grid_is_theorem,0\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    print(json.dumps({"ok": True, "metrics": metrics, "blocker": blocker, "twin": twin_rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
