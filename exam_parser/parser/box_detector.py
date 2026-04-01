import fitz
from dataclasses import dataclass
from typing import List, Literal
from .block_extractor import Block

BoxType = Literal["text_box", "condition_box", "text"]


@dataclass
class BlockWithBoxType:
    """Block with box classification"""
    block: Block
    box_type: BoxType


class BoxDetector:
    """Detect and classify text boxes (white vs. filled)"""

    def __init__(self, page: fitz.Page):
        self.page = page
        self.drawings = page.get_drawings()

    def classify_blocks(self, blocks: List[Block]) -> List[BlockWithBoxType]:
        """Classify each block as text_box, condition_box, or text"""
        classified = []

        for block in blocks:
            if block.block_type == 1:  # Image
                classified.append(BlockWithBoxType(block, "text"))
                continue

            box_type = self._detect_box_type(block)
            classified.append(BlockWithBoxType(block, box_type))

        return classified

    def _detect_box_type(self, block: Block) -> BoxType:
        """Determine if block is in a text_box, condition_box, or plain text"""

        # Find rectangles overlapping this block
        for drawing in self.drawings:
            if drawing.type != "re":  # Only rectangles
                continue

            rect = drawing.rect
            if self._boxes_overlap(block.bbox, rect):
                # Check fill color
                if drawing.fill is not None:
                    fill_color = drawing.fill
                    # Non-white fill (grayscale/color) → condition_box
                    if self._is_non_white(fill_color):
                        return "condition_box"
                    else:
                        return "text_box"
                else:
                    # No fill but has stroke → text_box
                    return "text_box"

        return "text"

    @staticmethod
    def _boxes_overlap(bbox1: tuple, bbox2: tuple, threshold: float = 0.5) -> bool:
        """Check if two bboxes overlap significantly"""
        x0_1, y0_1, x1_1, y1_1 = bbox1
        x0_2, y0_2, x1_2, y1_2 = bbox2

        # Calculate intersection
        x0 = max(x0_1, x0_2)
        y0 = max(y0_1, y0_2)
        x1 = min(x1_1, x1_2)
        y1 = min(y1_1, y1_2)

        if x1 <= x0 or y1 <= y0:
            return False

        intersection_area = (x1 - x0) * (y1 - y0)
        bbox1_area = (x1_1 - x0_1) * (y1_1 - y0_1)

        return intersection_area / bbox1_area > threshold

    @staticmethod
    def _is_non_white(fill_color: tuple) -> bool:
        """Check if color is non-white (grayscale/colored)"""
        if isinstance(fill_color, (list, tuple)):
            if len(fill_color) == 1:  # Grayscale
                return fill_color[0] < 0.95  # Threshold for "not white"
            elif len(fill_color) == 3:  # RGB
                avg = sum(fill_color) / 3
                return avg < 0.95
        return False
