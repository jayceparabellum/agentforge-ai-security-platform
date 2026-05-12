import asyncio
import json

from agentforge.config import get_settings
from agentforge.target import TargetClient


async def run() -> dict:
    return await TargetClient(get_settings()).probe()


def main() -> None:
    print(json.dumps(asyncio.run(run()), indent=2))


if __name__ == "__main__":
    main()
