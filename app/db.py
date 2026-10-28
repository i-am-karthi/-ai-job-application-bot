import os, sqlite3
from app.config import DATABASE_PATH

def connect():
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    c=sqlite3.connect(DATABASE_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT NOT NULL,
          location TEXT DEFAULT '', url TEXT NOT NULL UNIQUE, description TEXT DEFAULT '',
          source TEXT DEFAULT 'manual', status TEXT DEFAULT 'discovered', resume_path TEXT DEFAULT '',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS activity (
          id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, event TEXT NOT NULL,
          details TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

def log_event(job_id,event,details=""):
    with connect() as c: c.execute("INSERT INTO activity(job_id,event,details) VALUES(?,?,?)",(job_id,event,details))

def get_job(job_id):
    with connect() as c:
        r=c.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
        return dict(r) if r else None

def list_jobs():
    with connect() as c: return [dict(r) for r in c.execute("SELECT * FROM jobs ORDER BY created_at DESC")]

def add_job(d):
    with connect() as c:
        cur=c.execute("INSERT INTO jobs(title,company,location,url,description,source) VALUES(?,?,?,?,?,?)",
          (d["title"],d["company"],d.get("location",""),d["url"],d.get("description",""),d.get("source","manual")))
        jid=cur.lastrowid
    log_event(jid,"discovered",f"Source: {d.get('source','manual')}")
    return get_job(jid)

def update_job(jid,**fields):
    fields={k:v for k,v in fields.items() if k in {"status","resume_path"}}
    if fields:
        sets=", ".join(f"{k}=?" for k in fields)
        with connect() as c: c.execute(f"UPDATE jobs SET {sets},updated_at=CURRENT_TIMESTAMP WHERE id=?",list(fields.values())+[jid])
    return get_job(jid)

def get_activity(jid):
    with connect() as c: return [dict(r) for r in c.execute("SELECT * FROM activity WHERE job_id=? ORDER BY created_at DESC",(jid,))]
