"""Streamlit frontend for the Job Boards Tracker API.

A thin UI over the FastAPI backend: browse/filter jobs, manage tracked companies,
trigger ingestion, and track applications. Set API_BASE_URL to point at the backend
(defaults to a locally running server).

Run with:  uv run streamlit run streamlit_app.py
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
PAGE_SIZE = 25

# Backend timestamps are naive UTC (Postgres now()); display them in US Eastern.
EASTERN = ZoneInfo("America/New_York")

SECTORS = ["tech", "finance", "pharma", "cybersecurity", "robotics", "healthcare"]
SIZES = ["startup", "small", "medium", "big"]
STATUSES = ["unapplied", "applied", "rejected", "offer"]

st.set_page_config(page_title="Job Boards Tracker", layout="wide")


# ── API client ────────────────────────────────────────────────────────────────


def _request(method: str, path: str, **kwargs):
    """Call the API. Stop the app on connection errors; surface HTTP errors inline."""
    try:
        resp = httpx.request(method, f"{API_BASE_URL}{path}", timeout=30, **kwargs)
    except httpx.RequestError as exc:
        st.error(f"Cannot reach the API at {API_BASE_URL} — is the backend running? ({exc})")
        st.stop()
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        st.error(f"{method} {path} failed ({resp.status_code}): {detail}")
        return None
    return resp.json() if resp.content else {}


def api_get(path, params=None):
    return _request("GET", path, params=params)


def api_post(path, json=None):
    return _request("POST", path, json=json)


def api_patch(path, json=None):
    return _request("PATCH", path, json=json)


def api_delete(path):
    return _request("DELETE", path)


# ── helpers ───────────────────────────────────────────────────────────────────


def fmt_dt(value):
    """Format a backend ISO datetime in US Eastern, e.g. '9:14 AM 08-June-2026'."""
    if not value:
        return "—"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(EASTERN).strftime("%-I:%M %p %d-%B-%Y")


def render_pager(key: str, page: dict):
    """Prev/Next controls bound to st.session_state[f'{key}_offset']."""
    offset_key = f"{key}_offset"
    total, offset, limit = page["total"], page["offset"], page["limit"]
    page_num = offset // limit + 1
    total_pages = max(1, (total + limit - 1) // limit)

    prev_col, info_col, next_col = st.columns([1, 4, 1])
    with prev_col:
        if st.button("‹ Prev", key=f"{key}_prev", disabled=offset <= 0):
            st.session_state[offset_key] = max(0, offset - limit)
            st.rerun()
    with info_col:
        st.caption(f"Page {page_num} of {total_pages} · {total} total")
    with next_col:
        if st.button("Next ›", key=f"{key}_next", disabled=not page["has_more"]):
            st.session_state[offset_key] = offset + limit
            st.rerun()


def reset_offset_on_change(key: str, signature):
    """Reset a tab's pagination offset to 0 when its filters change."""
    sig_key = f"{key}_filter_sig"
    if st.session_state.get(sig_key) != signature:
        st.session_state[sig_key] = signature
        st.session_state[f"{key}_offset"] = 0


for _offset_key in ("jobs_offset", "companies_offset", "applications_offset"):
    st.session_state.setdefault(_offset_key, 0)


# ── header: stats + ingest ────────────────────────────────────────────────────

stats = api_get("/stats") or {"total_jobs": 0, "total_companies": 0, "last_sync": None}

title_col, ingest_col = st.columns([4, 1])
with title_col:
    st.title("📋 Job Boards Tracker")
    sync_label = (
        f"{fmt_dt(stats['last_sync'])} ET" if stats["last_sync"] else "never"
    )
    st.caption(
        f"{stats['total_jobs']} jobs · {stats['total_companies']} companies · "
        f"last sync {sync_label}"
    )
with ingest_col:
    if st.button("⟳ Ingest all", type="primary", use_container_width=True):
        result = api_post("/ingest/all")
        if result is not None:
            st.success(
                f"Ingested {result['jobs_fetched']} jobs from "
                f"{result['successful_companies']} companies "
                f"({len(result['failed_companies'])} failed)."
            )
            st.rerun()


# ── sidebar filters (GET /jobs query params) ──────────────────────────────────

company_list = api_get("/companies", params={"limit": 500}) or {"items": []}
company_names = [c["company"] for c in company_list["items"]]
company_options = ["All companies", *company_names]


def clear_filters():
    st.session_state["filter_company"] = "All companies"
    st.session_state["filter_status"] = "Any"
    st.session_state["filter_size"] = "Any size"
    st.session_state["filter_sector"] = "Any sector"
    st.session_state["jobs_offset"] = 0


# Drop a stale selection (e.g. a company that was just deleted) back to the default.
if st.session_state.get("filter_company") not in company_options:
    st.session_state["filter_company"] = "All companies"

with st.sidebar:
    st.header("Filters")
    st.button("Clear filters", on_click=clear_filters, use_container_width=True)
    f_company = st.selectbox("Company", company_options, key="filter_company")
    f_status = st.selectbox(
        "Application status", ["Any", "Not tracked", *STATUSES], key="filter_status"
    )
    f_size = st.selectbox("Company size", ["Any size", *SIZES], key="filter_size")
    f_sector = st.selectbox(
        "Industry / sector", ["Any sector", *SECTORS], key="filter_sector"
    )
    st.caption(
        "Title search, location, and remote filtering aren't backend filters yet — "
        "shown as columns only."
    )

reset_offset_on_change("jobs", (f_company, f_status, f_size, f_sector))

job_params = {"limit": PAGE_SIZE, "offset": st.session_state.jobs_offset}
if f_company != "All companies":
    job_params["company"] = f_company
if f_status == "Not tracked":
    job_params["tracked"] = False
elif f_status != "Any":
    job_params["application_status"] = f_status
if f_size != "Any size":
    job_params["size"] = f_size
if f_sector != "Any sector":
    job_params["sector"] = f_sector


# ── tabs ──────────────────────────────────────────────────────────────────────

jobs_tab, companies_tab, applications_tab = st.tabs(
    ["Jobs", "Companies", "Applications"]
)


with jobs_tab:
    page = api_get("/jobs", params=job_params) or {
        "items": [], "total": 0, "offset": 0, "limit": PAGE_SIZE, "has_more": False
    }
    render_pager("jobs", page)

    header = st.columns([3, 2, 2, 1.5, 1.5, 1])
    for col, label in zip(
        header, ["Title", "Company", "Location", "Applied?", "", ""]
    ):
        col.markdown(f"**{label}**")

    for job in page["items"]:
        title, company, location, status, track, remove = st.columns(
            [3, 2, 2, 1.5, 1.5, 1]
        )
        title.markdown(f"[{job['title']}]({job['url']})")
        company.write(job["company"])
        location.write(job.get("location") or "—")
        status.write(job.get("application_status") or "—")
        if job.get("application_status") is None:
            if track.button("Track", key=f"track_{job['id']}"):
                created = api_post(
                    "/applications",
                    json={"job_posting_id": job["id"], "status": "unapplied"},
                )
                if created is not None:
                    st.rerun()
        if remove.button("✕", key=f"deljob_{job['id']}", help="Remove job"):
            if api_delete(f"/jobs/{job['id']}") is not None:
                st.rerun()


with companies_tab:
    page = api_get(
        "/companies",
        params={"limit": PAGE_SIZE, "offset": st.session_state.companies_offset},
    ) or {"items": [], "total": 0, "offset": 0, "limit": PAGE_SIZE, "has_more": False}
    render_pager("companies", page)

    header = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1])
    for col, label in zip(
        header, ["Company", "Source", "Board", "Sector", "Size", ""]
    ):
        col.markdown(f"**{label}**")

    for company in page["items"]:
        name, source, board, sector, size, remove = st.columns(
            [2, 1.5, 1.5, 1.5, 1.5, 1]
        )
        name.write(company["company"])
        source.write(company["source"])
        board.write(company["board"])
        sector.write(company.get("sector") or "—")
        size.write(company.get("size") or "—")
        if remove.button("Delete", key=f"delco_{company['id']}"):
            if api_delete(f"/companies/{company['id']}") is not None:
                st.rerun()

    st.subheader("Add company")
    with st.form("add_company", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        new_company = c1.text_input("Company")
        new_board = c2.text_input("Board token")
        new_source = c3.selectbox("Source", ["greenhouse"])
        new_sector = c4.selectbox("Sector", ["—", *SECTORS])
        new_size = c5.selectbox("Size", ["—", *SIZES])
        if st.form_submit_button("+ Add company", type="primary"):
            if not new_company or not new_board:
                st.warning("Company and board token are required.")
            else:
                payload = {
                    "company": new_company,
                    "board": new_board,
                    "source": new_source,
                }
                if new_sector != "—":
                    payload["sector"] = new_sector
                if new_size != "—":
                    payload["size"] = new_size
                if api_post("/company", json=payload) is not None:
                    st.success(f"Added {new_company}.")
                    st.rerun()


with applications_tab:
    f_app_status = st.selectbox(
        "Filter by status", ["Any", *STATUSES], key="app_status_filter"
    )
    reset_offset_on_change("applications", f_app_status)

    app_params = {"limit": PAGE_SIZE, "offset": st.session_state.applications_offset}
    if f_app_status != "Any":
        app_params["status_filter"] = f_app_status

    page = api_get("/applications", params=app_params) or {
        "items": [], "total": 0, "offset": 0, "limit": PAGE_SIZE, "has_more": False
    }
    render_pager("applications", page)

    header = st.columns([3, 2, 2, 1.5, 2, 1])
    for col, label in zip(
        header, ["Job", "Company", "Status", "Applied", "Notes", ""]
    ):
        col.markdown(f"**{label}**")

    for application in page["items"]:
        job = application["job"]
        job_col, company_col, status_col, applied_col, notes_col, remove_col = (
            st.columns([3, 2, 2, 1.5, 2, 1])
        )
        job_col.markdown(f"[{job['title']}]({job['url']})")
        company_col.write(job["company"])
        new_status = status_col.selectbox(
            "status",
            STATUSES,
            index=STATUSES.index(application["status"]),
            key=f"status_{application['id']}",
            label_visibility="collapsed",
        )
        if new_status != application["status"]:
            if api_patch(
                f"/applications/{application['id']}", json={"status": new_status}
            ) is not None:
                st.rerun()
        applied_col.write(fmt_dt(application.get("applied_at")))
        notes_col.write(application.get("notes") or "—")
        if remove_col.button("✕", key=f"delapp_{application['id']}", help="Remove"):
            if api_delete(f"/applications/{application['id']}") is not None:
                st.rerun()
