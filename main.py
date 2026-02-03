# main.py
from graph import robin_app

if __name__ == "__main__":
    print("🚢 Robin: Systems Active.")
    print("Choose Brain: [1] Llama 3 (Local) | [2] Gemini (Cloud)")
    choice = input("Select (1/2): ")
    
    history = []
    while True:
        user_input = input("\n👤 Manoj: ")
        if user_input.lower() in ["exit", "quit"]: break
        history.append(("user", user_input))
        result = robin_app.invoke({"messages": history, "model_choice": choice})
        ans = result["messages"][-1].content
        history.append(("assistant", ans))
        print(f"\n🚢 Robin: {ans}")