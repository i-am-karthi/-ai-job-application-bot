import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/jobs.db")
PROFILE_PATH = os.getenv("PROFILE_PATH", "data/profile.json")
RESUME_DIR = os.getenv("RESUME_DIR", "data/resumes")
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"

# Choose "openai_compatible" for a standard OpenAI-compatible chat API.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compatible")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
