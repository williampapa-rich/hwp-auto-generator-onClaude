#!/usr/bin/env python3
"""
Main pipeline for exam paper PDF parsing using Claude Vision API.
Direct image analysis without OCR/layout processing.
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exam_parser.parser.pdf_loader import PDFLoader
from exam_parser.parser.vision_extractor import VisionExtractor
from exam_parser.llm.schema_validator import SchemaValidator
from exam_parser.models.schema import ExamPaper, ExamMetadata, Question, StimulusItem
from exam_parser.output.writer import OutputWriter
from exam_parser.config import OUTPUT_DIR


class VisionExamPaperParser:
    """Exam paper parser using Claude Vision API"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.loader = PDFLoader(pdf_path)
        self.vision_extractor = VisionExtractor()
        self.output_writer = OutputWriter(OUTPUT_DIR)

    def parse(self) -> Optional[ExamPaper]:
        """Parse entire exam paper using Vision API"""
        print(f"📄 Loading PDF: {self.pdf_path}")
        total_pages = self.loader.get_page_count()
        print(f"📊 Total pages: {total_pages}")

        # Extract using Claude Vision
        print("\n🔍 Analyzing with Claude Vision...")
        extracted = self.vision_extractor.extract_from_pdf(self.pdf_path)

        # Parse metadata
        metadata_dict = extracted.get("metadata", {})
        metadata = SchemaValidator.validate_metadata(metadata_dict)
        if metadata:
            metadata.total_pages = total_pages
        else:
            metadata = ExamMetadata(total_pages=total_pages)

        # Parse questions
        print("\n📝 Validating questions...")
        questions = []
        for q_dict in extracted.get("questions", []):
            try:
                question = SchemaValidator.validate_question(q_dict)
                if question:
                    questions.append(question)
            except Exception as e:
                print(f"  ⚠️  Error validating Q{q_dict.get('q_number')}: {e}")

        exam = ExamPaper(
            metadata=metadata,
            questions=questions
        )

        print(f"\n✅ Parsed {len(questions)} questions")
        return exam

    def save_results(self, exam: ExamPaper) -> None:
        """Save exam paper to JSON"""
        self.output_writer.write_exam(exam)


def main():
    """Entry point"""
    if len(sys.argv) < 2:
        print("Usage: python main_vision.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    parser = VisionExamPaperParser(pdf_path)
    exam = parser.parse()

    if exam:
        parser.save_results(exam)
        print(f"\n🎉 Success! Results saved to {OUTPUT_DIR}")
    else:
        print("\n❌ Parsing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
