from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader


def extract_text_from_weblink(url: str, timeout: int = 20) -> str:
    """Fetch a web page and return cleaned visible text."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def extract_text_from_weblinks(urls: list[str], timeout: int = 20) -> dict[str, str]:
    """Extract text for each URL; failures are returned as error strings."""
    extracted: dict[str, str] = {}
    for url in urls:
        cleaned = url.strip()
        if not cleaned:
            continue
        try:
            extracted[cleaned] = extract_text_from_weblink(cleaned, timeout=timeout)
        except (requests.RequestException, ValueError) as exc:
            extracted[cleaned] = f"ERROR: {exc}"
    return extracted


def extract_text_from_pdf_file(file_obj: BinaryIO) -> str:
    """Extract text from a single PDF file-like object."""
    file_obj.seek(0)
    reader = PdfReader(file_obj)
    pages_text: list[str] = []

    for page in reader.pages:
        pages_text.append(page.extract_text() or "")

    return "\n".join(pages_text).strip()


def extract_text_from_pdfs(uploaded_files: list[object]) -> dict[str, str]:
    """Extract text from Streamlit uploaded PDF objects."""
    extracted: dict[str, str] = {}

    for pdf_file in uploaded_files:
        name = getattr(pdf_file, "name", "unknown.pdf")
        try:
            file_bytes = pdf_file.read()
            text = extract_text_from_pdf_file(BytesIO(file_bytes))
            extracted[name] = text
        except (ValueError, OSError) as exc:
            extracted[name] = f"ERROR: {exc}"
        finally:
            if hasattr(pdf_file, "seek"):
                pdf_file.seek(0)

    return extracted
