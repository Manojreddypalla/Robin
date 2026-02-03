from mem0 import Memory
from config import MEMORY_CONFIG, USER_ID

memory = Memory.from_config(MEMORY_CONFIG)

def add_to_memory(text):
    try:
        memory.add(text, user_id=USER_ID)
    except Exception as e:
        print(f"\n[SYSTEM] ⚠️ Memory Sync Error: {e}")

def search_memory(query):
    return memory.search(query, user_id=USER_ID)