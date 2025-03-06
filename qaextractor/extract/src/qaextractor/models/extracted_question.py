from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Image(BaseModel):
    """Model for an image associated with a question"""
    label: str
    description: Optional[str] = None
    url: str

class ContextMaterial(BaseModel):
    """Model for context materials (texts, references) associated with a question"""
    label: str
    content: str
    description: Optional[str] = None
    type: str = "text"  

class Difficulty(BaseModel):
    """Model for question difficulty assessment"""
    level: str  
    justification: Optional[str] = None

class Question(BaseModel):
    """Model for an extracted question"""
    question_id: str
    question_number: int
    question_text: str
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    context_materials: Optional[List[ContextMaterial]] = None
    images: Optional[List[Image]] = None
    marks: Optional[int] = None

class ExtractedQuestions(BaseModel):
    """Model for a document in the extracted-questions collection"""
    exam_id: str
    paper_meta: Dict[str, Any]
    questions: List[Question]
    total_questions: int
    extraction_date: datetime = Field(default_factory=datetime.now) 