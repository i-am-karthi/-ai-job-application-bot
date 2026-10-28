# AI Job Application Bot — Starter

Local-first Python/FastAPI starter: track jobs, read Gmail job alerts (read-only OAuth), generate real tailored PDF resumes with Azure OpenAI, and prepare application pages with Playwright. It intentionally does not click final Submit; review and submit yourself.

## Requirements
Python 3.11+, Google Cloud OAuth client (optional), Azure OpenAI deployment (optional).

## Install (Windows PowerShell)
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`, then run the same pip/install commands and `cp .env.example .env`.

Open http://127.0.0.1:8000/docs.

## Configure
1. Replace placeholders in `data/profile.json` with accurate details.
2. Set Azure OpenAI values in `.env` to enable tailoring. Without them, a baseline PDF is generated from your profile.
3. For Gmail: enable Gmail API in Google Cloud, create OAuth Desktop credentials, save the JSON at `credentials/google-oauth-client.json`, then call `/gmail/jobs`. Scope is read-only.
4. Add jobs using `POST /jobs`, generate a PDF with `POST /jobs/{id}/resume`, download it at `/jobs/{id}/resume.pdf`.
5. `POST /jobs/{id}/prepare` opens the job page, attempts a generic resume file upload, captures a screenshot, and stops without final submission. Career sites vary; site-specific adapters will often be needed.
6. Track status using `POST /jobs/{id}/status`.

## Example job JSON
```json
{"title":"Software Engineer I","company":"Example Corp","location":"Bengaluru","url":"https://careers.example.com/jobs/123","description":"Python, SQL, APIs, 0-2 years","source":"manual"}
```

## Important limitations and safety
- Email links and search results are leads, not proof a vacancy is open. Verify on the official employer site.
- Do not bypass CAPTCHAs, MFA, access controls, or website terms.
- The AI must not invent experience, metrics, qualifications, or application answers.
- Never commit `.env`, OAuth credentials, or personal resume data.
- This is a starter, not a universal auto-apply system. Different applicant tracking systems require separate adapters.


## Use a non-Azure LLM first
The project now uses the standard `OpenAI` Python client against an OpenAI-compatible Chat Completions API. Set these in `.env`:
- `LLM_API_KEY`: API key from your chosen provider
- `LLM_MODEL`: exact model/deployment name required by that provider
- `LLM_BASE_URL`: provider's documented API base URL; leave blank only if using the default OpenAI API endpoint

Not every provider supports `response_format={"type":"json_object"}`. If yours does not, remove that parameter and add robust JSON extraction/validation. Never paste API keys into chat or source code.

## Profile template
`data/profile.json` is prefilled with known role/date context as a starting point. Replace all `REPLACE_...` values and review every project/skill/bullet before generating applications. Some project descriptions are reminders to verify, not claims you should submit unchanged.

## Groq configuration and smoke test
Use these `.env` values:
```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=YOUR_GROQ_API_KEY
LLM_MODEL=openai/gpt-oss-20b
```
The current `app/ai.py` uses the `openai` package's `OpenAI` client, so no separate `groq` dependency is required. Install/update with:
```powershell
python -m pip install --upgrade openai python-dotenv
```
Then run the synthetic-profile test:
```powershell
python test_groq_resume.py
```
The test sends fake candidate data to Groq and checks that the response has the expected resume fields. It does not read your real profile or submit any applications.

## Dashboard and public job search
Run `uvicorn app.main:app --reload`, then open `http://127.0.0.1:8000/` for the local dashboard. It supports adding jobs, listing tracked jobs, generating/download PDFs, reading Gmail leads, and preparing an application page without clicking final submit.

Optional public job search uses Brave Search API. Add `BRAVE_SEARCH_API_KEY` to `.env`, install requirements, then visit `/docs` and call `GET /search/jobs?q=software%20engineer%20Python&location=Bengaluru`. Search results are leads only and must be verified against official employer listings. Never use search snippets as proof that a vacancy is active.

The current application-preparation adapter is generic and may not fill every employer's forms. The dashboard includes a manual status update action; only mark a job applied after you actually submit it yourself.
