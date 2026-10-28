import os,base64,re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from app.config import GOOGLE_OAUTH_CLIENT_SECRET_FILE,GOOGLE_TOKEN_FILE
SCOPES=["https://www.googleapis.com/auth/gmail.readonly"]

def service():
    creds=None
    if os.path.exists(GOOGLE_TOKEN_FILE): creds=Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE,SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else:
            if not os.path.exists(GOOGLE_OAUTH_CLIENT_SECRET_FILE): raise RuntimeError("OAuth client JSON missing; follow README Gmail setup.")
            flow=InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_CLIENT_SECRET_FILE,SCOPES); creds=flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(GOOGLE_TOKEN_FILE) or ".",exist_ok=True)
        with open(GOOGLE_TOKEN_FILE,"w",encoding="utf-8") as f: f.write(creds.to_json())
    return build("gmail","v1",credentials=creds,cache_discovery=False)

def text_part(p):
    data=p.get("body",{}).get("data","")
    txt=""
    if data:
        try: txt=base64.urlsafe_b64decode(data+"==").decode("utf-8",errors="ignore")
        except Exception: pass
    for c in p.get("parts",[]): txt += "\n"+text_part(c)
    return txt

def fetch_job_emails(query="newer_than:14d (job OR hiring OR careers OR vacancy)",max_results=20):
    api=service(); res=api.users().messages().list(userId="me",q=query,maxResults=min(max_results,50)).execute(); out=[]
    for item in res.get("messages",[]):
        msg=api.users().messages().get(userId="me",id=item["id"],format="full").execute()
        headers={h["name"].lower():h["value"] for h in msg.get("payload",{}).get("headers",[])}
        body=text_part(msg.get("payload",{}))
        links=list(dict.fromkeys(re.findall(r'https?://[^\s<>"\']+',body)))
        out.append({"message_id":item["id"],"subject":headers.get("subject",""),"from":headers.get("from",""),"date":headers.get("date",""),"body_excerpt":body[:10000],"links":links[:40]})
    return out
