import argparse
import json

from agentforge.campaign import run_campaign_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an AgentForge adversarial campaign.")
    parser.add_argument("--intensity", choices=["smoke", "scheduled", "deep"], default="scheduled")
    args = parser.parse_args()
    print(json.dumps(run_campaign_sync(intensity=args.intensity), indent=2))


if __name__ == "__main__":
    main()

