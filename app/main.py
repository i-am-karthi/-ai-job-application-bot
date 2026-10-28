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
