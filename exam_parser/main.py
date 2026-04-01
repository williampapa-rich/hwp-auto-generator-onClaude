#!/usr/bin/env python3
"""
Main pipeline for exam paper PDF parsing.
Orchestrates: PDF loading → block extraction → column splitting →
reading order → question grouping → LLM extraction → JSON output
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exam_parser.parser.pdf_loader import PDFLoader
from exam_parser.parser.block_extractor import BlockExtractor
from exam_parser.parser.image_extractor import ImageExtractor
from exam_parser.parser.box_detector import BoxDetector
from exam_parser.layout.column_splitter import ColumnSplitter
from exam_parser.layout.reading_order import ReadingOrderManager
from exam_parser.layout.question_grouper import QuestionGrouper, QuestionGroup
from exam_parser.llm.prompt_builder import PromptBuilder, MetadataPromptBuilder
from exam_parser.llm.gemini_client import GeminiClient
from exam_parser.llm.schema_validator import SchemaValidator
from exam_parser.models.schema import ExamPaper, ExamMetadata, Question, StimulusItem
from exam_parser.output.writer import OutputWriter
from exam_parser.config import IMAGE_DIR, OUTPUT_DIR


class ExamPaperParser:
    """Main orchestrator for exam paper parsing"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.loader = PDFLoader(pdf_path)
        self.llm_client = GeminiClient()
        self.output_writer = OutputWriter(OUTPUT_DIR)

    def parse(self) -> Optional[ExamPaper]:
        """Parse entire exam paper"""
        print(f"📄 Loading PDF: {self.pdf_path}")
        total_pages = self.loader.get_page_count()
        print(f"📊 Total pages: {total_pages}")

        # Extract metadata from first page
        print("\n🔍 Extracting metadata...")
        metadata = self._extract_metadata()

        # Extract questions from all pages
        print("\n📝 Extracting questions...")
        questions = self._extract_all_questions()

        exam = ExamPaper(
            metadata=metadata,
            questions=questions
        )

        print(f"\n✅ Parsed {len(questions)} questions")
        return exam

    def _extract_metadata(self) -> ExamMetadata:
        """Extract metadata from first page header"""
        try:
            page = self.loader.get_page(0)
            extractor = BlockExtractor(page)
            blocks = extractor.extract_blocks()

            # Get header blocks (top 60px)
            header_blocks = [b for b in blocks if b.bbox[1] < 60]
            header_text = '\n'.join(b.text for b in header_blocks)

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

    def _extract_all_questions(self) -> list[Question]:
        """Extract questions from all pages"""
        all_classified_blocks = []

        # Process each page
        for page_num, page in self.loader.iterate_pages():
            print(f"  Processing page {page_num + 1}...", end=" ")

            # Extract blocks
            extractor = BlockExtractor(page)
            blocks = extractor.extract_blocks()

            # Classify boxes
            detector = BoxDetector(page)
            classified = detector.classify_blocks(blocks)
            all_classified_blocks.extend(classified)

            print("✓")

        # Group blocks by question
        grouper = QuestionGrouper()
        question_groups = grouper.group_blocks(all_classified_blocks)

        # Extract questions via LLM
        questions = []
        for group in question_groups:
            if group.q_number == "0":
                continue  # Skip preamble

            question = self._extract_question(group)
            if question:
                questions.append(question)

        return questions

    def _extract_question(self, group: QuestionGroup) -> Optional[Question]:
        """Extract single question via LLM"""
        try:
            # Build prompt
            user_prompt = PromptBuilder.build_user_prompt(group.q_number, group.blocks)

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
        print("Usage: python main.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    parser = ExamPaperParser(pdf_path)
    exam = parser.parse()

    if exam:
        parser.save_results(exam)
        print(f"\n🎉 Success! Results saved to {OUTPUT_DIR}")
    else:
        print("\n❌ Parsing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
