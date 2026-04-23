# ============================================================
# memory_engine.py — Robin 2.0
# ============================================================

import asyncio
from concurrent.futures import ThreadPoolExecutor
from mem0 import Memory
from config import MEMORY_CONFIG, USER_ID, MEM_COLLECTION

print(f"🧠 Initializing Memory Engine [Collection: {MEM_COLLECTION}]...")

try:
    if "vector_store" in MEMORY_CONFIG:
        MEMORY_CONFIG["vector_store"]["config"]["collection_name"] = MEM_COLLECTION
    mem_client = Memory.from_config(MEMORY_CONFIG)
    print(f"✅ Memory Engine ready.")
except Exception as e:
    print(f"❌ Mem0 Init Failed: {e}")
    mem_client = None

# Thread pool for running blocking mem0 calls off the event loop
_executor = ThreadPoolExecutor(max_workers=2)


# ============================================================
# SYNC: search_memory (used by personal_search node)
# ============================================================

def search_memory(query: str, user_id: str = USER_ID) -> list:
    if not mem_client:
        return []
    try:
        results = mem_client.search(query=query, user_id=user_id)
        if isinstance(results, dict):
            results = results.get("results", [])
        return [r.get("memory") for r in results if isinstance(r, dict) and "memory" in r]
    except Exception as e:
        print(f"⚠️ Memory search error: {e}")
        return []


# ============================================================
# ASYNC: add_to_memory (called from oracle — non-blocking)
# mem0's .add() hits Qdrant + LLM — can take 1-3s.
# Running it in executor keeps oracle response snappy.
# ============================================================

def _add_to_memory_sync(user_input: str, ai_response: str, user_id: str):
    """Blocking mem0 write — runs in thread pool."""
    if not mem_client:
        return

    # Skip saving error responses or rate limit messages
    skip_signals = ["429", "RESOURCE_EXHAUSTED", "Error:", "❌", "Critical failure"]
    if not ai_response or any(s in str(ai_response) for s in skip_signals):
        print("⚠️ Memory save skipped — response looks like an error.")
        return

    try:
        mem_client.add(
            messages=[
                {"role": "user",      "content": user_input},
                {"role": "assistant", "content": ai_response}
            ],
            user_id=user_id
        )
        print(f"💾 Memory saved → {MEM_COLLECTION}")
    except Exception as e:
        print(f"⚠️ Mem0 error: {e}")


async def add_to_memory(user_input: str, ai_response: str, user_id: str = USER_ID):
    """
    Async wrapper — fires mem0 write in a thread pool.
    Oracle calls this with await; it won't block streaming.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor,
        _add_to_memory_sync,
        user_input,
        ai_response,
        user_id
    )