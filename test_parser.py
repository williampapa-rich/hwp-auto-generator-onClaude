#!/usr/bin/env python3
"""
Simple test script to validate parser on a sample PDF.
Usage: python test_parser.py <pdf_path>
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from exam_parser.parser.pdf_loader import PDFLoader
from exam_parser.parser.block_extractor import BlockExtractor
from exam_parser.parser.box_detector import BoxDetector
from exam_parser.layout.column_splitter import ColumnSplitter
from exam_parser.layout.reading_order import ReadingOrderManager
from exam_parser.layout.question_grouper import QuestionGrouper


def test_basic_extraction(pdf_path: str):
    """Test basic PDF extraction without LLM"""

    print(f"🧪 Testing PDF: {pdf_path}\n")

    with PDFLoader(pdf_path) as loader:
        total_pages = loader.get_page_count()
        print(f"📊 Total pages: {total_pages}\n")

        # Process first page
        page = loader.get_page(0)
        print(f"📄 Page 0 dimensions: {page.rect.width}x{page.rect.height}px\n")

        # Extract blocks
        extractor = BlockExtractor(page)
        blocks = extractor.extract_blocks()
        print(f"📦 Extracted {len(blocks)} blocks:")
        for i, block in enumerate(blocks[:5]):  # Show first 5
            print(f"  {i}: {block.block_type} | {block.text[:50]}... | bbox={block.bbox}")
        if len(blocks) > 5:
            print(f"  ... and {len(blocks) - 5} more\n")

        # Classify boxes
        detector = BoxDetector(page)
        classified = detector.classify_blocks(blocks)
        print(f"\n🎯 Box classification:")
        box_types = {}
        for item in classified:
            t = item.box_type
            box_types[t] = box_types.get(t, 0) + 1
        for t, count in box_types.items():
            print(f"  {t}: {count}")

        # Split columns
        col_splitter = ColumnSplitter(blocks, page.rect.width)
        boundary, _ = col_splitter.split_columns()
        left, right, spanning = col_splitter.classify_blocks(boundary)
        print(f"\n📐 Column split at x={boundary:.1f}:")
        print(f"  Left blocks: {len(left)}")
        print(f"  Right blocks: {len(right)}")
        print(f"  Spanning blocks: {len(spanning)}")

        # Reading order
        reader = ReadingOrderManager(page.rect.height)
        ordered = reader.order_blocks(left, right, spanning)
        print(f"\n📖 Reading order: {len(ordered)} blocks")
        for i, block in enumerate(ordered[:10]):  # Show first 10
            print(f"  {i}: y={block.bbox[1]:.0f} | {block.text[:40]}...")

        # Question grouping
        grouper = QuestionGrouper()
        groups = grouper.group_blocks(classified)
        print(f"\n❓ Question groups: {len(groups)}")
        for group in groups[:5]:
            print(f"  Q{group.q_number}: {len(group.blocks)} blocks (pages {group.start_page}-{group.end_page})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_parser.py <pdf_path>")
        print("\nTests basic extraction without LLM")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    try:
        test_basic_extraction(pdf_path)
        print("\n✅ Test completed")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
