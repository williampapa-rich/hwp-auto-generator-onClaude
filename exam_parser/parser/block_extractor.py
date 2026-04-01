import fitz
from dataclasses import dataclass
from typing import List


@dataclass
class Block:
    """Normalized text block from PDF"""
    block_id: int
    block_type: int  # 0=text, 1=image
    text: str
    bbox: tuple  # (x0, y0, x1, y1)
    page_num: int

    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    def area(self) -> float:
        return self.width() * self.height()


class BlockExtractor:
    """Extract text blocks from PDF page"""

    def __init__(self, page: fitz.Page):
        self.page = page

    def extract_blocks(self) -> List[Block]:
        """Extract all text blocks from page"""
        blocks = []

        # Apply derotation if needed
        mat = self.page.derotation_matrix

        raw_dict = self.page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for block_num, block in enumerate(raw_dict.get("blocks", [])):
            block_type = block.get("type")

            if block_type == 0:  # Text block
                text = "".join(line["spans"][0]["text"]
                              for line in block.get("lines", [])
                              if line.get("spans"))
                text = text.strip()

                if text:  # Only add non-empty blocks
                    bbox = block.get("bbox")
                    blocks.append(Block(
                        block_id=block_num,
                        block_type=0,
                        text=text,
                        bbox=bbox,
                        page_num=self.page.number
                    ))

            elif block_type == 1:  # Image block
                bbox = block.get("bbox")
                blocks.append(Block(
                    block_id=block_num,
                    block_type=1,
                    text="",
                    bbox=bbox,
                    page_num=self.page.number
                ))

        return blocks
