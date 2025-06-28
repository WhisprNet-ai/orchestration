from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.prompts import ChatPromptTemplate
from retrieval.vectorstore import get_vectorstore
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.documents import Document
from dotenv import load_dotenv
import uuid
import os
import sys
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

def get_rag_chain(user_id: str):
    """
    Returns a callable process_user_input(user_input: str, chat_history: list)
    that implements enhanced RAG with ChromaDB, similarity checking, and proper formatting.
    """
    try:
        # Load NVIDIA LLM
        llm = ChatNVIDIA(
            model="meta/llama3-70b-instruct",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
        formatter_llm = llm

        vectorstore = get_vectorstore()

        # 1. Format User Input Prompt
        format_prompt = ChatPromptTemplate.from_template("""
You are a rewriting assistant. Rephrase the user's message to be grammatically correct, structured, and clear.

Rules:
- Do NOT add new info.
- Combine attributes (e.g. experience, skills, job type).
- Example: "hi iam manoj kumar i  need a backend dev of 5 years experience, and as a remote employee"
  becomes → "I need a backend developer with 5 years of experience, working remotely."

Original Message: {message}

Rewrite:
""")

        # 2. History-Aware Question Creation Prompt
        contextualize_q_prompt = ChatPromptTemplate.from_template("""
Given the chat history and the latest user question, 
formulate a standalone question that can be understood without the chat history.

Chat History: {chat_history}
Latest Question: {input}

Standalone Question:
""")

        # 3. QA Prompt for RAG
        qa_prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. Use the following context to answer the question.
If the answer is not in the context, say you don't know.

Context: {context}
Question: {input}

Answer:
""")

        # Create retriever with user_id filter
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5, "filter": {"user_id": user_id}})
        
        # Create history-aware retriever
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )

        # Create QA chain
        qa_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

        def process_user_input(user_input: str, chat_history: list):
            """
            Process user input with enhanced RAG functionality.
            
            Args:
                user_input: Raw user input string
                chat_history: List of previous chat messages
                
            Returns:
                dict: Contains formatted_query, chat_context, and response
            """
            try:
                # Step 1: Format User Input
                print(f" Formatting user input: {user_input}")
                formatted_query = formatter_llm.invoke(
                    format_prompt.format(message=user_input)
                ).content
                print(f" Formatted query: {formatted_query}")

                # Step 2: Check Similarity in Chroma
                print(" Checking for similar messages in ChromaDB...")
                similar_docs = vectorstore.similarity_search_with_score(
                    query=formatted_query,
                    k=5,
                    filter={"user_id": user_id}
                )
                
                is_duplicate = False
                chat_context = ""
                
                # Check if any similarity > 0.9 (consider as duplicate)
                for doc, score in similar_docs:
                    if score > 0.8:
                        print(f"⚠️  Similar message found with score {score:.3f}: {doc.page_content}")
                        is_duplicate = True
                        # Retrieve matching messages for context
                        matching_docs = vectorstore.similarity_search(
                            query=doc.page_content,
                            k=10,
                            filter={"user_id": user_id}
                        )
                        chat_context = "\n".join([d.page_content for d in matching_docs])
                        break
                
                if not is_duplicate:
                    print("✅ No similar messages found, retrieving all user history")
                    # Retrieve all past messages for this user_id using ChromaDB get method
                    try:
                        # Get all documents for this user from ChromaDB collection
                        collection = vectorstore._collection
                        results = collection.get(where={"user_id": user_id})
                        
                        if results and results['documents']:
                            chat_context = "\n".join(results['documents'])
                        else:
                            chat_context = ""
                            
                    except Exception as e:
                        print(f"⚠️  Could not retrieve user history: {e}")
                        chat_context = ""

                # Step 3: Store Message in Vector DB
                chat_id = str(uuid.uuid4())
                timestamp = datetime.datetime.now().isoformat()
                
                print(f" Storing formatted message in ChromaDB...")
                vectorstore.add_documents([
                    Document(
                        page_content=formatted_query,
                        metadata={
                            "user_id": user_id,
                            "chat_id": chat_id,
                            "timestamp": timestamp
                        }
                    )
                ])
                print(f"Stored with chat_id: {chat_id}")

                # Step 4: History-Aware Question Creation
                print(" Creating history-aware question...")
                standalone_question = llm.invoke(
                    contextualize_q_prompt.format(
                        chat_history=chat_context,
                        input=formatted_query
                    )
                ).content
                print(f"✅ Standalone question: {standalone_question}")

                # Step 5: Answer Using RAG
                print("🤖 Generating RAG response...")
                rag_result = rag_chain.invoke({
                    "input": formatted_query,
                    "chat_history": chat_context
                })
                
                raw_response = rag_result["answer"]
                print(f"📄 Raw RAG response: {raw_response}")

                # Step 6: Format Final Output
                print("🎨 Formatting final response...")
                # Create a specific prompt for response formatting
                response_format_prompt = ChatPromptTemplate.from_template("""
You are a response synthesizer. Using only the information from the `formatted_query` and the `chat_context`, create one simple, grammatically correct sentence that clearly reflects the intent.

 Strict Rules:
- Only use words, phrases, or entities found in `formatted_query` and `chat_context`
- Do NOT introduce any new information
- Do NOT make assumptions or generate additional details
- If the sentence is already clear, return it as is
- Your response should be useful for intent detection
- Output only one sentence

Formatted Query:
{formatted_query}

Chat Context:
{chat_context}

Response:
""")
                
                final_output = formatter_llm.invoke(
    response_format_prompt.format(
        formatted_query=formatted_query,
        chat_context=chat_context
    )
).content

                print(f"✅ Final formatted response: {final_output}")

                # Return structured response
                return {
                    "formatted_query": formatted_query,
                    "chat_context": chat_context,
                    "response": final_output
                }

            except Exception as e:
                print(f"❌ Error in process_user_input: {e}")
                raise

        return process_user_input

    except Exception as e:
        print(f"❌ Error creating RAG chain: {e}")
        raise
