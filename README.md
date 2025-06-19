# Website to PDF

This repository contains a Python script that downloads **all** internal pages of a given domain as PDFs and then merges them into a single file. Every page discovered on the site is scanned so links found within internal pages are also followed.

## Requirements
- Python 3
- `requests`
- `beautifulsoup4`
- `pdfkit` (requires `wkhtmltopdf` installed)
- `PyPDF2`

## Usage

Run the script and provide one or more domains when prompted or via command line:

```bash
python domain_to_pdf.py example.com example.org
```

The script will create a `pdfs/<domain>` directory for each domain with individual PDFs. A final merged PDF named `<domain>.pdf` is placed in the same directory.
Internal links are validated as they are discovered so invalid pages are skipped immediately. Links discovered within internal pages are followed as well, ensuring every reachable page is processed. Any page that contains the text "Error 404" is skipped. All checked internal links are remembered so duplicates are not validated again.

Progress is displayed in the console so you can follow link validation, page saving and PDF merging without flooding your terminal. A simple progress bar shows the download of each page.

### Running in Jupyter or Google Colab

When running the script inside a notebook environment (e.g. Google Colab), use
the `!python` command. The script automatically removes arguments inserted by
IPython so you can simply run:

```bash
!python domain_to_pdf.py
```
If you do not pass domains on the command line, the script will prompt you to
enter them interactively.

Progress output is updated in-place using IPython's display utilities so the
progress bars remain tidy in notebook cells.
