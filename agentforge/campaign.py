import asyncio

from agentforge.core import MultiAgentCore


async def run_campaign(intensity: str = "scheduled") -> dict:
    return await MultiAgentCore().run_campaign(intensity=intensity)


def run_campaign_sync(intensity: str = "scheduled") -> dict:
    return asyncio.run(run_campaign(intensity=intensity))
