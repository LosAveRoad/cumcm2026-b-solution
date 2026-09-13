"""Regenerate paper figure 24 from the current N9 + R12 coordinates.

Run with Python 3, NumPy and Matplotlib installed. Outputs PNG and vector PDF
under paper/figures. The example explicitly uses R_eff = 1000 m; points outside
that disk must not be described as inaudible for every possible R_eff.
"""

from pathlib import Path
import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Wedge
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "paper/tables/q4_visit_xy.csv"
OUTPUT = ROOT / "paper/figures/directional_listen"
G = np.array([1200.0, 0.0])
U_H = np.array([1.0, 0.0])
R_EFF = 1000.0
INK = "#252525"
GRAY = "#8B9299"
BLUE = "#376987"
RED = "#BA4435"


def configure_fonts():
    """Prefer the paper's Chinese serif style, with portable fallbacks."""
    candidates = [Path("/Library/Fonts/SimSun.ttf"),
                  Path("/System/Library/Fonts/Supplemental/Songti.ttc")]
    songti = next((path for path in candidates if path.exists()), None)
    if songti is not None:
        font_manager.fontManager.addfont(str(songti))
        cjk_name = font_manager.FontProperties(fname=str(songti)).get_name()
    else:
        cjk_name = "Noto Serif CJK SC"
    plt.rcParams.update({
        "font.family": [cjk_name, "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 12,
        "axes.labelsize": 13,
        "axes.titlesize": 14,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "axes.unicode_minus": False,
        "axes.linewidth": 0.8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
    })


def read_and_verify():
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    xy = np.array([[float(row["x"]), float(row["y"])] for row in rows])
    outer = np.array([row["role"] == "外环R12" for row in rows])
    # Independently check the coordinate table against the equations in the text.
    inner_angles = np.arange(8) * np.pi / 4
    outer_angles = np.arange(12) * np.pi / 6
    expected = np.vstack((
        [0.0, 0.0],
        1000 * np.column_stack((np.cos(inner_angles), np.sin(inner_angles))),
        2000 * np.column_stack((np.cos(outer_angles), np.sin(outer_angles))),
    ))
    assert xy.shape == (21, 2) and np.allclose(xy, expected, atol=1e-9)
    distance = np.linalg.norm(xy - G, axis=1)
    projection = (xy - G) @ U_H
    in_disk = distance <= R_EFF + 1e-9
    in_front = projection >= -1e-9
    audible = in_disk & in_front
    rear = in_disk & ~in_front
    outside = ~in_disk
    assert (audible.sum(), rear.sum(), outside.sum()) == (1, 3, 17)
    assert np.allclose(xy[audible][0], [2000, 0])
    assert np.isclose(distance[audible][0], 800)
    return xy, outer, audible, rear, outside


def draw_geometry(ax, *, overview):
    ax.set_aspect("equal", adjustable="box")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(direction="out", length=3.5, color=GRAY)
    ax.set_xlabel(r"$x$ / m", labelpad=6)
    ax.set_ylabel(r"$y$ / m", labelpad=6)
    ax.add_patch(Wedge(G, R_EFF, 90, 270, facecolor="#EDF2F5",
                       edgecolor="none", zorder=0))
    ax.add_patch(Wedge(G, R_EFF, -90, 90, facecolor="#FAE8E4",
                       edgecolor="none", zorder=0))
    if overview:
        ax.add_patch(Circle((0, 0), 1000, fill=False, edgecolor="#C5CBD0",
                            linestyle=":", linewidth=0.9, zorder=1))
        ax.add_patch(Circle((0, 0), 2000, fill=False, edgecolor=GRAY,
                            linestyle=(0, (2, 3)), linewidth=1.0, zorder=1))
        ax.add_patch(Circle((0, 0), 1800, fill=False, edgecolor=INK,
                            linewidth=1.15, zorder=1))
    ax.add_patch(Circle(G, R_EFF, fill=False, edgecolor=GRAY,
                        linestyle=(0, (4, 3)), linewidth=1.2, zorder=2))
    ax.add_patch(Wedge(G, R_EFF, -90, 90, fill=False, edgecolor=RED,
                       linewidth=1.1, zorder=2))


def draw_stations(ax, xy, outer, audible, rear, outside):
    for group, marker in ((~outer, "o"), (outer, "s")):
        for condition, face, edge, size in (
            (outside, "white", GRAY, 42),
            (rear, BLUE, BLUE, 50),
            (audible, RED, RED, 75),
        ):
            points = xy[group & condition]
            ax.scatter(points[:, 0], points[:, 1], marker=marker, s=size,
                       facecolor=face, edgecolor=edge, linewidth=1.2, zorder=5)
    ax.scatter(*G, marker="D", s=42, color=INK, zorder=7)


def main():
    configure_fonts()
    xy, outer, audible, rear, outside = read_and_verify()
    fig, axes = plt.subplots(1, 2, figsize=(10.7, 5.65))
    fig.subplots_adjust(left=0.08, right=0.985, bottom=0.20, top=0.85, wspace=0.28)
    fig.suptitle(r"$G=(1200,0)\ \mathrm{m},\quad H=0^\circ,\quad R_{\mathrm{eff}}=1000\ \mathrm{m}$",
                 y=0.97, fontsize=15)

    for index, ax in enumerate(axes):
        draw_geometry(ax, overview=index == 0)
        draw_stations(ax, xy, outer, audible, rear, outside)

    ax = axes[0]
    ax.set_title(r"(a) 完整检测网 $N_9\cup R_{12}$", pad=12)
    ax.set(xlim=(-2350, 2350), ylim=(-2350, 2350),
           xticks=[-2000, -1000, 0, 1000, 2000],
           yticks=[-2000, -1000, 0, 1000, 2000])
    ax.annotate(r"$O$", (0, 0), xytext=(-16, -20), textcoords="offset points")
    ax.annotate(r"$G$", G, xytext=(-4, -23), textcoords="offset points")
    ax.annotate("场地边界：1800 m", (-1450, 1067), xytext=(-2200, 2250),
                fontsize=11, ha="left", va="top",
                arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.8})
    ax.annotate("外环：2000 m", (-1732, -1000), xytext=(-2160, -2220),
                fontsize=11, ha="left", va="bottom",
                arrowprops={"arrowstyle": "-", "color": GRAY, "lw": 0.8})
    ax.annotate("", (1700, 0), G,
                arrowprops={"arrowstyle": "->", "color": INK, "lw": 1.5})

    ax = axes[1]
    ax.set_title("(b) 接收范围与前、背瓣", pad=12)
    ax.set(xlim=(50, 2450), ylim=(-1200, 1200),
           xticks=[200, 700, 1200, 1700, 2200], yticks=[-1000, -500, 0, 500, 1000])
    ax.text(735, 400, "背瓣", color=BLUE, ha="center", fontsize=14)
    ax.text(1655, 400, "前瓣", color=RED, ha="center", fontsize=14)
    ax.text(710, -570, "距离内但不可听", color=BLUE, ha="center", fontsize=11)
    ax.annotate(r"$G$", G, xytext=(-5, 12), textcoords="offset points", fontsize=14)
    ax.annotate(r"$S^\star$", (2000, 0), xytext=(-5, 12), textcoords="offset points", ha="right", color=RED, fontsize=14)
    ax.annotate("", (1670, 0), G,
                arrowprops={"arrowstyle": "->", "color": INK, "lw": 1.5})
    ax.text(1450, 105, r"$H$", fontsize=14)
    ax.annotate(r"$S_b$", (1000, 0), xytext=(650, -190), color=BLUE,
                fontsize=13, arrowprops={"arrowstyle": "-", "color": BLUE, "lw": 0.8})
    ax.plot([1200, 1200], [-50, -260], color=RED, lw=0.8)
    ax.plot([2000, 2000], [-50, -260], color=RED, lw=0.8)
    ax.annotate("", (2000, -230), (1200, -230),
                arrowprops={"arrowstyle": "<->", "color": RED, "lw": 1.0})
    ax.text(1600, -335, "800 m", color=RED, ha="center", fontsize=12)
    ax.annotate("1000 m 距离边界", (350, 526), xytext=(70, 1140), fontsize=11,
                va="top", arrowprops={"arrowstyle": "-", "color": GRAY, "lw": 0.8})
    ax.annotate("前瓣内但距离超限", (1732.05, 1000), xytext=(2370, 1180),
                ha="right", va="top", fontsize=11, color="#5D636A",
                arrowprops={"arrowstyle": "-", "color": GRAY, "lw": 0.8})

    handles = [
        Line2D([], [], marker="D", linestyle="none", color=INK, markersize=6, label="干扰源"),
        Line2D([], [], marker="s", linestyle="none", color=RED, markersize=7, label="可听网点"),
        Line2D([], [], marker="o", linestyle="none", color=BLUE, markersize=6, label="距离内、背瓣网点"),
        Line2D([], [], marker="s", linestyle="none", markeredgecolor=GRAY,
               markerfacecolor="white", markersize=6, label="距离超限网点"),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.53, 0.025),
               ncol=4, frameon=False, handletextpad=0.55, columnspacing=1.65, fontsize=12)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        fig.savefig(OUTPUT.with_suffix(f".{extension}"), dpi=360, bbox_inches="tight", pad_inches=0.09)
    plt.close(fig)
    print(json.dumps({
        "source": str(SOURCE.relative_to(ROOT)),
        "radius_m": R_EFF,
        "station_count": len(xy),
        "audible_count": int(audible.sum()),
        "rear_within_range_count": int(rear.sum()),
        "outside_range_count": int(outside.sum()),
        "audible_station_xy_m": xy[audible].tolist(),
        "GS_star_m": float(np.linalg.norm(xy[audible][0] - G)),
        "software": f"Matplotlib {matplotlib.__version__}",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
