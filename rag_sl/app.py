from retrieval.retriever import get_rag_chain
from dotenv import load_dotenv
import os
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain


def main():
    """Main application function to run the RAG chatbot."""
    load_dotenv()
    
    print("🚀 Initializing RAG System...")
    
    try:
        rag_chain = get_rag_chain()
        chat_history = []
        
        print(" RAG System initialized successfully!")
        print(" Ask anything about your data. Type 'exit' to quit.")
       
        
        while True:
            query = input("\n🧠 You: ").strip()
            
            if query.lower() in ['exit', 'quit', 'bye']:
                print("👋 Goodbye!")
                break
                
            if not query:
                print("Please enter a question.")
                continue
                
            try:
                print("🔄 Processing...")
                result = rag_chain.invoke({
                    "input": query, 
                    "chat_history": chat_history
                })
                
                answer = result.get("answer", "Sorry, I couldn't generate an answer.")
                print(f"🤖 Assistant: {answer}")
                
                # Add to chat history
                chat_history.append((query, answer))
                
                # Keep chat history manageable (last 10 exchanges)
                if len(chat_history) > 10:
                    chat_history = chat_history[-10:]
                    
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        print("Please check your environment variables and try again.")

if __name__ == "__main__":
    main()