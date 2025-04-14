import requests
import urllib.parse
from llmproxy import generate
import agent_tools
import re
from env_variables import ragSessionId, cs_dept_username, cs_adv_username

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
    0. INTRODUCTION - the user wants to start planning their courses and needs guidance on what to provide. This category should be triggered when the user says  "introduction to shedule" without giving details.
    1. WELCOME - the user salutes or asks what you can do , what you can help with.
    2. PLANNING - the user want to help selecting courses based on credits, interests, or time constrains.
    3. COURSE - the user asks information about an specific course, such as: syllabus inquiry, gradin policies prerequisites, time schedule, title or professor. 
      If the question contains a course code like "CS-XXX" or "CSXXXX", where "CS" is followed by 2-5 digits (e.g. CS-0004 is a course), make sure it is categorized to COURSE. 
    4. CLARIFY - you are not clear about user's question or intent, need to ask further question for clarification. If you can inmply If the user's question is ambiguous but you can infer what they might be asking, include an additional response:
      However, I guess you might be asking: <your best guess at their intended question. Then, attempt to answer the guessed question>.
    5. INVALID - the user asks questions outside computer science, cs department contact information and the available tools.
    6. FOLLOWUP - the user is asking a follow-up question related to a previous response. This category should be triggered when the user's message clearly refers to previous information or when they ask for more details about something mentioned in the previous responses. Analyze the context of the conversation to determine the best way to answer the follow-up question.
    7. RATING - the user explicitly requests rating about a professor's teaching at Tufts University.
    8. MESSAGE DPT - the user explicitly states that wants to send a message to the CS Department.
    9. MESSAGE ADV - the user explicitly states that wants to send a message to a CS Advisor.

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
            - ⚠️ **NEVER make up or fabricate** course details, professor information, ratings, or any other data not found in the RAG sources.
            
            -📘 If the user asks about a specific course (e.g. "CS160", "COMP 131"), try to **locate the RAG context from the course's official syllabus page**. If available, extract:

            - 📊 **Grading Formula** (e.g. homework %, exam %, final project %)
            - 📝 **Assignments or Projects** (e.g. weekly problem sets, group projects)
            - 🕐 **Class Times & Instructors** (from different sections if available)
            - 💡 **Prerequisites or recommended background** - ALWAYS clearly state prerequisites for any course
            - 🌟 **Course and Professor Ratings & Reviews** (if available) - Include specific ratings and student feedback
            - 🔗 **Official Syllabus Link** (ALWAYS include if available)

            Respond using **structured sections** with clear headings and emojis:

            - Overview  
            - Schedule & Instructor  
            - Prerequisites (MUST be included and clearly stated)
            - Grading Breakdown  
            - Assignments & Structure  
            - Course/Professor Ratings & Reviews (if available, be specific about ratings and feedback)
            - Syllabus Link (MUST include if available, if not, MUST do not include)
            - Follow-Up

            When discussing the course, also consider:
            - How this course fits into broader curriculum planning
            - The relevance of this course to user's stated interests or needs
            - Potential conflicts with other mentioned courses
            - Detailed rationale for why this course might be valuable
            - Professor teaching style and reputation based on available ratings (DO NOT invent if not available)

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

        🌟 **Course/Professor Ratings & Reviews:**
        > Course Average rating: 4.2/5.0
        > Professor Average rating: 4.5/5.0
        > Student feedback highlights challenging but rewarding content
        > Students note Professor Sinapov's clear explanations and helpful office hours

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
            - Follow-Up (visible): Would you like to know [specific topic]?
            - Follow-Up (bot format): I want to know [specific topic].

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
    """
    response_text_no_stars = response_text.replace("**", "")
    response_text_no_stars = response_text_no_stars.replace(" (visible)", "")
    match = re.search(r'Follow-Up: (.+?)\n.*?Follow-Up \(bot format\): (.+)', response_text_no_stars, re.DOTALL)

    if match:
        print("matched")
        visible_question = match.group(1).strip()
        bot_question = match.group(2).strip()
        return visible_question, bot_question
    else:
        print("no match")
        return None, None  # No follow-up found

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
            - **NEVER invent or fabricate** course details, professor information, ratings, or any other data not found in the RAG sources.
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
            Provide a markdown table with **3–4 recommended CS courses** that have **NO SCHEDULING CONFLICTS** with each other. Use this exact format:

            | Course Code | Course Name | Credits | Schedule | Time | Instructor | Prerequisites | Tags | Rating |
            |------------|-------------|---------|----------|------|------------|---------------|------|--------|
            | CS 180     | Machine Learning | 4 | Mon/Wed | 10:00–11:30 AM | Dr. Smith | CS 15, CS 170 | AI, Core | 4.5/5 |
            | CS 289     | Software Eng. | 4 | Wed | 1:00–4:00 PM | Prof. Wang | CS 121 | Software Dev | 4.2/5 |

            ✅ Critical Requirements:
            - ⚠️ **NEVER include courses with scheduling conflicts in this main recommendation table**
            - ⚠️ **ALWAYS include prerequisites** for each recommended course
            - ⚠️ List course ratings when available (e.g., "4.3/5")
            - ⚠️ Include professor ratings and student feedback when available
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
            - Include professor ratings and reviews if available (DO NOT invent if not available)

            ---

            ### 📈 4. Course Summary  
            Use bullets or checklist:
            - ✅ Total Credits: [Sum of credits from the non-conflicting recommended courses only]
            - ✅ Interest Areas Covered  
            - ✅ Days of Week used  
            - ✅ Whether early classes were avoided (if applicable)
            - ✅ Prerequisites that need to be satisfied
            - ✅ Average course/professor rating of recommendations (if available)

            ---

            ### 🧠 5. Detailed Reasoning  
            In 4-6 sentences, provide a **detailed explanation** of:
            - Why these specific courses were selected for the student
            - How they align with the student's goals and interests
            - The rationale behind course prioritization
            - How prerequisites are satisfied or need to be addressed
            - Any trade-offs made in the recommendations
            - Professor reputation and teaching style considerations
            - Why these professors might be a good fit based on student feedback and ratings

            ---

            ### 🔗 6. Course Resources  
            For each recommended course, include:
            - 🔗 Syllabus link (if available)
            - 📊 Any additional resources that might help the student
            - 🌟 Specific professor feedback or notable strengths (based only on available data)

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
            - **DO NOT make up information** that is not provided in the RAG data

            ---

            📌 **Follow-Up Formatting Rule:**  
            Always include a follow-up question block at the end, in **both formats**:

            - Follow-Up (visible): Would you like to [explore X]?
            - Follow-Up (bot format): I want to know [explore X].

            ✅ The visible version should be natural and friendly.  
            ✅ The bot-format version should be structured for backend processing.

            ⚠️ **DO NOT use "Would you like to"** in the **bot-format line**.  
            ⚠️ **Both versions must appear** in the response, and clearly labeled.
                
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
            - **DO NOT make up any information** that is not in the RAG data
            - **NEVER invent or fabricate** course details, professor information, ratings, or any other data not found in the RAG sources
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
            - **Include course and professor ratings** if available - be specific about ratings and student feedback
            - **Discuss professor teaching style and reputation** based only on available data
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
            - Follow-Up (visible): Would you like to know [specific topic]?
            - Follow-Up (bot format): I want to know [specific topic].

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

def router_message(message, sessionID):
    router_system = f"""
    You are a Tufts University Advisor in the Computer Science Department.

    ## Instructions ##
    Your job is to correctly classify the user request into one of the following categories:
    - MESSAGE DPT
    - MESSAGE ADV
    - NONE

    You are only allowed to classify into one these three categories.

    ## Categories ##
    1. MESSAGE DPT - the user requests to send a message to CS Department
    2. MESSAGE ADV - the user requests to send a message to a CS Advisor
    3. NONE - the user does not request to send any message

    ## Response Instructions ##
    - You must always responde with a category and a message, in this format: CATEGORY()
    - Example: MESSAGE ADV()
    - Example: MESSAGE DPT()
    - Example: NONE()
    """

    response = generate(
        model="4o-mini",
        system=router_system,
        query=f"""
               User Request: {message}
               """,
        temperature=0.0,
        session_id=sessionID,
        lastk=0
    )

    msg_category, prompt = agent_tools.category_prompt_re_match(response)

    print(f"Message Category ({msg_category}), Prompt: {prompt}")

    # return msg_category, prompt
    if isinstance(response, dict):
        return response['response']

    return response

def detailed_message_agent(message, sessionId, username):
    print(f"Detailing message: {message}")
    router_system = f"""
    You are acting as a mediator agent between a student at Tufts University and a CS Advisor or CS Department contact.

    Your job is to get the user message and given their previous context, 
    elaborate a detailed information explaining the other part what the user is trying to communicate.

    ## Person you are communicating from ##
    - If {username} is {cs_dept_username}, then the message came from the CS Department.
    - If {username} if {cs_adv_username}, then the message came from a CS Advisor.
    Otherwise, the message came from an student.

    ## Person you are communicating to ##
    - If the message came from the CS Department, then your job is to clearly communicate the response to a student. 
    - If the message came from a CS Advisor, then your job is to clearly communicate the response to a student.
    - If the message came from an student, then you job is to clearly communicate the message to a CS Advisor or CS Department contact.

    ## For example ##
    - You receive a message from a user who is a student, you will do your best to provide valuable information to the CS Advisor about the user message.
    - You receive a message from an advisor or CS department, you will do you best to provide a detailed information to the student about the advisor message.

    ## Instructions ##
    - The most important thing is to answer the query.
    - Use previous context as support for your answer.
    - Use bullet points to supply the context to your answer.
    - Finalize the response with a concise answer to the user message.
    """

    response = generate(
        model="4o-mini",
        system=router_system,
        query=f"""
               User Message: {message}
               From User: {username}
               """,
        temperature=0.5,
        session_id=sessionId,
        lastk=20
    )

    print(f"Response: {response['response']}")

    # return msg_category, prompt
    if isinstance(response, dict):
        return response['response']

    return response

def professor_rating_agent(query, sessionId):
    # search_results = agent_tools.web_search(query, 5)
    # print(search_results)
    import json

    professor_name = generate(
        model = "4o-mini",
        system = f"""
            You are an agent working for Tufts University Advisor in the Computer Science Department.

            Your job is to extract the professor's name from the user query.

            The response should only include the professor's name and nothing else.
            """,
        query = query,
        temperature=0.0,
        lastk=0,
        session_id=sessionId
    )

    professor_name = professor_name['response'].replace(' ', '%20')
    print(f'Professor: {professor_name}')

    # 1. Search page
    search_url = f"https://www.ratemyprofessors.com/search/professors/1040?q={professor_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    res = requests.get(search_url, headers=headers)

    # 2. Get legacyId (professor ID)
    matches = re.findall(r'"legacyId":(\d+)', res.text)
    if not matches:
        print("Professor ID not found.")
        exit()

    prof_id = matches[0]

    # 3. Get the professor profile page
    prof_url = f"https://www.ratemyprofessors.com/professor/{prof_id}"
    res = requests.get(prof_url, headers=headers)

    # 4. Extract embedded JSON from <script> tag
    json_match = re.search(r'window\.__RELAY_STORE__ = ({.*});', res.text)

    if not json_match:
        print("Could not find professor data in HTML.")
        exit()

    data = json.loads(json_match.group(1))

    # Professor Info Dictionary
    professor_info = agent_tools.get_professor_info(data)

    # Get List of Rating Comments
    ratings_list = [rating['comment'] for rating in professor_info['ratings']]

    response = generate(
        model = "4o-mini",
        system = f"""
            You are an agent working for Tufts University Advisor in the Computer Science Department.

            Your job is to make retrieve information evaluating a professor.

            You will be given a user query and context.
            
            ## Response Instructions ##
            - Use the provided context to produce an effective and concise response the user query.
            - Always include the reference link in the response.
            - Include 1 to 5 stars based on the professor rating, use whole numebers, for example rating 3.6: ⭐️⭐️⭐️

            ## Response Format ##
            Each should be one line
            - Output the number of stars based on the professor rating, in the following format: >⭐️⭐️⭐️
            - Summary of the Professor's performance that the user might be interested in.
            - Teaching rating
            - Courses difficulty
            - (percentage %) of students would take one of professor's {professor_name} classes again.
            - Number of ratings
            - List a Few Ratings Comments, not more than 5, and use bullet points to separate each comment.
            - Provide reference links from ratemyprofessor websit and Tufts website
            """,
        query = f"""
                User query: {query}

                Professor Information:
                Name: {professor_info['name']}
                Department: {professor_info['dept']}
                Average Rating: {professor_info['avg_rating']}
                Average Difficulty: {professor_info['avg_difficulty']}
                Would Take Again Percent: {professor_info['would_take_again']}
                Number of Ratings: {professor_info['num_ratings']}
                Rate My Professor URL: {prof_url}

                Ratings:
                {ratings_list}
                """,
        temperature=0.2,
        lastk=0,
        session_id=sessionId
    )

    print(f'Professor Rating: {response['response']}')
    
    return response['response']
