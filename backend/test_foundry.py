import os
import asyncio
from dotenv import load_dotenv
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential

load_dotenv()

async def main():
    credential = AzureCliCredential()
    client = FoundryChatClient(
        credential=credential,
        project_endpoint=os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
        model=os.getenv("FOUNDRY_MODEL"),
    )
    agent = client.as_agent(
        instructions="You are a helpful assistant. Keep answers brief."
    )
    response = await agent.run("Say hello.")
    print(response)

asyncio.run(main())