import os
import json
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document

load_dotenv()

def get_vectorstore():
    from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
    embeddings = NVIDIAEmbeddings(
        model="nvidia/embed-qa-4",
        api_key=os.getenv("NVIDIA_API_KEY")
    )
    persist_directory = os.getenv("CHROMA_DIR", "./chroma_store")
    return Chroma(
        collection_name="rag_chroma",
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

def store_job_description(job_json_path="job_descp.json"):
    try:
        if not os.path.exists(job_json_path):
            return {"error": f"{job_json_path} not found"}

        with open(job_json_path, "r", encoding="utf-8") as f:
            job_data = json.load(f)

        user_id = job_data.get("user_id")
        job_desc = job_data.get("job_desc", "").strip()

        if not user_id or not job_desc:
            return {"error": "Missing user_id or job_desc in job_descp.json"}

        vectorstore = get_vectorstore()

        # Wrap the job description in a Document with metadata
        doc = Document(page_content=job_desc, metadata={"user_id": user_id})
        vectorstore.add_documents([doc])

        return {"status": "Job description stored successfully"}

    except Exception as e:
        return {"error": str(e)}

def alter_job_description_with_reply(user_id: str, reply_json_path="reply.json"):
    try:
        # Load the reply
        if not os.path.exists(reply_json_path):
            return {"error": f"{reply_json_path} not found"}

        with open(reply_json_path, "r", encoding="utf-8") as f:
            reply_data = json.load(f)

        reply_text = reply_data.get("reply", "").strip()
        if not reply_text:
            return {"error": "Reply text is empty in reply.json"}

        # Initialize vectorstore and LLM
        vectorstore = get_vectorstore()
        formatter_llm = ChatNVIDIA(
            model="meta/llama3-70b-instruct",
            api_key=os.getenv("NVIDIA_API_KEY")
        )

        # Retrieve job description
        job_docs = vectorstore.get(where={"user_id": user_id})
        if not job_docs['documents']:
            return {"error": f"No job description found for user_id: {user_id}"}
        job_desc = job_docs['documents'][0]

        # Prompt template
        alter_prompt = ChatPromptTemplate.from_template("""You are a smart rewriting assistant.

Use the user's reply to update the given job description accordingly.

Instructions:
- ONLY update fields like title, skills, experience, or location based on the reply.
- DO NOT add fictional or speculative information.
- MAINTAIN original job formatting, professionalism, and clarity.
- Your output should start **directly with the revised job description**. Do NOT include introductory text like "Here is the updated job description".

                                                        

User's Reply:
{reply}

Original Job Description:
{job_desc}

Updated Job Description:
""")

        # Rewrite
        updated_job_desc = formatter_llm.invoke(
            alter_prompt.format(reply=reply_text, job_desc=job_desc)
        ).content

        return {
            "new_job_description": updated_job_desc
        }

    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# MAIN EXECUTION BLOCK
# -------------------------------
if __name__ == "__main__":
    # Step 1: Store the job description from JSON
    store_result = store_job_description("job_descp.json")
    print("Store Result:", store_result)

    # If storing succeeded, proceed to alter job description
    if "error" not in store_result:
        result = alter_job_description_with_reply("1234", "reply.json")
        print("\nAltered Job Description Result:\n", result)

        # Save result to output.json
        if "new_job_description" in result:
            try:
                with open("output.json", "w", encoding="utf-8") as f:
                    json.dump({"user_id": "1234", "altered_job_desc": result["new_job_description"]}, f, indent=2, ensure_ascii=False)
                print("✅ Altered job description saved to output.json")
            except Exception as e:
                print("❌ Failed to save output.json:", str(e))
        else:
            print("❌ No altered job description to save.")
    else:
        print("Skipping alteration due to error in storing.")
