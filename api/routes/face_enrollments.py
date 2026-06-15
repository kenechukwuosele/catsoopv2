from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..auth import require_admin


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_router():
    router = APIRouter()

    @router.get("/admin/face-enrollments", dependencies=[Depends(require_admin)])
    def list_face_enrollments(db: Session = Depends(get_db)):
        rows = db.query(models.FaceEnrollment).order_by(models.FaceEnrollment.enrolled_at.desc()).all()
        return {"enrollments": [{"username": r.username, "enrolled_at": r.enrolled_at} for r in rows]}

    @router.delete("/admin/face-enrollments/{username}", dependencies=[Depends(require_admin)])
    def delete_face_enrollment(username: str, db: Session = Depends(get_db)):
        deleted = db.query(models.FaceEnrollment).filter_by(username=username).delete()
        db.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail="Not found")
        return {"status": "deleted"}

    return router
