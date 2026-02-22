import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Slack Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# LLM Configuration (OpenAI Compatible)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# Semantic Scholar API Key
S2_API_KEY = os.getenv("S2_API_KEY")

# Target Venues for Semantic Scholar
TARGET_VENUES = [
    # Computer Vision (CV)
    "CVPR", "ICCV", "ECCV",
    # Machine Learning / General AI
    "NeurIPS", "ICML", "ICLR",
    # Natural Language Processing (NLP)
    "ACL", "EMNLP", "NAACL"
]

# Database Path
DB_PATH = os.getenv("DB_PATH", "papers.db")

# Scheduler (Run interval in seconds, default 24 hours)
RUN_INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_SECONDS", 24 * 60 * 60))
