from typing import List
from exam_parser.parser.block_extractor import Block
from exam_parser.parser.box_detector import BlockWithBoxType
from exam_parser.config import HEADER_THRESHOLD, FOOTER_THRESHOLD


class ReadingOrderManager:
    """Determine correct reading order across columns"""

    def __init__(self, page_height: float):
        self.page_height = page_height

    def order_blocks(self,
                     left_blocks: List[Block],
                     right_blocks: List[Block],
                     spanning_blocks: List[Block]) -> List[Block]:
        """
        Order blocks: header → left → spanning → right → footer

        Within left/right columns, sort by y0 (top-to-bottom)
        """

        all_blocks = left_blocks + right_blocks + spanning_blocks
        result = []

        # 1. Header blocks (y0 < HEADER_THRESHOLD)
        headers = [b for b in all_blocks if b.bbox[1] < HEADER_THRESHOLD]
        result.extend(sorted(headers, key=lambda b: b.bbox[1]))

        # 2. Footer blocks (y0 > page_height - FOOTER_THRESHOLD)
        footers = [b for b in all_blocks
                   if b.bbox[1] > self.page_height - FOOTER_THRESHOLD]
        footer_list = sorted(footers, key=lambda b: b.bbox[1])

        # 3. Main content (not header/footer)
        main_content = [b for b in all_blocks
                        if HEADER_THRESHOLD <= b.bbox[1] <= self.page_height - FOOTER_THRESHOLD]

        # Separate left/right/spanning from main content
        left_main = [b for b in main_content if b in left_blocks]
        right_main = [b for b in main_content if b in right_blocks]
        spanning_main = [b for b in main_content if b in spanning_blocks]

        # Sort by y0
        left_main.sort(key=lambda b: b.bbox[1])
        right_main.sort(key=lambda b: b.bbox[1])
        spanning_main.sort(key=lambda b: b.bbox[1])

        # Interleave left/right by y-position
        left_idx, right_idx, spanning_idx = 0, 0, 0
        while left_idx < len(left_main) or right_idx < len(right_main) or spanning_idx < len(spanning_main):
            # Next spanning block
            if spanning_idx < len(spanning_main) and (
                (left_idx >= len(left_main) or spanning_main[spanning_idx].bbox[1] < left_main[left_idx].bbox[1])
                and (right_idx >= len(right_main) or spanning_main[spanning_idx].bbox[1] < right_main[right_idx].bbox[1])
            ):
                result.append(spanning_main[spanning_idx])
                spanning_idx += 1
            # Next left block
            elif left_idx < len(left_main) and (
                right_idx >= len(right_main) or left_main[left_idx].bbox[1] <= right_main[right_idx].bbox[1]
            ):
                result.append(left_main[left_idx])
                left_idx += 1
            # Next right block
            elif right_idx < len(right_main):
                result.append(right_main[right_idx])
                right_idx += 1

        # 4. Add footers
        result.extend(footer_list)

        return result
