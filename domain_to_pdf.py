import os
import sys
import argparse
from urllib.parse import urlparse, urljoin
from typing import Iterable

import requests
from bs4 import BeautifulSoup
import shutil
import pdfkit
from PyPDF2 import PdfWriter, PdfReader

try:
    from IPython.display import clear_output
    _IN_IPYTHON = True
except Exception:
    _IN_IPYTHON = False

# Remove arguments injected by IPython (e.g. "-f <connection file>") so that
# interactive input works when running inside notebooks like Google Colab.
def _remove_ipykernel_args() -> None:
    if "-f" in sys.argv:
        f_index = sys.argv.index("-f")
        # Remove '-f' and the path that follows it if present
        if f_index < len(sys.argv) - 1:
            del sys.argv[f_index : f_index + 2]
        else:
            del sys.argv[f_index]

_remove_ipykernel_args()

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


def _display_line(line: str) -> None:
    """Display ``line`` appropriately for terminal or Jupyter."""
    if _IN_IPYTHON:
        # Overwrite the output cell in notebooks so progress looks clean.
        clear_output(wait=True)
        print(line)
    else:
        # Clear any leftover characters from the previous line by padding the
        # output. 120 characters should be plenty for our messages.
        print("\r" + line.ljust(120), end="", flush=True)


def _url_is_valid(url: str) -> tuple[bool, str | None]:
    """Return ``(True, text)`` if ``url`` resolves successfully and is not a
    404 page. ``text`` contains the fetched page content when available."""

    try:
        head_resp = requests.head(url, allow_redirects=True, timeout=5)
        if head_resp.status_code >= 400:
            return False, None
    except requests.RequestException:
        pass

    try:
        resp = requests.get(url, allow_redirects=True, timeout=5)
        if resp.status_code >= 400:
            return False, resp.text
        text = resp.text
        if "error 404" in text.lower():
            return False, text
        return True, text
    except requests.RequestException:
        return False, None


def _print_progress(prefix: str, idx: int, total: int, message: str = "") -> None:
    """Print a single-line progress bar with an optional message.

    This helper attempts to keep the output on a single line so the
    progress looks clean even when the terminal does not fully support
    carriage return based updates.
    """

    bar_len = 30
    filled_len = int(bar_len * idx / total)
    bar = "#" * filled_len + "-" * (bar_len - filled_len)
    line = f"{prefix} [{bar}] {idx}/{total} {message}"

    _display_line(line)


def _contains_keywords(text: str, keywords: Iterable[str]) -> bool:
    """Return ``True`` if any keyword appears in ``text``."""

    text_l = text.lower()
    return any(k.lower() in text_l for k in keywords)


def find_internal_links(base_url: str, keywords: Iterable[str] | None = None) -> tuple[set[str], int, int]:
    """Return all valid internal links for ``base_url``.

    The search is performed recursively so that links discovered on each
    internal page are also scanned. The function returns a tuple
    ``(links, total_internal, invalid_count)`` where ``links`` is a set of valid
    internal URLs, ``total_internal`` is the number of internal links
    encountered across the entire site and ``invalid_count`` is how many of
    those links were not valid.
    """

    base_netloc = urlparse(base_url).netloc

    links: set[str] = {base_url}
    checked_links: set[str] = {base_url}
    invalid_count = 0
    total_internal = 0

    to_visit: set[str] = {base_url}
    visited_pages: set[str] = set()

    while to_visit:
        page_url = to_visit.pop()
        if page_url in visited_pages:
            continue
        visited_pages.add(page_url)

        try:
            resp = requests.get(page_url, timeout=5)
            resp.raise_for_status()
        except requests.RequestException:
            invalid_count += 1
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.find_all("a", href=True)

        total = len(anchors)
        for idx, a in enumerate(anchors, start=1):
            url = urljoin(page_url, a["href"])
            if urlparse(url).netloc != base_netloc:
                continue
            total_internal += 1
            if url in checked_links:
                continue
            checked_links.add(url)
            anchor_text = a.get_text()
            href_text = a["href"]
            if keywords and not _contains_keywords(anchor_text + " " + href_text, keywords):
                continue
            valid, text = _url_is_valid(url)
            if valid and (not keywords or (text and _contains_keywords(text, keywords))):
                links.add(url)
                to_visit.add(url)
                status = f"Valid: {url}"
            else:
                invalid_count += 1
                status = f"Invalid: {url}"
            _print_progress(
                "Checking links",
                idx,
                total,
                f"(total: {total_internal}, valid: {len(links)}, invalid: {invalid_count}) {status}",
            )
        if not anchors:
            _print_progress(
                "Checking links",
                1,
                1,
                f"(total: {total_internal}, valid: {len(links)}, invalid: {invalid_count})",
            )
        print()

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
    """Yield items from ``iterable`` while printing a simple progress bar."""

    total = len(iterable)
    for idx, item in enumerate(iterable, start=1):
        bar_len = 30
        filled_len = int(bar_len * idx / total)
        bar = "#" * filled_len + "-" * (bar_len - filled_len)
        line = f"{prefix} [{bar}] {idx}/{total}"
        _display_line(line)
        yield idx, item

    print()


def process_domain(domain: str, keywords: Iterable[str] | None = None) -> None:
    """Process ``domain`` by downloading and merging its pages.

    Only pages containing any of ``keywords`` are processed when provided."""

    info(f"Validating domain {domain}...")
    if not domain.startswith("http"):
        domain = "http://" + domain

    valid, _ = _url_is_valid(domain)
    if not valid:
        error(f"Domain '{domain}' is not reachable.")
        return

    info("Scanning for internal links...")
    pages, total_internal, invalid_count = find_internal_links(domain, keywords)
    valid_count = len(pages)

    if total_internal:
        info(
            f"Checked {total_internal} internal links: {valid_count} valid, {invalid_count} invalid."
        )
    else:
        info("No internal links found.")
        return

    netloc = urlparse(domain).netloc
    output_dir = os.path.join("pdfs", netloc)

    pdf_paths: list[str] = []
    for idx, url in _progress(pages, prefix=f"Saving PDFs ({netloc})"):
        pdf_path = save_page_as_pdf(url, output_dir)
        pdf_paths.append(pdf_path)

    output_pdf = os.path.join(output_dir, f"{netloc}.pdf")
    info("Merging PDFs...")
    merge_pdfs(pdf_paths, output_pdf)
    info(f"Combined PDF saved as {output_pdf}")


def main(domains: list[str], keywords: Iterable[str] | None = None) -> None:
    for domain in domains:
        process_domain(domain, keywords)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('domains', nargs='*', help='Domain(s) to process')
    parser.add_argument('--filter', nargs='+', help='Keywords to filter pages')
    args, _ = parser.parse_known_args()

    domains = args.domains
    if not domains:
        domains = input('Enter domain(s) separated by spaces: ').split()

    if not domains:
        print('No domain provided.')
        sys.exit(1)

    keywords = args.filter

    main(domains, keywords)
