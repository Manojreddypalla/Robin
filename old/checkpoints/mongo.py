# checkpoints/mongo.py

import os
from dotenv import load_dotenv
from langgraph.checkpoint.mongodb import MongoDBSaver

load_dotenv()

_ctx = None
_saver = None


def get_checkpointer():
    global _ctx, _saver

    # Already initialized
    if _saver is not None:
        return _saver

    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        raise ValueError("MONGO_URI not set in .env")

    # Create context manager
    _ctx = MongoDBSaver.from_conn_string(mongo_uri)

    # Manually enter ONCE
    _saver = _ctx.__enter__()

    return _saver
