import json
import uuid

import datetime
from dotenv import load_dotenv
from collections import defaultdict
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.documents import Document
from .retrieval.vectorstore import get_vectorstore
from intent_entity_extractor.extractor import intent_entity_processor

import sys
import os

# Dynamically add the root directory to sys.path
current_file = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)



# Load environment variables
load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Shared LLM for formatting
formatter_llm = ChatNVIDIA(
    model="meta/llama3-70b-instruct",
    api_key="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"
)

# Formatting prompt for batching
format_prompt = ChatPromptTemplate.from_template("""
You are a rewriting assistant. Your job is to intelligently combine multiple user messages into one clear, structured, and grammatically correct sentence reflecting the user's job intent.

Rules:
- Combine job-related details: role, skills, experience, location, job type.
- Include **any numeric experience** (e.g. "5 yrs", "3+ years", etc.) even if phrased vaguely.
- Do NOT skip or assume information — only use what's mentioned.
- Ignore greetings or casual words like "hi", "hello", "need job".
- Output should be a single clear sentence.

📘 Examples:

Messages:
- "frontend"
- "5 yrs"
- "remote job"

Combined Output:
"I am looking for a remote frontend developer role with 5 years of experience."

Messages:
- "backend"
- "node"
- "3+ yrs exp"
- "hybrid"

Combined Output:
"I want a hybrid backend developer role with over 3 years of experience in Node.js."

Messages:
{messages}

Combined Output:
""")


def get_rag_chain(user_id: str):
    llm = ChatNVIDIA(
        model="meta/llama3-70b-instruct",
        api_key="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"
    )
    vectorstore = get_vectorstore()

    contextualize_q_prompt = ChatPromptTemplate.from_template("""
Given a clumsy chat history and a vague or informal user message, rephrase it into a clear, standalone, and grammatically correct question.

Rules:
- Assume the user is casually expressing their needs or intentions.
- Correct grammar, spelling, and structure.
- Preserve all information, especially skills, experience, and job type.
- Do NOT hallucinate or add new info.

Chat History:
{chat_history}

Latest Input:
{input}

Standalone Question:
""")

    qa_prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. Use the provided context to accurately answer the user's intent or question.

Rules:
- Expect informal, shorthand, or clumsy user input.
- Extract meaning and match relevant context.
- If context lacks required info, respond with: "Sorry, I don't have enough information."

Context:
{context}

User Input:
{input}

Answer:
""")

    response_format_prompt = ChatPromptTemplate.from_template("""
You are a sentence optimizer. Your job is to synthesize a single, clear, grammatically correct sentence summarizing the user's intent.

Strict Rules:
- Input may be clumsy, broken, or shorthand — fix grammar, spelling, structure.
- Only use the information found in `formatted_query` and `chat_context`.
- Do NOT invent or guess anything.
- Combine related data (skills, experience, job type) logically.
- Output only one sentence.

Formatted Query:
{formatted_query}

Chat Context:
{chat_context}

Final Intent:
""")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5, "filter": {"user_id": user_id}})
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    def process_user_input(formatted_query: str) -> dict:
        similar_docs = vectorstore.similarity_search_with_score(
            query=formatted_query,
            k=5,
            filter={"user_id": user_id}
        )

        # chat_context = ""
        # is_duplicate = any(score > 0.9 for _, score in similar_docs)

        # if is_duplicate:
        #     matched_doc = similar_docs[0][0]
        #     matching_docs = vectorstore.similarity_search(
        #         query=matched_doc.page_content,
        #         k=10,
        #         filter={"user_id": user_id}
        #     )
        #     chat_context = "\n".join([d.page_content for d in matching_docs])
        # else:
        try:
            collection = vectorstore._collection
            user_docs = collection.get(where={"user_id": user_id})
            chat_context = "\n".join(user_docs.get("documents", [])) if user_docs else ""
            print("retriveing past data from rag")
            print(chat_context)
            print("#####")
        except Exception:
            chat_context = ""

        vectorstore.add_documents([
            Document(
                page_content=formatted_query,
                metadata={
                    "user_id": user_id,
                    "chat_id": str(uuid.uuid4()),
                    "timestamp": datetime.datetime.now().isoformat()
                }
            )
        ])

        # Generate final RAG response
        rag_result = rag_chain.invoke({
            "input": formatted_query,
            "chat_history": chat_context
        })

        # Final formatting
        final_output = llm.invoke(
            response_format_prompt.format(
                formatted_query=formatted_query,
                chat_context=chat_context
            )
        ).content

        return {
            "formatted_query": formatted_query,
            "chat_context": chat_context,
            "response": final_output
        }

    return process_user_input


def process_messages(json_data: dict) -> list:
    messages = json_data.get("messages", [])
    user_messages = defaultdict(list)
    user_meta = {}
    results = []
    handlers = {}

    for msg in messages:
        uid = msg.get("user_id")
        if not uid:
            continue

        text = msg.get("text", "").strip()
        if text:
            user_messages[uid].append(text)

        # Store metadata only once per user
        if uid not in user_meta:
            user_meta[uid] = {
                "user_id": uid,
                "username": msg.get("username", ""),
                "app_id": msg.get("app_id", ""),
                "channel_id": msg.get("channel_id", ""),
                "session_id": msg.get("session_id", "")
            }

    for user_id, message_list in user_messages.items():
        try:
            combined_text = "\n- " + "\n- ".join(message_list)
            formatted_query = formatter_llm.invoke(
                format_prompt.format(messages=combined_text)
            ).content

            if user_id not in handlers:
                handlers[user_id] = get_rag_chain(user_id)

            response_data = handlers[user_id](formatted_query)
            user_meta[user_id]["response"] = response_data.get("response", "")

        except Exception as e:
            user_meta[user_id]["response"] = f"Error: {str(e)}"

        results.append(user_meta[user_id])
        print(results)

    intent_entity_processor(results)


# CLI usage
def formator_llm(input_data):
    
    output = process_messages(input_data)
    print(json.dumps(output, indent=2))

