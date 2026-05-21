from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Float, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base  

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    role = Column(String)  # "student" or "instructor"
    
    # Relationship: One user has many quiz attempts
    attempts = relationship("Attempt", back_populates="user")

class Lecture(Base):
    __tablename__ = "lectures"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    course = Column(String)
    week = Column(String)

    # Relationship: One lecture has many questions
    questions = relationship("Question", back_populates="lecture")


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    question_text = Column(String, nullable=False)
    question_type = Column(String, nullable=False)  # 'short-answer' or 'multiple-choice'
    options = Column(JSON, nullable=True)           # Only for multiple-choice questions
    correct_answers = Column(JSON, nullable=False)
    username = Column(String, nullable=False)  
    course = Column(String, nullable=False)  
    week = Column(String, nullable=False)  
    created_at = Column(String, nullable=False)     # ISO format string
    lecture = relationship("Lecture", back_populates="questions")

class Attempt(Base):
    __tablename__ = 'attempts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String, nullable=False)
    course = Column(String, nullable=False)
    week = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    submitted_at = Column(String, nullable=False)
    attempt_session_id = Column(String, nullable=True)
    # Corrected: results is now a JSON column, not a relationship
    results = Column(JSON, nullable=False)
    seconds_spent = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    hint_count = Column(Integer, default=0)
    user = relationship("User", back_populates="attempts")
    
class Hint(Base):
    __tablename__ = "hints"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, index=True)
    hint_number = Column(Integer)
    hint_text = Column(String)

class LiveFile(Base):
    __tablename__ = "live_files"
    __table_args__ = (UniqueConstraint("course", "week", name="uq_live_files_course_week"),)
    id = Column(Integer, primary_key=True, index=True)
    course = Column(String, index=True)
    week = Column(String, index=True)
    filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    uploaded_at = Column(String, nullable=False)


class ContentChunk(Base):
    __tablename__ = "content_chunks"
    id = Column(Integer, primary_key=True, index=True)
    course = Column(String, index=True)
    week = Column(String, index=True)
    source_file = Column(String)
    chunk_index = Column(Integer)
    chunk_text = Column(Text)
    created_at = Column(String, default=datetime.now().isoformat)


class EngagementSample(Base):
    __tablename__ = "engagement_samples"
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, nullable=True)
    attempt_session_id = Column(String, index=True, nullable=False)
    username = Column(String, nullable=False)
    course = Column(String, nullable=False)
    week = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    face_present = Column(Integer, default=0)
    gaze_centered = Column(Integer, default=0)
    head_pose = Column(String, default="center")
    inactivity_seconds = Column(Integer, default=0)
    engagement_score = Column(Integer, default=0)
    focus_state = Column(String, default="Low")
    click_count = Column(Integer, default=0)
    typing_count = Column(Integer, default=0)
    # Enhanced affect fields
    eye_aspect_ratio = Column(Float, nullable=True)
    mouth_open_ratio = Column(Float, nullable=True)
    smile_score = Column(Float, nullable=True)
    head_yaw = Column(Float, nullable=True)
    head_pitch = Column(Float, nullable=True)
    head_roll = Column(Float, nullable=True)
    affect_state = Column(String, nullable=True)
