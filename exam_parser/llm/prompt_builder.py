import re
from typing import List
from exam_parser.parser.box_detector import BlockWithBoxType
from exam_parser.models.schema import StimulusItem


class PromptBuilder:
    """Build prompts for LLM question extraction"""

    SYSTEM_PROMPT = """You are a Korean high school exam paper structured data extractor.

You will receive pre-processed data for a single exam question with block types
already classified (text, text_box, condition_box, image) in correct reading order.

## Rules:
1. "instruction" = 지시문 (다음을 읽고..., 괄호 안에... 등 학생 지시 문장)
2. "stimulus" = 지문, 박스 텍스트, 조건, 이미지 (입력 순서 유지)
3. "choices" = ①②③④⑤ 포함 줄 → 배열로 추출
4. "q_type": choices 비어있으면 "subjective", 있으면 "multiple_choice"
5. "points": "(4.5점)", "[4점]", "〔4점〕" 등에서 float 추출, 없으면 null
6. stimulus type 매핑:
   - text: 일반 단락
   - text_box: 흰 테두리 사각형 안 텍스트
   - condition_box: 회색/음영 사각형 (조건, 보기, <보기>)
   - image: 제공된 src 경로 그대로 사용
7. sub_questions: 가)/나)/(A)/(B) 등 하위 문항만 채움
8. 출력: 순수 JSON만. 마크다운 펜스 없음. 설명 없음.

## Schema:
{"q_number":"string","q_type":"multiple_choice|subjective","points":4.5,
"instruction":"string|null","stimulus":[{"type":"text|text_box|condition_box|image",
"content":"string"}],"choices":["① ..."],"sub_questions":[]}"""

    @staticmethod
    def build_user_prompt(q_number: str, blocks: List[BlockWithBoxType]) -> str:
        """Build user message for single question"""

        stimulus_items = []
        for block_with_type in blocks:
            block = block_with_type.block
            box_type = block_with_type.box_type

            if block.block_type == 1:  # Image
                stimulus_items.append(f'[IMAGE: {block.text}]')
            else:
                stimulus_items.append(f'[{box_type.upper()}] {block.text}')

        stimulus_text = '\n'.join(stimulus_items)

        return f"""Question Number: {q_number}

Stimulus content (in reading order):
{stimulus_text}

Extract structured data for this question in JSON format."""

    @staticmethod
    def extract_points(text: str) -> float:
        """Extract points from text like '(4.5점)', '[4점]', '〔4점〕'"""
        # Pattern: number (with optional decimal) followed by 점
        match = re.search(r'[\[\(\〔]?(\d+\.?\d*)[\]\)\〕]?\s*점', text)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def extract_choices(text: str) -> List[str]:
        """Extract multiple choice options (①②③④⑤)"""
        choices = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if line and line[0] in '①②③④⑤':
                choices.append(line)

        return choices


class MetadataPromptBuilder:
    """Build prompt for exam metadata extraction"""

    METADATA_SYSTEM_PROMPT = """You are a Korean exam paper metadata extractor.

Extract exam information from header text of first page.

## Rules:
- school_name: 학교명
- year: 연도 (정수)
- semester: 1 또는 2 (1학기/2학기)
- exam_type: "중간", "기말", "수시" 등
- grade: 학년 (정수)
- subject: 과목명

## Output JSON format:
{"school_name":"string|null","year":2025,"semester":1,"exam_type":"string|null",
"grade":1,"subject":"string|null"}

출력: 순수 JSON만. 설명 없음."""

    @staticmethod
    def build_metadata_prompt(header_text: str) -> str:
        """Build prompt for metadata extraction from header"""
        return f"""Header text:
{header_text}

Extract exam metadata in JSON format."""
