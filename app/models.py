from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(100), primary_key=True, index=True)
    user_name = Column(String(100), nullable=False)
    device_name = Column(String(100), nullable=True)
    device_id = Column(String(100), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    activity_sessions = relationship("ActivitySession", back_populates="user")


class Activity(Base):
    __tablename__ = "activity"

    activity_id = Column(String(100), primary_key=True, index=True)
    activity_name = Column(String(100), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    activity_sessions = relationship("ActivitySession", back_populates="activity")


class ActivitySession(Base):
    __tablename__ = "activity_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        String(100), ForeignKey("users.user_id"), nullable=False, index=True
    )
    activity_id = Column(
        String(100), ForeignKey("activity.activity_id"), nullable=False, index=True
    )
    device_id = Column(String(100), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="activity_sessions")
    activity = relationship("Activity", back_populates="activity_sessions")

    __table_args__ = (
        Index("ix_activity_sessions_created_at", "created_at"),
        Index("ix_activity_sessions_device_id", "device_id"),
    )
