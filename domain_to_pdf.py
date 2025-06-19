import os
import sys
from urllib.parse import urlparse, urljoin
from typing import Iterable

import requests
from bs4 import BeautifulSoup
import shutil
import pdfkit
from PyPDF2 import PdfWriter, PdfReader

# Simple colored output helpers
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def info(message: str) -> None:
    print(f"{GREEN}{message}{RESET}")


def error(message: str) -> None:
    print(f"{RED}{message}{RESET}")


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


def find_internal_links(base_url: str) -> tuple[set[str], int, int]:
    """Return valid internal links and counters.

    Returns a tuple ``(links, total_internal, invalid_count)`` where ``links`` is
    a set of valid internal URLs, ``total_internal`` is the number of internal
    links encountered and ``invalid_count`` is how many of those were not valid.
    """

    resp = requests.get(base_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    base_netloc = urlparse(base_url).netloc
    anchors = soup.find_all("a", href=True)

    links: set[str] = set()
    invalid_count = 0
    total_internal = 0

    for idx, a in _progress(anchors, prefix="Checking links"):
        url = urljoin(base_url, a["href"])
        if urlparse(url).netloc != base_netloc:
            continue
        total_internal += 1
        if _url_is_valid(url):
            info(f"Valid: {url}")
            links.add(url)
        else:
            error(f"Invalid: {url}")
            invalid_count += 1

    return links, total_internal, invalid_count


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


def _progress(iterable: Iterable[str], prefix: str = ""):
    total = len(iterable)
    for idx, item in enumerate(iterable, start=1):
        bar_len = 30
        filled_len = int(bar_len * idx / total)
        bar = "#" * filled_len + "-" * (bar_len - filled_len)
        print(f"\r{prefix} [{bar}] {idx}/{total}", end="", flush=True)
        yield idx, item
    print()


def main(domain):
    info("Validating domain...")
    if not domain.startswith("http"):
        domain = "http://" + domain

    if not _url_is_valid(domain):
        error(f"Domain '{domain}' is not reachable.")
        sys.exit(1)

    info("Scanning for internal links...")
    pages, total_internal, invalid_count = find_internal_links(domain)
    valid_count = len(pages)

    if total_internal:
        info(
            f"Checked {total_internal} internal links: {valid_count} valid, {invalid_count} invalid."
        )
    else:
        info("No internal links found.")
        return

    pdf_paths: list[str] = []

    for idx, url in _progress(pages, prefix="Saving PDFs"):
        pdf_path = save_page_as_pdf(url, "pdfs")
        pdf_paths.append(pdf_path)

    info("Merging PDFs...")
    merge_pdfs(pdf_paths, "internal_pages.pdf")
    info("Combined PDF saved as internal_pages.pdf")


if __name__ == '__main__':
    domain = input('Enter domain: ').strip()
    if not domain:
        print('No domain provided.')
        sys.exit(1)
    main(domain)
