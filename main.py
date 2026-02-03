from graph import robin_app

if __name__ == "__main__":
    print("🚢 Robin: 'Modular systems active. Ready for scaling, Manoj.'")
    history = []
    while True:
        user_input = input("\n👤 Manoj: ")
        if user_input.lower() in ["exit", "quit"]: break
        
        history.append(("user", user_input))
        result = robin_app.invoke({"messages": history})
        
        ans = result["messages"][-1].content
        history.append(("assistant", ans))
        print(f"\n🚢 Robin: {ans}")