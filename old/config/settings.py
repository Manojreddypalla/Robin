# # config/settings.py
# So here you decide:

# Which model?

# Which API?

# Which DB?

# Which URL?

import os
from dotenv import load_dotenv

load_dotenv()


# ===============================
# GEMINI CONFIG
# ===============================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"


# ===============================
# OLLAMA CONFIG (LOCAL)
# ===============================

OLLAMA_BASE_URL = "http://localhost:11434"

OLLAMA_MODEL = "llama3"


# ===============================
# LLM MODE SWITCH
# ===============================
# "gemini" OR "ollama"

DEFAULT_LLM = "ollama"


# ===============================
# MEMORY CONFIG
# ===============================

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333


NEO4J_URL = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
