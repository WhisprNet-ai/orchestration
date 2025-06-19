from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain  # ✅ correct
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.prompts import ChatPromptTemplate
from retrieval.vectorstore import get_vectorstore
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from dotenv import load_dotenv
import os

load_dotenv()

def get_rag_chain():
    """Create and return the complete RAG chain with history awareness."""
    try:
        # Initialize LLM
        llm = ChatNVIDIA(
            model="meta/llama3-70b-instruct", 
            api_key=os.getenv("NVIDIA_API_KEY")
        )
        
        # Get vectorstore and retriever
        vectorstore = get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        
        # Create prompts
        contextualize_q_prompt = ChatPromptTemplate.from_template(
            """Given the chat history and the latest user question, 
            formulate a standalone question that can be understood without the chat history.
            
            Chat History: {chat_history}
            Latest Question: {input}
            
            Standalone Question:"""
        )
        
        qa_prompt = ChatPromptTemplate.from_template(
            """You are a helpful assistant. Use the following context to answer the question.
            If you don't know the answer based on the context, say so.
            
            Context: {context}
            
            Question: {input}
            
            Answer:"""
        )
        
        # Create chains
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )
        
        qa_chain = create_stuff_documents_chain(llm, qa_prompt)
        
        rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)
        
        return rag_chain
        
    except Exception as e:
        print(f"❌ Error creating RAG chain: {e}")
        raise