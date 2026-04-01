from typing import List, Tuple
from dataclasses import dataclass
from exam_parser.parser.block_extractor import Block
from exam_parser.config import DEAD_ZONE


@dataclass
class Column:
    """Column information"""
    name: str  # "left", "right", "spanning"
    blocks: List[Block]


class ColumnSplitter:
    """Dynamically detect column boundaries"""

    def __init__(self, blocks: List[Block], page_width: float):
        self.blocks = blocks
        self.page_width = page_width

    def split_columns(self) -> Tuple[float, float]:
        """
        Detect column boundaries.

        Returns:
            (left_boundary, right_boundary) - x-coordinates where columns start/end
        """

        # Analyze x-coordinates in middle 1/3 of page
        middle_third_start = self.page_width / 3
        middle_third_end = 2 * self.page_width / 3

        left_x1_values = []  # Right edges of left column blocks
        right_x0_values = []  # Left edges of right column blocks

        for block in self.blocks:
            x0, y0, x1, y1 = block.bbox

            # Check if block's y-range overlaps with middle third horizontally
            if middle_third_start <= y0 < middle_third_end:
                if x1 < self.page_width / 2:
                    left_x1_values.append(x1)
                elif x0 > self.page_width / 2:
                    right_x0_values.append(x0)

        if not left_x1_values or not right_x0_values:
            # Fallback: simple middle split
            return self.page_width / 2, self.page_width / 2

        # Find max x1 on left, min x0 on right
        left_max = max(left_x1_values)
        right_min = min(right_x0_values)

        # Boundary is midpoint
        boundary = (left_max + right_min) / 2

        return boundary, boundary

    def classify_blocks(self, boundary: float) -> tuple[List[Block], List[Block], List[Block]]:
        """
        Classify blocks as left, right, or spanning.

        Args:
            boundary: Column boundary x-coordinate

        Returns:
            (left_blocks, right_blocks, spanning_blocks)
        """
        left = []
        right = []
        spanning = []

        for block in self.blocks:
            x0, y0, x1, y1 = block.bbox

            # Dead zone: blocks too close to boundary are ambiguous
            if boundary - DEAD_ZONE < x1 < boundary + DEAD_ZONE:
                spanning.append(block)
            elif boundary - DEAD_ZONE < x0 < boundary + DEAD_ZONE:
                spanning.append(block)
            elif x1 < boundary:
                left.append(block)
            else:
                right.append(block)

        return left, right, spanning
