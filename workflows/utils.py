"""Utility functions for managing workflow runs."""

import asyncio
import os
import sys

from dotenv import load_dotenv
from mistralai_workflows import WorkflowsClient

load_dotenv()


async def terminate_run(execution_id: str) -> None:
    """Terminate a workflow execution by ID."""
    client = WorkflowsClient(
        base_url=os.environ["SERVER_URL"],
        api_key=os.environ["MISTRAL_API_KEY"],
    )
    await client.terminate_workflow_execution(execution_id=execution_id)
    print(f"Terminated: {execution_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python workflows/utils.py <execution_id>")
        sys.exit(1)
    asyncio.run(terminate_run(sys.argv[1]))
