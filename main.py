import warnings
import asyncio
import sys
import uuid
from graph import robin_app
from config import (
    USER_NAME, ROBIN_NAME,
    LOCAL_ORACLE_MODEL, GEMINI_MODEL
)
import os

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ============================================================
# ENV-DRIVEN DISPLAY CONFIG
# ============================================================
GPU_NAME    = os.getenv("GPU_NAME",    "Local GPU")
APP_VERSION = os.getenv("APP_VERSION", "2.0")

# ASCII Colors
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"


# ============================================================
# BANNER
# ============================================================
def print_banner():
    print(f"{CYAN}=========================================={RESET}")
    print(f"{CYAN}     🚀 {ROBIN_NAME} {APP_VERSION} | Personal AI Agent   {RESET}")
    print(f"{CYAN}     System: ONLINE  |  Memory: CONNECTED    {RESET}")
    print(f"{CYAN}=========================================={RESET}")


# ============================================================
# MODEL SELECTION
# ============================================================
def get_model_choice() -> str:
    while True:
        print(f"\n{YELLOW}Select Neural Engine:{RESET}")
        print(f" [1] {LOCAL_ORACLE_MODEL} (Local — {GPU_NAME})")
        print(f" [2] {GEMINI_MODEL} (Cloud — Multi-Key Rotation)")
        choice = input(f"{YELLOW}>>> Select (1/2): {RESET}").strip()
        if choice in ["1", "2"]:
            return choice
        print(f"{RED}❌ Invalid. Type 1 or 2.{RESET}")


# ============================================================
# SPECIALIST OUTPUT PRINTER
# Specialist goes straight to END — no oracle streaming.
# We capture its final message from state directly.
# ============================================================
def print_specialist_result(result: dict):
    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = last.content if hasattr(last, "content") else str(last)
        print(content)


# ============================================================
# MAIN ASYNC CHAT LOOP
# ============================================================
async def chat_loop():
    try:
        print_banner()
        choice = get_model_choice()

        if choice == "1":
            print(f"\n{GREEN}🟢 Local mode — {LOCAL_ORACLE_MODEL} on {GPU_NAME}{RESET}")
        else:
            print(f"\n{GREEN}🔵 Cloud mode — {GEMINI_MODEL} with key rotation{RESET}")

        thread_id = str(uuid.uuid4())
        config    = {"configurable": {"thread_id": thread_id}}

        print(f"\n{CYAN}--- SESSION STARTED (ID: {thread_id[:8]}) ---{RESET}")

        while True:
            try:
                user_input = input(f"\n👤 {YELLOW}{USER_NAME}:{RESET} ").strip()

                if user_input.lower() in ["exit", "quit", "bye"]:
                    print(f"\n{RED}🛑 Session ended. See you, {USER_NAME}.{RESET}")
                    break
                if not user_input:
                    continue

                inputs = {
                    "messages":    [("user", user_input)],
                    "model_choice": choice
                }

                print(f"\n🚢 {CYAN}{ROBIN_NAME}:{RESET} ", end="", flush=True)

                # Track which nodes fire so we know how to print
                specialist_fired = False
                oracle_fired     = False

                async for msg, metadata in robin_app.astream(
                    inputs,
                    config=config,
                    stream_mode="messages"
                ):
                    node = metadata.get("langgraph_node", "")

                    # Stream oracle tokens as they arrive
                    if node == "oracle":
                        oracle_fired = True
                        if hasattr(msg, "content") and msg.content:
                            print(msg.content, end="", flush=True)

                    # Specialist result arrives as a complete message (no streaming)
                    elif node == "specialist":
                        specialist_fired = True
                        if hasattr(msg, "content") and msg.content:
                            print(msg.content, end="", flush=True)

                print()  # newline after response

            except KeyboardInterrupt:
                print(f"\n{RED}🛑 Interrupted.{RESET}")
                break
            except asyncio.TimeoutError:
                print(f"\n{RED}⏱️ Request timed out. Try again.{RESET}")
            except Exception as e:
                print(f"\n{RED}❌ Error: {e}{RESET}")
                print(f"{YELLOW}🔄 Recovering — try again.{RESET}")

    except Exception as e:
        print(f"{RED}❌ Startup error: {e}{RESET}")
        raise


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    # Windows asyncio fix
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(chat_loop())