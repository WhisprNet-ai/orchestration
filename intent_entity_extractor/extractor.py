from langchain.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from maya_agent.naveens_agent import naveen
import json

# Define the full prompt template
def intent_entity_processor(data): 
    for list in data:
        print(f"\nProcessing user: {list.get('username', 'Unknown')}")
        message = list['response']
        print(f"Message: {message}")
        
        intent_entity_response = intent_entity_extractor(message)
        print(f"Raw intent extraction: {intent_entity_response}")
        
        try:
            response_dict = json.loads(intent_entity_response)
            print(f"Parsed entities: {response_dict.get('entities', {})}")
            
            # Add company details
            response_dict['entities']['company'] = 'whisprnet.ai'
            response_dict['entities']['url'] = 'http://linkedin.com'
            response_dict['entities']['city'] = 'pondicherry'
            response_dict['entities']['state'] = 'pondicherry'
            response_dict['entities']['mail'] = 'whisprnet.ai'
            response_dict['entities']['education'] = 'btech/mtech'
            
            # Add user metadata
            response_dict["user_id"] = list["user_id"]
            response_dict["username"] = list["username"]
            response_dict["app_id"] = list["app_id"]
            response_dict["channel_id"] = list["channel_id"]
            response_dict["session_id"] = list["session_id"]
            
            # Send to job posting system
            naveen(response_dict)
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse intent extraction JSON: {e}")
            print(f"Raw response: {intent_entity_response}")
        except Exception as e:
            print(f"Error in intent processing: {e}")
    
    print("="*80)
    print("INTENT ENTITY PROCESSOR - Completed")
    print("="*80)

def intent_entity_extractor(message):
    print("to... intent entity extractor")
    print(message)
    print("####")
    prompt = ChatPromptTemplate.from_template("""
    CONVERSATION:
    {message_batch}

    TASK: Analyze the conversation and extract the following information in JSON format:

    {{
     "intent": "hiring_request" | "non_hiring",
     "entities": {{
         "job_title": "exact job title mentioned or null",
         "skills": "comma-separated list of required skills or null",
         "experience": "experience requirement (e.g., '3+ years', 'Senior level') or null",
         "location": "job location (city, state, hybrid) or null",
         "job_type": "employment type (full-time, part-time,remote, contract, internship) or null",
         "expiration_date": "application deadline if mentioned or null",
         "number_of_people": "number of positions to fill or null"
     }}
     }}

 GUIDELINES:
 - Set intent to "hiring_request" if discussing job postings, recruitment, or hiring needs
 - Set intent to "non_hiring" for general questions, support issues, or non-recruitment topics
 - Extract entities ONLY if explicitly mentioned - use null for missing information
 - For skills, include both technical and soft skills mentioned
 - For experience, capture years, level (junior/senior), or specific requirements
 - For location, include remote work arrangements if mentioned
 - Be precise - don't infer or assume information not explicitly stated

 RESPONSE: Return only valid JSON, no additional text:
 """)

    # Setup NVIDIA LLM
    formatter_llm = ChatNVIDIA(
        model="meta/llama3-70b-instruct",
        api_key="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"
    )

    # Format the prompt
    formatted_prompt = prompt.format_messages(message_batch=message)

    # Invoke the model
    response = formatter_llm.invoke(formatted_prompt)

    # Print just the content
    print(response.content)
    return response.content
