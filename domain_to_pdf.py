import os
import sys
from urllib.parse import urlparse, urljoin
import logging

import requests
from bs4 import BeautifulSoup
import shutil
import pdfkit
from PyPDF2 import PdfWriter, PdfReader

logging.basicConfig(level=logging.INFO, format="%(message)s")


WKHTMLTOPDF_PATH = shutil.which("wkhtmltopdf")
_PDFKIT_CONFIG = (
    pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH) if WKHTMLTOPDF_PATH else None
)


def _url_is_valid(url: str) -> bool:
    """Return ``True`` if ``url`` resolves successfully and is not a 404 page."""

    try:
        head_resp = requests.head(url, allow_redirects=True, timeout=5)
        if head_resp.status_code >= 400:
            return False
    except requests.RequestException:
        # Some servers may not handle HEAD requests
        pass

    try:
        resp = requests.get(url, allow_redirects=True, timeout=5)
        if resp.status_code >= 400:
            return False
        if "error 404" in resp.text.lower():
            return False
        return True
    except requests.RequestException:
        return False


def find_internal_links(base_url: str) -> set[str]:
    """Return a set of full URLs that are internal to ``base_url``."""
    resp = requests.get(base_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    base_netloc = urlparse(base_url).netloc
    links: set[str] = set()

    for a in soup.find_all("a", href=True):
        url = urljoin(base_url, a["href"])
        if urlparse(url).netloc == base_netloc and _url_is_valid(url):
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
    pdfkit.from_url(url, output_path, configuration=_PDFKIT_CONFIG)
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
    logging.info("Validating domain...")
    if not domain.startswith("http"):
        domain = "http://" + domain

    if not _url_is_valid(domain):
        logging.error(f"Domain '{domain}' is not reachable.")
        sys.exit(1)

    logging.info("Scanning for internal links...")
    pages = find_internal_links(domain)

    if pages:
        logging.info(f"Found {len(pages)} internal pages.")
    else:
        logging.info("No internal links found.")
        return

    pdf_paths: list[str] = []

    for idx, url in enumerate(pages, start=1):
        logging.info(f"[{idx}/{len(pages)}] Saving {url}...")
        pdf_path = save_page_as_pdf(url, "pdfs")
        pdf_paths.append(pdf_path)

    logging.info("Merging PDFs...")
    merge_pdfs(pdf_paths, "internal_pages.pdf")
    logging.info("Combined PDF saved as internal_pages.pdf")


if __name__ == '__main__':
    domain = input('Enter domain: ').strip()
    if not domain:
        print('No domain provided.')
        sys.exit(1)
    main(domain)
