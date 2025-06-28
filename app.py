import json
from retrieval.retriever import get_rag_chain

def load_messages(path: str):
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("messages", [])

def run():
    messages = load_messages("data/messages.json")
    handlers = {}

    for msg in messages:
        user_input = msg.get("text", "").strip()
        user_id = msg.get("user_id", "")
        username = msg.get("username", "Unknown")

        if not user_input or not user_id:
            continue

        if user_id not in handlers:
            handlers[user_id] = get_rag_chain(user_id)

        # Process and return enhanced RAG response
        response = handlers[user_id](user_input, [])  # Empty chat_history for now

        # Print enhanced JSON response
        print(f"\n👤 [{username}] → Enhanced RAG Response:")
        print(json.dumps(response, indent=2))

if __name__ == "__main__":
    run()
