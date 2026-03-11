"""OCR Invoice Workflow - Extracts structured data from PDF invoices using Mistral OCR."""

import asyncio
import base64
import json
import os
from typing import Any
from temporalio import activity, workflow
import socket

from dotenv import load_dotenv

# load_dotenv must run before importing mistralai_workflows,
# because the config is read from env vars at import time.
load_dotenv()

import httpx  # noqa: E402
import pydantic  # noqa: E402
from mistralai import Mistral  # noqa: E402

import mistralai_workflows as workflows  # noqa: E402
import mistralai_workflows.core.encoding.payload_encoder as payload_encoder  # noqa: E402
import mistralai_workflows.core.temporal.payload_codec as payload_codec  # noqa: E402
import mistralai_workflows.core.temporal.payload_converter as payload_converter  # noqa: E402

server_url = os.environ.get("SERVER_URL")
api_key = os.environ.get("MISTRAL_API_KEY")
agent_id = os.environ.get("MISTRAL_AGENT_ID")

# Encoding format compatibility patch
NEW_ENCODING = "json/wf_v1"
payload_encoder.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_codec.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_converter.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_converter.WithContextJSONPayloadConverter.encoding = property(
    lambda self: NEW_ENCODING
)

THRESHOLD = 100.0


# Data Models

class DocumentInput(pydantic.BaseModel):
    """Input document URL for OCR processing."""
    document_url: str


class OCRResponse(pydantic.BaseModel):
    """Extracted invoice data and raw text."""
    raw_text: str


class InvoiceData(pydantic.BaseModel):
    """Structured invoice data extracted by LLM."""
    invoice_number: str
    date: str
    total_amount: float
    bank_details: str
    supplier: str
    invoice_category: str


class WorkflowResult(pydantic.BaseModel):
    """Final workflow result."""
    extracted_data: dict[str, Any]
    decision: bool
    total_amount: float
    required_human_approval: bool
    invoice_category: str


client = Mistral(
    server_url=server_url,
    api_key=api_key
)

# Activities

async def download_pdf(url: str) -> bytes:
    """Download a PDF from a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content


@workflows.activity()
async def process_document_ocr(doc: DocumentInput) -> OCRResponse:
    """Extract structured data from a PDF document using Mistral OCR."""

    document_url = doc.document_url

    # Get activity execution info
    info = activity.info()
    print(f"[Worker {socket.gethostname()}:{os.getpid()}] "
        f"Activity '{info.activity_type}' (id={info.activity_id}) "
        f"on task_queue='{info.task_queue}', attempt={info.attempt}, "
        f"workflow_id='{info.workflow_id}'")

    print(f"Downloading document from: {document_url}")
    pdf_bytes = await download_pdf(document_url)
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    print(f"Downloaded {len(pdf_bytes)} bytes")

    print("Running OCR with structured extraction...")
    ocr_response = await client.ocr.process_async(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{base64_pdf}",
        },
        include_image_base64=False,
    )

    # Log the OCR response for debugging
    print("OCR Response:", ocr_response)

    # Extract structured data and raw text
    raw_text_parts = []

    for page in ocr_response.pages:
        raw_text_parts.append(page.markdown)

    return OCRResponse(raw_text="\n\n".join(raw_text_parts))

@workflows.activity()
async def extract_invoice_data(ocr_result: OCRResponse) -> InvoiceData:
    """Extract structured invoice data from raw text using LLM."""

    # Get activity execution info
    info = activity.info()
    print(f"[Worker {socket.gethostname()}:{os.getpid()}] "
        f"Activity '{info.activity_type}' (id={info.activity_id}) "
        f"on task_queue='{info.task_queue}', attempt={info.attempt}, "
        f"workflow_id='{info.workflow_id}'")

    prompt = '''
    Extract the following information from the invoice text below:

    Invoice text:
    {raw_text}

    ###
    Provide the extracted information in the required format.
    '''

    # Agent from Playground
    inputs = [
        {"role":"user","content":prompt.format(raw_text=ocr_result.raw_text)}
    ]

    try:
        response = client.beta.conversations.start(
            agent_id=agent_id,
            inputs=inputs,
        )
        print(response)

        raw_content = response.outputs[0].content
        invoice_data = InvoiceData.model_validate_json(raw_content)

        print("Extracted invoice data:", invoice_data)
        return invoice_data

    except Exception as e:
        print(f"Error extracting invoice data: {e}")
        # Return default values if extraction fails
        return InvoiceData(
            invoice_number="unknown",
            date="unknown",
            total_amount=0.0,
            bank_details="unknown",
            supplier="unknown",
            invoice_category="unknown"
        )

# Workflow Definition
@workflows.workflow.define(
    name="ocr_invoice_workflow_test",
    workflow_display_name="OCR Invoice Workflow Test",
    workflow_description="Extract structured data from PDF invoices with human approval for high amounts",
)
class OCRDocumentWorkflow:
    """Extracts invoice data from PDFs. Requires human approval for amounts >= threshold."""

    def __init__(self) -> None:
        self.human_approved = False
        self._approval_received = False

    @workflows.workflow.signal(name="approve", description="Human approval signal")
    async def handle_approval(self, approved: bool) -> None:
        """Signal handler for human approval."""
        self.human_approved = approved
        self._approval_received = True
        print(f"Received approval signal: {approved}")

    @workflows.workflow.entrypoint
    async def run(self, document_url: str) -> WorkflowResult:
        """Process document, extract data, and get human approval if needed."""

        info = workflow.info()
        workflow.logger.info(
            f"Workflow '{info.workflow_type}' started | "
            f"workflow_id='{info.workflow_id}', run_id='{info.run_id}', "
            f"task_queue='{info.task_queue}', attempt={info.attempt}"
        )

        # Step 1: Extract raw text from document
        ocr_result = await process_document_ocr(DocumentInput(document_url=document_url))
        print("Raw text extracted:", ocr_result.raw_text[:200] + "...")  # Print first 200 chars

        # Step 2: Extract structured invoice data using LLM
        invoice_data = await extract_invoice_data(ocr_result)

        # Step 3: Check if human approval is needed (e.g., amount > 100)
        requires_approval = invoice_data.total_amount > 100

        # If human approval is required, wait for the signal
        if requires_approval:
            await workflows.workflow.wait_condition(lambda: self._approval_received is True)
            decision = self.human_approved
        else:
            decision = True  # Auto-approve if amount <= 100

        # Convert InvoiceData to dict for WorkflowResult
        extracted_data = {
            "invoice_number": invoice_data.invoice_number,
            "date": invoice_data.date,
            "total_amount": invoice_data.total_amount,
            "supplier": invoice_data.supplier,
            "bank_details": invoice_data.bank_details,
        }

        return WorkflowResult(
            extracted_data=extracted_data,
            decision=decision,
            total_amount=invoice_data.total_amount,
            required_human_approval=requires_approval,
            invoice_category=invoice_data.invoice_category,
        )

# Version STANDARD
async def main() -> None:
    """Start the OCR workflow worker."""
    print("Starting OCR Invoice Workflow worker...")

    # Run the worker — config discovery fetches Temporal settings from the Mistral API
    await workflows.run_worker(
        workflows=[OCRDocumentWorkflow],
        api_key=api_key,
    )

if __name__ == "__main__":
    asyncio.run(main())
