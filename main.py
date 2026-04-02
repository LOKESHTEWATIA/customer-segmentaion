"""
main.py  —  SegmentIQ Pro™ Backend API
Run:  uvicorn main:app --reload
Docs: http://localhost:8000/docs
"""
import io
import json
import pandas as pd
from fastapi import (FastAPI, Depends, HTTPException, UploadFile,
                      File, Form, status, BackgroundTasks)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models, schemas, auth
from database import engine, get_db
from segmentation import (detect_sector, run_pipeline, predict_single,
                           save_artifacts, load_artifacts)

# ─────────────────────────────────────────────
#  CREATE TABLES ON STARTUP
# ─────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────
#  APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="SegmentIQ Pro™ API",
    description="""
## 🎯 SegmentIQ Pro™ — Customer Segmentation Backend

### Features
- **JWT Auth** — signup, login, protected routes
- **CSV Upload** — upload any customer dataset
- **Auto Segmentation** — KNN + KMeans, auto-detects features & sector
- **Predictions** — classify new customers against trained model
- **Results DB** — all results saved to SQLite

### Auth
All endpoints except `/health`, `/auth/signup`, `/auth/login` require a Bearer token.
Get your token from `/auth/login` and pass it as `Authorization: Bearer <token>`.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════
@app.get("/health", response_model=schemas.HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Check API and database status."""
    try:
        db.execute(models.User.__table__.select().limit(1))
        db_status = "connected"
    except Exception:
        db_status = "error"

    return {"status": "ok", "version": "1.0.0", "db": db_status}


# ══════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════
@app.post("/auth/signup",
          response_model=schemas.TokenResponse,
          status_code=status.HTTP_201_CREATED,
          tags=["Auth"])
def signup(body: schemas.SignupRequest, db: Session = Depends(get_db)):
    """Register a new user. Returns a JWT token immediately."""

    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(400, "Username already taken")

    user = models.User(
        email=body.email,
        username=body.username,
        hashed_password=auth.hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user); db.commit(); db.refresh(user)

    token = auth.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Login with email + password. Returns a JWT token."""

    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not auth.verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "Account is inactive")

    token = auth.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/auth/me", response_model=schemas.UserResponse, tags=["Auth"])
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    """Get the currently logged-in user's profile."""
    return current_user


# ══════════════════════════════════════════════
#  PROJECTS
# ══════════════════════════════════════════════
@app.post("/projects",
          response_model=schemas.ProjectResponse,
          status_code=status.HTTP_201_CREATED,
          tags=["Projects"])
async def create_project(
    name:        str        = Form(...),
    description: str        = Form(""),
    file:        UploadFile = File(...),
    db:          Session    = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Upload a CSV/Excel file and create a project.
    The file is parsed to detect shape and sector — segmentation runs separately.
    """
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(400, "Only CSV and Excel files are supported")

    contents = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Could not parse file: {e}")

    if df.empty:
        raise HTTPException(400, "Uploaded file is empty")

    sector = detect_sector(df)

    project = models.Project(
        name=name,
        description=description,
        filename=file.filename,
        sector=sector,
        n_rows=len(df),
        n_features=len(df.columns),
        status="pending",
        owner_id=current_user.id,
    )
    db.add(project); db.commit(); db.refresh(project)

    # Store the raw CSV bytes in a temp file for later segmentation
    os.makedirs("uploads", exist_ok=True)
    with open(f"uploads/project_{project.id}.csv", "wb") as f:
        f.write(contents if file.filename.endswith(".csv") else df.to_csv(index=False).encode())

    return project


@app.get("/projects", response_model=list[schemas.ProjectResponse], tags=["Projects"])
def list_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """List all projects belonging to the current user."""
    return db.query(models.Project).filter(
        models.Project.owner_id == current_user.id
    ).order_by(models.Project.created_at.desc()).all()


@app.get("/projects/{project_id}", response_model=schemas.ProjectResponse, tags=["Projects"])
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Get a single project by ID."""
    p = _get_owned_project(project_id, current_user.id, db)
    return p


@app.delete("/projects/{project_id}", response_model=schemas.MessageResponse, tags=["Projects"])
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Delete a project and all its results."""
    p = _get_owned_project(project_id, current_user.id, db)
    db.delete(p); db.commit()
    # Clean up files
    for path in [f"uploads/project_{project_id}.csv",
                 f"ml_models/project_{project_id}.pkl"]:
        if os.path.exists(path): os.remove(path)
    return {"message": f"Project {project_id} deleted"}


# ══════════════════════════════════════════════
#  SEGMENTATION
# ══════════════════════════════════════════════
@app.post("/segment/run",
          response_model=schemas.SegmentResultResponse,
          tags=["Segmentation"])
def run_segmentation(
    body: schemas.SegmentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Run KNN+KMeans segmentation on an uploaded project.
    Saves results to DB and persists the trained model for predictions.
    """
    project = _get_owned_project(body.project_id, current_user.id, db)

    csv_path = f"uploads/project_{project.id}.csv"
    if not os.path.exists(csv_path):
        raise HTTPException(404, "Uploaded file not found. Please re-upload the project.")

    df = pd.read_csv(csv_path)

    # Update project status
    project.status = "running"
    db.commit()

    try:
        result = run_pipeline(
            df,
            features=body.features,
            n_segments=body.n_segments,
            n_neighbors=body.n_neighbors,
        )
    except ValueError as e:
        project.status = "failed"
        db.commit()
        raise HTTPException(422, str(e))

    # Save ML artifacts
    save_artifacts(
        project.id,
        result["scaler"],
        result["knn_clf"],
        result["seg_name_map"],
        result["features"],
        result["churn_by_seg"],
    )

    # Delete old result if exists
    old = db.query(models.SegmentResult).filter(
        models.SegmentResult.project_id == project.id
    ).first()
    if old:
        db.delete(old); db.commit()

    # Save new result
    seg_result = models.SegmentResult(
        project_id=project.id,
        n_segments=body.n_segments,
        silhouette_score=result["silhouette"],
        features_used=result["features"],
        segment_stats=result["segment_stats"],
        segment_counts=result["segment_counts"],
        churn_risk=result["churn_by_seg"],
    )
    db.add(seg_result); db.commit(); db.refresh(seg_result)

    # Save per-customer rows (batched)
    df_r = result["df_result"]
    id_col = next((c for c in ["customer_id","id","CustomerID"] if c in df_r.columns), None)
    BATCH = 500
    rows_to_add = []
    for i, (_, row) in enumerate(df_r.iterrows()):
        rows_to_add.append(models.CustomerSegment(
            result_id=seg_result.id,
            customer_id=str(row[id_col]) if id_col else str(i),
            segment_name=row["Segment"],
            churn_risk=round(float(row["churn_risk"]), 4),
            row_data={c: (float(v) if isinstance(v, (int, float)) else str(v))
                      for c, v in row.items()
                      if c not in ["_label","Segment","churn_risk"]},
        ))
        if len(rows_to_add) >= BATCH:
            db.bulk_save_objects(rows_to_add); db.commit()
            rows_to_add = []
    if rows_to_add:
        db.bulk_save_objects(rows_to_add); db.commit()

    project.status = "done"
    db.commit()
    db.refresh(seg_result)
    return seg_result


@app.post("/segment/predict",
          response_model=schemas.PredictResponse,
          tags=["Segmentation"])
def predict_customer(
    body: schemas.PredictRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Classify a single new customer using the trained KNN model for a project.
    Pass customer feature values as a JSON dict.
    """
    _get_owned_project(body.project_id, current_user.id, db)

    try:
        artifacts = load_artifacts(body.project_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    return predict_single(
        body.customer,
        artifacts["scaler"],
        artifacts["knn_clf"],
        artifacts["seg_name_map"],
        artifacts["features"],
        artifacts["churn_by_seg"],
    )


@app.get("/segment/sectors", tags=["Segmentation"])
def get_sectors():
    """List all supported industry sectors for auto-detection."""
    from segmentation import SECTORS
    return {"sectors": list(SECTORS.keys())}


# ══════════════════════════════════════════════
#  RESULTS
# ══════════════════════════════════════════════
@app.get("/results/{project_id}",
         response_model=schemas.SegmentResultResponse,
         tags=["Results"])
def get_result(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Get segmentation result stats for a project."""
    _get_owned_project(project_id, current_user.id, db)
    r = db.query(models.SegmentResult).filter(
        models.SegmentResult.project_id == project_id
    ).first()
    if not r:
        raise HTTPException(404, "No result found. Run segmentation first.")
    return r


@app.get("/results/{project_id}/customers",
         response_model=list[schemas.CustomerSegmentResponse],
         tags=["Results"])
def get_customers(
    project_id: int,
    segment: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Get per-customer segment assignments.
    Filter by segment name with ?segment=Champions
    """
    _get_owned_project(project_id, current_user.id, db)
    r = db.query(models.SegmentResult).filter(
        models.SegmentResult.project_id == project_id
    ).first()
    if not r:
        raise HTTPException(404, "Run segmentation first.")

    q = db.query(models.CustomerSegment).filter(
        models.CustomerSegment.result_id == r.id
    )
    if segment:
        q = q.filter(models.CustomerSegment.segment_name == segment)
    return q.offset(offset).limit(limit).all()


@app.get("/results/{project_id}/summary",
         response_model=schemas.SummaryResponse,
         tags=["Results"])
def get_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """High-level summary: counts, churn risk, top churn segment."""
    project = _get_owned_project(project_id, current_user.id, db)
    r = db.query(models.SegmentResult).filter(
        models.SegmentResult.project_id == project_id
    ).first()
    if not r:
        raise HTTPException(404, "Run segmentation first.")

    top_churn = None
    if r.churn_risk:
        top_churn = max(r.churn_risk, key=r.churn_risk.get)

    return {
        "project_id":        project_id,
        "project_name":      project.name,
        "sector":            project.sector,
        "n_customers":       project.n_rows or 0,
        "n_segments":        r.n_segments,
        "silhouette_score":  r.silhouette_score,
        "segment_counts":    r.segment_counts,
        "churn_risk":        r.churn_risk,
        "segment_stats":     r.segment_stats,
        "top_churn_segment": top_churn,
    }


@app.get("/results/{project_id}/csv", tags=["Results"])
def download_csv(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Download the segmented dataset as a CSV file."""
    _get_owned_project(project_id, current_user.id, db)
    r = db.query(models.SegmentResult).filter(
        models.SegmentResult.project_id == project_id
    ).first()
    if not r:
        raise HTTPException(404, "Run segmentation first.")

    customers = db.query(models.CustomerSegment).filter(
        models.CustomerSegment.result_id == r.id
    ).all()

    rows = []
    for c in customers:
        row = dict(c.row_data or {})
        row["customer_id"]  = c.customer_id
        row["Segment"]      = c.segment_name
        row["churn_risk_%"] = round((c.churn_risk or 0) * 100, 1)
        rows.append(row)

    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=segmentiq_project_{project_id}.csv"},
    )


# ─────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────
import os

def _get_owned_project(project_id: int, user_id: int, db: Session) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(404, f"Project {project_id} not found")
    if p.owner_id != user_id:
        raise HTTPException(403, "You don't have access to this project")
    return p
