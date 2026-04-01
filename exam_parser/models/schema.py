from typing import List, Optional, Literal
from pydantic import BaseModel, Field

StimulusType = Literal["text", "text_box", "condition_box", "image"]
QuestionType = Literal["multiple_choice", "subjective"]


class StimulusItem(BaseModel):
    """Individual stimulus component (text, box, image)"""
    type: StimulusType
    content: str  # text content or image path


class Question(BaseModel):
    """Single exam question"""
    q_number: str  # "1", "1-1", "1가"
    q_type: QuestionType
    points: Optional[float] = None
    instruction: Optional[str] = None  # 지시문 (다음을 읽고...)
    stimulus: List[StimulusItem] = Field(default_factory=list)
    choices: List[str] = Field(default_factory=list)  # ["① ...", "② ..."]
    sub_questions: List[str] = Field(default_factory=list)  # ["가)", "나)"]


class ExamMetadata(BaseModel):
    """Exam paper metadata"""
    school_name: Optional[str] = None
    year: Optional[int] = None
    semester: Optional[int] = None  # 1 or 2
    exam_type: Optional[str] = None  # "중간", "기말", "수시"
    grade: Optional[int] = None
    subject: Optional[str] = None  # "영어", "수학"
    total_pages: int = 0


class ExamPaper(BaseModel):
    """Complete exam paper structure"""
    metadata: ExamMetadata
    questions: List[Question]
