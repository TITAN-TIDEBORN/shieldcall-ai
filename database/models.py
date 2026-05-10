"""
SQLAlchemy models for ShieldCall AI
"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    caller_number = Column(String(50), index=True)
    caller_name = Column(String(200), default="Unknown")
    caller_org = Column(String(200), nullable=True)
    detected_language = Column(String(50), default="English")
    reason_summary = Column(Text, nullable=True)
    full_transcript = Column(Text, default="[]")   # JSON list of {role, text, timestamp}
    intent_label = Column(String(50), default="unknown")
    intent_confidence = Column(Float, default=0.0)
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="low")
    risk_signals = Column(Text, default="[]")       # JSON list of strings
    check_contact = Column(String(20), default="unverified")
    check_scam = Column(String(20), default="clean")
    check_spoofing = Column(String(20), default="genuine")
    check_urgency_score = Column(Integer, default=0)
    action_taken = Column(String(30), default="pending")
    call_duration_seconds = Column(Integer, default=0)
    is_simulated = Column(Integer, default=1)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "caller_number": self.caller_number,
            "caller_name": self.caller_name,
            "caller_org": self.caller_org,
            "detected_language": self.detected_language,
            "reason_summary": self.reason_summary,
            "full_transcript": json.loads(self.full_transcript or "[]"),
            "intent_label": self.intent_label,
            "intent_confidence": self.intent_confidence,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_signals": json.loads(self.risk_signals or "[]"),
            "check_contact": self.check_contact,
            "check_scam": self.check_scam,
            "check_spoofing": self.check_spoofing,
            "check_urgency_score": self.check_urgency_score,
            "action_taken": self.action_taken,
            "call_duration_seconds": self.call_duration_seconds,
            "is_simulated": bool(self.is_simulated),
        }


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    phone_number = Column(String(50), index=True)
    organization = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone_number": self.phone_number,
            "organization": self.organization,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Blocklist(Base):
    __tablename__ = "blocklist"

    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String(200), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "pattern": self.pattern,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)   # JSON-encoded value
