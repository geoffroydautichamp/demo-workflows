# Mistral Workflows Demo

## Setup

```bash
uv sync
```

Configure `.env`:
```
MISTRAL_API_KEY=your_api_key
```

## Workflows

### OCR Invoice Workflow
Extracts structured data from PDF invoices using Mistral OCR, detects the total amount and processes based on threshold. 

  - When amount >= 100: workflow pauses and waits for human approval signal                                                                                                                                                                      
  - When amount < 100: auto-approved immediately     

I first demo uploading the PDF in AI Studio and structured extraction, then show how this can be integrated into a workflow with HITL.
I run the worker and trigger the workflow, then approve via the UI (not the CLI) to show HITL, and then go through the traces in the UI. 

link to the url for demo here (dummy data, publicly accessible): https://github.com/natashaklingenbrunn/insurance-workflow-demp/raw/main/Facture%20Dentiste%20Sophie%20Martin.pdf

```bash
# Terminal 1 - Start worker
uv run python workflows/ocr/worker.py

# Terminal 2 - Run workflow
uv run python workflows/ocr/run.py

# Terminal 3 - Optionally, send approval via CLI instead of UI
uv run python workflows/ocr/approve.py <execution_id>
# Or reject via CLI:
uv run python workflows/ocr/approve.py <execution_id> --reject
```


### Email Agent Workflow
Sends emails to a Mistral AI agent to classifiy them as either medical, dental, pharmacy, or other. They can then be routed to the appropriate system for further processing.

```bash
# Terminal 1
uv run python workflows/agent/worker.py

# Terminal 2
uv run python workflows/agent/run.py
```

A sample text can be found here:
```
To whom it may concern, Please find attached the dental invoice for 127,5 EUR issued on 19/11/2025. Could you confirm receipt and process the reimbursement? Let me know if further details are needed. Best regards, Sophie Martin
```

## Utilities

```bash
# Terminate a running workflow execution
uv run python workflows/utils.py <execution_id>
```