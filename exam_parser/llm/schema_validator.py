import json
from typing import Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel, ValidationError
from exam_parser.models.schema import Question, ExamMetadata

T = TypeVar('T', bound=BaseModel)


class SchemaValidator:
    """Validate LLM responses against Pydantic schemas"""

    @staticmethod
    def validate_question(data: Dict[str, Any]) -> Optional[Question]:
        """
        Validate question data with lenient mode.

        Returns validated Question or None if invalid
        """
        try:
            # Fill defaults for optional fields
            if "q_type" not in data:
                data["q_type"] = "multiple_choice"
            if "stimulus" not in data:
                data["stimulus"] = []
            if "choices" not in data:
                data["choices"] = []

            question = Question(**data)
            return question

        except ValidationError as e:
            print(f"Question validation failed: {e}")
            return None

    @staticmethod
    def validate_metadata(data: Dict[str, Any]) -> Optional[ExamMetadata]:
        """Validate metadata"""
        try:
            metadata = ExamMetadata(**data)
            return metadata

        except ValidationError as e:
            print(f"Metadata validation failed: {e}")
            return None

    @staticmethod
    def validate_schema(data: Dict[str, Any], schema: Type[T]) -> Optional[T]:
        """Generic schema validation"""
        try:
            return schema(**data)
        except ValidationError as e:
            print(f"Schema validation failed: {e}")
            return None
