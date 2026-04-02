"""
models.py  —  SQLAlchemy ORM table definitions
Tables: users · projects · results · segments
"""
from sqlalchemy import (Column, Integer, String, Float, Boolean,
                         DateTime, Text, ForeignKey, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    username      = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name     = Column(String, nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String, nullable=False)
    description  = Column(Text, nullable=True)
    filename     = Column(String, nullable=False)
    sector       = Column(String, nullable=True)
    n_rows       = Column(Integer, nullable=True)
    n_features   = Column(Integer, nullable=True)
    status       = Column(String, default="pending")   # pending | running | done | failed
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner    = relationship("User", back_populates="projects")
    result   = relationship("SegmentResult", back_populates="project",
                             uselist=False, cascade="all, delete-orphan")


class SegmentResult(Base):
    __tablename__ = "segment_results"

    id              = Column(Integer, primary_key=True, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), unique=True, nullable=False)

    n_segments      = Column(Integer, nullable=False)
    silhouette_score= Column(Float,   nullable=True)
    features_used   = Column(JSON,    nullable=True)   # list of feature names
    segment_stats   = Column(JSON,    nullable=True)   # {segment: {mean_col: val, ...}}
    segment_counts  = Column(JSON,    nullable=True)   # {segment: count}
    churn_risk      = Column(JSON,    nullable=True)   # {segment: risk_pct}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project  = relationship("Project", back_populates="result")
    segments = relationship("CustomerSegment", back_populates="result",
                             cascade="all, delete-orphan")


class CustomerSegment(Base):
    __tablename__ = "customer_segments"

    id           = Column(Integer, primary_key=True, index=True)
    result_id    = Column(Integer, ForeignKey("segment_results.id"), nullable=False)
    customer_id  = Column(String,  nullable=True)
    segment_name = Column(String,  nullable=False)
    churn_risk   = Column(Float,   nullable=True)
    row_data     = Column(JSON,    nullable=True)   # original row as dict

    result = relationship("SegmentResult", back_populates="segments")
