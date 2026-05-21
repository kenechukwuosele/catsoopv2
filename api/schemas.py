from typing import Optional, List, Union
from pydantic import BaseModel


# --- Quiz / Attempt Schemas ---
class QuestionResponse(BaseModel):
    id: int
    text: str
    qtype: str
    options: List[str] | None
    correct_answers: List[Union[str, int]]
    username: str
    created_at: str
    course: str
    week: str


class EngagementMetrics(BaseModel):
    secondsSpent: int
    clickCount: int
    exitTime: str
    hintCount: int = 0


class AttemptSubmission(BaseModel):
    username: str
    score: int
    total: int
    course: str
    week: str
    results: List[dict]
    metrics: EngagementMetrics
    attemptSessionId: str | None = None


# --- Hint Schemas ---
class QuestionWithHints(BaseModel):
    text: str
    type: str
    options: List[str] = []
    correct_answers: List[Union[str, int]]
    hints: List[str] = []


class BulkImportRequest(BaseModel):
    course: str
    week: str
    questions: List[QuestionWithHints]


class HintCreate(BaseModel):
    question_id: int
    hints: List[str]


class HintGenerate(BaseModel):
    question_id: int
    question_text: str


# --- Course / Week Schemas ---
class CourseCreate(BaseModel):
    name: str
    number: str = ""
    description: str = ""
    content: str = ""
    icon: str = ""


class CourseEdit(BaseModel):
    number: str = ""
    description: str = ""
    content: str = ""
    icon: str = ""


class WeekCreate(BaseModel):
    week_id: str
    title: str
    content: str = ""
    lecture_title: str = ""
    lecture_content: str = ""
    practice_problems: List[dict] = []
    due_date: str = ""
    release_date: str = ""
    grace_period: int = 0
    lateness_penalty: float = 0.0
    allow_late: bool = True


class WeekEdit(BaseModel):
    title: str = ""
    content: str = ""
    lecture_title: str = ""
    lecture_content: str = ""
    practice_problems: list[dict] = []
    due_date: str = ""
    release_date: str = ""
    grace_period: int = 0
    lateness_penalty: float = 0.0
    allow_late: bool = True


# --- Live File Schemas ---
class LiveFileResponse(BaseModel):
    course: str
    week: str
    filename: str
    content_type: str
    uploaded_at: str


class LiveFileUpload(BaseModel):
    course: str
    week: str
    filename: str
    content_type: str
    data_base64: str


class EngagementSampleCreate(BaseModel):
    attemptSessionId: str
    username: str
    course: str
    week: str
    timestamp: str
    facePresent: bool
    gazeCentered: bool
    headPose: str
    inactivitySeconds: int
    engagementScore: int
    focusState: str
    clickCount: int = 0
    typingCount: int = 0
    eyeAspectRatio: float | None = None
    mouthOpenRatio: float | None = None
    smileScore: float | None = None
    headYaw: float | None = None
    headPitch: float | None = None
    headRoll: float | None = None
    affectState: str | None = None


# --- RAG Schemas ---
class RAGIngestRequest(BaseModel):
    course: str
    week: str


class RAGGenerateHint(BaseModel):
    question_text: str
    hint_level: int = 1
    course: str = ""
    week: str = ""


class RAGStatusResponse(BaseModel):
    embed_model: str
    chromadb_available: bool
    collections: dict[str, int]
