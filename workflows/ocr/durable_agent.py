"""OCR Invoice Durable Agent - Uses Mistral's Durable Agent feature to orchestrate invoice processing."""

import asyncio

from dotenv import load_dotenv
import os

# load_dotenv must run before importing mistralai_workflows,
# because the config is read from env vars at import time.
load_dotenv()

import mistralai  # noqa: E402
import mistralai_workflows as workflows  # noqa: E402
import mistralai_workflows.plugins.mistralai as workflows_mistralai  # noqa: E402
import mistralai_workflows.plugins.mistralai.activities  # noqa: E402, F401 - registers plugin activities on the worker
import mistralai_workflows.core.encoding.payload_encoder as payload_encoder  # noqa: E402
import mistralai_workflows.core.temporal.payload_codec as payload_codec  # noqa: E402
import mistralai_workflows.core.temporal.payload_converter as payload_converter  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from worker import process_document_ocr, extract_invoice_data  # noqa: E402

api_key = os.environ.get("MISTRAL_API_KEY")

# Encoding format compatibility patch
NEW_ENCODING = "json/wf_v1"
payload_encoder.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_codec.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_converter.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_converter.WithContextJSONPayloadConverter.encoding = property(
    lambda self: NEW_ENCODING
)


class PdfDoc(BaseModel):
    document_url: str


document_url = "https://kltmfijkwchheensxrkw.supabase.co/storage/v1/object/public/github/facture_stylo.pdf"


@workflows.workflow.define(name="ocr_durable_agent")
class OCRDurableAgent:
    @workflows.workflow.entrypoint
    async def entrypoint(self, document_url: str) -> dict:
        session = workflows_mistralai.RemoteSession()

        agent = workflows_mistralai.Agent(
            model="mistral-medium-latest",
            name="ocr-invoice-agent",
            description="Agent that extracts structured data from PDF invoices",
            instructions=(
                "You are an invoice processing agent. "
                "When given a document URL, follow these steps:\n"
                "1. Use process_document_ocr to extract text from the PDF.\n"
                "2. Use extract_invoice_data to get structured invoice fields from the OCR result.\n"
                "3. Return a summary of the extracted invoice data."
            ),
            tools=[process_document_ocr, extract_invoice_data],
            completion_args=mistralai.CompletionArgs(tool_choice="auto"),
        )

        outputs = await workflows_mistralai.Runner.run(
            agent=agent,
            inputs=f"Process the invoice at this URL: {document_url}",
            session=session,
        )

        answer = "\n".join([
            output.text for output in outputs
            if isinstance(output, mistralai.TextChunk)
        ])

        return {"answer": answer}


async def main() -> None:
    # Run the worker — config discovery fetches Temporal settings from the Mistral API
    await workflows.run_worker(
        workflows=[OCRDurableAgent],
        api_key=api_key,
    )


if __name__ == "__main__":
    asyncio.run(main())
