from __future__ import annotations

import json

from agentforge.evaluation import evaluate_golden_cases


def main() -> None:
    print(json.dumps(evaluate_golden_cases(write_latest=True), indent=2))


if __name__ == "__main__":
    main()
