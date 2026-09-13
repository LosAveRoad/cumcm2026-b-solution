"""Q3 only: finite nine-station discovery and certified bearing contraction.

Standard-library-only implementation. Historical code is in searcher_legacy.py.
The guarantee assumes fixed omni sources, accepted operations and the stated
error/range model. Runtime/network failures return incomplete explicitly.
"""
from __future__ import annotations
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from certificates import certified_covered

ARENA_R, R_HEAR, R_CLEAR, R_INITIAL = 1800.0, 1000.0, 20.0, 1500.0
CONTRACTION = 0.501  # strictly exceeds sqrt(5/4-cos(1 degree))
POSITION_MARGIN_M = 1e-6
MAX_ACTIONS = 900
ACTION_BOUND = 294  # enter + 9*20 measurements + 16*7 service actions + exit


def q3_scouts():
    return [(0.0, 0.0)] + [(1000*math.cos(k*math.pi/4),
                            1000*math.sin(k*math.pi/4)) for k in range(8)]


def contraction_step(station, bearing, radius):
    if not math.isfinite(bearing) or not 0 < radius <= R_INITIAL:
        raise ValueError("invalid contraction state")
    a = math.radians(bearing % 360)
    p = (station[0]+radius/2*math.cos(a), station[1]+radius/2*math.sin(a))
    bound = math.nextafter(CONTRACTION*radius + POSITION_MARGIN_M, math.inf)
    return p, bound


def tsp_visit_order(origin, points):
    """Exact open TSP for at most nine coverage points; deterministic ties."""
    n = len(points)
    if not n:
        return []
    dp = {(1 << j, j): (math.dist(origin, p), (j,)) for j, p in enumerate(points)}
    for mask in range(1, 1 << n):
        for j in range(n):
            item = dp.get((mask, j))
            if item is None:
                continue
            cost, path = item
            for k in range(n):
                if mask & (1 << k):
                    continue
                key = (mask | (1 << k), k)
                cand = (cost + math.dist(points[j], points[k]), path + (k,))
                if key not in dp or cand < dp[key]:
                    dp[key] = cand
    return list(min(dp[((1 << n)-1, j)] for j in range(n))[1])


class SearchStopped(RuntimeError):
    pass


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
    prune: bool = True
    x: float = 0.0
    y: float = 0.0
    radio: int = 1
    actions: int = 0
    cleared: set = field(default_factory=set)
    fixes: dict = field(default_factory=dict)
    discovery_stations: list = field(default_factory=list)
    trace: list = field(default_factory=list)
    certificate_trace: list = field(default_factory=list)
    last_virtual: float = 0.0
    remaining_real_s: float = 1200.0
    detection_complete: bool = False
    stop_reason: str = "not_started"
    _deadline: float = math.inf
    _seq: int = 0
    _entered: bool = False
    _prefix: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self):
        if self.mixed:
            raise ValueError("This searcher is Q3-only; use the separate Q4 files.")
        if self.max_actions < 2:
            raise ValueError("need room for enter and exit")

    def _request(self, kind, *args):
        # Reserve one action for /exit. Count attempts, including rejected calls.
        if kind != "exit" and self.actions >= self.max_actions-1:
            raise SearchStopped("action_budget")
        if kind not in ("enter", "exit") and time.monotonic() >= self._deadline:
            raise SearchStopped("runtime_deadline")
        self._seq += 1
        rid = f"q3-{self._prefix}-{self._seq}"
        self.actions += 1
        body = getattr(self.client, kind)(rid, *args)
        row = {"path": "/"+kind, "request_id": rid, "args": args, "response": body}
        self.trace.append(row)
        if self.log_path is not None:
            with Path(self.log_path).open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False)+"\n")
        if not isinstance(body, dict) or body.get("accepted") is not True:
            raise SearchStopped(kind+"_rejected")
        if kind == "enter":
            self._entered = True
        if "virtual_time_s" in body:
            self.last_virtual = float(body["virtual_time_s"])
        return body

    def enter(self):
        start = time.monotonic()
        body = self._request("enter")
        value = body.get("remaining_real_duration_s")
        if value is None or not math.isfinite(float(value)) or float(value) < 0:
            raise SearchStopped("invalid_remaining_duration")
        self.remaining_real_s = float(value)
        self._deadline = start + max(0.0, self.remaining_real_s-2.0)
        self.x, self.y, self.radio = 0.0, 0.0, 1
        return body

    def exit(self):
        return self._request("exit")

    def measure_at(self, x, y, channel):
        self._valid_position(x, y)
        body = self._request("measure", float(x), float(y), int(channel))
        self.x, self.y, self.radio = x, y, int(channel)
        kind = body.get("measure_result")
        if kind == "direction":
            angle = float(body["svd_deg"])
            if not math.isfinite(angle):
                raise SearchStopped("invalid_bearing")
            self.fixes[channel] = [Fix(x, y, kind, angle % 360)]
        elif kind == "near":
            self.fixes[channel] = [Fix(x, y, kind, None)]
        elif kind != "no_signal":
            raise SearchStopped("invalid_measure_result")
        return body

    def clear_at(self, x, y, channel):
        self._valid_position(x, y)
        body = self._request("clear", float(x), float(y), int(channel))
        self.x, self.y = x, y
        if body.get("clear_result") != "success":
            raise SearchStopped("certified_clear_failed")
        self.cleared.add(channel)
        return body

    @staticmethod
    def _valid_position(x, y):
        if not all(math.isfinite(v) and abs(v) <= 2_000_000 for v in (x, y)):
            raise SearchStopped("invalid_position")

    def remaining_channels(self):
        return [c for c in range(1, 21) if c not in self.cleared]

    def _silent_channels(self):
        return [c for c in range(1, 21) if c not in self.fixes and c not in self.cleared]

    def _n_found(self):
        return len(set(self.fixes) | self.cleared)

    def scan_point(self, point, channels=None, *, chase=False):
        """Commit a discovery station ONLY after the complete accepted scan."""
        if chase:
            raise ValueError("discovery scans cannot chase")
        required = set(self._silent_channels())
        requested = required if channels is None else set(channels)
        order = sorted(requested, key=lambda c: (c != self.radio, c))
        for channel in order:
            body = self.measure_at(*point, channel)
            if body["measure_result"] == "near":
                self.clear_at(*point, channel)
        if required <= requested:
            if point not in self.discovery_stations:
                self.discovery_stations.append(point)
            return True
        return False

    def _discover(self):
        self.scan_point((0.0, 0.0))
        remaining = q3_scouts()[1:]
        while remaining and self._n_found() < 16 and self._silent_channels():
            order = tsp_visit_order((self.x, self.y), remaining)
            point = remaining.pop(order[0])
            disks = [(point, R_HEAR), ((0.0, 0.0), ARENA_R)]
            if self.prune and certified_covered(self.discovery_stations, disks):
                self.certificate_trace.append({"kind": "covered_lens", "scout": point})
                continue
            self.scan_point(point)
        # Each iteration removes one of eight cells: scanned, certified, or no
        # remaining source under the channel-count bound. No heuristic starvation.
        self.detection_complete = True

    def _contract_clear(self, channel):
        fx = self.fixes[channel][-1]
        if fx.kind == "near":
            self.clear_at(fx.x, fx.y, channel)
            return
        bound = R_INITIAL
        for step in range(1, 8):
            point, next_bound = contraction_step((fx.x, fx.y), fx.svd_deg, bound)
            self.certificate_trace.append({"kind": "contraction", "channel": channel,
                "step": step, "point": point, "radius_bound_m": next_bound})
            if next_bound <= R_CLEAR:
                self.clear_at(*point, channel)
                return
            if next_bound > R_HEAR:
                raise SearchStopped("invalid_hearing_certificate")
            body = self.measure_at(*point, channel)
            if body["measure_result"] == "near":
                self.clear_at(*point, channel)
                return
            if body["measure_result"] != "direction":
                raise SearchStopped("contraction_no_signal")
            fx, bound = self.fixes[channel][-1], next_bound
        raise SearchStopped("contraction_bound_exhausted")

    def search_after_enter(self):
        self._discover()
        pending = set(self.fixes)-self.cleared
        while pending:
            def approach(c):
                fx = self.fixes[c][-1]
                p = ((fx.x, fx.y) if fx.kind == "near" else
                     contraction_step((fx.x, fx.y), fx.svd_deg, R_INITIAL)[0])
                return math.dist((self.x, self.y), p), c
            # Go directly to the saved bearing's first contraction point.
            channel = min(pending, key=approach)
            self._contract_clear(channel)
            pending.remove(channel)
        self.stop_reason = "complete"

    def run(self):
        entered = False
        exit_body = None
        try:
            self.enter()
            entered = True
            self.search_after_enter()
        except SearchStopped as exc:
            self.stop_reason = str(exc)
        except Exception as exc:
            self.stop_reason = "technical_exception:"+type(exc).__name__+":"+str(exc)
        finally:
            if entered or self._entered:
                try:
                    exit_body = self.exit()
                except Exception as exc:
                    self.stop_reason = "exit_exception:"+str(exc)
        complete = (self.stop_reason == "complete" and self.detection_complete and
                    set(self.fixes) <= self.cleared)
        return {"ok": complete, "complete": complete, "reason": self.stop_reason,
                "policy": "q3_nine_net_contraction_v1", "n_actions": self.actions,
                "n_found": self._n_found(), "n_cleared": len(self.cleared),
                "cleared": sorted(self.cleared), "detection_complete": self.detection_complete,
                "virtual_time_s": self.last_virtual, "exit": exit_body,
                "action_bound_under_model": ACTION_BOUND,
                "remaining_unfixed": self._silent_channels()}
