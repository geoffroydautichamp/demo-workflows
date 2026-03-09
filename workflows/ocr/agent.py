import mistralai_workflows as workflows
import mistralai_workflows.plugins.mistralai as workflows_mistralai
import mistralai_workflows.core.encoding.payload_encoder as payload_encoder
import mistralai_workflows.core.temporal.payload_codec as payload_codec
import mistralai_workflows.core.temporal.payload_converter as payload_converter
from worker import process_document_ocr, extract_invoice_data
import asyncio
from pydantic import BaseModel
from typing import Any

# Encoding format compatibility patch
NEW_ENCODING = "json/wf_v1"
payload_encoder.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_codec.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_converter.CUSTOM_ENCODING_FORMAT = NEW_ENCODING
payload_converter.WithContextJSONPayloadConverter.encoding = property(
    lambda self: NEW_ENCODING
)


class pdfDoc(BaseModel):
    document_url: str


document_url = "https://kltmfijkwchheensxrkw.supabase.co/storage/v1/object/public/github/facture_stylo.pdf"

@workflows.workflow.define(name="ocr_agent")
class OCRAgent:
    @workflows.workflow.entrypoint
    async def entrypoint(self, document_url: str) -> Any:
        # Use the existing workflow activities directly instead of agent tools
        try:
            # Step 1: Process the document with OCR
            ocr_result = await process_document_ocr(document_url)
            print(f"OCR processing completed. Extracted data: {ocr_result.extracted_data}")
            
            # Step 2: Extract invoice data from OCR results
            invoice_data = await extract_invoice_data(ocr_result)
            print(f"Invoice data extraction completed: {invoice_data}")
            
            # Return the structured result
            return {
                "success": True,
                "ocr_result": ocr_result.model_dump(),
                "invoice_data": invoice_data.model_dump(),
                "message": "Document processed successfully"
            }
            
        except Exception as e:
            print(f"Error processing document: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process document"
            }

async def main() -> None:
    
    result = await workflows.execute_workflow(
        OCRAgent,
        params=pdfDoc(document_url=document_url)
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
