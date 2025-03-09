import requests
import urllib.parse
from flask import Flask, request, jsonify
from llmproxy import generate, pdf_upload
from datetime import datetime
import agent_tools
import re

# ROUTER AGENT
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
    2. CAPABILITIES - the user asks what can you do.
    3. PROGRAM - the user asks questions about credit requirement, academic rules, or degree requirements.
    4. PLANNING - the user want to help selecting courses based on credits, interests, or time constrains.
    5. COURSE - the user asks information about an specific course, such as: syllabus inquiry, gradin policies prerequisites, time schedule, title or professor.
    6. CLARIFY - you are not clear about user's question or intent, need to ask further question for clarification.
    7. CONTACT - the user needs information to contact cs department, such as: email address, phone number, address, website link, faculty.
    8. MESSAGE DPT - the user explicitly states that wants to send a message to the CS Department.
    9. JOB - the user explicitly requests job recommendations related to a certain class; If the user mentioned [job] wrods, make sure it is categorized into Job. if no specific class name or class description is provided, it should fall into the CLARIFY category.
    10. INVALID - the user asks questions outside computer science, cs department contact information and the available tools.

    ## Response Instructions ##
    Always produce a prompt and category for the response.
    Strictly only respond with the category's name and prompt parameters in the format of "CATEGORY(PROMT)"; See the examples below.
    - Example response 1: PROGRAM(What are the degree requirements for M.S. in Cybersecurtiy program?)
    - Exmaple response 2: WELCOME(Hi! How can I assist you today?)
    """

    response = generate(
        model="4o-mini",
        system=router_system,
        query=query,
        temperature=0.5,
        lastk=100,
        session_id=sessionID
    )

    category, prompt = agent_tools.category_prompt_re_match(response)

    print(f"Category ({category}), prompt: {prompt}")

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
        - **Directly answer** the user's question with relevant details.
        - **Use bullet points, tables, and appropriate emojis** for readability.
        - **Ask for clarification** if the query lacks details (e.g., preferred class days, required subjects).
        - **ALWAYS provide at least one follow-up question** at the end of your response.

        📌 **Follow-Up Formatting Rule:**  
        - The follow-up question **must** be formatted as follows:
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
        "response": response_text,  # Bot's full response including visible follow-up
        "attachments": []
    }

    # If a valid follow-up question exists, add a button
    if visible_follow_up and bot_follow_up:
        # remove bot-format line
        response['response'] = "\n".join(response['response'].splitlines()[:-1])
        # remove "(visible)"
        response['response'] = response['response'].replace("(visible)", "")
        
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

    return response['response']


def extract_follow_up_question(response_text):
    """
    Extracts both the visible and bot-format follow-up question from the response.
    """
    match = re.search(r'Follow-Up \(visible\): (.+?)\nFollow-Up \(bot format\): (.+)', response_text, re.DOTALL)

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

    response = generate(
        model = '4o-mini',
        system = f"""
                You are a Tufts University Advisor in the Computer Science Department.

                Your job is to provide the user with the requested program information.

                Given the user's prompt and provided context, give a good response.
                
                Provide a structured and visually engaging response. 
                
                Use bullet points, tables, and relevant emojis to enhance readability.
                
                Use appropriate emojis in your response to enhance readability and make the schedule visually engaging.
                
                After you finish answering the question, give related suggested follow-up question.
                
                
                

                
                """,
        query = query_with_rag_context,
        temperature=0.3,
        lastk=20,
        session_id=sessionID
    )

    print(response)

    return response['response']

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


def planning_agent(query, sessionID):
    query_with_rag_context = agent_tools.query_rag_context(query)

    print(query_with_rag_context)

    response = generate(
        model = '4o-mini',
        system = f"""
                You are a Tufts University Advisor in the Computer Science Department.
                Your job is to provide the user with the requested program information.
                Given the user's prompt and provided context, give a good response.
                Provide a structured and visually engaging response. 
                Use bullet points, tables, and relevant emojis to enhance readability.
                If the user asks for the class planning, try to provide details down to the content of each session.
                When providing the class schedule, format the response as a daily plan. For each day, list the course name, time, and content description.
                Use appropriate emojis in your response to enhance readability and make the schedule visually engaging.
                after you finish answering the question, give related suggested follow-up question.
                """,
        query = query_with_rag_context,
        temperature=0.3,
        lastk=20,
        session_id=sessionID
    )

    print(response)
    
    if isinstance(response, str):
        return response

    return response['response']


locationId = 102380872
x_rapidapi_host = 'linkedin-data-api.p.rapidapi.com'
x_rapidapi_key = 'cfd585ecdemshc2f7759959ed435p17fa0fjsn4ba89051e09f'

def job_agent(query, sessionID):
    skill = generate(
        model="4o-mini",
        system='''You'll be provided with a class name and a description of the class.
        Repsond with a single word or phrase that is the key skill or concept that the class teaches.
        ''',
        query=query,
        temperature=0,
        lastk=1024,
        session_id=sessionID,
    )
    if isinstance(skill, dict):
        skill = skill['response']

    print(f'Skill identified: {skill}')
    
    encoded_skill = urllib.parse.quote(skill)
    linkedin_url = f"https://linkedin-data-api.p.rapidapi.com/search-jobs-v2?locationId={locationId}&keywords={encoded_skill}&datePosted=anyTime&sort=mostRelevant"
    jobs = requests.get(linkedin_url, headers={
        'x-rapidapi-key': x_rapidapi_key,
        'x-rapidapi-host': x_rapidapi_host,
    })

    response = generate(
        model="4o-mini",
        system='''You'll be provided with a list of jobs that are related to the skill or concept that you provided.
        Show the list of jobs in the most readable way possible and at the same time be specific about the jobs, 
        and summarize the jobs in a single sentence.
        ''',
        query=f'''Show the list of jobs in the most readable way possible, and summarize the jobs in a single sentence.
        
        {jobs.text}
        ''',
        temperature=0,
        lastk=1024,
        session_id=sessionID,
    )
    
    if isinstance(response, dict):
        return response['response']

    return response


