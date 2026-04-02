"""
segmentation.py  —  KNN + KMeans pipeline (same logic as the Streamlit app)
Called by the FastAPI endpoints — no Streamlit dependency here.
"""
import re
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neighbors import NearestNeighbors, KNeighborsClassifier
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from typing import List, Optional, Dict, Any, Tuple
import joblib, os


# ─────────────────────────────────────────────
#  SECTOR DETECTION
# ─────────────────────────────────────────────
SECTORS = {
    "Retail / E-commerce":  ["purchase","order","recency","frequency","basket","spend","cart","product","category"],
    "EV / Automotive":      ["battery","charging","range","kwh","mileage","vehicle","ev","electric","service"],
    "Construction":         ["project","material","labour","labor","contractor","bid","site","contract","build"],
    "Sales / CRM":          ["deal","pipeline","lead","opportunity","quota","close","revenue","sales","account"],
    "Healthcare":           ["patient","visit","claim","diagnosis","treatment","medication","appointment"],
    "Finance / Banking":    ["portfolio","investment","transaction","balance","credit","loan","asset","deposit"],
    "SaaS / Tech":          ["subscription","session","feature","churn","mrr","arr","license","login","dau"],
    "Other":                [],
}


def detect_sector(df: pd.DataFrame) -> str:
    cols = " ".join(df.columns.str.lower())
    scores = {s: sum(1 for kw in kws if kw in cols) for s, kws in SECTORS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Other"


# ─────────────────────────────────────────────
#  SMART FEATURE DETECTION
# ─────────────────────────────────────────────
SKIP_WORDS = [
    "id","_id","uuid","key","code","zip","pin","postal","phone","mobile",
    "index","unnamed","row","serial","seq","rank","num","no",
    "year","month","day","hour","date","time","gender","sex",
    "country","city","state","region","flag","status","type",
    "category","class","label","tag","group",
]
KEEP_WORDS = [
    "amount","value","spend","revenue","sales","profit","cost","price",
    "frequency","freq","count","qty","quantity","volume","rate","score",
    "risk","churn","recency","days","age","tenure","balance","credit",
    "total","avg","average","mrr","arr","ltv","deal","purchase","order",
]


def _parse_val(v: str) -> float:
    v = str(v).strip().upper().replace(",", "").replace("$","").replace("€","").replace("₹","").replace("%","")
    try:
        if v.endswith("K"): return float(v[:-1]) * 1_000
        if v.endswith("M"): return float(v[:-1]) * 1_000_000
        if v.endswith("B"): return float(v[:-1]) * 1_000_000_000
        return float(v)
    except:
        return np.nan


def detect_numeric_features(df: pd.DataFrame) -> List[str]:
    result = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if any(re.search(r"(^|_)" + w + r"($|_)", col_lower) for w in SKIP_WORDS):
            continue
        series = df[col].copy()
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if len(clean) == 0 or clean.nunique() <= 1:
                continue
            result[col] = series
            continue
        if series.dtype == object:
            converted = series.astype(str).str.strip().apply(_parse_val)
            non_null = converted.dropna()
            if len(non_null) / max(len(series.dropna()), 1) >= 0.6 and non_null.nunique() > 1:
                result[col] = converted

    def sort_key(c):
        return (0 if any(w in c.lower() for w in KEEP_WORDS) else 1, c)

    return sorted(result.keys(), key=sort_key)


# ─────────────────────────────────────────────
#  CHURN RISK
# ─────────────────────────────────────────────
def compute_churn(df: pd.DataFrame, features: List[str]) -> pd.Series:
    rec = next((f for f in features if any(x in f.lower()
        for x in ["recency","days","since","last","age"])), None)
    frq = next((f for f in features if any(x in f.lower()
        for x in ["frequency","freq","count","visit","purchase","order","session"])), None)

    score = pd.Series(0.5, index=df.index)
    if rec:
        r = pd.to_numeric(df[rec], errors="coerce")
        score += 0.45 * (r - r.min()) / (r.max() - r.min() + 1e-9)
    if frq:
        f = pd.to_numeric(df[frq], errors="coerce")
        score -= 0.35 * (f - f.min()) / (f.max() - f.min() + 1e-9)

    return score.clip(0.05, 0.95)


# ─────────────────────────────────────────────
#  MAIN SEGMENTATION PIPELINE
# ─────────────────────────────────────────────
SEGMENT_NAMES = [
    "Champions", "Loyal Customers", "Promising",
    "At-Risk", "Hibernating", "Lost",
    "New Customers", "Need Attention",
]


def run_pipeline(
    df: pd.DataFrame,
    features: Optional[List[str]] = None,
    n_segments: int = 4,
    n_neighbors: int = 5,
) -> Dict[str, Any]:
    """
    Full segmentation pipeline.
    Returns a dict with:
        df_result       — original df + Segment + churn_risk columns
        scaler          — fitted StandardScaler
        knn_clf         — fitted KNeighborsClassifier (for new predictions)
        seg_name_map    — {cluster_label: segment_name}
        features        — list of features actually used
        silhouette      — float
        segment_stats   — {segment: {feature: mean, ...}}
        segment_counts  — {segment: count}
        churn_by_seg    — {segment: avg_churn_risk}
    """
    # ── 1. Feature selection ──────────────────
    if not features:
        features = detect_numeric_features(df)
    if len(features) < 2:
        raise ValueError("Need at least 2 numeric features for segmentation.")

    # ── 2. Coerce + clean ────────────────────
    X_df = pd.DataFrame(index=df.index)
    used_features = []
    for col in features:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col].astype(str).str.replace(
            r'[$€£¥₹,%\s]', '', regex=True).apply(_parse_val), errors="coerce")
        s = s.fillna(s.median() if pd.notna(s.median()) else 0)
        X_df[col] = s.astype(np.float64)
        used_features.append(col)

    X_df = X_df.dropna(axis=1, how="all")
    X_df = X_df.loc[:, X_df.std() > 0]
    X_df = X_df.astype(np.float64)
    used_features = list(X_df.columns)

    if len(used_features) < 2:
        raise ValueError("Not enough valid numeric columns after cleaning.")

    # ── 3. Scale ─────────────────────────────
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_df.values)

    # ── 4. KMeans clustering ─────────────────
    km = KMeans(n_clusters=n_segments, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    # ── 5. Name segments by value ─────────────
    val_col = next((f for f in used_features if any(
        x in f.lower() for x in ["spend","value","revenue","total","amount","price","mrr"]
    )), used_features[0])

    seg_means = (
        pd.Series(labels, index=df.index)
        .to_frame("_lbl")
        .join(X_df[val_col])
        .groupby("_lbl")[val_col]
        .mean()
        .sort_values(ascending=False)
    )
    seg_name_map = {int(lbl): SEGMENT_NAMES[i] for i, lbl in enumerate(seg_means.index)}

    # ── 6. Train KNN classifier ───────────────
    knn_clf = KNeighborsClassifier(
        n_neighbors=min(n_neighbors, 11), metric="euclidean", n_jobs=-1
    )
    knn_clf.fit(X_scaled, labels)

    # ── 7. Silhouette score ───────────────────
    sil = float(silhouette_score(X_scaled, labels)) if n_segments > 1 else 0.0

    # ── 8. Build result dataframe ─────────────
    df_result = df.copy()
    df_result["_label"]   = labels
    df_result["Segment"]  = [seg_name_map[int(l)] for l in labels]
    df_result["churn_risk"] = compute_churn(df, used_features).values

    # ── 9. Aggregated stats ───────────────────
    segment_stats  = {}
    segment_counts = {}
    churn_by_seg   = {}

    for seg_name in df_result["Segment"].unique():
        mask  = df_result["Segment"] == seg_name
        group = df_result[mask]
        segment_counts[seg_name] = int(mask.sum())
        churn_by_seg[seg_name]   = round(float(group["churn_risk"].mean()), 4)
        segment_stats[seg_name]  = {
            f: round(float(pd.to_numeric(group[f], errors="coerce").mean()), 4)
            for f in used_features if f in group.columns
        }

    return {
        "df_result":      df_result,
        "scaler":         scaler,
        "knn_clf":        knn_clf,
        "seg_name_map":   seg_name_map,
        "features":       used_features,
        "silhouette":     sil,
        "segment_stats":  segment_stats,
        "segment_counts": segment_counts,
        "churn_by_seg":   churn_by_seg,
    }


# ─────────────────────────────────────────────
#  PREDICT SINGLE CUSTOMER
# ─────────────────────────────────────────────
def predict_single(
    customer: Dict[str, Any],
    scaler: StandardScaler,
    knn_clf: KNeighborsClassifier,
    seg_name_map: Dict[int, str],
    features: List[str],
    churn_by_seg: Dict[str, float],
) -> Dict[str, Any]:

    X = np.array([[_parse_val(str(customer.get(f, 0))) for f in features]], dtype=np.float64)
    X_scaled = scaler.transform(X)

    pred_label   = int(knn_clf.predict(X_scaled)[0])
    pred_proba   = knn_clf.predict_proba(X_scaled)[0]
    pred_seg     = seg_name_map.get(pred_label, f"Segment {pred_label+1}")
    confidence   = float(pred_proba.max())
    all_probs    = {
        seg_name_map.get(int(i), f"Segment {i+1}"): round(float(p), 4)
        for i, p in enumerate(pred_proba)
    }
    churn_risk   = float(churn_by_seg.get(pred_seg, 0.5))

    return {
        "segment":    pred_seg,
        "confidence": round(confidence, 4),
        "churn_risk": round(churn_risk, 4),
        "all_probs":  all_probs,
    }


# ─────────────────────────────────────────────
#  SAVE / LOAD MODEL ARTIFACTS
# ─────────────────────────────────────────────
MODELS_DIR = "ml_models"


def save_artifacts(project_id: int, scaler, knn_clf, seg_name_map, features, churn_by_seg):
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump({
        "scaler":       scaler,
        "knn_clf":      knn_clf,
        "seg_name_map": seg_name_map,
        "features":     features,
        "churn_by_seg": churn_by_seg,
    }, f"{MODELS_DIR}/project_{project_id}.pkl")


def load_artifacts(project_id: int) -> Dict[str, Any]:
    path = f"{MODELS_DIR}/project_{project_id}.pkl"
    if not os.path.exists(path):
        raise FileNotFoundError(f"No trained model found for project {project_id}. Run segmentation first.")
    return joblib.load(path)
