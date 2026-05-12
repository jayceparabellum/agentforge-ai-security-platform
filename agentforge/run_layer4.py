import argparse
import json

from agentforge.deterministic import run_fuzzer, run_regression_replay_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgentForge deterministic Layer 4 tooling.")
    parser.add_argument("tool", choices=["fuzz", "regression"])
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--intensity", choices=["smoke", "scheduled", "deep"], default="smoke")
    args = parser.parse_args()
    if args.tool == "fuzz":
        result = run_fuzzer(max_cases=args.max_cases)
    else:
        result = run_regression_replay_sync(intensity=args.intensity)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
