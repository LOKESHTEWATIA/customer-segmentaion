"""
schemas.py  —  Pydantic v2 request / response schemas
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────
class SignupRequest(BaseModel):
    email:     EmailStr
    username:  str
    password:  str
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not v.replace("_","").replace("-","").isalnum():
            raise ValueError("Username can only contain letters, numbers, _ and -")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         "UserResponse"


class UserResponse(BaseModel):
    id:         int
    email:      str
    username:   str
    full_name:  Optional[str]
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  PROJECTS
# ─────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name:        str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id:          int
    name:        str
    description: Optional[str]
    filename:    str
    sector:      Optional[str]
    n_rows:      Optional[int]
    n_features:  Optional[int]
    status:      str
    created_at:  datetime
    owner_id:    int

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  SEGMENTATION
# ─────────────────────────────────────────────
class SegmentRequest(BaseModel):
    project_id:    int
    n_segments:    int = 4
    n_neighbors:   int = 5
    features:      Optional[List[str]] = None    # None = auto-detect


class PredictRequest(BaseModel):
    project_id: int
    customer:   Dict[str, Any]    # {feature: value, ...}


class PredictResponse(BaseModel):
    segment:      str
    confidence:   float
    churn_risk:   float
    all_probs:    Dict[str, float]


# ─────────────────────────────────────────────
#  RESULTS
# ─────────────────────────────────────────────
class SegmentResultResponse(BaseModel):
    id:               int
    project_id:       int
    n_segments:       int
    silhouette_score: Optional[float]
    features_used:    Optional[List[str]]
    segment_stats:    Optional[Dict[str, Any]]
    segment_counts:   Optional[Dict[str, int]]
    churn_risk:       Optional[Dict[str, float]]
    created_at:       datetime

    model_config = {"from_attributes": True}


class CustomerSegmentResponse(BaseModel):
    id:           int
    customer_id:  Optional[str]
    segment_name: str
    churn_risk:   Optional[float]
    row_data:     Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class SummaryResponse(BaseModel):
    project_id:       int
    project_name:     str
    sector:           Optional[str]
    n_customers:      int
    n_segments:       int
    silhouette_score: Optional[float]
    segment_counts:   Optional[Dict[str, int]]
    churn_risk:       Optional[Dict[str, float]]
    segment_stats:    Optional[Dict[str, Any]]
    top_churn_segment: Optional[str]


# ─────────────────────────────────────────────
#  MISC
# ─────────────────────────────────────────────
class HealthResponse(BaseModel):
    status:  str
    version: str
    db:      str


class MessageResponse(BaseModel):
    message: str


TokenResponse.model_rebuild()
