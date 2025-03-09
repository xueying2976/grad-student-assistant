import requests
from flask import Flask, request, jsonify, render_template
from datetime import datetime
import upload_rag
import llm_agents
import agent_tools
import env_variables
from random import randint

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
    user = data.get("user_id", 'TestUserName') + '-' + env_variables.version
    message = data.get("text", "")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})

    # Get User message
    # Check if message is allowed or illegal, return false until get allowed request

    # Receive and classify user's query
    category, prompt = llm_agents.router_agent(message, user)

    print(f"Prompt: {prompt}")
    response = {"text": "Not Available. Try again."}

    if category == 'WELCOME':
        response = {
            "text": f"""
                    {prompt} 🐘
                    """
        }


    if category == 'WELCOME':
            response = {
                "text": f"""
                        Hello, I can help you with: (version: {env_variables.version})
                        - Course Information
                        - Program Requirements
                        - Course Planning
                        - CS Department Contact
                        - Job Recommendation
                        💡 Here are some example questions you can ask me:
                        ✅ "If I take both COMP 150-SEN and CS 15, can you give me the March schedule for both classes?"
                        ✅ "How many credits do you recommend per semester for a CS graduate student?"
                        ✅ "Can you provide the grading formula for CS160?"
                        ✅ "I'm interested in AI—can you recommend three courses?"
                        ✅ "I want to take 9 credits but only attend classes on Tuesdays and Thursdays. Which real courses would you suggest?"
                        ✅ "What job can I do if I take CS160 Algorithm"
                        """,
                "attachments": [ 
                    agent_tools.welcome_buttons()
                ]
            }




    if category == 'COURSE':
        response = llm_agents.course_agent(prompt, user)

    if category == 'PROGRAM':
        response = {
            "text": llm_agents.program_agent(prompt, user)
        }

    if category == 'CAPABILITIES':
        response = {
            "text": f"""
                    I can help you with:
                    - Course Information
                    - Program Requirements
                    - Course Planning
                    - CS Department Contact
                    - Job Recommendation
                    💡 Here are some example questions you can ask me:
                    ✅ "If I take both COMP 150-SEN and CS 15, can you give me the March schedule for both classes?"
                    ✅ "How many credits do you recommend per semester for a CS graduate student?"
                    ✅ "Can you provide the grading formula for CS160?"
                    ✅ "I'm interested in AI—can you recommend three courses?"
                    ✅ "I want to take 9 credits but only attend classes on Tuesdays and Thursdays. Which real courses would you suggest?"
                    ✅ "What job can I do if I take CS160 Algorithm"

                    """,
            "attachments": [ 
                agent_tools.capabilites_buttons()
            ]
        }

    if category == 'CONTACT':
        response = {
            "text": llm_agents.contact_agent(prompt, user),
            "attachments": [
                agent_tools.contact_buttons(prompt)
            ]
        }

    if category == 'MESSAGE DPT':   
        response = {
            "text": agent_tools.message_user(prompt, "javier.villegas_nunez")
        }

    if category == 'INVALID':
        response = {
            "text": "I am sorry I can only help you with questions regarding the 🐘 CS Department"
        }
        
    if category == 'CLARIFY':
        response = {
            "text": prompt
        }
        
    if category == "PLANNING":
        response = {
            "text": llm_agents.planning_agent(prompt, user)
        }
        
    if category == 'JOB':
        response = {
            "text": llm_agents.job_agent(prompt, user)
        }
    
    return jsonify(response)
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    if env_variables.needToUpload:
        upload_rag.upload_all()
    app.run(host='0.0.0.0', port=8000)
