# utils/llm_factory.py

import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()


def get_llm():

    provider = os.getenv("LLM_PROVIDER", "ollama")

    if provider == "gemini":
        return init_chat_model(
            model="gemini-pro",
            model_provider="google_genai",
            api_key=os.getenv("GEMINI_API_KEY")
        )

    # Default: Ollama
    return init_chat_model(
        model=os.getenv("OLLAMA_CHAT_MODEL", "llama3"),
        model_provider="ollama"
    )
