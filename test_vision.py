#!/usr/bin/env python3
"""
Test Claude Vision API on sample PDF.
Usage: python test_vision.py <pdf_path>
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from exam_parser.parser.pdf_loader import PDFLoader
from exam_parser.parser.vision_extractor import VisionExtractor


def test_vision(pdf_path: str):
    """Test Vision extraction on first page"""

    print(f"🔍 Testing Claude Vision on: {pdf_path}\n")

    with PDFLoader(pdf_path) as loader:
        total_pages = loader.get_page_count()
        print(f"📊 Total pages: {total_pages}\n")

        vision = VisionExtractor()

        # Analyze first page
        print("🤖 Analyzing first page with Claude Vision...")
        page = loader.get_page(0)

        try:
            result = vision.analyze_page(page)

            # Display metadata
            print("\n📋 Metadata:")
            metadata = result.get("metadata", {})
            for key, value in metadata.items():
                print(f"  {key}: {value}")

            # Display questions
            questions = result.get("questions", [])
            print(f"\n❓ Questions found: {len(questions)}\n")

            for q in questions[:5]:  # Show first 5
                print(f"Q{q.get('q_number')}: {q.get('q_type')}")
                if q.get('instruction'):
                    print(f"  Instruction: {q.get('instruction')[:60]}...")
                if q.get('stimulus'):
                    print(f"  Stimulus: {len(q.get('stimulus'))} items")
                if q.get('choices'):
                    print(f"  Choices: {len(q.get('choices'))} items")
                print()

            if len(questions) > 5:
                print(f"... and {len(questions) - 5} more questions\n")

            # Save raw JSON
            with open("vision_output.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("✓ Raw output saved to vision_output.json")

            print("\n✅ Vision test completed")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vision.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    test_vision(pdf_path)
