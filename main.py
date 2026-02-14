import warnings
# 1. SILENCE THE WARNINGS (Must be at the very top)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import uuid
import time
from graph import robin_app

# ASCII Colors for a Professional Look
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def print_banner():
    """Prints the startup logo."""
    print(f"{CYAN}=========================================={RESET}")
    print(f"{CYAN}    🚀 ROBIN 2.0 | AI ARCHAEOLOGIST        {RESET}")
    print(f"{CYAN}    System: ONLINE | Memory: CONNECTED     {RESET}")
    print(f"{CYAN}=========================================={RESET}")

def get_model_choice():
    """Forces the user to pick 1 or 2."""
    while True:
        print(f"\n{YELLOW}Select Neural Engine:{RESET}")
        print(" [1] Llama 3 (Local - RTX 4060 Acceleration)")
        print(" [2] Gemini 2.5 (Cloud - 6-Key Rotation)")
        
        choice = input(f"{YELLOW}>>> Select (1/2): {RESET}").strip()
        if choice in ["1", "2"]:
            return choice
        print(f"{RED}❌ Invalid selection. Please type 1 or 2.{RESET}")

if __name__ == "__main__":
    try:
        print_banner()
        choice = get_model_choice()
        
        if choice == "1":
            print(f"\n{GREEN}🟢 System locked to LOCAL. Leveraging RTX 4060.{RESET}")
        else:
            print(f"\n{GREEN}🔵 System locked to CLOUD. Auto-Rotation active.{RESET}")

        # --- SESSION CONFIGURATION ---
        # thread_id identifies the conversation for the LangGraph checkpointer.
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        print(f"\n{CYAN}--- BEGIN TRANSMISSION (Session ID: {thread_id[:8]}) ---{RESET}")

        # --- MAIN CHAT LOOP ---
        while True:
            try:
                user_input = input(f"\n👤 {YELLOW}Manoj:{RESET} ").strip()
                
                # Exit Commands
                if user_input.lower() in ["exit", "quit", "bye"]:
                    print(f"\n{RED}🛑 System Shutdown.{RESET}")
                    break
                
                # Skip empty enters
                if not user_input: continue

                # Prepare Payload
                inputs = {
                    "messages": [("user", user_input)], 
                    "model_choice": choice
                }
                
                print(f"\n🚢 {CYAN}Robin:{RESET} ", end="", flush=True)

                # --- STREAMING LOGIC ---
                # LangGraph streams updates as the state moves through nodes.
                # 'messages' mode yields specific token chunks.
                last_node = ""
                for msg, metadata in robin_app.stream(
                    inputs, 
                    config=config, 
                    stream_mode="messages"
                ):
                    current_node = metadata.get("langgraph_node")
                    
                    # Optional: Log node transitions for debugging
                    if current_node != last_node and current_node:
                        # print(f"\n{YELLOW}[{current_node}]{RESET} ", end="", flush=True)
                        last_node = current_node

                    # Only stream the final "talk" from the oracle
                    if current_node == "oracle":
                        # msg is an AIMessageChunk
                        if hasattr(msg, "content"):
                            print(msg.content, end="", flush=True)
                
                print() # Ensure the next prompt starts on a new line

            except KeyboardInterrupt:
                print(f"\n{RED}🛑 Interrupted by User.{RESET}")
                break
            
            except Exception as e:
                print(f"\n{RED}❌ Runtime Error: {e}{RESET}")
                print(f"{YELLOW}🔄 Attempting to recover... Try again.{RESET}")

    except Exception as e:
        print(f"{RED}❌ Critical Startup Error: {e}{RESET}")