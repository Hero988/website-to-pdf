import os
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import pdfkit
from PyPDF2 import PdfWriter, PdfReader


def find_internal_links(base_url):
    """Fetch base_url and return set of full URLs within the same domain."""
    resp = requests.get(base_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    base_netloc = urlparse(base_url).netloc
    links = set()
    for a in soup.find_all('a', href=True):
        url = urljoin(base_url, a['href'])
        if urlparse(url).netloc == base_netloc:
            links.add(url)
    return links


def save_page_as_pdf(url, output_dir):
    """Save the given URL as a PDF in output_dir and return the path."""
    os.makedirs(output_dir, exist_ok=True)
    parsed = urlparse(url)
    safe_path = parsed.path.strip('/') or 'index'
    safe_path = safe_path.replace('/', '_')
    filename = f"{parsed.netloc.replace('.', '_')}_{safe_path}.pdf"
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
    if not domain.startswith('http'):  # Add scheme if missing
        domain = 'http://' + domain
    pages = find_internal_links(domain)
    pdf_paths = []
    for url in pages:
        print(f"Saving {url}...")
        pdf_path = save_page_as_pdf(url, 'pdfs')
        pdf_paths.append(pdf_path)
    if pdf_paths:
        merge_pdfs(pdf_paths, 'all_pages.pdf')
        print('Combined PDF saved as all_pages.pdf')
    else:
        print('No internal pages found.')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: python domain_to_pdf.py <domain>')
        sys.exit(1)
    main(sys.argv[1])
