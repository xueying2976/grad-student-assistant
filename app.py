from flask import Flask, request, jsonify, render_template
from datetime import datetime
import upload_rag
import llm_agents
import agent_tools
import env_variables
from random import randint
import threading
import re

session_map = {}
# LLM - User Message:
# State what tools are available, be candid to any user prompt.
app = Flask(__name__)

@app.route('/')
def hello_world():
   return render_template('index.html')

@app.route('/chat', methods=['POST'])
def main():
    data = request.get_json()
    print(f"Data: {data}")

    # Extract relevant information
    session = data.get("user_id", 'TestUserName')
    if session not in session_map:
        session_map[session] = 'lxy' + str(len(session_map))
    user = session_map[session] + '-' + env_variables.version
    print("Current user: ", user)
    message = data.get("text", "")
    username = data.get("user_name", "")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})
    
    # Get User message
    # Check if message is allowed or illegal, return false until get allowed request
    if '@' in message and 'sent the following message:' in message:
        print("Getting Message Context")
        match = re.match(r'@(.+) sent the following message:\n(.+)', message)
        from_user = match.group(1)
        message = match.group(2)
        print(f"from: {from_user}, message:{message}")
        
        context = llm_agents.detailed_message_agent(message, user, from_user) # fix
        
        response = {
            "text": f"@{from_user}:\n>{message}\nContext:\n{context}"
        }

        return jsonify(response)

    if 'Not right now, Thank you!' in message:
        response = {
            "text": "Of course! Let me know if need more help 🐘",
            "attachments": [
                {
                    "title": "Need help?",
                    "actions": [
                        {
                            "type": "button",
                            "text": "🔍 Menu",
                            "msg": "Show me what you can do",
                            "msg_in_chat_window": True,
                            "msg_processing_type": "sendMessage"
                        }
                    ]
                }
            ]
        }

        return jsonify(response)
    
    if 'Message to CS Department:' in message:
        message = message.replace('Message to CS Department:', '').strip()

        # context = llm_agents.detailed_message_agent(message, user, from_user)

        status = agent_tools.post_message(message, env_variables.cs_dept_username, username) #add context

        # return jsonify({"text": status})
        return jsonify(
            {
                "text": status,
                "attachments": [ 
                    {
                        "title": "More help?",
                        "actions": [
                            {
                                "type": "button",
                                "text": "🔍 Menu",
                                "msg": "Show me what you can do",
                                "msg_in_chat_window": True,
                                "msg_processing_type": "sendMessage"
                            }
                        ]
                    }
                ]
            }
        )
    
    if 'Message to CS Advisor:' in message:
        message = message.replace('Message to CS Advisor:', '').strip()
        status = agent_tools.post_message(message, env_variables.cs_adv_username, username)

        return jsonify(
            {
                "text": status,
                "attachments": [ 
                    {
                        "title": "More help?",
                        "actions": [
                            {
                                "type": "button",
                                "text": "🔍 Menu",
                                "msg": "Show me what you can do",
                                "msg_in_chat_window": True,
                                "msg_processing_type": "sendMessage"
                            }
                        ]
                    }
                ]
            }
        )
    
    if 'Message to @' in message:
        match = re.match(r'Message to @(.+):(.+)', message)
        
        to_user = match.group(1).strip()
        message = match.group(2).strip()

        status = agent_tools.post_message(message, to_user, username)

        return jsonify(
            {
                "text": status,
                "attachments": [ 
                    {
                        "title": "More help?",
                        "actions": [
                            {
                                "type": "button",
                                "text": "🔍 Menu",
                                "msg": "Show me what you can do",
                                "msg_in_chat_window": True,
                                "msg_processing_type": "sendMessage"
                            }
                        ]
                    }
                ]
            }
        )

    # Receive and classify user's query
    category, prompt = llm_agents.router_agent(message, user)

    response = {"text": "Not Available. Try again."}
    
    if category == 'INTRODUCTION':
            response = {
                "text": f"""
                    I can help you with : (version: {env_variables.version} )
                    - INTRODUCTION(If you'd like me to help you plan your next semester, please provide the following:
                    - 🎓 Your year (e.g. First-year Master's, Sophomore)
                    - 📚 Courses you've already taken
                    - 💡 Interest areas (AI, Cybersecurity...)
                    - 📅 Preferred class days
                    - 🔢 Desired number of credits
                    - 🎯 Specific courses you want to take
                    - 📝 Other notes)
                    """,
            }

    if category == 'WELCOME':
        response = {
            "text": f"""
                Welcome to the Course Planning Chatbot! (version: {env_variables.version})
                I can assist you with various aspects of course planning, including:
                
                - **Course Information**
                ✅ "Can you provide the grading formula for CS160?"
                ✅ "What are the prerequisites for CS160?"
                
                - **Course Scheduling**
                INTRODUCTION(If you'd like me to help you plan your next semester, please provide the following:
                    - 🎓 Your year (e.g. First-year Master's, Sophomore)
                    - 📚 Courses you've already taken
                    - 💡 Interest areas (AI, Cybersecurity...)
                    - 📅 Preferred class days
                    - 🔢 Desired number of credits
                    - 🎯 Specific courses you want to take
                    - 📝 Other notes)
                
                Feel free to ask me anything related to course planning!
                    """,
            "attachments": [ 
                agent_tools.welcome_buttons()
            ]
        }

    if category == 'COURSE':
        response = llm_agents.course_agent(prompt, user)
        
    if category == 'CLARIFY':
        response = {
            "text": prompt
        }
    
    if category == "PLANNING":
        response = llm_agents.planning_agent(prompt, user)
    
    if category == "FOLLOWUP":
        response = llm_agents.followup_agent(prompt, user)

    if category == 'RATING':
        response = {
            "text": llm_agents.professor_rating_agent(prompt, user),
            "attachments": [
                {
                    "actions": [
                        {
                            "type": "button",
                            "text": "👨‍🏫 Search Professor",
                            "msg": "Search for rating of professor: ",
                            "msg_in_chat_window": True,
                            "msg_processing_type": "respondWithMessage"
                        },
                        {
                            "type": "button",
                            "text": "🔍 Menu",
                            "msg": "Show me what you can do",
                            "msg_in_chat_window": True,
                            "msg_processing_type": "sendMessage"
                        }
                    ]
                }
            ]
        }

    if category == 'MESSAGE DPT':
        response = {
            "text": "Would you like to send a Message?",
            "attachments": [
                {
                    "actions": [
                        {
                            "type": "button",
                            "text": "✅ Yes",
                            "msg": "Message to CS Department: ",
                            "msg_in_chat_window": True,
                            "msg_processing_type": "respondWithMessage"
                        },
                        {
                            "type": "button",
                            "text": "❌ No",
                            "msg": "Not right now, Thank you! :)",
                            "msg_in_chat_window": True,
                            "msg_processing_type": "sendMessage"
                        }
                    ]
                }
            ]
        }
    
    if category == 'MESSAGE ADV':
        response = {
            "text": "Would you like to send a Message?",
            "attachments": [
                {
                    "actions": [
                        {
                            "type": "button",
                            "text": "✅ Yes",
                            "msg": "Message to CS Advisor: ",
                            "msg_in_chat_window": True,
                            "msg_processing_type": "respondWithMessage"
                        },
                        {
                            "type": "button",
                            "text": "❌ No",
                            "msg": "Not right now, Thank you! :)",
                            "msg_in_chat_window": True,
                            "msg_processing_type": "sendMessage"
                        }
                    ]
                }
            ]
        }

    if category == 'INVALID': # need optimize 
        response = {
            "text": f""" {prompt}
            I am sorry I can only help you with questions regarding the 🐘 CS Department.   
            """
        }
    
    return jsonify(response)
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    if env_variables.needToUpload:
        t = threading.Thread(target=upload_rag.upload_all)
        t.start()
    app.run(host='0.0.0.0', port=8000)
