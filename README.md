# Website to PDF

This repository contains a Python script that downloads the internal pages of a given domain as PDFs and then merges them into a single file.

## Requirements
- Python 3
- `requests`
- `beautifulsoup4`
- `pdfkit` (requires `wkhtmltopdf` installed)
- `PyPDF2`

## Usage

Run the script and provide a domain when prompted:

```bash
python domain_to_pdf.py
```

The script will create a `pdfs` directory with individual PDFs and an `internal_pages.pdf` file containing all merged pages.
Internal links are validated before processing to avoid invalid pages.
