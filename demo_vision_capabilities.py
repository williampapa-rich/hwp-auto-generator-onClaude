#!/usr/bin/env python3
"""
Claude Vision API Demo — Comprehensive Exam PDF Analysis
=========================================================

This script demonstrates Claude's multimodal capabilities for analyzing
scanned exam PDFs, including:
- Page-by-page extraction with visual understanding
- Metadata recognition from headers
- Question structure understanding
- Choice classification and points extraction
- Visual layout comprehension (boxes, formatting, hierarchy)
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from exam_parser.config import ANTHROPIC_API_KEY


class VisionCapabilitiesDemo:
    """Demonstrate Claude Vision's exam PDF analysis capabilities."""

    def __init__(self):
        """Initialize the demo with Anthropic client."""
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Please set it in .env file."
            )
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-opus-4-6"  # Use best model for vision analysis

    def extract_page_image(self, page: fitz.Page, zoom: float = 1.5) -> bytes:
        """Render PDF page to PNG image.

        Args:
            page: PyMuPDF page object
            zoom: Zoom level for rendering (1.5 = 150% resolution)

        Returns:
            PNG image bytes
        """
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")

    def analyze_page_full_structure(self, page: fitz.Page, page_num: int) -> dict:
        """Analyze complete page structure using Claude Vision.

        This shows Claude understanding:
        - Metadata from headers
        - Question numbers and types
        - Stimulus vs choices vs instructions
        - Visual hierarchy and formatting
        """
        image_data = self.extract_page_image(page)
        image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

        print(f"\n📖 Page {page_num} - Full Structure Analysis")
        print("=" * 60)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": """이 이미지는 한국 중/고등학교 영어 시험지입니다.

다음 정보를 JSON 형식으로 추출하세요:

1. 메타데이터 (페이지 헤더에서):
   - school_name: 학교명
   - year: 연도
   - semester: 학기 (1 또는 2)
   - exam_type: 시험 유형 (중간, 기말, 수시 등)
   - grade: 학년
   - subject: 과목명

2. 모든 문항에 대해:
   - q_number: 문항 번호 (1, 2-1, 3가 등)
   - q_type: 문항 유형 (multiple_choice 또는 subjective)
   - points: 배점 (숫자만, 없으면 null)
   - instruction: 지시문 (다음을 읽고... 등)
   - stimulus: 지문, 박스 텍스트, 이미지 설명 등 순서대로
   - choices: ["①", "②", "③", "④", "⑤"] 형식의 선택지 배열
   - sub_questions: 하위 문항 (가, 나 등)

3. 주의사항:
   - stimulus 배열 순서는 페이지에서의 읽기 순서를 따릅니다
   - 선택지는 기호를 포함하여 정확히 표기합니다
   - 점수는 (3점), [4점], 〔4점〕 등에서 숫자만 추출합니다
   - 모든 텍스트는 정확하게 입력합니다

출력 형식:
{
  "metadata": {...},
  "questions": [...]
}

결과는 순수 JSON만 반환하세요. 마크다운 포맷이나 설명은 빼고 JSON만.""",
                        },
                    ],
                }
            ],
        )

        response_text = response.content[0].text

        # Parse and pretty-print JSON
        try:
            result = json.loads(response_text)
            print("\n✅ Extracted Structure:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        except json.JSONDecodeError:
            print("\n⚠️  Could not parse JSON response.")
            print(f"Raw response:\n{response_text}")
            return {"error": "JSON parsing failed", "raw": response_text}

    def analyze_page_capabilities(self, page: fitz.Page, page_num: int) -> dict:
        """Demonstrate specific Claude Vision capabilities."""
        image_data = self.extract_page_image(page)
        image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

        print(f"\n🔍 Page {page_num} - Capability Analysis")
        print("=" * 60)

        capabilities = [
            {
                "name": "Visual Hierarchy Understanding",
                "prompt": "이 페이지의 시각적 계층 구조를 분석해주세요. 제목, 문항번호, 지시문, 선택지의 위치와 크기, 강조 표시 등을 설명하세요.",
            },
            {
                "name": "Text Layout Recognition",
                "prompt": "페이지에 있는 텍스트 박스들을 식별하세요. 각 박스의 목적(지문, 조건, 보기 등)을 설명하세요.",
            },
            {
                "name": "Question Type Detection",
                "prompt": "이 페이지의 모든 문항들을 식별하고, 각 문항이 객관식인지 주관식인지 판단하세요.",
            },
            {
                "name": "Metadata Extraction",
                "prompt": "페이지 헤더에서 학교명, 학년, 과목, 시험 유형, 연도 등의 메타데이터를 추출하세요.",
            },
        ]

        results = {}
        for capability in capabilities:
            print(f"\n  {capability['name']}:")
            print("  " + "-" * 50)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64,
                                },
                            },
                            {"type": "text", "text": capability["prompt"]},
                        ],
                    }
                ],
            )

            response_text = response.content[0].text
            print(f"  {response_text[:300]}...")
            results[capability["name"]] = response_text

        return results

    def compare_with_ocr_limitations(self, page: fitz.Page, page_num: int) -> dict:
        """Show what Vision can do that OCR cannot."""
        image_data = self.extract_page_image(page)
        image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

        print(f"\n🎯 Page {page_num} - Vision vs OCR Comparison")
        print("=" * 60)

        prompt = """이 시험지 페이지에 대해 다음을 분석해주세요:

1. OCR이 놓칠 수 있는 것들:
   - 페이지의 전체 구조와 계층 관계
   - 문항의 의미 있는 그룹화
   - 지시문, 지문, 선택지의 의미적 구분
   - 메타데이터의 자동 추출

2. Claude Vision이 할 수 있는 것:
   - 위의 모든 항목을 자동으로 처리
   - 구조화된 JSON 형식으로 직접 출력
   - 예상 정확도와 이유를 설명

JSON 형식으로 답변하세요:
{
  "ocr_limitations": ["제한사항1", "제한사항2", ...],
  "vision_advantages": ["장점1", "장점2", ...],
  "estimated_accuracy": "95-99%",
  "reason": "설명"
}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        response_text = response.content[0].text

        try:
            result = json.loads(response_text)
            print("\n📊 Analysis Results:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        except json.JSONDecodeError:
            print("\n⚠️  Response:")
            print(response_text)
            return {"error": "JSON parsing failed", "raw": response_text}

    def run_demo(self, pdf_path: str, pages: Optional[list] = None):
        """Run comprehensive vision capability demonstration.

        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to analyze (0-indexed). None = first page only.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return

        print("\n" + "=" * 70)
        print("🎬 Claude Vision API — Exam PDF Analysis Demonstration")
        print("=" * 70)

        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        if pages is None:
            pages = [0]  # First page only by default
        elif isinstance(pages, int):
            pages = [pages]

        # Validate page numbers
        pages = [p for p in pages if 0 <= p < total_pages]

        if not pages:
            print(f"❌ Invalid page numbers. PDF has {total_pages} pages.")
            return

        print(f"\n📄 PDF: {pdf_path.name}")
        print(f"📑 Total Pages: {total_pages}")
        print(f"🔍 Analyzing Pages: {[p+1 for p in pages]}")

        for page_num in pages:
            page = doc[page_num]

            # 1. Full structure extraction
            structure = self.analyze_page_full_structure(page, page_num + 1)

            # 2. Capability analysis
            capabilities = self.analyze_page_capabilities(page, page_num + 1)

            # 3. Vision vs OCR comparison
            comparison = self.compare_with_ocr_limitations(page, page_num + 1)

            # Save results
            output_dir = PROJECT_ROOT / "demo_results"
            output_dir.mkdir(exist_ok=True)

            result_file = output_dir / f"page_{page_num + 1}_analysis.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "page_number": page_num + 1,
                        "structure": structure,
                        "capabilities": capabilities,
                        "comparison": comparison,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(f"\n✅ Results saved to: {result_file}")

        doc.close()

        print("\n" + "=" * 70)
        print("✨ Vision Capability Demo Complete")
        print("=" * 70)


def main():
    """Run the vision capabilities demo."""
    parser = argparse.ArgumentParser(
        description="Claude Vision API — Exam PDF Analysis Demo"
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=str(PROJECT_ROOT / "sample" / "sample.pdf"),
        help="Path to PDF file",
    )
    parser.add_argument(
        "--pages",
        type=int,
        nargs="+",
        default=None,
        help="Page numbers to analyze (1-indexed). Default: 1",
    )

    args = parser.parse_args()

    # Convert 1-indexed to 0-indexed
    pages = [p - 1 for p in args.pages] if args.pages else None

    demo = VisionCapabilitiesDemo()
    demo.run_demo(args.pdf_path, pages)


if __name__ == "__main__":
    main()
