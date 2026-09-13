"""Live 演练 only. Never start 正式测试. robot_id is the logged-in 队号."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib.error import URLError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from searcher import Searcher  # noqa: E402

from jianmo.b_sim.client import SimClient, SimError  # noqa: E402

WS = HERE.parents[3]
OUT = HERE / "results_rehearsal.json"
TRACE = HERE / "rehearsal_q3.jsonl"


def _load_robot_id() -> str:
    env = os.environ.get("JIANMO_B_SIM_ROBOT_ID", "").strip()
    if env:
        return env
    env_path = WS / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("JIANMO_B_SIM_ROBOT_ID="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and not val.startswith("#"):
                    return val
    return ""


def _problem() -> int:
    raw = os.environ.get("JIANMO_B_SIM_PROBLEM", "3").strip()
    return 4 if raw == "4" else 3


def enter_retry(client: SimClient, request_id: str, *, seconds: float = 90.0) -> dict:
    """Hammer /enter while the 5 s countdown has the socket closed.

    The 25-minute window starts at countdown end. Enter within the first 5
    minutes or remaining_real_duration_s drops below 1200.
    """
    deadline = time.time() + seconds
    last: dict | None = None
    last_err: str | None = None
    beat = HERE / "enter_wait.log"
    while time.time() < deadline:
        t0 = time.time()
        try:
            body = client.enter(request_id)
            last = body
            if body.get("accepted"):
                print(
                    "ENTER_OK remaining_real_duration_s=%s virtual_time_s=%s"
                    % (body.get("remaining_real_duration_s"), body.get("virtual_time_s")),
                    flush=True,
                )
                return body
            # JSON refused: robot_id mismatch or already entered. Do not spin.
            return body
        except (SimError, URLError, TimeoutError, OSError) as exc:
            last_err = str(exc)
            beat.write_text(
                "%s waiting_enter last_err=%s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), last_err[:200]),
                encoding="utf-8",
            )
            # Closed socket / countdown: retry immediately. Floor 0.15 s to avoid a tight spin.
            time.sleep(max(0.15, 0.15 - (time.time() - t0)))
    if last is not None:
        return last
    return {"accepted": False, "error": last_err or "enter_timeout", "request_id": request_id}


def main() -> int:
    robot_id = _load_robot_id()
    problem = _problem()
    mixed = problem == 4
    payload: dict = {
        "schema_version": "jianmo.metrics.v0",
        "official_tests": "forbidden",
        "robot_id": robot_id,
        "problem": problem,
        "mixed": mixed,
        "attempted": False,
    }
    if not robot_id:
        payload["blocker"] = "missing_JIANMO_B_SIM_ROBOT_ID"
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    if os.environ.get("JIANMO_B_SIM_ALLOW_OFFICIAL") in {"1", "true", "TRUE"}:
        payload["blocker"] = "refusing_official_flag"
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    trace_path = HERE / ("rehearsal_q4.jsonl" if mixed else "rehearsal_q3.jsonl")
    if trace_path.exists():
        trace_path.unlink()
    # Short timeout while the API is closed (a 60 s hang would burn the 25 min window).
    client = SimClient(robot_id=robot_id, timeout_s=2.0)
    dog = Searcher(client, mixed=mixed, log_path=trace_path, max_actions=900)

    wait_s = float(os.environ.get("JIANMO_B_SIM_ENTER_WAIT_S", "600"))
    print("ARMED problem=%s robot_id=%s wait_s=%s" % (problem, robot_id, wait_s), flush=True)
    enter_body = enter_retry(client, "enter-1", seconds=wait_s)
    client.timeout_s = 15.0
    # Searcher.enter() would mint a new id; reuse the accepted session by injecting state.
    if not enter_body.get("accepted"):
        payload.update(
            {
                "attempted": True,
                "ok": False,
                "blocker": "enter_rejected",
                "enter": enter_body,
                "hint": "Start 问题%d演练测试 (never 正式测试), wait until the API is ready, then re-run."
                % problem,
            }
        )
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 3

    dog.actions = 1
    dog.seq = 1
    dog.x, dog.y, dog.radio = 0.0, 0.0, 1
    dog.remaining_real_s = float(enter_body.get("remaining_real_duration_s") or 1200)
    dog.last_virtual = float(enter_body.get("virtual_time_s") or 0)
    dog._record("/enter", {"request_id": "enter-1"}, enter_body)

    try:
        dog.search_after_enter()
        exit_body = dog.exit()
        n_cleared = len(dog.cleared)
        vt = float(dog.last_virtual)
        mean_s = (vt / n_cleared) if n_cleared else None
        walk = float(dog.walk_m())
        payload.update(
            {
                "attempted": True,
                "ok": True,
                "enter": {k: enter_body.get(k) for k in ("accepted", "remaining_real_duration_s", "virtual_time_s")},
                "exit": exit_body,
                "cleared": sorted(dog.cleared),
                "n_cleared": n_cleared,
                "n_actions": dog.actions,
                "virtual_time_s": vt,
                "walk_m": walk,
                "mean_clear_time_s": mean_s,
                "remaining_unfixed": [c for c in dog.remaining_channels() if c not in dog.fixes],
                "trace": str(trace_path.relative_to(WS)).replace("\\", "/"),
                "note": (
                    "n_cleared is from /clear success. 演练 UI may show true jammer count; "
                    "do not invent n_true. This is not a 正式测试 table."
                ),
            }
        )
        metrics = {
            "n_cleared": float(n_cleared),
            "n_actions": float(dog.actions),
            "virtual_time_s": float(vt),
            "walk_m": walk,
        }
        if mean_s is not None:
            metrics["mean_clear_time_s"] = float(mean_s)
        payload["metrics"] = metrics
        payload["seed"] = 0
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({k: payload[k] for k in payload if k != "exit"}, ensure_ascii=False, indent=2))
        return 0
    except (SimError, URLError, TimeoutError, OSError) as exc:
        payload.update(
            {
                "attempted": True,
                "ok": False,
                "blocker": "sim_error",
                "error": str(exc),
                "cleared": sorted(dog.cleared),
                "n_cleared": len(dog.cleared),
                "n_actions": dog.actions,
                "virtual_time_s": dog.last_virtual,
            }
        )
        try:
            dog.exit()
        except Exception:
            pass
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
