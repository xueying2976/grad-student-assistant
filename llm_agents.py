import requests
import urllib.parse
from flask import Flask, request, jsonify
from llmproxy import generate, pdf_upload
from datetime import datetime
import agent_tools
import re
import json

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
    0. INTRODUCTION - the user wants to start planning their courses and needs guidance on what to provide. This category should be triggered when the user says  "introduction to shedule" without giving details.
    1. WELCOME - the user salutes or asks what you can do , what you can help with.
    2. PLANNING - the user want to help selecting courses based on credits, interests, or time constrains.
    3. COURSE - the user asks information about an specific course, such as: syllabus inquiry, gradin policies prerequisites, time schedule, title or professor. 
      If the question contains a course code like "CS-XXX" or "CSXXXX", where "CS" is followed by 2-5 digits (e.g. CS-0004 is a course), make sure it is categorized to COURSE. 
    4. CLARIFY - you are not clear about user's question or intent, need to ask further question for clarification. If you can inmply If the user's question is ambiguous but you can infer what they might be asking, include an additional response:
      However, I guess you might be asking: <your best guess at their intended question. Then, attempt to answer the guessed question>.
    5. INVALID - the user asks questions outside computer science, cs department contact information and the available tools.
    6. FOLLOWUP - the user is asking a follow-up question related to a previous response. This category should be triggered when the user's message clearly refers to previous information or when they ask for more details about something mentioned in the previous responses. Analyze the context of the conversation to determine the best way to answer the follow-up question.

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

            - ✅ **Answer the question directly**, using only the provided **retrieval-augmented generation (RAG) data**.
            - ⚠️ **DO NOT make up any information.** If the requested information is not in the RAG source, clearly state:
            - MUST check if it has syllabus link (the link is in below ,if has must be shown in the response!!!!)
            `"I do not have this information in my available data."`
            
            -📘 If the user asks about a specific course (e.g. "CS160", "COMP 131"), try to **locate the RAG context from the course's official syllabus page**. If available, extract:

            - 📊 **Grading Formula** (e.g. homework %, exam %, final project %)
            - 📝 **Assignments or Projects** (e.g. weekly problem sets, group projects)
            - 🕐 **Class Times & Instructors** (from different sections if available)
            - 💡 **Prerequisites or recommended background** - ALWAYS clearly state prerequisites for any course
            - 🌟 **Course Ratings & Reviews** (if available)
            - 🔗 **Official Syllabus Link** (ALWAYS include if available)

            - For syllabus links:
              * If the syllabus link is found in the RAG data, ALWAYS include it in your response
              * If no syllabus link exists for the course, explicitly state: "Syllabus link is not currently available for this course."
              * NEVER use placeholder text like "[Syllabus Link](#)" or similar - if you don't have the link, just say it's not available
              * Do not make up syllabus links - only provide real ones from the RAG data

            Respond using **structured sections** with clear headings and emojis:

            - Overview  
            - Schedule & Instructor  
            - Prerequisites (MUST be included and clearly stated)
            - Grading Breakdown  
            - Assignments & Structure  
            - Course Ratings & Reviews (if available)
            - Syllabus Link (MUST include if available)
            - Follow-Up

            When discussing the course, also consider:
            - How this course fits into broader curriculum planning
            - The relevance of this course to user's stated interests or needs
            - Potential conflicts with other mentioned courses
            - Detailed rationale for why this course might be valuable

        📎 Example format:

        ---

        📘 **Course Overview: CS 131 — Programming Languages**

        - **Focus:** The course introduces algorithms, data structures, and key programming principles.
        - **Credits:** 3
        - **Location:** Medford/Somerville or Online (Section M1)

        🕐 **Schedule:**
        | Section | Days | Time | Location | Instructor |
        |--------|------|------|----------|------------|
        | 01     | Tue/Thu | 10:30–11:45 AM | Medford/Somerville | Jivko Sinapov |
        | M1     | Wed | 7:00–8:30 PM | Online | TBD |

        🧠 **Prerequisites:**  
        - CS15  
        - (CS/Math 61 or Math 65)  
        - Or Graduate Standing

        📊 **Grading:**
        > Currently not specified in the RAG syllabus.  
        > ✅ You can check the official syllabus for updates.

        📝 **Assignments & Format:**  
        > Based on prior iterations, CS 131 may include:
        > - Weekly problem sets  
        > - Midterm & final exams  
        > - Class participation

        🌟 **Course Ratings & Reviews:**
        > Average rating: 4.2/5.0
        > Student feedback highlights challenging but rewarding content

        📎 **Syllabus Link:**  
        🔗 [CS131 Syllabus](https://www.cs.tufts.edu/comp/131/)

            📌 Course Syllabus Sources:
            - CS115: https://davelillethun.wordpress.com/teaching/cs115/
            - CS116: https://cs116.org/
            - CS121: https://www.cs.tufts.edu/comp/150SEN/
            - CS131: https://www.cs.tufts.edu/comp/131/
            - CS135: https://www.cs.tufts.edu/cs/135/2025s/index.html
            - CS160: https://www.cs.tufts.edu/comp/160/
            - CS170: https://www.cs.tufts.edu/comp/170/
            - CS175: https://www.cs.tufts.edu/comp/175/
            - CS201: https://davelillethun.wordpress.com/teaching/cfp/

            ---

            📌 **Follow-Up Formatting Rule:**  
            - ALWAYS generate a follow-up question that is DIRECTLY RELATED to the course being discussed.
            - Follow-up suggestions should be SPECIFIC and USEFUL, such as:
              * Asking about prerequisites for this course
              * Inquiring about other courses that build on this one
              * Asking about how this course fits into a specific concentration
              * Requesting detailed syllabus information
              * Asking about project examples from the course
            
            - Format EXACTLY as follows:
            Follow-Up (visible): Would you like to know [specific course-related topic]?
            Follow-Up (bot format): I want to know [same specific course-related topic].

            - Examples of good follow-ups:
              "Would you like to know what courses build upon CS 160?"
              "Would you like to know about typical projects in CS 170?"
              "Would you like to know how this course helps with AI specialization?"

            ⚠️ Do **not** use "Would you like to" in the bot format.  
            Ensure both versions are included for consistent follow-up generation. 

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
    Uses multiple regex patterns to increase robustness.
    """
    # Primary pattern - strict format
    primary_match = re.search(r'Follow-Up \(visible\): (.+?)\n.*?Follow-Up \(bot format\): (.+)', response_text, re.DOTALL)
    
    if primary_match:
        visible_question = primary_match.group(1).strip()
        bot_question = primary_match.group(2).strip()
        return visible_question, bot_question
    
    # Secondary pattern - more flexible
    secondary_match = re.search(r'Follow-Up.*?visible.*?: (.+?)\n.*?bot format.*?: (.+)', response_text, re.DOTALL | re.IGNORECASE)
    
    if secondary_match:
        visible_question = secondary_match.group(1).strip()
        bot_question = secondary_match.group(2).strip()
        return visible_question, bot_question
    
    # Last resort - look for any follow-up pattern
    fallback_match = re.search(r'Follow-Up.*?:\s*(.+)', response_text, re.IGNORECASE)
    
    if fallback_match:
        visible_question = fallback_match.group(1).strip()
        # Use the same text for both visible and bot format as a fallback
        return visible_question, visible_question.replace("Would you like to", "I want to")
    
    # No follow-up found
    return None, None

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
        - Generate follow-up questions that are DIRECTLY RELATED to the program information discussed.
        - Follow-up questions MUST be specific and valuable, such as:
          * "Would you like to know about internship opportunities in this program?"
          * "Would you like to see what courses are required for the AI concentration?"
          * "Would you like to know about research opportunities in this department?"
        
        - Format EXACTLY as follows:
        Follow-Up (visible): Would you like to know [specific program-related question]?
        Follow-Up (bot format): I want to know [same specific program-related question].
        
        - Examples of effective follow-ups:
          "Would you like to know about the graduation requirements for CS majors?"
          "Would you like to see what electives are popular among cybersecurity students?"
          "Would you like to know about faculty research in machine learning?"
        
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

            Your job is to provide the user with the requested planning information.
            Given the user's prompt and provided context, give a good response.

            Your role is to provide **clear, structured, and informative** answers to students' planning-related questions.

            ---

            When responding:
            - **Only use the provided retrieval-augmented generation (RAG) data.**
            - **DO NOT make up any information.** If the requested data is missing, say:  
            `"I do not have this information in my available data."`
            - Ask for clarification if needed.
            - **ALWAYS provide at least one follow-up question** to encourage continued planning.
            - Use **markdown headers**, **tables**, and **emojis** to enhance structure and readability.
            - Do not write the whole reply in prose or paragraph form.

            ---

            📋 You **MUST follow this exact structure and formatting** below in your response.

            ---

            ### 📌 1. Student Profile  
            List:
            - 🎓 Program / Year  
            - ✅ Completed Courses  
            - 🎯 Goals (e.g. internships, grad school, skill growth)  
            - 💡 Interest Areas  
            - 📅 Preferred Days for Classes  
            - 🔢 Target Number of Credits  
            - 📝 Other Notes (e.g. avoid early mornings)

            ---

            ### 📚 2. Recommended Courses Table  
            For each recommended course (3-4 courses with NO SCHEDULING CONFLICTS), include:

            **CS 180: Machine Learning**
            - Credits: 4
            - Schedule: Mon/Wed 10:00–11:30 AM
            - Instructor: Dr. Smith
            - Prerequisites: CS 15, CS 170
            - Tags: AI, Core
            - Rating: 4.5/5

            **CS 289: Software Engineering**
            - Credits: 4
            - Schedule: Wed 1:00–4:00 PM
            - Instructor: Prof. Wang
            - Prerequisites: CS 121
            - Tags: Software Dev
            - Rating: 4.2/5

            ✅ Critical Requirements:
            - ⚠️ **NEVER include courses with scheduling conflicts in this main recommendation table**
            - ⚠️ **ALWAYS include prerequisites** for each recommended course
            - ⚠️ List course ratings when available (e.g., "4.3/5")
            - Avoid early classes or unwanted days if the student indicated so
            - Reference real Tufts CS course names & times when available
            - Only include courses that can actually be taken together in the same semester
            - Include syllabus links when available

            ---

            ### 📚 3. Alternative Courses  
            Provide 2-3 alternative courses that could replace the recommended ones, with brief explanations of:
            - Why they might be suitable alternatives
            - How they compare to the main recommendations
            - Any advantages/disadvantages they might have
            - ⚠️ **Clearly mark any scheduling conflicts** with other recommended courses

            ---

            ### 📈 4. Course Summary  
            Use bullets or checklist:
            - ✅ Total Credits: [Sum of credits from the non-conflicting recommended courses only]
            - ✅ Interest Areas Covered  
            - ✅ Days of Week used  
            - ✅ Whether early classes were avoided (if applicable)
            - ✅ Prerequisites that need to be satisfied

            ---

            ### 🧠 5. Detailed Reasoning  
            In 4-6 sentences, provide a **detailed explanation** of:
            - Why these specific courses were selected for the student
            - How they align with the student's goals and interests
            - The rationale behind course prioritization
            - How prerequisites are satisfied or need to be addressed
            - Any trade-offs made in the recommendations

            ---

            ### 🔗 6. Course Resources  
            For each recommended course, include:
            - 🔗 Syllabus link (if available)
            - 📊 Any additional resources that might help the student

            ---

            ### ✨ 7. Additional Suggestions  
            Provide 1–3 helpful next steps:
            - 📌 Join CS research talks
            - 📌 Apply for TA/RA positions
            - 📌 Consider an independent study or senior project

            ---

            ✅ Formatting Guidelines:
            - Use clear section headers (### + emojis)
            - Use markdown tables for course recommendations
            - Do NOT summarize in paragraph form
            - If student input is missing, say so politely and provide best-effort recommendations
            - **Double-check that there are NO scheduling conflicts between recommended courses**
            - **Ensure Total Credits reflects ONLY the sum of credits from courses that can actually be taken together**

            ---

            📌 **Follow-Up Formatting Rule:**  
            - The follow-up question **must** be formatted as follows, it can be related to course information or time planning or program information:
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

# FOLLOWUP AGENT
def followup_agent(query, sessionID):
    query_with_rag_context = agent_tools.query_rag_context(query)

    print(query_with_rag_context)

    response_text = generate(
        model = '4o-mini',
        system = f"""
            You are a Tufts University Advisor in the Computer Science Department.

            Your role is to provide **clear, direct answers** to student follow-up questions based on previous conversation context.

            When responding to follow-up questions:
            - **Answer directly and precisely** using the provided RAG context and conversation history
            - **Maintain continuity** with previous answers
            - **If information is missing**, clearly state: "I don't have this specific information in my available data"
            - **Use conversational, helpful tone** with students
            - **Structure your answer** with bullet points, tables, or sections as appropriate
            - Use emojis to enhance readability when appropriate

            Key Guidelines for Course-Related Follow-ups:
            - **Always mention prerequisites** for any discussed course
            - **Never recommend courses with scheduling conflicts in the main recommendations**
            - **Move conflicting courses to alternatives section** and clearly mark the conflicts
            - **Calculate total credits only from non-conflicting courses** that can be taken together
            - **Include syllabus links** whenever available
            - **Provide detailed explanations** about course content and relevance
            - **Include course ratings** if available
            - **Offer alternatives** when discussing course options
            - **Give detailed rationales** for course recommendations

            Additional Response Requirements:
            - Reference previous information in your answer
            - Be specific and provide details when available
            - Ensure a cohesive experience that builds on prior exchanges
            - Always provide at least one follow-up question at the end
            - When discussing multiple courses, use tables to compare them clearly
            - Always check for and avoid scheduling conflicts in main recommendations

            📌 **Follow-Up Formatting Rule:**  
            - Generate follow-up questions that build naturally on the current conversation.
            - Follow-up questions MUST be specific and actionable, such as:
              * "Would you like to know more details about CS 160's projects?"
              * "Would you like to see how this course compares to CS 170?"
              * "Would you like to know what career paths this course prepares you for?"
            
            - Format EXACTLY as follows:
            Follow-Up (visible): Would you like to know [specific, contextual question]?
            Follow-Up (bot format): I want to know [same specific, contextual question].
            
            - Each follow-up should deepen the conversation and provide valuable information that logically extends from the current discussion.

            ⚠️ Do **not** use "Would you like to" in the bot format.  
            Ensure both versions are included for consistent follow-up generation.
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
