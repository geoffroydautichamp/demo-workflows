"""Send approval signal to a running OCR workflow."""

import asyncio
import os
import sys

from dotenv import load_dotenv
from mistralai_workflows import WorkflowsClient
from pydantic import BaseModel

load_dotenv()


class ApprovalInput(BaseModel):
    """Input for the approval signal."""
    approved: bool


async def send_approval(execution_id: str, approved: bool = True) -> None:
    """Send approval signal to a workflow execution."""
    client = WorkflowsClient(
        base_url=os.environ["SERVER_URL"],
        api_key=os.environ["MISTRAL_API_KEY"],
    )

    await client.signal_workflow(
        execution_id=execution_id,
        signal_name="approve",
        input_data=ApprovalInput(approved=approved),
    )

    status = "APPROVED" if approved else "REJECTED"
    print(f"Sent {status} signal to execution: {execution_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python workflows/ocr/approve.py <execution_id> [--reject]")
        sys.exit(1)

    exec_id = sys.argv[1]
    approved = "--reject" not in sys.argv

    asyncio.run(send_approval(exec_id, approved))
