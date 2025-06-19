import os
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
import pdfkit
from PyPDF2 import PdfWriter, PdfReader


def find_internal_links(base_url: str) -> set[str]:
    """Return a set of full URLs that are internal to ``base_url``."""
    resp = requests.get(base_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    base_netloc = urlparse(base_url).netloc
    links: set[str] = set()

    for a in soup.find_all("a", href=True):
        url = urljoin(base_url, a["href"])
        if urlparse(url).netloc == base_netloc:
            links.add(url)

    return links


def save_page_as_pdf(url: str, output_dir: str) -> str:
    """Save ``url`` as a PDF in ``output_dir`` and return the created path."""
    os.makedirs(output_dir, exist_ok=True)

    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    filename = f"{parsed.netloc.replace('.', '_')}_{path.replace('/', '_')}.pdf"

    output_path = os.path.join(output_dir, filename)
    pdfkit.from_url(url, output_path)
    return output_path


def merge_pdfs(pdf_paths, output_file):
    """Merge PDFs from pdf_paths into output_file."""
    writer = PdfWriter()
    for pdf in pdf_paths:
        reader = PdfReader(pdf)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_file, 'wb') as f:
        writer.write(f)


def main(domain):
    if not domain.startswith("http"):  # Add scheme if missing
        domain = "http://" + domain

    pages = find_internal_links(domain)
    pdf_paths: list[str] = []

    for url in pages:
        print(f"Saving {url}...")
        pdf_path = save_page_as_pdf(url, "pdfs")
        pdf_paths.append(pdf_path)

    if pdf_paths:
        merge_pdfs(pdf_paths, "internal_pages.pdf")
        print("Combined PDF saved as internal_pages.pdf")
    else:
        print("No internal links found.")


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: python domain_to_pdf.py <domain>')
        sys.exit(1)
    main(sys.argv[1])
