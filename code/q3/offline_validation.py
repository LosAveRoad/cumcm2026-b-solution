"""Independent, deterministic Q3 test double. NO official simulator/network calls.

This is not the official simulator. Error is fixed at each (source, position).
Run: python offline_validation.py --output offline_results.json
"""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path
from searcher import Searcher, ACTION_BOUND


class OfflineClient:
    def __init__(self, sources, mode="spatial", reject_measure=None, duration=1200.0):
        self.sources = sources  # channel -> (x, y, effective radius)
        self.mode, self.reject_measure, self.duration = mode, reject_measure, duration
        self.cleared = set()
        self.point, self.radio, self.virtual, self.walk = (0.0, 0.0), 1, 0.0, 0.0
        self.requests = []
        self.measure_count = 0

    def _response(self, rid, **fields):
        assert rid not in self.requests, "duplicate request ID"
        self.requests.append(rid)
        return {"accepted": True, "virtual_time_s": self.virtual, **fields}

    def enter(self, rid):
        return self._response(rid, remaining_real_duration_s=self.duration)

    def exit(self, rid):
        return self._response(rid)

    def _move(self, x, y):
        d = math.dist(self.point, (x, y))
        self.walk += d
        self.virtual += d/5
        self.point = (x, y)

    def error(self, channel, x, y):
        if self.mode == "positive":
            return 1.0
        if self.mode == "negative":
            return -1.0
        if self.mode == "zero":
            return 0.0
        b = hashlib.sha256(f"{channel}:{x.hex()}:{y.hex()}".encode()).digest()
        if self.mode == "extremes":
            return 1.0 if b[0] & 1 else -1.0
        return 2*int.from_bytes(b[:8], "big")/(2**64-1)-1

    def measure(self, rid, x, y, channel):
        self.measure_count += 1
        if self.measure_count == self.reject_measure:
            return {"accepted": False, "error": "injected_rejection"}
        self._move(x, y)
        self.virtual += 5 + (self.radio != channel)
        self.radio = channel
        source = self.sources.get(channel)
        if source is None or channel in self.cleared or math.dist((x, y), source[:2]) > source[2]:
            return self._response(rid, measure_result="no_signal")
        if math.dist((x, y), source[:2]) <= 5:
            return self._response(rid, measure_result="near")
        angle = math.degrees(math.atan2(source[1]-y, source[0]-x))
        return self._response(rid, measure_result="direction",
                              svd_deg=(angle+self.error(channel, x, y)) % 360)

    def clear(self, rid, x, y, channel):
        self._move(x, y)
        source = self.sources.get(channel)
        success = source is not None and channel not in self.cleared and math.dist(source[:2], (x, y)) <= 20
        self.virtual += 5 if success else 3
        if success:
            self.cleared.add(channel)
        return self._response(rid, clear_result="success" if success else "no_target_in_range")


def make_scene(seed, n, kind):
    rng = random.Random(seed)
    channels = rng.sample(range(1, 21), n)
    sources = {}
    for k, c in enumerate(channels):
        angle = rng.uniform(0, 2*math.pi)
        r = 1800 if kind == "boundary" else 1800*math.sqrt(rng.random())
        if kind == "cluster":
            angle, r = 0.3 + 0.02*k, 1500+10*k
        radius = 1000 if kind in ("boundary", "cluster") else rng.uniform(1000, 1500)
        sources[c] = (r*math.cos(angle), r*math.sin(angle), radius)
    if kind == "regression":
        sources[channels[0]] = (1800*math.cos(math.pi/24), 1800*math.sin(math.pi/24), 1000)
        sources[channels[1]] = (1400, 0, 1500)
        sources[channels[2]] = (0, 0, 1000)
    return sources


def validate_scene(seed, n, kind, mode, prune=True):
    client = OfflineClient(make_scene(seed, n, kind), mode)
    dog = Searcher(client, prune=prune)
    started = time.perf_counter()
    result = dog.run()
    elapsed = time.perf_counter()-started
    assert result["complete"], result
    assert len(client.cleared) == n
    assert result["n_actions"] <= ACTION_BOUND
    max_ratio = 0
    for event in dog.certificate_trace:
        if event["kind"] != "contraction":
            continue
        source = client.sources[event["channel"]]
        d = math.dist(source[:2], event["point"])
        assert d <= event["radius_bound_m"], (event, d)
        max_ratio = max(max_ratio, d/event["radius_bound_m"])
    return {"seed": seed, "n_true": n, "scene": kind, "error_mode": mode,
            "n_cleared": len(client.cleared), "n_actions": dog.actions,
            "virtual_time_s": client.virtual, "mean_clear_time_s": client.virtual/n,
            "walk_m": client.walk, "offline_runtime_s": elapsed,
            "max_actual_to_bound_ratio": max_ratio, "prune": prune}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="offline_results.json")
    args = parser.parse_args()
    rows = []
    for i in range(48):
        rows.append(validate_scene(20260913+i, 10+i%7,
                    ("uniform", "boundary", "cluster", "regression")[i%4],
                    ("positive", "negative", "zero", "spatial", "extremes")[i%5]))
    out = {"kind": "offline_model_validation_not_official_simulator", "seed_base": 20260913,
           "policy": "q3_nine_net_contraction_v1", "n_scenes": len(rows),
           "n_full_clear": len(rows), "min_actions": min(r["n_actions"] for r in rows),
           "max_actions": max(r["n_actions"] for r in rows),
           "pooled_mean_clear_time_s": sum(r["virtual_time_s"] for r in rows)/sum(r["n_true"] for r in rows),
           "mean_walk_m": sum(r["walk_m"] for r in rows)/len(rows), "rows": rows}
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
