# run_local.py (updated for local execution)
import asyncio
import json
import os
from dotenv import load_dotenv
from mistralai_workflows import WorkflowsClient  # Use execute_workflow instead of WorkflowsClient
from pydantic import BaseModel
from worker import OCRDocumentWorkflow
import uuid

load_dotenv()

class OCRWorkflowInput(BaseModel):
    document_url: str

async def main() -> None:
    client = WorkflowsClient(
        base_url=os.environ["SERVER_URL"],
        api_key=os.environ["MISTRAL_API_KEY"],
    )
        
    document_url = "https://kltmfijkwchheensxrkw.supabase.co/storage/v1/object/public/github/facture_stylo.pdf"

    print("=" * 70)
    print("OCR INVOICE WORKFLOW (LOCAL EXECUTION)")
    print("=" * 70)
    print(f"\nDocument: {document_url}\n")

    execution_id = uuid.uuid4().hex

    await client.execute_workflow(
        workflow_identifier="ocr_invoice_workflow",
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

    # Convert Pydantic model to dict before JSON serialization
    result_dict = result.model_dump() if hasattr(result, "model_dump") else result

    if isinstance(result_dict, dict):
        decision = result_dict.get("decision", "unknown")
        total_amount = result_dict.get("total_amount", 0)
        required_approval = result_dict.get("required_human_approval", False)
        invoice_category = result_dict.get("invoice_category", "")

        print(f"\nDECISION: {decision}")
        print(f"Total Amount: {total_amount} EUR")
        print(f"Threshold: {100.0} EUR")
        print(f"Required Human Approval: {required_approval}")
        print(f"Invoice category: {invoice_category}")
        print("-" * 70)

        print("\nEXTRACTED DATA:")
        print("-" * 70)
        extracted_data = result_dict.get("extracted_data", {})
        print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
    else:
        # Handle case where result is a Pydantic model
        decision = result.decision if hasattr(result, "decision") else "unknown"
        total_amount = result.total_amount if hasattr(result, "total_amount") else 0
        required_approval = result.required_human_approval if hasattr(result, "required_human_approval") else False
        invoice_category = result.invoice_category if hasattr(result, "invoice_category") else ""

        print(f"\nDECISION: {decision}")
        print(f"Total Amount: {total_amount} EUR")
        print(f"Threshold: {100.0} EUR")
        print(f"Required Human Approval: {required_approval}")
        print(f"Invoice Category: {invoice_category}")
        print("-" * 70)

        print("\nEXTRACTED DATA:")
        print("-" * 70)
        extracted_data = result.extracted_data if hasattr(result, "extracted_data") else {}
        print(json.dumps(extracted_data, indent=2, ensure_ascii=False))

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
