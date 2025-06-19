# Website to PDF

This repository contains a Python script that downloads **all** internal pages of a given domain as PDFs and then merges them into a single file. Every page discovered on the site is scanned so links found within internal pages are also followed.

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
Internal links are validated as they are discovered so invalid pages are skipped immediately. Links discovered within internal pages are followed as well, ensuring every reachable page is processed. Any page that contains the text "Error 404" is skipped.

Progress is displayed in the console so you can follow link validation, page saving and PDF merging without flooding your terminal. A simple progress bar shows the download of each page.
