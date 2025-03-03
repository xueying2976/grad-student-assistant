import requests
from flask import Flask, request, jsonify
from datetime import datetime
import upload_rag
import llm_agents
import agent_tools

# LLM - User Message:
# State what tools are available, be candid to any user prompt.

app = Flask(__name__)

@app.route('/')
def hello_world():
   return jsonify({"text":'Hello from Koyeb - you reached the main page!'})

@app.route('/chat', methods=['POST'])
def main():
    data = request.get_json() 
    print(f"Data: {data}")

    # Extract relevant information
    # user = data.get("user_name", "Unknown")
    user = "TestUser-00"
    message = data.get("text", "")

    print(data)

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})

    print(f"Message from {user} : {message}")

    current_date = datetime.now().strftime("%B %d, %Y")

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

    if category == 'COURSE':
        response = {
            "text": llm_agents.course_agent(prompt, user)
        }

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
    
    return jsonify(response)
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    upload_rag.upload_all()
    app.run(host='0.0.0.0', port=8000)
