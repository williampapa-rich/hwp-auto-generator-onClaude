import fitz
from pathlib import Path
from PIL import Image
import io
from typing import Optional


class ImageExtractor:
    """Extract and save images from PDF"""

    def __init__(self, page: fitz.Page, output_dir: Path):
        self.page = page
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def extract_image(self, block_id: int, min_area: float = 5000) -> Optional[str]:
        """
        Extract image block and save to disk.

        Args:
            block_id: Block ID from extracted blocks
            min_area: Minimum area in px² (ignore decorative images)

        Returns:
            Relative path to saved image, or None if too small
        """
        try:
            # Get all images on page
            images = self.page.get_images()

            # Find image by block_id (xref)
            for img_index, img_info in enumerate(images):
                xref = img_info[0]

                # Extract image data
                pix = fitz.Pixmap(self.page.parent, xref)

                # Check area
                area = pix.width * pix.height
                if area < min_area:
                    return None

                # Convert to PNG
                if pix.n - pix.alpha < 4:  # Gray or RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                filename = f"page_{self.page.number:03d}_img_{img_index:02d}.png"
                filepath = self.output_dir / filename

                pix.save(str(filepath))
                pix = None  # Release memory

                return f"images/{filename}"

        except Exception as e:
            print(f"Error extracting image from block {block_id}: {e}")

        return None

    def extract_all_images(self, min_area: float = 5000) -> dict:
        """Extract all images from page"""
        images_map = {}

        try:
            images = self.page.get_images()
            for img_index, img_info in enumerate(images):
                xref = img_info[0]
                pix = fitz.Pixmap(self.page.parent, xref)

                area = pix.width * pix.height
                if area < min_area:
                    continue

                if pix.n - pix.alpha < 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                filename = f"page_{self.page.number:03d}_img_{img_index:02d}.png"
                filepath = self.output_dir / filename
                pix.save(str(filepath))

                images_map[xref] = f"images/{filename}"
                pix = None

        except Exception as e:
            print(f"Error extracting images from page {self.page.number}: {e}")

        return images_map
