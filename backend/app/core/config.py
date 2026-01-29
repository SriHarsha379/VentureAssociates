import os

# -------- OpenAI --------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = "gpt-4o-mini"

# -------- Mongo --------
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "invoice_db"

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")