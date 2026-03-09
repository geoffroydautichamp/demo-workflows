import asyncio
from worker import download_pdf, process_document_ocr, extract_invoice_data

document_url = "https://kltmfijkwchheensxrkw.supabase.co/storage/v1/object/public/github/facture_stylo.pdf"

async def main():
    """Download document and process it"""
    # Download the PDF
    pdf_bytes = await download_pdf(document_url)
    print(f"Downloaded PDF with {len(pdf_bytes)} bytes")

    # Process the document with OCR
    ocr_result = await process_document_ocr(document_url)
    invoice_data = await extract_invoice_data(ocr_result)
    print("OCR Processing Complete!")
    print("Extracted Data:", ocr_result.extracted_data)
    print("Raw Text:", ocr_result.raw_text[:500])
    print("Structured Output result:", invoice_data)

if __name__ == "__main__":
    asyncio.run(main())
    