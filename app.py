"""
app.py  —  SegmentIQ Pro™ Frontend (connected to FastAPI backend)
Run backend first:  cd ../segmentiq_backend && python run_me.py
Then run this:      streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import api
from api import APIError

st.set_page_config(
    page_title="SegmentIQ Pro™",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  CSS  (same dark/light theme as before)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'Plus Jakarta Sans',sans-serif!important;background:#F5F7FF!important;color:#111827!important}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:0!important;max-width:1160px}
[data-testid="stSidebar"]{background:#fff!important;border-right:1px solid #E5E7EB!important}
[data-testid="stSidebar"] *{color:#111827!important}
.stButton>button[kind="primary"]{background:#2563EB!important;color:#fff!important;border:none!important;border-radius:10px!important;font-weight:700!important;box-shadow:0 4px 14px rgba(37,99,235,0.35)!important}
.stButton>button[kind="primary"]:hover{background:#1D4ED8!important;transform:translateY(-2px)!important}
.stButton>button[kind="secondary"]{background:#fff!important;color:#1E40AF!important;border:2px solid #BFDBFE!important;border-radius:10px!important;font-weight:600!important}
label,.stTextInput label,.stSelectbox label,.stSlider label,.stMultiSelect label,.stCheckbox label span{color:#0F172A!important;font-weight:600!important;font-size:13px!important}
.stTextInput input,.stTextArea textarea,.stNumberInput input{background:#fff!important;border:2px solid #BFDBFE!important;border-radius:9px!important;color:#0F172A!important}
[data-testid="metric-container"]{background:#fff!important;border:1.5px solid #DBEAFE!important;border-radius:14px!important;box-shadow:0 2px 8px rgba(37,99,235,0.07)!important;padding:16px!important}
[data-testid="metric-container"] [data-testid="stMetricLabel"] p{color:#1E3A5F!important;font-size:12px!important;font-weight:600!important;text-transform:uppercase}
[data-testid="metric-container"] [data-testid="stMetricValue"] div{color:#0F172A!important;font-size:1.7rem!important;font-weight:800!important}
[data-baseweb="tab-list"]{background:#DBEAFE!important;border-radius:12px!important;padding:4px!important}
[data-baseweb="tab"]{color:#1E40AF!important;font-weight:600!important;border-radius:9px!important}
[aria-selected="true"][data-baseweb="tab"]{background:#fff!important;color:#1D4ED8!important;font-weight:700!important}
hr{border-color:#BFDBFE!important}
.auth-card{background:#fff;border:1.5px solid #E0EAFF;border-radius:18px;padding:36px 32px;max-width:440px;margin:0 auto}
.auth-title{font-size:1.6rem;font-weight:800;color:#0F172A;margin-bottom:6px}
.auth-sub{font-size:.9rem;color:#374151;margin-bottom:24px}
.hero-bar{background:linear-gradient(135deg,#060C1F,#0F1D4A 55%,#0C1A3A);border-radius:0 0 22px 22px;padding:36px 52px 40px;margin-bottom:28px;position:relative;overflow:hidden}
.hero-bar::before{content:'';position:absolute;top:-80px;right:-40px;width:420px;height:420px;background:radial-gradient(circle,rgba(37,99,235,0.3) 0%,transparent 65%)}
.hero-title{font-size:1.8rem;font-weight:800;color:#fff!important;margin-bottom:6px;position:relative}
.hero-sub-text{color:#CBD5E1!important;font-size:.93rem;margin:0;position:relative;font-weight:500}
.stat-card{background:#fff;border:1px solid #E0EAFF;border-radius:14px;padding:18px;text-align:center;transition:transform .2s}
.stat-card:hover{transform:translateY(-2px)}
.stat-num{font-size:1.5rem;font-weight:800;color:#2563EB}
.stat-label{font-size:.78rem;color:#6B7280;margin-top:3px}
.project-card{background:#fff;border:1.5px solid #E0EAFF;border-radius:14px;padding:18px 20px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;transition:border-color .15s}
.project-card:hover{border-color:#93C5FD}
.pill{display:inline-block;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}
.pill-done{background:#D1FAE5;color:#065F46}
.pill-pending{background:#FEF3C7;color:#92400E}
.pill-running{background:#DBEAFE;color:#1E40AF}
.pill-failed{background:#FEE2E2;color:#7F1D1D}
.insight-card{background:#fff;border:1px solid #E0EAFF;border-radius:12px;padding:16px 18px;margin-bottom:10px;border-left:4px solid #2563EB}
.insight-card.high{border-left-color:#DC2626;background:#FFF5F5}
.insight-card.med{border-left-color:#D97706;background:#FFFBEB}
.insight-card.low{border-left-color:#16A34A;background:#F0FDF4}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
for k, v in dict(token=None, user=None, logged_in=False,
                 page="login", active_project=None).items():
    if k not in st.session_state:
        st.session_state[k] = v

COLORS = ["#2563EB","#06B6D4","#F59E0B","#EF4444","#10B981","#8B5CF6","#EC4899","#14B8A6"]


# ─────────────────────────────────────────────
#  BACKEND STATUS INDICATOR
# ─────────────────────────────────────────────
def backend_status_badge():
    h = api.health_check()
    if h.get("status") == "ok":
        st.markdown("""<div style='font-size:11px;color:#16A34A;font-weight:600;
            padding:4px 0'>● Backend connected</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style='font-size:11px;color:#DC2626;font-weight:600;
            padding:4px 0'>● Backend offline — run: python run_me.py</div>""",
            unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  AUTH PAGES  (shown before login)
# ══════════════════════════════════════════════
if not st.session_state.logged_in:

    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        backend_status_badge()
        st.markdown("""
        <div class="auth-card">
          <div class="auth-title">🎯 SegmentIQ Pro™</div>
          <div class="auth-sub">AI-powered customer segmentation</div>
        </div>""", unsafe_allow_html=True)

        auth_tab1, auth_tab2 = st.tabs(["Sign In", "Create Account"])

        # ── LOGIN ────────────────────────────
        with auth_tab1:
            with st.form("login_form"):
                email    = st.text_input("Email", placeholder="you@company.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign In →", type="primary",
                                                   use_container_width=True)
            if submitted:
                if not email or not password:
                    st.warning("Enter email and password.")
                else:
                    try:
                        data = api.login(email, password)
                        st.session_state.token     = data["access_token"]
                        st.session_state.user      = data["user"]
                        st.session_state.logged_in = True
                        st.session_state.page      = "dashboard"
                        st.rerun()
                    except APIError as e:
                        st.error(str(e))

        # ── SIGNUP ───────────────────────────
        with auth_tab2:
            with st.form("signup_form"):
                s_name  = st.text_input("Full name",  placeholder="Arjun Kumar")
                s_user  = st.text_input("Username",   placeholder="arjun_k")
                s_email = st.text_input("Email",      placeholder="arjun@company.com")
                s_pass  = st.text_input("Password",   type="password",
                                        help="Minimum 6 characters")
                submitted2 = st.form_submit_button("Create Account →", type="primary",
                                                    use_container_width=True)
            if submitted2:
                if not all([s_email, s_user, s_pass]):
                    st.warning("Fill in all required fields.")
                else:
                    try:
                        data = api.signup(s_email, s_user, s_pass, s_name)
                        st.session_state.token     = data["access_token"]
                        st.session_state.user      = data["user"]
                        st.session_state.logged_in = True
                        st.session_state.page      = "dashboard"
                        st.rerun()
                    except APIError as e:
                        st.error(str(e))
    st.stop()


# ══════════════════════════════════════════════
#  NAVBAR  (shown after login)
# ══════════════════════════════════════════════
nb0, nb1, nb2, nb3, nb4 = st.columns([3, 1, 1, 1, 1])
with nb0:
    user = st.session_state.user
    st.markdown(f"""<div style='padding:12px 0;display:flex;align-items:center;gap:10px'>
        <span style='font-size:1.2rem;font-weight:800;color:#111827'>🎯 SegmentIQ</span>
        <span style='background:#2563EB;color:#fff;font-size:9px;font-weight:700;
          padding:2px 7px;border-radius:4px'>PRO</span>
        <span style='font-size:11px;color:#6B7280;margin-left:8px'>
          👤 {user.get("username","")}</span>
        </div>""", unsafe_allow_html=True)

for col, pg in zip([nb1, nb2, nb3], ["Dashboard", "New Project", "Predict"]):
    with col:
        if st.button(pg, key=f"nav_{pg}", use_container_width=True,
                     type="primary" if st.session_state.page == pg.lower().replace(" ","_") else "secondary"):
            st.session_state.page = pg.lower().replace(" ", "_")
            st.rerun()

with nb4:
    if st.button("Sign Out", use_container_width=True):
        for k in ["token","user","logged_in","active_project"]:
            st.session_state[k] = None if k != "logged_in" else False
        st.session_state.page = "login"
        st.rerun()
st.divider()


# ══════════════════════════════════════════════
#  DASHBOARD PAGE
# ══════════════════════════════════════════════
if st.session_state.page in ("dashboard", None):

    st.markdown("""
    <div class="hero-bar">
      <div style='position:relative;z-index:1'>
        <div class="hero-title">📊 Your Projects</div>
        <p class="hero-sub-text">Manage datasets, run segmentation, download results</p>
      </div>
    </div>""", unsafe_allow_html=True)

    # Load projects from backend
    try:
        projects = api.list_projects()
    except APIError as e:
        st.error(f"Could not load projects: {e}"); projects = []

    # Stats row
    done_count = sum(1 for p in projects if p["status"] == "done")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f"""<div class="stat-card"><div class="stat-num">{len(projects)}</div>
            <div class="stat-label">Total projects</div></div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""<div class="stat-card"><div class="stat-num">{done_count}</div>
            <div class="stat-label">Segmented</div></div>""", unsafe_allow_html=True)
    with s3:
        st.markdown(f"""<div class="stat-card"><div class="stat-num">{len(projects)-done_count}</div>
            <div class="stat-label">Pending</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not projects:
        st.markdown("""<div style='text-align:center;padding:48px 20px;background:#fff;
            border-radius:14px;border:1.5px dashed #BFDBFE'>
            <div style='font-size:2.5rem'>📁</div>
            <div style='font-weight:700;color:#0F172A;margin:10px 0 6px'>No projects yet</div>
            <div style='color:#6B7280;font-size:.9rem'>Click "New Project" to upload a CSV and run segmentation</div>
            </div>""", unsafe_allow_html=True)
    else:
        for p in projects:
            pill_cls = {"done":"pill-done","pending":"pill-pending",
                        "running":"pill-running","failed":"pill-failed"}.get(p["status"],"pill-pending")
            c1, c2, c3, c4 = st.columns([3, 1.5, 1, 1])
            with c1:
                st.markdown(f"""<div style='padding:14px 0'>
                    <div style='font-weight:700;color:#0F172A;font-size:.95rem'>{p["name"]}</div>
                    <div style='font-size:.8rem;color:#6B7280;margin-top:2px'>
                      {p.get("sector","—")} · {p.get("n_rows",0):,} rows · {p.get("filename","")}
                    </div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div style='padding:20px 0'><span class='pill {pill_cls}'>{p['status'].upper()}</span></div>",
                            unsafe_allow_html=True)
            with c3:
                if p["status"] == "done":
                    if st.button("📊 View", key=f"view_{p['id']}", use_container_width=True):
                        st.session_state.active_project = p["id"]
                        st.session_state.page = "results"
                        st.rerun()
                else:
                    if st.button("▶️ Run", key=f"run_{p['id']}", use_container_width=True, type="primary"):
                        st.session_state.active_project = p["id"]
                        st.session_state.page = "run_seg"
                        st.rerun()
            with c4:
                if st.button("🗑️", key=f"del_{p['id']}", use_container_width=True):
                    try:
                        api.delete_project(p["id"])
                        st.success(f"Deleted '{p['name']}'")
                        st.rerun()
                    except APIError as e:
                        st.error(str(e))
            st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  NEW PROJECT PAGE
# ══════════════════════════════════════════════
elif st.session_state.page == "new_project":

    st.markdown("""<div class="hero-bar">
      <div style='position:relative;z-index:1'>
        <div class="hero-title">📁 Upload a Dataset</div>
        <p class="hero-sub-text">Upload any CSV or Excel file — sector and features are auto-detected</p>
      </div></div>""", unsafe_allow_html=True)

    col_form, col_info = st.columns([1.2, 1])
    with col_form:
        with st.form("upload_form"):
            proj_name = st.text_input("Project name *", placeholder="Q3 Customer Analysis")
            proj_desc = st.text_area("Description (optional)", height=80,
                                     placeholder="Retail customer data for churn analysis...")
            uploaded  = st.file_uploader("Upload CSV or Excel *",
                                          type=["csv","xlsx","xls"],
                                          label_visibility="visible")
            submitted = st.form_submit_button("Upload & Create Project →",
                                               type="primary", use_container_width=True)

        if submitted:
            if not proj_name:
                st.warning("Enter a project name.")
            elif not uploaded:
                st.warning("Please upload a file.")
            else:
                with st.spinner("Uploading..."):
                    try:
                        result = api.create_project(
                            name=proj_name,
                            file_bytes=uploaded.read(),
                            filename=uploaded.name,
                            description=proj_desc,
                        )
                        st.success(f"✅ Project created! ID: {result['id']} · Sector detected: **{result['sector']}**")
                        st.session_state.active_project = result["id"]
                        st.session_state.page = "run_seg"
                        st.rerun()
                    except APIError as e:
                        st.error(str(e))

    with col_info:
        st.markdown("""
        <div style='background:#fff;border:1.5px solid #DBEAFE;border-radius:14px;padding:22px'>
          <div style='font-weight:700;color:#0F172A;margin-bottom:12px'>What happens after upload</div>
          <div style='font-size:.85rem;color:#374151;line-height:1.8'>
            ✅ File is sent to the FastAPI backend<br>
            ✅ Sector auto-detected from column names<br>
            ✅ Shape (rows × columns) stored in DB<br>
            ✅ You're taken to the segmentation config<br><br>
            <b>Supported formats:</b> CSV, XLSX, XLS<br>
            <b>Works with:</b> any column names, string numbers like $1,200 or 45%
          </div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  RUN SEGMENTATION PAGE
# ══════════════════════════════════════════════
elif st.session_state.page == "run_seg":

    pid = st.session_state.active_project
    if not pid:
        st.warning("No project selected."); st.stop()

    try:
        project = api.get_project(pid)
    except APIError as e:
        st.error(str(e)); st.stop()

    st.markdown(f"""<div class="hero-bar">
      <div style='position:relative;z-index:1'>
        <div class="hero-title">⚙️ Configure Segmentation</div>
        <p class="hero-sub-text">{project["name"]} · {project.get("n_rows",0):,} rows · {project.get("sector","—")}</p>
      </div></div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        n_seg  = st.slider("Number of segments (K)", 2, 8, 4)
        n_nbrs = st.slider("KNN neighbours", 3, 15, 5)
        st.caption("Features are auto-detected from your data. Leave blank to use all.")
        feat_input = st.text_input("Override features (comma-separated, optional)",
                                    placeholder="recency_days, total_spent, frequency")
    with c2:
        st.markdown(f"""
        <div style='background:#fff;border:1.5px solid #DBEAFE;border-radius:14px;padding:20px;margin-top:28px'>
          <div style='font-weight:700;margin-bottom:10px'>What will happen</div>
          <div style='font-size:.84rem;color:#374151;line-height:1.8'>
            1. Backend loads your uploaded file<br>
            2. Auto-detects numeric/string-number features<br>
            3. Runs KMeans to seed {n_seg} cluster labels<br>
            4. Trains KNN classifier on those labels<br>
            5. Computes churn risk per segment<br>
            6. Saves everything to the database
          </div>
        </div>""", unsafe_allow_html=True)

    if st.button("🚀 Run Segmentation", type="primary", use_container_width=True):
        features = [f.strip() for f in feat_input.split(",") if f.strip()] or None
        with st.spinner("Running segmentation on backend... (this may take 30–60 seconds)"):
            try:
                result = api.run_segmentation(pid, n_seg, n_nbrs, features)
                st.success(f"✅ Done! Silhouette score: **{result.get('silhouette_score', 0):.3f}**")
                st.session_state.page = "results"
                st.rerun()
            except APIError as e:
                st.error(f"Segmentation failed: {e}")


# ══════════════════════════════════════════════
#  RESULTS PAGE
# ══════════════════════════════════════════════
elif st.session_state.page == "results":

    pid = st.session_state.active_project
    if not pid:
        st.warning("No project selected."); st.stop()

    try:
        summary = api.get_summary(pid)
        result  = api.get_result(pid)
    except APIError as e:
        st.error(str(e)); st.stop()

    st.markdown(f"""<div class="hero-bar">
      <div style='position:relative;z-index:1'>
        <div class="hero-title">📈 {summary["project_name"]}</div>
        <p class="hero-sub-text">{summary.get("sector","—")} · {summary["n_customers"]:,} customers · {summary["n_segments"]} segments</p>
      </div></div>""", unsafe_allow_html=True)

    # KPIs
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Customers",      f"{summary['n_customers']:,}")
    k2.metric("Segments",       summary["n_segments"])
    k3.metric("Silhouette",     f"{summary.get('silhouette_score', 0):.3f}")
    k4.metric("Top Churn Risk", summary.get("top_churn_segment","—"))

    t1, t2, t3 = st.tabs(["📊 Charts", "🤖 Insights", "📋 Export"])

    with t1:
        counts = summary.get("segment_counts", {})
        churn  = summary.get("churn_risk", {})

        if counts:
            cc1, cc2 = st.columns(2)
            with cc1:
                fig_pie = go.Figure(go.Pie(
                    labels=list(counts.keys()),
                    values=list(counts.values()),
                    marker=dict(colors=COLORS[:len(counts)]),
                    hole=0.45,
                    textfont=dict(size=12)
                ))
                fig_pie.update_layout(
                    height=320, margin=dict(t=20,b=20,l=10,r=10),
                    title=dict(text="Segment distribution", font=dict(size=14,color="#0F172A")),
                    plot_bgcolor="#fff", paper_bgcolor="#fff",
                    legend=dict(font=dict(color="#374151"))
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with cc2:
                if churn:
                    segs   = list(churn.keys())
                    risks  = [v * 100 for v in churn.values()]
                    colors = ["#EF4444" if r > 65 else "#F59E0B" if r > 40 else "#22C55E" for r in risks]
                    fig_ch = go.Figure(go.Bar(
                        x=risks, y=segs, orientation="h",
                        marker=dict(color=colors),
                        text=[f"{r:.0f}%" for r in risks],
                        textposition="inside",
                        textfont=dict(color="#fff", size=12),
                    ))
                    fig_ch.update_layout(
                        height=320, margin=dict(t=20,b=30,l=10,r=20),
                        title=dict(text="Churn risk %", font=dict(size=14,color="#0F172A")),
                        plot_bgcolor="#FAFAFA", paper_bgcolor="#fff",
                        xaxis=dict(title="Risk %", color="#374151",
                                   tickfont=dict(color="#374151"),
                                   title_font=dict(color="#374151")),
                        yaxis=dict(color="#374151", tickfont=dict(color="#0F172A")),
                    )
                    st.plotly_chart(fig_ch, use_container_width=True)

    with t2:
        churn = summary.get("churn_risk", {})
        stats = summary.get("segment_stats", {})
        for seg, risk in sorted(churn.items(), key=lambda x: -x[1]):
            pct = risk * 100
            cls = "high" if pct > 65 else "med" if pct > 40 else "low"
            icon = "⚠️" if pct > 65 else "🔶" if pct > 40 else "✅"
            seg_stat = stats.get(seg, {})
            vals_html = " &nbsp;·&nbsp; ".join([
                f"Avg <b>{k}</b>: {v:.1f}"
                for k, v in list(seg_stat.items())[:3]
            ])
            count = summary.get("segment_counts", {}).get(seg, 0)
            st.markdown(f"""
            <div class="insight-card {cls}">
              <div style='font-size:.88rem;font-weight:800;color:#0F172A;margin-bottom:5px'>
                {seg} <span style='font-weight:400;font-size:.8rem;color:#6B7280'>
                  · {count:,} customers · {icon} {pct:.0f}% churn risk</span>
              </div>
              <div style='font-size:.85rem;color:#1E293B'>{vals_html}</div>
            </div>""", unsafe_allow_html=True)

    with t3:
        st.markdown("#### Download segmented dataset")
        st.caption("Full CSV with Segment label and churn risk % per customer")
        if st.button("📄 Generate & Download CSV", type="primary", use_container_width=True):
            with st.spinner("Fetching from backend..."):
                try:
                    csv_bytes = api.download_csv(pid)
                    st.download_button(
                        "⬇️ Download CSV",
                        csv_bytes,
                        file_name=f"segmentiq_project_{pid}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                except APIError as e:
                    st.error(str(e))


# ══════════════════════════════════════════════
#  PREDICT PAGE
# ══════════════════════════════════════════════
elif st.session_state.page == "predict":

    st.markdown("""<div class="hero-bar">
      <div style='position:relative;z-index:1'>
        <div class="hero-title">🔮 Predict Customer Segment</div>
        <p class="hero-sub-text">Enter any customer's feature values — the trained KNN model classifies them instantly</p>
      </div></div>""", unsafe_allow_html=True)

    # Pick a project
    try:
        projects = [p for p in api.list_projects() if p["status"] == "done"]
    except APIError as e:
        st.error(str(e)); st.stop()

    if not projects:
        st.info("No segmented projects yet. Upload a CSV and run segmentation first.")
        st.stop()

    proj_options = {f"{p['name']} (ID {p['id']})": p["id"] for p in projects}
    chosen_label = st.selectbox("Select project", list(proj_options.keys()))
    chosen_pid   = proj_options[chosen_label]

    # Get features for that project
    try:
        result = api.get_result(chosen_pid)
        features = result.get("features_used", [])
    except APIError as e:
        st.error(str(e)); st.stop()

    if not features:
        st.warning("No feature info for this project. Re-run segmentation.")
        st.stop()

    st.markdown(f"**Enter values for {len(features)} features:**")
    with st.form("predict_form"):
        n_col = min(3, len(features))
        cols  = st.columns(n_col)
        inputs = {}
        for i, feat in enumerate(features):
            with cols[i % n_col]:
                inputs[feat] = st.number_input(feat, value=0.0, step=0.01)
        submitted = st.form_submit_button("🔮 Predict Segment", type="primary",
                                           use_container_width=True)

    if submitted:
        with st.spinner("Asking the backend..."):
            try:
                pred = api.predict_customer(chosen_pid, inputs)
                seg   = pred["segment"]
                conf  = pred["confidence"] * 100
                churn = pred["churn_risk"] * 100
                churn_color = "#EF4444" if churn > 65 else "#F59E0B" if churn > 40 else "#22C55E"
                churn_icon  = "⚠️ HIGH" if churn > 65 else "🔶 MEDIUM" if churn > 40 else "✅ LOW"

                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#EFF6FF,#DBEAFE);
                  border:2px solid #93C5FD;border-radius:18px;
                  padding:32px;text-align:center;margin-top:16px'>
                  <div style='font-size:.78rem;font-weight:700;color:#1E40AF;
                    text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px'>
                    Predicted Segment</div>
                  <div style='font-size:2rem;font-weight:800;color:#1D4ED8;
                    margin-bottom:6px'>{seg}</div>
                  <div style='font-size:.95rem;font-weight:600;color:#3B82F6'>
                    {conf:.1f}% confidence</div>
                  <div style='margin-top:14px;font-size:.9rem;font-weight:600'>
                    Churn Risk:
                    <span style='color:{churn_color}'>{churn_icon} ({churn:.0f}%)</span>
                  </div>
                </div>""", unsafe_allow_html=True)

                # Probability bars
                st.markdown("<br>**Probability breakdown:**", unsafe_allow_html=True)
                for seg_name, prob in sorted(pred["all_probs"].items(),
                                              key=lambda x: -x[1]):
                    pct = round(prob * 100, 1)
                    color = "#2563EB" if seg_name == seg else "#CBD5E1"
                    st.markdown(f"""
                    <div style='margin-bottom:8px'>
                      <div style='display:flex;justify-content:space-between;
                        font-size:12px;margin-bottom:3px'>
                        <span style='font-weight:{"700" if seg_name==seg else "400"};
                          color:#0F172A'>{seg_name}</span>
                        <span style='font-weight:600;color:{color}'>{pct}%</span>
                      </div>
                      <div style='background:#E0EAFF;border-radius:99px;height:7px'>
                        <div style='width:{pct}%;background:{color};
                          border-radius:99px;height:7px'></div>
                      </div>
                    </div>""", unsafe_allow_html=True)

            except APIError as e:
                st.error(str(e))
