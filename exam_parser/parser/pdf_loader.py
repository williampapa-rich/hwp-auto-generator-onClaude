import fitz
from pathlib import Path
from typing import Iterator


class PDFLoader:
    """Load and iterate through PDF pages"""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        self.doc = fitz.open(self.pdf_path)

    def get_page_count(self) -> int:
        """Get total number of pages"""
        return len(self.doc)

    def get_page(self, page_num: int) -> fitz.Page:
        """Get specific page (0-indexed)"""
        if page_num < 0 or page_num >= len(self.doc):
            raise IndexError(f"Page {page_num} out of range (0-{len(self.doc)-1})")
        return self.doc[page_num]

    def iterate_pages(self) -> Iterator[tuple[int, fitz.Page]]:
        """Iterate through all pages with page numbers"""
        for page_num in range(len(self.doc)):
            yield page_num, self.doc[page_num]

    def close(self):
        """Close PDF document"""
        self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
