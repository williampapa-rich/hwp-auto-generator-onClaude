import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
IMAGE_DIR = PROJECT_ROOT / "images"

# Create directories if they don't exist
IMAGE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# API Keys (from environment)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# PDF Processing
HEADER_THRESHOLD = 60  # px
FOOTER_THRESHOLD = 50  # px
DEAD_ZONE = 15  # px for column boundary ambiguity
MIN_IMAGE_AREA = 5000  # px² - ignore decorative images

# LLM
MAX_RETRIES = 3
LLM_TIMEOUT = 30  # seconds
