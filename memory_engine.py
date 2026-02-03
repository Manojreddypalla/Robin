from mem0 import Memory
from config import MEMORY_CONFIG

# Initialize once to be reused across the app
mem_client = Memory.from_config(MEMORY_CONFIG)

def search_memory(query, user_id="manoj_palla"):
    try:
        search_results = mem_client.search(query=query, user_id=user_id)
        # Handle dict or list return formats
        results = search_results.get("results", []) if isinstance(search_results, dict) else search_results
        return [mem.get('memory') for mem in results if 'memory' in mem]
    except Exception as e:
        print(f"❌ Search Error: {e}")
        return []

def add_to_memory(user_query, ai_response, user_id="manoj_palla"):
    try:
        mem_client.add(user_id=user_id, messages=[
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": ai_response}
        ])
    except Exception as e:
        print(f"❌ Storage Error: {e}")