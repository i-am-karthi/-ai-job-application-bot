import os
from dotenv import load_dotenv

load_dotenv()

# Database and profile paths
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/jobs.db")
PROFILE_PATH = os.getenv("PROFILE_PATH", "data/profile.json")
RESUME_DIR = os.getenv("RESUME_DIR", "data/resumes")

# Browser automation
PLAYWRIGHT_HEADLESS = (
    os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
)

# Gmail OAuth configuration
GOOGLE_OAUTH_CLIENT_SECRET_FILE = os.getenv(
    "GOOGLE_OAUTH_CLIENT_SECRET_FILE",
    "credentials.json",
)
GOOGLE_TOKEN_FILE = os.getenv(
    "GOOGLE_TOKEN_FILE",
    "token.json",
)

# LLM configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compatible")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
