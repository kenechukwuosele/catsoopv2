from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session

from .. import models

BADGE_META = {
    "first_attempt": {"label": "First Attempt",  "icon": "🎯"},
    "streak_3":      {"label": "3-Day Streak",    "icon": "🔥"},
    "streak_7":      {"label": "7-Day Streak",    "icon": "💎"},
    "top_class":     {"label": "Top of Class",    "icon": "🏆"},
}


def _award_badge(db: Session, username: str, course: str, badge_type: str, earned: list):
    exists = db.query(models.Badge).filter_by(
        username=username, course=course, badge_type=badge_type
    ).first()
    if not exists:
        db.add(models.Badge(
            username=username, course=course, badge_type=badge_type,
            earned_at=datetime.utcnow().isoformat()
        ))
        meta = BADGE_META.get(badge_type, {"label": badge_type, "icon": "🏅"})
        earned.append({"type": badge_type, **meta})


def award_xp(db: Session, username: str, course: str, percent_correct: float) -> dict:
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    profile = db.query(models.StudentProfile).filter_by(username=username, course=course).first()
    if not profile:
        profile = models.StudentProfile(username=username, course=course, xp=0, streak=0, last_active=None)
        db.add(profile)
        db.flush()

    if profile.last_active == today:
        pass  # already counted today, don't change streak
    elif profile.last_active == yesterday:
        profile.streak += 1
    else:
        profile.streak = 1
    profile.last_active = today

    base_xp = round(percent_correct * 100)
    streak_bonus = min(profile.streak * 10, 50)
    xp_awarded = base_xp + streak_bonus
    profile.xp += xp_awarded

    badges_earned: list = []

    # first_attempt: first ever quiz completion across all courses
    total_events = db.query(models.ProcessedQuizEvent).filter_by(username=username).count()
    if total_events <= 1:  # current event was just inserted before this call
        _award_badge(db, username, course, "first_attempt", badges_earned)

    if profile.streak >= 7:
        _award_badge(db, username, course, "streak_7", badges_earned)
    elif profile.streak >= 3:
        _award_badge(db, username, course, "streak_3", badges_earned)

    # top_class: check after xp update
    db.flush()
    top = db.query(models.StudentProfile).filter_by(course=course).order_by(
        models.StudentProfile.xp.desc()
    ).first()
    if top and top.username == username:
        _award_badge(db, username, course, "top_class", badges_earned)

    db.commit()

    return {
        "xp_awarded": xp_awarded,
        "new_total_xp": profile.xp,
        "streak": profile.streak,
        "badges_earned": badges_earned,
    }


def update_streak_only(db: Session, username: str, course: str) -> dict:
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    profile = db.query(models.StudentProfile).filter_by(username=username, course=course).first()
    if not profile:
        profile = models.StudentProfile(username=username, course=course, xp=0, streak=0, last_active=None)
        db.add(profile)
        db.flush()

    if profile.last_active == today:
        pass
    elif profile.last_active == yesterday:
        profile.streak += 1
    else:
        profile.streak = 1
    profile.last_active = today

    db.commit()
    return {"streak": profile.streak}
