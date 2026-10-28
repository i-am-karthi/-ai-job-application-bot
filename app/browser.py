import os
from playwright.sync_api import sync_playwright
from app.config import PLAYWRIGHT_HEADLESS
from app.db import log_event,update_job

def prepare_application(job,resume_path):
    # Best-effort generic upload. ATS pages often need a dedicated site adapter.
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
        page=browser.new_page()
        page.goto(job["url"],wait_until="domcontentloaded",timeout=60000)
        page.wait_for_timeout(1000)
        uploaded=0
        for loc in page.locator('input[type="file"]').all():
            try: loc.set_input_files(resume_path,timeout=1500); uploaded+=1; break
            except Exception: pass
        os_path=f"data/application_{job['id']}.png"
        page.screenshot(path=os_path,full_page=True)
        result={"title":page.title(),"current_url":page.url,"screenshot_path":os_path,"upload_inputs_filled":uploaded,
                "status":"awaiting_review","message":"Final submit was NOT clicked. Inspect the page/screenshot; site-specific form work may be required."}
        browser.close()
    update_job(job["id"],status="awaiting_review")
    log_event(job["id"],"application_prepared",f"URL {job['url']}; upload inputs filled: {uploaded}; final submit not clicked")
    return result
