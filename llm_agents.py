import requests
from flask import Flask, request, jsonify
from llmproxy import generate, pdf_upload
from datetime import datetime
import agent_tools

# ROUTER AGENT
# Classify user message request and route to correct response
def router_agent(query, sessionID):
    """
    Uses LLM to classify the user's question into one of six categories.
    """
    # classification_prompt = '''You are an AI assistant that categorizes course-related questions for Tufts graduate students. 
    #     Classify the following question into one of these six categories and return only a single digit:
    #     1 Program Requirements - Questions about credit requirements, academic rules, or degree requirements
    #     2 Course Planning - Selecting courses based on credits, interests, or time constraints
    #     3 Specific Course Info - Inquiring about syllabus, grading policy, prerequisites, or instructor details
    #     4 Career Relevance - Asking about how courses relate to job opportunities
    #     5 Bot Capabilities - Asking what this bot can do
    #     6 None of Above - If the question is too vague, suggest how to clarify it.'''
    cs_programs = ["Artificial Intelligence", "Bioengineering", "Computer Engineering", "Computer Science", 
                        "Cybersecurity", "Data Science", "Human-Robot Interaction", "Software Systems Developement"]
    router_system = f"""
    You are a Tufts University Advisor in the Computer Science Department.
    The Computer Science Department covers all undergraduate, graduate and PhD degrees including but limited to {', '.join(cs_programs)}

    Your job is two produce two parameter: Catgory and Prompt

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
    9. INVALID - the user asks questions outside computer science, cs department contact information and the available tools.

    ## Response Instructions ##
    - Always produce a prompt and category for the response.
    - Strictly only respond with the category's name and prompt parameters.
    - Example response: PROGRAM(What are the degree requirements for M.S. in Cybersecurtiy program?)
    - Exmaple response: WELCOME(Hi! How can I assist you today?)
    """

    response = generate(
        model="4o-mini",
        system=router_system,
        query=query,
        temperature=0.5,
        lastk=10
    )

    category, prompt = agent_tools.category_prompt_re_match(response)

    print(f"Category ({category}), prompt: {prompt}")

    return category, prompt

# COURSE INFORMATION AGENT
def course_agent(query, sessionID):
    query_with_rag_context = agent_tools.query_rag_context(query)

    print(query_with_rag_context)

    response = generate(
        model = '4o-mini',
        system = f"""
                You are a Tufts University Advisor in the Computer Science Department.

                Your job is to provide the user with the requested course information.

                Given the user's prompt and provided context, give a good response.
                
                You are a course selection advisor helping Tufts graduate students choose courses based on their academic interests, credit requirements, and scheduling constraints. "
                
                Provide a structured and visually engaging response that helps students select courses that fit their preferences. 
                
                If their question lacks details (e.g., preferred class days, required subjects), ask for clarification. 
                
                Use bullet points, tables, and relevant emojis to enhance readability.
                
                Use appropriate emojis in your response to enhance readability and make the schedule visually engaging.
                
                
                """,
        query = query_with_rag_context,
        temperature=0.3,
        lastk=20,
        session_id=sessionID
    )

    print(response)

    return response['response']

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