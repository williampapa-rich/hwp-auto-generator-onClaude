import fitz
import base64
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass
import anthropic
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from exam_parser.config import ANTHROPIC_API_KEY


@dataclass
class VisionBlock:
    """Vision-extracted text block"""
    text: str
    block_type: str  # "text", "instruction", "stimulus", "choice", "etc"


class VisionExtractor:
    """Extract and parse exam structure using Claude Vision API"""

    def __init__(self, api_key: str = None):
        """
        Initialize Vision extractor.

        Args:
            api_key: Anthropic API key (default: from ANTHROPIC_API_KEY env var)
        """
        key = api_key or ANTHROPIC_API_KEY
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Please set it in .env file or environment variable."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.model = "claude-3-5-sonnet-20241022"

    def extract_page_image(self, page: fitz.Page, zoom: float = 1.5) -> bytes:
        """
        Render page to PNG image.

        Args:
            page: PyMuPDF page object
            zoom: Zoom level for rendering

        Returns:
            PNG image bytes
        """
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")

    def analyze_page(self, page: fitz.Page) -> dict:
        """
        Analyze exam page structure using Claude Vision.

        Args:
            page: PyMuPDF page object

        Returns:
            Extracted structure with questions, metadata, etc
        """
        # Render page to image
        image_data = self.extract_page_image(page)
        image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

        # Call Claude Vision
        message = self.client.messages.create(
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
   - stimulus: [
       - 지문, 박스 텍스트, 이미지 설명 등
       - 순서대로 배열
     ]
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

결과는 순수 JSON만 반환하세요. 마크다운 포맷이나 설명은 빼고 JSON만.
""",
                        },
                    ],
                }
            ],
        )

        response_text = message.content[0].text

        # Parse JSON response
        import json
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse Claude response: {response_text}")

    def extract_from_pdf(self, pdf_path: str) -> dict:
        """
        Extract all pages from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Combined structure from all pages
        """
        doc = fitz.open(pdf_path)

        all_metadata = {}
        all_questions = []

        for page_num in range(len(doc)):
            print(f"  Processing page {page_num + 1}/{len(doc)}...", end=" ")
            page = doc[page_num]

            try:
                result = self.analyze_page(page)

                # Merge metadata (first page wins)
                if page_num == 0 and result.get("metadata"):
                    all_metadata = result["metadata"]

                # Collect questions
                if result.get("questions"):
                    all_questions.extend(result["questions"])

                print("✓")
            except Exception as e:
                print(f"❌ Error: {e}")

        doc.close()

        return {
            "metadata": all_metadata,
            "questions": all_questions
        }
