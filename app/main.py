import os
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from app.db import init_db,add_job,list_jobs,get_job,update_job,get_activity,log_event
from app.schemas import JobCreate,StatusUpdate
from app.resume import build_resume
from app.gmail_reader import fetch_job_emails
from app.browser import prepare_application
from app.job_search import search_public_jobs

app=FastAPI(title="AI Job Application Bot",version="0.1.0")
@app.on_event("startup")
def startup():
    os.makedirs("data",exist_ok=True); os.makedirs("data/resumes",exist_ok=True); init_db()
@app.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(os.path.dirname(__file__), "dashboard.html"), encoding="utf-8") as f:
        return f.read()
@app.get("/jobs")
def jobs(): return list_jobs()
@app.post("/jobs")
def create_job(job:JobCreate):
    d=job.model_dump(); d["url"]=str(d["url"])
    try: return add_job(d)
    except Exception as e:
        if "UNIQUE constraint failed" in str(e): raise HTTPException(409,"This URL is already tracked.")
        raise
@app.get("/jobs/{job_id}")
def detail(job_id:int):
    j=get_job(job_id)
    if not j: raise HTTPException(404,"Job not found")
    return {"job":j,"activity":get_activity(job_id)}
@app.post("/jobs/{job_id}/resume")
def make_resume(job_id:int):
    j=get_job(job_id)
    if not j: raise HTTPException(404,"Job not found")
    path=build_resume(j); update_job(job_id,resume_path=path,status="resume_ready"); log_event(job_id,"resume_created",path)
    return {"job_id":job_id,"resume_path":path,"download_url":f"/jobs/{job_id}/resume.pdf"}
@app.get("/jobs/{job_id}/resume.pdf")
def get_resume(job_id:int):
    j=get_job(job_id)
    if not j or not j.get("resume_path") or not os.path.exists(j["resume_path"]): raise HTTPException(404,"PDF not found; generate it first.")
    return FileResponse(j["resume_path"],media_type="application/pdf",filename=os.path.basename(j["resume_path"]))
@app.post("/jobs/{job_id}/prepare")
def prepare(job_id:int):
    j=get_job(job_id)
    if not j: raise HTTPException(404,"Job not found")
    if not j.get("resume_path") or not os.path.exists(j["resume_path"]): raise HTTPException(400,"Generate PDF first.")
    if not j["url"].startswith("https://"): raise HTTPException(400,"Only HTTPS application URLs are accepted.")
    return prepare_application(j,j["resume_path"])
@app.post("/jobs/{job_id}/status")
def status(job_id:int,body:StatusUpdate):
    if not get_job(job_id): raise HTTPException(404,"Job not found")
    allowed={"discovered","verified","resume_ready","awaiting_review","applied","rejected","interview","closed","needs_manual_work"}
    if body.status not in allowed: raise HTTPException(400,"Invalid status: "+", ".join(sorted(allowed)))
    update_job(job_id,status=body.status); log_event(job_id,"status_changed",body.status); return get_job(job_id)
@app.get("/jobs/{job_id}/activity")
def activity(job_id:int):
    if not get_job(job_id): raise HTTPException(404,"Job not found")
    return get_activity(job_id)

import json
import hmac
import base64
from fastapi import Request
from fastapi.responses import RedirectResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
from app.config import GOOGLE_TOKEN_FILE

SESSION_SECRET = os.getenv("SESSION_SECRET", "")
APP_USERNAME = os.getenv("APP_USERNAME", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
GOOGLE_CLIENT_CONFIG = os.getenv("GOOGLE_OAUTH_CLIENT_CONFIG", "")
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

@app.middleware("http")
async def protect_app(request: Request, call_next):
    if request.url.path not in {"/gmail/callback", "/health"}:
        if not APP_USERNAME or not APP_PASSWORD:
            return PlainTextResponse(
                "Set APP_USERNAME and APP_PASSWORD in Render.",
                status_code=503,
            )
        auth = request.headers.get("authorization", "")
        valid = False
        if auth.startswith("Basic "):
            try:
                user, password = base64.b64decode(auth[6:]).decode().split(":", 1)
                valid = (
                    hmac.compare_digest(user, APP_USERNAME)
                    and hmac.compare_digest(password, APP_PASSWORD)
                )
            except Exception:
                pass
        if not valid:
            return PlainTextResponse(
                "Login required.",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="AI Job Application Bot"'},
            )
    return await call_next(request)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET or "disabled-until-secret-is-set",
    https_only=True,
    same_site="lax",
)

def create_oauth_flow(request: Request, state=None):
    if not SESSION_SECRET:
        raise HTTPException(503, "Set SESSION_SECRET in Render.")
    if not GOOGLE_CLIENT_CONFIG:
        raise HTTPException(503, "Set GOOGLE_OAUTH_CLIENT_CONFIG in Render.")
    try:
        config = json.loads(GOOGLE_CLIENT_CONFIG)
    except json.JSONDecodeError:
        raise HTTPException(500, "Google OAuth client config is not valid JSON.")
    flow = Flow.from_client_config(config, scopes=GOOGLE_SCOPES, state=state)
    flow.redirect_uri = str(request.base_url).rstrip("/") + "/gmail/callback"
    return flow

@app.get("/gmail/connect")
def gmail_connect(request: Request):
    flow = create_oauth_flow(request)
    url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    request.session["oauth_state"] = state
    return RedirectResponse(url)

@app.get("/gmail/callback")
def gmail_callback(
    request: Request, state: str = "", code: str = "", error: str = ""
):
    if error:
        raise HTTPException(400, "Google authorization was cancelled or denied.")
    expected = request.session.pop("oauth_state", None)
    if not expected or not hmac.compare_digest(str(expected), str(state)):
        raise HTTPException(400, "OAuth state mismatch. Retry Gmail connection.")
    flow = create_oauth_flow(request, state=state)
    flow.fetch_token(code=code)
    os.makedirs(os.path.dirname(GOOGLE_TOKEN_FILE) or ".", exist_ok=True)
    with open(GOOGLE_TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(flow.credentials.to_json())
    return RedirectResponse("/", status_code=303)


@app.get("/gmail/jobs")
def gmail_jobs(query:str="newer_than:14d (job OR hiring OR careers OR vacancy)",max_results:int=20):
    try: return {"count":len(emails:=fetch_job_emails(query,max_results)),"emails":emails,"notice":"Links are unverified leads; check the official employer listing before applying."}
    except Exception as e: raise HTTPException(400,str(e))


@app.get("/search/jobs")
async def search_jobs(q: str = "software engineer Python AI", location: str = "Bengaluru", count: int = 10):
    try:
        return await search_public_jobs(q, location, count)
    except Exception as e:
        raise HTTPException(400, str(e))
