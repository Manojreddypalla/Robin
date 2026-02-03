# memory/store.py

from memory.client import get_memory_client

_memory = None


def get_memory():
    global _memory

    if _memory is None:
        _memory = get_memory_client()

    return _memory
