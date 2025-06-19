import os
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import pdfkit
from PyPDF2 import PdfWriter, PdfReader


def _get_root_domain(netloc: str) -> str:
    """Return the registrable part of a netloc (e.g. example.com)."""
    parts = netloc.split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return netloc


def find_subdomain_links(base_url):
    """Fetch base_url and return set of full URLs to subdomains within the same domain."""
    resp = requests.get(base_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    base_netloc = urlparse(base_url).netloc
    base_root = _get_root_domain(base_netloc)
    links = set()
    for a in soup.find_all('a', href=True):
        url = urljoin(base_url, a['href'])
        netloc = urlparse(url).netloc
        if netloc and netloc != base_netloc and _get_root_domain(netloc) == base_root:
            links.add(url)
    return links


def save_page_as_pdf(url, output_dir):
    """Save the given URL as a PDF in output_dir and return the path."""
    os.makedirs(output_dir, exist_ok=True)
    filename = urlparse(url).netloc.replace('.', '_') + '.pdf'
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
    subdomains = find_subdomain_links(domain)
    pdf_paths = []
    for url in subdomains:
        print(f"Saving {url}...")
        pdf_path = save_page_as_pdf(url, 'pdfs')
        pdf_paths.append(pdf_path)
    if pdf_paths:
        merge_pdfs(pdf_paths, 'all_subdomains.pdf')
        print('Combined PDF saved as all_subdomains.pdf')
    else:
        print('No subdomains found.')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: python domain_to_pdf.py <domain>')
        sys.exit(1)
    main(sys.argv[1])
