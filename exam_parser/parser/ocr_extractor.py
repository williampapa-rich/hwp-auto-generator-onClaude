import easyocr
import fitz
from typing import List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from PIL import Image
import numpy as np


@dataclass
class OCRBlock:
    """OCR extracted text block with position"""
    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    confidence: float


class OCRExtractor:
    """Extract text from scanned PDF pages using EasyOCR"""

    def __init__(self, languages: List[str] = None, use_gpu: bool = False):
        """
        Initialize OCR extractor.

        Args:
            languages: List of language codes (default: ['ko', 'en'])
            use_gpu: Use GPU if available
        """
        self.languages = languages or ['ko', 'en']
        self.reader = None
        self.use_gpu = use_gpu
        self._initialize_reader()

    def _initialize_reader(self):
        """Lazy load EasyOCR reader"""
        if self.reader is None:
            print(f"🤖 Initializing EasyOCR for {self.languages}...")
            try:
                # Try with SSL verification disabled for model download
                import ssl
                ssl._create_default_https_context = ssl._create_unverified_context
                self.reader = easyocr.Reader(self.languages, gpu=self.use_gpu)
            except Exception as e:
                print(f"⚠️  EasyOCR initialization failed: {e}")
                print("    Attempting with model cache...")
                # Fallback: try without downloading
                self.reader = easyocr.Reader(
                    self.languages,
                    gpu=self.use_gpu,
                    download_enabled=False  # Don't auto-download
                )

    def extract_from_page(self, page: fitz.Page) -> List[OCRBlock]:
        """
        Extract text blocks from PDF page using OCR.

        Args:
            page: PyMuPDF page object

        Returns:
            List of OCRBlock objects
        """
        # Render page to image (more reliable than extracting embedded image)
        mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom for better quality
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to PIL Image
        pil_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img_array = np.array(pil_image)

        # Run OCR
        results = self.reader.readtext(img_array, detail=1)

        # Convert results to OCRBlock format
        # EasyOCR returns: (bbox, text, confidence)
        # bbox format: [[x0,y0], [x1,y1], [x2,y2], [x3,y3]] (corners)
        blocks = []
        for bbox, text, confidence in results:
            if not text.strip():
                continue

            # Convert corner points to axis-aligned bbox
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)

            blocks.append(OCRBlock(
                text=text.strip(),
                bbox=(x0, y0, x1, y1),
                confidence=confidence
            ))

        return blocks

    def extract_from_pdf(self, pdf_path: str) -> dict:
        """
        Extract text from all pages of PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with page number as key, list of OCRBlock as value
        """
        doc = fitz.open(pdf_path)
        all_blocks = {}

        for page_num in range(len(doc)):
            print(f"  Processing page {page_num + 1}/{len(doc)}...", end=" ")
            page = doc[page_num]

            blocks = self.extract_from_page(page)
            all_blocks[page_num] = blocks

            print(f"✓ ({len(blocks)} blocks)")

        doc.close()
        return all_blocks

    def filter_by_confidence(self, blocks: List[OCRBlock], threshold: float = 0.5) -> List[OCRBlock]:
        """Filter blocks by confidence threshold"""
        return [b for b in blocks if b.confidence >= threshold]

    def merge_nearby_blocks(self, blocks: List[OCRBlock], threshold: float = 10.0) -> List[OCRBlock]:
        """
        Merge blocks that are very close horizontally.
        Useful for reassembling split text.

        Args:
            blocks: List of OCRBlock
            threshold: Maximum gap in pixels to consider for merging

        Returns:
            Merged list of OCRBlock
        """
        if not blocks:
            return blocks

        # Sort by y position, then x position
        sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

        merged = []
        current = sorted_blocks[0]

        for next_block in sorted_blocks[1:]:
            # Check if blocks are on same line (similar y coordinates)
            y_diff = abs(next_block.bbox[1] - current.bbox[1])
            if y_diff > (current.bbox[3] - current.bbox[1]) * 0.3:
                # Different line, start new block
                merged.append(current)
                current = next_block
            else:
                # Same line, check horizontal distance
                x_gap = next_block.bbox[0] - current.bbox[2]
                if x_gap < threshold:
                    # Close enough, merge
                    merged_text = current.text + " " + next_block.text
                    merged_bbox = (
                        min(current.bbox[0], next_block.bbox[0]),
                        min(current.bbox[1], next_block.bbox[1]),
                        max(current.bbox[2], next_block.bbox[2]),
                        max(current.bbox[3], next_block.bbox[3])
                    )
                    merged_confidence = (current.confidence + next_block.confidence) / 2
                    current = OCRBlock(merged_text, merged_bbox, merged_confidence)
                else:
                    # Too far, start new block
                    merged.append(current)
                    current = next_block

        merged.append(current)
        return merged
