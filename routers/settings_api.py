"""
Settings API router — GET/POST /api/settings, contacts, blocklist
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import Setting, Contact, Blocklist
from config import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/api", tags=["settings"])

DEFAULT_SETTINGS = {
    "auto_screen": True,
    "ask_followup": True,
    "auto_block_high_risk": True,
    "contact_verification": True,
    "scam_detection": True,
    "spoofing_detection": True,
    "urgency_analysis": True,
    "supported_languages": SUPPORTED_LANGUAGES,
    "risk_threshold": 60,
    "auto_simulate": False,
    "auto_simulate_interval": 30,
    "ollama_model": "llama3",
    "user_real_number": "",
}


def _get_setting(db: Session, key: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        try:
            return json.loads(row.value)
        except Exception:
            return row.value
    return DEFAULT_SETTINGS.get(key)


def _set_setting(db: Session, key: str, value):
    row = db.query(Setting).filter(Setting.key == key).first()
    encoded = json.dumps(value)
    if row:
        row.value = encoded
    else:
        db.add(Setting(key=key, value=encoded))
    db.commit()


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Return all current settings (merged with defaults)."""
    result = dict(DEFAULT_SETTINGS)
    rows = db.query(Setting).all()
    for row in rows:
        try:
            result[row.key] = json.loads(row.value)
        except Exception:
            result[row.key] = row.value
    return result


@router.post("/settings")
def save_settings(body: dict, db: Session = Depends(get_db)):
    """Save settings to the database."""
    for key, value in body.items():
        _set_setting(db, key, value)
    return {"status": "saved", "updated_keys": list(body.keys())}


# ── Contacts ──────────────────────────────────────────────────────────────────

@router.get("/contacts")
def list_contacts(db: Session = Depends(get_db)):
    contacts = db.query(Contact).all()
    return {"contacts": [c.to_dict() for c in contacts]}


@router.post("/contacts")
def add_contact(body: dict, db: Session = Depends(get_db)):
    contact = Contact(
        name=body.get("name", ""),
        phone_number=body.get("phone_number", ""),
        organization=body.get("organization"),
        notes=body.get("notes"),
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact.to_dict()


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return {"status": "deleted", "id": contact_id}


@router.post("/contacts/upload")
async def upload_contacts_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload contacts as CSV (name,phone_number,organization)."""
    import csv, io
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    added = 0
    for row in reader:
        if row.get("name") and row.get("phone_number"):
            contact = Contact(
                name=row["name"],
                phone_number=row["phone_number"],
                organization=row.get("organization"),
                notes=row.get("notes"),
            )
            db.add(contact)
            added += 1
    db.commit()
    return {"status": "imported", "contacts_added": added}


# ── Blocklist ─────────────────────────────────────────────────────────────────

@router.get("/blocklist")
def list_blocklist(db: Session = Depends(get_db)):
    entries = db.query(Blocklist).all()
    return {"blocklist": [e.to_dict() for e in entries]}


@router.post("/blocklist")
def add_to_blocklist(body: dict, db: Session = Depends(get_db)):
    entry = Blocklist(
        pattern=body.get("pattern", ""),
        reason=body.get("reason"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry.to_dict()


@router.delete("/blocklist/{entry_id}")
def remove_from_blocklist(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Blocklist).filter(Blocklist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Blocklist entry not found")
    db.delete(entry)
    db.commit()
    return {"status": "deleted", "id": entry_id}
