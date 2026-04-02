"""
run_me.py  —  Install everything and start the SegmentIQ API
Run:  python run_me.py
API will be live at:  http://localhost:8000
Docs (Swagger UI) at: http://localhost:8000/docs
"""
import subprocess, sys, importlib

PACKAGES = {
    "fastapi":          "fastapi",
    "uvicorn":          "uvicorn[standard]",
    "sqlalchemy":       "sqlalchemy",
    "jose":             "python-jose[cryptography]",
    "passlib":          "passlib[bcrypt]",
    "multipart":        "python-multipart",
    "pandas":           "pandas",
    "numpy":            "numpy",
    "sklearn":          "scikit-learn",
    "joblib":           "joblib",
    "openpyxl":         "openpyxl",
    "pydantic":         "pydantic[email]",
}

print("\n" + "="*54)
print("   SegmentIQ Pro™ Backend  —  Auto Setup")
print("="*54)
print("\n📦 Installing packages...\n")

for imp, pip in PACKAGES.items():
    try:
        importlib.import_module(imp.split(".")[0])
        print(f"  ✅  {pip} (already installed)")
    except ImportError:
        for cmd in [
            [sys.executable, "-m", "pip", "install", pip, "-q"],
            [sys.executable, "-m", "pip", "install", pip, "-q", "--user"],
        ]:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                print(f"  ✅  {pip}")
                break
        else:
            print(f"  ❌  {pip}  →  run manually: pip install {pip}")

print("\n🚀 Starting SegmentIQ API...")
print("   API  →  http://localhost:8000")
print("   Docs →  http://localhost:8000/docs\n")
subprocess.run([
    sys.executable, "-m", "uvicorn", "main:app",
    "--reload", "--host", "0.0.0.0", "--port", "8000"
])
