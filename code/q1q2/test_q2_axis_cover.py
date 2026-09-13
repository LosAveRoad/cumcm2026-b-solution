"""Q2 axis covering lemmas (no simulator)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from geom import (  # noqa: E402
    axis_crossing_psi_deg,
    axis_psi_band_offset,
    axis_psi_cover_offset,
    axis_psi_ge45_offset,
    crossing_angle_deg,
    policy_offaxis_far_psi_deg,
    second_station_point,
    wedge_far_corner_point,
)


def test_axis_iff_band_and_ge45() -> None:
    s1 = (0.0, 0.0)
    theta = 0.0
    r = 800.0
    r_lo, r_hi = 5.0, 1500.0

    t_band = axis_psi_band_offset(r, r_lo, r_hi)
    t_ge45 = axis_psi_ge45_offset(r, r_lo, r_hi)
    assert abs(t_band - 795.0) < 1e-12
    assert abs(axis_psi_cover_offset(r, r_lo, r_hi) - 795.0) < 1e-12
    assert abs(t_ge45 - 700.0) < 1e-12

    s2_band = second_station_point(s1, theta, r, t_band)
    for r_g in (r_lo, 800.0, r_hi):
        psi = crossing_angle_deg(s1, s2_band, (r_g, 0.0))
        assert 45.0 - 1e-9 <= psi <= 135.0 + 1e-9
    assert abs(axis_crossing_psi_deg(r, t_band, r_lo) - 135.0) < 1e-9
    assert abs(axis_crossing_psi_deg(r, t_band, r_hi) - math.degrees(math.atan2(795.0, 700.0))) < 1e-9

    s2_ge45 = second_station_point(s1, theta, r, t_ge45)
    for r_g in (r_lo, 800.0, r_hi):
        psi = crossing_angle_deg(s1, s2_ge45, (r_g, 0.0))
        assert psi + 1e-9 >= 45.0
    assert abs(axis_crossing_psi_deg(r, t_ge45, r_hi) - 45.0) < 1e-12
    psi_near = axis_crossing_psi_deg(r, t_ge45, r_lo)
    assert psi_near > 135.0
    expected_near = math.degrees(math.acos(-795.0 / math.hypot(795.0, 700.0)))
    assert abs(psi_near - expected_near) < 1e-9

    s2_short = second_station_point(s1, theta, r, 690.9)
    psi_short = crossing_angle_deg(s1, s2_short, (r_hi, 0.0))
    assert psi_short < 45.0
    assert axis_crossing_psi_deg(r, 690.9090909090909, r_hi) < 45.0

    s2_axis = second_station_point(s1, theta, r, 0.0)
    psi0 = crossing_angle_deg(s1, s2_axis, (400.0, 0.0))
    assert psi0 < 1e-6 or abs(psi0 - 180.0) < 1e-6


def test_offaxis_far_corner_is_named_residual() -> None:
    s1 = (0.0, 0.0)
    psi_axis = axis_crossing_psi_deg(800.0, 700.0, 1500.0)
    psi_corner = policy_offaxis_far_psi_deg(r=800.0, t=700.0, r_g=1500.0, err_deg=1.0)
    assert abs(psi_axis - 45.0) < 1e-12
    assert psi_corner < 45.0
    g = wedge_far_corner_point(s1, 0.0, 1500.0, 1.0, t_sign=1.0)
    s2 = second_station_point(s1, 0.0, 800.0, 700.0)
    assert abs(crossing_angle_deg(s1, s2, g) - psi_corner) < 1e-12
    # Along the +1° ray, the far end is worse than a nearer point.
    g_near = wedge_far_corner_point(s1, 0.0, 800.0, 1.0, t_sign=1.0)
    assert crossing_angle_deg(s1, s2, g_near) > psi_corner


if __name__ == "__main__":
    test_axis_iff_band_and_ge45()
    test_offaxis_far_corner_is_named_residual()
    print("ok")
