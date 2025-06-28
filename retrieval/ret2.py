from retrieval.vectorstore import get_vectorstore
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from dotenv import load_dotenv
import uuid
import os
import sys
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

def get_message_handler(user_id: str):
    try:
        vectorstore = get_vectorstore()

        def handle_message(user_input: str):
            cleaned_input = user_input.strip()

            # Step 1: Store current message
            vectorstore.add_documents([
                Document(
                    page_content=cleaned_input,
                    metadata={
                        "user_id": user_id,
                        "chat_id": str(uuid.uuid4()),
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                )
            ])

            # Step 2: Retrieve recent messages for this user
            user_docs = vectorstore.similarity_search(
                query="irrelevant",
                k=5,
                filter={"user_id": user_id}
            )

            user_docs = sorted(user_docs, key=lambda d: d.metadata.get("timestamp", ""))

            history = [doc.page_content for doc in user_docs]

            # Step 3: Generate prompt with history
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant that rewrites a user's current message by combining it with relevant past messages to form a complete, organized input."),
                ("human", "Previous messages: {history}\nCurrent message: {input}\n\nRewrite the current message by combining it with the previous ones to form a clear, complete sentence.")
            ])

            # Step 4: Prepare LLM
            formatter_llm = ChatNVIDIA(
                model="meta/llama3-70b-instruct",
                api_key=os.getenv("NVIDIA_API_KEY")
            )

            formatted_prompt = prompt.format_messages(history="\n".join(history), input=cleaned_input)
            response = formatter_llm.invoke(formatted_prompt)

            # Step 5: Return structured response
            return {
                "user_input": cleaned_input,
                "history": history,
                "rewritten": response.content.strip()
            }

        return handle_message

    except Exception as e:
        print(f"❌ Error in message handler: {e}")
        raise
