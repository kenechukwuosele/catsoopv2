from typing import Optional, List
from pydantic import BaseModel


# --- Course / Week ---

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
    time_limit_minutes: int = 0


class WeekEdit(BaseModel):
    title: str = ""
    content: str = ""
    lecture_title: str = ""
    lecture_content: str = ""
    practice_problems: List[dict] = []
    due_date: str = ""
    release_date: str = ""
    grace_period: int = 0
    lateness_penalty: float = 0.0
    allow_late: bool = True
    time_limit_minutes: int = 0


# --- Live File ---

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


# --- Engagement ---

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
    eyeAspectRatio: Optional[float] = None
    mouthOpenRatio: Optional[float] = None
    smileScore: Optional[float] = None
    headYaw: Optional[float] = None
    headPitch: Optional[float] = None
    headRoll: Optional[float] = None
    affectState: Optional[str] = None


# --- RAG ---

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
    collections: dict
