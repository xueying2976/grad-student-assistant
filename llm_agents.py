import requests
import urllib.parse
from flask import Flask, request, jsonify
from llmproxy import generate, pdf_upload
from datetime import datetime
import agent_tools
import re

# ROUTER AGENTa
# Classify user message request and route to correct response
def router_agent(query, sessionID):
    """
    Uses LLM to classify the user's question into one of six categories.
    """
    

    cs_programs = ["Artificial Intelligence", "Bioengineering", "Computer Engineering", "Computer Science", 
                        "Cybersecurity", "Data Science", "Human-Robot Interaction", "Software Systems Developement"]
    router_system = f"""
    You are a Tufts University Advisor in the Computer Science Department.
    The Computer Science Department covers all undergraduate, graduate and PhD degrees including but limited to {', '.join(cs_programs)}

    Your job is two produce two parameter: Catgory and Prompt. Your response needs to be in the format of "CATEGORY(PROMT)".

    ## Prompt ##
    Your job for this parameter is to analyze the user request, which might be vague, and produce a more effective, clear and complete query statement
    that is equal in intent to user's original query but formatted for better processing and understanding.
    Example vague prompt: who teaches cs150
    Example effective prompt: Who is the professor that is teaching the course CS 150 during this current semester?

    ## Category ##
    Your job for this parameter is to analyze the newly created effective prompt and classify the prompt in one the following categories:
    1. WELCOME - the user salutes
    2. CAPABILITIES - the user asks what you can do.
    3. PLANNING - the user want to help selecting courses based on credits, interests, or time constrains.
    4. COURSE - the user asks information about an specific course, such as: syllabus inquiry, gradin policies prerequisites, time schedule, title or professor. 
      If the question contains a course code like "CS-XXX" or "CSXXXX", where "CS" is followed by 2-5 digits (e.g. CS-0004 is a course), make sure it is categorized to COURSE. 
    5. CLARIFY - you are not clear about user's question or intent, need to ask further question for clarification. If you can inmply If the user's question is ambiguous but you can infer what they might be asking, include an additional response:
      However, I guess you might be asking: <your best guess at their intended question. Then, attempt to answer the guessed question>.
    6. INVALID - the user asks questions outside computer science, cs department contact information and the available tools.

    ## Response Instructions ##
    Always produce a prompt and category for the response.
    Strictly only respond with the category's name and prompt parameters in the format of "CATEGORY(PROMT)"; See the examples below.
    - Exmaple response: WELCOME(Hi! How can I assist you today?)
    """

    response = generate(
        model="4o-mini",
        system=router_system,
        query=query,
        temperature=0.5,
        lastk=20,
        session_id=sessionID
    )
    
    if isinstance(response, dict):
        response = response['response']

    category, prompt = agent_tools.category_prompt_re_match(response)

    print(f"Category: {category}\nPrompt: {prompt}")

    return category, prompt


# COURSE INFORMATION AGENT
def course_agent(query, sessionID):
    query_with_rag_context = agent_tools.query_rag_context(query)

    print(query_with_rag_context)

    response_text = generate(
        model = '4o-mini',
        system = f"""                                  
        You are a Tufts University Advisor in the Computer Science Department.

        Your role is to provide **clear, structured, and informative** answers to students' course-related questions.

        When responding:
        - **Answer the question directly** using only the provided **retrieval-augmented generation (RAG) data**.
        - **DO NOT** make up any information. If the requested information is not in the RAG source, explicitly state:  
        `"I do not have this information in my available data."`
        - **Use bullet points, tables, and formatting** to enhance readability.
        - **If the user's question is unclear**, ask for clarification (e.g., preferred semester, professor name).
        - **ALWAYS provide at least one follow-up question** to encourage further discussion.
        - Use appropriate emojis in your response to enhance readability and make the schedule visually engaging.
        - If you can inmply If the user's question is ambiguous but you can infer what they might be asking, include an additional response:
        However, I guess you might be asking: //your best guess at their intended question. Then, attempt to answer the guessed question.


        📌 **Follow-Up Formatting Rule:**  
        - The follow-up question **must** be formatted as follows, it can be related to course information or time planning,ensuring the topic is specific enough to provide a direct answer. :
        Follow-Up (visible): Would you like to know [specific topic]?
        Follow-Up (bot format): I want to know [specific topic].
        
        - The **visible follow-up** should be conversational for readability.  
        - The **bot format** should be directly actionable and understandable for automated queries.  

        ⚠️ **Important:**  
        - **DO NOT** use "Would you like to" in the bot-processing format.  
        - Ensure both formats appear in the response for easy extraction.  

        """,
        query = query_with_rag_context,
        temperature=0.3,
        lastk=20,
        session_id=sessionID
    )
    
    if isinstance(response_text, dict):
        response_text = response_text["response"]

    # Extract the generated follow-up question
    visible_follow_up, bot_follow_up = extract_follow_up_question(response_text)

    response = {
        "text": response_text,  # Bot's full response including visible follow-up
        "attachments": []
    }

    # If a valid follow-up question exists, add a button
    if visible_follow_up and bot_follow_up:
        # remove bot-format line
        response['text'] = "\n".join(response['text'].splitlines()[:-1])
        # remove "(visible)"
        response['text'] = response['text'].replace("(visible)", "")
        
        response["attachments"].append({
            "title": "Follow-Up Question",
            "text": f"🔍 {visible_follow_up}",
            "actions": [
                {
                    "type": "button",
                    "text": "✅ Ask This Question",
                    "msg": bot_follow_up,  # Sends the "I want to know..." version
                    "msg_in_chat_window": True,
                    "msg_processing_type": "sendMessage"
                }
            ]
        })
    
    print(response)

    return response


def extract_follow_up_question(response_text):
    """
    Extracts both the visible and bot-format follow-up question from the response.
    """
    match = re.search(r'Follow-Up \(visible\): (.+?)\n.*?Follow-Up \(bot format\): (.+)', response_text, re.DOTALL)

    if match:
        visible_question = match.group(1).strip()
        bot_question = match.group(2).strip()
        return visible_question, bot_question
    else:
        return None, None  # No follow-up found

# PROGRAM INFORMATION AGENT
def program_agent(query, sessionID):
    query_with_rag_context = agent_tools.query_rag_context(query)

    print(query_with_rag_context)

    response_text = generate(
        model = '4o-mini',
        system = f"""
        You are a Tufts University Advisor in the Computer Science Department.

        Your role is to provide **clear, structured, and informative** answers to students' program-related questions.

        When responding:
        - **Answer the question directly** using only the provided **retrieval-augmented generation (RAG) data**.
        - **DO NOT** make up any information. If the requested information is not in the RAG source, explicitly state:  
        `"I do not have this information in my available data."`
        - **Use bullet points, tables, and formatting** to enhance readability.
        - **If the user's question is unclear**, ask for clarification.
        - **ALWAYS provide at least one follow-up question** to encourage further discussion.
        - Use appropriate emojis in your response to enhance readability and make the schedule visually engaging.

        📌 **Follow-Up Formatting Rule:**  
        - The follow-up question **must** be formatted as follows, it can be related to course information or time planning  or program information,ensuring the topic is specific enough to provide a direct answer. :
        Follow-Up (visible): Would you like to know [specific topic]?
        Follow-Up (bot format): I want to know [specific topic].
        
        - The **visible follow-up** should be conversational for readability.  
        - The **bot format** should be directly actionable and understandable for automated queries.  

        ⚠️ **Important:**  
        - **DO NOT** use "Would you like to" in the bot-processing format.  
        - Ensure both formats appear in the response for easy extraction.  

        """,
        query = query_with_rag_context,
        temperature=0.3,
        lastk=20,
        session_id=sessionID
    )
    if isinstance(response_text, dict):
        response_text = response_text["response"]

    # Extract the generated follow-up question
    visible_follow_up, bot_follow_up = extract_follow_up_question(response_text)

    response = {
        "text": response_text,  # Bot's full response including visible follow-up
        "attachments": []
    }

    # If a valid follow-up question exists, add a button
    if visible_follow_up and bot_follow_up:
        # remove bot-format line
        response['text'] = "\n".join(response['text'].splitlines()[:-1])
        # remove "(visible)"
        response['text'] = response['text'].replace("(visible)", "")
        
        response["attachments"].append({
            "title": "Follow-Up Question",
            "text": f"🔍 {visible_follow_up}",
            "actions": [
                {
                    "type": "button",
                    "text": "✅ Ask This Question",
                    "msg": bot_follow_up,  # Sends the "I want to know..." version
                    "msg_in_chat_window": True,
                    "msg_processing_type": "sendMessage"
                }
            ]
        })
    
    print(response)

    return response

# CONTACT INFORMATION AGENT
def contact_agent(query, sessionID):
    search_results = agent_tools.web_search(query)
    print(search_results)

    response = generate(
        model = "4o-mini",
        system = f"""
            You are a Tufts University Advisor in the Computer Science Department.
            Your job is to make a concise and clear response to the user prompt given the provided context.
            """,
        query = f"""
                User prompt: 
                {query}

                Context:
                {str(search_results)}
                """,
        temperature=0.3,
        lastk=20,
        session_id=sessionID,
    )

    print(f'Contact Response: {response}')

    return response['response']



def process_bot_message(user_message, user_name):
    """
    Handles bot commands like "send_to_advisor" and sends messages accordingly.
    """
    if user_message.startswith("send_to_advisor:"):
        planning_details = user_message.replace("send_to_advisor:", "").strip()

        # Define the advisor's username
        advisor_username = "cs_advisor"  # Replace with the actual username

        # Send the message using message_user function
        message_user(f"📌 Student Course Planning Request:\n\n{planning_details}", advisor_username)

        return {
            "text": "✅ Your course planning has been sent to your advisor!",
            "msg_in_chat_window": True
        }

    return None


def planning_agent(query, sessionID):
    query_with_rag_context = agent_tools.query_rag_context(query)

    print(query_with_rag_context)

    response_text = generate(
        model = '4o-mini',
        system = f"""
                You are a Tufts University Advisor in the Computer Science Department.
                Your job is to provide the user with the requested program information.
                Given the user's prompt and provided context, give a good response.
                Provide a structured and visually engaging response. 
                Use bullet points, tables, and relevant emojis to enhance readability.
                
                
                
                You are a Tufts University Advisor in the Computer Science Department.

                Your role is to provide **clear, structured, and informative** answers to students' planning-related questions.

                When responding:
                - **Answer the question directly** using only the provided **retrieval-augmented generation (RAG) data**.
                - **DO NOT** make up any information. If the requested information is not in the RAG source, explicitly state:  
                `"I do not have this information in my available data."`
                - **Use bullet points, tables, and formatting** to enhance readability.
                - **If the user's question is unclear**, ask for clarification.
                - **ALWAYS provide at least one follow-up question** to encourage further discussion.
                - If the user asks for the class planning, try to provide details down to the content of each session.
                - When providing the class schedule, format the response as a daily plan. For each day, list the course name, time, and content description.
                - Use appropriate emojis in your response to enhance readability and make the schedule visually engaging.

                📌 **Follow-Up Formatting Rule:**  
                - The follow-up question **must** be formatted as follows, it can be related to course information or time planning  or program information,ensuring the topic is specific enough to provide a direct answer:
                Follow-Up (visible): Would you like to know [specific topic]?
                Follow-Up (bot format): I want to know [specific topic].
                
                - The **visible follow-up** should be conversational for readability.  
                - The **bot format** should be directly actionable and understandable for automated queries.  

                ⚠️ **Important:**  
                - **DO NOT** use "Would you like to" in the bot-processing format.  
                - Ensure both formats appear in the response for easy extraction.  
                
                """,
        query = query_with_rag_context,
        temperature=0.3,
        lastk=20,
        session_id=sessionID
    )

    if isinstance(response_text, dict):
        response_text = response_text["response"]

    # Extract the generated follow-up question
    visible_follow_up, bot_follow_up = extract_follow_up_question(response_text)

    response = {
        "text": response_text,  # Bot's full response including visible follow-up
        "attachments": []
    }

    # If a valid follow-up question exists, add a button
    if visible_follow_up and bot_follow_up:
        # remove bot-format line
        response['text'] = "\n".join(response['text'].splitlines()[:-1])
        # remove "(visible)"
        response['text'] = response['text'].replace("(visible)", "")
        
        response["attachments"].append({
            "title": "Follow-Up Question",
            "text": f"🔍 {visible_follow_up}",
            "actions": [
                {
                    "type": "button",
                    "text": "✅ Ask This Question",
                    "msg": bot_follow_up,  # Sends the "I want to know..." version
                    "msg_in_chat_window": True,
                    "msg_processing_type": "sendMessage"
                }
            ]
        })
        
        
    
    print(response)

    return response


locationId = 102380872
x_rapidapi_host = 'linkedin-data-api.p.rapidapi.com'
x_rapidapi_key = 'cfd585ecdemshc2f7759959ed435p17fa0fjsn4ba89051e09f'

# def job_agent(query, sessionID):
#     skill = generate(
#         model="4o-mini",
#         system='''You'll be provided with a class name and a description of the class.
#         Repsond with a single word or phrase that is the key skill or concept that the class teaches.
#         ''',
#         query=query,
#         temperature=0,
#         lastk=1024,
#         session_id=sessionID,
#     )
#     if isinstance(skill, dict):
#         skill = skill['response']

#     print(f'Skill identified: {skill}')
    
#     encoded_skill = urllib.parse.quote(skill)
#     linkedin_url = f"https://linkedin-data-api.p.rapidapi.com/search-jobs-v2?locationId={locationId}&keywords={encoded_skill}&datePosted=anyTime&sort=mostRelevant"
#     jobs = requests.get(linkedin_url, headers={
#         'x-rapidapi-key': x_rapidapi_key,
#         'x-rapidapi-host': x_rapidapi_host,
#     })

#     response = generate(
#         model="4o-mini",
#         system='''You'll be provided with a list of jobs that are related to the skill or concept that you provided.
#         Show the list of jobs in the most readable way possible and at the same time be specific about the jobs, 
#         and summarize the jobs in a single sentence.
#         ''',
#         query=f'''Show the list of jobs in the most readable way possible, and summarize the jobs in a single sentence.
        
#         {jobs.text}
#         ''',
#         temperature=0,
#         lastk=1024,
#         session_id=sessionID,
#     )
    
#     if isinstance(response, dict):
#         return response['response']

#     return response
