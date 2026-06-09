from sqlalchemy import Column, Integer, String, Float, Text, UniqueConstraint, Boolean
from datetime import datetime
from .database import Base


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
    eye_aspect_ratio = Column(Float, nullable=True)
    mouth_open_ratio = Column(Float, nullable=True)
    smile_score = Column(Float, nullable=True)
    head_yaw = Column(Float, nullable=True)
    head_pitch = Column(Float, nullable=True)
    head_roll = Column(Float, nullable=True)
    affect_state = Column(String, nullable=True)


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (UniqueConstraint("username", "course", name="uq_profile_username_course"),)
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    course = Column(String, nullable=False)
    xp = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    last_active = Column(String, nullable=True)


class Badge(Base):
    __tablename__ = "badges"
    __table_args__ = (UniqueConstraint("username", "course", "badge_type", name="uq_badge"),)
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    course = Column(String, nullable=False)
    badge_type = Column(String, nullable=False)
    earned_at = Column(String, nullable=False)


class ProcessedQuizEvent(Base):
    __tablename__ = "processed_quiz_events"
    __table_args__ = (UniqueConstraint("username", "course", "week", name="uq_quiz_event"),)
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    course = Column(String, nullable=False)
    week = Column(String, nullable=False)
    processed_at = Column(String, nullable=False)
    xp_awarded = Column(Integer, default=0)


class FaceEnrollment(Base):
    __tablename__ = "face_enrollments"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    descriptor = Column(Text, nullable=False)   # JSON array of 128 floats
    enrolled_at = Column(String, nullable=False)


class Lecturer(Base):
    __tablename__ = "lecturers"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    courses = Column(Text, nullable=True)   # JSON array of course IDs
    registered_at = Column(String, nullable=False)
