import argparse
import json

from agentforge.agents.threat_intel import ThreatIntelAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh AgentForge external threat intelligence feeds.")
    parser.add_argument("--campaign-id", default="threat-intel-refresh")
    args = parser.parse_args()
    result = ThreatIntelAgent().refresh(campaign_id=args.campaign_id)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
