import json
import logging
from datetime import datetime

from tracker_app.db.models import SessionLocal, SessionToggle, EarCalibration
from tracker_app.utils import utcnow as _utcnow

_log = logging.getLogger(__name__)


def _get_toggle_db():
    db = SessionLocal()
    toggle = db.query(SessionToggle).filter(SessionToggle.id == 1).first()
    if not toggle:
        toggle = SessionToggle(id=1, active=False)
        db.add(toggle)
        db.commit()
        db.refresh(toggle)
    return db, toggle


def is_active():
    try:
        db, toggle = _get_toggle_db()
        try:
            return bool(toggle.active)
        finally:
            db.close()
    except Exception as exc:
        _log.warning("Session state operation failed: %s", exc)
        return False


def start():
    try:
        db, toggle = _get_toggle_db()
        try:
            now = _utcnow()
            toggle.active = True
            toggle.started_at = now
            toggle.stopped_at = None
            db.commit()
            return {
                "active": True,
                "started_at": now.isoformat(),
                "stopped_at": None,
                "ear_calibration": get_calibration(),
            }
        finally:
            db.close()
    except Exception as exc:
        _log.warning("Session state operation failed: %s", exc)
        return {"active": False, "started_at": None, "stopped_at": None, "ear_calibration": None}


def stop():
    try:
        db, toggle = _get_toggle_db()
        try:
            now = _utcnow()
            toggle.active = False
            toggle.stopped_at = now
            db.commit()
            cal = db.query(EarCalibration).filter(EarCalibration.id == 1).first()
            if cal:
                db.delete(cal)
                db.commit()
            return {
                "active": False,
                "started_at": toggle.started_at.isoformat() if toggle.started_at else None,
                "stopped_at": now.isoformat(),
                "ear_calibration": None,
            }
        finally:
            db.close()
    except Exception as exc:
        _log.warning("Session state operation failed: %s", exc)
        return {"active": False, "started_at": None, "stopped_at": None, "ear_calibration": None}


def set_calibration(data):
    try:
        db = SessionLocal()
        try:
            cal = db.query(EarCalibration).filter(EarCalibration.id == 1).first()
            if not cal:
                cal = EarCalibration(id=1)
                db.add(cal)
            cal.personal_ear_low = data.get("personal_ear_low")
            cal.personal_ear_high = data.get("personal_ear_high")
            cal.mean_ear = data.get("mean_ear")
            cal.std_ear = data.get("std_ear")
            cal.fallback = data.get("fallback", False)
            cal.raw_data = json.dumps(data) if data else None
            cal.updated_at = _utcnow()
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        _log.warning("Session state operation failed: %s", exc)


def get_calibration():
    try:
        db = SessionLocal()
        try:
            cal = db.query(EarCalibration).filter(EarCalibration.id == 1).first()
            if cal and cal.raw_data:
                return json.loads(cal.raw_data)
            return None
        finally:
            db.close()
    except Exception as exc:
        _log.warning("Session state operation failed: %s", exc)
        return None


def get_status():
    try:
        db, toggle = _get_toggle_db()
        try:
            elapsed = None
            if toggle.active and toggle.started_at:
                try:
                    elapsed = int((_utcnow() - toggle.started_at).total_seconds())
                except Exception:
                    elapsed = None
            return {
                "active": bool(toggle.active),
                "started_at": toggle.started_at.isoformat() if toggle.started_at else None,
                "stopped_at": toggle.stopped_at.isoformat() if toggle.stopped_at else None,
                "elapsed_seconds": elapsed,
                "ear_calibration": get_calibration(),
            }
        finally:
            db.close()
    except Exception as exc:
        _log.warning("Session state operation failed: %s", exc)
        return {
            "active": False,
            "started_at": None,
            "stopped_at": None,
            "elapsed_seconds": None,
            "ear_calibration": None,
        }
