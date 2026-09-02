
import zipfile
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="FITX UX Intelligence", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ---------- Safe, targeted styling ----------
st.markdown("""
<style>
.stApp { background: #f6f8fb; }
.block-container { max-width: 1500px; padding-top: 1.3rem; padding-bottom: 2.5rem; }
[data-testid="stSidebar"] { background: #111827; }
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #f9fafb !important; }
[data-testid="stSidebar"] [data-baseweb="radio"] label { color: #f9fafb !important; }
.hero { padding: 1.35rem 1.5rem; border-radius: 18px; background: linear-gradient(135deg,#111827,#25344d); margin-bottom: 1rem; box-shadow: 0 10px 28px rgba(15,23,42,.10); }
.hero h1 { margin:0; color:#fff !important; font-size:2.05rem; }
.hero p { margin:.45rem 0 0; color:#dbeafe !important; font-size:1rem; }
.section-title { color:#111827 !important; font-weight:800; font-size:1.25rem; margin:.5rem 0 .55rem; }
[data-testid="stMetric"] { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:1rem; }
[data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] { color:#111827 !important; }
.main-copy { color:#344054 !important; }
</style>
""", unsafe_allow_html=True)

DATA_DIR = "data"
FILES = sorted(glob.glob(DATA_DIR + "/*.xlsx"))

@st.cache_data(show_spinner=False)
def load_raw(files):
    frames = []
    for path in files:
        try:
            df = pd.read_excel(path, engine="openpyxl")
            df["source_file"] = path.split("/")[-1]
            frames.append(df)
        except Exception as exc:
            st.error(f"Could not read {path}: {exc}")
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True, sort=False)
    out["timestamp"] = pd.to_datetime(out.get("timestamp"), errors="coerce")
    if "device" in out.columns:
        out["device"] = out["device"].astype(str).str.title()
    return out

raw = load_raw(FILES)
if raw.empty:
    st.error("No FITX datasets were found. Keep the provided data folder beside app.py.")
    st.stop()

# ---------- Sidebar navigation and filters (NO UPLOAD OPTION) ----------
with st.sidebar:
    st.markdown("# FITX Analytics")
    st.caption("Behavior & UX intelligence")
    st.divider()
    page = st.radio("Navigation", [
        "Executive Overview", "Audience & Devices", "Navigation & Sankey",
        "Conversion", "Forms & Errors", "Engagement", "Exit & Scroll", "Raw Data"
    ], index=0)
    st.divider()
    valid_dates = raw["timestamp"].dropna()
    if len(valid_dates):
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()
        date_value = st.date_input("Date range", (min_date, max_date), min_value=min_date, max_value=max_date)
        if isinstance(date_value, tuple) and len(date_value) == 2:
            start_date, end_date = date_value
            mask = raw["timestamp"].dt.date.between(start_date, end_date)
            view = raw.loc[mask].copy()
        else:
            view = raw.copy()
    else:
        view = raw.copy()
    devices = sorted([x for x in view.get("device", pd.Series(dtype=str)).dropna().unique().tolist()])
    device_pick = st.multiselect("Device", devices, default=devices)
    if device_pick and "device" in view.columns:
        view = view[view["device"].isin(device_pick)]
    st.caption(f"{len(FILES)} source files • {len(view):,} filtered events")

# ---------- Helpers ----------
def count_users(df):
    return int(df["user_id"].nunique()) if "user_id" in df.columns else 0

def count_sessions(df):
    return int(df["session_id"].nunique()) if "session_id" in df.columns else 0

def metric_event(df, event_name):
    if "event" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["event"].astype(str).eq(event_name)].copy()

def plot_style(fig, height=420, title=None):
    if title:
        fig.update_layout(title=title)
    fig.update_layout(
        height=height, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(color="#101828", family="Arial", size=13),
        title_font=dict(color="#101828", size=18),
        margin=dict(l=20, r=20, t=60, b=25),
        legend=dict(font=dict(color="#101828")),
        hoverlabel=dict(bgcolor="#111827", font_color="#ffffff")
    )
    fig.update_xaxes(tickfont=dict(color="#344054"), title_font=dict(color="#101828"), gridcolor="#e5e7eb")
    fig.update_yaxes(tickfont=dict(color="#344054"), title_font=dict(color="#101828"), gridcolor="#e5e7eb")
    return fig

def top_counts(df, col, n=10):
    if col not in df.columns or df.empty:
        return pd.DataFrame(columns=[col, "Count"])
    x = df[col].fillna("Unknown").astype(str).value_counts().head(n).reset_index()
    x.columns = [col, "Count"]
    return x

# ---------- Header ----------
st.markdown('''<div class="hero"><h1>FITX UX Intelligence Dashboard</h1><p>Interactive analysis of real FITX event logs: acquisition, navigation, conversion, forms, engagement, exits and user behavior.</p></div>''', unsafe_allow_html=True)

# ---------- Executive ----------
if page == "Executive Overview":
    st.markdown('<div class="section-title">Performance snapshot</div>', unsafe_allow_html=True)
    page_views = metric_event(view, "page_view")
    cta = metric_event(view, "cta_click")
    btn = metric_event(view, "button_click")
    bookings = metric_event(view, "class_booking")
    submitted = metric_event(view, "form_submitted")
    errors = metric_event(view, "validation_error")
    exits = metric_event(view, "page_exit")
    h = st.columns(6)
    metrics = [
        ("Users", count_users(view)), ("Sessions", count_sessions(view)), ("Events", len(view)),
        ("Page views", len(page_views)), ("CTA clicks", len(cta)), ("Bookings", len(bookings))
    ]
    for col, (label, value) in zip(h, metrics):
        col.metric(label, f"{value:,}")

    st.markdown('<div class="section-title">Core signals</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    repeat_users = view.groupby("user_id")["session_id"].nunique() if "user_id" in view.columns else pd.Series(dtype=int)
    repeat_rate = float((repeat_users > 1).mean() * 100) if len(repeat_users) else 0
    with a:
        st.metric("Repeat-user rate", f"{repeat_rate:.1f}%")
        st.caption("Users with more than one observed session in the supplied event logs.")
    with b:
        booking_rate = (len(bookings) / max(count_users(page_views), 1)) * 100
        st.metric("Booking events / viewed users", f"{booking_rate:.1f}%")
        st.caption("Event-volume ratio, not a unique-user conversion rate.")
    with c:
        error_rate = (len(errors) / max(len(metric_event(view, "form_started")), 1)) * 100
        st.metric("Validation errors / form starts", f"{error_rate:.1f}%")
        st.caption("Useful friction signal from the actual logs.")

    left, right = st.columns(2)
    with left:
        x = top_counts(cta, "cta", 10)
        if len(x):
            st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="cta", orientation="h", text="Count"), title="Top CTA clicks"), use_container_width=True)
    with right:
        x = top_counts(bookings, "booking_status", 10)
        if len(x):
            st.plotly_chart(plot_style(px.pie(x, names="booking_status", values="Count", hole=.52), title="Booking status mix"), use_container_width=True)

    st.markdown('<div class="section-title">Top pages</div>', unsafe_allow_html=True)
    x = top_counts(page_views, "page", 12)
    if len(x):
        st.dataframe(x, use_container_width=True, hide_index=True)

# ---------- Audience ----------
elif page == "Audience & Devices":
    st.markdown('<div class="section-title">Audience and device behavior</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        x = top_counts(view, "device", 10)
        if len(x): st.plotly_chart(plot_style(px.pie(x, names="device", values="Count", hole=.55), title="Event volume by device"), use_container_width=True)
    with b:
        x = top_counts(view, "browser", 10)
        if len(x): st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="browser", orientation="h"), title="Browser distribution"), use_container_width=True)
    c, d = st.columns(2)
    with c:
        x = top_counts(view, "referrer", 10)
        if len(x): st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="referrer", orientation="h"), title="Top referrers"), use_container_width=True)
    with d:
        x = top_counts(view, "language", 10)
        if len(x): st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="language", orientation="h"), title="Language mix"), use_container_width=True)

# ---------- Navigation & Sankey ----------
elif page == "Navigation & Sankey":
    nav = metric_event(view, "page_navigation")
    st.markdown('<div class="section-title">Navigation pathways</div>', unsafe_allow_html=True)
    if len(nav):
        nav = nav.dropna(subset=["from_page", "to_page"]).copy()
        agg = nav.groupby(["from_page", "to_page"], as_index=False).agg(Transitions=("session_id", "size"), Users=("user_id", "nunique"))
        top_n = st.slider("Number of flows", 5, min(30, max(5, len(agg))), min(15, len(agg)))
        top = agg.sort_values("Transitions", ascending=False).head(top_n)
        labels = pd.unique(pd.concat([top["from_page"], top["to_page"]], ignore_index=True)).tolist()
        idx = {v:i for i,v in enumerate(labels)}
        fig = go.Figure(go.Sankey(node=dict(label=labels, pad=18, thickness=20), link=dict(
            source=[idx[x] for x in top["from_page"]], target=[idx[x] for x in top["to_page"]], value=top["Transitions"].tolist(),
            customdata=top["Users"].tolist(), hovertemplate="%{source.label} → %{target.label}<br>Transitions: %{value}<br>Users: %{customdata}<extra></extra>")))
        fig.update_layout(title="Top navigation flow Sankey")
        st.plotly_chart(plot_style(fig, 600), use_container_width=True)
        top["Flow"] = top["from_page"].astype(str) + " → " + top["to_page"].astype(str)
        st.plotly_chart(plot_style(px.bar(top.sort_values("Transitions"), x="Transitions", y="Flow", orientation="h", text="Transitions"), title="Top page-to-page transitions"), use_container_width=True)
        st.dataframe(top[["Flow", "Transitions", "Users"]], use_container_width=True, hide_index=True)
    else:
        st.info("No page_navigation events match the selected filters.")

# ---------- Conversion ----------
elif page == "Conversion":
    st.markdown('<div class="section-title">Conversion and outcome events</div>', unsafe_allow_html=True)
    b = metric_event(view, "class_booking")
    s = metric_event(view, "membership_selection")
    sub = metric_event(view, "form_submitted")
    a, c, d = st.columns(3)
    a.metric("Class booking events", f"{len(b):,}")
    c.metric("Membership selections", f"{len(s):,}")
    d.metric("Successful form submissions", f"{len(sub[sub.get('submission_status', pd.Series(index=sub.index)).astype(str).str.lower().eq('success')]):,}")

    left, right = st.columns(2)
    with left:
        if len(b) and "class" in b.columns:
            x = top_counts(b, "class", 10)
            st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="class", orientation="h"), title="Most booked classes"), use_container_width=True)
    with right:
        if len(s) and "membership" in s.columns:
            x = top_counts(s, "membership", 10)
            st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="membership", orientation="h"), title="Membership selection volume"), use_container_width=True)

# ---------- Forms ----------
elif page == "Forms & Errors":
    st.markdown('<div class="section-title">Form friction</div>', unsafe_allow_html=True)
    started = metric_event(view, "form_started")
    aband = metric_event(view, "form_abandonment")
    err = metric_event(view, "validation_error")
    sub = metric_event(view, "form_submitted")
    a,b,c,d = st.columns(4)
    a.metric("Forms started", f"{len(started):,}")
    b.metric("Forms submitted", f"{len(sub):,}")
    c.metric("Forms abandoned", f"{len(aband):,}")
    d.metric("Validation errors", f"{len(err):,}")
    left, right = st.columns(2)
    with left:
        x = top_counts(err, "error_type", 10)
        if len(x): st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="error_type", orientation="h", text="Count"), title="Validation error types"), use_container_width=True)
    with right:
        x = top_counts(aband, "abandonment_reason", 10)
        if len(x): st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="abandonment_reason", orientation="h"), title="Form abandonment reasons"), use_container_width=True)
    if len(started) and "form" in started.columns:
        st.dataframe(started["form"].value_counts().reset_index().rename(columns={"form":"Form", "count":"Starts"}), use_container_width=True, hide_index=True)

# ---------- Engagement ----------
elif page == "Engagement":
    st.markdown('<div class="section-title">Interaction engagement</div>', unsafe_allow_html=True)
    events_to_compare = ["cta_click", "button_click", "hover", "double_click", "right_click", "mouse_movement", "filter_apply", "exercise_library_loaded", "mobile_menu"]
    rows = []
    for e in events_to_compare:
        q = metric_event(view, e)
        rows.append((e, len(q), count_users(q)))
    summary = pd.DataFrame(rows, columns=["Event", "Events", "Users"]).sort_values("Events", ascending=False)
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.plotly_chart(plot_style(px.bar(summary.sort_values("Events"), x="Events", y="Event", orientation="h", text="Events"), title="Interaction event volume"), use_container_width=True)
    hover = metric_event(view, "hover")
    if len(hover) and "hover_duration_ms" in hover.columns:
        h = pd.to_numeric(hover["hover_duration_ms"], errors="coerce").dropna()
        if len(h):
            c1,c2 = st.columns(2)
            c1.metric("Median hover duration", f"{h.median():,.0f} ms")
            c2.metric("Average hover duration", f"{h.mean():,.0f} ms")

# ---------- Exit & Scroll ----------
elif page == "Exit & Scroll":
    st.markdown('<div class="section-title">Exit behavior and scroll depth</div>', unsafe_allow_html=True)
    exits = metric_event(view, "page_exit")
    scroll = metric_event(view, "scroll_depth")
    left,right = st.columns(2)
    with left:
        x = top_counts(exits, "page", 12)
        if len(x): st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="page", orientation="h"), title="Exit events by page"), use_container_width=True)
    with right:
        x = top_counts(exits, "exit_reason", 10)
        if len(x): st.plotly_chart(plot_style(px.bar(x.sort_values("Count"), x="Count", y="exit_reason", orientation="h"), title="Exit reasons"), use_container_width=True)
    if len(scroll) and "scroll_percent" in scroll.columns:
        x = scroll.copy(); x["scroll_percent"] = pd.to_numeric(x["scroll_percent"], errors="coerce"); x=x.dropna()
        x["Depth"] = x["scroll_percent"].astype(int).astype(str)+"%"
        agg=x.groupby("Depth",as_index=False).size().rename(columns={"size":"Events"})
        order={f"{i}%":i for i in sorted(x["scroll_percent"].astype(int).unique())}
        agg["sort"] = agg["Depth"].map(order); agg=agg.sort_values("sort")
        st.plotly_chart(plot_style(px.line(agg, x="Depth", y="Events", markers=True), title="Scroll-depth event volume"), use_container_width=True)

# ---------- Raw Data ----------
elif page == "Raw Data":
    st.markdown('<div class="section-title">Raw event explorer</div>', unsafe_allow_html=True)
    st.caption("The dashboard is locked to the supplied FITX event logs. There is no upload control.")
    event_choices = sorted(view["event"].dropna().astype(str).unique().tolist()) if "event" in view.columns else []
    event_pick = st.selectbox("Event type", ["All events"] + event_choices)
    df = view if event_pick == "All events" else view[view["event"].astype(str).eq(event_pick)]
    st.write(f"**{len(df):,} rows × {df.shape[1]:,} columns**")
    st.dataframe(df.head(5000), use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered CSV", csv, file_name="fitx_filtered_events.csv", mime="text/csv")

st.divider()
st.caption(f"FITX UX Intelligence • {len(FILES)} supplied raw datasets • {len(raw):,} total event rows")
