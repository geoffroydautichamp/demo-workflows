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


async def main() -> None:
    """Run the OCR workflow on the sample dental invoice."""
    client = WorkflowsClient(
        base_url=os.environ["SERVER_URL"],
        api_key=os.environ["MISTRAL_API_KEY"],
    )

    invoices_folder = "invoices"
        # "https://kltmfijkwchheensxrkw.supabase.co/storage/v1/object/public/github/facture_stylo.pdf"
        # "https://raw.githubusercontent.com/natashaklingenbrunn/insurance-workflow-demp/main/Facture%20Dentiste%20Sophie%20Martin.pdf"
        # "https://kltmfijkwchheensxrkw.supabase.co/storage/v1/object/public/github/facture.pdf"

    execution_id = uuid.uuid4().hex

    print("=" * 70)
    print("OCR INVOICE WORKFLOW")
    print("=" * 70)
    print(f"\nDocument: {document_url}")
    print(f"Execution ID: {execution_id}\n")

    # Version with Temporal server
    # Start the workflow (don't wait - it may need human approval)
    await client.execute_workflow(
        workflow_identifier="ocr_invoice_workflow_test",
        input_data=OCRWorkflowInput(document_url=document_url),
        execution_id=execution_id,
    )

    print("Workflow started. Waiting for completion...")
    print("(If amount >= 100 EUR, human approval is required)")
    print(f"\nTo approve: uv run python workflows/ocr/approve.py {execution_id}\n")

    # Wait for completion
    response = await client.wait_for_workflow_completion(execution_id)
    result = response.result

    print("Workflow completed!")
    print("=" * 70)

    if isinstance(result, dict):
        decision = result.get("decision", "unknown")
        total_amount = result.get("total_amount", 0)
        required_approval = result.get("required_human_approval", False)

        print(f"\nDECISION: {decision}")
        print(f"Total Amount: {total_amount} EUR")
        print(f"Threshold: 100 EUR")
        print(f"Required Human Approval: {required_approval}")
        print("-" * 70)

        print("\nEXTRACTED DATA:")
        print("-" * 70)
        extracted = result.get("extracted_data", result)
        print(json.dumps(extracted, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
