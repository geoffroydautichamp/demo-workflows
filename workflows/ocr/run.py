"""Execute the OCR Invoice Workflow."""

import asyncio
import json
import os
import uuid

from dotenv import load_dotenv
from mistralai_workflows import WorkflowsClient
from pydantic import BaseModel

load_dotenv()


class OCRWorkflowInput(BaseModel):
    """Input for the OCR workflow."""
    document_url: str


async def run_single(client: WorkflowsClient, invoice_id: int) -> None:
    """Run the OCR workflow on a single invoice."""
    invoices_url = "https://raw.githubusercontent.com/geoffroydautichamp/demo-workflows/master/invoices/batch1-{id}.jpg"
    document_url = invoices_url.format(id=invoice_id)
    execution_id = uuid.uuid4().hex

    print(f"[{invoice_id}] Starting workflow for {document_url}")
    print(f"[{invoice_id}] Execution ID: {execution_id}")

    await client.execute_workflow(
        workflow_identifier="ocr_invoice_workflow_test",
        input_data=OCRWorkflowInput(document_url=document_url),
        execution_id=execution_id,
    )

    print(f"[{invoice_id}] Workflow started. Waiting for completion...")
    print(f"[{invoice_id}] To approve: uv run python workflows/ocr/approve.py {execution_id}")

    response = await client.wait_for_workflow_completion(execution_id)
    result = response.result

    print("=" * 70)
    print(f"[{invoice_id}] Workflow completed!")

    if isinstance(result, dict):
        decision = result.get("decision", "unknown")
        total_amount = result.get("total_amount", 0)
        required_approval = result.get("required_human_approval", False)

        print(f"[{invoice_id}] DECISION: {decision}")
        print(f"[{invoice_id}] Total Amount: {total_amount} EUR")
        print(f"[{invoice_id}] Required Human Approval: {required_approval}")
        print("-" * 70)

        print(f"[{invoice_id}] EXTRACTED DATA:")
        extracted = result.get("extracted_data", result)
        print(json.dumps(extracted, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    print("=" * 70)


async def main() -> None:
    """Run OCR workflows on all invoices in parallel."""
    client = WorkflowsClient(
        base_url=os.environ["SERVER_URL"],
        api_key=os.environ["MISTRAL_API_KEY"],
    )

    invoice_ids = range(1472, 1490)
    print(f"Launching {len(invoice_ids)} workflows in parallel...\n")

    await asyncio.gather(*(run_single(client, id) for id in invoice_ids))


if __name__ == "__main__":
    asyncio.run(main())
