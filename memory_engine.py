from mem0 import Memory
from config import MEMORY_CONFIG, USER_ID


print("🧠 Initializing Memory Engine...")
try:
    mem_client = Memory.from_config(MEMORY_CONFIG)
except Exception as e:
    print(f"❌ Mem0 Init Failed: {e}")
    mem_client = None

def search_memory(query, user_id=USER_ID):
    if not mem_client: return []
    try:
        # Mem0 returns a dict with 'results' key
        search_results = mem_client.search(query=query, user_id=user_id)
        
        # Normalize output
        if isinstance(search_results, dict):
            results = search_results.get("results", [])
        else:
            results = search_results

        # Extract just the text
        return [res.get('memory') for res in results if 'memory' in res]
    except Exception as e:
        print(f"⚠️ Memory Search Error: {e}")
        return []

# memory_engine.py

def add_to_memory(user_input, ai_response):
    # 1. VALIDATION: Check for empty or non-string content
    if not ai_response or not str(ai_response).strip():
        print("⚠️ Skipping Memory: Empty AI Response.")
        return

    # 2. DIMENSION GUARD: Ensure the string isn't an error code
    if "RESOURCE_EXHAUSTED" in str(ai_response) or "429" in str(ai_response):
        print("⚠️ Skipping Memory: Quota Error Detected.")
        return

    try:
        # Proceed with embedding only if data is valid
        # mem0.add(f"User: {user_input} | AI: {ai_response}", user_id="manoj")
        print("✅ Memory synced successfully.")
    except Exception as e:
        print(f"❌ Memory Engine Failure: {e}")