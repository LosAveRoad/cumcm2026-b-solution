"""Connect only to a simulator window already started by the operator."""
import argparse
import json
from pathlib import Path
from searcher import Searcher
from sim_client import SimClient


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--robot-id", required=True)
    p.add_argument("--base-url", default="http://127.0.0.1:2026")
    p.add_argument("--timeout-s", type=float, default=5)
    p.add_argument("--max-actions", type=int, default=900)
    p.add_argument("--output", default="q3_run_result.json")
    p.add_argument("--trace", default="q3_run_trace.jsonl")
    args = p.parse_args()
    client = SimClient(robot_id=args.robot_id, base_url=args.base_url, timeout_s=args.timeout_s)
    dog = Searcher(client, log_path=Path(args.trace), max_actions=args.max_actions)
    result = dog.run()
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
