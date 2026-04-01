import re
from typing import List, Tuple
from dataclasses import dataclass
from exam_parser.parser.block_extractor import Block
from exam_parser.parser.box_detector import BlockWithBoxType


@dataclass
class QuestionGroup:
    """Group of blocks belonging to single question"""
    q_number: str
    blocks: List[BlockWithBoxType]
    start_page: int
    end_page: int


class QuestionGrouper:
    """Group blocks by question number"""

    # Regex to match question numbers: 1, 1), 1., (1), [1], etc.
    Q_NUMBER_PATTERN = re.compile(r'^[\[\(]?(\d{1,2})[\]\)\.]?\s')

    # Sub-question patterns: 가), 나), (A), (B), ①, ②, etc.
    SUB_Q_PATTERN = re.compile(r'^[가-힣a-zA-Z①-⑤①-⑤]\)')

    def __init__(self):
        self.current_q_num = None

    def group_blocks(self, classified_blocks: List[BlockWithBoxType]) -> List[QuestionGroup]:
        """
        Group blocks by question number.
        Handles questions spanning multiple pages.
        """
        groups = []
        current_group = None

        for block_with_type in classified_blocks:
            block = block_with_type.block
            text = block.text

            # Try to detect question number
            match = self.Q_NUMBER_PATTERN.match(text)

            if match:
                q_number = match.group(1)

                # Save previous group
                if current_group is not None:
                    groups.append(current_group)

                # Start new group
                current_group = QuestionGroup(
                    q_number=q_number,
                    blocks=[block_with_type],
                    start_page=block.page_num,
                    end_page=block.page_num
                )
                self.current_q_num = q_number
            else:
                # Add to current group
                if current_group is None:
                    # First block before any question number detected
                    current_group = QuestionGroup(
                        q_number="0",
                        blocks=[block_with_type],
                        start_page=block.page_num,
                        end_page=block.page_num
                    )
                else:
                    current_group.blocks.append(block_with_type)
                    current_group.end_page = max(current_group.end_page, block.page_num)

        # Add last group
        if current_group is not None:
            groups.append(current_group)

        return groups

    @staticmethod
    def extract_sub_questions(text: str) -> List[str]:
        """Extract sub-question markers from text"""
        sub_questions = []
        for line in text.split('\n'):
            if re.match(QuestionGrouper.SUB_Q_PATTERN, line.strip()):
                sub_questions.append(line.strip()[:2])
        return sub_questions
