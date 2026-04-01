#!/usr/bin/env python3
"""
Main pipeline for scanned exam paper PDF parsing with OCR.
Orchestrates: PDF loading → OCR extraction → layout analysis →
question grouping → LLM extraction → JSON output
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exam_parser.parser.pdf_loader import PDFLoader
from exam_parser.parser.ocr_extractor import OCRExtractor, OCRBlock
from exam_parser.layout.column_splitter import ColumnSplitter
from exam_parser.layout.reading_order import ReadingOrderManager
from exam_parser.layout.question_grouper import QuestionGrouper
from exam_parser.llm.prompt_builder import PromptBuilder, MetadataPromptBuilder
from exam_parser.llm.gemini_client import GeminiClient
from exam_parser.llm.schema_validator import SchemaValidator
from exam_parser.models.schema import ExamPaper, ExamMetadata, Question, StimulusItem
from exam_parser.output.writer import OutputWriter
from exam_parser.config import IMAGE_DIR, OUTPUT_DIR


class OCRBlock:
    """Wrapper to match block_extractor.Block interface"""
    def __init__(self, ocr_block, page_num: int):
        self.block_id = hash(ocr_block.text)
        self.block_type = 0  # Text
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


class OCRExamPaperParser:
    """Scanned PDF parser using OCR"""

    def __init__(self, pdf_path: str, use_gemini: bool = True):
        self.pdf_path = pdf_path
        self.loader = PDFLoader(pdf_path)
        self.ocr_extractor = OCRExtractor()
        self.use_gemini = use_gemini
        self.llm_client = GeminiClient() if use_gemini else None
        self.output_writer = OutputWriter(OUTPUT_DIR)

    def parse(self) -> Optional[ExamPaper]:
        """Parse entire exam paper using OCR"""
        print(f"📄 Loading PDF: {self.pdf_path}")
        total_pages = self.loader.get_page_count()
        print(f"📊 Total pages: {total_pages}")

        # Extract text via OCR from all pages
        print("\n🤖 Extracting text via OCR...")
        all_ocr_blocks = self._extract_ocr_text()

        # Extract metadata from first page
        print("\n🔍 Extracting metadata...")
        metadata = self._extract_metadata(all_ocr_blocks.get(0, []))

        # Extract questions from all pages
        print("\n📝 Extracting questions...")
        questions = self._extract_all_questions(all_ocr_blocks)

        exam = ExamPaper(
            metadata=metadata,
            questions=questions
        )

        print(f"\n✅ Parsed {len(questions)} questions")
        return exam

    def _extract_ocr_text(self) -> dict:
        """Extract text from all pages using OCR"""
        all_blocks = {}

        for page_num, page in self.loader.iterate_pages():
            ocr_blocks = self.ocr_extractor.extract_from_page(page)

            # Filter low confidence
            ocr_blocks = self.ocr_extractor.filter_by_confidence(ocr_blocks, threshold=0.4)

            # Merge nearby blocks
            ocr_blocks = self.ocr_extractor.merge_nearby_blocks(ocr_blocks, threshold=15.0)

            # Convert to Block format
            blocks = [OCRBlock(ocr_b, page_num) for ocr_b in ocr_blocks]
            all_blocks[page_num] = blocks

        return all_blocks

    def _extract_metadata(self, header_blocks: list) -> ExamMetadata:
        """Extract metadata from header blocks"""
        if not header_blocks or not self.use_gemini:
            return ExamMetadata(total_pages=self.loader.get_page_count())

        try:
            # Collect header text
            header_text = '\n'.join(b.text for b in header_blocks[:10])

            if not header_text.strip():
                return ExamMetadata(total_pages=self.loader.get_page_count())

            # Call LLM for metadata extraction
            prompt = MetadataPromptBuilder.build_metadata_prompt(header_text)
            result = self.llm_client.extract_metadata(
                MetadataPromptBuilder.METADATA_SYSTEM_PROMPT,
                prompt
            )

            if result:
                metadata = SchemaValidator.validate_metadata(result)
                if metadata:
                    metadata.total_pages = self.loader.get_page_count()
                    return metadata

        except Exception as e:
            print(f"⚠️  Error extracting metadata: {e}")

        return ExamMetadata(total_pages=self.loader.get_page_count())

    def _extract_all_questions(self, all_ocr_blocks: dict) -> list[Question]:
        """Extract questions from all pages"""
        all_blocks = []

        # Flatten and order blocks from all pages
        for page_num in sorted(all_ocr_blocks.keys()):
            blocks = all_ocr_blocks[page_num]
            all_blocks.extend(blocks)

        # Group blocks by question
        grouper = QuestionGrouper()

        # Convert to BlockWithBoxType format (simplified)
        from exam_parser.parser.box_detector import BlockWithBoxType
        classified_blocks = [
            BlockWithBoxType(b, "text") for b in all_blocks
        ]

        question_groups = grouper.group_blocks(classified_blocks)

        # Extract questions via LLM
        questions = []
        for group in question_groups:
            if group.q_number == "0":
                continue  # Skip preamble

            if not self.use_gemini:
                # Without LLM, create basic question object
                question = Question(
                    q_number=group.q_number,
                    q_type="multiple_choice",  # Default type
                    stimulus=[
                        StimulusItem(type="text", content=b.block.text)
                        for b in group.blocks
                    ]
                )
                questions.append(question)
            else:
                question = self._extract_question(group)
                if question:
                    questions.append(question)

        return questions

    def _extract_question(self, group) -> Optional[Question]:
        """Extract single question via LLM"""
        try:
            # Build prompt
            user_prompt = PromptBuilder.build_user_prompt(
                group.q_number,
                group.blocks
            )

            # Call LLM
            result = self.llm_client.extract_question(
                PromptBuilder.SYSTEM_PROMPT,
                user_prompt
            )

            if not result:
                print(f"    ⚠️  Q{group.q_number}: LLM extraction failed")
                return None

            # Validate
            question = SchemaValidator.validate_question(result)
            if not question:
                print(f"    ⚠️  Q{group.q_number}: Validation failed")
                return None

            return question

        except Exception as e:
            print(f"    ⚠️  Q{group.q_number}: {e}")
            return None

    def save_results(self, exam: ExamPaper) -> None:
        """Save exam paper to JSON"""
        self.output_writer.write_exam(exam)


def main():
    """Entry point"""
    if len(sys.argv) < 2:
        print("Usage: python main_ocr.py <pdf_path> [--no-llm]")
        print("  --no-llm: Extract structure without LLM")
        sys.exit(1)

    pdf_path = sys.argv[1]
    use_llm = "--no-llm" not in sys.argv

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    parser = OCRExamPaperParser(pdf_path, use_gemini=use_llm)
    exam = parser.parse()

    if exam:
        parser.save_results(exam)
        print(f"\n🎉 Success! Results saved to {OUTPUT_DIR}")
    else:
        print("\n❌ Parsing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
