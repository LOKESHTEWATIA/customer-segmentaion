# customer-segmentaion
# 🎯 SegmentIQ Pro™ - AI-Powered Customer Segmentation

**Smart Customer Segmentation & Churn Prediction Platform** built with **FastAPI + Streamlit**

SegmentIQ Pro is a full-stack web application that helps businesses automatically segment their customers using **KMeans + KNN**, detect high-churn segments, and predict segment membership for new customers — all with a beautiful, modern UI.

---

### ✨ Key Features

#### Backend (FastAPI)
- **JWT Authentication** — Secure signup, login, and protected routes
- **File Upload** — Supports CSV and Excel files with automatic parsing
- **Smart Auto-Detection**:
  - Industry sector detection (Retail, SaaS, EV, Finance, Healthcare, etc.)
  - Numeric feature detection with intelligent cleaning
- **Advanced Segmentation Pipeline**:
  - KMeans clustering + KNN classifier
  - Silhouette score calculation
  - Automated churn risk scoring based on recency & frequency
- **Model Persistence** — Saves trained scaler, KNN model, and artifacts per project
- **Single Customer Prediction** — Real-time segment classification for new customers
- **SQLite Database** with full ORM using SQLAlchemy

#### Frontend (Streamlit)
- Modern, clean, and responsive dark/light-friendly UI
- **Dashboard** to manage all your projects
- **One-click Segmentation** with customizable parameters (number of segments, KNN neighbors, feature override)
- **Rich Visualizations**:
  - Segment distribution pie chart
  - Churn risk horizontal bar chart
  - Detailed per-segment insights with average metrics
- **Export** — Download full segmented dataset with segment labels and churn risk
- **Live Prediction Tool** — Predict segment & churn risk for any new customer
- Beautiful cards, metrics, pills, and hover effects

---

### 🛠️ Tech Stack

**Backend:**
- FastAPI
- SQLAlchemy + SQLite
- Scikit-learn (KMeans, KNN, StandardScaler)
- Pandas & NumPy
- Python-JOSE + Passlib (JWT + bcrypt)
- Joblib (model serialization)

**Frontend:**
- Streamlit
- Plotly (interactive charts)
- Tailwind-inspired custom CSS

---

### 🚀 Quick Start

#### 1. Clone the repository
```bash
git clone https://github.com/yourusername/segmentiq-pro.git
cd segmentiq-pro
