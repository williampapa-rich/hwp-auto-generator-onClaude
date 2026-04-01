#!/usr/bin/env python3
"""
Test OCR extraction from scanned PDF.
Usage: python test_ocr.py <pdf_path>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from exam_parser.parser.pdf_loader import PDFLoader
from exam_parser.parser.ocr_extractor import OCRExtractor
from exam_parser.layout.column_splitter import ColumnSplitter
from exam_parser.layout.reading_order import ReadingOrderManager
from exam_parser.layout.question_grouper import QuestionGrouper
from exam_parser.parser.box_detector import BlockWithBoxType


class OCRBlock:
    """Wrapper to match block_extractor.Block interface"""
    def __init__(self, ocr_block, page_num: int):
        self.block_id = hash(ocr_block.text)
        self.block_type = 0
        self.text = ocr_block.text
        self.bbox = ocr_block.bbox
        self.page_num = page_num
        self.confidence = ocr_block.confidence

    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    def area(self) -> float:
        return self.width() * self.height()


def test_ocr(pdf_path: str):
    """Test OCR extraction from PDF"""

    print(f"🧪 Testing OCR on: {pdf_path}\n")

    with PDFLoader(pdf_path) as loader:
        total_pages = loader.get_page_count()
        print(f"📊 Total pages: {total_pages}\n")

        ocr = OCRExtractor()

        # Process first page only for speed
        print("🤖 Extracting text via OCR (page 0)...")
        page = loader.get_page(0)
        ocr_blocks_raw = ocr.extract_from_page(page)

        print(f"  Raw blocks extracted: {len(ocr_blocks_raw)}")
        for i, block in enumerate(ocr_blocks_raw[:5]):
            print(f"    {i}: conf={block.confidence:.2f} | {block.text[:50]}...")

        # Filter by confidence
        ocr_blocks = ocr.filter_by_confidence(ocr_blocks_raw, threshold=0.4)
        print(f"\n✓ After confidence filter (0.4): {len(ocr_blocks)} blocks")

        # Merge nearby blocks
        ocr_blocks = ocr.merge_nearby_blocks(ocr_blocks, threshold=15.0)
        print(f"✓ After merging nearby: {len(ocr_blocks)} blocks\n")

        # Convert to Block format
        blocks = [OCRBlock(b, 0) for b in ocr_blocks]

        # Column analysis
        print("📐 Column split analysis:")
        col_splitter = ColumnSplitter(blocks, page.rect.width)
        boundary, _ = col_splitter.split_columns()
        left, right, spanning = col_splitter.classify_blocks(boundary)
        print(f"  Column boundary at x={boundary:.1f}")
        print(f"  Left blocks: {len(left)}")
        print(f"  Right blocks: {len(right)}")
        print(f"  Spanning blocks: {len(spanning)}\n")

        # Reading order
        print("📖 Reading order:")
        reader = ReadingOrderManager(page.rect.height)
        ordered = reader.order_blocks(left, right, spanning)
        print(f"  Total ordered blocks: {len(ordered)}")
        for i, block in enumerate(ordered[:10]):
            print(f"    {i}: y={block.bbox[1]:.0f} | {block.text[:40]}...")
        if len(ordered) > 10:
            print(f"    ... and {len(ordered) - 10} more\n")

        # Question grouping
        print("❓ Question grouping:")
        classified = [BlockWithBoxType(b, "text") for b in ordered]
        grouper = QuestionGrouper()
        groups = grouper.group_blocks(classified)
        print(f"  Question groups found: {len(groups)}")
        for group in groups[:10]:
            print(f"    Q{group.q_number}: {len(group.blocks)} blocks | {group.blocks[0].block.text[:40]}...")
        if len(groups) > 10:
            print(f"    ... and {len(groups) - 10} more\n")

        print("✅ OCR Test completed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    try:
        test_ocr(pdf_path)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
