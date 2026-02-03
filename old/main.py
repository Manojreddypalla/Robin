# main.py

import os
from dotenv import load_dotenv

from graph.workflow import create_workflow
from checkpoints.mongo import get_checkpointer


# ------------------------
# Manual LLM Selector
# ------------------------
def select_llm():

    print("\nSelect LLM:")
    print("1) Ollama (Local)")
    print("2) Gemini (Cloud)")

    choice = input("Enter choice (1/2): ").strip()

    if choice == "2":
        os.environ["LLM_PROVIDER"] = "gemini"
    else:
        os.environ["LLM_PROVIDER"] = "ollama"

    print(f"\nUsing: {os.environ['LLM_PROVIDER'].upper()}\n")


# ------------------------
# Main App
# ------------------------
def main():

    load_dotenv()

    select_llm()

    print("🚀 Robin Memory Agent Started")
    print("Type 'exit' to quit\n")

    # Create workflow
    workflow = create_workflow()

    # Mongo checkpointer
    checkpointer = get_checkpointer()

    # Compile graph
    graph = workflow.compile(checkpointer=checkpointer)

    # Session config
    config = {
        "configurable": {
            "thread_id": "manoj"
        }
    }

    # Chat loop
    while True:

        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("Goodbye 👋")
            break

        if not user_input:
            continue

        # Initial state
        state = {
            "messages": [user_input],
            "memories": [],
            "answer": ""
        }

        # Run workflow
        for step in graph.stream(
            state,
            config=config,
            stream_mode="values"
        ):
            last_msg = step["messages"][-1]
            last_msg.pretty_print()


# ------------------------
# Entry
# ------------------------
if __name__ == "__main__":
    main()
