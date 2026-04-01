import json
import time
from typing import Optional, Dict, Any
import google.generativeai as genai
from exam_parser.config import GEMINI_API_KEY, MAX_RETRIES, LLM_TIMEOUT


class GeminiClient:
    """Gemini API client for question/metadata extraction"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-pro")

    def extract_question(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Extract question data with retries.

        Returns:
            Parsed JSON response, or None if all retries fail
        """
        for attempt in range(MAX_RETRIES):
            try:
                response = self.model.generate_content(
                    [system_prompt, user_prompt],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,  # Low temperature for consistent JSON
                        max_output_tokens=2000,
                    ),
                    timeout=LLM_TIMEOUT
                )

                response_text = response.text.strip()

                # Remove markdown code fence if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                response_text = response_text.strip()

                # Parse JSON
                parsed = json.loads(response_text)
                return parsed

            except json.JSONDecodeError as e:
                if attempt == MAX_RETRIES - 1:
                    print(f"Failed to parse JSON after {MAX_RETRIES} retries: {e}")
                    return None
                time.sleep(0.5)
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    print(f"Error calling Gemini API: {e}")
                    return None
                time.sleep(1)

        return None

    def extract_metadata(self, system_prompt: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Extract metadata with same retry logic"""
        return self.extract_question(system_prompt, prompt)
