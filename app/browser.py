import json, os, re
from playwright.sync_api import sync_playwright
from app.config import PLAYWRIGHT_HEADLESS, PROFILE_PATH
from app.db import log_event, update_job

SENSITIVE = re.compile(r"work authori[sz]|visa|sponsor|gender|pronoun|race|ethnic|disabilit|veteran|criminal|date of birth|birth date|age|citizenship|eeo|consent|terms|privacy|salary|compensation|relocat|notice period|years of experience|cover letter|why (do you|are you)", re.I)

def _value(profile, label):
    if SENSITIVE.search(label): return None
    groups = [(r"e[- ]?mail", "email"), (r"phone|mobile|telephone", "phone"),
      (r"first name|given name", "first_name"), (r"last name|family name|surname", "last_name"),
      (r"full name|your name|^name$", "full_name"), (r"linkedin", "linkedin"),
      (r"github", "github"), (r"portfolio|website|personal site|url", "portfolio"),
      (r"city|location|address", "location")]
    for pattern,key in groups:
        v=profile.get(key)
        if re.search(pattern,label,re.I) and isinstance(v,str) and v.strip(): return v.strip()
    return None

def _run(page, job, resume_path, profile):
    page.goto(job["url"], wait_until="domcontentloaded", timeout=60000); page.wait_for_timeout(1200)
    fields=page.locator("input,textarea,select"); filled=[]; skipped=[]
    for i in range(fields.count()):
        f=fields.nth(i)
        try:
            if not f.is_visible() or not f.is_enabled(): continue
            d=f.evaluate("""e=>{let id=e.id,l=id?[...document.querySelectorAll('label[for="'+CSS.escape(id)+'"]')]:[],p=e.closest('label');return {tag:e.tagName.toLowerCase(),type:(e.type||'').toLowerCase(),label:[...l,...(p?[p]:[])].map(x=>x.innerText).join(' '),aria:e.getAttribute('aria-label')||'',placeholder:e.placeholder||'',name:e.name||'',id,required:!!e.required,value:e.value||''}}""")
            if d["type"]=="file":
                try: f.set_input_files(resume_path,timeout=1500); filled.append({"label":"Resume upload","value":os.path.basename(resume_path)})
                except Exception:
                    if d["required"]: skipped.append({"label":"Resume upload","required":True})
                continue
            if d["type"] in {"hidden","submit","button","reset","checkbox","radio","password"}: continue
            label=" ".join(x for x in [d["label"],d["aria"],d["placeholder"],d["name"],d["id"]] if x)
            v=_value(profile,label)
            if d["value"] or not v:
                if d["required"] and not d["value"]: skipped.append({"label":label or f"Field {i+1}","required":True})
                continue
            if d["tag"]=="select":
                match=None
                for o in f.locator("option").all():
                    if v.casefold() in {(o.inner_text() or "").strip().casefold(),(o.get_attribute("value") or "").casefold()}: match=o.get_attribute("value"); break
                if match is None:
                    if d["required"]: skipped.append({"label":label,"required":True})
                    continue
                f.select_option(match)
            elif d["type"] in {"","text","email","tel","url","search"} or d["tag"]=="textarea": f.fill(v)
            else: continue
            filled.append({"label":label or f"Field {i+1}","value":v})
        except Exception: continue
    shot=f"data/application_{job['id']}.png"; page.screenshot(path=shot,full_page=True)
    return {"title":page.title(),"current_url":page.url,"screenshot_path":shot,"filled_fields":filled,"unfilled_required_fields":skipped}

def prepare_application(job,resume_path):
    with open(PROFILE_PATH,encoding="utf-8") as f: profile=json.load(f)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=PLAYWRIGHT_HEADLESS); page=browser.new_page()
        result=_run(page,job,resume_path,profile); browser.close()
    result.update({"status":"awaiting_review","message":"Review the screenshot and filled fields. Submit is separate and requires your confirmation; unsupported questions remain blank."})
    update_job(job["id"],status="awaiting_review")
    log_event(job["id"],"application_prepared",f"URL {job['url']}; filled {len(result['filled_fields'])} profile-backed fields; did not submit")
    return result

def submit_application(job,resume_path):
    with open(PROFILE_PATH,encoding="utf-8") as f: profile=json.load(f)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=PLAYWRIGHT_HEADLESS); page=browser.new_page()
        result=_run(page,job,resume_path,profile)
        body=(page.locator("body").inner_text(timeout=5000) or "").lower()
        if re.search(r"captcha|verify you are human|two[- ]factor|multi[- ]factor|one[- ]time code",body):
            browser.close(); return {"status":"needs_manual_work","message":"Verification/CAPTCHA detected. Nothing was submitted; complete it manually."}
        required=page.locator("input[required]:visible,textarea[required]:visible,select[required]:visible")
        missing=0
        for i in range(required.count()):
            try:
                if not (required.nth(i).input_value() or "").strip(): missing+=1
            except Exception: missing+=1
        # Never auto-accept a required checkbox (including consent/terms).
        checks=page.locator('input[type="checkbox"]:visible')
        for i in range(checks.count()):
            if not checks.nth(i).is_checked(): missing+=1
        if missing:
            browser.close(); return {"status":"needs_manual_work","message":f"{missing} required field(s) need manual answers. Nothing was submitted.","unfilled_required_fields":result["unfilled_required_fields"]}
        rx=re.compile(r"^(apply|submit application|send application|complete application)$",re.I)
        btn=page.get_by_role("button",name=rx); link=page.get_by_role("link",name=rx)
        candidates=[x for x in (btn,link) if x.count()==1]
        if len(candidates)!=1:
            browser.close(); return {"status":"needs_manual_work","message":"Could not identify one unambiguous final application button. Nothing was submitted."}
        candidates[0].click(timeout=10000); page.wait_for_timeout(1500)
        text=page.locator("body").inner_text(timeout=5000) or ""
        shot=f"data/application_{job['id']}_submitted.png"; page.screenshot(path=shot,full_page=True)
        result={"status":"submitted","current_url":page.url,"confirmation_text":text[:1200],"screenshot_path":shot,"message":"Submit was clicked after your confirmation. Verify the employer confirmation page."}
        browser.close()
    log_event(job["id"],"application_submit_clicked",f"URL {job['url']}; verify employer confirmation")
    return result
