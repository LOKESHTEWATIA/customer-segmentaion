"""
api.py  —  SegmentIQ Frontend API Client
Drop this file in the same folder as your Streamlit app.py
Every API call goes through this file — never call requests directly.
"""
import requests
import streamlit as st
from typing import Optional, Dict, Any, List
import io

# ─────────────────────────────────────────────
#  CONFIG  (change if backend runs elsewhere)
# ─────────────────────────────────────────────
BASE_URL = "http://localhost:8000"


# ─────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────
def _headers() -> Dict[str, str]:
    """Attach JWT token from session state to every request."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _handle(resp: requests.Response) -> Dict:
    """Raise a clean Streamlit error on non-2xx, else return JSON."""
    if resp.status_code == 401:
        st.session_state.token    = None
        st.session_state.user     = None
        st.session_state.logged_in = False
        st.error("Session expired. Please log in again.")
        st.stop()
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise APIError(detail, resp.status_code)
    return resp.json()


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


# ─────────────────────────────────────────────
#  HEALTH
# ─────────────────────────────────────────────
def health_check() -> Dict:
    """Ping the backend. Returns {status, version, db}."""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        return _handle(resp)
    except requests.ConnectionError:
        return {"status": "offline", "version": "—", "db": "—"}


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────
def signup(email: str, username: str, password: str, full_name: str = "") -> Dict:
    """Register a new user. Returns {access_token, user}."""
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email, "username": username,
        "password": password, "full_name": full_name,
    })
    return _handle(resp)


def login(email: str, password: str) -> Dict:
    """Login. Returns {access_token, user}."""
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email, "password": password,
    })
    return _handle(resp)


def get_me() -> Dict:
    """Get current logged-in user profile."""
    resp = requests.get(f"{BASE_URL}/auth/me", headers=_headers())
    return _handle(resp)


# ─────────────────────────────────────────────
#  PROJECTS
# ─────────────────────────────────────────────
def create_project(name: str, file_bytes: bytes,
                   filename: str, description: str = "") -> Dict:
    """
    Upload a CSV/Excel file and create a project.
    file_bytes: raw bytes from st.file_uploader (uploaded_file.read())
    """
    resp = requests.post(
        f"{BASE_URL}/projects",
        headers=_headers(),
        data={"name": name, "description": description},
        files={"file": (filename, io.BytesIO(file_bytes), "text/csv")},
    )
    return _handle(resp)


def list_projects() -> List[Dict]:
    """List all projects for the current user."""
    resp = requests.get(f"{BASE_URL}/projects", headers=_headers())
    return _handle(resp)


def get_project(project_id: int) -> Dict:
    """Get a single project by ID."""
    resp = requests.get(f"{BASE_URL}/projects/{project_id}", headers=_headers())
    return _handle(resp)


def delete_project(project_id: int) -> Dict:
    """Delete a project and all its results."""
    resp = requests.delete(f"{BASE_URL}/projects/{project_id}", headers=_headers())
    return _handle(resp)


# ─────────────────────────────────────────────
#  SEGMENTATION
# ─────────────────────────────────────────────
def run_segmentation(project_id: int, n_segments: int = 4,
                     n_neighbors: int = 5,
                     features: Optional[List[str]] = None) -> Dict:
    """
    Trigger KNN+KMeans segmentation on a project.
    Returns SegmentResultResponse with silhouette, stats, counts, churn.
    """
    resp = requests.post(
        f"{BASE_URL}/segment/run",
        headers=_headers(),
        json={
            "project_id":  project_id,
            "n_segments":  n_segments,
            "n_neighbors": n_neighbors,
            "features":    features,
        },
        timeout=300,    # training can take a while on large datasets
    )
    return _handle(resp)


def predict_customer(project_id: int, customer: Dict[str, Any]) -> Dict:
    """
    Classify a single new customer using the trained KNN model.
    customer = {"recency_days": 15, "total_spent": 5000, ...}
    Returns {segment, confidence, churn_risk, all_probs}
    """
    resp = requests.post(
        f"{BASE_URL}/segment/predict",
        headers=_headers(),
        json={"project_id": project_id, "customer": customer},
    )
    return _handle(resp)


def get_sectors() -> List[str]:
    """Get list of supported industry sectors."""
    resp = requests.get(f"{BASE_URL}/segment/sectors", headers=_headers())
    return _handle(resp).get("sectors", [])


# ─────────────────────────────────────────────
#  RESULTS
# ─────────────────────────────────────────────
def get_result(project_id: int) -> Dict:
    """Get segmentation result stats (silhouette, segment_stats, churn_risk)."""
    resp = requests.get(f"{BASE_URL}/results/{project_id}", headers=_headers())
    return _handle(resp)


def get_summary(project_id: int) -> Dict:
    """High-level summary: counts, churn risk, top churn segment."""
    resp = requests.get(f"{BASE_URL}/results/{project_id}/summary", headers=_headers())
    return _handle(resp)


def get_customers(project_id: int, segment: Optional[str] = None,
                  limit: int = 200, offset: int = 0) -> List[Dict]:
    """
    Fetch per-customer segment assignments.
    Filter by segment name: get_customers(1, segment="Champions")
    """
    params = {"limit": limit, "offset": offset}
    if segment:
        params["segment"] = segment
    resp = requests.get(
        f"{BASE_URL}/results/{project_id}/customers",
        headers=_headers(), params=params,
    )
    return _handle(resp)


def download_csv(project_id: int) -> bytes:
    """Download segmented dataset as CSV bytes."""
    resp = requests.get(
        f"{BASE_URL}/results/{project_id}/csv",
        headers=_headers(), stream=True,
    )
    if not resp.ok:
        raise APIError(f"Download failed: {resp.status_code}")
    return resp.content
