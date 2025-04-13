import requests
from flask import Flask, request, jsonify, render_template
from datetime import datetime
import upload_rag
import llm_agents
import agent_tools
import env_variables
from random import randint
import threading

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

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})

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

    if category == 'CAPABILITIES':
        response = {
            "text": f"""
                    I can help you with : (version: {env_variables.version})
                    - **Course Information(25 fall semester courses)**
                    ✅ "Can you provide the grading formula for CS160?"    
                    
                    - **Course Planning(25 spring semester courses)**
                    ✅ "If I take both COMP 150-SEN and CS 15, can you give me the March schedule for both classes?"
                    ✅ "I'm interested in AI—can you recommend three courses?"
                    ✅ "I want to take 9 credits but only attend classes on Tuesdays and Thursdays. Which real courses would you suggest?"
                    """,
            "attachments": [ 
                agent_tools.capabilites_buttons()
            ]
        }

    if category == 'INVALID': # need optimize 
        response = {
            "text": f""" {prompt}
            I am sorry I can only help you with questions regarding the 🐘 CS Department.   
            """
        }
        
    if category == 'CLARIFY':
        response = {
            "text": prompt
        }
    
    if category == "PLANNING":
        response = llm_agents.planning_agent(prompt, user)
    
    if category == "FOLLOWUP":
        response = llm_agents.followup_agent(prompt, user)
    
    return jsonify(response)
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    if env_variables.needToUpload:
        t = threading.Thread(target=upload_rag.upload_all)
        t.start()
    app.run(host='0.0.0.0', port=8000)
